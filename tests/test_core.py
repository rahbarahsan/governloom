import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from governloom.demo import LexicalTarget, generate_candidates, seed, seed_gold
from governloom.metrics import METRICS, evaluate, recommend
from governloom.providers import Budget, UnavailableProvider
from governloom.schemas import Application, Case, ProviderConfig, Review, RunRequest, Trace
from governloom.service import Workbench, checksum
from governloom.storage import Entity, Job, Result, Store
from governloom.worker import Worker


def complete(workbench, dataset, target="clean", **kwargs):
    run = workbench.queue(RunRequest(dataset_id=dataset["id"], target=target, **kwargs))
    Worker(workbench.store).run_once()
    return workbench.run(run["id"])


def test_import_source_identity_utf8_and_version(workbench):
    app = workbench.create_application(Application(name="Test", owner="Me", purpose="Support", expected_behavior="Evidence"))
    source = workbench.import_source(app["id"], "policy", "1", "policy.md", "Café\n政策")
    assert source["content_hash"] == checksum("Café\n政策")
    assert workbench.import_source(app["id"], "policy", "1", "policy.md", "Café\n政策")["id"] == source["id"]
    with pytest.raises(ValueError, match="new version"):
        workbench.import_source(app["id"], "policy", "1", "policy.md", "changed")
    assert workbench.import_source(app["id"], "policy", "2", "policy.txt", "changed")["id"] != source["id"]
    with pytest.raises(ValueError, match="UTF-8"):
        workbench.import_source(app["id"], "pdf", "1", "policy.pdf", "binary")


def test_gold_references_categories_and_group_splits(demo):
    wb, app, dataset = demo
    assert len(dataset["cases"]) == 40
    assert len([c for c in dataset["cases"] if c["split"] == "held_out"]) == 20
    assert len({c["category"] for c in dataset["cases"]}) == 6
    assert all("no independent human review" in c["provenance"] for c in dataset["cases"])
    for case in dataset["cases"]:
        wb.validate_case(Case.model_validate(case), dataset["sources"])
    groups = {}
    for case in dataset["cases"]:
        groups.setdefault(case["group_id"], set()).add(case["split"])
    assert all(len(splits) == 1 for splits in groups.values())
    assert seed_gold(wb, app["id"]) == []


def test_invalid_references_and_atomic_jsonl(workbench):
    app = seed(workbench)
    case = generate_candidates(app["id"], workbench.store.list("source", app["id"]))[0]
    case.references[0].quote = "invented"
    with pytest.raises(ValueError, match="Invalid source"):
        workbench.import_cases(app["id"], case.model_dump_json())
    assert workbench.store.list("case", app["id"]) == []
    with pytest.raises(ValueError, match="JSONL line 2"):
        workbench.import_cases(app["id"], case.model_dump_json() + "\n{}")


def test_unstructured_generation_unavailable(workbench):
    app = workbench.create_application(Application(name="Text", owner="Me", purpose="Any prose", expected_behavior="Answer"))
    workbench.import_source(app["id"], "text", "1", "text.md", "Arbitrary prose.")
    with pytest.raises(ValueError, match="structured facts"):
        workbench.generate(app["id"])


def test_cross_split_import_rejected(demo):
    wb, app, dataset = demo
    case = Case.model_validate(dataset["cases"][0])
    case.id = "other"
    case.question += " different wording"
    case.split = "exploratory"
    with pytest.raises(ValueError, match="cannot cross"):
        wb.import_cases(app["id"], case.model_dump_json())


def test_publication_is_immutable_and_review_is_audited(demo):
    wb, app, dataset = demo
    case = dataset["cases"][0]
    old_checksum = dataset["checksum"]
    changed = wb.review(case["id"], Review(actor="Reviewer", expected_revision=case["revision"], decision="approved", question=case["question"] + " Please."))
    assert changed["revision"] == case["revision"] + 1
    assert wb.store.get("dataset", dataset["id"])["checksum"] == old_checksum
    assert wb.store.get("dataset", dataset["id"])["cases"] == dataset["cases"]
    second = wb.publish(app["id"], "Reviewer")
    assert second["version"] == 2 and second["checksum"] != old_checksum
    assert any(e["actor"] == "Reviewer" and e["revision"] == changed["revision"] for e in wb.store.list("review_event", app["id"]))
    with pytest.raises(ValueError, match="Stale"):
        wb.review(case["id"], Review(actor="Other", expected_revision=case["revision"], decision="rejected"))


def test_prerequisites_and_numeric_metrics(demo):
    wb, app, dataset = demo
    case = next(c for c in dataset["cases"] if c["category"] == "answerable")
    trace = LexicalTarget().execute(case, dataset["sources"], app)
    definitions = recommend(app, [case])
    states = {m["id"]: m["state"] for m in definitions}
    assert states["task_success"] == "enabled"
    assert states["cost"] == states["semantic_grounding"] == "unavailable"
    rows = {m["metric"]: m for m in evaluate(case, trace, dataset["sources"], definitions, {"input": None, "output": None})}
    assert rows["cost"]["value"] is None
    assert rows["semantic_grounding"]["status"] == "insufficient_evidence"
    trace.update(input_tokens=100, output_tokens=50, latency_ms=123, retrieved_ids=[case["references"][0]["source_id"], "other"])
    rows = {m["metric"]: m for m in evaluate(case, trace, dataset["sources"], definitions, {"input": 2, "output": 4})}
    assert rows["cost"]["value"] == pytest.approx(0.0004)
    assert rows["token_usage"]["value"] == 150
    assert rows["latency"]["value"] == 123
    assert rows["retrieval_precision"]["value"] == 0.5
    assert rows["retrieval_recall"]["value"] == 1
    trace["latency_ms"] = None
    assert next(m for m in evaluate(case, trace, dataset["sources"], definitions, {}) if m["metric"] == "latency")["value"] is None


def test_skips_errors_and_missing_traces(demo):
    wb, app, dataset = demo
    case = next(c for c in dataset["cases"] if c["expected_behavior"] == "abstain")
    definitions = recommend(app, [case])
    trace = LexicalTarget().execute(case, dataset["sources"], app)
    rows = evaluate(case, trace, dataset["sources"], definitions, {})
    assert next(m for m in rows if m["metric"] == "citation_existence")["status"] == "skipped"
    assert all(m["status"] == "insufficient_evidence" for m in evaluate(case, None, dataset["sources"], definitions, {}))
    bad_definition = [{**definitions[0], "id": "broken"}]
    assert evaluate(case, trace, dataset["sources"], bad_definition, {})[0]["status"] == "evaluator_error"


def test_clean_and_fault_detection_with_denominators(demo):
    wb, app, dataset = demo
    clean = complete(wb, dataset)
    assert clean["status"] == "completed" and clean["total"] == clean["completed"] == 20
    assert not any(m["status"] == "failed" for r in clean["results"] for m in r["metrics"])
    for target in ("irrelevant_retrieval", "outdated_source", "invalid_citation", "timeout"):
        faulty = complete(wb, dataset, target)
        assert faulty["status"] == "completed"
        assert any(m["status"] == "failed" for r in faulty["results"] for m in r["metrics"])
        comparison = wb.compare(clean["id"], faulty["id"])
        assert comparison["compatible"] and comparison["matched_cases"] == 20 and comparison["changes"]
    unsupported = complete(wb, dataset, "unsupported_statement")
    assert not any(m["status"] == "failed" for r in unsupported["results"] for m in r["metrics"])
    assert clean["summary"]["cost"]["scored"] == 0
    assert clean["summary"]["cost"]["insufficient_evidence"] == 20
    assert clean["summary"]["citation_existence"]["skipped"] > 0
    assert clean["summary"]["citation_existence"]["scored"] + clean["summary"]["citation_existence"]["skipped"] == 20


def test_restart_and_lease_recovery_without_duplicate_results(demo):
    wb, app, dataset = demo
    run = wb.queue(RunRequest(dataset_id=dataset["id"]))
    worker = Worker(wb.store)
    worker.run_once(max_cases=3)
    assert wb.run(run["id"])["completed"] == 3
    # Simulate a hard crash after several finalized results and before lease release.
    with wb.store.session() as session:
        job = session.get(Job, run["id"])
        job.status, job.owner, job.lease_until = "running", "dead-process", time.time() - 1
    restarted = Workbench(Store(wb.store.url))
    Worker(restarted.store).run_once()
    final = restarted.run(run["id"])
    assert final["status"] == "completed" and final["completed"] == 20
    assert len({r["case_id"] for r in final["results"]}) == len(final["results"]) == 20
    assert sum(r["attempt"]["worker"] == worker.owner for r in final["results"]) == 3


def test_atomic_claim_and_lease_owner_fencing(demo):
    wb, _, dataset = demo
    run = wb.queue(RunRequest(dataset_id=dataset["id"]))
    workers = [Worker(wb.store), Worker(wb.store)]
    with ThreadPoolExecutor(2) as pool:
        claims = list(pool.map(lambda w: w.claim(), workers))
    assert claims.count(run["id"]) == 1
    assert claims.count(None) == 1
    loser = workers[claims.index(None)]
    loser.release(run["id"])
    assert wb.run(run["id"])["status"] == "running"


def test_cancellation_queued_and_during_execution(demo):
    wb, app, dataset = demo
    queued = wb.queue(RunRequest(dataset_id=dataset["id"]))
    assert wb.cancel(queued["id"])["status"] == "cancelled"
    assert not Worker(wb.store).run_once()
    run = wb.queue(RunRequest(dataset_id=dataset["id"]))

    class CancellingTarget:
        def execute(self, *args):
            wb.cancel(run["id"])
            return LexicalTarget().execute(*args)

    Worker(wb.store, target=CancellingTarget()).run_once()
    final = wb.run(run["id"])
    assert final["status"] == "cancelled" and final["results"] == []


def test_sampling_limits_and_incompatible_comparison(demo):
    wb, _, dataset = demo
    with pytest.raises(ValueError, match="max_requests"):
        wb.queue(RunRequest(dataset_id=dataset["id"], max_requests=2))
    a = complete(wb, dataset, sample_size=4, sampling_seed=8)
    b = complete(wb, dataset, sample_size=4, sampling_seed=8)
    assert [r["case_id"] for r in a["results"]] == [r["case_id"] for r in b["results"]]
    other = complete(wb, dataset, metrics=["latency"])
    comparison = wb.compare(a["id"], other["id"])
    assert not comparison["compatible"] and comparison["reasons"]


def test_imported_trace_missing_evidence_and_frozen_versions(demo):
    wb, app, dataset = demo
    case = dataset["cases"][0]
    trace = Trace(case_id=case["id"], application_version=app["application_version"], model_version=app["model_version"], prompt_version=app["prompt_version"])
    batch = wb.import_traces(app["id"], trace.model_dump_json())
    run = wb.queue(RunRequest(dataset_id=dataset["id"], target="imported", split="all"), batch["id"])
    Worker(wb.store).run_once()
    final = wb.run(run["id"])
    assert len(final["results"]) == 40
    assert final["summary"]["latency"]["insufficient_evidence"] == 40
    assert final["summary"]["errors"]["scored"] == 0
    assert final["snapshot"]["traces"] == batch["traces"]
    trace.model_version = "wrong"
    with pytest.raises(ValueError, match="versions"):
        wb.import_traces(app["id"], trace.model_dump_json())


def test_provider_disabled_and_budget():
    config = ProviderConfig()
    with pytest.raises(ValueError, match="disabled"):
        Budget(config).reserve(0.01)
    with pytest.raises(ValueError, match="No provider"):
        UnavailableProvider().generate([], config)
    budget = Budget(ProviderConfig(enabled=True, spending_cap=0.02, max_requests=2, model_version="fake-v1"))
    budget.reserve(0.01)
    budget.reserve(0.01)
    with pytest.raises(ValueError, match="limit"):
        budget.reserve(0.01)
