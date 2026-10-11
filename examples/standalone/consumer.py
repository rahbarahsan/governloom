"""Standalone actual digit classifier; only public SDK/model dependencies."""
import json
import os
from pathlib import Path

import governloom
from governloom.hook import PolicyViolation, RuntimeHook
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def main():
    data = load_digits()
    train, held = train_test_split(range(len(data.target)), test_size=.25, random_state=71, stratify=data.target)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=72)).fit(data.data[train], data.target[train])
    predictions = model.predict(data.data[held])
    probabilities = model.predict_proba(data.data[held])
    mistakes = [i for i, label in enumerate(predictions) if label != data.target[held[i]]]
    assert mistakes, "No natural mistake available in this frozen split"
    selected = min(mistakes, key=lambda i: probabilities[i].max())
    calls = 0
    def predict(pixels):
        nonlocal calls
        calls += 1
        scores = model.predict_proba([pixels])[0]
        return {"label": int(scores.argmax()), "confidence": float(scores.max())}
    hook = RuntimeHook(os.environ["GOVERNLOOM_ENDPOINT"], os.environ["GOVERNLOOM_INGEST_KEY"], mode="enforce", on_unavailable="raise")
    wrapped = hook.wrap(predict, task_type="vision", model_version="standalone-logistic-v1", application_version="standalone-consumer-v1",
        output_mapper=lambda result: {"metrics": {"confidence": result["confidence"]}})
    try:
        wrapped(data.data[held[selected]])
    except PolicyViolation as risk:
        assert risk.receipt["action"] == "block" and calls == 1
        report = {"status": "withheld", "package_version": governloom.__version__, "installed_package": str(Path(governloom.__file__).resolve()),
            "natural_errors": len(mistakes), "held_out_cases": len(held), "target_calls": calls, "confidence": float(probabilities[selected].max()),
            "scope": "Owned independent LogisticRegression consumer; selected natural error, not independent onboarding feedback or detector accuracy evidence"}
        print(json.dumps(report))
        return
    raise AssertionError("Expected the illustrative confidence policy to withhold this selected error")


if __name__ == "__main__":
    main()
