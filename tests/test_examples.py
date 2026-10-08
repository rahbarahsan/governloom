"""Optional actual-model checks; no subscription calls or remote data downloads."""

import json
import secrets

import pytest

pytest.importorskip("sklearn", reason="Install examples/requirements.txt for actual model tests")

from examples.common import State, http
from examples.processes import Processes
from examples.vision.model import DigitModel


@pytest.fixture(scope="module")
def digits():
    return DigitModel()


@pytest.fixture
def collector(tmp_path):
    token = secrets.token_urlsafe(32)
    with Processes(tmp_path / "logs") as processes:
        endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": f"sqlite:///{(tmp_path / 'collector.db').as_posix()}",
                                  "GOVERNLOOM_ADMIN_TOKEN": token}, readiness="/api/health")
        def call(path, body=None):
            return http(endpoint, "/api" + path, body, token)
        yield processes, endpoint, call


def connect(call, name, rules):
    app = call("/applications", {"name": name, "purpose": "Actual model test service", "owner": "Testbed operator",
                                "expected_behavior": "Apply serving policy", "model_version": "configured-by-service"})
    prefix = f"/applications/{app['id']}"
    policy = call(prefix + "/monitor-policy", {"name": name + " policy", "actor": "Testbed operator",
                  "rationale": "Integration test boundaries", "expected_events_per_minute": 10000, "rules": rules})
    key = call(prefix + "/ingest-keys", {"name": "service", "actor": "Testbed operator"})["key"]
    return app, policy, key


def test_trained_digit_model_has_disjoint_splits_and_reports_missed_errors(digits):
    assert set(digits.train).isdisjoint(digits.calibration)
    assert set(digits.train).isdisjoint(digits.held_out)
    assert set(digits.calibration).isdisjoint(digits.held_out)
    assert len(digits.train) + len(digits.calibration) + len(digits.held_out) == 1797
    evaluation = digits.evaluate()
    assert evaluation["correct"] / evaluation["cases"] > 0.8
    assert evaluation["errors"] == evaluation["errors_flagged"] + evaluation["confident_errors_missed"]
    assert digits.sample(digits.held_out[0], "occlusion") != digits.sample(digits.held_out[0])


def test_actual_vision_http_hook_withholding_review_and_restart(collector, digits, tmp_path):
    processes, endpoint, call = collector
    app, _, key = connect(call, "Digit service", [{"id": "uncertainty", "name": "Review uncertain digit",
        "detector": "metric_threshold", "task_type": "vision", "phase": "output", "metric": "confidence",
        "comparator": "lt", "threshold": digits.threshold, "action": "block", "mitigation": "Queue manual review"}])
    state_path = tmp_path / "vision.db"
    service = processes.start("examples.vision.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint,
        "GOVERNLOOM_INGEST_KEY": key, "MINI_STATE": str(state_path)}, factory=True)
    row = next(row for row in digits.evaluate()["rows"] if row["review"])
    result = http(service, "/predict", {"sample_id": row["sample_id"], "mode": "enforce"})
    assert result["status"] == "withheld" and result["result"] is None
    assert result["receipt"]["action"] == "block"
    reviews = http(service, "/reviews")
    assert len(reviews) == 1 and reviews[0]["result"]["prediction"] == row["prediction"]
    assert State("vision", state_path).list("review") == reviews
    events = call(f"/applications/{app['id']}/runtime-events")["events"]
    assert len(events) == 2 and "pixels" not in json.dumps(events)
    observer = http(service, "/predict", {"sample_id": row["sample_id"], "mode": "observe"})
    assert observer["result"]["prediction"] == row["prediction"] and observer["status"] == "queued_for_review"
    assert len(call(f"/applications/{app['id']}/runtime-alerts")) == 2
    outcome = http(service, "/outcomes", {"event_id": result["receipt"]["event_id"], "actual_label": row["actual"]})
    assert outcome["correct"] == (row["prediction"] == row["actual"])
    review = http(service, f"/reviews/{reviews[0]['id']}/resolve", {"actor": "Test operator", "rationale": "Checked the public image label",
        "corrected_label": row["actual"], "expected_revision": 1})
    assert review["status"] == "resolved" and review["revision"] == 2
    processes.stop_last()
    restarted = processes.start("examples.vision.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint,
        "GOVERNLOOM_INGEST_KEY": key, "MINI_STATE": str(state_path)}, factory=True)
    assert any(item["id"] == review["id"] and item["status"] == "resolved" for item in http(restarted, "/reviews"))
