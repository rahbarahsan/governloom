"""Publish selected owned discovery measurements; omit bundles, prompts and credentials."""
import argparse
import json
from pathlib import Path

from governloom.discovery import SECRET, Artifact, validate_semantic
from governloom.service import checksum


def publish(original, replay, output):
    original, replay = Path(original), Path(replay)
    capture = json.loads((original/"report.json").read_text(encoding="utf-8"))
    final = json.loads((replay/"report.json").read_text(encoding="utf-8"))
    for report in (capture,final):
        if report["status"]!="completed" or not report["owned_services_stopped"]:
            raise ValueError("Only completed captures with stopped services may be published")
    if capture["provider_requests"]!=3 or final["provider_requests"]!=0:
        raise ValueError("Expected exactly three original requests and zero replay requests")
    review = {}
    for task in ("vision","forecasting","rag"):
        bundle = json.loads((original/task/"discovery.json").read_text(encoding="utf-8"))
        artifacts = [Artifact.model_validate(item).model_dump() for item in bundle["artifacts"]]
        semantic = validate_semantic(bundle["semantic"],artifacts)
        review[task] = {"summary":semantic["summary"],"model":semantic["model"],"prompt_sha256":semantic["prompt_sha256"],
            "artifact_sha256":{item["path"]:item["sha256"] for item in artifacts},
            "exact_reference_checks":len(semantic["hypotheses"])+len(semantic["scenarios"]),
            "hypotheses":semantic["hypotheses"],"scenarios":semantic["scenarios"],
            "label_provenance":"Model-generated unreviewed suggestions; exact quotes verify provenance, not interpretation or correctness"}
    report = {"schema_version":1,"scope":"Three owned applications; scripted owner acceptance; not independent usability or discovery accuracy",
        "original_provider_requests":3,"replay_provider_requests":0,"original_elapsed_seconds":capture["elapsed_seconds"],
        "replay_elapsed_seconds":final["elapsed_seconds"],"original_report_sha256":checksum(capture),"replay_report_sha256":checksum(final),
        "replay_code_files_sha256":final.get("code_files_sha256"),"applications":final["applications"],"semantic_review":review,
        "limits":["Sources and field names contain useful task cues; this is not a blind external benchmark.",
            "Zero scripted corrections is not evidence that real owners need no corrections.",
            "Generated scenarios are not ground truth and are excluded from held-out counts.",
            "No new RAG answer was generated. Its single recorded answer cannot support calibration.",
            "Forecast threshold is a point-residual quantile, separate from the v0.5 block experiment.",
            "The rolling forecaster is scoped by fixed pipeline code plus snapshot; fitted coefficient hashes are recorded separately.",
            "Held-out budget warnings remain visible; thresholds were not retuned on held-out outcomes."]}
    text = json.dumps(report,indent=2,ensure_ascii=False)+"\n"
    if SECRET.search(text):
        raise ValueError("Public report contains a credential pattern")
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(text,encoding="utf-8")
    print(f"Published selected report: {output}")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original",type=Path,required=True)
    parser.add_argument("--replay",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    publish(args.original,args.replay,args.output)
