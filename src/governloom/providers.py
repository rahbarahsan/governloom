import math
from typing import Protocol

from pydantic import Field

from .schemas import Case, ProviderConfig, Record, SourceRef


class CandidateProvider(Protocol):
    def generate(self, passages: list[dict], config: ProviderConfig) -> list[dict]: ...


class JudgeProvider(Protocol):
    def judge(self, case: dict, trace: dict, rubric: str, config: ProviderConfig) -> dict: ...


class UnavailableProvider:
    def generate(self, passages, config):
        raise ValueError("No provider adapter configured; no paid requests are supported in this release")

    def judge(self, case, trace, rubric, config):
        raise ValueError("No calibrated judge adapter configured")


class Budget:
    """Preflight reservation for future provider adapters; credentials remain server-side."""
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.requests = 0
        self.reserved = 0.0

    def reserve(self, maximum_cost: float):
        if not self.config.enabled or not self.config.model_version:
            raise ValueError("Provider is disabled or lacks a pinned model version")
        if self.config.spending_cap <= 0 or not math.isfinite(maximum_cost) or maximum_cost <= 0:
            raise ValueError("An explicit positive spending cap and request cost bound are required")
        if self.requests >= self.config.max_requests or self.reserved + maximum_cost > self.config.spending_cap:
            raise ValueError("Provider request/spending limit exceeded")
        self.requests += 1
        self.reserved += maximum_cost


class JudgeEstimate(Record):
    judge: str
    model_version: str
    rubric_version: str
    score: float = Field(ge=0, le=1)
    explanation: str
    evidence: list[SourceRef] = Field(min_length=1)
    calibration: str = "unavailable; requires independent human labels"


class ProviderSession:
    """Explicit integration seam for trusted adapters, tested with a no-network fake.

    No API route instantiates this session. The caller must supply an adapter,
    pinned configuration, bounded passage sample, and worst-case request price.
    Failed requests retain their reservation and are never retried implicitly.
    """
    def __init__(self, config: ProviderConfig, adapter):
        self.budget = Budget(config)
        self.adapter = adapter

    def candidates(self, workbench, application_id, source_ids, maximum_cost):
        if not source_ids or len(source_ids) > 20 or len(set(source_ids)) != len(source_ids):
            raise ValueError("Provide 1–20 unique source IDs as an explicit evidence sample")
        sources = [workbench.store.get("source", source_id) for source_id in source_ids]
        if any(source["application_id"] != application_id for source in sources):
            raise ValueError("Evidence sample belongs to another application")
        self.budget.reserve(maximum_cost)
        output = self.adapter.generate(sources, self.budget.config)
        if len(output) > 100:
            raise ValueError("Provider exceeded the 100-candidate response bound")
        cases = [Case.model_validate(item) for item in output]
        for case in cases:
            workbench.validate_case(case, sources)
            case.provenance = f"model-generated estimate; {self.budget.config.model_version}; unreviewed"
        return workbench.import_cases(application_id, "\n".join(case.model_dump_json() for case in cases))

    def estimate(self, workbench, case, trace, rubric_version, maximum_cost):
        if not rubric_version.strip():
            raise ValueError("A versioned rubric is required")
        self.budget.reserve(maximum_cost)
        estimate = JudgeEstimate.model_validate(self.adapter.judge(case, trace, rubric_version, self.budget.config))
        if estimate.model_version != self.budget.config.model_version or estimate.rubric_version != rubric_version:
            raise ValueError("Judge model/rubric version differs from pinned configuration")
        validation_case = Case.model_validate({**case, "references": [ref.model_dump() for ref in estimate.evidence]})
        workbench.validate_case(validation_case, workbench.store.list("source", case["application_id"]))
        # Adapter claims cannot stand in for measured independent agreement.
        estimate.calibration = "unavailable; requires independent human labels"
        return estimate.model_dump()
