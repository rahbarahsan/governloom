"""Apply a reviewed discovery plan's field mappings at an existing application boundary."""
from uuid import uuid4

from .discovery import flatten
from .hook import RuntimeHook
from .service import checksum
from .discovery_calibration import dataset_digest


class DiscoveredObserver:
    def __init__(self, endpoint, key, plan, *, on_unavailable="raise"):
        if plan.get("status") != "ready" or not plan.get("policy"):
            raise ValueError("Use a ready, reviewed discovery plan")
        dataset = dict(plan["dataset"])
        expected = dataset.pop("sha256")
        digest = dataset_digest(dataset) if dataset.get("checksum_method")=="numeric-normalized-json-v1" else checksum(dataset)
        if digest != expected:
            raise ValueError("Frozen evaluation dataset checksum differs")
        if any(rule["action"] != "flag" for rule in plan["policy"]["rules"]):
            raise ValueError("DiscoveredObserver supports observation flags only")
        self.mapping = plan["instrumentation"]["fields"]
        self.scope = plan["instrumentation"]["scope"]
        self.task = plan["instrumentation"]["task_type"]
        self.hook = RuntimeHook(endpoint, key, mode="observe", on_unavailable=on_unavailable)

    def output(self, observation, *, trace_id=None, event_id=None, outcome_due_at=None):
        values = self._values(observation)
        metrics = {name: values[name] for name in ("prediction", "confidence", "latency_ms") if name in values and values[name] is not None}
        fields = {name: values[name] for name in ("citations", "source_ids") if name in values and values[name] is not None}
        identity = {"event_id": event_id} if event_id is not None else {}
        return self.hook.emit(trace_id=trace_id or uuid4().hex, **identity, phase="output", task_type=self.task,
            **self._scope(values), metrics=metrics, outcome_due_at=outcome_due_at, **fields)

    def outcome(self, observation, prediction_receipt, *, event_id=None):
        if self.task != "forecasting":
            raise ValueError("Numeric linked actuals apply to forecasting plans")
        values = self._values(observation)
        if values.get("actual") is None:
            raise ValueError("Mapped observed actual is missing; do not substitute zero")
        identity = {"event_id": event_id} if event_id is not None else {}
        return self.hook.emit(trace_id=prediction_receipt["trace_id"], **identity, related_event_id=prediction_receipt["event_id"],
            phase="outcome", task_type=self.task, **self._scope(values), metrics={"actual": values["actual"]})

    def _values(self, observation):
        flat = flatten(observation)
        return {role: flat.get(path) for role, path in self.mapping.items()}

    def _scope(self, values):
        # Require live version fields: never stamp the old calibration version on a new model.
        scope = {role: values.get(role) for role in ("model_version", "application_version", "environment")}
        for role in ("model_version", "application_version"):
            if not isinstance(scope[role], str) or not scope[role].strip():
                raise ValueError("Mapped live model/application versions are required")
        if scope["environment"] is None:
            scope["environment"] = "production"
        return scope
