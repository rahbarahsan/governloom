from types import SimpleNamespace
import time

from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.otel import span_event
from governloom.schemas import Application


def test_span_projection_preserves_linkage_omits_prompt_and_reports_missing_evidence(workbench):
    end = time.time_ns()
    span = SimpleNamespace(context=SimpleNamespace(is_valid=True, trace_id=42, span_id=99), start_time=end - 12_000_000, end_time=end,
        attributes={"model.confidence": .2, "gen_ai.prompt": "private prompt", "user.email": "private@example.com"})
    event = span_event(span, task_type="vision", model_version="model-1", application_version="app-1", metric_attributes={"confidence": "model.confidence"})
    assert event["trace_id"] == f"{42:032x}" and event["metrics"] == {"confidence": .2, "latency_ms": 12.0}
    assert "private" not in str(event) and "text" not in {key for key, value in event.items() if value is not None}
    app = workbench.create_application(Application(name="Traced AI", purpose="Selected evidence", owner="Test", expected_behavior="Flag confidence"))
    monitor = Monitor(workbench)
    monitor.policy(app["id"], MonitorPolicy(name="Trace signal", actor="Test", rationale="Explicit signal",
        rules=[dict(id="confidence", name="Confidence", detector="metric_threshold", metric="confidence", comparator="lt", threshold=.8, action="review", mitigation="Inspect")]))
    key = monitor.issue_key(app["id"], "span", "Test")["key"]
    assert monitor.ingest(key, RuntimeEvent(**event))["action"] == "review"
    assert monitor.ingest(key, RuntimeEvent(**event))["duplicate"] is True
    span.context.span_id = 100
    missing = span_event(span, task_type="vision", model_version="model-1", application_version="app-1", metric_attributes={"confidence": "missing"})
    assert monitor.ingest(key, RuntimeEvent(**missing))["checks"][0]["status"] == "insufficient_evidence"
