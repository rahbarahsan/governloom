import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from sklearn.linear_model import LinearRegression

from examples.common import digest

SOURCE = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt"


def download(destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Refusing to overwrite a frozen data snapshot")
    with urlopen(SOURCE, timeout=30) as response:
        content = response.read(1_000_001)
    if len(content) > 1_000_000 or not content.startswith(b"#"):
        raise ValueError("Unexpected NOAA dataset response")
    # Validate before publishing the snapshot; no download during service startup.
    parse(content.decode("utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    metadata = {"url": SOURCE, "sha256": digest(content), "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "attribution": "NOAA Global Monitoring Laboratory; monthly CO2 data and source-header contributors"}
    destination.with_suffix(".manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def parse(text):
    values = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 8:
            raise ValueError("NOAA monthly rows require eight columns")
        year, month = int(parts[0]), int(parts[1])
        average, days, deviation, uncertainty = float(parts[3]), int(parts[5]), float(parts[6]), float(parts[7])
        if not 1 <= month <= 12 or not all(math.isfinite(value) for value in (average, deviation, uncertainty)):
            raise ValueError("Invalid monthly observation")
        identifier = f"{year:04d}-{month:02d}"
        if identifier in values:
            raise ValueError("Duplicate monthly observation")
        values[identifier] = {"date": identifier, "value": average, "observed": average > 0 and days > 0 and deviation >= 0 and uncertainty >= 0}
    if not values:
        raise ValueError("No monthly observations")
    return values


def features(date):
    year, month = map(int, date.split("-"))
    years = (year - 2005) + (month - 1) / 12
    angle = 2 * math.pi * (month - 1) / 12
    return [years, years * years, math.sin(angle), math.cos(angle)]


class ForecastModel:
    def __init__(self, path):
        self.path = Path(path)
        content = self.path.read_bytes()
        self.rows = parse(content.decode("utf-8"))
        self.data_hash = digest(content)
        metadata_path = self.path.with_suffix(".manifest.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {"kind": "unverified_local_series"}
        if "sha256" in metadata and metadata["sha256"] != self.data_hash:
            raise ValueError("Snapshot differs from its recorded hash")
        self.calibration = [date for date, row in sorted(self.rows.items()) if "2019-01" <= date <= "2020-12" and row["observed"]]
        self.held_out = [date for date in sorted(self.rows) if "2021-01" <= date <= "2024-12"]
        if len(self.calibration) < 12 or len(self.held_out) < 24:
            raise ValueError("Need calibration 2019-2020 and held-out 2021-2024 observations")
        errors = [abs(self.predict(date)["prediction"] - self.rows[date]["value"]) for date in self.calibration]
        self.threshold = float(np.quantile(errors, 0.9))
        self.manifest = {"source_url": metadata.get("url"), "provenance": metadata, "dataset_hash": self.data_hash, "algorithm": "Quadratic trend plus annual Fourier terms",
            "fit_window": "last 120 observed months, strictly before forecast date", "first_training_month": "2005-01",
            "calibration_period": ["2019-01", "2020-12"], "held_out_period": ["2021-01", "2024-12"],
            "calibration_count": len(self.calibration), "held_out_count": len(self.held_out), "unit": "ppm", "horizon_months": 1,
            "absolute_error_threshold": self.threshold, "selection": "90th calibration absolute-error percentile, frozen",
            "limitation": "Historical replay; excludes interpolated/missing actuals; source documents a 2022-2023 site change"}

    def predict(self, date, fallback=False):
        if date not in self.rows:
            raise ValueError("Unknown snapshot month")
        training = [row for key, row in sorted(self.rows.items()) if "2005-01" <= key < date and row["observed"]][-120:]
        if len(training) < 24:
            raise ValueError("Insufficient prior observed training months")
        if fallback:
            year, month = map(int, date.split("-"))
            prior = self.rows.get(f"{year - 1:04d}-{month:02d}")
            if not prior or not prior["observed"]:
                raise ValueError("Seasonal-naive fallback lacks an observed prior-year month")
            prediction = prior["value"]
            model_hash = digest(["seasonal-naive", prior, self.data_hash])
        else:
            fitted = LinearRegression().fit([features(row["date"]) for row in training], [row["value"] for row in training])
            prediction = float(fitted.predict([features(date)])[0])
            model_hash = digest([self.data_hash, [row["date"] for row in training], fitted.coef_.tolist(), float(fitted.intercept_)])
        return {"prediction": prediction, "date": date, "training_cutoff": training[-1]["date"], "training_count": len(training),
                "model_version": ("seasonal-naive-" if fallback else "co2-regression-") + model_hash[:16], "fallback": fallback}

    def actual(self, date):
        if date not in self.held_out:
            raise ValueError("Outcomes are restricted to held-out historical months")
        return self.rows[date] if self.rows[date]["observed"] else None

    def evaluate(self):
        rows = []
        missing = 0
        for date in self.held_out:
            actual = self.actual(date)
            if actual is None:
                missing += 1
                continue
            result = self.predict(date)
            error = abs(result["prediction"] - actual["value"])
            try:
                baseline = self.predict(date, fallback=True)["prediction"]
            except ValueError:
                baseline = None
            rows.append({**result, "actual": actual["value"], "absolute_error": error, "over_tolerance": error > self.threshold,
                         "baseline_absolute_error": abs(baseline - actual["value"]) if baseline is not None else None})
        errors = [row["absolute_error"] for row in rows]
        baseline = [row["baseline_absolute_error"] for row in rows if row["baseline_absolute_error"] is not None]
        return {"cases": len(rows), "missing_actuals": missing, "mae_ppm": float(np.mean(errors)),
                "rmse_ppm": float(np.sqrt(np.mean(np.square(errors)))), "baseline_mae_ppm": float(np.mean(baseline)) if baseline else None,
                "baseline_cases": len(baseline), "over_tolerance": sum(row["over_tolerance"] for row in rows), "rows": rows}
