"""Installed-package discovery consumer; no imports from the repository examples."""
import json
import os
from urllib.request import Request, urlopen

import governloom
from governloom.discovered_hook import DiscoveredObserver
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def main():
    endpoint, token = os.environ["GOVERNLOOM_ENDPOINT"], os.environ["GOVERNLOOM_OPERATOR_TOKEN"]
    def call(path, body=None):
        request = Request(endpoint+"/api"+path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer "+token})
        with urlopen(request, timeout=5) as response:
            return json.load(response)
    digits = load_digits()
    train, rest = train_test_split(range(len(digits.target)), test_size=.4, random_state=74, stratify=digits.target)
    cal, held = train_test_split(rest, test_size=.5, random_state=75, stratify=digits.target[rest])
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=76)).fit(digits.data[train], digits.target[train])
    rows = []
    for split, indices in (("calibration", cal), ("held_out", held)):
        predictions = model.predict(digits.data[indices])
        scores = model.predict_proba(digits.data[indices])
        for index, predicted, score in zip(indices, predictions, scores):
            rows.append({"sample_id": int(index), "split": split, "predicted_label": int(predicted), "actual_label": int(digits.target[index]),
                         "confidence": float(max(score)), "model_version": "standalone-policy-logistic-v1", "application_version": "standalone-policy-v1"})
    app = call("/applications", {"name": "Installed discovery classifier", "owner": "onboarding-admin", "purpose": "Discover actual model telemetry", "expected_behavior": "Review default policies"})
    prefix = f"/applications/{app['id']}"
    draft = call(prefix+"/discoveries", {"actor": "scripted-owner", "traces": rows})
    confirmation = call(prefix+f"/discoveries/{draft['id']}/confirm", {"actor": "scripted-owner", "expected_checksum": draft["checksum"],
        "task_type": draft["analysis"]["task_type"], "purpose": "Classify public digit images", "rationale": "Owned script confirms actual public labels",
        "mappings": draft["analysis"]["mappings"], "outcome_meaning_confirmed": True})
    plan = call(prefix+"/discovery-plans", {"actor": "scripted-owner", "confirmation_id": confirmation["id"]})
    assert plan["status"] == "ready", plan["gaps"]
    call(prefix+f"/discovery-plans/{plan['id']}/activate", {"actor": "scripted-owner", "expected_policy_id": None, "acknowledge_limitations": True, "rationale": "Review installed-package observation flags"})
    key = call(prefix+"/ingest-keys", {"actor": "scripted-owner", "name": "installed-discovery"})["key"]
    threshold = plan["policy"]["rules"][0]["threshold"]
    chosen = next(row for row in rows if row["split"] == "held_out" and row["predicted_label"] != row["actual_label"] and row["confidence"] < threshold)
    receipt = DiscoveredObserver(endpoint, key, plan).output(chosen, trace_id="installed-discovery")
    assert receipt["action"] == "flag"
    assert receipt["checks"][0]["control_reference"]["control_id"] == "classification.confidence"
    print(json.dumps({"status": "completed", "package_version": governloom.__version__, "no_prewritten_policy": True,
                      "catalogue_sha256": plan["catalogue"]["sha256"], "selected_controls": plan["control_decisions"]["selected"],
                      "held_out_cases": len(held), "incident_count": len(call(prefix+"/runtime-incidents")), "provider_requests": 0}))


if __name__ == "__main__":
    main()
