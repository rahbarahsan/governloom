import time

from fastapi.testclient import TestClient
import pytest

from governloom.api import create_app
from governloom.auth import Operators, UserCreate
from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.schemas import Application
from governloom.storage import Entity

PASSWORD = "test-only long passphrase 42"


def setup(workbench, monkeypatch):
    monkeypatch.setenv("GOVERNLOOM_AUTH_MODE", "operators")
    monkeypatch.setenv("GOVERNLOOM_ADMIN_TOKEN", "x" * 32)
    auth = Operators(workbench)
    admin = auth.create(UserCreate(username="admin", password=PASSWORD, role="admin"), "test", bootstrap=True)
    apps = [workbench.create_application(Application(name=f"App {i}", purpose="Test", owner="Test", expected_behavior="Scope")) for i in range(2)]
    users = {role: auth.create(UserCreate(username=role, password=PASSWORD, role=role, application_ids=[apps[0]["id"]]), "admin") for role in ("viewer", "reviewer", "operator")}
    client = TestClient(create_app(workbench.store))
    headers = {}
    for role in ("admin", "viewer", "reviewer", "operator"):
        response = client.post("/api/auth/login", json={"username": role, "password": PASSWORD})
        assert response.status_code == 200
        headers[role] = {"Authorization": "Bearer " + response.json()["token"]}
    return auth, client, apps, users, headers, admin


def test_server_role_scope_and_authenticated_actor(workbench, monkeypatch):
    auth, client, apps, users, headers, admin = setup(workbench, monkeypatch)
    app = apps[0]
    prefix = f"/api/applications/{app['id']}"
    policy = {"name": "Errors", "actor": "forged-admin", "rationale": "Test", "rules": [{"id": "error", "name": "Error", "detector": "target_error", "mitigation": "Investigate"}]}
    assert client.get("/api/applications").status_code == 401
    assert client.get("/api/applications", headers={"Authorization": "Bearer " + "x" * 32}).status_code == 401
    assert client.get("/api/applications", headers=headers["viewer"]).json() == [app]
    assert client.get(f"/api/applications/{apps[1]['id']}/sources", headers=headers["viewer"]).status_code == 403
    assert client.post(prefix + "/monitor-policy", json=policy, headers=headers["viewer"]).status_code == 403
    assert client.post(prefix + "/monitor-policy", json=policy, headers=headers["reviewer"]).status_code == 403
    response = client.post(prefix + "/monitor-policy", json=policy, headers=headers["operator"])
    assert response.status_code == 201, response.text
    assert response.json()["actor"] == "operator"
    assert client.get("/api/monitor-policies/" + response.json()["id"], headers=headers["viewer"]).status_code == 200
    monitor = Monitor(workbench)
    key = monitor.issue_key(app["id"], "test", "setup")["key"]
    receipt = client.post("/api/runtime/events", json=RuntimeEvent(trace_id="auth-test", phase="error", error_type="TestFailure", task_type="vision", model_version="v1", application_version="v1").model_dump(mode="json"), headers={"Authorization": "Bearer " + key}).json()
    alert = monitor.alerts(app["id"])[0]
    review = {"actor": "forged-admin", "owner": "reviewer", "status": "acknowledged", "rationale": "Investigating", "expected_revision": 1}
    assert client.post(f"/api/runtime-alerts/{alert['id']}/review", json=review, headers=headers["viewer"]).status_code == 403
    assert client.post(f"/api/runtime-alerts/{alert['id']}/review", json=review, headers=headers["reviewer"]).status_code == 200
    audits = workbench.store.list("review_event", app["id"])
    assert any(row["actor"] == "reviewer" and row["action"] == "runtime_alert_review" for row in audits)
    other = apps[1]
    other_policy = monitor.policy(other["id"], MonitorPolicy(**policy))
    assert client.get("/api/monitor-policies/" + other_policy["id"], headers=headers["operator"]).status_code == 403
    assert client.get("/api/export/review_event?application_id=" + other["id"], headers=headers["viewer"]).status_code == 403
    assert client.get("/api/auth/users", headers=headers["operator"]).status_code == 403
    assert client.post("/api/demo", headers=headers["operator"]).status_code == 403
    assert client.get("/api/applications", headers={"Authorization": "Bearer " + key}).status_code == 401
    assert receipt["alert_ids"]
    # The mode persists in configuration and identities/sessions survive API reconstruction.
    restarted = TestClient(create_app(workbench.store))
    assert restarted.get("/api/auth/me", headers=headers["reviewer"]).json()["username"] == "reviewer"
    stored = str(workbench.store.list("operator_user") + workbench.store.list("operator_session") + workbench.store.list("review_event"))
    assert PASSWORD not in stored and headers["admin"]["Authorization"][7:] not in stored
    with pytest.raises(ValueError, match="Bootstrap"):
        auth.create(UserCreate(username="second", password=PASSWORD, role="admin"), "test", bootstrap=True)


def test_logout_revocation_expiry_password_rate_limit_and_validation(workbench, monkeypatch):
    auth, client, apps, users, headers, admin = setup(workbench, monkeypatch)
    bad = client.post("/api/auth/login", json={"username": "admin", "password": "private" * 300})
    assert bad.status_code == 422 and "privateprivate" not in bad.text
    assert client.post("/api/auth/login", json={"username": "unknown", "password": PASSWORD}).json()["detail"] == "Invalid username or password"
    assert client.post("/api/auth/logout", headers=headers["viewer"]).status_code == 200
    assert client.get("/api/auth/me", headers=headers["viewer"]).status_code == 401
    assert client.post(f"/api/auth/users/{users['reviewer']['id']}/revoke", headers=headers["admin"]).status_code == 200
    assert client.get("/api/auth/me", headers=headers["reviewer"]).status_code == 401
    assert client.post(f"/api/auth/users/{admin['id']}/revoke", headers=headers["admin"]).status_code == 400
    token = headers["operator"]["Authorization"][7:]
    session_id = token.split(".")[0][3:]
    with workbench.store.session() as session:
        row = session.get(Entity, session_id)
        row.payload = {**row.payload, "expires": time.time() - 1}
    assert client.get("/api/auth/me", headers=headers["operator"]).status_code == 401
    assert client.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": PASSWORD + "new"}, headers=headers["admin"]).status_code == 200
    assert client.get("/api/auth/me", headers=headers["admin"]).status_code == 401
    for _ in range(6):
        client.post("/api/auth/login", json={"username": "unknown", "password": PASSWORD})
    assert client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD + "new"}).status_code == 403
