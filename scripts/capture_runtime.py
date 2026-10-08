"""Own real local services and record a runtime GIF without new inference calls."""
import argparse
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from examples.common import ROOT, http
from examples.processes import Processes, free_port
from examples.vision.model import DigitModel
from governloom.auth import Operators, UserCreate
from governloom.schemas import now
from governloom.service import Workbench
from governloom.storage import Store


def run(directory, evidence):
    directory, evidence = Path(directory).resolve(), Path(evidence).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    if not (ROOT / "web/dist/index.html").exists():
        raise ValueError("Build the dashboard first")
    report = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
    if report["status"] != "completed" or not report.get("rag"):
        raise ValueError("Use a completed actual-model grounding capture")
    with sqlite3.connect(f"file:{(evidence/'rag.db').as_posix()}?mode=ro", uri=True) as db:
        original = json.loads(db.execute("SELECT payload FROM records WHERE kind='answer' LIMIT 1").fetchone()[0])
    judgment = json.loads((evidence / "natural-judge-capture/request-01/record.json").read_text(encoding="utf-8"))
    if judgment["status"] != "completed":
        raise ValueError("Recorded judgment did not complete")
    digits = DigitModel()
    rows = digits.evaluate()["rows"]
    good = max((row for row in rows if row["prediction"] == row["actual"]), key=lambda row: row["confidence"])
    bad = min((row for row in rows if row["prediction"] != row["actual"]), key=lambda row: row["confidence"])
    assert bad["confidence"] < digits.threshold <= good["confidence"]
    bootstrap_password, password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db_path = directory / "collector.db"
    workbench = Workbench(Store(f"sqlite:///{db_path.as_posix()}"))
    Operators(workbench).create(UserCreate(username="capture-admin", password=bootstrap_password, role="admin"), "scripted capture bootstrap", bootstrap=True)
    workbench.store.engine.dispose()
    config = {"created_at": now(), "vision_good": good["sample_id"], "vision_bad": bad["sample_id"],
              "vision_manifest": digits.manifest, "source": "Actual UCI digit inference over HTTP; recorded real documentation RAG output/judgment replay",
              "demo": "Named scripted operator; live model predictions and local mitigation; RAG replay is labeled, not new inference or independent human validation"}
    config["selection"] = "Illustrative selection of one correct and one naturally wrong low-confidence held-out digit; quality counts come from the full separate benchmark"
    try:
        with Processes(directory / "logs") as processes:
            port = free_port()
            endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": f"sqlite:///{db_path.as_posix()}", "GOVERNLOOM_AUTH_MODE": "operators", "GOVERNLOOM_ALLOWED_ORIGINS": f"http://127.0.0.1:{port}"}, port=port, readiness="/api/health")
            admin_token = http(endpoint, "/api/auth/login", {"username": "capture-admin", "password": bootstrap_password})["token"]
            def call(path, body=None):
                return http(endpoint, "/api" + path, body, admin_token)
            vision = call("/applications", {"name": "Live digit recognition", "purpose": "Actual held-out digit recognition", "owner": "Demo operator", "expected_behavior": "Withhold low-confidence predictions; resolve using the benchmark label"})
            rag = call("/applications", {"name": "Documentation RAG — recorded model evidence", "purpose": "Replay an actual generated answer and its recorded judge evidence", "owner": "Demo operator", "expected_behavior": "Review unsupported claims against frozen repository sources"})
            call("/auth/users", {"username": "demo-operator", "password": password, "role": "operator", "application_ids": [vision["id"], rag["id"]]})
            token = http(endpoint, "/api/auth/login", {"username": "demo-operator", "password": password})["token"]
            call(f"/applications/{vision['id']}/monitor-policy", {"name": "Frozen vision confidence gate", "actor": "capture-admin", "rationale": "20th calibration confidence percentile; actual held-out errors remain visible", "rules": [{"id": "confidence", "name": "Low confidence prediction", "detector": "metric_threshold", "phase": "output", "task_type": "vision", "metric": "confidence", "comparator": "lt", "threshold": digits.threshold, "action": "block", "severity": "high", "mitigation": "Withhold the prediction and resolve its application review using the actual benchmark label."}]})
            vision_key = call(f"/applications/{vision['id']}/ingest-keys", {"name": "digit-service", "actor": "capture-admin"})["key"]
            vision_endpoint = processes.start("examples.vision.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint, "GOVERNLOOM_INGEST_KEY": vision_key, "MINI_STATE": str(directory / "vision.db"), "ENABLE_BROWSER": "1", "ENABLE_BACKGROUND": "1", "ENABLE_DURABLE": "1", "VISION_OUTBOX": str(directory / "vision-outbox.db")}, factory=True)
            http(vision_endpoint, "/observe-background", {"sample_id": good["sample_id"]})
            profile_body = next(item["request"] for item in report["profiles"] if item["request"]["kind"] == "claim_support" and item["request"]["environment"] == "testbed-natural")
            profile_body = {**profile_body, "environment": "recorded-rag-replay"}
            profile = call(f"/applications/{rag['id']}/detector-profiles", profile_body)
            call(f"/detector-profiles/{profile['id']}/approve", {"actor": "capture-admin", "expected_checksum": profile["checksum"], "rationale": "Reviewed frozen engineering controls and known unavailable case; recorded replay only"})
            call(f"/applications/{rag['id']}/monitor-policy", {"name": "Recorded claim support", "actor": "capture-admin", "rationale": "Replay actual evidence with the exact frozen sources; no new judge calls", "rules": [{"id": "grounding", "name": "Unsupported RAG claim", "detector": "claim_support", "phase": "output", "task_type": "rag", "profile_id": profile["id"], "action": "review", "severity": "high", "mitigation": "Inspect the source positions and qualify the claim that all blocks happen before inference."}]})
            rag_key = call(f"/applications/{rag['id']}/ingest-keys", {"name": "recorded-rag-replay", "actor": "capture-admin"})["key"]
            answer = original["output"]["answer"]
            import hashlib
            config.update(collector=endpoint, vision_endpoint=vision_endpoint, vision_id=vision["id"], rag_id=rag["id"],
                rag_event=dict(trace_id="recorded-rag-replay", phase="output", task_type="rag", environment="recorded-rag-replay", model_version=profile["model_version"], application_version=profile["application_version"], text=answer, citations=original["output"]["citations"], source_ids=[s["id"] for s in original["sources"]],
                    grounding=dict(profile_id=profile["id"], corpus_sha256=profile["corpus_sha256"], judge_version=profile["judge_version"], rubric_version=profile["rubric_version"], answer_sha256=hashlib.sha256(answer.encode()).hexdigest(), claims=judgment["output"]["claims"], sources=[{"id":s["id"], "content":s["content"]} for s in original["sources"]])),
                rag_capture={"created_at": report["created_at"], "corpus_sha256": profile["corpus_sha256"], "judge_version": profile["judge_version"]})
            (directory / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
            node = shutil.which("node")
            if not node:
                raise ValueError("Install Node first")
            environment = {**os.environ, "CAPTURE_CONFIG": str(directory / "config.json"), "CAPTURE_PASSWORD": password, "CAPTURE_OPERATOR_TOKEN": token, "CAPTURE_RAG_KEY": rag_key}
            with (directory / "browser.log").open("w", encoding="utf-8") as log:
                subprocess.run([node, str(ROOT / "web/scripts/capture-runtime.mjs")], cwd=ROOT, env=environment, timeout=180, check=True,
                               stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        subprocess.run([sys.executable, str(ROOT / "scripts/encode_demo.py"), str(directory / "manifest.json"), "--output", str(ROOT / "docs/media/demo.gif")], check=True)
    finally:
        (directory / "cleanup.json").write_text(json.dumps({"owned_services_stopped": True, "new_subscription_requests": 0}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    run(args.directory, args.evidence)
