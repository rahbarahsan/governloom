"""Exercise the public hook against a real collector process, without a model provider."""

import json
import os
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

from governloom.hook import MonitoringUnavailable, PolicyViolation, RuntimeHook


def test_http_hook_prediction_block_late_outcome_and_tool_boundary(tmp_path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    admin = "integration-admin-" + "x" * 32
    environment = {**os.environ, "GOVERNLOOM_DB": f"sqlite:///{tmp_path / 'collector.db'}",
                   "GOVERNLOOM_ADMIN_TOKEN": admin}
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "governloom.api:app", "--host", "127.0.0.1", "--port", str(port)],
                               env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def api(path, body=None):
        request = Request(endpoint + "/api" + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Authorization": "Bearer " + admin, "Content-Type": "application/json"})
        with urlopen(request, timeout=2) as response:
            return json.load(response)

    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                api("/health")
                break
            except (URLError, OSError):
                assert process.poll() is None, "Collector exited before readiness"
                if time.monotonic() >= deadline:
                    pytest.fail("Collector did not become ready")
                time.sleep(0.05)
        app = api("/applications", {"name": "HTTP serving integration", "purpose": "Existing predictions",
                                    "owner": "Serving team", "expected_behavior": "Enforce configured limits"})
        prefix = f"/applications/{app['id']}"
        api(prefix + "/monitor-policy", {"name": "Serving boundaries", "actor": "operator", "rationale": "Integration check",
            "rules": [
                {"id": "confidence", "name": "Low confidence", "detector": "metric_threshold", "task_type": "vision",
                 "phase": "output", "metric": "confidence", "comparator": "lt", "threshold": 0.8,
                 "action": "block", "mitigation": "Withhold uncertain output"},
                {"id": "forecast", "name": "Outcome error", "detector": "metric_threshold", "task_type": "forecasting",
                 "phase": "outcome", "metric": "absolute_error", "threshold": 10, "mitigation": "Investigate forecast"},
                {"id": "tools", "name": "Allowed tools", "detector": "tool_allowlist", "phase": "tool",
                 "allowed": ["search"], "action": "block", "mitigation": "Deny unauthorized operation"}]})
        key = api(prefix + "/ingest-keys", {"name": "serving", "actor": "operator"})["key"]
        observed = RuntimeHook(endpoint, key, mode="observe")
        result = {"confidence": 0.2, "label": "uncertain"}
        prediction = observed.wrap(lambda _: result, task_type="vision", model_version="cv-1", application_version="service-1",
                                   output_mapper=lambda output: {"metrics": {"confidence": output["confidence"]}, "labels": [output["label"]]})
        assert prediction(object()) is result and observed.last_receipt["action"] == "block"
        enforced = RuntimeHook(endpoint, key, mode="enforce")
        with pytest.raises(PolicyViolation):
            enforced.wrap(lambda: result, task_type="vision", model_version="cv-1", application_version="service-1",
                          output_mapper=lambda output: {"metrics": {"confidence": output["confidence"]}})()
        called = []
        with pytest.raises(PolicyViolation):
            enforced.wrap_tool(lambda: called.append(True), tool_name="delete", task_type="custom",
                               model_version="agent-1", application_version="service-1")()
        assert not called
        context = {"trace_id": "forecast-real-http", "task_type": "forecasting", "model_version": "f-1", "application_version": "service-1"}
        receipt = observed.emit(**context, phase="output", metrics={"prediction": 100})
        outcome = observed.emit(**context, phase="outcome", related_event_id=receipt["event_id"], metrics={"actual": 125})
        assert outcome["action"] == "flag"
        alerts = api(prefix + "/runtime-alerts")
        assert len(alerts) == 4
        reviewed = api(f"/runtime-alerts/{alerts[0]['id']}/review", {"actor": "operator", "owner": "Serving team",
            "status": "mitigated", "rationale": "Recorded operator action", "expected_revision": 1})
        assert reviewed["revision"] == 2
        assert len(api(prefix + "/runtime-events")["events"]) == 7
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_http_redirect_never_forwards_ingestion_key():
    visited = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            visited.append(self.path)
            self.send_response(307)
            self.send_header("Location", "/redirect-target")
            self.send_header("Content-Length", "0")
            self.end_headers()
        def log_message(self, *args):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        hook = RuntimeHook(f"http://127.0.0.1:{server.server_port}", "gl_test.secret")
        with pytest.raises(MonitoringUnavailable):
            hook.emit(trace_id="redirect-test", phase="output", task_type="custom", model_version="v1", application_version="v1")
        assert visited == ["/api/runtime/events"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
