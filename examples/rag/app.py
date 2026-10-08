from typing import Literal
import os
import hashlib

from pydantic import BaseModel, ConfigDict, Field

from examples.common import State, hook, service
from examples.rag.model import Retriever, SubscriptionGenerator, SubscriptionJudge
from governloom.hook import PolicyViolation


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=5000)
    mode: Literal["observe", "enforce"] = "enforce"


class Fault(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)
    mutation: Literal["invalid_citation", "credential"]


def create_app(retriever=None, generator=None, state=None, hook_factory=hook, judge=None):
    retriever, generator = retriever or Retriever(), generator or SubscriptionGenerator()
    state = state or State("rag")
    profile_id = os.environ.get("RAG_GROUNDING_PROFILE")
    judge = judge or (SubscriptionJudge() if profile_id else None)
    version = generator.model + "-" + retriever.manifest["corpus_sha256"][:12]
    api = service("Repository documentation RAG")

    @api.get("/manifest")
    def manifest():
        return {**retriever.manifest, "model_selector": generator.model,
                "model_version": version, "generator": type(generator).__name__}

    @api.get("/reviews")
    def reviews():
        return state.list("review")

    def output_fields(output, sources):
        fields = {"text": output["answer"], "citations": output["citations"],
                  "source_ids": [source["id"] for source in sources]}
        if judge and profile_id:
            judged = judge.judge(output["answer"], sources)
            fields["grounding"] = {"profile_id": profile_id, "corpus_sha256": retriever.manifest["corpus_sha256"],
                "judge_version": judged["judge_version"], "rubric_version": judged["rubric_version"],
                "answer_sha256": hashlib.sha256(output["answer"].encode()).hexdigest(),
                "claims": judged["judgment"]["claims"], "sources": [{"id": source["id"], "content": source["content"]} for source in sources]}
            fields["metrics"] = {"judge_latency_ms": judged["latency_ms"]}
        return fields

    def save(receipt, output, sources, scenario, blocked, capture=None):
        record = {"id": receipt["event_id"], "output": output, "sources": sources,
                  "receipt": receipt, "scenario": scenario, "withheld": blocked, "capture": capture}
        state.put(record["id"], "answer", record)
        if receipt["action"] in ("review", "block"):
            state.put("review-" + record["id"], "review", {**record, "status": "awaiting_review"})
            for alert_id in receipt["alert_ids"]:
                hook_factory("observe").acknowledge_action(alert_id=alert_id,
                    action_type="withheld" if blocked else "review_queued", evidence_id=record["id"])
        return {"status": "withheld" if blocked else "returned", "answer": None if blocked else output,
                "receipt": receipt, "scenario": scenario, "capture": capture}

    @api.post("/answer")
    def answer(body: Question):
        sources = retriever.retrieve(body.question)
        captured = {}
        def generate(question):
            record = generator.generate(question, sources)
            captured.update(record)
            return record["output"]
        connection = hook_factory(body.mode)
        monitored = connection.wrap(generate, task_type="rag", model_version=version,
            application_version="documentation-service-v1", environment="testbed-natural",
            input_mapper=lambda question: {"text": question},
            output_mapper=lambda output: output_fields(output, sources))
        blocked = False
        try:
            output = monitored(body.question)
        except PolicyViolation:
            blocked, output = True, captured.get("output")
        receipt = connection.last_receipt
        return save(receipt, output, sources, "natural", blocked, captured or None)

    @api.post("/faults")
    def fault(body: Fault):
        original = state.get(body.event_id)
        if original["scenario"] != "natural" or original["output"] is None:
            raise ValueError("Faults require an actual completed natural answer")
        output = {**original["output"], "citations": list(original["output"]["citations"])}
        if body.mutation == "invalid_citation":
            output["citations"] = ["deliberately-nonexistent-source"]
        else:
            output["answer"] += "\nDeclared test credential: sk-test123456789012345678901234567890"
        connection = hook_factory("enforce")
        blocked = False
        try:
            receipt = connection.emit(trace_id=original["receipt"]["trace_id"], phase="output", task_type="rag",
                model_version=version, application_version="documentation-service-v1", environment="testbed-fault",
                **output_fields(output, original["sources"]))
        except PolicyViolation as exc:
            blocked, receipt = True, exc.receipt
        return save(receipt, output, original["sources"], "post-generation-" + body.mutation, blocked)

    @api.post("/tools/write")
    def attempt_write():
        marker = state.path.parent / "tool-write-marker.txt"
        if marker.exists():
            raise ValueError("Use fresh application storage for a side-effect check")
        connection = hook_factory("enforce")
        monitored = connection.wrap_tool(lambda: marker.write_text("unauthorized write", encoding="utf-8"),
            tool_name="write_file", task_type="rag", model_version=version,
            application_version="documentation-service-v1", environment="testbed-fault")
        blocked = False
        try:
            monitored()
        except PolicyViolation:
            blocked = True
        if blocked and not marker.exists():
            for alert_id in connection.last_receipt["alert_ids"]:
                connection.acknowledge_action(alert_id=alert_id, action_type="tool_denied", evidence_id=connection.last_receipt["event_id"])
        return {"blocked": blocked, "side_effect_occurred": marker.exists(), "receipt": connection.last_receipt}

    return api
