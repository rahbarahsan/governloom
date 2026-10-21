"""Capture the real discovery-to-forecast-incident UI using frozen model analysis."""
import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

from examples.common import ROOT, http
from examples.processes import Processes, free_port
from governloom.auth import Operators, UserCreate
from governloom.discovered_hook import DiscoveredObserver
from governloom.service import Workbench
from governloom.storage import Store


def emit(request):
    from examples.discovery_testbed import forecast_data
    rows, model = forecast_data(request["snapshot"])
    plan = request["plan"]
    selected = next(row for row in rows if row["split"]=="held_out" and abs(row["prediction"]-row["actual"])>plan["metrics"][0]["threshold"])
    prediction = model.predict(selected["timestamp"][:7])
    assert selected["model_version"] == plan["instrumentation"]["scope"]["model_version"]
    observer = DiscoveredObserver(request["endpoint"],request["key"],plan)
    original = observer.output({**selected,**prediction,"model_version":selected["model_version"]},trace_id="discovery-capture")
    result = observer.outcome(selected,original)
    assert result["action"] == "flag"
    return {"action":result["action"],"date":selected["timestamp"],"prediction":prediction["prediction"],"actual":selected["actual"]}


def run(directory, evidence, snapshot):
    directory, evidence, snapshot = map(lambda value:Path(value).resolve(),(directory,evidence,snapshot))
    if not directory.is_relative_to(ROOT/"data"):
        raise ValueError("Keep capture state under data/")
    directory.mkdir(parents=True,exist_ok=False)
    password, bootstrap = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    database = directory/"collector.db"
    workbench = Workbench(Store(f"sqlite:///{database.as_posix()}"))
    Operators(workbench).create(UserCreate(username="capture-admin",password=bootstrap,role="admin"),"scripted-bootstrap",bootstrap=True)
    workbench.store.engine.dispose()
    try:
        with Processes(directory/"logs") as processes:
            port = free_port()
            endpoint = processes.start("governloom.api:app",{"GOVERNLOOM_DB":f"sqlite:///{database.as_posix()}",
                "GOVERNLOOM_AUTH_MODE":"operators","GOVERNLOOM_ALLOWED_ORIGINS":f"http://127.0.0.1:{port}"},port=port,readiness="/api/health")
            admin = http(endpoint,"/api/auth/login",{"username":"capture-admin","password":bootstrap})["token"]
            app = http(endpoint,"/api/applications",{"name":"Discover the NOAA forecaster","purpose":"Awaiting discovery confirmation",
                "owner":"Demo operator","expected_behavior":"Prepare and inspect an empirical observation policy"},admin)
            http(endpoint,"/api/auth/users",{"username":"demo-operator","password":password,"role":"operator","application_ids":[app["id"]]},admin)
            bundle = json.loads((evidence/"forecasting/discovery.json").read_text(encoding="utf-8"))
            config = {"collector":endpoint,"application_id":app["id"],"evidence":str(evidence/"forecasting/discovery.json"),
                "snapshot":str(snapshot),"provenance":{"artifact_hashes":{item["path"]:item["sha256"] for item in bundle["artifacts"]},
                    "semantic_model":bundle["semantic"]["model"],"semantic_prompt_sha256":bundle["semantic"]["prompt_sha256"],
                    "semantic_status":"Frozen real model analysis replay; not new inference", "new_subscription_requests":0,
                    "scripted_operator":"demo-operator","scope":"Owned NOAA snapshot and actual rolling model; scripted owner acceptance"}}
            config_path = directory/"config.json"
            config_path.write_text(json.dumps(config,indent=2),encoding="utf-8")
            completed = subprocess.run(["node",str(ROOT/"web/scripts/capture-discovery.mjs")],cwd=ROOT,env={**os.environ,
                "CAPTURE_CONFIG":str(config_path),"CAPTURE_PASSWORD":password,"CAPTURE_PYTHON":sys.executable},
                capture_output=True,text=True,encoding="utf-8",timeout=180,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            (directory/"browser.log").write_text(completed.stdout+completed.stderr,encoding="utf-8")
            if completed.returncode:
                raise RuntimeError("Browser capture failed; inspect the private browser.log")
        from scripts.encode_demo import encode
        encode(directory/"manifest.json",ROOT/"docs/media/demo.gif")
    finally:
        (directory/"cleanup.json").write_text(json.dumps({"owned_services_stopped":True,"new_subscription_requests":0}),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit",action="store_true")
    parser.add_argument("--directory",type=Path)
    parser.add_argument("--evidence",type=Path)
    parser.add_argument("--snapshot",type=Path)
    args=parser.parse_args()
    if args.emit:
        print(json.dumps(emit(json.loads(sys.stdin.buffer.read().decode("utf-8")))))
    else:
        if not all((args.directory,args.evidence,args.snapshot)):
            parser.error("Capture requires --directory, --evidence and --snapshot")
        run(args.directory,args.evidence,args.snapshot)
