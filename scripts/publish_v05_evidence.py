"""Publish reviewed non-secret summaries; raw keys/databases/prompts stay private."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reliability", type=Path, required=True); parser.add_argument("--onboarding", type=Path, required=True)
    parser.add_argument("--rag-original", type=Path, required=True); parser.add_argument("--rag-replay", type=Path, required=True)
    parser.add_argument("--vision", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    reliability, onboarding, original, replay, vision = [read(path) for path in (options.reliability, options.onboarding, options.rag_original, options.rag_replay, options.vision)]
    for capture in (reliability, onboarding, original, replay):
        if capture.get("status") != "completed" or not capture.get("owned_services_stopped"):
            raise ValueError("Only completed, stopped captures can be published")
    consumer = {key: value for key, value in onboarding["consumer"].items() if key != "installed_package"}
    rag_fields = ("dataset_sha256", "label_provenance", "rubric", "unsupported_fraction_threshold", "groups", "calibration", "held_out", "claims", "retrieval", "retrieval_gaps", "natural_answer", "collector_checks", "profile_checksum", "subscription_requests", "recorded_subscription_requests", "capture_mode")
    report = {"schema_version": 1, "date": "2026-10-11", "phase": "Development captures preceding final 0.5 version/commits; public package/image verification is separate",
        "capture_hashes": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in
            (("reliability", options.reliability), ("onboarding", options.onboarding), ("rag_original", options.rag_original), ("rag_replay", options.rag_replay), ("vision", options.vision))},
        "reliability": reliability,
        "onboarding": {"setup_seconds": onboarding["setup_seconds"], "setup_to_first_incident_seconds": onboarding["setup_to_first_incident_seconds"],
            "consumer": consumer, "installed_into_isolated_environment": True, "owned_services_stopped": True, "provider_requests": 0},
        "rag": {key: replay[key] for key in rag_fields if key in replay},
        "rag_original_capture": {"subscription_requests": original["subscription_requests"], "expected_document_retrieved": sum(item["expected_document_retrieved"] for item in original["retrieval"]),
            "retrieval_questions": len(original["retrieval"]), "natural_answer": original["natural_answer"],
            "correction": "Explicit corpus argument was overwritten. Corrected retrieval uses the same frozen eight documents/questions; all real judge outputs and the original natural answer are replayed unchanged, with zero additional requests."},
        "vision": vision,
        "limits": ["No independent users or human label review", "Tiny authored RAG controls; same-model natural answer/judgment and three remaining retrieval misses",
            "Dependent revised NOAA replay; block threshold has no nominal coverage guarantee", "Declared vision corruptions retain engineering reference labels",
            "600-event serial drill and one fresh install do not establish production load/recovery objectives", "No registry publication, hosted deployment or external-recipient notification"]}
    content = json.dumps(report, indent=2) + "\n"
    if re.search(r"\b(?:gl_|go_|whsec_|sk-)[A-Za-z0-9_+/=-]{20,}", content):
        raise ValueError("Credential-like content found; do not publish")
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
