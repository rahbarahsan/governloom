"""Publish selected non-secret quickstart measurements for human review."""
import argparse
import json
import platform
import re
from pathlib import Path


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", type=Path, required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    fields = ("schema_version", "status", "source", "label_provenance", "new_provider_requests", "first_incident_seconds", "notification",
        "model_manifest", "model_quality", "policy_gate", "mitigation", "overhead", "owned_services_stopped", "elapsed_seconds", "setup_seconds",
        "setup_to_first_incident_seconds", "provenance")
    captures = []
    for name, path in (("fresh_install_development_baseline", options.fresh), ("final_committed_source_gate", options.final)):
        original = read(path)
        if original.get("status") != "completed" or not original.get("owned_services_stopped"):
            raise ValueError("Only completed, stopped captures can be published")
        captures.append({"name": name, "report": {key: original[key] for key in fields if key in original}})
    report = {"schema_version": 1, "date": "2026-10-10", "publication_runtime": {"os": platform.system(), "python": platform.python_version()},
        "capture_notes": "Fresh-install baseline preceded the new calibration-budget gate and final version/docs. Final gate capture follows the committed reliability, SDK, calibration and quickstart changes and records both Git revision and Python source snapshot hash. These are development captures, not independent deployments.",
        "captures": captures, "vision_gate_comparison": read(options.gate),
        "limits": ["One Windows installation, two serial loopback captures; not setup-time or throughput guarantees", "Scripted benchmark operator actions; verification is an attestation",
            "Public digit labels and small authored RAG evidence do not establish customer/domain performance", "Forecast historical dependence prevents a nominal false-alert guarantee", "No new provider requests, deployment or external-recipient notification"]}
    content = json.dumps(report, indent=2) + "\n"
    if re.search(r"\b(?:gl_|go_|whsec_|sk-)[A-Za-z0-9_+/=-]{20,}", content):
        raise ValueError("Credential-like content found; do not publish")
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
