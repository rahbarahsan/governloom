"""Per-label/perturbation measurements with the calibration gate kept frozen."""
import json

from examples.common import digest
from examples.vision.calibration import gate_evidence
from examples.vision.model import DigitModel
from governloom.calibration import evaluate_threshold


def evidence(model):
    gate = gate_evidence(model)
    scenarios = []
    for scenario in ("none", "occlusion", "noise"):
        rows = []
        for index in model.held_out:
            result = model.predict(model.sample(index, scenario))
            rows.append({"sample_id": index, "actual": int(model.labels[index]), "value": result["confidence"], "risk": result["prediction"] != int(model.labels[index])})
        scenarios.append({"scenario": "natural" if scenario == "none" else scenario, "rows_sha256": digest(rows),
            "overall": evaluate_threshold(rows, gate["selection"]["threshold"]),
            "labels": [{"label": label, **evaluate_threshold([row for row in rows if row["actual"] == label], gate["selection"]["threshold"])} for label in range(10)]})
    return {"manifest": model.manifest, "gate": gate, "scenarios": scenarios,
        "label_provenance": "Original public UCI labels; transformed-image labels are engineering references, not independently checked recognizability",
        "limitation": "Small public benchmark and declared corruptions, no new domain/writer population. Per-label rates are descriptive, not fairness certification."}


if __name__ == "__main__":
    print(json.dumps(evidence(DigitModel()), indent=2))
