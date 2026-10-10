"""Select numeric evidence from completed Python OpenTelemetry ReadableSpan objects."""
from datetime import datetime, timezone

from .contract import prepare_event


def span_event(span, *, task_type, model_version, application_version, metric_attributes=None, environment="production", phase="output"):
    context = span.context
    start, end = span.start_time, span.end_time
    if (not context or not context.is_valid or not isinstance(start, int) or not isinstance(end, int) or end < start):
        raise ValueError("Use a completed span with valid context and nanosecond timestamps")
    metrics = {name: span.attributes[attribute] for name, attribute in (metric_attributes or {}).items()
               if attribute in (span.attributes or {})}
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in metrics.values()):
        raise ValueError("Explicitly mapped attributes must be numeric")
    metrics["latency_ms"] = (end - start) / 1_000_000
    trace_id, span_id = f"{context.trace_id:032x}", f"{context.span_id:016x}"
    return prepare_event(event_id=f"otel:{trace_id}:{span_id}:{phase}", trace_id=trace_id, phase=phase,
        task_type=task_type, model_version=model_version, application_version=application_version, environment=environment,
        occurred_at=datetime.fromtimestamp(end / 1_000_000_000, timezone.utc), metrics=metrics)
