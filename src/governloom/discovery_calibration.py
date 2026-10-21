"""Deterministic evaluation recipes on frozen, confirmed application evidence."""
import math
from datetime import datetime, timezone

from .calibration import calibrate_threshold, evaluate_threshold
from .service import checksum


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
        if len(value) == 10:  # A date is a calendar period, not a fabricated receipt time.
            return moment.replace(tzinfo=timezone.utc)
        return moment if moment.tzinfo else None
    except ValueError:
        return None


def partition(rows, task):
    """Preserve provided splits or freeze a chronological/group-disjoint split."""
    supplied = [row["values"].get("split") for row in rows]
    if any(value is not None for value in supplied):
        if any(value not in ("calibration", "held_out") for value in supplied):
            raise ValueError("Every row needs calibration/held_out when a split field is supplied")
        for row, split in zip(rows, supplied):
            row["split"] = split
        method = "provided split, checked for group overlap and forecast chronology"
    elif task == "forecasting":
        if any(timestamp(row["values"].get("timestamp")) is None for row in rows):
            raise ValueError("Forecast calibration needs dates or timezone-aware timestamps")
        rows.sort(key=lambda row: timestamp(row["values"]["timestamp"]))
        boundary = len(rows) * 2 // 3
        for index, row in enumerate(rows):
            row["split"] = "calibration" if index < boundary else "held_out"
        method = "oldest two thirds calibration; newest third held out"
    else:
        groups = sorted({str(row["values"].get("group") or row["case_id"]) for row in rows}, key=checksum)
        calibration_groups = set(groups[:len(groups) * 2 // 3])
        for row in rows:
            row["split"] = "calibration" if str(row["values"].get("group") or row["case_id"]) in calibration_groups else "held_out"
        method = "deterministic hash split by supplied group, otherwise exact case identity"
    calibration = [row for row in rows if row["split"] == "calibration"]
    held = [row for row in rows if row["split"] == "held_out"]
    if not calibration or not held:
        raise ValueError("Separate nonempty calibration and held-out sets are required")
    if task == "forecasting":
        times = [timestamp(row["values"].get("timestamp")) for row in rows]
        if any(moment is None for moment in times) or len(set(times)) != len(times):
            raise ValueError("One numeric forecast series needs unique dates; separate horizons/series into different discoveries")
        if max(timestamp(row["values"]["timestamp"]) for row in calibration) >= min(timestamp(row["values"]["timestamp"]) for row in held):
            raise ValueError("Forecast calibration must strictly precede held-out cases")
    # Repeated series IDs are allowed across time for forecasting, not duplicate observations.
    else:
        left = {row["values"]["group"] for row in calibration if row["values"].get("group") is not None}
        right = {row["values"]["group"] for row in held if row["values"].get("group") is not None}
        if left & right:
            raise ValueError("A group cannot appear in calibration and held-out data")
    return calibration, held, method


def quantile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def prepare(discovery, confirmation, fraction):
    mappings = confirmation["mappings"]
    rows = [{"case_id": checksum([index, sha])[:24], "source_index": index, "source_sha256": sha,
             "values": {role: discovery["trace_columns"][path][index] for role, path in mappings.items()}}
            for index, sha in enumerate(discovery["trace_hashes"])]
    # Exact duplicate selected observations must not inflate denominators or cross splits.
    unique, duplicate_count = {}, 0
    for row in rows:
        identity = checksum({key: value for key, value in row["values"].items() if key != "split"})
        if identity in unique:
            duplicate_count += 1
            if unique[identity]["values"].get("split") != row["values"].get("split"):
                raise ValueError("Exact duplicate observations cross declared splits")
        else:
            unique[identity] = row
    rows = list(unique.values())
    task = confirmation["task_type"]
    metrics, rules, gaps = [], [], []
    limitations = ["Proposals are empirical observation baselines, not acceptable-harm decisions or safety guarantees.",
                  "Trace fields and labels were supplied by the application; owner confirmation is not independent label review.",
                  "Near-duplicate/semantic groups are not inferred automatically; supply group IDs to prevent group leakage.",
                  "Historical traffic may omit important deployment groups and rare failures."]
    try:
        calibration, held, split_method = partition(rows, task)
    except ValueError as error:
        calibration, held, split_method = [], [], "unavailable"
        gaps.append(str(error))
    scope = {}
    for role in ("model_version", "application_version", "environment"):
        versions = {row["values"].get(role) for row in rows}
        if len(versions) == 1 and None not in versions:
            scope[role] = next(iter(versions))
        elif role in mappings:
            gaps.append(f"Mixed or missing {role}; collect a single deployment version/scope before activation")
    if "model_version" not in scope or "application_version" not in scope:
        gaps.append("Map a single model_version and application_version to bind the proposed policy")
    def rule(identifier, name, metric, threshold, comparator="gt", phase="output"):
        return {"id": identifier, "name": name, "detector": "metric_threshold", "phase": phase,
                "task_type": task, "metric": metric, "threshold": threshold, "comparator": comparator,
                "severity": "medium", "action": "flag", **scope,
                "mitigation": "Inspect the linked evidence and actual outcomes; select a response after review."}
    def numeric_rows(items, fields):
        return [row for row in items if all(number(row["values"].get(field)) for field in fields)]
    if task == "forecasting":
        cal = numeric_rows(calibration, ("prediction", "actual"))
        evaluation = numeric_rows(held, ("prediction", "actual"))
        missing = len(rows) - len(cal) - len(evaluation) if calibration else len(rows)
        if not confirmation["outcome_meaning_confirmed"]:
            gaps.append("Confirm that actual values are observed target outcomes, not model estimates or substituted missing values")
        if len(cal) >= 20 and len(evaluation) >= 5:
            residuals = [abs(row["values"]["prediction"] - row["values"]["actual"]) for row in cal]
            threshold = quantile(residuals, 1-fraction)
            def report(items):
                errors = [row["values"]["prediction"] - row["values"]["actual"] for row in items]
                return {"cases": len(errors), "mae": sum(abs(error) for error in errors)/len(errors),
                        "rmse": math.sqrt(sum(error*error for error in errors)/len(errors)),
                        "bias_prediction_minus_actual": sum(errors)/len(errors),
                        "exceedances": sum(abs(error) > threshold for error in errors)}
            metrics.append({"name": "Forecast outcome error", "status": "available", "threshold": threshold,
                "calibration": report(cal), "held_out": report(evaluation), "missing_actual_or_prediction": missing,
                "meaning": "Residual exceedance is not an independently labeled harmful forecast",
                "selection": "Calibration-only empirical residual quantile", "nominal_probability_valid": False})
            rules.append(rule("discovered_residual", "Forecast error above historical baseline", "absolute_error", threshold, phase="outcome"))
        else:
            gaps.append("Forecast errors need at least 20 numeric calibration pairs and five held-out pairs")
        metrics.append({"name": "Outcome deadline coverage", "status": "requires_instrumentation",
                        "reason": "Choose a real feedback deadline and emit outcome_due_at plus related_event_id; no deadline is invented from historical dates"})
        limitations.append("Serial dependence and revised snapshots invalidate nominal false-alert/coverage claims. This is a monthly residual baseline, not block calibration.")
    elif task in ("classification", "vision"):
        def labeled(items):
            return [row for row in items if number(row["values"].get("confidence")) and 0 <= row["values"]["confidence"] <= 1
                    and row["values"].get("predicted_label") is not None and row["values"].get("actual_label") is not None]
        cal, evaluation = labeled(calibration), labeled(held)
        if not confirmation["outcome_meaning_confirmed"]:
            gaps.append("Confirm the meaning and provenance of reference labels before error-based calibration")
        if cal and len(evaluation) >= 5:
            examples = lambda items: [{"value": row["values"]["confidence"], "risk": row["values"]["predicted_label"] != row["values"]["actual_label"]} for row in items]
            try:
                selected = calibrate_threshold(examples(cal), false_positive_budget=fraction)
                metrics.append({"name": "Confidence error gate", "status": "available", **selected,
                    "held_out": evaluate_threshold(examples(evaluation), selected["threshold"], "low"),
                    "missing_confidence_or_label": len(rows)-len(cal)-len(evaluation)})
                rules.append(rule("discovered_confidence", "Low classification confidence", "confidence", selected["threshold"], "lt"))
            except ValueError as error:
                gaps.append(str(error))
        else:
            gaps.append("Confidence calibration needs labeled calibration examples and at least five labeled held-out examples")
        limitations.append("Confidence can miss confident errors; labels and deployment groups require domain validation.")
    elif task == "rag":
        def citation_report(items):
            complete = [row for row in items if isinstance(row["values"].get("citations"), list) and isinstance(row["values"].get("source_ids"), list)]
            return {"cases": len(items), "available": len(complete), "unavailable": len(items)-len(complete),
                    "flagged": sum(not row["values"]["citations"] or bool(set(row["values"]["citations"]) - set(row["values"]["source_ids"])) for row in complete)}
        left, right = citation_report(calibration), citation_report(held)
        metrics.append({"name": "Citation identity", "status": "available" if left["available"] and right["available"] else "unavailable", "calibration": left, "held_out": right,
            "meaning": "Checks source membership only; no semantic correctness, retrieval recall or hallucination accuracy is inferred"})
        if left["available"] and right["available"]:
            rules.append({"id": "discovered_citations", "name": "Missing or unknown citation", "detector": "citation_integrity",
                "phase": "output", "task_type": "rag", "action": "flag", "severity": "medium", **scope,
                "mitigation": "Inspect retrieved passages and the answer before selecting a response."})
        else:
            gaps.append("Citation checks need citations and retrieved source IDs in both splits")
        metrics.extend([{"name": "Claim support", "status": "unavailable", "reason": "Requires frozen source passages, a calibrated judge and reviewed claim labels"},
                        {"name": "Retrieval recall", "status": "unavailable", "reason": "Requires relevant-document judgments; retrieved IDs alone are insufficient"}])
    else:
        gaps.append("No quality policy can be inferred for this task; correct the task or collect task-specific outcome evidence")
    if not rules:
        gaps.append("No quality rule is ready for activation")
    dataset = {"provenance": "selected application observations; labels/outcomes owner-confirmed, not independently reviewed",
        "split_method": split_method, "duplicates_removed": duplicate_count, "cases": rows,
        "calibration_cases": len(calibration), "held_out_cases": len(held),
        "synthetic_scenarios": [dict(item, label_status="model_generated_unreviewed_not_evaluation_truth") for item in (discovery.get("semantic") or {}).get("scenarios", [])]}
    dataset["sha256"] = checksum(dataset)
    policy = {"name": "Discovered observation baseline", "rules": rules,
              "actor": confirmation["actor"], "rationale": "Reviewed discovery evidence; empirical baseline, not a safety certification",
              "outcome_deadline_action": "flag"} if rules else None
    return {"status": "needs_evidence" if gaps else "ready", "metrics": metrics, "gaps": gaps,
            "limitations": limitations, "dataset": dataset, "policy": policy,
            "instrumentation": {"task_type": task, "fields": mappings, "scope": scope,
                "recipe": "Emit mapped fields via the public hook with stable event IDs. Forecast actuals must link to their prediction. Observation activation never withholds outputs."},
            "unresolved_business_decisions": ["Whether the empirical threshold reflects acceptable harm", "Who investigates alerts and what response is appropriate"]}
