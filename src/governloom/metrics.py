from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Metric:
    id: str
    purpose: str
    required_inputs: tuple[str, ...]
    method: str
    limitations: str
    direction: str = "higher"
    threshold: float | None = 1
    evaluator_version: str = "deterministic-v1"


METRICS = {
    m.id: m for m in [
        Metric("task_success", "Expected response behavior", ("behavior", "expected_behavior"), "Exact behavior match", "Does not establish factual correctness."),
        Metric("reference_agreement", "Agreement with reviewed literal answer", ("answer", "reference_answer"), "Case-insensitive normalized reference substring", "Only literal agreement; misses unsupported additions and semantic paraphrases."),
        Metric("citation_existence", "Answer includes a citation", ("citations",), "At least one citation for answer cases", "A citation alone proves neither correctness nor grounding."),
        Metric("citation_consistency", "Citations identify expected versioned evidence", ("citations", "references"), "All cited source IDs exist in the snapshot and match reviewed references", "Document-level consistency only; does not assess claim entailment."),
        Metric("retrieval_recall", "Coverage of judged relevant documents", ("retrieved_ids", "relevant_source_ids"), "Relevant retrieved / all relevant", "Requires explicit relevance judgments; document-level measurement."),
        Metric("retrieval_precision", "Fraction of retrieval judged relevant", ("retrieved_ids", "relevant_source_ids"), "Relevant retrieved / all retrieved", "Unjudged documents count as non-relevant only with supplied exhaustive judgments."),
        Metric("latency", "Observed target latency in milliseconds", ("latency_ms",), "Supplied or measured elapsed milliseconds", "Missing telemetry is unavailable; local demo latency is not production performance.", "lower", 1000),
        Metric("errors", "Observed target error", ("error_observed",), "1 if target reported an error, else 0", "Only explicitly observed errors.", "lower", 0),
        Metric("token_usage", "Reported input plus output tokens", ("input_tokens", "output_tokens"), "Sum of supplied token telemetry", "No tokenizer estimate is substituted.", "lower", None),
        Metric("cost", "Cost from supplied usage and configured prices", ("input_tokens", "output_tokens", "prices"), "Usage multiplied by price per million", "Unavailable without both token counts and configured prices.", "lower", None),
        Metric("semantic_grounding", "Semantic answer support", ("judge",), "Unavailable model-backed estimate", "Needs configured judge, rubric, and independent calibration; no paid adapter shipped.", evaluator_version="unavailable-v1"),
    ]
}


def recommend(application: dict, cases: list[dict], traces: list[dict] | None = None, prices=False):
    supported = set(application["supported_fields"])
    if traces is not None:
        supported = {field for trace in traces for field, value in trace.items() if value is not None}
    available = supported | {"expected_behavior"}
    if "error" in supported:
        available.add("error_observed")
    for field in ("reference_answer", "references", "relevant_source_ids"):
        if any(case.get(field) for case in cases):
            available.add(field)
    if prices:
        available.add("prices")
    answer_profile = bool(application.get("expected_behavior"))
    output = []
    for metric in METRICS.values():
        missing = sorted(set(metric.required_inputs) - available)
        suggested = metric.id not in ("token_usage", "cost", "semantic_grounding") and answer_profile
        state = "unavailable" if missing else "enabled" if suggested else "suggested"
        output.append({**asdict(metric), "state": state, "missing_inputs": missing,
                       "reason": f"Profile: {application['expected_behavior']}. " + (
                           "Required inputs are present for at least one case; per-case coverage is checked during evaluation."
                           if not missing else "Missing prerequisites: " + ", ".join(missing))})
    return output


def evaluate(case: dict, trace: dict | None, sources: list[dict], metrics: list[dict], prices: dict):
    results = []
    for definition in metrics:
        metric_id = definition["id"]
        row = {"metric": metric_id, "evaluator_version": definition["evaluator_version"],
               "status": "insufficient_evidence", "value": None, "explanation": "", "evidence": [], "failure_tags": []}
        try:
            if not trace:
                row["explanation"] = "No trace matched this frozen case ID."
            elif metric_id == "semantic_grounding":
                row["explanation"] = "No configured and calibrated semantic judge."
            elif metric_id in ("citation_existence", "citation_consistency", "reference_agreement") and case["expected_behavior"] != "answer":
                row.update(status="skipped", explanation="This case expects clarification or abstention.")
            else:
                values = {**case, **trace}
                values["references"] = case["references"]
                values["prices"] = prices if all(prices.get(k) is not None for k in ("input", "output")) else None
                missing = [k for k in definition["required_inputs"] if values.get(k) is None or
                           (k in ("references", "relevant_source_ids", "reference_answer") and not values.get(k)) or
                           (k == "error_observed" and not values.get(k))]
                if missing:
                    row["explanation"] = "Missing prerequisites: " + ", ".join(missing)
                else:
                    value, evidence = score(metric_id, case, trace, sources, prices)
                    threshold = definition["threshold"]
                    passed = threshold is None or (value >= threshold if definition["direction"] == "higher" else value <= threshold)
                    row.update(value=value, status="passed" if passed else "failed", evidence=evidence,
                               explanation=definition["method"], failure_tags=[] if passed else [metric_id])
        except Exception as exc:
            row.update(status="evaluator_error", explanation=f"{type(exc).__name__}: {exc}")
        results.append(row)
    return results


def score(metric_id, case, trace, sources, prices):
    citations = trace.get("citations") or []
    retrieved = set(trace.get("retrieved_ids") or [])
    relevant = set(case.get("relevant_source_ids") or [])
    if metric_id == "task_success":
        return float(trace["behavior"] == case["expected_behavior"]), [trace["behavior"], case["expected_behavior"]]
    if metric_id == "reference_agreement":
        normalize = lambda s: " ".join(s.lower().split())
        return float(normalize(case["reference_answer"]) in normalize(trace["answer"])), [trace["answer"], case["reference_answer"]]
    if metric_id == "citation_existence":
        return float(bool(citations)), citations
    if metric_id == "citation_consistency":
        expected = {r["source_id"] for r in case["references"]}
        valid = {s["id"] for s in sources}
        return float(bool(citations) and set(citations) <= valid & expected), citations
    if metric_id == "retrieval_recall":
        return len(retrieved & relevant) / len(relevant), sorted(retrieved)
    if metric_id == "retrieval_precision":
        return len(retrieved & relevant) / len(retrieved) if retrieved else 0, sorted(retrieved)
    if metric_id == "latency":
        return trace["latency_ms"], ["Observed milliseconds"]
    if metric_id == "errors":
        return float(bool(trace["error"])), [trace["error"] or "No observed error"]
    if metric_id == "token_usage":
        return trace["input_tokens"] + trace["output_tokens"], ["Supplied telemetry"]
    if metric_id == "cost":
        return (trace["input_tokens"] * prices["input"] + trace["output_tokens"] * prices["output"]) / 1_000_000, [prices]
    raise ValueError(f"Unknown evaluator: {metric_id}")


def summarize(results: list[dict], selected_count: int):
    summary = {}
    for result in results:
        for metric in result["metrics"]:
            bucket = summary.setdefault(metric["metric"], {s: 0 for s in (
                "passed", "failed", "skipped", "insufficient_evidence", "evaluator_error")})
            bucket[metric["status"]] += 1
    for bucket in summary.values():
        bucket["scored"] = bucket["passed"] + bucket["failed"]
        bucket["selected"] = selected_count
        bucket["finalized"] = len(results)
        bucket["pending"] = selected_count - len(results)
        bucket["pass_rate"] = bucket["passed"] / bucket["scored"] if bucket["scored"] else None
    return summary
