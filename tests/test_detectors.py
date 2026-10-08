import copy
import hashlib
import random

import pytest

from governloom.detectors import DetectorProfile, ProfileApproval, Profiles, distribution_check
from governloom.monitoring import Monitor, MonitorPolicy, RuntimeEvent
from governloom.schemas import Application

CALIBRATION = dict(dataset_sha256="a"*64, labels_sha256="b"*64, label_provenance="engineering", description="Test controls, not independent human labels", calibration_groups=["calibration"], held_out_groups=["held-out"], true_positives=1, false_positives=0, true_negatives=1, false_negatives=0)
FIELDS = dict(trace_id="detector-test", phase="output", task_type="rag", model_version="target-v1", application_version="service-v1", environment="test")


def setup(workbench, kind, **extra):
    app = workbench.create_application(Application(name="Detector", purpose="Test", owner="Test", expected_behavior="Evidence"))
    monitor, profiles = Monitor(workbench), Profiles(workbench)
    profile = profiles.create(app["id"], DetectorProfile(name="Frozen evidence", actor="test", kind=kind, calibration=CALIBRATION,
        **{k: FIELDS[k] for k in ("task_type", "model_version", "application_version", "environment")}, **extra))
    monitor.policy(app["id"], MonitorPolicy(name="Evidence", actor="test", rationale="Test", rules=[dict(id="evidence", name="Evidence", detector=kind, profile_id=profile["id"], action="review", mitigation="Investigate evidence")]))
    key = monitor.issue_key(app["id"], "test", "test")["key"]
    return app, monitor, profiles, profile, key


def test_finite_sample_distance_ties_alpha_spending_and_negative_controls():
    assert distribution_check([0, 0, 1], [0, 1, 1], minimum_effect=0)["distance"] == pytest.approx(1/3)
    assert distribution_check([0]*100, [1]*100)["triggered"]
    assert not distribution_check([0]*100, [0]*100)["triggered"]
    assert not distribution_check([0], [1])["can_detect"]
    assert sum(distribution_check([0]*20, [1]*20, window_index=k)["alpha_spent"] for k in range(1, 100)) < .05
    rng = random.Random(41)
    # This reproducible software validation checks IID controls only; its result
    # does not imply calibration on customers' temporally correlated signals.
    false_positive = 0
    for _ in range(200):
        false_positive += distribution_check([rng.random() for _ in range(100)], [rng.random() for _ in range(100)])["triggered"]
    assert false_positive <= 5
    with pytest.raises(ValueError):
        distribution_check([float("nan")], [1])


def test_window_approval_scope_restart_and_duplicate_do_not_spend_twice(workbench):
    app, monitor, profiles, profile, key = setup(workbench, "distribution_shift", metric="confidence", reference=[.5]*20, window_size=20)
    event = RuntimeEvent(**FIELDS, metrics={"confidence": .5})
    assert monitor.ingest(key, event)["checks"][0]["status"] == "insufficient_evidence"
    profiles.approve(profile["id"], ProfileApproval(actor="reviewer", expected_checksum=profile["checksum"], rationale="Accept engineering controls"))
    assert monitor.ingest(key, RuntimeEvent(**{**FIELDS, "phase": "input"}, metrics={"confidence": 1}))["checks"][0]["status"] == "insufficient_evidence"
    for _ in range(19):
        assert monitor.ingest(key, RuntimeEvent(**FIELDS, metrics={"confidence": .5}))["checks"][0]["status"] == "insufficient_evidence"
    # Reconstruction and exact replay preserve the 19-sample window.
    assert Monitor(workbench).ingest(key, event)["duplicate"]
    completed = monitor.ingest(key, RuntimeEvent(**FIELDS, metrics={"confidence": .5}))
    assert completed["checks"][0]["status"] == "clear"
    assert completed["checks"][0]["evidence"]["window_index"] == 1
    assert monitor.ingest(key, RuntimeEvent(**{**FIELDS, "model_version": "other"}, metrics={"confidence": 1}))["checks"][0]["status"] == "insufficient_evidence"
    for _ in range(20):
        shifted = monitor.ingest(key, RuntimeEvent(**FIELDS, metrics={"confidence": 1}))
    assert shifted["action"] == "review" and shifted["checks"][0]["evidence"]["window_index"] == 2
    assert len(monitor.alerts(app["id"])) == 1
    assert monitor.ingest(key, RuntimeEvent(**FIELDS))["checks"][0]["status"] == "insufficient_evidence"
    with pytest.raises(ValueError, match="approved"):
        profiles.approve(profile["id"], ProfileApproval(actor="test", expected_checksum=profile["checksum"], rationale="Again"))


def test_grounding_hashes_quotes_coverage_privacy_and_unsupported(workbench):
    source = "The collector scans text transiently."
    sha = lambda value: hashlib.sha256(value.encode()).hexdigest()
    app, monitor, profiles, profile, key = setup(workbench, "claim_support", corpus_sha256="c"*64, judge_version="judge-v1", rubric_version="rubric-v1", source_hashes={"source-1": sha(source)})
    profiles.approve(profile["id"], ProfileApproval(actor="reviewer", expected_checksum=profile["checksum"], rationale="Accept narrowly scoped engineering evidence"))
    claim = {"claim": source, "verdict": "supported", "explanation": "Exact source evidence", "evidence": [{"source_id": "source-1", "quote": source}]}
    body = dict(profile_id=profile["id"], corpus_sha256="c"*64, judge_version="judge-v1", rubric_version="rubric-v1", answer_sha256=sha(source), claims=[claim], sources=[{"id": "source-1", "content": source}])
    def ingest(text=source, grounding=body, **fields):
        return monitor.ingest(key, RuntimeEvent(**FIELDS, text=text, grounding=grounding, source_ids=["source-1"], citations=["source-1"], **fields))
    clear = ingest()
    assert clear["checks"][0]["status"] == "clear"
    stored = str(monitor.events(app["id"])) + str(monitor.alerts(app["id"]))
    assert source not in stored and "Exact source evidence" not in stored
    assert "content_hash" in stored and "claim_positions" in stored
    invalid = copy.deepcopy(body); invalid["sources"][0]["content"] = source + " Tampered."
    assert ingest(grounding=invalid)["checks"][0]["status"] == "insufficient_evidence"
    invalid = copy.deepcopy(body); invalid["claims"][0]["evidence"][0]["quote"] = "Fabricated quote"
    assert ingest(grounding=invalid)["checks"][0]["status"] == "insufficient_evidence"
    gap = copy.deepcopy(body); gap["answer_sha256"] = sha(source + " It sells your data.")
    assert ingest(text=source + " It sells your data.", grounding=gap)["checks"][0]["status"] == "insufficient_evidence"
    unsupported = copy.deepcopy(body); unsupported["claims"][0].update(claim="The collector stores all raw text.", verdict="unsupported", explanation="Contradicts source")
    unsupported["answer_sha256"] = sha(unsupported["claims"][0]["claim"])
    flagged = ingest(text=unsupported["claims"][0]["claim"], grounding=unsupported)
    assert flagged["action"] == "review" and flagged["checks"][0]["evidence"]["counts"]["unsupported"] == 1
    assert ingest(text=None, grounding=None)["checks"][0]["status"] == "insufficient_evidence"
    assert monitor.ingest(key, RuntimeEvent(**FIELDS, text=source, grounding=body, source_ids=["source-1"], citations=[]))["checks"][0]["status"] == "insufficient_evidence"
