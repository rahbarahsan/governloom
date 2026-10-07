import json

from fastapi.testclient import TestClient

from governloom.api import create_app
from governloom.worker import Worker


def test_api_review_publish_queue_evidence_export_and_restart(workbench):
    client = TestClient(create_app(workbench.store))
    assert client.get("/api/health").json()["provider_available"] is False
    app = client.post("/api/demo").json()
    app_id = app["id"]
    cases = client.get(f"/api/applications/{app_id}/cases").json()
    assert len(cases) == 40 and all(c["review_status"] == "unreviewed" for c in cases)
    assert client.post(f"/api/applications/{app_id}/datasets", json={"actor": "reviewer"}).status_code == 400
    for case in cases:
        response = client.post(f"/api/cases/{case['id']}/review", json={"actor": "reviewer", "expected_revision": 1, "decision": "approved"})
        assert response.status_code == 200, response.text
    dataset = client.post(f"/api/applications/{app_id}/datasets", json={"actor": "reviewer"}).json()
    run = client.post("/api/runs", json={"dataset_id": dataset["id"], "target": "invalid_citation"}).json()
    Worker(workbench.store).run_once()
    results = client.get(f"/api/runs/{run['id']}").json()
    assert results["status"] == "completed" and results["summary"]["citation_consistency"]["failed"] > 0
    assert results["results"][0]["trace"] and results["snapshot"]["dataset"]["sources"]
    exported = client.get(f"/api/export/case?application_id={app_id}")
    assert len(exported.text.splitlines()) == 40
    assert json.loads(exported.text.splitlines()[0])["schema_version"] == 1
    restarted = TestClient(create_app(workbench.store))
    assert restarted.get(f"/api/runs/{run['id']}").json()["results"] == results["results"]
    assert client.post("/api/demo").json()["id"] == app_id
    assert len(client.get(f"/api/applications/{app_id}/cases").json()) == 40


def test_api_application_import_validation_and_local_origin(workbench):
    client = TestClient(create_app(workbench.store))
    response = client.post("/api/applications", json={"name": "My app", "purpose": "Answer", "owner": "me", "expected_behavior": "Cite sources"})
    assert response.status_code == 201
    app = response.json()
    source = client.post(f"/api/applications/{app['id']}/sources", json={"document_id": "one", "version": "1", "filename": "one.txt", "content": "Café"})
    assert source.status_code == 201 and source.json()["content"] == "Café"
    assert client.post("/api/applications", json={}, headers={"origin": "https://other.example"}).status_code == 403
    assert client.post("/api/runs", json={"dataset_id": "missing", "target": "clean"}).status_code == 400
    assert client.post("/api/runs", json={"dataset_id": "missing", "paid_provider": True}).status_code == 422
