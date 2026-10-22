"""Exercise trusted policy recommendations against owned applications over HTTP."""
import argparse
import json
from pathlib import Path

from examples.common import ROOT, http
from examples.discovery_testbed import vision_data, forecast_data
from examples.processes import Processes
from examples.tools.model import observations
from governloom.discovered_hook import DiscoveredObserver
from governloom.explorer import collect, write_bundle
from governloom.schemas import now
from governloom.service import checksum


def retrieval_observations():
    """Actual local retrieval with explicitly authored document relevance labels.

    Citation empty-list controls are deliberate, not newly generated AI answers.
    Documents/topics remain disjoint across the existing grouped evaluation split.
    """
    from examples.rag.model import Retriever
    from examples.rag.grouped_validation import SPECS
    retriever = Retriever(documents=[item[2] for item in SPECS])
    version = "policy-retrieval-" + checksum(retriever.manifest["documents"])[:16]
    rows = []
    for index, (split, group, document, question, *_) in enumerate(SPECS):
        passages = retriever.retrieve(question)
        # Labels concern documents, not semantic claim correctness. Preserve
        # rank and duplicate document positions rather than improving recall.
        source_ids = [passage["path"] for passage in passages]
        rows.append({"sample_id": group, "split": "calibration" if split == "cal" else "held_out",
            "citations": [] if index % 2 else source_ids[:1], "source_ids": source_ids,
            "relevant_source_ids": [document], "model_version": version, "application_version": "owned-retrieval-v1", "environment": "owned-test"})
    return rows, retriever


def run(directory, forecast_snapshot=None):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT/"data"):
        raise ValueError("Keep owned runs under data/")
    directory.mkdir(parents=True, exist_ok=False)
    sources = {"vision": vision_data(), "tools": observations(), "rag": retrieval_observations()}
    if forecast_snapshot:
        sources["forecasting"] = forecast_data(forecast_snapshot)
    report = {"status": "started", "created_at": now(), "provider_requests": 0,
              "scope": "Owned scripted applications; no independent discovery or label validation", "applications": {}}
    report["code_sha256"] = {name: checksum((ROOT/name).read_text(encoding="utf-8")) for name in (
        "src/governloom/policy_catalogue.py", "src/governloom/policy_guidance.py", "src/governloom/discovery.py",
        "src/governloom/discovery_calibration.py", "examples/policy_testbed.py", "examples/tools/model.py")}
    with Processes(directory/"logs") as processes:
        endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": f"sqlite:///{(directory/'collector.db').as_posix()}", "GOVERNLOOM_AUTH_MODE": "local"}, readiness="/api/health")
        catalogue = http(endpoint, "/api/policy-catalogue")
        report["catalogue_sha256"] = catalogue["sha256"]
        for name, (rows, model) in sources.items():
            appdir = directory/name
            appdir.mkdir()
            path = appdir/"traces.jsonl"
            path.write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf-8")
            bundle = collect(ROOT/"examples"/name, traces_path=path)
            write_bundle(bundle, appdir/"discovery.json")
            app = http(endpoint, "/api/applications", {"name": "Policy test "+name, "purpose": "Discover owned application", "owner": "Scripted owner", "expected_behavior": "Review monitoring recommendations"})
            prefix = f"/api/applications/{app['id']}"
            draft = http(endpoint, prefix+"/discoveries", bundle.model_dump())
            task = draft["analysis"]["task_type"]
            confirmation = http(endpoint, prefix+f"/discoveries/{draft['id']}/confirm", {"actor": "scripted-owner", "expected_checksum": draft["checksum"],
                "task_type": task, "purpose": draft["analysis"]["summary"], "mappings": draft["analysis"]["mappings"], "rationale": "Owned scripted review",
                "outcome_meaning_confirmed": name not in ("tools", "rag"), "relevance_meaning_confirmed": name == "rag",
                "allowed_tools": ["search"] if name == "tools" else None})
            plan = http(endpoint, prefix+"/discovery-plans", {"actor": "scripted-owner", "confirmation_id": confirmation["id"], "classification_false_positive_budget": .05})
            assert plan["status"] == "ready", plan["gaps"]
            assert plan["catalogue"]["sha256"] == catalogue["sha256"]
            (appdir/"plan.json").write_text(json.dumps(plan, indent=2)+"\n", encoding="utf-8")
            http(endpoint, prefix+f"/discovery-plans/{plan['id']}/activate", {"actor": "scripted-owner", "expected_policy_id": None, "acknowledge_limitations": True, "rationale": "Review owned observation flags"})
            key = http(endpoint, prefix+"/ingest-keys", {"actor": "scripted-owner", "name": "owned-consumer"})["key"]
            observer = DiscoveredObserver(endpoint, key, plan)
            if name == "tools":
                receipts = [observer.tool(row, trace_id=f"tool-{index}") for index, row in enumerate(rows)]
                clear = next(index for index, row in enumerate(rows) if row["tool_name"] == "search")
                flagged = next(index for index, row in enumerate(rows) if row["tool_name"] == "delete_draft")
                assert receipts[clear]["action"] == "allow" and receipts[flagged]["action"] == "flag"
                assert model.execute(rows[clear])["source_ids"]
                try:
                    model.execute(rows[flagged])
                    raise AssertionError("Independent authorization must reject deletion")
                except PermissionError:
                    pass
                control = observer.tool({**rows[clear], "tool_name": "delete_draft"}, trace_id="deliberate-engineering-control")
                assert control["action"] == "flag" and not model.deleted
                observed = {"model_selected_attempts": len(rows), "model_selected_flags": sum(item["action"] == "flag" for item in receipts),
                            "deliberate_control_flags": 1, "application_authorization": "independent local check denied deletion"}
            elif name == "rag":
                control = next(row for row in rows if row["split"] == "held_out" and not row["citations"])
                receipt = observer.output(control, trace_id="deliberate-citation-control")
                assert receipt["action"] == "flag"
                observed = {"retrieval": "actual local TF-IDF ranked passages", "relevance_labels": "repository-authored relevant document per question; no independent human review",
                            "corpus_manifest": model.manifest,
                            "new_answer_generations": 0, "citation_flags": "deliberate empty-citation engineering control"}
            elif name == "vision":
                chosen = min((row for row in rows if row["split"] == "held_out" and row["predicted_label"] != row["actual_label"]), key=lambda row: row["confidence"])
                receipt = observer.output(chosen, trace_id="actual-digit")
                assert receipt["action"] == "flag"
                observed = {"actual_model_flag": receipt["action"]}
            else:
                chosen = next(row for row in rows if row["split"] == "held_out" and abs(row["prediction"]-row["actual"]) > plan["metrics"][0]["threshold"])
                output = observer.output(chosen, trace_id="actual-forecast")
                receipt = observer.outcome(chosen, output)
                assert receipt["action"] == "flag"
                observed = {"actual_model_flag": receipt["action"]}
            incidents = http(endpoint, prefix+"/runtime-incidents")
            assert incidents and all(item["control_reference"]["catalogue_sha256"] == catalogue["sha256"] for item in incidents)
            report["applications"][name] = {"inferred_task": task, "selected_controls": plan["control_decisions"]["selected"],
                "metric_results": plan["metric_results"], "dataset_sha256": plan["dataset"]["sha256"], "incidents": len(incidents), **observed}
    report.update(status="completed", owned_services_stopped=True)
    (directory/"report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--forecast-snapshot", type=Path)
    args = parser.parse_args()
    result = run(args.directory, args.forecast_snapshot)
    print(json.dumps({"status": result["status"], "applications": list(result["applications"]), "provider_requests": 0}))
