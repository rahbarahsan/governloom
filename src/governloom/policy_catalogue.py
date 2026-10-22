"""Trusted, versioned starter objectives. Mappings are guidance, not certification.

Definitions ship with the package; source/model text cannot supply executable rules.
Published plans freeze the definitions they use instead of following remote updates.
"""
from copy import deepcopy

from .service import checksum

VERSION = "2026-10-21.1"
NIST = {"framework": "NIST AI RMF", "version": "1.0", "reference": "MEASURE 1.1",
        "url": "https://airc.nist.gov/airmf-resources/playbook/measure/",
        "rationale": "Select context-appropriate risk metrics and document risks that cannot be measured."}


def owasp(reference, slug, rationale):
    return {"framework": "OWASP LLM Top 10", "version": "2025", "reference": reference,
            "url": f"https://genai.owasp.org/llmrisk/{slug}/", "rationale": rationale}


def control(identifier, pack, name, requires, metrics, threshold, response, limitation, reference=None):
    return {"id": identifier, "version": 1, "pack_id": pack, "name": name,
            "required_inputs": requires, "metric_ids": metrics, "threshold_selection": threshold,
            "suggested_response": response, "limitations": limitation,
            "references": [NIST] + ([reference] if reference else [])}


CONTROLS = [
    control("common.coverage", "common", "Understand telemetry coverage", ["confirmed field mappings"],
            ["field_coverage", "missing_version_rate"], "Descriptive; no automatic activation",
            "Instrument missing fields and verify production paths emit events.",
            "Observed rows cannot establish coverage of traffic that never reached the collector."),
    control("common.latency", "common", "Observe serving latency", ["latency_ms"], ["latency_p50", "latency_p95"],
            "Owner-confirmed latency SLA required for a runtime flag",
            "Inspect slow requests and serving dependencies.", "Historical latency does not establish an acceptable SLA."),
    control("common.outcomes", "common", "Track feedback deadlines", ["linked prediction", "outcome_due_at"],
            ["outcome_pending", "outcome_overdue", "outcome_resolved"], "Application supplies a real outcome_due_at",
            "Investigate missing feedback before interpreting model quality.",
            "Only explicitly tracked predictions count; unavailable outcomes are never zero errors."),
    control("forecast.error", "forecasting", "Flag unusual forecast error", ["prediction", "actual", "timestamp", "confirmed actual meaning"],
            ["forecast_mae", "forecast_rmse", "forecast_bias", "forecast_exceedance_rate"],
            "Calibration-only absolute residual quantile; default exploratory fraction 10%",
            "Inspect actuals, target units, horizon and deployment changes.",
            "An empirical residual exceedance is not a harmful-outcome label or a probability guarantee."),
    control("classification.quality", "classification", "Measure classification quality", ["predicted_label", "actual_label", "confirmed label meaning"],
            ["classification_accuracy", "class_precision", "class_recall", "class_confusion"], "Descriptive; no universal acceptable accuracy",
            "Review class-specific errors and label provenance.", "Observed labels may omit deployment groups or be incorrect."),
    control("classification.confidence", "classification", "Flag low-confidence predictions", ["confidence", "predicted_label", "actual_label", "confirmed label meaning"],
            ["gate_precision", "gate_error_recall", "gate_false_positive_rate"],
            "Calibration-only false-positive budget; default exploratory budget 10%",
            "Review flagged predictions and sample unflagged predictions for confident errors.",
            "Confidence can miss confident errors; held-out false-positive budgets may be exceeded."),
    control("rag.citations", "rag", "Flag missing or unknown citations", ["citations", "source_ids"],
            ["citation_missing_rate", "citation_unknown_rate"], "Flag empty citations or IDs absent from retrieved sources",
            "Inspect the answer and retrieved passages before choosing a response.",
            "Citation identity does not prove source authority, claim support or answer correctness.",
            owasp("LLM09:2025", "llm092025-misinformation", "Evidence inspection supports misinformation investigation; identity checks cover only a narrow part of the risk.")),
    control("rag.retrieval", "rag", "Measure retrieval coverage", ["ordered source_ids", "relevant_source_ids", "confirmed relevance judgments"],
            ["retrieval_recall_at_k"], "Descriptive; k defaults to 5, no universal passing score",
            "Investigate missed relevant documents and relevance labels.", "Retrieved documents alone cannot establish recall."),
    control("tools.permissions", "tools", "Flag tools outside confirmed permissions", ["tool_name", "owner-confirmed allowed_tools"],
            ["unauthorized_tool_attempts", "unauthorized_tool_rate"], "Flag attempts outside the confirmed nonempty allowlist",
            "Investigate the attempt and independently verify any side effect; review least privilege.",
            "A recorded attempt is not proof of successful execution or independent authorization enforcement.",
            owasp("LLM06:2025", "llm062025-excessive-agency", "Explicit tool permissions address excessive functionality; downstream permissions and high-impact approvals still need independent controls.")),
]

METHODS = {
    "field_coverage": "Rows with a non-null selected field / all selected rows, per field; metric-specific type validity is separate",
    "missing_version_rate": "Rows missing the version field / all selected rows, per version field",
    "latency_p50": "Nearest-rank empirical 50th percentile of finite nonnegative milliseconds",
    "latency_p95": "Nearest-rank empirical 95th percentile of finite nonnegative milliseconds",
    "outcome_pending": "Live explicitly tracked predictions awaiting feedback before their deadline",
    "outcome_overdue": "Live explicitly tracked predictions past deadline without linked actuals",
    "outcome_resolved": "Live explicitly tracked predictions with linked actuals received",
    "forecast_mae": "Mean absolute prediction-minus-actual error",
    "forecast_rmse": "Square root of mean squared prediction-minus-actual error",
    "forecast_bias": "Mean prediction-minus-actual error",
    "forecast_exceedance_rate": "Absolute residuals strictly exceeding the fixed calibration threshold / evaluable pairs",
    "classification_accuracy": "Matching predicted/reference labels / owner-confirmed labeled cases",
    "class_precision": "True positives / predicted positives, one-versus-rest per class",
    "class_recall": "True positives / actual positives, one-versus-rest per class",
    "class_confusion": "Counts with predicted classes as rows and actual classes as columns",
    "gate_precision": "Errors flagged / all flagged predictions",
    "gate_error_recall": "Errors flagged / all labeled errors, including unflagged predictions",
    "gate_false_positive_rate": "Correct predictions flagged / all labeled correct predictions",
    "citation_missing_rate": "Cases with empty citations / cases with citation and retrieved-source lists",
    "citation_unknown_rate": "Cases citing any unknown source ID / cases with both source lists",
    "retrieval_recall_at_k": "Macro mean of unique relevant IDs retrieved in the first k positions / unique judged relevant IDs; empty relevant sets excluded",
    "unauthorized_tool_attempts": "Count of evaluable calls outside owner-confirmed allowed tool names",
    "unauthorized_tool_rate": "Out-of-allowlist calls / all evaluable tool calls",
}


def catalogue():
    payload = {"schema_version": 1, "version": VERSION,
               "interpretation": "GovernLoom starter guidance mapped to selected objectives, not complete framework coverage or compliance certification.",
               "packs": [{"id": key, "name": name} for key, name in (
                   ("common", "Operational coverage"), ("forecasting", "Forecasting quality"),
                   ("classification", "Vision and classification"), ("rag", "RAG evidence"), ("tools", "Tool permissions"))],
               "controls": deepcopy(CONTROLS),
               "metrics": [{"id": key, "method": value, "evaluator_version": "policy-metrics-v1",
                            "undefined": "Unavailable when prerequisites or a required denominator are missing"} for key, value in METHODS.items()]}
    return {**payload, "sha256": checksum(payload)}
