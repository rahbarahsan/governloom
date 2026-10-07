import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from governloom import subscription


def session_with_process(monkeypatch, tmp_path, events, timeout=False, authentication="Logged in using ChatGPT"):
    monkeypatch.setattr(subscription, "codex_command", lambda: "test-codex")
    monkeypatch.setenv("CODEX_API_KEY", "must-not-reach-child")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-child")
    seen = []

    def run(command, **kwargs):
        assert "CODEX_API_KEY" not in kwargs["env"] and "OPENAI_API_KEY" not in kwargs["env"]
        return SimpleNamespace(returncode=0, stdout=authentication if "login" in command else "test-cli-v1", stderr="")

    class Process:
        returncode = None
        killed = False

        def __init__(self, command, **kwargs):
            assert "--ignore-user-config" in command and "read-only" in command
            assert "CODEX_API_KEY" not in kwargs["env"]
            seen.append(self)

        def communicate(self, prompt=None, timeout=None):
            if timeout is not None and raise_timeout:
                raise subprocess.TimeoutExpired("test-codex", timeout)
            self.returncode = -1 if self.killed else 0
            return "\n".join(json.dumps(event) for event in events), ""

        def poll(self):
            return self.returncode

        def kill(self):
            self.killed = True

    raise_timeout = timeout
    monkeypatch.setattr(subscription.subprocess, "run", run)
    monkeypatch.setattr(subscription.subprocess, "Popen", Process)
    return subscription.SubscriptionSession(tmp_path / "requests", "test-model", 1, 10), seen


def test_subscription_auth_requires_chatgpt(monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="ChatGPT Codex login"):
        session_with_process(monkeypatch, tmp_path, [], authentication="Logged in using an API key")


def test_completed_capture_retains_usage_and_stops_at_budget(monkeypatch, tmp_path):
    output = {"answer": "A paraphrase", "behavior": "answer", "citations": ["missing-id"]}
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(output)}},
        {"type": "turn.completed", "usage": {"input_tokens": 81, "output_tokens": 15}},
    ]
    session, processes = session_with_process(monkeypatch, tmp_path, events)
    capture = session.request("Policy question", subscription.ANSWER_SCHEMA, "case-1")
    assert capture["output"] == output and capture["usage"]["input_tokens"] == 81
    assert capture["latency_ms"] >= 0
    # Invalid IDs are real target findings, not silently repaired by capture.
    assert subscription.validate_answer(output, []) == output
    with pytest.raises(ValueError, match="limit exceeded"):
        session.request("Another question", subscription.ANSWER_SCHEMA, "case-2")
    assert len(processes) == 1


@pytest.mark.parametrize("failure", ["tool", "turn", "timeout"])
def test_failed_capture_is_durable_and_never_retried(monkeypatch, tmp_path, failure):
    events = [{"type": "turn.completed", "usage": {}}]
    if failure == "tool":
        events.append({"type": "item.completed", "item": {"type": "command_execution"}})
    elif failure == "turn":
        events = [{"type": "turn.failed"}]
    session, processes = session_with_process(monkeypatch, tmp_path, events, timeout=failure == "timeout")
    with pytest.raises((ValueError, subprocess.TimeoutExpired)):
        session.request("Question", subscription.ANSWER_SCHEMA, "case")
    record = json.loads((tmp_path / "requests/request-01/record.json").read_text(encoding="utf-8"))
    assert record["status"] == "error" and session.requests == 1 and len(processes) == 1
    if failure == "timeout":
        assert processes[0].killed


def test_judge_evidence_validation_rejects_invented_support():
    source = {"id": "policy", "content": "Invoices arrive on the first day.", "content_hash": "hash"}
    answer = "You receive unlimited credit."
    estimate = {"claims": [{"claim": answer, "verdict": "supported", "explanation": "Claimed support",
                            "evidence": [{"source_id": "policy", "quote": "Unlimited credit is available."}]}]}
    with pytest.raises(ValueError, match="frozen source"):
        subscription.validate_judgment(estimate, answer, [source])
    estimate["claims"][0].update(verdict="unsupported", evidence=[])
    assert subscription.validate_judgment(estimate, answer, [source])["claims"][0]["verdict"] == "unsupported"


def test_local_capture_evaluates_observed_answers_and_preserves_misses(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts/run_subscription_eval.py"
    spec = importlib.util.spec_from_file_location("subscription_experiment", path)
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)

    class FakeSession:
        cli_version = "test-only"
        requests = 0

        def __init__(self, *args):
            pass

        def request(self, prompt, schema, label):
            self.requests += 1
            payload = json.loads(prompt.split("\n", 1)[1])
            assert "reference_answer" not in payload and "expected_behavior" not in payload
            if schema == subscription.ANSWER_SCHEMA:
                question = payload["question"]
                if "bill" in question:
                    answer, behavior, document = "Your bill arrives at the start of each month.", "answer", 0
                elif "key" in question:
                    answer, behavior, document = "Complete identity checks, then reset the key in Account Settings.", "answer", 1
                elif "waive" in question:
                    answer, behavior, document = "That exception is not documented.", "abstain", None
                else:
                    answer, behavior, document = "Which credit entitlement are you referring to?", "clarify", None
                output = {"answer": answer, "behavior": behavior,
                          "citations": [payload["documents"][document]["source_id"]] if document is not None else []}
            else:
                output = {"claims": [{"claim": payload["answer"], "verdict": "insufficient_evidence",
                                      "explanation": "Integration fake, not a quality measurement", "evidence": []}]}
            return {"output": output, "usage": {"input_tokens": 100, "output_tokens": 20}, "latency_ms": 1}

    monkeypatch.setattr(experiment, "SubscriptionSession", FakeSession)
    report = experiment.execute(tmp_path / "capture", "fake-only", 8, 10)
    assert report["status"] == "completed" and report["requests_attempted"] == 8
    assert report["baseline_run"]["summary"]["task_success"]["passed"] == 4
    assert report["baseline_run"]["summary"]["reference_agreement"]["failed"] == 2
    assert report["controlled_run"]["summary"]["latency"]["insufficient_evidence"] == 2
    assert report["comparison"]["matched_cases"] == 4
    assert "unavailable" in report["calibration"]
    with pytest.raises(ValueError, match="fresh output"):
        experiment.execute(tmp_path / "capture", "fake-only", 8, 10)
