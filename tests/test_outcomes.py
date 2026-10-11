from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.outcomes import Outcomes
from governloom.schemas import Application
from governloom.webhooks import DestinationCreate, Webhooks, verify_webhook


def provision(workbench):
    app = workbench.create_application(Application(name="Forecast delivery", purpose="Observe actual outcomes", owner="Test", expected_behavior="Flag gaps without inventing errors"))
    monitor = Monitor(workbench)
    monitor.policy(app["id"], MonitorPolicy(name="Forecast evidence", actor="operator", rationale="An overdue actual is missing evidence", escalate_after_count=1,
        rules=[dict(id="residual", name="Residual", detector="metric_threshold", phase="outcome", metric="absolute_error", threshold=2, action="review", mitigation="Investigate prediction")]))
    key = monitor.issue_key(app["id"], "forecast", "operator")["key"]
    context = dict(trace_id="forecast-1", task_type="forecasting", model_version="forecast-1", application_version="service-1")
    moment = datetime.now(timezone.utc)
    event = RuntimeEvent(**context, phase="output", occurred_at=moment - timedelta(seconds=30), outcome_due_at=moment - timedelta(seconds=10), metrics={"prediction": 12})
    return app, monitor, key, context, event


def test_restart_watchdog_signed_incident_then_late_actual(workbench, tmp_path):
    app, monitor, key, context, event = provision(workbench)
    sent = []
    def receiver(endpoint, body, headers, *rest):
        verify_webhook(destination["secret"], headers, body)
        sent.append(body)
        return 204, None
    endpoint = "http://127.0.0.1:9880/incidents"
    hooks = Webhooks(workbench, allowed=[endpoint], secrets_directory=tmp_path / "secrets", transport=receiver)
    destination = hooks.create(app["id"], DestinationCreate(name="Owned receiver", endpoint=endpoint, actor="operator"))
    first = monitor.ingest(key, event)
    assert first["action"] == "allow" and not first["alert_ids"]
    coverage = Outcomes(monitor).coverage(app["id"])
    assert coverage["counts"] == {"pending": 0, "overdue": 1, "resolved": 0} and coverage["unswept_overdue"] == 1
    with ThreadPoolExecutor(2) as pool:
        flagged = list(pool.map(lambda _: Outcomes(Monitor(workbench)).sweep()["flagged"], range(2)))
    assert sum(flagged) == 1 and len(monitor.alerts(app["id"])) == 1
    assert hooks.dispatch()["delivered"] == 1 and len(sent) == 1
    assert monitor.ingest(key, event)["duplicate"]
    no_actual = monitor.ingest(key, RuntimeEvent(**context, phase="outcome", related_event_id=event.event_id))
    assert no_actual["checks"][0]["status"] == "insufficient_evidence"
    assert Outcomes(monitor).coverage(app["id"])["counts"]["overdue"] == 1
    actual = monitor.ingest(key, RuntimeEvent(**context, phase="outcome", related_event_id=event.event_id, metrics={"actual": 16}))
    assert actual["action"] == "review"
    resolved = Outcomes(monitor).coverage(app["id"])
    assert resolved["counts"] == {"pending": 0, "overdue": 0, "resolved": 1}
    assert resolved["expectations"][0]["late_seconds"] >= 10
    assert Outcomes(monitor).sweep()["flagged"] == 0
    # Eventual evidence resolves delivery coverage, never operator mitigation.
    assert all(row["status"] == "open" for row in monitor.incidents(app["id"]))


def test_on_time_actual_and_scoped_mismatches_do_not_resolve(workbench):
    app, monitor, key, context, event = provision(workbench)
    future = event.model_copy(update={"outcome_due_at": datetime.now(timezone.utc) + timedelta(minutes=1)})
    monitor.ingest(key, future)
    with pytest.raises(ValueError, match="matching"):
        monitor.ingest(key, RuntimeEvent(**{**context, "model_version": "other"}, phase="outcome", related_event_id=future.event_id, metrics={"actual": 12}))
    assert Outcomes(monitor).coverage(app["id"])["counts"]["pending"] == 1
    monitor.ingest(key, RuntimeEvent(**context, phase="outcome", related_event_id=future.event_id, metrics={"actual": 12}))
    assert Outcomes(monitor).coverage(app["id"])["expectations"][0]["late_seconds"] == 0
    assert Outcomes(monitor).sweep(instant=future.outcome_due_at + timedelta(minutes=1))["flagged"] == 0


def test_deadline_validation_and_retention_protect_pending_origin(workbench):
    from governloom.operations import retention
    app, monitor, key, context, event = provision(workbench)
    for changes in (dict(phase="input"), dict(metrics={}), dict(outcome_due_at=datetime.now()), dict(outcome_due_at=event.occurred_at - timedelta(seconds=1))):
        with pytest.raises(ValueError):
            RuntimeEvent.model_validate({**event.model_dump(), **changes})
    monitor.ingest(key, event)
    # Advance the global cursor; the protected origin would otherwise qualify.
    monitor.ingest(key, RuntimeEvent(**context, phase="output", occurred_at=event.occurred_at))
    from governloom.storage import RuntimeObservation
    from sqlalchemy import select
    with workbench.store.session() as session:
        for row in session.scalars(select(RuntimeObservation)):
            row.received_at = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    assert retention(workbench.store.url.removeprefix("sqlite:///"), 30, "operator")["eligible_observations"] == 0


def test_expectation_context_preserves_existing_secret_redaction(workbench):
    import json
    app, monitor, key, context, event = provision(workbench)
    secret = "sk-" + "known-secret-value" * 3
    monitor.ingest(key, event.model_copy(update={"model_version": secret}))
    assert secret not in json.dumps(Outcomes(monitor).coverage(app["id"]))
