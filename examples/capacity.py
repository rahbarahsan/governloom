"""Local HTTP delivery stress; controlled telemetry, not model-quality evidence."""

import argparse
import json
import secrets
import time
from pathlib import Path

from examples.common import digest, http
from examples.processes import Processes
from examples.testbed import event_feed, percentiles, provision
from governloom.delivery import ObservationHook


def run(output):
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    report = {"scope": "Local delivery capacity using controlled custom telemetry; no independent model accuracy cases",
              "targets": {"enqueue_p95_ms": 5, "attempted_steady_rate_per_second": 100, "steady_events": 100,
                          "burst_events": 1000, "burst_queue_bound": 16}, "processes_stopped": False}
    processes = Processes(directory / "logs")
    try:
        admin = secrets.token_urlsafe(32)
        endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": f"sqlite:///{(directory / 'collector.db').as_posix()}",
            "GOVERNLOOM_ADMIN_TOKEN": admin}, readiness="/api/health")
        def call(path, body=None):
            return http(endpoint, "/api" + path, body, admin)
        app, policy, key = provision(call, "Delivery capacity fixture", [{"id": "signal", "name": "Controlled signal",
            "detector": "metric_threshold", "phase": "output", "metric": "test_signal", "threshold": 0,
            "action": "flag", "mitigation": "Transport stress fixture; no model risk inference"}])
        fields = dict(trace_id="capacity-fixture", phase="output", task_type="custom", model_version="controlled-telemetry-v1",
                      application_version="capacity-v1", environment="testbed-fault", metrics={"test_signal": 1})
        hook = ObservationHook(endpoint, key, queue_size=256, timeout_seconds=1, max_age_seconds=30)
        enqueue = []
        started = time.perf_counter()
        try:
            for index in range(100):
                delay = started + index / 100 - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                before = time.perf_counter()
                hook.emit(**fields)
                enqueue.append((time.perf_counter() - before) * 1000)
            elapsed = time.perf_counter() - started
            steady = hook.close(20)
        finally:
            hook.close(1)
        report["steady"] = {"enqueue": percentiles(enqueue), "emission_seconds": elapsed, "delivery": steady}
        assert steady["accepted"] == 100 and steady["pending"] == 0 and not steady["worker_alive"]
        assert report["steady"]["enqueue"]["p95_ms"] < 5
        hook = ObservationHook(endpoint, key, queue_size=16, max_queue_bytes=100_000, timeout_seconds=1)
        peak_count, peak_bytes = 0, 0
        try:
            for _ in range(1000):
                hook.emit(**fields)
                stats = hook.stats
                peak_count, peak_bytes = max(peak_count, stats["pending"]), max(peak_bytes, stats["bytes_pending"])
            burst = hook.close(20)
        finally:
            hook.close(1)
        report["burst"] = {"delivery": burst, "peak_pending": peak_count, "peak_bytes": peak_bytes}
        assert burst["dropped"] > 0 and peak_count <= 16 and peak_bytes <= 100_000
        assert burst["emitted"] == burst["accepted"] + burst["dropped"] + burst["failed"] + burst["expired"] + burst["pending"]
        events = event_feed(call, app)
        assert len(events) == steady["accepted"] + burst["accepted"]
        hook.heartbeat(agent_id="capacity-agent", boot_id="capacity-boot-1", sequence=1,
            counters={name: burst[name] for name in ("emitted", "queued", "accepted", "dropped", "failed", "expired", "pending")})
        report.update(policy_sha256=digest(policy), accepted_collector_events=len(events), agents=call(f"/applications/{app['id']}/runtime-agents"),
            incidents=call(f"/applications/{app['id']}/runtime-incidents"), status="passed")
    except BaseException as exc:
        report.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        processes.close()
        report["processes_stopped"] = not processes.children
        (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    run(parser.parse_args().output)
