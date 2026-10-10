"""Frozen public-label calibration and untouched held-out gate comparison."""
import json

from examples.common import digest
from examples.vision.model import DigitModel
from governloom.calibration import calibrate_threshold, evaluate_threshold


def gate_evidence(model, false_positive_budget=.05):
    def rows(indices):
        probabilities = model.classifier.predict_proba(model.images[indices])
        predictions = model.classifier.predict(model.images[indices])
        return [{"sample_id": int(identifier), "value": float(probabilities[index].max()),
            "risk": bool(int(predictions[index]) != int(model.labels[identifier]))} for index, identifier in enumerate(indices)]
    calibration, held_out = rows(model.calibration), rows(model.held_out)
    selected = calibrate_threshold(calibration, false_positive_budget=false_positive_budget)
    return {"label_provenance": "Original public UCI benchmark labels; risk means wrong predicted digit", "model_version": model.version,
        "dataset_sha256": model.manifest["dataset_hash"], "calibration_sha256": digest(calibration), "held_out_sha256": digest(held_out),
        "selection": selected, "held_out": evaluate_threshold(held_out, selected["threshold"]),
        "original_percentile_gate": {"threshold": model.threshold, "held_out": evaluate_threshold(held_out, model.threshold)},
        "split": "Disjoint frozen training/calibration/held-out indices; threshold selected on calibration only"}


if __name__ == "__main__":
    print(json.dumps(gate_evidence(DigitModel()), indent=2))
