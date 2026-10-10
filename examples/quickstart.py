"""Actual-model first incident with an owned signed receiver and named console."""
import argparse
import hashlib
import json
import os
import secrets
import statistics
import subprocess
import sys
import time
from pathlib import Path

from examples.common import ROOT, http
from examples.processes import Processes, free_port
from examples.vision.model import DigitModel
from examples.vision.calibration import gate_evidence
from governloom.auth import Operators, UserCreate
from governloom.service import Workbench
from governloom.storage import Store
from governloom import __version__


def private_json(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as target:
        json.dump(value, target, indent=2)


def run(directory, *, check=False, headless=False):
    started = time.perf_counter()
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT / "data") or directory == ROOT / "data":
        raise ValueError("Choose a fresh directory beneath ignored data/")
    if not headless and not (ROOT / "web/dist/index.html").exists():
        raise ValueError("Build the dashboard or use scripts/quickstart.py")
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "status": "started", "source": "Actual frozen UCI digits, real collector/application/receiver HTTP",
        "label_provenance": "Public benchmark labels; scripted operator actions", "new_provider_requests": 0}
    code_files = sorted([*ROOT.glob("src/governloom/*.py"), *ROOT.glob("examples/**/*.py"), ROOT / "scripts/quickstart.py"])
    snapshot = hashlib.sha256()
    for file in code_files:
        snapshot.update(file.relative_to(ROOT).as_posix().encode() + b"\0" + file.read_bytes())
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5)
    report["provenance"] = {"package_version": __version__, "git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
        "python_source_snapshot_sha256": snapshot.hexdigest(), "scope": "Working-tree Python source snapshot; Git revision alone may precede local changes"}
    password = secrets.token_urlsafe(32)
    db_url = f"sqlite:///{(directory / 'collector.db').as_posix()}"
    workbench = Workbench(Store(db_url))
    Operators(workbench).create(UserCreate(username="quickstart-admin", password=password, role="admin"), "local quickstart bootstrap", bootstrap=True)
    workbench.store.engine.dispose()
    digits = DigitModel()
    quality = digits.evaluate()
    gate = gate_evidence(digits)
    rows = quality["rows"]
    good = max((row for row in rows if row["prediction"] == row["actual"]), key=lambda row: row["confidence"])
    bad = min((row for row in rows if row["prediction"] != row["actual"]), key=lambda row: row["confidence"])
    receiver_port = free_port()
    receiver_url = f"http://127.0.0.1:{receiver_port}/incidents"
    secret_directory = directory / "webhook-secrets"
    environment = {"GOVERNLOOM_DB": db_url, "GOVERNLOOM_AUTH_MODE": "operators",
        "GOVERNLOOM_WEBHOOK_ALLOWLIST": receiver_url, "GOVERNLOOM_WEBHOOK_SECRETS": str(secret_directory)}
    try:
        with Processes(directory / "logs") as processes:
            endpoint = processes.start("governloom.api:app", environment, readiness="/api/health")
            token = http(endpoint, "/api/auth/login", {"username": "quickstart-admin", "password": password})["token"]
            def call(path, body=None):
                return http(endpoint, "/api" + path, body, token)
            app = call("/applications", {"name": "Quickstart: real digit recognition", "purpose": "Withhold uncertain real predictions and investigate incidents", "owner": "quickstart-admin", "expected_behavior": "Record a review and linked benchmark outcome"})
            prefix = f"/applications/{app['id']}"
            destination = call(prefix + "/webhook-destinations", {"name": "Owned signed receiver", "endpoint": receiver_url, "actor": "scripted"})
            receiver = processes.start("examples.signed_receiver:create_app", {"RECEIVER_DB": str(directory / "receiver.db"),
                "RECEIVER_SECRET_FILE": str(secret_directory / destination["id"]), "RECEIVER_LOSE_FIRST_ACK": "1"}, factory=True, port=receiver_port)
            policy = call(prefix + "/monitor-policy", {"name": "Frozen confidence review gate", "actor": "scripted", "rationale": "Threshold selected using calibration only; benchmark misses remain published",
                "escalate_after_count": 1, "escalation_cooldown_seconds": 1, "expected_events_per_minute": 10000,
                "rules": [{"id": "confidence", "name": "Low confidence digit", "detector": "metric_threshold", "phase": "output", "task_type": "vision",
                    "metric": "confidence", "comparator": "lt", "threshold": gate["selection"]["threshold"], "action": "block", "severity": "high", "mitigation": "Withhold, inspect the image and record the corrected label."}]})
            key = call(prefix + "/ingest-keys", {"name": "digit-service", "actor": "scripted"})["key"]
            vision = processes.start("examples.vision.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint, "GOVERNLOOM_INGEST_KEY": key,
                "MINI_STATE": str(directory / "vision.db"), "ENABLE_BROWSER": "1", "ENABLE_BACKGROUND": "1", "ENABLE_DURABLE": "1", "VISION_OUTBOX": str(directory / "vision-outbox.db")}, factory=True)
            private_json(directory / "credentials.json", {"console": endpoint, "username": "quickstart-admin", "password": password,
                "application_id": app["id"], "ingest_key": key, "vision": vision, "scope": "Private generated local quickstart credentials; never commit or share"})
            returned = http(vision, "/predict", {"sample_id": good["sample_id"], "mode": "enforce"})
            assert returned["status"] == "returned"
            withheld = http(vision, "/predict", {"sample_id": bad["sample_id"], "mode": "enforce"})
            assert withheld["status"] == "withheld" and withheld["result"] is None
            report["first_incident_seconds"] = round(time.perf_counter() - started, 3)
            worker = processes.command([sys.executable, "-m", "governloom.cli", "--db", db_url, "webhook-worker"], environment)
            deadline = time.monotonic() + 25
            while True:
                deliveries = call(prefix + "/webhook-deliveries")
                if deliveries and deliveries[0]["status"] == "delivered":
                    break
                if worker.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Signed delivery failed; inspect worker log")
                time.sleep(.1)
            notifications = http(receiver, "/notifications")
            assert len(notifications) == 1 and deliveries[0]["attempts"] == 2
            report["notification"] = {"receiver_notifications": 1, "sender_attempts": 2, "lost_first_receipt": True, "same_id_deduplication": True,
                "body_sha256": deliveries[0]["body_sha256"], "seconds_from_start": round(time.perf_counter() - started, 3)}
            incident = call(prefix + "/runtime-incidents")[0]
            incident = call(f"/runtime-incidents/{incident['id']}/review", {"actor": "scripted", "owner": "quickstart-admin", "status": "acknowledged", "rationale": "Inspecting actual withheld digit", "expected_revision": incident["revision"]})
            review = http(vision, "/reviews")[0]
            resolved = http(vision, f"/reviews/{review['id']}/resolve", {"actor": "scripted benchmark operator", "rationale": "Checked original public benchmark label", "corrected_label": bad["actual"], "expected_revision": review["revision"]})
            assert resolved["status"] == "resolved"
            outcome = http(vision, "/outcomes", {"event_id": review["id"], "actual_label": bad["actual"]})
            action = call(prefix + "/runtime-actions")[0]
            response_hash = hashlib.sha256(json.dumps(withheld, sort_keys=True).encode()).hexdigest()
            action = call(f"/runtime-actions/{action['id']}/verify", {"actor": "scripted", "criterion": "response_withheld", "evidence_sha256": response_hash, "rationale": "Script inspected HTTP status withheld and result null; operator attestation"})
            incident = call(f"/runtime-incidents/{incident['id']}/review", {"actor": "scripted", "owner": "quickstart-admin", "status": "mitigated", "rationale": "Application review resolved against public label; linked outcome and response inspection recorded", "expected_revision": incident["revision"]})
            http(vision, "/observe-background", {"sample_id": good["sample_id"]})
            report.update(model_manifest=digits.manifest, model_quality={k: v for k, v in quality.items() if k != "rows"}, policy_gate=gate,
                selected_samples={"correct": good["sample_id"], "natural_error": bad["sample_id"], "selection": "Illustrative; quality report uses all 360 held-out cases"},
                mitigation={"incident_status": incident["status"], "application_review": resolved["status"], "linked_outcome_action": outcome["receipt"]["action"],
                    "action_status": action["status"], "evidence_sha256": response_hash, "limitation": "Scripted application evidence and operator attestation; not independent verification"})
            print(f"Console: {endpoint}\nActual digit service: {vision}\nPrivate sign-in and SDK connection: {directory / 'credentials.json'}", flush=True)
            print("Real risk withheld; signed receiver accepted once after two attempts; application mitigation recorded.", flush=True)
            if check:
                baseline, monitored = [], []
                controls = [row for row in rows if row["confidence"] >= gate["selection"]["threshold"]][:32]
                for row in controls:
                    begin = time.perf_counter(); http(vision, "/baseline", {"sample_id": row["sample_id"]}); baseline.append((time.perf_counter() - begin) * 1000)
                    begin = time.perf_counter(); http(vision, "/predict", {"sample_id": row["sample_id"], "mode": "enforce"}); monitored.append((time.perf_counter() - begin) * 1000)
                report["overhead"] = {"samples": len(controls), "unmonitored_median_ms": round(statistics.median(baseline), 3),
                    "monitored_median_ms": round(statistics.median(monitored), 3), "paired_overhead_median_ms": round(statistics.median(b - a for a, b in zip(baseline, monitored)), 3),
                    "monitored_p95_ms": round(sorted(monitored)[int(.95 * (len(monitored) - 1))], 3), "scope": "Serial loopback HTTP, real digit model, 32 confidence-clear controls; not a production throughput estimate"}
                report["status"] = "completed"
            else:
                report["status"] = "interactive"
                (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print("Keep this terminal open. Press Ctrl+C to stop every owned service.", flush=True)
                try:
                    while True:
                        if os.environ.get("GOVERNLOOM_QUICKSTART_STOP_FILE") and Path(os.environ["GOVERNLOOM_QUICKSTART_STOP_FILE"]).exists():
                            report["status"] = "stopped"
                            break
                        if worker.poll() is not None:
                            raise RuntimeError("Webhook worker exited")
                        time.sleep(.5)
                except KeyboardInterrupt:
                    report["status"] = "stopped"
    except BaseException:
        report["status"] = "failed"
        raise
    finally:
        report["owned_services_stopped"] = True
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data") / ("quickstart-" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)))
    parser.add_argument("--check", action="store_true", help="Run the entire workflow, measure HTTP overhead, stop and exit")
    parser.add_argument("--headless", action="store_true", help="API-only integration check without a dashboard build")
    options = parser.parse_args()
    run(options.directory, check=options.check, headless=options.headless)
