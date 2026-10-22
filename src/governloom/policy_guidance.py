"""Compose trusted controls and explicit measurements on a frozen discovery dataset."""
import math
from collections import Counter

from .discovery_calibration import number, quantile
from .policy_catalogue import catalogue

EVALUATOR = "policy-metrics-v1"
RULE_CONTROLS = {"discovered_residual": "forecast.error", "discovered_confidence": "classification.confidence",
                 "discovered_citations": "rag.citations"}


def guide(plan, confirmation, request):
    frozen = catalogue()
    rows = plan["dataset"]["cases"]
    mappings = confirmation["mappings"]
    task = confirmation["task_type"]
    capabilities = {"common"}
    if task in ("vision", "classification"):
        capabilities.add("classification")
    elif task in ("forecasting", "rag"):
        capabilities.add(task)
    if "citations" in mappings or "source_ids" in mappings:
        capabilities.add("rag")
    if "tool_name" in mappings or confirmation.get("allowed_tools") is not None:
        capabilities.add("tools")
    results = []

    def measurement(metric, value, denominator, total, split="all", *, label=None, reason=None, unit="ratio"):
        results.append({"metric_id": metric, "status": "available" if value is not None else "unavailable",
                        "value": value, "denominator": denominator, "excluded_cases": total-denominator,
                        "split": split, "label": label, "unit": unit, "reason": reason if value is None else None,
                        "evaluator_version": EVALUATOR, "dataset_sha256": plan["dataset"]["sha256"],
                        "provenance": plan["dataset"]["provenance"]})

    def ratio(metric, numerator, denominator, total, split="all", **kwargs):
        measurement(metric, numerator/denominator if denominator else None, denominator, total, split,
                    reason="No evaluable denominator; missing evidence is not a passing score", **kwargs)

    for role in sorted(set(mappings) | {"model_version", "application_version"}):
        present = sum(row["values"].get(role) is not None for row in rows)
        ratio("field_coverage", present, len(rows), len(rows), label=role)
        if role in ("model_version", "application_version"):
            ratio("missing_version_rate", len(rows)-present, len(rows), len(rows), label=role)
    latencies = [row["values"]["latency_ms"] for row in rows if number(row["values"].get("latency_ms")) and row["values"]["latency_ms"] >= 0]
    for metric, fraction in (("latency_p50", .5), ("latency_p95", .95)):
        measurement(metric, quantile(latencies, fraction) if latencies else None, len(latencies), len(rows),
                    unit="milliseconds", reason="Emit finite nonnegative latency_ms")
    for metric in ("outcome_pending", "outcome_overdue", "outcome_resolved"):
        measurement(metric, None, 0, len(rows), unit="count", reason="Live tracked-outcome counts are available in the runtime outcome coverage view; historical actuals do not supply receipt deadlines")

    # Metrics are separated by the frozen split; no tuning on held-out results.
    for split in ("calibration", "held_out"):
        subset = [row["values"] for row in rows if row.get("split") == split]
        total = len(subset)
        if "forecasting" in capabilities:
            valid = [row for row in subset if confirmation["outcome_meaning_confirmed"] and number(row.get("prediction")) and number(row.get("actual")) and math.isfinite(row["prediction"]-row["actual"])]
            errors = [row["prediction"]-row["actual"] for row in valid]
            for metric, value in (("forecast_mae", sum(abs(error)/len(errors) for error in errors) if errors else None),
                                  ("forecast_rmse", math.hypot(*(error/math.sqrt(len(errors)) for error in errors)) if errors else None),
                                  ("forecast_bias", sum(error/len(errors) for error in errors) if errors else None)):
                measurement(metric, value, len(valid), total, split, unit="target_units", reason="Need predictions and owner-confirmed observed actuals")
            gate = next((item for item in plan["metrics"] if item["name"] == "Forecast outcome error" and item["status"] == "available"), None)
            count = sum(abs(error) > gate["threshold"] for error in errors) if gate else 0
            ratio("forecast_exceedance_rate", count, len(valid) if gate else 0, total, split)
        if "classification" in capabilities:
            valid = [row for row in subset if confirmation["outcome_meaning_confirmed"] and row.get("predicted_label") is not None and row.get("actual_label") is not None]
            ratio("classification_accuracy", sum(row["predicted_label"] == row["actual_label"] for row in valid), len(valid), total, split)
            labels = sorted({str(row["values"][key]) for row in rows for key in ("predicted_label", "actual_label")
                             if confirmation["outcome_meaning_confirmed"] and row["values"].get(key) is not None})
            if len(labels) <= 100:
                pairs = Counter((row["predicted_label"], row["actual_label"]) for row in valid)
                predicted_counts = Counter(row["predicted_label"] for row in valid)
                actual_counts = Counter(row["actual_label"] for row in valid)
                confusion = {predicted: {actual: pairs[predicted, actual] for actual in labels} for predicted in labels}
                for label in labels:
                    ratio("class_precision", pairs[label, label], predicted_counts[label], total, split, label=label)
                    ratio("class_recall", pairs[label, label], actual_counts[label], total, split, label=label)
                measurement("class_confusion", confusion if valid else None, len(valid), total, split, unit="counts", reason="Need owner-confirmed labels; rows are predicted classes and columns actual classes")
            else:
                for identifier in ("class_precision", "class_recall", "class_confusion"):
                    measurement(identifier, None, 0, total, split, reason="Per-class reports support at most 100 distinct labels; select a bounded task-specific evaluation scope")
            gate = next((item for item in plan["metrics"] if item["name"] == "Confidence error gate" and item["status"] == "available"), None)
            if gate:
                counts = gate[split]
                tp, fp, fn, tn = (counts[key] for key in ("true_positives", "false_positives", "false_negatives", "true_negatives"))
                for metric, numerator, denominator in (("gate_precision", tp, tp+fp), ("gate_error_recall", tp, tp+fn), ("gate_false_positive_rate", fp, fp+tn)):
                    ratio(metric, numerator, denominator, total, split)
            else:
                for metric in ("gate_precision", "gate_error_recall", "gate_false_positive_rate"):
                    measurement(metric, None, 0, total, split, reason="Need a calibrated confidence gate with confirmed labels")
        if "rag" in capabilities:
            valid = [row for row in subset if isinstance(row.get("citations"), list) and isinstance(row.get("source_ids"), list)]
            ratio("citation_missing_rate", sum(not row["citations"] for row in valid), len(valid), total, split)
            ratio("citation_unknown_rate", sum(bool(set(row["citations"])-set(row["source_ids"])) for row in valid), len(valid), total, split)
            judgments = [row for row in subset if confirmation.get("relevance_meaning_confirmed") and isinstance(row.get("source_ids"), list) and isinstance(row.get("relevant_source_ids"), list) and row["relevant_source_ids"]]
            recalls = [len(set(row["source_ids"][:request.retrieval_k]) & set(row["relevant_source_ids"]))/len(set(row["relevant_source_ids"])) for row in judgments]
            measurement("retrieval_recall_at_k", sum(recalls)/len(recalls) if recalls else None, len(recalls), total, split,
                        label=f"k={request.retrieval_k}", reason="Need ordered retrieved IDs and owner-confirmed nonempty relevance judgments; empty judged sets have undefined recall")
        if "tools" in capabilities:
            allowed = confirmation.get("allowed_tools")
            valid = [row for row in subset if isinstance(row.get("tool_name"), str) and row["tool_name"].strip()] if allowed else []
            attempts = sum(row["tool_name"] not in allowed for row in valid) if allowed else 0
            measurement("unauthorized_tool_attempts", attempts if valid else None, len(valid), total, split, unit="count", reason="Need tool names and owner-confirmed permissions")
            ratio("unauthorized_tool_rate", attempts, len(valid), total, split)

    scope = plan["instrumentation"]["scope"]
    scope_ready = "model_version" in scope and "application_version" in scope and not any("Mixed or missing" in gap for gap in plan["gaps"])
    split_ready = plan["dataset"]["split_method"] != "unavailable"
    rules = {RULE_CONTROLS[rule["id"]]: rule for rule in (plan.get("policy") or {}).get("rules", [])}
    # Composite applications can also use deterministic citation checks.
    if "rag" in capabilities and "rag.citations" not in rules and all(any(isinstance(row["values"].get("citations"), list) and isinstance(row["values"].get("source_ids"), list) for row in rows if row.get("split") == split) for split in ("calibration", "held_out")):
        rules["rag.citations"] = {"id": "discovered_citations", "name": "Missing or unknown citation", "detector": "citation_integrity", "phase": "output", "task_type": task, "severity": "medium", "action": "flag", **scope}
    if "tools" in capabilities and confirmation.get("allowed_tools") and "tool_name" in mappings:
        rules["tools.permissions"] = {"id": "discovered_tools", "name": "Tool outside confirmed permissions", "detector": "tool_allowlist", "phase": "tool", "task_type": task,
                                      "allowed": confirmation["allowed_tools"], "severity": "high", "action": "flag", **scope}
    if latencies and confirmation.get("latency_sla_ms"):
        rules["common.latency"] = {"id": "discovered_latency", "name": "Latency exceeds confirmed SLA", "detector": "metric_threshold", "phase": "output", "task_type": task,
                                   "metric": "latency_ms", "threshold": confirmation["latency_sla_ms"], "comparator": "gt", "severity": "medium", "action": "flag", **scope}
    if not confirmation["outcome_meaning_confirmed"]:
        rules.pop("forecast.error", None)
        rules.pop("classification.confidence", None)
    if not scope_ready or not split_ready:
        rules = {}
    ids = {control["id"] for control in frozen["controls"]}
    selected = set(request.selected_controls) if request.selected_controls is not None else set(rules)-set(request.dismissed_controls)
    if (selected | set(request.dismissed_controls)) - ids or selected & set(request.dismissed_controls):
        raise ValueError("Use known, distinct selected/dismissed controls")
    if any(not reason.strip() or len(reason) > 2000 for reason in request.dismissed_controls.values()):
        raise ValueError("Each dismissal requires a bounded rationale")
    recommendations = []
    for definition in frozen["controls"]:
        identifier = definition["id"]
        applicable = definition["pack_id"] in capabilities
        metrics = [item for item in results if item["metric_id"] in definition["metric_ids"]]
        evidence = [{"role": role, "path": path} for role, path in mappings.items() if role in definition["required_inputs"]]
        status = "ready" if identifier in rules else "measurement_only" if any(item["status"] == "available" for item in metrics) else "needs_evidence"
        recommendations.append({**definition, "applicability": "applicable" if applicable else "not_indicated",
                                "why": f"Confirmed {task} application; capabilities: {', '.join(sorted(capabilities))}",
                                "evidence": evidence, "status": status if applicable else "not_applicable",
                                "missing_prerequisites": sorted({item["reason"] for item in metrics if item["status"] == "unavailable" and item["reason"]}) +
                                    (["No ready runtime rule; review required inputs and business decisions"] if applicable and identifier not in rules else []),
                                "selected": identifier in selected, "dismissal_rationale": request.dismissed_controls.get(identifier)})
        if identifier in rules:
            rules[identifier]["mitigation"] = definition["suggested_response"]
            rules[identifier]["control_reference"] = {"catalogue_version": frozen["version"], "catalogue_sha256": frozen["sha256"],
                "control_id": identifier, "control_version": definition["version"], "references": definition["references"]}
    blocked = selected-set(rules)
    active_rules = [rules[key] for key in sorted(selected & rules.keys())]
    plan["policy"] = {"name": "Reviewed starter observation policies", "rules": active_rules, "actor": request.actor,
                      "rationale": "Evidence-backed starter controls reviewed for observation", "outcome_deadline_action": "flag"} if active_rules else None
    plan["status"] = "ready" if active_rules and not blocked else "needs_evidence"
    plan.update(catalogue=frozen, recommendations=recommendations, metric_results=results,
                control_decisions={"selected": sorted(selected), "dismissed": request.dismissed_controls},
                calibration_settings={"forecast_alert_fraction": request.forecast_alert_fraction if request.forecast_alert_fraction is not None else request.alert_fraction,
                    "classification_false_positive_budget": request.classification_false_positive_budget if request.classification_false_positive_budget is not None else request.alert_fraction,
                    "retrieval_k": request.retrieval_k})
    if blocked:
        plan["gaps"].append("Selected controls are not ready: " + ", ".join(sorted(blocked)))
    return plan
