from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from governloom.schemas import Application, Case, Review, RunRequest, Trace


def test_explicit_null_edit_and_whitespace_validation(demo):
    wb, _, dataset = demo
    original = next(c for c in dataset["cases"] if c["category"] == "answerable")
    updated = wb.review(original["id"], Review(actor="reviewer", expected_revision=original["revision"],
        decision="unreviewed", expected_behavior="abstain", reference_answer=None))
    assert updated["reference_answer"] is None
    with pytest.raises(ValueError, match="cannot be blank"):
        wb.review(updated["id"], Review(actor="reviewer", expected_revision=updated["revision"], decision="unreviewed", question="   "))
    with pytest.raises(ValueError, match="Reviewer actor"):
        wb.review(updated["id"], Review(actor="  ", expected_revision=updated["revision"], decision="unreviewed"))


def test_source_range_must_not_extend_past_content(demo):
    wb, _, dataset = demo
    original = Case.model_validate(dataset["cases"][0])
    source = next(s for s in dataset["sources"] if s["id"] == original.references[0].source_id)
    original.references[0].start = 0
    original.references[0].end = len(source["content"]) + 50
    original.references[0].quote = source["content"]
    with pytest.raises(ValueError, match="Invalid source"):
        wb.validate_case(original, dataset["sources"])


def test_concurrent_publish_assigns_unique_versions(demo):
    wb, app, _ = demo
    with ThreadPoolExecutor(2) as pool:
        versions = list(pool.map(lambda actor: wb.publish(app["id"], actor)["version"], ["A", "B"]))
    assert sorted(versions) == [2, 3]


def test_nonfinite_telemetry_and_unsupported_fields_rejected():
    with pytest.raises(ValidationError):
        Trace(case_id="x", application_version="1", model_version="1", prompt_version="1", latency_ms=float("inf"))
    with pytest.raises(ValidationError):
        RunRequest(dataset_id="x", spending_cap=float("nan"))
    with pytest.raises(ValidationError):
        Application(name="x", owner="x", purpose="x", expected_behavior="x", supported_fields=["judge"])
