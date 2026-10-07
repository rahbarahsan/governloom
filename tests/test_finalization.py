from governloom.demo import LexicalTarget
from governloom.schemas import Review, RunRequest
from governloom.storage import Job
from governloom.worker import Worker


def test_rejection_excluded_from_new_dataset_preserves_old_evidence(demo):
    wb, app, dataset = demo
    case = dataset["cases"][0]
    wb.review(case["id"], Review(actor="reviewer", expected_revision=case["revision"], decision="rejected"))
    next_version = wb.publish(app["id"], "reviewer")
    assert len(next_version["cases"]) == 39
    assert case["id"] not in {c["id"] for c in next_version["cases"]}
    assert len(wb.store.get("dataset", dataset["id"])["cases"]) == 40


def test_worker_losing_lease_during_target_cannot_finalize(demo):
    wb, _, dataset = demo
    run = wb.queue(RunRequest(dataset_id=dataset["id"]))

    class LeaseStealingTarget:
        def execute(self, *args):
            with wb.store.session() as session:
                job = session.get(Job, run["id"])
                job.owner, job.lease_until = "replacement-worker", 0
            return LexicalTarget().execute(*args)

    Worker(wb.store, target=LeaseStealingTarget()).run_once()
    assert wb.run(run["id"])["results"] == []
    Worker(wb.store).run_once()
    assert wb.run(run["id"])["status"] == "completed"
    assert len(wb.run(run["id"])["results"]) == 20
