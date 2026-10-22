"""Fresh wheel/venv consumer check; no editable checkout or provider requests."""
import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


def run(directory):
    root = Path(__file__).resolve().parents[1]
    directory = (root / directory).resolve()
    if not directory.is_relative_to(root / "data"):
        raise ValueError("Keep the fresh check beneath data/")
    directory.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    def execute(command, **kwargs):
        return subprocess.run([str(value) for value in command], check=True, creationflags=flags, **kwargs)
    execute([sys.executable, "-m", "pip", "wheel", root, "--no-deps", "--wheel-dir", directory / "wheels"])
    execute([sys.executable, "-m", "venv", directory / "venv"])
    python = directory / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    execute([python, "-m", "pip", "install", "-r", root / "requirements.lock", "-r", root / "examples/requirements.txt"])
    execute([python, "-m", "pip", "install", "--no-deps", next((directory / "wheels").glob("governloom-*.whl"))])
    consumer = directory / "consumer"
    consumer.mkdir()
    shutil.copyfile(root / "examples/standalone/consumer.py", consumer / "consumer.py")
    shutil.copyfile(root / "examples/standalone/policy_consumer.py", consumer / "policy_consumer.py")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    password = secrets.token_urlsafe(32)
    environment = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "OPENAI_API_KEY", "CODEX_API_KEY")}
    environment.update(GOVERNLOOM_DB=f"sqlite:///{(directory / 'collector.db').as_posix()}", GOVERNLOOM_AUTH_MODE="operators")
    execute([python, "-m", "governloom.cli", "bootstrap-admin", "onboarding-admin", "--password-stdin"], cwd=consumer, env=environment, input=password + "\n", text=True, capture_output=True)
    setup_seconds = round(time.perf_counter() - began, 3)
    def call(path, body=None, token=None):
        request = Request(endpoint + "/api" + path, data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
        with urlopen(request, timeout=3) as response:
            return json.load(response)
    report = {"schema_version": 1, "status": "started", "setup_seconds": setup_seconds, "provider_requests": 0,
        "scope": "Owned standalone fresh-wheel consumer, not independent developer feedback"}
    with (directory / "collector.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([str(python), "-m", "uvicorn", "governloom.api:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
            cwd=consumer, env=environment, stdout=log, stderr=log, creationflags=flags)
        try:
            deadline = time.monotonic() + 30
            while True:
                try:
                    call("/health"); break
                except OSError:
                    assert server.poll() is None and time.monotonic() < deadline
                    time.sleep(.1)
            token = call("/auth/login", {"username": "onboarding-admin", "password": password})["token"]
            app = call("/applications", {"name": "Standalone LogisticRegression", "purpose": "Test installed SDK boundaries", "owner": "onboarding-admin", "expected_behavior": "Withhold illustrative uncertain natural error"}, token)
            prefix = f"/applications/{app['id']}"
            call(prefix + "/monitor-policy", {"name": "Illustrative confidence gate", "actor": "scripted", "rationale": "Integration check, not calibrated quality or production policy", "rules": [
                {"id": "confidence", "name": "Low confidence", "detector": "metric_threshold", "phase": "output", "metric": "confidence", "comparator": "lt", "threshold": .95, "action": "block", "mitigation": "Inspect actual digit"}]}, token)
            key = call(prefix + "/ingest-keys", {"name": "consumer", "actor": "scripted"}, token)["key"]
            result = execute([python, "consumer.py"], cwd=consumer, env={**environment, "GOVERNLOOM_ENDPOINT": endpoint, "GOVERNLOOM_INGEST_KEY": key}, capture_output=True, text=True)
            outcome = json.loads(result.stdout)
            assert Path(outcome["installed_package"]).is_relative_to(directory / "venv")
            assert call(prefix + "/runtime-alerts", token=token)
            report.update(status="completed", consumer=outcome, setup_to_first_incident_seconds=round(time.perf_counter() - began, 3))
            policies = execute([python, "policy_consumer.py"], cwd=consumer,
                env={**environment, "GOVERNLOOM_ENDPOINT": endpoint, "GOVERNLOOM_OPERATOR_TOKEN": token}, capture_output=True, text=True)
            report["policy_discovery_consumer"] = json.loads(policies.stdout)
        except BaseException:
            report["status"] = "failed"
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait(timeout=5)
            report["owned_services_stopped"] = server.poll() is not None
            (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.directory), indent=2))
