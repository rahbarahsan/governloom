import json
import threading
import time

import pytest

from governloom.delivery import ObservationHook
from governloom.hook import MonitoringUnavailable

FIELDS = dict(trace_id="delivery-test", phase="output", task_type="custom", model_version="real-target-v1", application_version="service-v1")


def test_retry_after_supports_dates_and_does_not_shorten_server_delay():
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime
    from governloom.hook import retry_delay
    assert retry_delay("60") == 60
    assert 59 <= retry_delay(format_datetime(datetime.now(timezone.utc) + timedelta(seconds=60))) <= 60
    assert retry_delay("invalid") is None and retry_delay("-2") is None
    assert retry_delay("9" * 100) == float("inf")


def test_lost_receipt_retry_preserves_body_and_observation_return():
    bodies = []
    def transport(event):
        bodies.append(json.dumps(event))
        if len(bodies) == 1:
            raise MonitoringUnavailable("Lost receipt")
        return {"event_id": event["event_id"], "action": "block"}
    hook = ObservationHook("http://127.0.0.1:8000", "gl_test.key", transport=transport, backoff_seconds=0)
    wrapped = hook.wrap(lambda: "real return", task_type="custom", model_version="v1", application_version="v1")
    assert wrapped() == "real return"
    stats = hook.close()
    assert bodies[0] == bodies[1]
    assert stats["accepted"] == 2 and stats["retries"] == 1 and stats["pending"] == 0 and not stats["worker_alive"]
    assert hook.emit(**FIELDS)["reason"] == "closed"
    with pytest.raises(ValueError, match="cannot enforce"):
        ObservationHook("http://127.0.0.1:8000", "gl_test.key", mode="enforce")


def test_queue_overflow_and_shutdown_exposes_inflight_request():
    entered, release = threading.Event(), threading.Event()
    def transport(event):
        entered.set()
        release.wait(2)
        return {"event_id": event["event_id"], "action": "allow"}
    hook = ObservationHook("http://127.0.0.1:8000", "gl_test.key", transport=transport, queue_size=2)
    hook.emit(**FIELDS)
    assert entered.wait(1)
    hook.emit(**FIELDS)
    assert hook.emit(**FIELDS)["reason"] == "overflow"
    started = time.monotonic()
    stats = hook.close(drain_seconds=0)
    assert time.monotonic() - started < 0.2
    assert stats["dropped"] == 2 and stats["pending"] == 1 and stats["worker_alive"]
    release.set()
    hook.worker.join(2)
    assert hook.stats["accepted"] == 1 and hook.stats["pending"] == 0 and not hook.stats["worker_alive"]


def test_auth_is_not_retried_and_rate_limit_age_is_visible():
    for status, retryable, category in ((401, False, "auth_failed"), (429, True, "rate_limited")):
        def transport(event):
            raise MonitoringUnavailable("Rejected", status_code=status, retryable=retryable, retry_after_seconds=60)
        hook = ObservationHook("http://127.0.0.1:8000", "gl_test.key", transport=transport, max_age_seconds=1)
        hook.emit(**FIELDS)
        stats = hook.close()
        assert stats[category] == 1 and stats["retries"] == 0
        assert stats["failed" if status == 401 else "expired"] == 1


def test_byte_bound_drops_large_text_without_persistence():
    hook = ObservationHook("http://127.0.0.1:8000", "gl_test.key", max_queue_bytes=500)
    assert hook.emit(**FIELDS, text="sensitive" * 100)["action"] == "dropped"
    assert hook.close()["bytes_pending"] == 0


def test_heartbeat_scoping_boot_sequence_and_quiet_traffic(workbench):
    from datetime import datetime, timedelta, timezone
    from fastapi.testclient import TestClient
    from governloom.api import create_app
    from governloom.monitoring import Monitor, MonitorPolicy
    from governloom.schemas import Application
    from governloom.storage import Entity

    monitor = Monitor(workbench)
    app = workbench.create_application(Application(name="Batch forecaster", purpose="Monthly forecasting", owner="Test", expected_behavior="Send separate heartbeat"))
    key = monitor.issue_key(app["id"], "agent", "operator")["key"]
    monitor.policy(app["id"], MonitorPolicy(name="Cadence", actor="operator", rationale="Quiet batch traffic is expected",
        heartbeat_timeout_seconds=10, rules=[{"id": "errors", "name": "Errors", "detector": "target_error", "mitigation": "Inspect"}]))
    client = TestClient(create_app(workbench.store))
    headers = {"Authorization": "Bearer " + key}
    body = {"agent_id": "batch-agent", "boot_id": "boot-1", "sequence": 1,
            "occurred_at": datetime.now(timezone.utc).isoformat(), "counters": {"emitted": 0, "accepted": 0}}
    response = client.post("/api/runtime/heartbeats", json=body, headers=headers)
    assert response.status_code == 200
    assert client.post("/api/runtime/heartbeats", json=body, headers=headers).json()["duplicate"]
    assert client.post("/api/runtime/heartbeats", json=body).status_code == 401
    identifier = response.json()["id"]
    with workbench.store.session() as session:
        row = session.get(Entity, identifier)
        row.payload = {**row.payload, "received_at": (datetime.now(timezone.utc) - timedelta(seconds=11)).isoformat()}
    assert monitor.agents(app["id"])[0]["status"] == "stale"
    body.update(sequence=2, occurred_at=datetime.now(timezone.utc).isoformat(), counters={"emitted": 10, "accepted": 9})
    assert client.post("/api/runtime/heartbeats", json=body, headers=headers).status_code == 200
    assert monitor.agents(app["id"])[0]["status"] == "reporting"
    assert monitor.events(app["id"])["events"] == []  # Heartbeats do not pretend to be predictions.
    body.update(sequence=3, occurred_at=datetime.now(timezone.utc).isoformat(), counters={"emitted": 0, "accepted": 0})
    assert client.post("/api/runtime/heartbeats", json=body, headers=headers).status_code == 409
    body.update(sequence=1, boot_id="boot-2", occurred_at=datetime.now(timezone.utc).isoformat())
    assert client.post("/api/runtime/heartbeats", json=body, headers=headers).status_code == 200


def test_real_http_outage_restart_and_lost_ack_deduplicate(tmp_path):
    import secrets
    from urllib.parse import urlsplit
    from examples.common import http
    from examples.processes import Processes
    from governloom.hook import RuntimeHook

    admin = secrets.token_urlsafe(32)
    environment = {"GOVERNLOOM_DB": f"sqlite:///{(tmp_path / 'collector.db').as_posix()}", "GOVERNLOOM_ADMIN_TOKEN": admin}
    with Processes(tmp_path / "logs") as processes:
        endpoint = processes.start("governloom.api:app", environment, readiness="/api/health")
        def call(path, body=None):
            return http(endpoint, "/api" + path, body, admin)
        app = call("/applications", {"name": "Restart test", "purpose": "Delivery test", "owner": "Test", "expected_behavior": "Recover exact event"})
        prefix = f"/applications/{app['id']}"
        call(prefix + "/monitor-policy", {"name": "Errors", "actor": "test", "rationale": "Outage check",
            "rules": [{"id": "error", "name": "Target error", "detector": "target_error", "phase": "error", "mitigation": "Inspect target"}]})
        key = call(prefix + "/ingest-keys", {"name": "test", "actor": "test"})["key"]
        synchronous = RuntimeHook(endpoint, key, timeout_seconds=0.3)
        attempts = []
        def lost_ack(event):
            attempts.append(json.dumps(event))
            receipt = synchronous._send(event)
            if len(attempts) == 1:
                raise MonitoringUnavailable("Receipt lost after commit")
            return receipt
        hook = ObservationHook(endpoint, key, transport=lost_ack, backoff_seconds=0)
        hook.emit(**{**FIELDS, "phase": "error", "error_type": "DeclaredTestFailure"})
        assert hook.close()["accepted"] == 1
        assert attempts[0] == attempts[1] and len(call(prefix + "/runtime-alerts")) == 1
        processes.stop_last()
        hook = ObservationHook(endpoint, key, timeout_seconds=0.3, backoff_seconds=0.3, max_attempts=10, max_age_seconds=15)
        try:
            hook.emit(**FIELDS)
            # Starting the same DB/port includes a real period of collector unavailability.
            processes.start("governloom.api:app", environment, port=urlsplit(endpoint).port, readiness="/api/health")
            stats = hook.close(drain_seconds=10)
            assert stats["accepted"] == 1 and stats["retries"] >= 1 and not stats["worker_alive"]
            assert len(call(prefix + "/runtime-events")["events"]) == 2
            synchronous.heartbeat(agent_id="http-agent", boot_id="boot-1", sequence=1,
                                  counters={name: stats[name] for name in ("emitted", "queued", "accepted", "dropped", "failed", "pending")})
            assert call(prefix + "/runtime-agents")[0]["heartbeat"]["counters"]["accepted"] == 1
        finally:
            hook.close(1)


def test_independent_heartbeat_retries_same_boot_sequence_until_acknowledged():
    from governloom.delivery import HeartbeatReporter
    bodies = []
    class HeartbeatFixture(ObservationHook):
        def heartbeat(self, **fields):
            bodies.append(json.dumps(fields, sort_keys=True))
            if len(bodies) == 1:
                raise MonitoringUnavailable("Lost heartbeat receipt")
            return {"id": "test-agent", "duplicate": False}
    hook = HeartbeatFixture("http://127.0.0.1:8000", "gl_test.key")
    reporter = HeartbeatReporter(hook, "quiet-agent", interval_seconds=0.01)
    try:
        deadline = time.monotonic() + 1
        while reporter.sent < 2 and time.monotonic() < deadline:
            time.sleep(0.005)
        assert reporter.sent >= 2 and reporter.failures == 1
        assert bodies[0] == bodies[1]
        assert json.loads(bodies[2])["sequence"] == 2
    finally:
        assert not reporter.close()["worker_alive"]
        hook.close()
