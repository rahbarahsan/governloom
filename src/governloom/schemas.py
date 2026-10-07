from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1


class Application(Record):
    id: str = Field(default_factory=uid)
    name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    expected_behavior: str = Field(min_length=1)
    application_version: str = "1"
    model_version: str = "lexical-demo-v1"
    prompt_version: str = "literal-v1"
    supported_fields: list[str] = Field(default_factory=lambda: [
        "answer", "citations", "retrieved_ids", "latency_ms", "error"
    ])
    demo: bool = False


class Source(Record):
    id: str = Field(default_factory=uid)
    application_id: str
    document_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    filename: str
    content: str
    content_hash: str
    created_at: str = Field(default_factory=now)


class SourceRef(Record):
    source_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)
    content_hash: str

    @model_validator(mode="after")
    def range_order(self):
        if self.end <= self.start:
            raise ValueError("Reference end must follow start")
        return self


class Case(Record):
    id: str = Field(default_factory=uid)
    application_id: str
    question: str = Field(min_length=1)
    category: Literal["answerable", "missing_information", "out_of_scope", "contradictory_outdated", "misleading_premise", "multi_turn_correction"]
    expected_behavior: Literal["answer", "abstain", "clarify"]
    reference_answer: str | None = None
    references: list[SourceRef] = Field(default_factory=list)
    relevant_source_ids: list[str] | None = None
    provenance: str = "manual; unreviewed"
    review_status: Literal["unreviewed", "approved", "rejected"] = "unreviewed"
    group_id: str = Field(min_length=1)
    split: Literal["calibration", "held_out", "exploratory"] = "exploratory"
    revision: int = Field(default=1, ge=1)


class Trace(Record):
    id: str = Field(default_factory=uid)
    case_id: str
    application_version: str
    model_version: str
    prompt_version: str
    answer: str | None = None
    behavior: Literal["answer", "abstain", "clarify"] | None = None
    citations: list[str] | None = None
    retrieved_ids: list[str] | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    error: str | None = None
    error_observed: bool = False
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    fault_label: str | None = None
    created_at: str = Field(default_factory=now)


class RunRequest(Record):
    dataset_id: str
    target: Literal["clean", "irrelevant_retrieval", "outdated_source", "unsupported_statement", "invalid_citation", "timeout", "imported"] = "clean"
    split: Literal["calibration", "held_out", "exploratory", "all"] = "held_out"
    sample_size: int = Field(default=100, ge=1, le=2000)
    sampling_seed: int = 0
    max_requests: int = Field(default=100, ge=1, le=2000)
    spending_cap: float = Field(default=0, ge=0)
    input_price_per_million: float | None = Field(default=None, ge=0)
    output_price_per_million: float | None = Field(default=None, ge=0)
    metrics: list[str] | None = None


class Review(Record):
    actor: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    decision: Literal["unreviewed", "approved", "rejected"]
    question: str | None = None
    reference_answer: str | None = None
    expected_behavior: Literal["answer", "abstain", "clarify"] | None = None


class ProviderConfig(Record):
    enabled: bool = False
    spending_cap: float = Field(default=0, ge=0)
    max_requests: int = Field(default=0, ge=0)
    model_version: str | None = None
