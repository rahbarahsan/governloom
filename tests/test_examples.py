"""Optional actual-model checks; no subscription calls or remote data downloads."""

import json
import secrets

import pytest

pytest.importorskip("sklearn", reason="Install examples/requirements.txt for actual model tests")

from examples.common import State, http
from examples.processes import Processes
from examples.vision.model import DigitModel
from examples.forecasting.model import ForecastModel, parse


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
    background_environment = {"ENABLE_BACKGROUND": "1", "ENABLE_DURABLE": "1", "VISION_OUTBOX": str(tmp_path / "outbox.db"), "ENABLE_BROWSER": "1"}
    service = processes.start("examples.vision.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint,
        "GOVERNLOOM_INGEST_KEY": key, "MINI_STATE": str(state_path), **background_environment}, factory=True)
    row = next(row for row in digits.evaluate()["rows"] if row["review"])
    sample = http(service, f"/samples/{row['sample_id']}")
    assert sample["pixels"] == digits.sample(row["sample_id"]) and sample["actual_label"] == row["actual"]
    import urllib.request
    import urllib.error
    request = urllib.request.Request(service + "/baseline", data=json.dumps({"sample_id":row["sample_id"]}).encode(), headers={"Content-Type":"application/json", "Origin":"https://untrusted.example"})
    with pytest.raises(urllib.error.HTTPError) as rejected:
        urllib.request.urlopen(request)
    assert rejected.value.code == 403
    rejected.value.close()
    request = urllib.request.Request(service + "/baseline", data=json.dumps({"sample_id":row["sample_id"]}).encode(), headers={"Content-Type":"application/json", "Origin":service})
    with urllib.request.urlopen(request) as response:
        assert json.load(response)["prediction"] == row["prediction"]
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
    import time
    background = http(service, "/observe-background", {"sample_id": row["sample_id"]})
    assert background["result"]["prediction"] == row["prediction"] and background["delivery"]["action"] == "queued"
    deadline = time.monotonic() + 5
    while http(service, "/delivery")["accepted"] != 1 and time.monotonic() < deadline:
        time.sleep(0.05)
    assert http(service, "/delivery")["accepted"] == 1
    assert http(service, "/delivery")["durable"] is True
    assert call(f"/applications/{app['id']}/runtime-agents")[0]["status"] == "reporting"
    assert len(call(f"/applications/{app['id']}/runtime-actions")) == 2
    processes.stop_last()
    restarted = processes.start("examples.vision.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint,
        "GOVERNLOOM_INGEST_KEY": key, "MINI_STATE": str(state_path), **background_environment}, factory=True)
    assert any(item["id"] == review["id"] and item["status"] == "resolved" for item in http(restarted, "/reviews"))
    assert http(restarted, "/delivery")["accepted"] == 1


@pytest.fixture
def series(tmp_path):
    # Deliberately synthetic CI fixture, not NOAA measurements or accuracy evidence.
    path = tmp_path / "synthetic-monthly.txt"
    rows = ["# Synthetic integration fixture"]
    for year in range(2005, 2025):
        for month in range(1, 13):
            value = 380 + 2 * (year - 2005) + month / 12
            days = -1 if (year, month) == (2022, 2) else 28
            rows.append(f"{year} {month} 0 {value} 0 {days} 0.2 0.1")
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def test_forecast_uses_only_prior_data_and_preserves_missing_ground_truth(series):
    model = ForecastModel(series)
    forecast = model.predict("2021-01")
    assert forecast["training_cutoff"] < forecast["date"]
    old_prediction = forecast["prediction"]
    text = series.read_text().replace("2024 12 0 419.0", "2024 12 0 999.0")
    series.write_text(text)
    assert ForecastModel(series).predict("2021-01")["prediction"] == old_prediction
    assert model.actual("2022-02") is None
    assert model.evaluate()["missing_actuals"] == 1
    assert model.manifest["source_url"] is None
    with pytest.raises(ValueError, match="Duplicate"):
        parse("2005 1 0 400 0 20 0.1 0.1\n2005 1 0 400 0 20 0.1 0.1")


def test_forecast_http_outcome_fault_and_subsequent_fallback(collector, series, tmp_path):
    processes, endpoint, call = collector
    app, _, key = connect(call, "Forecast fixture", [{"id": "error", "name": "Error tolerance", "detector": "metric_threshold",
        "phase": "outcome", "metric": "absolute_error", "threshold": 5, "action": "flag", "mitigation": "Investigate forecast"}])
    service = processes.start("examples.forecasting.app:create_app", {"NOAA_SNAPSHOT": str(series),
        "GOVERNLOOM_ENDPOINT": endpoint, "GOVERNLOOM_INGEST_KEY": key, "MINI_STATE": str(tmp_path / "forecast.db")}, factory=True)
    prediction = http(service, "/predict", {"date": "2021-01", "scenario": "offset_fault"})
    outcome = http(service, "/outcomes", {"event_id": prediction["receipt"]["event_id"]})
    assert outcome["receipt"]["action"] == "flag"
    assert len(http(service, "/investigations")) == 1
    http(service, "/fallback", {"enabled": True, "actor": "Test operator", "rationale": "Explicit fallback test"})
    following = http(service, "/predict", {"date": "2021-02"})
    assert following["result"]["fallback"] and following["result"]["model_version"].startswith("seasonal-naive-")
    missing = http(service, "/predict", {"date": "2022-02"})
    assert http(service, "/outcomes", {"event_id": missing["receipt"]["event_id"]})["status"] == "unavailable"
    assert len(call(f"/applications/{app['id']}/runtime-alerts")) == 1


def test_rag_retrieval_http_monitoring_faults_and_tool_side_effect(collector, tmp_path):
    from fastapi.testclient import TestClient
    from examples.rag.app import create_app
    from examples.rag.model import Retriever
    from governloom.hook import RuntimeHook

    class ExplicitFakeGenerator:
        model = "ci-fake-no-quality-evidence"
        def generate(self, question, sources):
            return {"output": {"answer": "Integration fixture", "behavior": "answer", "citations": [sources[0]["id"]]},
                    "usage": None}

    _, endpoint, call = collector
    app, _, key = connect(call, "RAG fixture", [
        {"id": "citations", "name": "Citation membership", "detector": "citation_integrity", "phase": "output", "action": "block", "mitigation": "Withhold response"},
        {"id": "secrets", "name": "Credential pattern", "detector": "secrets", "phase": "output", "action": "block", "mitigation": "Withhold response"},
        {"id": "tools", "name": "Approved tools", "detector": "tool_allowlist", "phase": "tool", "allowed": ["search"], "action": "block", "mitigation": "Deny write"}])
    retriever = Retriever()
    sources = retriever.retrieve("Does the collector retain raw prompt text?")
    assert sources and all(source["content_hash"] and source["line_start"] <= source["line_end"] for source in sources)
    client = TestClient(create_app(retriever, ExplicitFakeGenerator(), State("rag", tmp_path / "rag.db"),
                                  lambda mode: RuntimeHook(endpoint, key, mode=mode)))
    original = client.post("/answer", json={"question": "Does the collector retain raw prompt text?"}).json()
    assert original["status"] == "returned"
    for mutation in ("invalid_citation", "credential"):
        result = client.post("/faults", json={"event_id": original["receipt"]["event_id"], "mutation": mutation}).json()
        assert result["status"] == "withheld" and result["answer"] is None
    tool = client.post("/tools/write").json()
    assert tool["blocked"] and not tool["side_effect_occurred"]
    assert len(client.get("/reviews").json()) == 2
    events = call(f"/applications/{app['id']}/runtime-events")["events"]
    assert "Integration fixture" not in json.dumps(events) and "sk-test" not in json.dumps(events)


def test_launcher_completes_and_cleans_up_without_inference_or_download(series, tmp_path):
    from types import SimpleNamespace
    from examples.testbed import run
    directory = tmp_path / "testbed"
    args = SimpleNamespace(output=str(directory), noaa_snapshot=str(series), allow_subscription=False,
                           model="never-called", vision_cases=4)
    run(args)
    report = json.loads((directory / "report.json").read_text())
    assert report["status"] == "completed" and report["processes_stopped"]
    assert report["vision"]["natural"]["cases"] == 4
    assert report["forecasting"]["missing_outcomes"] == 1
    assert report["forecasting"]["manifest"]["source_url"] is None
    assert report["rag"]["status"] == "not_run" and report["code_sha256"]
    assert not (directory / "subscription").exists()
    with pytest.raises(FileExistsError):
        run(args)


def test_actual_signal_distance_matches_scipy_and_known_perturbations(digits, series):
    from examples.detector_validation import windows
    reference = digits.classifier.predict_proba(digits.images[digits.calibration]).max(axis=1).tolist()
    natural = [digits.predict(digits.sample(i))["confidence"] for i in digits.held_out[:120]]
    noise = [digits.predict(digits.sample(i, "noise"))["confidence"] for i in digits.held_out[:120]]
    measured = windows(reference, [("natural", False, natural), ("noise", True, noise)], 120)
    assert not measured[0]["triggered"] and measured[1]["triggered"]
    forecast = ForecastModel(series)
    baseline = [abs(forecast.predict(date)["prediction"] - forecast.rows[date]["value"]) for date in forecast.calibration]
    errors = [row["absolute_error"] for row in forecast.evaluate()["rows"][:24]]
    measured = windows(baseline, [("fixture-natural", False, errors), ("fixture-offset", True, [value+5 for value in errors])], 24)
    assert not measured[0]["triggered"] and measured[1]["triggered"]
