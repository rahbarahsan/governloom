"""Measure real model signals and opt-in source-backed judgments through HTTP."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

from scipy.stats import ks_2samp

from examples.common import ROOT, digest, http
from examples.forecasting.model import ForecastModel
from examples.processes import Processes
from examples.vision.model import DigitModel
from governloom.detectors import Profiles, distribution_check
from governloom.schemas import now


def confusion(rows):
    result = dict(true_positives=0, false_positives=0, true_negatives=0, false_negatives=0, unavailable=0)
    for row in rows:
        if row.get("unavailable"):
            result["unavailable"] += 1
        else:
            key = "true_positives" if row["expected_risk"] and row["triggered"] else "false_negatives" if row["expected_risk"] else "false_positives" if row["triggered"] else "true_negatives"
            result[key] += 1
    return result


def windows(reference, groups, size):
    rows = []
    for scenario, expected, values in groups:
        for offset in range(0, len(values) - size + 1, size):
            sample = values[offset:offset + size]
            measured = distribution_check(reference, sample, window_index=len(rows)+1)
            # Independent library cross-check of the ECDF statistic, not its
            # continuous-distribution p-value (vision confidence has ties).
            assert abs(measured["distance"] - ks_2samp(reference, sample).statistic) < 1e-12
            rows.append({"scenario": scenario, "expected_risk": expected, "values": sample,
                         "unavailable": not measured["can_detect"], **measured})
    return rows


def calibration(rows, source_hash, groups, *, provenance="observed_outcomes", description):
    return {"dataset_sha256": source_hash, "labels_sha256": digest([[r["scenario"], r["expected_risk"]] for r in rows]),
            "label_provenance": provenance, "description": description, "calibration_groups": groups,
            "held_out_groups": sorted({row["scenario"] for row in rows}), **confusion(rows)}


def run(directory, forecast_path, subscription=False):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "created_at": now(), "status": "running", "subscription_enabled": subscription,
              "interpretation": "Engineering validation on public mini applications; not independent human/customer calibration", "profiles": [], "subscription_requests": 0}
    try:
        digits = DigitModel()
        reference = digits.classifier.predict_proba(digits.images[digits.calibration]).max(axis=1).tolist()
        vision_groups = [("held-natural", False, [digits.predict(digits.sample(i))["confidence"] for i in digits.held_out])]
        vision_groups += [("held-" + fault, True, [digits.predict(digits.sample(i, fault))["confidence"] for i in digits.held_out]) for fault in ("occlusion", "noise")]
        vision_rows = windows(reference, vision_groups, 120)
        forecast = ForecastModel(forecast_path)
        residuals = [abs(forecast.predict(date)["prediction"] - forecast.rows[date]["value"]) for date in forecast.calibration]
        evaluation = forecast.evaluate()
        forecast_rows = windows(residuals, [("held-natural", False, [r["absolute_error"] for r in evaluation["rows"]]),
            ("held-offset-fault", True, [abs(r["prediction"] + 5 - r["actual"]) for r in evaluation["rows"]])], 24)
        specs = [("Vision confidence distribution", "vision", digits.version, "confidence", reference, 120, vision_rows, digits.manifest["dataset_hash"], ["train", "calibration"], "independent_samples"),
                 ("Forecast residual replay", "forecasting", "rolling-residual-replay-" + digest(forecast.manifest)[:12], "absolute_error", residuals, 24, forecast_rows, forecast.data_hash, ["2019-2020"], "dependent_replay")]
        report["vision"] = {"manifest": digits.manifest, "quality": {k:v for k,v in digits.evaluate().items() if k != "rows"}, "distribution_controls": confusion(vision_rows), "unit": "non-overlapping 120-image windows", "assumption_limit": "Writer dependence/sampling shift are not certified by this benchmark"}
        report["forecasting"] = {"manifest": forecast.manifest, "quality": {k:v for k,v in evaluation.items() if k != "rows"}, "distribution_controls": confusion(forecast_rows), "unit": "24-month historical windows", "nominal_probability_valid": False, "limitation": "Serially dependent revised historical series; reports an empirical replay signal only"}
        admin = "detector-validation-" + os.urandom(24).hex()
        with Processes(directory / "logs") as processes:
            endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": f"sqlite:///{(directory/'collector.db').as_posix()}", "GOVERNLOOM_ADMIN_TOKEN": admin, "GOVERNLOOM_AUTH_MODE": "local"}, readiness="/api/health")
            def call(path, body=None):
                return http(endpoint, "/api" + path, body, admin)
            def provision(name, bodies):
                app = call("/applications", {"name": name, "purpose": "Actual-model detector validation", "owner": "Engineering benchmark", "expected_behavior": "Measure controls and expose limitations"})
                prefix = f"/applications/{app['id']}"
                profiles = []
                for body in bodies:
                    profile = call(prefix + "/detector-profiles", body)
                    call(f"/detector-profiles/{profile['id']}/approve", {"actor": "engineering-runner", "expected_checksum": profile["checksum"], "rationale": "Accept public benchmark evidence for experimental review; not independent validation"})
                    profiles.append(profile)
                    report["profiles"].append({"application": name, "request": body, "record": profile})
                call(prefix + "/monitor-policy", {"name": name + " evidence", "actor": "engineering-runner", "rationale": "Frozen reference and grouped controls", "expected_events_per_minute": 10000,
                    "rules": [{"id": f"evidence_{i}", "name": p["name"], "detector": p["kind"], "profile_id": p["id"], "environment": p["environment"], "phase": "outcome" if p["task_type"] == "forecasting" else "output", "action": "review", "mitigation": "Inspect outcomes and quoted evidence before mitigation"} for i,p in enumerate(profiles)]})
                key = call(prefix + "/ingest-keys", {"name": "benchmark", "actor": "engineering-runner"})["key"]
                return app, profiles, key
            for name, task, version, metric, baseline, size, rows, fingerprint, cal_groups, assumption in specs:
                body = dict(name=name, actor="engineering-runner", kind="distribution_shift", task_type=task, phase="outcome" if task == "forecasting" else "output", environment="validation-replay", model_version=version, application_version="detector-benchmark-v1", metric=metric, reference=baseline, window_size=size, alpha=.05, minimum_effect=.2, sampling_assumption=assumption,
                    calibration=calibration(rows, fingerprint, cal_groups, description="Baseline and rule frozen before held-out windows; declared perturbations are detection controls, not labels of individual prediction correctness"))
                app, profiles, key = provision(name, [body])
                for row in rows:
                    for value in row["values"]:
                        receipt = http(endpoint, "/api/runtime/events", dict(trace_id="benchmark-"+os.urandom(8).hex(), phase="outcome" if task == "forecasting" else "output", task_type=task, environment=body["environment"], model_version=version, application_version=body["application_version"], metrics={metric:value}), key)
                    check = receipt["checks"][0]
                    assert (check["status"] == "triggered") == row["triggered"]
                    assert check["evidence"]["window_index"] == row["window_index"]
                report[task if task == "forecasting" else "vision"]["windows"] = [{k:v for k,v in row.items() if k != "values"} for row in rows]
            if subscription:
                from examples.rag.model import Retriever, SubscriptionJudge, RUBRIC_VERSION
                from governloom.subscription import SubscriptionSession
                retriever = Retriever()
                session = SubscriptionSession(directory / "judge-captures", "gpt-6.1-sol", max_requests=8)
                judge = SubscriptionJudge(session)
                groups = [
                    ("keys", "Only its hash is stored.", "The collector stores only a hash of each ingestion key.", "The collector stores every ingestion key in plaintext."),
                    ("binary-inputs", "Binary inputs and provider keys are unnecessary.", "Binary inputs and provider keys are unnecessary for telemetry.", "Telemetry requires automatic upload of all binary inputs and the provider key."),
                    ("enforcement", "output blocks withhold results.", "Output blocks withhold results.", "Output blocks always return the blocked result to the caller."),
                    ("citation-support", "Source-ID membership does not", "Source-ID membership does not establish claim support.", "Source-ID membership proves factual support for every answer claim.")]
                pseudo = dict(id="benchmark-profile", checksum="0"*64, engine_version="evidence-detectors-v1", corpus_sha256=retriever.manifest["corpus_sha256"], judge_version=f"gpt-6.1-sol@{session.cli_version}", rubric_version=RUBRIC_VERSION,
                    source_hashes={s["id"]:s["content_hash"] for s in retriever.sources}, unsupported_fraction_threshold=0, calibration=CAL_PLACEHOLDER)
                authored = []
                for group, marker, supported, unsupported in groups:
                    source = next(s for s in retriever.sources if marker in s["content"])
                    for risk, answer in ((False, supported), (True, unsupported)):
                        judged = judge.judge(answer, [source])
                        grounding = {"profile_id": pseudo["id"], "corpus_sha256": pseudo["corpus_sha256"], "judge_version": judged["judge_version"], "rubric_version": RUBRIC_VERSION, "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(), "claims": judged["judgment"]["claims"], "sources": [{"id": source["id"], "content": source["content"]}]}
                        from governloom.monitoring import RuntimeEvent
                        event = RuntimeEvent(trace_id="judge-benchmark", phase="output", task_type="rag", model_version="benchmark", application_version="benchmark", text=answer, grounding=grounding, source_ids=[source["id"]], citations=[source["id"]])
                        missing, flagged, evidence = Profiles.grounding(pseudo, event, {})
                        authored.append({"scenario": group, "expected_risk": risk, "triggered": flagged, "unavailable": missing, "answer": answer, "grounding": grounding, "source_ids": [source["id"]], "evidence": evidence, "usage": judged["usage"]})
                        print(f"Judged {group} {'perturbation' if risk else 'source-supported'}: {'unavailable' if missing else 'review' if flagged else 'clear'}", flush=True)
                held = [r for r in authored if r["scenario"] in ("enforcement", "citation-support")]
                labels = calibration(held, digest([{k:r[k] for k in ("scenario", "answer", "source_ids")} for r in authored]), ["keys", "binary-inputs"], provenance="engineering", description="Eight authored claims over real repository passages; paired topics grouped, four calibration and four held-out. No independent human labelers. Threshold zero predeclared and checked on calibration only.")
                model_version = "gpt-6.1-sol-" + retriever.manifest["corpus_sha256"][:12]
                bodies = [dict(name="Documentation claim support", actor="engineering-runner", kind="claim_support", task_type="rag", environment=env, model_version=model_version, application_version="documentation-service-v1", calibration=labels,
                    corpus_sha256=pseudo["corpus_sha256"], judge_version=pseudo["judge_version"], rubric_version=RUBRIC_VERSION, source_hashes=pseudo["source_hashes"], unsupported_fraction_threshold=0) for env in ("validation-authored", "testbed-natural")]
                app, profiles, key = provision("Documentation RAG grounding", bodies)
                for row in authored:
                    body = copy.deepcopy(row["grounding"]); body["profile_id"] = profiles[0]["id"]
                    receipt = http(endpoint, "/api/runtime/events", dict(trace_id="authored-"+os.urandom(8).hex(), phase="output", task_type="rag", environment="validation-authored", model_version=model_version, application_version="documentation-service-v1", text=row["answer"], grounding=body, source_ids=row["source_ids"], citations=row["source_ids"]), key)
                    assert (receipt["checks"][0]["status"] == "triggered") == row["triggered"]
                rag_endpoint = processes.start("examples.rag.app:create_app", {"GOVERNLOOM_ENDPOINT": endpoint, "GOVERNLOOM_INGEST_KEY": key, "MINI_STATE": str(directory/"rag.db"), "ALLOW_SUBSCRIPTION": "1", "RAG_MODEL": "gpt-6.1-sol", "RAG_CAPTURE": str(directory/"target-capture"), "RAG_MAX_REQUESTS": "1", "RAG_GROUNDING_PROFILE": profiles[1]["id"], "RAG_JUDGE_CAPTURE": str(directory/"natural-judge-capture"), "RAG_JUDGE_MAX_REQUESTS": "1"}, factory=True)
                natural = http(rag_endpoint, "/answer", {"question": "How does GovernLoom prevent tool side effects when an enforce-mode policy blocks?"}, timeout=370)
                report["rag"] = {"corpus": retriever.manifest, "judge_version": pseudo["judge_version"], "rubric_version": RUBRIC_VERSION, "calibration_controls": confusion(authored[:4]), "held_out_controls": confusion(held),
                    "natural_generated_answer": natural, "benchmark": [{k:v for k,v in row.items() if k not in ("grounding", "answer")} for row in authored], "limitation": "Small engineering-authored calibration; quote provenance and source coverage do not prove semantic reliability"}
                report["subscription_requests"] = session.requests + 2
            report["status"] = "completed"
        report["owned_services_stopped"] = True
    except BaseException as exc:
        report.update(status="error", error_type=type(exc).__name__)
        raise
    finally:
        records = [json.loads(path.read_text(encoding="utf-8")) for path in directory.glob("**/record.json")]
        report["subscription_requests"] = len(records)
        report["subscription_completed"] = sum(record["status"] == "completed" for record in records)
        report["owned_services_stopped"] = True
        report["code_sha256"] = digest({str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes()) for base in (ROOT/"src", ROOT/"examples") for path in sorted(base.rglob("*.py"))})
        (directory/"report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "vision": report["vision"]["distribution_controls"], "forecasting": report["forecasting"]["distribution_controls"], "rag": report.get("rag", {}).get("held_out_controls"), "subscription_requests": report["subscription_requests"]}), flush=True)
    return report


CAL_PLACEHOLDER = {"label_provenance": "engineering"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--forecast-data", type=Path, required=True)
    parser.add_argument("--subscription", action="store_true", help="Explicit bounded opt-in: eight benchmark judges plus one target and one natural judge")
    args = parser.parse_args()
    if args.subscription:
        os.environ["ALLOW_SUBSCRIPTION"] = "1"
    run(args.directory, args.forecast_data, args.subscription)
