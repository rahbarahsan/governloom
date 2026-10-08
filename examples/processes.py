"""Own subprocesses, bounded readiness and cleanup for local integration runs."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from examples.common import ROOT, http


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class Processes:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.children = []

    def start(self, module, environment, *, factory=False, port=None, readiness="/health"):
        port = port or free_port()
        endpoint = f"http://127.0.0.1:{port}"
        log = (self.directory / f"service-{port}.log").open("w", encoding="utf-8")
        command = [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port), "--no-access-log"]
        if factory:
            command.append("--factory")
        child = subprocess.Popen(command, cwd=ROOT, env={**os.environ, **environment}, stdout=log, stderr=log,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.children.append((child, log))
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f"Service {module} exited; inspect service-{port}.log")
            try:
                http(endpoint, readiness, timeout=0.5)
                return endpoint
            except (OSError, ValueError):
                time.sleep(0.05)
        raise RuntimeError(f"Service {module} readiness deadline exceeded")

    def close(self):
        for child, log in reversed(self.children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            log.close()
        self.children.clear()

    def stop_last(self):
        child, log = self.children.pop()
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        log.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
