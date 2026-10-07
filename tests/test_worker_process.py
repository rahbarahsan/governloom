import os
import subprocess
import sys
import time

from governloom.schemas import RunRequest
from governloom.storage import Job


def test_actual_worker_termination_and_restart(demo):
    wb, _, dataset = demo
    run = wb.queue(RunRequest(dataset_id=dataset["id"]))
    script = """
import time
from governloom.storage import Store
from governloom.worker import Worker
from governloom.demo import LexicalTarget
class SlowTarget(LexicalTarget):
    def execute(self, *args):
        time.sleep(0.15)
        return super().execute(*args)
Worker(Store(), lease_seconds=1, target=SlowTarget()).run_once()
"""
    environment = {**os.environ, "GOVERNLOOM_DB": wb.store.url}
    process = subprocess.Popen([sys.executable, "-c", script], env=environment)
    try:
        deadline = time.monotonic() + 15
        while wb.run(run["id"])["completed"] < 3 and time.monotonic() < deadline:
            assert process.poll() is None, "Worker exited before interruption"
            time.sleep(0.05)
        before = wb.run(run["id"])
        assert before["status"] == "running" and 3 <= before["completed"] < 20
        process.kill()
        process.wait(timeout=5)
        with wb.store.session() as session:
            expiry = session.get(Job, run["id"]).lease_until
        time.sleep(max(0, expiry - time.time()) + 0.05)
        resumed = subprocess.run([sys.executable, "-m", "governloom.cli", "worker", "--once"], env=environment, capture_output=True, text=True, timeout=15)
        assert resumed.returncode == 0, resumed.stderr
        final = wb.run(run["id"])
        assert final["status"] == "completed" and len(final["results"]) == 20
        assert len({r["case_id"] for r in final["results"]}) == 20
        preserved = {r["case_id"]: r for r in final["results"]}
        assert all(preserved[r["case_id"]] == r for r in before["results"])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
