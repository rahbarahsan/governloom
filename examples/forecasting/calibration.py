"""Frozen NOAA rolling forecasts, block calibration and untouched later months."""
import argparse
import json

from examples.common import digest
from examples.forecasting.model import ForecastModel
from governloom.calibration import temporal_block_threshold


def evidence(model):
    residuals = [{"timestamp": date + "-01T00:00:00+00:00", "value": abs(model.predict(date)["prediction"] - model.rows[date]["value"])} for date in model.calibration]
    selection = temporal_block_threshold(residuals, block_size=3, alpha=.2, held_out_start="2021-01-01T00:00:00+00:00")
    evaluation = model.evaluate()
    indexed = {row["date"]: row for row in evaluation["rows"]}
    blocks = []
    for i in range(0, len(model.held_out), 3):
        dates = model.held_out[i:i + 3]
        observed = [indexed[date] for date in dates if date in indexed]
        # Keep missing actuals in their time block, never shift later months.
        blocks.append({"start": dates[0], "end": dates[-1], "cases": len(observed), "missing": len(dates) - len(observed),
            "score": max(row["absolute_error"] for row in observed) if len(observed) == 3 else None,
            "flagged": max(row["absolute_error"] for row in observed) > selection["threshold"] if len(observed) == 3 else None})
    return {"manifest": model.manifest, "calibration_sha256": digest(residuals), "held_out_sha256": digest(evaluation["rows"]),
        "selection": selection, "held_out_blocks": blocks,
        "held_out": {"observed_months": evaluation["cases"], "missing_actuals": evaluation["missing_actuals"],
            "blocks": len(blocks), "flagged_blocks": sum(block["flagged"] is True for block in blocks),
            "unavailable_blocks": sum(block["flagged"] is None for block in blocks),
            "months_over_block_threshold": sum(row["absolute_error"] > selection["threshold"] for row in evaluation["rows"]),
            "months_over_original_threshold": evaluation["over_tolerance"], "mae_ppm": evaluation["mae_ppm"]},
        "interpretation": "Block exceedance is an empirical residual signal, not an independently labeled unsafe forecast. No held-out tuning; rolling models use only prior months from a revised snapshot."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot")
    args = parser.parse_args()
    print(json.dumps(evidence(ForecastModel(args.snapshot)), indent=2))
