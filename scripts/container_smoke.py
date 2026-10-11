"""Owned ephemeral CI container checks. Never use this test account in a deployment."""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from governloom.contract import prepare_event
from governloom.hook import RuntimeHook

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phase", choices=["create", "restart"])
args = parser.parse_args()
assert os.getuid() == 10001, "Container must run without root"
endpoint = "http://127.0.0.1:8000"
password = "ephemeral CI account passphrase 73"
state_file = Path("/data/ci-private.json")
if args.phase == "create":
    subprocess.run([sys.executable, "-m", "governloom.cli", "bootstrap-admin", "ci-admin", "--password-stdin"],
        input=password + "\n", text=True, check=True, capture_output=True, timeout=30)
def call(path, body=None, token=None):
    request = Request(endpoint + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    with urlopen(request, timeout=3) as response:
        return json.load(response)
token = call("/api/auth/login", {"username": "ci-admin", "password": password})["token"]
with urlopen(endpoint, timeout=3) as response:
    assert b'id="root"' in response.read(), "Installed image must serve built dashboard"
if args.phase == "create":
    app = call("/api/applications", {"name": "Container evidence", "purpose": "Software boundary test", "owner": "ci-admin", "expected_behavior": "Persist deadline and exact replay"}, token)
    prefix = f"/api/applications/{app['id']}"
    call(prefix + "/monitor-policy", {"name": "Container policy", "actor": "ci-admin", "rationale": "Declared numeric fixture, not actual model quality", "escalate_after_count": 1,
        "rules": [{"id": "residual", "name": "Residual", "detector": "metric_threshold", "phase": "outcome", "metric": "absolute_error", "threshold": 2, "action": "review", "mitigation": "Investigate"}]}, token)
    key = call(prefix + "/ingest-keys", {"name": "consumer", "actor": "ci-admin"}, token)["key"]
    event = prepare_event(trace_id="container-fixture", phase="output", task_type="forecasting", model_version="fixture-v1", application_version="fixture-v1",
        metrics={"prediction": 10}, outcome_due_at=datetime.now(timezone.utc) + timedelta(seconds=.2))
    receipt = RuntimeHook(endpoint, key).emit(**event)
    time.sleep(.3)
    subprocess.run([sys.executable, "-m", "governloom.cli", "monitor-worker", "--once"], check=True, capture_output=True, timeout=30)
    assert call(prefix + "/outcome-coverage", token=token)["counts"]["overdue"] == 1
    descriptor = os.open(state_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump({"application_id": app["id"], "key": key, "event": event, "cursor": receipt["cursor"]}, output)
else:
    state = json.loads(state_file.read_text(encoding="utf-8"))
    prefix = f"/api/applications/{state['application_id']}"
    replay = RuntimeHook(endpoint, state["key"]).emit(**state["event"])
    assert replay["duplicate"] and replay["cursor"] == state["cursor"]
    assert len(call(prefix + "/runtime-incidents", token=token)) == 1
    outcome = RuntimeHook(endpoint, state["key"]).emit(trace_id="container-fixture", phase="outcome", task_type="forecasting", model_version="fixture-v1", application_version="fixture-v1",
        related_event_id=state["event"]["event_id"], metrics={"actual": 10})
    assert outcome["action"] == "allow"
    assert call(prefix + "/outcome-coverage", token=token)["counts"]["resolved"] == 1
print(json.dumps({"phase": args.phase, "status": "passed", "nonroot": True, "dashboard_served": True, "scope": "Named access, deadline persistence and exact replay under container restart; software fixture"}))
