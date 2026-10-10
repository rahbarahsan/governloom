import base64
import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from governloom.api import create_app
from governloom.auth import Operators, UserCreate
from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.schemas import Application
from governloom.storage import Entity, Store
from governloom.webhooks import DeliveryChange, DestinationCreate, Webhooks, signing_headers, validate_endpoint, verify_webhook


def setup(workbench, tmp_path, transport=None):
    app = workbench.create_application(Application(name="Connected model", purpose="Runtime checks", owner="Test", expected_behavior="Withhold risk"))
    endpoint = "http://127.0.0.1:9876/incidents"
    kwargs = {"transport": transport} if transport else {}
    hooks = Webhooks(workbench, allowed=[endpoint], secrets_directory=tmp_path / "secrets", **kwargs)
    destination = hooks.create(app["id"], DestinationCreate(name="Owned receiver", endpoint=endpoint, actor="operator"))
    monitor = Monitor(workbench)
    monitor.policy(app["id"], MonitorPolicy(name="Gate", actor="operator", rationale="Risk boundary", escalate_after_count=1,
        rules=[dict(id="confidence", name="Confidence", detector="metric_threshold", phase="output", metric="confidence",
            comparator="lt", threshold=.8, action="block", mitigation="Withhold for review")]))
    key = monitor.issue_key(app["id"], "model", "operator")["key"]
    event = RuntimeEvent(trace_id="model-risk", phase="output", task_type="vision", model_version="model-1", application_version="app-1", metrics={"confidence": .3})
    receipt = monitor.ingest(key, event)
    return app, hooks, destination, monitor, key, event, receipt


def due(hooks, identifier, **updates):
    with hooks.store.session() as session:
        row = session.get(Entity, identifier)
        row.payload = {**row.payload, "next_attempt_at": 0, **updates}


def test_signature_interoperability_replay_tamper_and_endpoint_guards():
    secret = "whsec_" + base64.b64encode(b"x" * 32).decode()
    body = b'{"risk":true}'
    headers = signing_headers(secret, "delivery-1", body, timestamp=1000)
    expected = base64.b64encode(hmac.new(b"x" * 32, b"delivery-1.1000." + body, hashlib.sha256).digest()).decode()
    assert headers["webhook-signature"] == "v1," + expected
    assert verify_webhook(secret, headers, body, instant=1000) == "delivery-1"
    for bad_body, instant in ((body + b" ", 1000), (body, 1301)):
        with pytest.raises(ValueError):
            verify_webhook(secret, headers, bad_body, instant=instant)
    for endpoint in ("http://example.com/incidents", "https://user:password@example.com/path", "https://example.com/path?secret=x", "http://localhost:9876/incidents"):
        with pytest.raises(ValueError):
            validate_endpoint(endpoint, [endpoint])
    with pytest.raises(ValueError, match="ALLOWLIST"):
        validate_endpoint("https://example.com/incidents", [])


def test_durable_exact_body_retry_concurrent_claim_no_secrets_and_terminal_replay(workbench, tmp_path):
    sent = []
    def transport(endpoint, body, headers, timeout, allowed):
        sent.append((body, headers))
        return (503, "120") if len(sent) == 1 else (204, None)
    app, hooks, destination, monitor, key, event, receipt = setup(workbench, tmp_path, transport)
    delivery = hooks.deliveries(app["id"])[0]
    assert monitor.ingest(key, event)["duplicate"] and len(hooks.deliveries(app["id"])) == 1
    assert hooks.dispatch()["pending"] == 1
    waiting = hooks.deliveries(app["id"])[0]
    assert waiting["next_attempt_at"] >= time.time() + 118
    due(hooks, delivery["id"])
    restarted = Webhooks(workbench, allowed=hooks.allowed, secrets_directory=hooks.secrets_directory, transport=transport)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: restarted.dispatch(), range(2)))
    assert sum(row["delivered"] for row in results) == 1 and len(sent) == 2
    assert sent[0][0] == sent[1][0] and sent[0][1]["webhook-id"] == sent[1][1]["webhook-id"]
    verify_webhook(destination["secret"], sent[1][1], sent[1][0])
    public = json.dumps(hooks.destinations(app["id"]) + hooks.deliveries(app["id"]) + hooks.store.list("review_event", app["id"]))
    assert destination["secret"] not in public and "body\"" not in json.dumps(hooks.deliveries(app["id"]))
    assert json.loads(sent[0][0])["data"].keys() == {"application_id", "incident_id", "count", "severity"}
    due(hooks, delivery["id"], status="pending", expires_at=0)
    assert hooks.dispatch()["dead_letter"] == 1
    dead = hooks.deliveries(app["id"])[0]
    with pytest.raises(ValueError, match="Stale"):
        hooks.replay(dead["id"], DeliveryChange(actor="operator", expected_revision=1))
    replay = hooks.replay(dead["id"], DeliveryChange(actor="operator", expected_revision=dead["revision"]))
    assert replay["body_sha256"] == delivery["body_sha256"] and replay["replays"] == 1
    assert hooks.dispatch()["delivered"] == 1


def test_named_destination_roles_scope_and_server_actor(workbench, tmp_path, monkeypatch):
    app, hooks, destination, _, _, _, _ = setup(workbench, tmp_path)
    monkeypatch.setenv("GOVERNLOOM_WEBHOOK_ALLOWLIST", destination["endpoint"])
    monkeypatch.setenv("GOVERNLOOM_WEBHOOK_SECRETS", str(tmp_path / "api-secrets"))
    operators = Operators(workbench)
    password = "a long private integration password"
    operators.create(UserCreate(username="admin", password=password, role="admin"), "bootstrap", bootstrap=True)
    for name, role, apps in (("viewer", "viewer", [app["id"]]), ("reviewer", "reviewer", [app["id"]]), ("operator", "operator", [app["id"]]), ("outsider", "operator", [])):
        if not apps:
            other = workbench.create_application(Application(name="Other", purpose="Scope", owner="Test", expected_behavior="Isolation"))
            apps = [other["id"]]
        operators.create(UserCreate(username=name, password=password, role=role, application_ids=apps), "admin")
    with TestClient(create_app(workbench.store)) as client:
        for name in ("viewer", "reviewer", "operator", "outsider"):
            token = client.post("/api/auth/login", json={"username": name, "password": password}).json()["token"]
            headers = {"Authorization": "Bearer " + token}
            path = f"/api/applications/{app['id']}/webhook-destinations"
            assert client.get(path, headers=headers).status_code == (403 if name == "outsider" else 200)
            response = client.post(path, headers=headers, json={"name": "API sink", "endpoint": destination["endpoint"], "actor": "forged"})
            assert response.status_code == (201 if name == "operator" else 403)
    audits = hooks.store.list("review_event", app["id"])
    assert any(row["action"] == "webhook_destination_created" and row["actor"] == "operator" for row in audits)
    assert not any(row["actor"] == "forged" for row in audits)


def test_real_signed_receiver_lost_ack_and_worker_death_after_acceptance(workbench, tmp_path):
    import os
    import subprocess
    import sys
    from examples.common import http
    from examples.processes import Processes, free_port
    app, original, destination, monitor, key, event, receipt = setup(workbench, tmp_path)
    port = free_port()
    endpoint = f"http://127.0.0.1:{port}/incidents"
    with original.store.session() as session:
        row = session.get(Entity, destination["id"])
        row.payload = {**row.payload, "endpoint": endpoint}
    environment = {"GOVERNLOOM_WEBHOOK_ALLOWLIST": endpoint, "GOVERNLOOM_WEBHOOK_SECRETS": str(original.secrets_directory)}
    with Processes(tmp_path / "logs") as processes:
        receiver = processes.start("examples.signed_receiver:create_app", {"RECEIVER_DB": str(tmp_path / "receiver.db"),
            "RECEIVER_SECRET_FILE": str(original.secrets_directory / destination["id"]), "RECEIVER_LOSE_FIRST_ACK": "1"}, factory=True, port=port)
        code = """import os
from governloom.storage import Store
from governloom.service import Workbench
from governloom.webhooks import Webhooks,send
def die(*args):
    send(*args)
    os._exit(23)
Webhooks(Workbench(Store(os.environ['TEST_DB'])),transport=die).dispatch(timeout=.5)
"""
        child = subprocess.run([sys.executable, "-c", code], env={**os.environ, **environment, "TEST_DB": workbench.store.url}, timeout=20)
        assert child.returncode == 23 and len(http(receiver, "/notifications")) == 1
        delivery = original.deliveries(app["id"])[0]
        assert delivery["status"] == "delivering"
        due(original, delivery["id"], lease_until=0)
        resumed = Webhooks(workbench, allowed=[endpoint], secrets_directory=original.secrets_directory)
        assert resumed.dispatch()["delivered"] == 1
        assert len(http(receiver, "/notifications")) == 1
        assert monitor.incidents(app["id"])[0]["status"] == "open"


def test_dns_rebinding_private_answers_and_redirect_are_rejected(workbench, tmp_path, monkeypatch):
    from governloom.webhooks import resolved_addresses
    from urllib.parse import urlsplit
    monkeypatch.setattr("governloom.webhooks.socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443)), (2, 1, 6, "", ("169.254.169.254", 443))])
    with pytest.raises(ValueError, match="public"):
        resolved_addresses(urlsplit("https://receiver.example/incidents"))
    app, hooks, destination, _, _, _, _ = setup(workbench, tmp_path, lambda *args: (302, None))
    assert hooks.dispatch()["dead_letter"] == 1
    assert hooks.deliveries(app["id"])[0]["http_status"] == 302
