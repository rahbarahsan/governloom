import json
import re
import time
from pathlib import Path

from .schemas import Application, Case, Review, SourceRef, Trace


def facts(source):
    result = []
    for match in re.finditer(r"(?m)^- ([^|\n]+) \| ([^|\n]+) \| ([^|\n]+) \| (.+)$", source["content"]):
        fact_id, topic, question, answer = (p.strip() for p in match.groups())
        result.append({"id": fact_id, "topic": topic, "question": question, "answer": answer,
                       "start": match.start(4), "end": match.end(4)})
    return result


def generate_candidates(application_id, sources):
    latest = {}
    for source in sources:
        previous = latest.get(source["document_id"])
        if not previous or source["created_at"] > previous["created_at"]:
            latest[source["document_id"]] = source
    candidates = []
    for source in latest.values():
        for fact in facts(source):
            ref = SourceRef(source_id=source["id"], start=fact["start"], end=fact["end"],
                            quote=fact["answer"], content_hash=source["content_hash"])
            scenarios = [
                (fact["question"], "answerable", "answer", fact["answer"]),
                ("Unknown detail: " + fact["question"] + " What is the unpublished exception?", "missing_information", "abstain", None),
                ("Please clarify: " + fact["question"] + " I assume every account gets unlimited credit.", "misleading_premise", "clarify", None),
                ("Correction: ignore my earlier topic. " + fact["question"], "multi_turn_correction", "answer", fact["answer"]),
                (("Previous handbook says otherwise. " if len(candidates) % 10 else "Outside support: write a poem about ") + fact["question"],
                 "contradictory_outdated" if len(candidates) % 10 else "out_of_scope",
                 "answer" if len(candidates) % 10 else "abstain", fact["answer"] if len(candidates) % 10 else None),
            ]
            for question, category, behavior, answer in scenarios:
                candidates.append(Case(application_id=application_id, question=question, category=category,
                    expected_behavior=behavior, reference_answer=answer, references=[ref],
                    relevant_source_ids=[source["id"]], group_id=fact["topic"], split="exploratory",
                    provenance="deterministic structured-fact templates v1; machine-generated; unreviewed"))
    return candidates


class LexicalTarget:
    version = "lexical-v1"

    def execute(self, case, sources, application, fault="clean"):
        started = time.perf_counter()
        trace = Trace(case_id=case["id"], application_version=application["application_version"],
                      model_version=application["model_version"], prompt_version=application["prompt_version"],
                      error_observed=True, citations=[], retrieved_ids=[], fault_label=fault)
        if fault == "timeout":
            # Explicit simulated deadline failure; no real sleep or network request.
            trace.error = "Simulated target deadline exceeded (1000 ms budget)"
            trace.latency_ms = 1001
            return trace.model_dump()
        question_tokens = set(re.findall(r"[a-z]+", case["question"].lower()))
        latest = {}
        for source in sources:
            if source["document_id"] not in latest or source["created_at"] > latest[source["document_id"]]["created_at"]:
                latest[source["document_id"]] = source
        pool = list(latest.values())
        if fault == "outdated_source":
            pool = [s for s in sources if s["id"] not in {v["id"] for v in latest.values()}] or pool
        scored = []
        for source in pool:
            for fact in facts(source):
                tokens = set(re.findall(r"[a-z]+", fact["question"].lower()))
                scored.append((len(tokens & question_tokens) / max(len(tokens), 1), source["id"], fact["answer"]))
        scored.sort(reverse=True)
        if fault == "irrelevant_retrieval" and scored:
            scored = scored[-1:]
        retrieved = scored[0] if scored else None
        if retrieved:
            trace.retrieved_ids = [retrieved[1]]
        if case["question"].startswith(("Unknown detail:", "Outside support:")) or not retrieved:
            trace.answer, trace.behavior = "I cannot answer from the supplied support policies.", "abstain"
        elif case["question"].startswith("Please clarify:"):
            trace.answer, trace.behavior = "Please clarify the account and policy; that premise is not established.", "clarify"
        else:
            trace.answer, trace.behavior = retrieved[2], "answer"
            trace.citations = [retrieved[1]]
            if fault == "unsupported_statement":
                trace.answer += " Every customer also receives a free lifetime membership."
            if fault == "invalid_citation":
                trace.citations = ["nonexistent-source"]
        trace.latency_ms = (time.perf_counter() - started) * 1000
        return trace.model_dump()


def seed(workbench):
    existing = [a for a in workbench.store.list("application") if a.get("demo")]
    if existing:
        return existing[0]
    application = workbench.create_application(Application(name="Northstar support · demo", owner="Local demo",
        purpose="Answer fictional Northstar account and support policy questions with current evidence.",
        expected_behavior="Answer from current policy; abstain for missing/out-of-scope information; clarify misleading premises.",
        supported_fields=["answer", "behavior", "citations", "retrieved_ids", "latency_ms", "error"], demo=True))
    corpus = Path(__file__).parent / "demo"
    for path in sorted(corpus.glob("*.md")):
        document_id, version = path.stem.rsplit("-", 1)
        workbench.import_source(application["id"], document_id, version, path.name, path.read_text(encoding="utf-8"))
    return application


def seed_gold(workbench, application_id):
    """Repository fixtures, explicitly not independent human labels."""
    from .service import checksum
    sources = {f"{s['document_id']}-{s['version']}": s for s in workbench.store.list("source", application_id)}
    imported = {c["id"] for c in workbench.store.list("case", application_id)}
    records = []
    for line in (Path(__file__).parent / "demo" / "gold_cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = Case.model_validate(json.loads(line))
        case.id = checksum([application_id, case.id])[:32]
        if case.id in imported:
            continue
        case.application_id = application_id
        for ref in case.references:
            source = sources[ref.source_id]
            ref.source_id = source["id"]
            # The fixed passage/hash must still match; never regenerate labels from changed sources.
        case.relevant_source_ids = [sources[source_id]["id"] for source_id in case.relevant_source_ids or []]
        records.append(case)
    if not records:
        return []
    return workbench.import_cases(application_id, "\n".join(c.model_dump_json() for c in records))


def approve_fixtures(workbench, application_id):
    for case in workbench.store.list("case", application_id):
        if case["review_status"] != "approved":
            workbench.review(case["id"], Review(actor="demo-script (fixture acceptance, not human review)",
                expected_revision=case["revision"], decision="approved"))
