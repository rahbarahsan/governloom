"""Owned forecast deadline, signed retry/rotation and database recovery drill."""
import argparse
import json
import os
import secrets
import time
from pathlib import Path

from examples.common import ROOT, http
from examples.forecasting.calibration import evidence
from examples.forecasting.model import ForecastModel
from examples.processes import Processes, free_port
from governloom.auth import Operators, UserCreate
from governloom.monitoring import Monitor, RuntimeEvent
from governloom.recovery import backup_bundle, restore_bundle
from governloom.service import Workbench
from governloom.storage import Store
from governloom.webhooks import Webhooks


def run(directory, snapshot, *, events=600):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT / "data") or not 100 <= events <= 10_000:
        raise ValueError("Use a fresh data/ directory and 100..10000 controlled events")
    directory.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"schema_version": 1, "status": "started", "scope": "Owned real forecast and bounded software drills, not production load/customer validation", "new_provider_requests": 0}
    database = directory / "collector.db"
    db_url = f"sqlite:///{database.as_posix()}"
    workbench = Workbench(Store(db_url))
    password = secrets.token_urlsafe(32)
    Operators(workbench).create(UserCreate(username="drill-admin", password=password, role="admin"), "local drill", bootstrap=True)
    workbench.store.engine.dispose()
    gate = evidence(ForecastModel(snapshot))
    report["forecast"] = gate
    receiver_port = free_port()
    receiver_url = f"http://127.0.0.1:{receiver_port}/incidents"
    secret_directory = directory / "secrets"
    environment = {"GOVERNLOOM_DB": db_url, "GOVERNLOOM_AUTH_MODE": "operators", "GOVERNLOOM_WEBHOOK_ALLOWLIST": receiver_url, "GOVERNLOOM_WEBHOOK_SECRETS": str(secret_directory)}
    try:
        with Processes(directory / "logs") as processes:
            collector = processes.start("governloom.api:app", environment, readiness="/api/health")
            token = http(collector, "/api/auth/login", {"username": "drill-admin", "password": password})["token"]
            def call(path, body=None):
                return http(collector, "/api" + path, body, token)
            app = call("/applications", {"name": "Forecast deadlines", "purpose": "Actual forecast with explicitly delayed feedback", "owner": "drill-admin", "expected_behavior": "Flag missing evidence and investigate actual residuals"})
            prefix = f"/applications/{app['id']}"
            call(prefix + "/monitor-policy", {"name": "Chronological residual evidence", "actor": "scripted", "rationale": "Block threshold frozen on 2019-2020; 2021-2024 untouched", "escalate_after_count": 1, "expected_events_per_minute": 10000,
                "rules": [{"id": "residual", "name": "Residual above block threshold", "detector": "metric_threshold", "phase": "outcome", "metric": "absolute_error", "threshold": gate["selection"]["threshold"], "action": "review", "mitigation": "Inspect actuals and data changes"}]})
            destination = call(prefix + "/webhook-destinations", {"name": "Owned receiver", "endpoint": receiver_url, "actor": "scripted"})
            receiver_key = directory / "receiver-key"
            descriptor = os.open(receiver_key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="ascii") as target:
                target.write(destination["secret"])
            receiver = processes.start("examples.signed_receiver:create_app", {"RECEIVER_DB": str(directory / "receiver.db"), "RECEIVER_SECRET_FILE": str(receiver_key), "RECEIVER_LOSE_FIRST_ACK": "1"}, factory=True, port=receiver_port)
            key = call(prefix + "/ingest-keys", {"name": "forecast", "actor": "scripted"})["key"]
            forecast = processes.start("examples.forecasting.app:create_app", {"NOAA_SNAPSHOT": str(Path(snapshot).resolve()), "MINI_STATE": str(directory / "forecast.db"), "GOVERNLOOM_ENDPOINT": collector, "GOVERNLOOM_INGEST_KEY": key}, factory=True)
            prediction = http(forecast, "/predict", {"date": "2021-01", "outcome_wait_seconds": 1})
            assert prediction["result"]["training_cutoff"] < "2021-01"
            time.sleep(1.1)
            watchdog = processes.command([os.sys.executable, "-m", "governloom.cli", "--db", db_url, "monitor-worker", "--once"], environment, "watchdog")
            assert watchdog.wait(timeout=20) == 0
            overdue = call(prefix + "/outcome-coverage")
            assert overdue["counts"]["overdue"] == 1 and overdue["expectations"][0]["alert_id"]
            # Rotation before retry lets the old receiver accept dual signatures.
            rotation = call(f"/webhook-destinations/{destination['id']}/rotate-secret", {"actor": "scripted", "expected_revision": 1, "overlap_seconds": 60})
            sender = processes.command([os.sys.executable, "-m", "governloom.cli", "--db", db_url, "webhook-worker"], environment)
            deadline = time.monotonic() + 25
            while call(prefix + "/webhook-deliveries")[0]["status"] != "delivered":
                assert time.monotonic() < deadline and sender.poll() is None
                time.sleep(.1)
            delivery = call(prefix + "/webhook-deliveries")[0]
            assert delivery["attempts"] == 2 and len(http(receiver, "/notifications")) == 1
            receiver_key.write_text(rotation["secret"], encoding="ascii")
            actual = http(forecast, "/outcomes", {"event_id": prediction["receipt"]["event_id"]})
            resolved = call(prefix + "/outcome-coverage")
            assert actual["status"] == "observed" and resolved["counts"]["resolved"] == 1
            report["deadline_delivery"] = {"overdue_flagged": True, "sender_attempts": delivery["attempts"], "receiver_notifications": 1,
                "old_receiver_during_overlap": True, "receiver_updated": True, "late_seconds": resolved["expectations"][0]["late_seconds"],
                "incident_still_requires_review": call(prefix + "/runtime-incidents")[0]["status"] == "open"}
            begin = time.perf_counter()
            for offset in range(0, events, 100):
                batch = [RuntimeEvent(trace_id=f"drill-{i}", phase="output", task_type="custom", model_version="controlled-v1", application_version="drill-v1", metrics={"latency_ms": 1}).model_dump(mode="json") for i in range(offset, min(offset + 100, events))]
                result = http(collector, "/api/runtime/events/batch", {"events": batch}, key, timeout=30)
                assert all(item["status"] == 200 for item in result["results"])
            report["bounded_load"] = {"controlled_events": events, "elapsed_seconds": round(time.perf_counter() - begin, 3), "interpretation": "Serial loopback observation batches; not real model predictions or sustained production throughput"}
        # All network actors stopped before offline backup/restore activation.
        record = backup_bundle(database, secret_directory, directory / "backup")
        restored = restore_bundle(directory / "backup", directory / "restored")
        recovered = Store(f"sqlite:///{(directory / 'restored/collector.db').as_posix()}")
        try:
            assert Monitor(Workbench(recovered)).events(app["id"], limit=1)["events"]
            assert len(Webhooks(Workbench(recovered), allowed=[receiver_url], secrets_directory=directory / "restored/secrets").destinations(app["id"])) == 1
        finally:
            recovered.engine.dispose()
        report["recovery"] = {"backup": record, "restore": restored, "network_auto_started": False}
        report["status"] = "completed"
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
    parser.add_argument("--directory", type=Path, required=True); parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--events", type=int, default=600)
    args = parser.parse_args()
    print(json.dumps(run(args.directory, args.snapshot, events=args.events), indent=2))
