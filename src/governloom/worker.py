import signal
import time

from sqlalchemy import func, or_, select, update

from .demo import LexicalTarget
from .metrics import evaluate
from .schemas import now, uid
from .storage import Job, Result, Store


class Worker:
    def __init__(self, store: Store, lease_seconds=30, target=None):
        self.store = store
        self.owner = uid()
        self.lease_seconds = lease_seconds
        self.target = target or LexicalTarget()
        self.stopping = False

    def claim(self):
        timestamp = time.time()
        eligible = or_(Job.status == "queued", (Job.status == "running") & (Job.lease_until < timestamp))
        with self.store.session() as session:
            job_id = session.scalar(select(Job.id).where(eligible).order_by(Job.created_at).limit(1))
            if not job_id:
                return None
            claimed = session.execute(update(Job).where(Job.id == job_id, eligible).values(
                status="running", owner=self.owner, lease_until=timestamp + self.lease_seconds, updated_at=now()))
            return job_id if claimed.rowcount == 1 else None

    def run_once(self, max_cases=None):
        run_id = self.claim()
        if not run_id:
            return False
        with self.store.session() as session:
            snapshot = session.get(Job, run_id).payload
        processed = 0
        try:
            for case in snapshot["cases"]:
                if self.stopping or (max_cases is not None and processed >= max_cases):
                    self.release(run_id)
                    return True
                with self.store.session() as session:
                    job = session.get(Job, run_id)
                    if job.owner != self.owner or job.lease_until < time.time():
                        return True
                    if job.cancel_requested:
                        job.status, job.updated_at = "cancelled", now()
                        job.owner, job.lease_until = None, 0
                        return True
                    exists = session.scalar(select(Result.id).where(Result.run_id == run_id, Result.case_id == case["id"]))
                    if exists:
                        continue
                    job.lease_until = time.time() + self.lease_seconds
                started = now()
                if snapshot["traces"] is not None:
                    trace = next((t for t in snapshot["traces"] if t["case_id"] == case["id"]), None)
                else:
                    trace = self.target.execute(case, snapshot["dataset"]["sources"], snapshot["application"], snapshot["request"]["target"])
                result = {"schema_version": 1, "id": uid(), "run_id": run_id, "case_id": case["id"],
                          "case_revision": case["revision"], "dataset_checksum": snapshot["dataset"]["checksum"],
                          "application_version": snapshot["application"]["application_version"],
                          "model_version": snapshot["application"]["model_version"],
                          "prompt_version": snapshot["application"]["prompt_version"],
                          "target_version": snapshot["target_version"], "trace": trace,
                          "metrics": evaluate(case, trace, snapshot["dataset"]["sources"], snapshot["metrics"], snapshot["prices"]),
                          "attempt": {"worker": self.owner, "started_at": started, "finished_at": now()}}
                # Ownership, cancellation and unique finalization share one transaction.
                with self.store.session() as session:
                    locked = session.execute(update(Job).where(Job.id == run_id, Job.owner == self.owner,
                        Job.status == "running", Job.lease_until >= time.time()).values(updated_at=now()))
                    if locked.rowcount != 1:
                        return True
                    job = session.get(Job, run_id)
                    if job.cancel_requested:
                        job.status, job.owner, job.lease_until = "cancelled", None, 0
                        return True
                    session.add(Result(id=result["id"], run_id=run_id, case_id=case["id"], payload=result))
                    session.flush()
                    job.completed = session.scalar(select(func.count()).select_from(Result).where(Result.run_id == run_id))
                    job.lease_until = time.time() + self.lease_seconds
                processed += 1
            with self.store.session() as session:
                job = session.get(Job, run_id)
                if job.owner == self.owner:
                    job.status = "cancelled" if job.cancel_requested else "completed"
                    job.updated_at, job.owner, job.lease_until = now(), None, 0
        except Exception as exc:
            with self.store.session() as session:
                job = session.get(Job, run_id)
                if job.owner == self.owner:
                    job.status, job.error, job.updated_at = "failed", f"{type(exc).__name__}: {exc}", now()
                    job.owner, job.lease_until = None, 0
        return True

    def release(self, run_id):
        with self.store.session() as session:
            session.execute(update(Job).where(Job.id == run_id, Job.owner == self.owner).values(
                status="queued", owner=None, lease_until=0, updated_at=now()))

    def serve(self):
        def stop(*_):
            self.stopping = True
        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        while not self.stopping:
            if not self.run_once():
                time.sleep(0.5)
