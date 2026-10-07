import hashlib
import json
import random
from pathlib import Path

from sqlalchemy import select, update

from .metrics import METRICS, recommend, summarize
from .schemas import Application, Case, Review, RunRequest, Source, SourceRef, Trace, now, uid
from .storage import Entity, Job, Result, Store


def checksum(value) -> str:
    raw = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def jsonl(text: str, model):
    records = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate(json.loads(line)))
        except Exception as exc:
            raise ValueError(f"JSONL line {line_number}: {exc}") from exc
    if not records:
        raise ValueError("Import contains no records")
    if len(records) > 2000:
        raise ValueError("Import limit is 2000 records")
    return records


class Workbench:
    def __init__(self, store: Store):
        self.store = store

    def create_application(self, application: Application):
        return self.store.put("application", application.model_dump(), application.id)

    def import_source(self, application_id, document_id, version, filename, content):
        self.store.get("application", application_id)
        if Path(filename).suffix.lower() not in (".md", ".txt"):
            raise ValueError("Only UTF-8 .md and .txt sources are supported")
        if not content.strip() or len(content.encode("utf-8")) > 2_000_000:
            raise ValueError("Source must contain text and be at most 2 MB")
        source = Source(application_id=application_id, document_id=document_id, version=version,
                        filename=filename, content=content, content_hash=checksum(content))
        # Immutable source identity is derived from application/document/version.
        source.id = checksum([application_id, document_id, version])[:32]
        existing = [s for s in self.store.list("source", application_id) if s["id"] == source.id]
        if existing:
            if existing[0]["content_hash"] != source.content_hash:
                raise ValueError("Document version already exists with different content; import a new version")
            return existing[0]
        return self.store.put("source", source.model_dump(), application_id)

    def validate_case(self, case: Case, sources: list[dict]):
        if not case.question.strip():
            raise ValueError("Case question cannot be blank")
        by_id = {source["id"]: source for source in sources}
        for ref in case.references:
            source = by_id.get(ref.source_id)
            if not source or source["content_hash"] != ref.content_hash or ref.end > len(source["content"]) or source["content"][ref.start:ref.end] != ref.quote:
                raise ValueError("Invalid source reference: ID, hash, or passage range does not match")
        if case.relevant_source_ids is not None and not set(case.relevant_source_ids) <= by_id.keys():
            raise ValueError("Relevance judgment refers to unknown sources")
        if case.expected_behavior == "answer" and not (case.reference_answer or "").strip():
            raise ValueError("Answer cases require a reference answer")
        if case.review_status == "approved" and not case.references:
            raise ValueError("Approved cases require source evidence, including boundary scenarios")

    def import_cases(self, application_id, text):
        self.store.get("application", application_id)
        records = jsonl(text, Case)
        sources = self.store.list("source", application_id)
        for case in records:
            if case.application_id != application_id:
                raise ValueError("Case application does not match import destination")
            case.review_status = "unreviewed"
            case.revision = 1
            self.validate_case(case, sources)
        existing = self.store.list("case", application_id)
        self.validate_groups(existing + [c.model_dump() for c in records])
        fingerprints = {self.case_fingerprint(c) for c in existing}
        output = []
        with self.store.session() as session:
            for case in records:
                fingerprint = self.case_fingerprint(case.model_dump())
                if fingerprint in fingerprints:
                    continue
                if session.get(Entity, case.id):
                    raise ValueError("Case ID already exists")
                fingerprints.add(fingerprint)
                payload = case.model_dump()
                session.add(Entity(id=case.id, kind="case", application_id=application_id, payload=payload))
                self.audit(session, application_id, case.id, 1, "import", "importer", payload)
                output.append(payload)
        return output

    @staticmethod
    def case_fingerprint(case):
        return checksum([" ".join(case["question"].lower().split()), case["expected_behavior"], case["reference_answer"]])

    @staticmethod
    def validate_groups(cases):
        groups = {}
        for case in cases:
            if case["group_id"] in groups and groups[case["group_id"]] != case["split"]:
                raise ValueError("A source/topic/scenario group cannot cross dataset splits")
            groups[case["group_id"]] = case["split"]

    def generate(self, application_id):
        from .demo import generate_candidates
        sources = self.store.list("source", application_id)
        candidates = generate_candidates(application_id, sources)
        if not candidates:
            raise ValueError("No structured facts found. Use '- fact_id | topic | question | answer' or import manual cases.")
        return self.import_cases(application_id, "\n".join(c.model_dump_json() for c in candidates))

    @staticmethod
    def audit(session, application_id, object_id, revision, action, actor, value):
        event = {"schema_version": 1, "id": uid(), "object_id": object_id, "revision": revision, "action": action,
                 "actor": actor, "created_at": now(), "value": value}
        session.add(Entity(id=event["id"], kind="review_event", application_id=application_id, payload=event))

    def review(self, case_id, review: Review):
        if not review.actor.strip():
            raise ValueError("Reviewer actor is required")
        old = self.store.get("case", case_id)
        if old["revision"] != review.expected_revision:
            raise ValueError("Stale case revision; reload before reviewing")
        edits = review.model_dump()
        revised = {**old, **{k: edits[k] for k in ("question", "reference_answer", "expected_behavior") if k in review.model_fields_set},
                   "review_status": review.decision, "revision": old["revision"] + 1}
        case = Case.model_validate(revised)
        self.validate_case(case, self.store.list("source", case.application_id))
        siblings = [c for c in self.store.list("case", case.application_id) if c["id"] != case.id]
        if any(self.case_fingerprint(c) == self.case_fingerprint(revised) for c in siblings):
            raise ValueError("Edit would duplicate another case")
        with self.store.session() as session:
            changed = session.execute(update(Entity).where(Entity.id == case_id, Entity.payload == old).values(payload=revised))
            if changed.rowcount != 1:
                raise ValueError("Concurrent review; reload before retrying")
            self.audit(session, case.application_id, case_id, case.revision, "review", review.actor, revised)
        return revised

    def publish(self, application_id, actor):
        if not actor.strip():
            raise ValueError("Publisher actor is required")
        self.store.get("application", application_id)
        cases = sorted([c for c in self.store.list("case", application_id) if c["review_status"] == "approved"], key=lambda c: c["id"])
        if not cases:
            raise ValueError("Approve at least one case before publishing")
        sources = self.store.list("source", application_id)
        for case in cases:
            self.validate_case(Case.model_validate(case), sources)
        self.validate_groups(cases)
        # Keep all imported source versions so outdated retrieval remains inspectable.
        snapshot = {"schema_version": 1, "application_id": application_id, "cases": cases, "sources": sources}
        dataset = {**snapshot, "id": uid(), "checksum": checksum(snapshot), "created_at": now(), "actor": actor,
                   "version": 0}
        with self.store.session() as session:
            # Serialize version assignment even if two browser requests publish together.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            dataset["version"] = len(list(session.scalars(select(Entity.id).where(
                Entity.kind == "dataset", Entity.application_id == application_id)))) + 1
            session.add(Entity(id=dataset["id"], kind="dataset", application_id=application_id, payload=dataset))
            self.audit(session, application_id, dataset["id"], dataset["version"], "publish", actor, {"checksum": dataset["checksum"]})
        return dataset

    def import_traces(self, application_id, text):
        application = self.store.get("application", application_id)
        traces = jsonl(text, Trace)
        case_ids = {c["id"] for c in self.store.list("case", application_id)}
        if len({t.case_id for t in traces}) != len(traces):
            raise ValueError("One trace per case per import batch is required")
        if any(t.case_id not in case_ids for t in traces):
            raise ValueError("Trace case_id does not belong to this application")
        if any(any(getattr(t, field) != application[field] for field in ("application_version", "model_version", "prompt_version")) for t in traces):
            raise ValueError("Trace application/model/prompt versions must match the application record")
        batch = {"id": uid(), "schema_version": 1, "application_id": application_id, "created_at": now(),
                 "traces": [t.model_dump() for t in traces]}
        self.store.put("trace_batch", batch, application_id)
        return batch

    def queue(self, request: RunRequest, trace_batch_id=None):
        dataset = self.store.get("dataset", request.dataset_id)
        application = self.store.get("application", dataset["application_id"])
        cases = [c for c in dataset["cases"] if request.split == "all" or c["split"] == request.split]
        if not cases:
            raise ValueError("Selected split has no approved cases")
        # Deterministic seeded selection, then stable execution order.
        cases = sorted(cases, key=lambda c: c["id"])
        cases = random.Random(request.sampling_seed).sample(cases, min(len(cases), request.sample_size))
        cases.sort(key=lambda c: c["id"])
        if len(cases) > request.max_requests:
            raise ValueError("Selected sample exceeds max_requests")
        traces = None
        if request.target == "imported":
            if not trace_batch_id:
                raise ValueError("Imported target requires a trace batch")
            batch = self.store.get("trace_batch", trace_batch_id)
            if batch["application_id"] != application["id"]:
                raise ValueError("Trace batch belongs to another application")
            traces = batch["traces"]
        prices = {"input": request.input_price_per_million, "output": request.output_price_per_million}
        recommendations = recommend(application, cases, traces, all(v is not None for v in prices.values()))
        selected = request.metrics if request.metrics is not None else list(METRICS)
        if not selected or len(set(selected)) != len(selected) or any(m not in METRICS for m in selected):
            raise ValueError("Select unique known metrics")
        run = {"id": uid(), "request": request.model_dump(), "dataset": dataset, "application": application,
               "cases": cases, "traces": traces, "trace_batch_id": trace_batch_id,
               "metrics": [m for m in recommendations if m["id"] in selected], "prices": prices,
               "target_version": "lexical-v1" if traces is None else "imported-traces-v1",
               "provider": {"enabled": False, "requests": 0, "spend": 0}, "schema_version": 1}
        with self.store.session() as session:
            session.add(Job(id=run["id"], application_id=application["id"], status="queued", payload=run,
                            created_at=now(), updated_at=now(), total=len(cases), completed=0, lease_until=0, cancel_requested=0))
        return self.run(run["id"])

    def run(self, run_id, include_snapshot=True):
        with self.store.session() as session:
            job = session.get(Job, run_id)
            if not job:
                raise ValueError("Unknown run")
            results = [r.payload for r in session.scalars(select(Result).where(Result.run_id == run_id).order_by(Result.case_id))]
            data = {"schema_version": 1, "id": job.id, "status": job.status, "completed": job.completed, "total": job.total,
                    "cancel_requested": bool(job.cancel_requested), "created_at": job.created_at, "updated_at": job.updated_at,
                    "error": job.error, "request": job.payload["request"], "application_id": job.application_id,
                    "dataset_checksum": job.payload["dataset"]["checksum"], "results": results,
                    "summary": summarize(results, job.total)}
            if include_snapshot:
                data["snapshot"] = job.payload
            return data

    def runs(self, application_id=None):
        with self.store.session() as session:
            query = select(Job).order_by(Job.created_at.desc())
            if application_id:
                query = query.where(Job.application_id == application_id)
            ids = [j.id for j in session.scalars(query)]
        return [self.run(run_id, False) for run_id in ids]

    def cancel(self, run_id):
        with self.store.session() as session:
            job = session.get(Job, run_id)
            if not job:
                raise ValueError("Unknown run")
            if job.status not in ("completed", "cancelled", "failed"):
                job.cancel_requested = 1
                job.updated_at = now()
                if job.status == "queued":
                    job.status = "cancelled"
        return self.run(run_id)

    def compare(self, left_id, right_id):
        left, right = self.run(left_id), self.run(right_id)
        ls, rs = left["snapshot"], right["snapshot"]
        reasons = []
        if left["application_id"] != right["application_id"]:
            reasons.append("Different applications")
        if left["dataset_checksum"] != right["dataset_checksum"]:
            reasons.append("Different dataset snapshots; changed cases are excluded")
        if ls["metrics"] != rs["metrics"] or ls["prices"] != rs["prices"]:
            reasons.append("Different evaluator definitions, thresholds, input availability, or prices")
        if left["status"] != "completed" or right["status"] != "completed":
            reasons.append("One or both runs are incomplete")
        lcases, rcases = ({c["id"]: checksum(c) for c in snapshot["cases"]} for snapshot in (ls, rs))
        matched = {cid for cid in lcases.keys() & rcases.keys() if lcases[cid] == rcases[cid]}
        lresults, rresults = ({r["case_id"]: r for r in run["results"]} for run in (left, right))
        matched &= lresults.keys() & rresults.keys()
        if set(lcases) != matched or set(rcases) != matched:
            reasons.append("Only matched unchanged finalized case IDs can be compared")
        definitions_left = {m["id"]: m for m in ls["metrics"]}
        definitions_right = {m["id"]: m for m in rs["metrics"]}
        changes = []
        for cid in sorted(matched):
            lm, rm = ({m["metric"]: m for m in results[cid]["metrics"]} for results in (lresults, rresults))
            for metric_id in lm.keys() & rm.keys():
                if definitions_left[metric_id] != definitions_right[metric_id] or ls["prices"] != rs["prices"]:
                    continue
                if (lm[metric_id]["status"], lm[metric_id]["value"]) != (rm[metric_id]["status"], rm[metric_id]["value"]):
                    changes.append({"case_id": cid, "metric": metric_id, "left": lm[metric_id], "right": rm[metric_id]})
        return {"left": left_id, "right": right_id, "compatible": not reasons, "reasons": reasons,
                "matched_cases": len(matched), "left_cases": len(lcases), "right_cases": len(rcases), "changes": changes}
