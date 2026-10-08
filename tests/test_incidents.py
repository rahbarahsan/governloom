import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from governloom.api import create_app
from governloom.monitoring import ActionAcknowledgment, ActionVerification, AlertReview, Monitor, MonitorPolicy, RuntimeEvent
from governloom.schemas import Application
from governloom.storage import Entity, Store


def setup(workbench):
    app = workbench.create_application(Application(name="Model service", purpose="Incident checks", owner="Test", expected_behavior="Withhold"))
    monitor = Monitor(workbench)
    policy = monitor.policy(app["id"], MonitorPolicy(name="Group uncertainty", actor="operator", rationale="Incident check",
        incident_window_seconds=86400, escalate_after_count=2, escalation_cooldown_seconds=300,
        rules=[{"id": "uncertainty", "name": "Uncertainty", "detector": "metric_threshold", "metric": "confidence",
                "comparator": "lt", "threshold": 0.8, "action": "block", "mitigation": "Queue review"}]))
    key = monitor.issue_key(app["id"], "agent", "operator")["key"]
    def emit(**values):
        return monitor.ingest(key, RuntimeEvent(**{"trace_id": "incident-test", "phase": "output", "task_type": "vision",
            "model_version": "model-1", "application_version": "app-1", "metrics": {"confidence": 0.3}, **values}))
    return app, monitor, policy, key, emit


def test_incident_grouping_policy_isolation_owner_restart_and_action_states(workbench):
    app, monitor, policy, key, emit = setup(workbench)
    first, second, third = emit(), emit(), emit()
    assert first["incident_ids"] == second["incident_ids"] == third["incident_ids"]
    incident = monitor.incidents(app["id"])[0]
    assert incident["count"] == 3 and incident["escalations_queued"] == 1
    assert len(monitor.store.list("runtime_escalation", app["id"])) == 1
    emit(model_version="model-2")
    assert len(monitor.incidents(app["id"])) == 2
    revised = monitor.review_incident(incident["id"], AlertReview(actor="operator", owner="Serving owner", status="acknowledged",
        rationale="Investigating grouped events", expected_revision=incident["revision"]))
    with pytest.raises(ValueError, match="Stale"):
        monitor.review_incident(incident["id"], AlertReview(actor="operator", owner="Serving owner", status="mitigated", rationale="Stale", expected_revision=1))
    body = ActionAcknowledgment(alert_id=first["alert_ids"][0], action_type="withheld", evidence_id="response-record-1")
    action = monitor.acknowledge_action(key, body)
    assert action["status"] == "acknowledged" and action["verification"] is None
    assert monitor.acknowledge_action(key, body)["id"] == action["id"]
    client = TestClient(create_app(workbench.store))
    assert client.post("/api/runtime/actions", json={**body.model_dump(), "status": "verified"}, headers={"Authorization": "Bearer " + key}).status_code == 422
    other = workbench.create_application(Application(name="Other", purpose="Isolation", owner="Test", expected_behavior="Scope"))
    other_key = monitor.issue_key(other["id"], "other", "operator")["key"]
    assert client.post("/api/runtime/actions", json=body.model_dump(), headers={"Authorization": "Bearer " + other_key}).status_code == 401
    verification = ActionVerification(actor="Evidence inspector", criterion="response_withheld", evidence_sha256="a" * 64, rationale="Inspected the HTTP response capture")
    verified = monitor.verify_action(action["id"], verification)
    assert verified["status"] == "verified_by_operator" and "attestation" in verified["limitation"]
    reloaded = Store(workbench.store.url)
    try:
        assert reloaded.get("runtime_incident", incident["id"])["owner"] == revised["owner"]
        assert reloaded.get("runtime_action", action["id"])["verification"]["evidence_sha256"] == "a" * 64
        assert len([row for row in reloaded.list("review_event", app["id"]) if row.get("action", "").startswith("runtime_")]) >= 1
    finally:
        reloaded.engine.dispose()


def test_test_sink_retry_exact_notification_and_audit(workbench, tmp_path):
    from examples.common import http
    from examples.processes import Processes
    from governloom.escalation import dispatch_test_sink
    app, monitor, _, _, emit = setup(workbench)
    emit()
    emit()
    with Processes(tmp_path / "logs") as processes:
        endpoint = processes.start("examples.test_sink:create_app", {"MINI_STATE": str(tmp_path / "sink.db"), "SINK_LOSE_FIRST_ACK": "1"}, factory=True)
        sink = endpoint + "/governloom-test-sink"
        first = dispatch_test_sink(monitor, sink, "test dispatcher")
        assert first["retry_pending"] == 1 and len(http(endpoint, "/notifications")) == 1
        with monitor.store.session() as session:
            row = session.scalar(select(Entity).where(Entity.kind == "runtime_escalation"))
            row.payload = {**row.payload, "next_attempt_at": time.time() - 1}
        second = dispatch_test_sink(monitor, sink, "test dispatcher")
        assert second["delivered"] == 1 and len(http(endpoint, "/notifications")) == 1
    assert monitor.store.list("runtime_escalation", app["id"])[0]["attempts"] == 2
    audits = json.dumps(monitor.store.list("review_event", app["id"]))
    assert "runtime_escalation_attempt" in audits and "runtime_escalation_result" in audits
    with pytest.raises(ValueError, match="127.0.0.1"):
        dispatch_test_sink(monitor, "https://example.com/webhook", "test dispatcher")
