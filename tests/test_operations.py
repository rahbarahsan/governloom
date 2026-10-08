import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.operations import backup, restore, retention
from governloom.schemas import Application
from governloom.service import Workbench
from governloom.storage import Entity, RuntimeObservation, Store


def test_live_wal_backup_restore_preserves_ingest_idempotency_and_evidence(workbench, tmp_path):
    monitor = Monitor(workbench)
    app = workbench.create_application(Application(name="Restore", purpose="Recover", owner="Test", expected_behavior="Keep evidence"))
    policy = monitor.policy(app["id"], MonitorPolicy(name="Errors", actor="operator", rationale="Restore check",
        rules=[{"id": "errors", "name": "Errors", "detector": "target_error", "mitigation": "Inspect"}]))
    key = monitor.issue_key(app["id"], "agent", "operator")["key"]
    event = RuntimeEvent(trace_id="backup-trace", phase="error", task_type="custom", model_version="v1", application_version="v1", error_type="DeclaredFailure")
    receipt = monitor.ingest(key, event)
    source = workbench.store.url.removeprefix("sqlite:///")
    snapshot = tmp_path / "backup.db"
    record = backup(source, snapshot)
    assert record["counts"]["runtime_observations"] == 1
    with pytest.raises(FileExistsError):
        backup(source, snapshot)
    destination = tmp_path / "restored.db"
    restore(snapshot, destination)
    recovered = Store(f"sqlite:///{destination.as_posix()}")
    try:
        replay = Monitor(Workbench(recovered)).ingest(key, event)
        assert replay["duplicate"] and replay["cursor"] == receipt["cursor"]
        assert recovered.get("monitor_policy", policy["id"]) == policy
        assert len(recovered.list("runtime_alert", app["id"])) == 1
        assert len(recovered.list("runtime_incident", app["id"])) == 1
        assert recovered.list("review_event", app["id"])
    finally:
        recovered.engine.dispose()
    with snapshot.open("ab") as target:
        target.write(b"corruption")
    with pytest.raises(ValueError, match="checksum"):
        restore(snapshot, tmp_path / "bad.db")
    assert not (tmp_path / "bad.db").exists()


def test_retention_preview_apply_protects_alerts_outcome_links_and_cursor(workbench):
    monitor = Monitor(workbench)
    app = workbench.create_application(Application(name="Retention", purpose="Bound history", owner="Test", expected_behavior="Keep evidence"))
    monitor.policy(app["id"], MonitorPolicy(name="Errors", actor="operator", rationale="Retention check",
        rules=[{"id": "errors", "name": "Errors", "detector": "target_error", "phase": "error", "mitigation": "Inspect"}]))
    key = monitor.issue_key(app["id"], "agent", "operator")["key"]
    context = dict(trace_id="retention-trace", task_type="forecasting", model_version="v1", application_version="v1")
    receipts = []
    for phase in ("output", "error", "output", "output"):
        receipts.append(monitor.ingest(key, RuntimeEvent(**context, phase=phase, metrics={"prediction": 10})))
    monitor.ingest(key, RuntimeEvent(**context, phase="outcome", related_event_id=receipts[2]["event_id"], metrics={"actual": 12}))
    with workbench.store.session() as session:
        for row in session.scalars(select(RuntimeObservation)):
            row.received_at = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    path = workbench.store.url.removeprefix("sqlite:///")
    preview = retention(path, 60, "operator")
    assert not preview["applied"] and preview["eligible_observations"] == 2
    assert len(monitor.events(app["id"])["events"]) == 5
    applied = retention(path, 60, "operator", apply=True)
    assert applied["applied"] and len(monitor.events(app["id"])["events"]) == 3
    assert monitor.store.list("runtime_alert", app["id"])
    assert any(row["action"] == "runtime_retention_applied" for row in monitor.store.list("review_event"))
    newer = monitor.ingest(key, RuntimeEvent(**context, phase="output"))
    assert newer["cursor"] > 5
