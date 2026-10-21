"""Owned real-model discovery workflows. No prewritten monitoring policy is supplied."""
import argparse
import json
import os
import secrets
import time
from pathlib import Path

from examples.common import ROOT, http
from examples.processes import Processes
from examples.vision.model import DigitModel
from governloom.auth import Operators, UserCreate
from governloom.discovery import DiscoveryImport
from governloom.explorer import collect, enrich, write_bundle
from governloom.discovered_hook import DiscoveredObserver
from governloom.service import Workbench, checksum
from governloom.storage import Store
from governloom.schemas import now


def vision_data():
    model = DigitModel()
    rows = []
    for split, indices in (("calibration", model.calibration), ("held_out", model.held_out)):
        for index in indices:
            result = model.predict(model.images[index])
            rows.append({"sample_id": index, "predicted_label": result["prediction"], "actual_label": int(model.labels[index]),
                "confidence": result["confidence"], "split": split, "model_version": model.version,
                "application_version": "digit-service-v1", "environment": "discovery-natural"})
    return rows, model


def forecast_data(path):
    from examples.forecasting.model import ForecastModel
    model = ForecastModel(path)
    # One fixed rolling algorithm + frozen snapshot is the monitored pipeline version.
    # Individual refit hashes remain in the trace as fitted_version, not pooled silently.
    version = "rolling-pipeline-" + checksum([model.data_hash, (ROOT/"examples/forecasting/model.py").read_text(encoding="utf-8")])[:16]
    rows = []
    for split, dates in (("calibration", model.calibration), ("held_out", model.held_out)):
        for date in dates:
            result = model.predict(date)
            actual = model.rows[date]
            rows.append({"timestamp": date+"-01", "prediction": result["prediction"], "actual": actual["value"] if actual["observed"] else None,
                "model_version": version, "fitted_version": result["model_version"], "application_version": "forecast-pipeline-v1",
                "environment": "discovery-natural", "split": split})
    return rows, model


def run(directory, *, forecast_snapshot=None, rag_capture=None, subscription=False, model="gpt-6.1-sol", replay=None):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT/"data"):
        raise ValueError("Keep owned captures under data/")
    directory.mkdir(parents=True, exist_ok=False)
    if subscription and replay:
        raise ValueError("Choose new semantic capture or frozen replay")
    report = {"schema_version": 1, "status": "started", "created_at":now(), "provider_request_cap": 3 if subscription else 0,
        "provider_requests": 0, "scope": "Owned scripted review, not independent usability or label validation", "applications": {}}
    report["code_files_sha256"] = {name:checksum((ROOT/name).read_text(encoding="utf-8")) for name in
        ("src/governloom/discovery.py","src/governloom/discovery_calibration.py","src/governloom/explorer.py",
         "src/governloom/discovered_hook.py","examples/discovery_testbed.py")}
    sources = {"vision": vision_data()}
    if forecast_snapshot:
        sources["forecasting"] = forecast_data(forecast_snapshot)
    if rag_capture:
        capture = json.loads(Path(rag_capture).read_text(encoding="utf-8"))
        if capture["status"] != "completed":
            raise ValueError("Use a completed real RAG capture")
        answer = capture["natural_answer"]
        source_ids = sorted({item["source_id"] for claim in answer["judgment"]["claims"] for item in claim["evidence"]})
        sources["rag"] = ([{"citations": answer["citations"], "source_ids": source_ids,
            "model_version": "recorded-rag-v05", "application_version": "documentation-v05", "environment": "recorded-replay"}], None)
    password = secrets.token_urlsafe(32)
    database = directory/"collector.db"
    workbench = Workbench(Store(f"sqlite:///{database.as_posix()}"))
    Operators(workbench).create(UserCreate(username="discovery-admin", password=password, role="admin"), "scripted-bootstrap", bootstrap=True)
    workbench.store.engine.dispose()
    environment = {"GOVERNLOOM_DB": f"sqlite:///{database.as_posix()}", "GOVERNLOOM_AUTH_MODE": "operators"}
    session = None
    started = time.perf_counter()
    try:
        if subscription:
            from governloom.subscription import SubscriptionSession
            session = SubscriptionSession(directory/"semantic-capture", model, max_requests=3)
        with Processes(directory) as processes:
            endpoint = processes.start("governloom.api:app", environment, readiness="/api/health")
            token = http(endpoint,"/api/auth/login",{"username":"discovery-admin","password":password})["token"]
            for task, (traces, target) in sources.items():
                app_started = time.perf_counter()
                appdir = directory/task
                appdir.mkdir()
                traces_path = appdir/"traces.jsonl"
                traces_path.write_text("".join(json.dumps(row)+"\n" for row in traces), encoding="utf-8")
                root = ROOT/"examples"/task
                bundle = collect(root, traces_path=traces_path)
                if replay:
                    frozen = DiscoveryImport.model_validate_json((Path(replay)/task/"discovery.json").read_text(encoding="utf-8"))
                    if checksum(frozen.traces) != checksum(bundle.traces):
                        raise ValueError("Frozen replay observations differ from current model outputs")
                    bundle = frozen  # Preserve original source snapshots and model interpretations.
                if session:
                    bundle = enrich(bundle, session)
                write_bundle(bundle, appdir/"discovery.json")
                app = http(endpoint,"/api/applications",{"name":"Discovered "+task,"purpose":"Awaiting discovery", "owner":"Scripted owner", "expected_behavior":"Evaluate discovered evidence"},token)
                prefix = f"/api/applications/{app['id']}"
                draft = http(endpoint,prefix+"/discoveries",bundle.model_dump(),token)
                assert draft["analysis"]["task_type"] == task, draft["analysis"]
                confirmation = http(endpoint,prefix+f"/discoveries/{draft['id']}/confirm",{
                    "actor":"scripted-owner", "expected_checksum":draft["checksum"], "task_type":task,
                    "purpose":(draft.get("semantic") or {}).get("summary",draft["analysis"]["summary"])[:2000],
                    "rationale":"Scripted acceptance of known owned application; no independent human review",
                    "mappings":draft["analysis"]["mappings"], "outcome_meaning_confirmed":task!="rag"},token)
                plan = http(endpoint,prefix+"/discovery-plans",{"actor":"scripted-owner","confirmation_id":confirmation["id"],"alert_fraction":.05 if task=="vision" else .1},token)
                (appdir/"plan.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
                outcome = {"discovery_id":draft["id"],"application_id":app["id"], "inferred_task":draft["analysis"]["task_type"],
                    "source_artifacts":len(bundle.artifacts), "source_findings":len(draft["analysis"]["findings"]),
                    "model_hypotheses":len((draft.get("semantic") or {}).get("hypotheses",[])),
                    "unreviewed_scenarios":len(plan["dataset"]["synthetic_scenarios"]), "owner_corrections":confirmation["corrections"],
                    "plan_status":plan["status"], "dataset_sha256":plan["dataset"]["sha256"],
                    "calibration_cases":plan["dataset"]["calibration_cases"], "held_out_cases":plan["dataset"]["held_out_cases"],
                    "metrics":plan["metrics"], "gaps":plan["gaps"], "no_prewritten_policy":True}
                if plan["status"] == "ready":
                    activation = http(endpoint,prefix+f"/discovery-plans/{plan['id']}/activate",{"actor":"scripted-owner","expected_policy_id":None,
                        "acknowledge_limitations":True,"rationale":"Reviewed owned empirical observation baseline"},token)
                    key = http(endpoint,prefix+"/ingest-keys",{"name":"actual-consumer","actor":"scripted-owner"},token)["key"]
                    observer = DiscoveredObserver(endpoint,key,plan)
                    scope = plan["instrumentation"]["scope"]
                    if task == "vision":
                        sample = min((row for row in traces if row["split"]=="held_out" and row["predicted_label"]!=row["actual_label"]), key=lambda row:row["confidence"])
                        actual_prediction = target.predict(target.sample(sample["sample_id"]))
                        receipt = observer.output({**actual_prediction, **scope},trace_id="discovery-vision")
                    else:
                        sample = next(row for row in traces if row["split"]=="held_out" and abs(row["prediction"]-row["actual"])>plan["metrics"][0]["threshold"])
                        actual_prediction = target.predict(sample["timestamp"][:7])
                        original = observer.output({**actual_prediction, **scope},trace_id="discovery-forecast")
                        receipt = observer.outcome({"actual":sample["actual"], **scope},original)
                    assert receipt["action"] == "flag" and http(endpoint,prefix+"/runtime-incidents",token=token)
                    outcome.update(policy_id=activation["policy_id"],actual_boundary_action=receipt["action"],incident_count=len(http(endpoint,prefix+"/runtime-incidents",token=token)))
                elif task != "rag":
                    raise AssertionError(plan["gaps"])
                outcome["seconds"] = round(time.perf_counter()-app_started,3)
                report["applications"][task] = outcome
            report.update(status="completed",elapsed_seconds=round(time.perf_counter()-started,3))
    except BaseException:
        report["status"] = "failed"
        raise
    finally:
        report["provider_requests"] = session.requests if session else 0
        report["owned_services_stopped"] = True
        (directory/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--forecast-snapshot",type=Path)
    parser.add_argument("--rag-capture",type=Path)
    parser.add_argument("--subscription",action="store_true")
    parser.add_argument("--model",default="gpt-6.1-sol")
    parser.add_argument("--replay",type=Path,help="Reuse frozen discovery bundles; zero provider requests")
    args = parser.parse_args()
    print(json.dumps(run(args.directory,forecast_snapshot=args.forecast_snapshot,rag_capture=args.rag_capture,subscription=args.subscription,model=args.model,replay=args.replay),indent=2))
