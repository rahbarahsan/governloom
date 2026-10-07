"""Record synthetic fault-detection evidence using the shipped fixed fixtures."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from governloom.demo import approve_fixtures, seed, seed_gold
from governloom.schemas import RunRequest, now
from governloom.service import Workbench
from governloom.storage import Store
from governloom.worker import Worker


def verify(output: Path):
    with tempfile.TemporaryDirectory(prefix="governloom-evidence-") as directory:
        wb = Workbench(Store(f"sqlite:///{(Path(directory) / 'demo.db').as_posix()}"))
        application = seed(wb)
        seed_gold(wb, application["id"])
        approve_fixtures(wb, application["id"])
        dataset = wb.publish(application["id"], "release check (scripted fixture acceptance, not human review)")
        measurements = []
        baseline = None
        for target in ("clean", "irrelevant_retrieval", "outdated_source", "unsupported_statement", "invalid_citation", "timeout"):
            queued = wb.queue(RunRequest(dataset_id=dataset["id"], target=target, split="held_out"))
            Worker(wb.store).run_once()
            run = wb.run(queued["id"])
            assert run["status"] == "completed", run["error"]
            cases = {case["id"]: case for case in run["snapshot"]["cases"]}
            counts = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
            for result in run["results"]:
                fault_present = target != "clean" and (target not in ("invalid_citation", "unsupported_statement") or cases[result["case_id"]]["expected_behavior"] == "answer")
                detected = any(metric["status"] == "failed" for metric in result["metrics"])
                key = ("true_positive" if detected else "false_negative") if fault_present else ("false_positive" if detected else "true_negative")
                counts[key] += 1
            if baseline is None:
                baseline = run["id"]
            comparison = wb.compare(baseline, run["id"])
            assert comparison["compatible"] and comparison["matched_cases"] == 20
            measurements.append({"target": target, "cases": run["total"], "known_positive_cases": counts["true_positive"] + counts["false_negative"],
                                 **counts, "metrics": run["summary"], "matched_baseline_cases": comparison["matched_cases"]})
        assert measurements[0]["false_positive"] == 0
        assert measurements[3]["false_negative"] == 10
        corpus = Path(__file__).resolve().parents[1] / "src/governloom/demo/gold_cases.jsonl"
        report = {"schema_version": 1, "created_at": now(), "workbench_version": "0.1.0",
                  "target_version": "lexical-v1", "evaluator_version": "deterministic-v1",
                  "label_provenance": "repository-authored template fixtures; no independent human review",
                  "scope": "Synthetic integration check, not real-model or generalization evidence",
                  "fixture_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
                  "dataset_cases": 40, "calibration_cases": 20, "held_out_cases": 20,
                  "dataset_checksum": dataset["checksum"], "runs": measurements}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        wb.store.engine.dispose()
    print(f"Verified six 20-case runs; saved {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/release-evidence.json"))
    verify(parser.parse_args().output)
