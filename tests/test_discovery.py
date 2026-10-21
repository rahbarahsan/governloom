from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from governloom.api import create_app
from governloom.discovery import Activation, Artifact, CalibrationRequest, Confirmation, Discovery, DiscoveryImport
from governloom.explorer import collect
from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.schemas import Application
from governloom.service import checksum


def evidence():
    origin = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [dict(timestamp=(origin+timedelta(days=index)).isoformat(), prediction=100+index,
        actual=100+index+(index % 5)/10 if index < 30 else 120+index,
        split="calibration" if index < 30 else "held_out", model_version="regression-v1",
        application_version="service-v1", environment="test") for index in range(40)]


def provision(workbench):
    app = workbench.create_application(Application(name="Connected system", purpose="Await discovery", owner="Owner", expected_behavior="Review discovered evidence"))
    service = Discovery(workbench)
    content = "def run(model, values):\n    return model.predict(values)\n"
    body = DiscoveryImport(actor="operator", traces=evidence(), artifacts=[Artifact(path="app.py", content=content, sha256=checksum(content))])
    discovery = service.create(app["id"], body)
    confirmation = service.confirm(app["id"], discovery["id"], Confirmation(actor="owner", expected_checksum=discovery["checksum"],
        task_type="forecasting", purpose="Predict a numeric process", rationale="Confirmed target feedback", mappings=discovery["analysis"]["mappings"], outcome_meaning_confirmed=True))
    return app, service, body, discovery, confirmation


def test_forecast_slice_is_immutable_calibration_only_and_version_scoped(workbench):
    app, service, body, discovery, confirmation = provision(workbench)
    assert discovery["analysis"]["task_type"] == "forecasting"
    assert discovery["analysis"]["findings"][0]["excerpt"].strip() == "return model.predict(values)"
    assert service.create(app["id"], body)["id"] == discovery["id"]
    request = CalibrationRequest(actor="operator", confirmation_id=confirmation["id"])
    plan = service.calibrate(app["id"], request)
    assert plan["status"] == "ready" and plan["dataset"]["calibration_cases"] == 30 and plan["dataset"]["held_out_cases"] == 10
    assert plan["metrics"][0]["threshold"] == pytest.approx(.4)
    assert plan["metrics"][0]["held_out"]["exceedances"] == 10
    assert service.calibrate(app["id"], request)["id"] == plan["id"]
    activate = Activation(actor="operator", expected_policy_id=None, acknowledge_limitations=True, rationale="Inspect flags only")
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: service.activate(app["id"], plan["id"], activate), range(2)))
    assert results[0]["policy_id"] == results[1]["policy_id"]
    assert len(workbench.store.list("monitor_policy", app["id"])) == 1
    monitor = Monitor(workbench)
    key = monitor.issue_key(app["id"], "consumer", "operator")["key"]
    context = dict(trace_id="observed", task_type="forecasting", model_version="regression-v1", application_version="service-v1", environment="test")
    prediction = monitor.ingest(key, RuntimeEvent(**context, phase="output", metrics={"prediction": 100}))
    result = monitor.ingest(key, RuntimeEvent(**context, phase="outcome", related_event_id=prediction["event_id"], metrics={"actual": 110}))
    assert result["action"] == "flag" and len(monitor.incidents(app["id"])) == 1
    other = monitor.ingest(key, RuntimeEvent(**{**context, "model_version": "new-model"}, phase="outcome", metrics={"absolute_error": 100}))
    assert other["checks"][0]["status"] == "insufficient_evidence"
    assert "policy" not in workbench.store.get("discovery", discovery["id"])


def test_corrections_preserve_inference_and_activation_detects_replacement(workbench):
    app, service, _, discovery, confirmation = provision(workbench)
    corrected = service.confirm(app["id"], discovery["id"], Confirmation(actor="owner", expected_checksum=discovery["checksum"],
        task_type="custom", purpose="This numeric process is not a forecasting task", rationale="Correct task inference", mappings={}))
    assert corrected["corrections"]["task_type"]["inferred"] == "forecasting"
    assert service.scoped(app["id"], "discovery", discovery["id"])["analysis"]["task_type"] == "forecasting"
    unavailable = service.calibrate(app["id"], CalibrationRequest(actor="owner", confirmation_id=corrected["id"]))
    assert unavailable["status"] == "needs_evidence"
    with pytest.raises(ValueError, match="ready"):
        service.activate(app["id"], unavailable["id"], Activation(actor="operator", expected_policy_id=None, acknowledge_limitations=True, rationale="Wrong"))
    ready = service.calibrate(app["id"], CalibrationRequest(actor="owner", confirmation_id=confirmation["id"]))
    Monitor(workbench).policy(app["id"], MonitorPolicy(**ready["policy"]))
    with pytest.raises(ValueError, match="changed"):
        service.activate(app["id"], ready["id"], Activation(actor="operator", expected_policy_id=None, acknowledge_limitations=True, rationale="Stale"))


def test_missing_actuals_and_unconfirmed_labels_never_become_zero(workbench):
    app, service, body, _, _ = provision(workbench)
    rows = evidence()
    for row in rows[:15]:
        row["actual"] = None
    discovery = service.create(app["id"], body.model_copy(update={"traces": rows}))
    confirmed = service.confirm(app["id"], discovery["id"], Confirmation(actor="owner", expected_checksum=discovery["checksum"],
        task_type="forecasting", purpose="Numeric target", rationale="Meaning unconfirmed", mappings=discovery["analysis"]["mappings"]))
    plan = service.calibrate(app["id"], CalibrationRequest(actor="operator", confirmation_id=confirmed["id"]))
    assert plan["status"] == "needs_evidence"
    assert any("20 numeric" in gap for gap in plan["gaps"])
    assert plan["dataset"]["cases"][0]["values"]["actual"] is None


@pytest.mark.parametrize("fault", ["chronology", "duplicates", "versions"])
def test_reject_leakage_or_mixed_deployment(workbench, fault):
    app, service, body, _, _ = provision(workbench)
    rows = evidence()
    if fault == "chronology":
        rows[0]["timestamp"], rows[-1]["timestamp"] = rows[-1]["timestamp"], rows[0]["timestamp"]
    elif fault == "duplicates":
        rows[-1] = {**rows[0], "split": "held_out"}
    else:
        rows[-1]["model_version"] = "other-model"
    discovery = service.create(app["id"], body.model_copy(update={"traces": rows}))
    confirmed = service.confirm(app["id"], discovery["id"], Confirmation(actor="owner", expected_checksum=discovery["checksum"],
        task_type="forecasting", purpose="Numeric target", rationale="Reviewed mapping", mappings=discovery["analysis"]["mappings"], outcome_meaning_confirmed=True))
    if fault == "duplicates":
        with pytest.raises(ValueError, match="duplicate"):
            service.calibrate(app["id"], CalibrationRequest(actor="operator", confirmation_id=confirmed["id"]))
    else:
        plan = service.calibrate(app["id"], CalibrationRequest(actor="operator", confirmation_id=confirmed["id"]))
        assert plan["status"] == "needs_evidence"


def test_local_explorer_does_not_execute_source_or_collect_hidden_secrets(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root/"app.py").write_text("raise RuntimeError('MUST NOT RUN')\napi_key = 'private credential'\ndef run(model):\n    return model.predict_proba([1])\n")
    (root/".env").write_text("SECRET=private")
    (root/"credentials.json").write_text('{"password":"private"}')
    (root/"data").mkdir()
    (root/"data"/"user.json").write_text('{"private":true}')
    bundle = collect(root)
    assert len(bundle.artifacts) == 1 and "private credential" not in bundle.artifacts[0].content
    assert "predict_proba" in bundle.artifacts[0].content


def test_semantic_quotes_and_artifact_hashes_are_verified(workbench):
    app, service, body, _, _ = provision(workbench)
    with pytest.raises(ValueError, match="checksum"):
        Artifact(path="app.py", content="changed", sha256="a"*64)
    semantic = {"summary": "May classify", "hypotheses": [{"description": "Inferred", "path": "app.py", "quote": "not in source"}],
                "scenarios": [], "model": "test-adapter", "prompt_sha256": "a"*64}
    with pytest.raises(ValueError, match="quote"):
        service.create(app["id"], body.model_copy(update={"semantic": semantic}))


def test_discovery_api_named_scope_and_actor_binding(workbench, monkeypatch):
    from governloom.auth import Operators, UserCreate
    app, _, body, discovery, _ = provision(workbench)
    operators = Operators(workbench)
    password = "test-only strong password 42"
    operators.create(UserCreate(username="admin", password=password, role="admin"), "bootstrap", bootstrap=True)
    for role in ("viewer", "reviewer", "operator"):
        operators.create(UserCreate(username=role, password=password, role=role, application_ids=[app["id"]]), "admin")
    monkeypatch.setenv("GOVERNLOOM_AUTH_MODE", "operators")
    client = TestClient(create_app(workbench.store))
    for role in ("viewer", "reviewer", "operator"):
        token = client.post("/api/auth/login", json={"username": role, "password": password}).json()["token"]
        headers = {"Authorization": "Bearer " + token}
        assert client.get(f"/api/applications/{app['id']}/discoveries", headers=headers).status_code == 200
        response = client.post(f"/api/applications/{app['id']}/discoveries", json={**body.model_dump(), "actor": "forged"}, headers=headers)
        assert response.status_code == (201 if role == "operator" else 403)
        if role == "operator":
            assert response.json()["actor"] == "operator"
        assert client.get("/api/applications/not-granted/discoveries", headers=headers).status_code == 403
    assert client.get(f"/api/applications/{app['id']}/discoveries").status_code == 401
