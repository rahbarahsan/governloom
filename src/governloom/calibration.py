"""Explicit empirical threshold selection; never a population error guarantee."""
import math
from bisect import bisect_left, bisect_right


def evaluate_threshold(rows, threshold, direction="low"):
    if direction not in ("low", "high") or not math.isfinite(threshold) or not rows or len(rows) > 100_000:
        raise ValueError("Specify finite threshold, low/high direction and 1..100000 labeled rows")
    counts = dict(true_positives=0, false_positives=0, true_negatives=0, false_negatives=0)
    for row in rows:
        if not isinstance(row["risk"], bool) or isinstance(row["value"], bool) or not isinstance(row["value"], (int, float)) or not math.isfinite(row["value"]):
            raise ValueError("Calibration values must be finite numeric values with explicit Boolean risk labels")
        flagged = row["value"] < threshold if direction == "low" else row["value"] > threshold
        counts["true_positives" if flagged and row["risk"] else "false_positives" if flagged else "false_negatives" if row["risk"] else "true_negatives"] += 1
    positives = counts["true_positives"] + counts["false_negatives"]
    negatives = counts["false_positives"] + counts["true_negatives"]
    return {**counts, "cases": len(rows), "false_positive_rate": counts["false_positives"] / negatives if negatives else None,
        "risk_capture_rate": counts["true_positives"] / positives if positives else None}


def calibrate_threshold(rows, *, false_positive_budget=.05, direction="low"):
    if not 0 <= false_positive_budget <= 1 or not math.isfinite(false_positive_budget):
        raise ValueError("False-positive budget must be between zero and one")
    initial = evaluate_threshold(rows, 0, direction)
    if initial["true_negatives"] + initial["false_positives"] < 20 or initial["true_positives"] + initial["false_negatives"] < 1:
        raise ValueError("Need at least 20 negative controls and one labeled risk for empirical calibration")
    candidates = sorted({row["value"] for row in rows})
    boundary = math.nextafter(candidates[-1] if direction == "low" else candidates[0], math.inf if direction == "low" else -math.inf)
    if math.isfinite(boundary):
        candidates.append(boundary)
    negatives = sorted(row["value"] for row in rows if not row["risk"])
    admissible = [threshold for threshold in candidates if
        (bisect_left(negatives, threshold) if direction == "low" else len(negatives) - bisect_right(negatives, threshold)) / len(negatives) <= false_positive_budget]
    threshold = max(admissible) if direction == "low" else min(admissible)
    result = evaluate_threshold(rows, threshold, direction)
    return {"threshold": threshold, "comparator": "lt" if direction == "low" else "gt", "false_positive_budget": false_positive_budget,
        "calibration": result, "method": "Most permissive observed threshold meeting empirical calibration false-positive budget",
        "limitation": "Empirical calibration only; small/dependent samples and domain shift can violate the held-out or production budget"}
