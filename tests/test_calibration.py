import pytest

from governloom.calibration import calibrate_threshold, evaluate_threshold


def test_budget_ties_and_untouched_holdout_show_misses_and_false_alarms():
    calibration = [{"value": .1, "risk": True}] * 4 + [{"value": .3, "risk": False}] * 2 + [{"value": .9, "risk": False}] * 38
    selected = calibrate_threshold(calibration, false_positive_budget=.05)
    assert selected["calibration"]["false_positive_rate"] == .05
    held = [{"value": .1, "risk": True}, {"value": .99, "risk": True}, {"value": .2, "risk": False}, {"value": 1., "risk": False}]
    report = evaluate_threshold(held, selected["threshold"])
    assert [report[key] for key in ("true_positives", "false_negatives", "false_positives", "true_negatives")] == [1, 1, 1, 1]
    assert report["false_positive_rate"] > selected["false_positive_budget"]  # No held-out guarantee or tuning.
    strict = calibrate_threshold(calibration, false_positive_budget=0)
    assert strict["threshold"] == .3 and strict["calibration"]["false_positives"] == 0
    with pytest.raises(ValueError):
        calibrate_threshold(calibration[:4])
    with pytest.raises(ValueError):
        calibrate_threshold([{**row, "value": float("nan")} for row in calibration])
