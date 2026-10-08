import os
import time
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from examples.common import State, hook, service
from examples.forecasting.model import ForecastModel


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str = Field(pattern=r"^202[1-4]-(0[1-9]|1[0-2])$")
    scenario: Literal["natural", "offset_fault"] = "natural"


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)


class Fallback(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    enabled: bool
    actor: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=2000)


def create_app(model=None, state=None, hook_factory=hook):
    model = model or ForecastModel(os.environ["NOAA_SNAPSHOT"])
    state = state or State("forecasting")
    api = service("CO2 forecasting")

    @api.get("/manifest")
    def manifest():
        return model.manifest

    @api.get("/evaluation")
    def evaluation():
        return model.evaluate()

    @api.get("/investigations")
    def investigations():
        return state.list("investigation")

    @api.post("/fallback")
    def configure_fallback(body: Fallback):
        return state.put("fallback", "config", body.model_dump())

    @api.post("/predict")
    def predict(body: Prediction):
        try:
            fallback = state.get("fallback")["enabled"]
        except ValueError:
            fallback = False
        started = time.perf_counter()
        result = model.predict(body.date, fallback)
        if body.scenario == "offset_fault":
            result["prediction"] += 20  # Declared fault, never a natural-model result.
        environment = "testbed-fault" if body.scenario != "natural" else "testbed-natural"
        receipt = hook_factory("observe").emit(trace_id=uuid4().hex, phase="output", task_type="forecasting",
            model_version=result["model_version"], application_version="forecast-service-v1", environment=environment,
            metrics={"prediction": result["prediction"], "latency_ms": (time.perf_counter() - started) * 1000,
                     "horizon_months": 1, "offset_fault": float(body.scenario == "offset_fault")})
        state.put(receipt["event_id"], "prediction", {**result, "receipt": receipt, "environment": environment,
                                                     "scenario": body.scenario})
        return {"result": result, "receipt": receipt, "scenario": body.scenario}

    @api.post("/outcomes")
    def outcome(body: Outcome):
        original = state.get(body.event_id)
        actual = model.actual(original["date"])
        if actual is None:
            return {"status": "unavailable", "reason": "Snapshot outcome is missing or interpolated; no zero substituted"}
        receipt = hook_factory("observe").emit(trace_id=original["receipt"]["trace_id"], phase="outcome", task_type="forecasting",
            model_version=original["model_version"], application_version="forecast-service-v1", environment=original["environment"],
            related_event_id=body.event_id, metrics={"actual": actual["value"]})
        if receipt["action"] != "allow":
            state.put(receipt["event_id"], "investigation", {"date": original["date"], "prediction_event_id": body.event_id,
                "actual": actual["value"], "receipt": receipt, "status": "awaiting_investigation"})
        return {"status": "observed", "actual": actual["value"], "receipt": receipt}

    return api
