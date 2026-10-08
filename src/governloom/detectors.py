"""Versioned detector evidence and conservative, bounded distribution checks."""
import bisect
import copy
import hashlib
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from .schemas import Record, now, uid
from .service import checksum
from .storage import Entity
from .subscription import validate_judgment


class Calibration(Record):
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    labels_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    label_provenance: Literal["engineering", "independent_human", "observed_outcomes"]
    description: str = Field(min_length=1, max_length=2000)
    calibration_groups: list[str] = Field(min_length=1, max_length=100)
    held_out_groups: list[str] = Field(min_length=1, max_length=100)
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    true_negatives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    unavailable: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def disjoint(self):
        if set(self.calibration_groups) & set(self.held_out_groups):
            raise ValueError("Calibration and held-out groups must be disjoint")
        if not sum((self.true_positives, self.false_positives, self.true_negatives, self.false_negatives, self.unavailable)):
            raise ValueError("Report measured held-out outcomes, including unavailable checks")
        return self


class DetectorProfile(Record):
    name: str = Field(min_length=1, max_length=120)
    actor: str = Field(min_length=1, max_length=200)
    kind: Literal["claim_support", "distribution_shift"]
    task_type: Literal["vision", "rag", "forecasting", "classification", "generative", "custom"]
    phase: Literal["input", "output", "tool", "error", "outcome"] = "output"
    environment: str = Field(min_length=1, max_length=64)
    model_version: str = Field(min_length=1, max_length=200)
    application_version: str = Field(min_length=1, max_length=200)
    calibration: Calibration
    metric: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    reference: list[float] = Field(default_factory=list, max_length=1000)
    window_size: int = Field(default=100, ge=20, le=1000)
    alpha: float = Field(default=0.05, ge=0.001, le=0.2)
    minimum_effect: float = Field(default=0.2, ge=0, le=1)
    sampling_assumption: Literal["independent_samples", "dependent_replay"] = "independent_samples"
    corpus_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_hashes: dict[str, str] = Field(default_factory=dict, max_length=1000)
    judge_version: str | None = Field(default=None, max_length=200)
    rubric_version: str | None = Field(default=None, max_length=200)
    unsupported_fraction_threshold: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def prerequisites(self):
        if self.kind == "distribution_shift" and (not self.metric or len(self.reference) < 20 or any(not math.isfinite(v) for v in self.reference)):
            raise ValueError("Distribution profiles require a metric and 20..1000 finite reference samples")
        if self.kind == "claim_support" and not all((self.corpus_sha256, self.judge_version, self.rubric_version)):
            raise ValueError("Claim profiles require corpus, judge and rubric versions")
        if self.kind == "claim_support" and (not self.source_hashes or any(not key or len(key) > 200 or len(value) != 64 or any(c not in "0123456789abcdef" for c in value) for key, value in self.source_hashes.items())):
            raise ValueError("Claim profiles need immutable source IDs and SHA-256 hashes")
        return self


class ProfileApproval(Record):
    actor: str = Field(min_length=1, max_length=200)
    expected_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    rationale: str = Field(min_length=1, max_length=2000)


class Transient(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Quote(Transient):
    source_id: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=32000)


class Claim(Transient):
    claim: str = Field(min_length=1, max_length=32000)
    verdict: Literal["supported", "unsupported", "insufficient_evidence"]
    explanation: str = Field(min_length=1, max_length=4000)
    evidence: list[Quote] = Field(max_length=20)


class Passage(Transient):
    id: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=32000)


class Grounding(Transient):
    profile_id: str = Field(min_length=1, max_length=128)
    corpus_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    judge_version: str = Field(min_length=1, max_length=200)
    rubric_version: str = Field(min_length=1, max_length=200)
    answer_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    claims: list[Claim] = Field(min_length=1, max_length=100)
    sources: list[Passage] = Field(min_length=1, max_length=20)


def distribution_check(reference, observed, *, alpha=0.05, window_index=1, minimum_effect=0.2):
    """Triangle inequality + two one-sample DKW bounds + union bound.

    Spending alpha/(k(k+1)) sums to alpha over all completed windows. The
    finite-sample probability statement requires IID samples; ties are allowed.
    """
    if not reference or not observed or window_index < 1 or not 0 < alpha < 1 or not 0 <= minimum_effect <= 1 or any(not math.isfinite(v) for v in (*reference, *observed)):
        raise ValueError("Finite nonempty samples and valid probability/effect parameters required")
    left, right = sorted(reference), sorted(observed)
    distance = max(abs(bisect.bisect_right(left, v) / len(left) - bisect.bisect_right(right, v) / len(right)) for v in set(left + right))
    spent = alpha / (window_index * (window_index + 1))
    critical = math.sqrt(math.log(4 / spent) / (2 * len(left))) + math.sqrt(math.log(4 / spent) / (2 * len(right)))
    return {"distance": distance, "critical_distance": critical, "alpha_spent": spent, "window_index": window_index,
            "reference_samples": len(left), "samples": len(right), "minimum_effect": minimum_effect,
            "triggered": distance > max(critical, minimum_effect), "can_detect": critical < 1,
            "method": "two one-sample DKW-Massart bounds; triangle/union bound; lifetime alpha spending"}


class Profiles:
    def __init__(self, workbench):
        self.workbench, self.store = workbench, workbench.store

    def create(self, application_id, body):
        self.store.get("application", application_id)
        payload = body.model_dump(mode="json")
        record = {**payload, "id": uid(), "application_id": application_id, "created_at": now(),
                  "checksum": checksum(payload), "reference_sha256": checksum(body.reference), "engine_version": "evidence-detectors-v1"}
        with self.store.session() as session:
            session.add(Entity(id=record["id"], kind="detector_profile", application_id=application_id, payload=record))
            self.workbench.audit(session, application_id, record["id"], 1, "detector_profile_created", body.actor, {"checksum": record["checksum"]})
        return record

    def approve(self, identifier, body):
        profile = self.store.get("detector_profile", identifier)
        if profile["checksum"] != body.expected_checksum:
            raise ValueError("Profile checksum differs; inspect the immutable profile")
        record = {**body.model_dump(), "id": checksum(["profile_approval", identifier])[:32], "profile_id": identifier,
                  "application_id": profile["application_id"], "created_at": now(), "meaning": "Operator accepts this evidence for an experimental signal; not a safety certification"}
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            if session.get(Entity, record["id"]):
                raise ValueError("Profile already approved; create a new version to change evidence")
            session.add(Entity(id=record["id"], kind="profile_approval", application_id=record["application_id"], payload=record))
            self.workbench.audit(session, record["application_id"], identifier, 1, "detector_profile_approved", body.actor, {"checksum": profile["checksum"], "rationale": body.rationale})
        return record

    @staticmethod
    def evaluate(session, application_id, rule, event, metrics):
        row = session.get(Entity, rule["profile_id"])
        if not row or row.kind != "detector_profile" or row.application_id != application_id:
            return True, False, {"reason": "Profile unavailable for this application"}
        profile = row.payload
        evidence = {"profile_id": row.id, "profile_checksum": profile["checksum"], "calibration": profile["calibration"], "engine_version": profile["engine_version"]}
        approval = session.get(Entity, checksum(["profile_approval", row.id])[:32])
        if not approval or approval.kind != "profile_approval":
            return True, False, {**evidence, "reason": "Profile has not been approved"}
        if any(profile[field] != getattr(event, field) for field in ("task_type", "environment", "model_version", "application_version")) or profile["kind"] != rule["detector"]:
            return True, False, {**evidence, "reason": "Event outside the calibrated deployment scope"}
        phase = profile.get("phase", "outcome" if profile["task_type"] == "forecasting" else "output")
        if phase != event.phase:
            return True, False, {**evidence, "reason": "Event outside the calibrated phase"}
        if rule["detector"] == "claim_support":
            return Profiles.grounding(profile, event, evidence)
        if profile["metric"] not in metrics:
            return True, False, {**evidence, "reason": "Calibrated metric unavailable"}
        identifier = checksum(["detector_window", application_id, row.id])[:32]
        window_row = session.get(Entity, identifier)
        window = copy.deepcopy(window_row.payload) if window_row else {"id": identifier, "values": [], "index": 0}
        window["values"].append(metrics[profile["metric"]])
        if len(window["values"]) < profile["window_size"]:
            result = True, False, {**evidence, "reason": "Waiting for a complete non-overlapping window", "samples": len(window["values"]), "required": profile["window_size"]}
        else:
            window["index"] += 1
            measured = distribution_check(profile["reference"], window["values"], alpha=profile["alpha"], window_index=window["index"], minimum_effect=profile["minimum_effect"])
            window["values"] = []
            dependence = profile["sampling_assumption"] == "dependent_replay"
            measured["interpretation"] = "Replay distance signal only; serial dependence invalidates the nominal probability bound" if dependence else "Conditional on IID reference/current sampling, not a proof of model quality"
            # Never advertise significance for a known dependent time series.
            measured["nominal_probability_valid"] = not dependence
            result = not measured["can_detect"], measured["triggered"], {**evidence, **measured}
        if window_row:
            window_row.payload = window
        else:
            session.add(Entity(id=identifier, kind="detector_window", application_id=application_id, payload=window))
        return result

    @staticmethod
    def grounding(profile, event, evidence):
        body = event.grounding
        if body is None or event.text is None:
            return True, False, {**evidence, "reason": "Transient text/judge evidence unavailable"}
        if body.profile_id != profile["id"] or any(getattr(body, field) != profile[field] for field in ("corpus_sha256", "judge_version", "rubric_version")) or body.answer_sha256 != hashlib.sha256(event.text.encode()).hexdigest():
            return True, False, {**evidence, "reason": "Judge, rubric, corpus or answer version mismatch"}
        if len({s.id for s in body.sources}) != len(body.sources) or not event.source_ids or set(s.id for s in body.sources) != set(event.source_ids):
            return True, False, {**evidence, "reason": "Source identity mismatch"}
        sources = [{"id": source.id, "content": source.content, "content_hash": hashlib.sha256(source.content.encode()).hexdigest()} for source in body.sources]
        if any(profile["source_hashes"].get(source["id"]) != source["content_hash"] for source in sources):
            return True, False, {**evidence, "reason": "Source content differs from the frozen corpus"}
        output = {"claims": [claim.model_dump() for claim in body.claims]}
        try:
            validate_judgment(output, event.text, sources)
        except ValueError:
            return True, False, {**evidence, "reason": "Judge evidence is invalid; no trustworthy verdict"}
        covered, positions = set(), []
        counts = {"supported": 0, "unsupported": 0, "insufficient_evidence": 0}
        for claim in output["claims"]:
            if claim["verdict"] == "supported" and any(quote["source_id"] not in (event.citations or []) for quote in claim["evidence"]):
                return True, False, {**evidence, "reason": "Supported claim evidence must identify a cited source"}
            start = event.text.index(claim["claim"])
            end = start + len(claim["claim"])
            # Duplicate/overlapping excerpt judgments are ambiguous, not extra votes.
            if any(i in covered for i in range(start, end)):
                return True, False, {**evidence, "reason": "Overlapping claim excerpts"}
            covered.update(range(start, end))
            counts[claim["verdict"]] += 1
            positions.append({"start": start, "end": end, "verdict": claim["verdict"],
                "evidence": [{key: quote[key] for key in ("source_id", "start", "end", "content_hash")} for quote in claim["evidence"]]})
        meaningful = {i for i, char in enumerate(event.text) if not char.isspace()}
        coverage = len(covered & meaningful) / len(meaningful) if meaningful else 0
        fraction = counts["unsupported"] / len(output["claims"])
        triggered = fraction > profile["unsupported_fraction_threshold"]
        missing = not triggered and (coverage < 0.95 or counts["insufficient_evidence"] > 0)
        return missing, triggered, {**evidence, "counts": counts, "claim_positions": positions, "coverage": coverage,
            "unsupported_fraction": fraction, "threshold": profile["unsupported_fraction_threshold"],
            "answer_sha256": body.answer_sha256, "content": "not retained", "limitation": "Upstream model judgment; exact quotes verify provenance, not entailment. Coverage gaps never clear."}
