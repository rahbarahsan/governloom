"""Opt-in, trusted local Codex capture. Never used by the API or worker."""

import json
import math
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path


ANSWER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "behavior": {"type": "string", "enum": ["answer", "abstain", "clarify"]},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "behavior", "citations"],
}

JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"claims": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "claim": {"type": "string"},
            "verdict": {"type": "string", "enum": ["supported", "unsupported", "insufficient_evidence"]},
            "explanation": {"type": "string"},
            "evidence": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"source_id": {"type": "string"}, "quote": {"type": "string"}},
                "required": ["source_id", "quote"],
            }},
        },
        "required": ["claim", "verdict", "explanation", "evidence"],
    }}},
    "required": ["claims"],
}


def codex_command():
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("Install the Codex CLI and run 'codex login' with ChatGPT first")
    path = Path(executable)
    if os.name == "nt" and path.suffix.lower() in (".cmd", ".ps1"):
        # Invoke the native npm package binary directly: no shell interpretation
        # of prompts and no Node wrapper left behind after a deadline.
        target = "aarch64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
        package = "codex-win32-arm64" if target == "aarch64" else "codex-win32-x64"
        root = path.parent / "node_modules" / "@openai" / "codex"
        candidates = [
            root / "node_modules" / "@openai" / package / "vendor" / f"{target}-pc-windows-msvc" / "bin" / "codex.exe",
            root / "vendor" / f"{target}-pc-windows-msvc" / "bin" / "codex.exe",
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            raise ValueError("Native Codex binary not found in the npm installation")
    return str(path)


class SubscriptionSession:
    def __init__(self, directory, model, max_requests, timeout_seconds=180):
        if not model.strip() or not 1 <= max_requests <= 20:
            raise ValueError("Specify a model selector and a request limit from 1 to 20")
        if not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 300:
            raise ValueError("Deadline must be from 1 to 300 seconds")
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=False)
        self.model = model
        self.max_requests = max_requests
        self.timeout = timeout_seconds
        self.requests = 0
        self.executable = codex_command()
        self.environment = dict(os.environ)
        # A key in the surrounding developer environment must never silently
        # switch this explicitly subscription-only experiment to API billing.
        for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"):
            self.environment.pop(name, None)
        status = subprocess.run([self.executable, "login", "status"], env=self.environment,
                                capture_output=True, text=True, timeout=15, encoding="utf-8")
        if status.returncode or "Logged in using ChatGPT" not in status.stdout + status.stderr:
            raise ValueError("This experiment requires an existing ChatGPT Codex login; API-key login is not accepted")
        version = subprocess.run([self.executable, "--version"], capture_output=True,
                                 text=True, timeout=15, encoding="utf-8", env=self.environment)
        if version.returncode:
            raise ValueError("Could not inspect Codex CLI version")
        self.cli_version = version.stdout.strip()

    def request(self, prompt, schema, label):
        if self.requests >= self.max_requests:
            raise ValueError("Subscription request limit exceeded; no implicit retries")
        if len(prompt.encode("utf-8")) > 32_000:
            raise ValueError("Prompt exceeds the 32 KB input bound")
        self.requests += 1
        request_dir = self.directory / f"request-{self.requests:02d}"
        request_dir.mkdir()
        schema_path = request_dir / "schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        record = {"label": label, "model_selector": self.model, "status": "started", "prompt": prompt,
                  "schema": schema, "timeout_seconds": self.timeout, "usage": None,
                  "cli_version": self.cli_version, "authentication": "ChatGPT subscription"}
        record_path = request_dir / "record.json"
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        command = [self.executable, "exec", "--ignore-user-config", "--ephemeral",
                   "--skip-git-repo-check", "--sandbox", "read-only", "--disable", "shell_tool",
                   "--model", self.model, "--json", "--color", "never",
                   "-c", "model_reasoning_effort=\"low\"",
                   "--output-schema", str(schema_path), "-"]
        started = time.perf_counter()
        process = None
        try:
            process = subprocess.Popen(command, cwd=request_dir, env=self.environment,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding="utf-8", creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
            stdout, stderr = process.communicate(prompt, timeout=self.timeout)
            # Local diagnostics are deliberately separate from publishable records.
            (request_dir / "events.jsonl").write_text(stdout, encoding="utf-8")
            (request_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
            events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            completed = [event for event in events if event.get("type") == "turn.completed"]
            forbidden = {"command_execution", "file_change", "mcp_tool_call", "web_search"}
            if any(event.get("item", {}).get("type") in forbidden for event in events):
                raise ValueError("Target attempted tool use; reject this capture")
            if process.returncode or len(completed) != 1 or any(event.get("type") in ("error", "turn.failed") for event in events):
                raise ValueError("Codex inference did not complete successfully; inspect local request diagnostics")
            messages = [event["item"]["text"] for event in events
                        if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message"]
            if not messages:
                raise ValueError("Codex returned no final message")
            output = json.loads(messages[-1])
            record.update(status="completed", output=output, usage=completed[0].get("usage"))
            return record
        except BaseException as exc:
            record.update(status="error", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                stdout, stderr = process.communicate()
                (request_dir / "events.jsonl").write_text(stdout, encoding="utf-8")
                (request_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
            record["latency_ms"] = (time.perf_counter() - started) * 1000
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_answer(output, sources):
    if set(output) != {"answer", "behavior", "citations"} or not isinstance(output["answer"], str) or not output["answer"].strip():
        raise ValueError("Invalid target answer")
    if output["behavior"] not in ("answer", "abstain", "clarify") or not isinstance(output["citations"], list):
        raise ValueError("Invalid target behavior/citations")
    if any(not isinstance(citation, str) for citation in output["citations"]):
        raise ValueError("Citation IDs must be strings")
    # Preserve nonexistent citations as target findings; do not silently repair.
    return output


def validate_judgment(output, answer, sources):
    if set(output) != {"claims"} or not isinstance(output["claims"], list) or not output["claims"]:
        raise ValueError("Judge must return inspectable claims")
    by_id = {source["id"]: source for source in sources}
    for claim in output["claims"]:
        if set(claim) != {"claim", "verdict", "explanation", "evidence"}:
            raise ValueError("Invalid claim fields")
        if not isinstance(claim["claim"], str) or not claim["claim"].strip() or claim["claim"] not in answer:
            raise ValueError("Judge claim must be an exact excerpt from the observed answer")
        if claim["verdict"] not in ("supported", "unsupported", "insufficient_evidence"):
            raise ValueError("Invalid claim verdict")
        if not isinstance(claim["explanation"], str) or not claim["explanation"].strip() or not isinstance(claim["evidence"], list):
            raise ValueError("Invalid claim explanation/evidence")
        if claim["verdict"] == "supported" and not claim["evidence"]:
            raise ValueError("Supported claims need source passages")
        for evidence in claim["evidence"]:
            if set(evidence) != {"source_id", "quote"}:
                raise ValueError("Invalid evidence fields")
            source = by_id.get(evidence["source_id"])
            if not source or not isinstance(evidence["quote"], str) or not evidence["quote"].strip() or evidence["quote"] not in source["content"]:
                raise ValueError("Judge evidence does not occur in the frozen source")
            evidence["start"] = source["content"].index(evidence["quote"])
            evidence["end"] = evidence["start"] + len(evidence["quote"])
            evidence["content_hash"] = source["content_hash"]
    return output
