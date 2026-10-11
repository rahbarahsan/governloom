"""Explicit empirical threshold selection; never a population error guarantee."""
import math
from datetime import datetime
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


def temporal_block_threshold(rows, *, block_size=3, alpha=.2, held_out_start):
    """An empirical threshold on preceding non-overlapping block maxima.

    Preserves within-block dependence; it does not establish exchangeable blocks
    or a conformal coverage guarantee for a dependent, nonstationary series.
    """
    if type(block_size) is not int or not 1 <= block_size <= 1000 or not 0 < alpha < 1 or not math.isfinite(alpha):
        raise ValueError("Specify block size 1..1000 and finite alpha strictly between zero and one")
    if not rows or len(rows) > 100_000 or len(rows) % block_size:
        raise ValueError("Use complete chronological blocks; do not silently discard missing/tail observations")
    boundary = datetime.fromisoformat(held_out_start)
    if boundary.tzinfo is None:
        raise ValueError("Held-out boundary needs a timezone")
    timestamps = [datetime.fromisoformat(row["timestamp"]) for row in rows]
    values = [row["value"] for row in rows]
    if any(value.tzinfo is None for value in timestamps) or any(a >= b for a, b in zip(timestamps, timestamps[1:])) or timestamps[-1] >= boundary:
        raise ValueError("Calibration must be strictly chronological and entirely before held-out evaluation")
    if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Block scores need nonnegative finite residual magnitudes")
    blocks = [{"start": timestamps[i].isoformat(), "end": timestamps[i + block_size - 1].isoformat(),
        "score": max(values[i:i + block_size]), "cases": block_size} for i in range(0, len(rows), block_size)]
    rank = math.ceil((len(blocks) + 1) * (1 - alpha))
    if rank > len(blocks):
        raise ValueError("Too few calibration blocks for a finite threshold at this alpha; collect more evidence")
    return {"threshold": sorted(block["score"] for block in blocks)[rank - 1], "comparator": "gt", "alpha": alpha,
        "block_size": block_size, "blocks": blocks, "rank": rank, "held_out_start": boundary.isoformat(),
        "method": "Finite-sample order statistic of non-overlapping chronological block maxima",
        "nominal_probability_valid": False,
        "limitation": "Empirical replay only: dependence between blocks, nonstationarity and revised data can invalidate nominal coverage"}
