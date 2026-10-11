import pytest

from governloom.calibration import temporal_block_threshold


def rows():
    return [{"timestamp": f"2020-{month:02d}-{day:02d}T00:00:00+00:00", "value": month + day / 100} for month in range(1, 9) for day in (1, 2, 3)]


def test_block_maxima_order_statistic_and_holdout_not_used():
    report = temporal_block_threshold(rows(), held_out_start="2021-01-01T00:00:00+00:00")
    assert len(report["blocks"]) == report["rank"] == 8
    assert report["threshold"] == 8.03 and report["nominal_probability_valid"] is False
    assert report["blocks"][0]["score"] == 1.03


def test_refuses_leakage_reordering_missing_tail_and_unattainable_budget():
    for values, options in ((rows()[::-1], {}), (rows()[:-1], {}), (rows(), {"alpha": .05}),
        (rows(), {"held_out_start": "2020-08-01T00:00:00+00:00"}), (rows(), {"held_out_start": "2021-01-01"})):
        with pytest.raises(ValueError):
            temporal_block_threshold(values, **{"held_out_start": "2021-01-01T00:00:00+00:00", **options})
