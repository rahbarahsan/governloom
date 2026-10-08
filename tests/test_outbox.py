import json
import os
import subprocess
import sys
import threading
import time

import pytest

from governloom.hook import MonitoringUnavailable
from governloom.outbox import DurableObservationHook

FIELDS = dict(trace_id="durable-test", phase="output", task_type="vision", model_version="v1", application_version="v1")


def test_pending_survives_close_bounds_privacy_binding_and_expiry(tmp_path):
    path = tmp_path / "outbox.db"
    hook = DurableObservationHook("http://127.0.0.1:8000", "gl_test.key", outbox=path, queue_size=1, auto_start=False)
    assert hook.emit(**FIELDS)["action"] == "queued"
    assert hook.emit(**FIELDS)["reason"] == "overflow"
    for extra in ({"text": "private output"}, {"labels": ["person@example.org"]}, {"labels": ["gl_test.key"]}, {"labels": ["gl_another.key"]}):
        with pytest.raises(ValueError):
            hook.emit(**FIELDS, **extra)
    assert hook.close(0)["pending"] == 1
    with pytest.raises(ValueError, match="binding"):
        DurableObservationHook("http://127.0.0.1:8000", "gl_other.key", outbox=path, queue_size=1)
    seen = []
    def transport(event):
        seen.append(event)
        return {"event_id": event["event_id"], "action": "block"}
    reopened = DurableObservationHook("http://127.0.0.1:8000", "gl_test.key", outbox=path, queue_size=1, transport=transport)
    assert reopened.close()["accepted"] == 1
    assert seen[0]["text"] is None and reopened.stats["text_coverage"] == "unavailable"
    assert reopened.stats["dropped"] == 1
    assert reopened.terminal_records()[0]["status"] == "accepted"
    assert b"gl_test.key" not in path.read_bytes() and b"private output" not in path.read_bytes()
    expired = DurableObservationHook("http://127.0.0.1:8000", "gl_test.key", outbox=tmp_path / "expired.db", max_age_seconds=0.02, auto_start=False)
    expired.emit(**FIELDS)
    time.sleep(0.03)
    expired.worker.start()
    assert expired.close()["expired"] == 1


def test_concurrent_admission_terminal_auth_and_exact_retry(tmp_path):
    bodies = []
    lock = threading.Lock()
    def transport(event):
        with lock:
            bodies.append(json.dumps(event))
            first = len(bodies) == 1
        if first:
            raise MonitoringUnavailable("Lost receipt")
        return {"event_id": event["event_id"], "action": "allow"}
    hook = DurableObservationHook("http://127.0.0.1:8000", "gl_test.key", outbox=tmp_path / "retry.db", queue_size=2, transport=transport, backoff_seconds=0, auto_start=False)
    threads = [threading.Thread(target=lambda: hook.emit(**FIELDS)) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert hook.stats["pending"] == 2 and hook.stats["dropped"] == 8
    hook.worker.start()
    assert hook.close()["accepted"] == 2
    assert bodies[0] == bodies[1]
    def unauthorized(event):
        raise MonitoringUnavailable("Denied", retryable=False, status_code=401)
    hook = DurableObservationHook("http://127.0.0.1:8000", "gl_test.key", outbox=tmp_path / "auth.db", transport=unauthorized)
    hook.emit(**FIELDS)
    stats = hook.close()
    assert stats["auth_failed"] == 1 and stats["failed"] == 1 and stats["retries"] == 0


def test_process_death_after_real_collector_commit_recovers_one_alert(tmp_path):
    from examples.common import http
    from examples.processes import Processes
    admin = "durable-test-admin-" + "x" * 32
    with Processes(tmp_path / "logs") as processes:
        endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": f"sqlite:///{(tmp_path / 'collector.db').as_posix()}", "GOVERNLOOM_ADMIN_TOKEN": admin}, readiness="/api/health")
        application = http(endpoint, "/api/applications", {"name": "Crash recovery", "purpose": "Test", "owner": "Test", "expected_behavior": "Deduplicate"}, admin)
        prefix = f"/api/applications/{application['id']}"
        http(endpoint, prefix + "/monitor-policy", {"name": "Errors", "actor": "test", "rationale": "Crash check", "rules": [{"id": "err", "name": "Error", "detector": "target_error", "mitigation": "Investigate"}]}, admin)
        key = http(endpoint, prefix + "/ingest-keys", {"name": "test", "actor": "test"}, admin)["key"]
        path = tmp_path / "crashed.db"
        environment = {**os.environ, "TEST_ENDPOINT": endpoint, "TEST_KEY": key, "TEST_OUTBOX": str(path)}
        code = '''import os, time
from governloom.outbox import DurableObservationHook
from governloom.hook import RuntimeHook
sync = RuntimeHook(os.environ["TEST_ENDPOINT"], os.environ["TEST_KEY"], timeout_seconds=0.1)
def crash(event):
    sync._send(event)
    os._exit(23)
hook = DurableObservationHook(os.environ["TEST_ENDPOINT"], os.environ["TEST_KEY"], outbox=os.environ["TEST_OUTBOX"], timeout_seconds=0.1, transport=crash, backoff_seconds=0)
hook.emit(trace_id="crash", phase="error", error_type="TestFailure", task_type="custom", model_version="v1", application_version="v1")
time.sleep(10)
'''
        child = subprocess.run([sys.executable, "-c", code], env=environment, timeout=15, capture_output=True)
        assert child.returncode == 23, child.stderr.decode()
        original = http(endpoint, prefix + "/runtime-events", token=admin)["events"][0]
        reopened = DurableObservationHook(endpoint, key, outbox=path, timeout_seconds=0.1, backoff_seconds=0)
        stats = reopened.close(10)
        assert stats["accepted"] == 1 and stats["retries"] == 1 and stats["pending"] == 0
        assert reopened.last_receipt["duplicate"]
        assert http(endpoint, prefix + "/runtime-events", token=admin)["events"][0] == original
        assert len(http(endpoint, prefix + "/runtime-alerts", token=admin)) == 1
