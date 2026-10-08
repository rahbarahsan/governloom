import os
import time
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from examples.common import State, hook, service
from examples.vision.model import DigitModel
from governloom.hook import PolicyViolation
from governloom.delivery import HeartbeatReporter, ObservationHook


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    sample_id: int | None = None
    pixels: list[float] | None = Field(default=None, min_length=64, max_length=64)
    corruption: Literal["none", "occlusion", "noise"] = "none"
    mode: Literal["observe", "enforce"] = "observe"

    @model_validator(mode="after")
    def validate_input(self):
        if (self.sample_id is None) == (self.pixels is None):
            raise ValueError("Supply exactly one held-out sample ID or 64 pixels")
        if self.pixels is not None and (self.corruption != "none" or any(not 0 <= value <= 16 for value in self.pixels)):
            raise ValueError("Custom pixels must be in [0,16]; corruption applies only to dataset samples")
        return self


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=2000)
    corrected_label: int = Field(ge=0, le=9)
    expected_revision: int = Field(ge=1)


class Outcome(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    actual_label: int = Field(ge=0, le=9)


def create_app(model=None, state=None, hook_factory=hook):
    model = model or DigitModel()
    state = state or State("vision")
    api = service("Digit recognition")
    background = reporter = None
    if os.environ.get("ENABLE_BACKGROUND") == "1":
        background = ObservationHook(os.environ["GOVERNLOOM_ENDPOINT"], os.environ["GOVERNLOOM_INGEST_KEY"],
                                     timeout_seconds=0.5, max_age_seconds=15)
        reporter = HeartbeatReporter(background, "digit-service-background", interval_seconds=2)

    @asynccontextmanager
    async def lifespan(_):
        try:
            yield
        finally:
            if reporter:
                reporter.close()
            if background:
                background.close()
    api.router.lifespan_context = lifespan

    @api.get("/delivery")
    def delivery():
        if background is None:
            raise ValueError("Set ENABLE_BACKGROUND=1 to enable the observation benchmark")
        return {**background.stats, "heartbeat_sent": reporter.sent, "heartbeat_failures": reporter.failures}

    @api.post("/observe-background")
    def observe_background(body: Prediction):
        if background is None or body.mode != "observe":
            raise ValueError("Background observation requires ENABLE_BACKGROUND=1 and observe mode")
        pixels = body.pixels if body.pixels is not None else model.sample(body.sample_id, body.corruption)
        started = time.perf_counter()
        result = model.predict(pixels)
        queued = background.emit(trace_id=uuid4().hex, phase="output", task_type="vision", model_version=model.version,
            application_version="vision-service-v1", environment="testbed-fault" if body.corruption != "none" else "testbed-natural",
            metrics={"confidence": result["confidence"], "latency_ms": (time.perf_counter() - started) * 1000}, labels=[str(result["prediction"])])
        return {"result": result, "delivery": queued, "limitation": "Queued decisions cannot withhold a returned prediction"}

    @api.get("/manifest")
    def manifest():
        return model.manifest

    @api.get("/samples")
    def samples():
        return {"held_out_ids": model.held_out, "shape": [8, 8], "pixel_range": [0, 16]}

    @api.get("/evaluation")
    def evaluation():
        return model.evaluate()

    @api.get("/reviews")
    def reviews():
        return state.list("review")

    @api.post("/reviews/{identifier}/resolve")
    def resolve(identifier: str, body: Resolution):
        old = state.get(identifier)
        if old.get("status") != "awaiting_review" or old["revision"] != body.expected_revision:
            raise ValueError("Stale or resolved review")
        return state.revise(identifier, old, {**old, **body.model_dump(exclude={"expected_revision"}),
                           "status": "resolved", "revision": old["revision"] + 1})

    @api.post("/outcomes")
    def outcome(body: Outcome):
        original = state.get("prediction-" + body.event_id)
        receipt = hook_factory("observe").emit(phase="outcome", task_type="vision",
            trace_id=original["receipt"]["trace_id"], related_event_id=body.event_id,
            model_version=original["model_version"], application_version="vision-service-v1",
            environment=original["environment"], metrics={"correct": float(body.actual_label == original["result"]["prediction"])})
        return {"correct": body.actual_label == original["result"]["prediction"], "receipt": receipt}

    @api.post("/predict")
    def predict(body: Prediction):
        pixels = body.pixels if body.pixels is not None else model.sample(body.sample_id, body.corruption)
        connection = hook_factory(body.mode)
        captured = {}
        def output_mapper(result):
            captured.update(result)
            return {"metrics": {"confidence": result["confidence"]}, "labels": [str(result["prediction"])]}
        environment = "testbed-fault" if body.corruption != "none" else "testbed-natural"
        function = connection.wrap(model.predict, task_type="vision", model_version=model.version,
            application_version="vision-service-v1", environment=environment,
            input_mapper=lambda _: {"metrics": {"input_corrupted": float(body.corruption != "none")}}, output_mapper=output_mapper)
        blocked = False
        try:
            output = function(pixels)
        except PolicyViolation:
            blocked, output = True, None
        receipt = connection.last_receipt
        needs_review = receipt["action"] in ("review", "block")
        if receipt["phase"] == "output":
            state.put("prediction-" + receipt["event_id"], "prediction", {"result": captured,
                "receipt": receipt, "model_version": model.version, "environment": environment})
        if needs_review:
            state.put(receipt["event_id"], "review", {"id": receipt["event_id"], "sample_id": body.sample_id,
                "scenario": body.corruption, "result": captured, "receipt": receipt, "status": "awaiting_review",
                "revision": 1, "withheld": blocked})
            for alert_id in receipt["alert_ids"]:
                connection.acknowledge_action(alert_id=alert_id, action_type="withheld" if blocked else "review_queued",
                                             evidence_id=receipt["event_id"])
        return {"status": "withheld" if blocked else "queued_for_review" if needs_review else "returned",
                "result": output, "receipt": receipt, "scenario": body.corruption}

    @api.post("/baseline")
    def baseline(body: Prediction):
        """Explicitly unmonitored local benchmark; never a governance path."""
        pixels = body.pixels if body.pixels is not None else model.sample(body.sample_id, body.corruption)
        return model.predict(pixels)

    return api
