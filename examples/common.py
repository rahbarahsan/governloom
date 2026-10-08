"""Client-side integration and application-owned state. No collector storage access."""

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, build_opener

from fastapi import FastAPI, Request as WebRequest
from fastapi.responses import JSONResponse

from governloom.hook import MonitoringUnavailable, NoRedirect, RuntimeHook

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    content = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(content).hexdigest()


def http(endpoint, path, body=None, token=None, timeout=5):
    request = Request(endpoint.rstrip("/") + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        return json.load(response)


def hook(mode="observe"):
    return RuntimeHook(os.environ.get("GOVERNLOOM_ENDPOINT", "http://127.0.0.1:8000"),
                       os.environ["GOVERNLOOM_INGEST_KEY"], mode=mode, timeout_seconds=3)


class State:
    def __init__(self, project, path=None):
        self.path = Path(path or os.environ.get("MINI_STATE", f"data/miniapps/{project}.db")).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def put(self, identifier, kind, payload):
        with self.connect() as connection:
            connection.execute("INSERT INTO records VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                               (identifier, kind, json.dumps(payload, allow_nan=False)))
        return payload

    def get(self, identifier):
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM records WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Unknown application record")
        return json.loads(row[0])

    def list(self, kind):
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM records WHERE kind=? ORDER BY rowid DESC LIMIT 500", (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def revise(self, identifier, old, revised):
        with self.connect() as connection:
            changed = connection.execute("UPDATE records SET payload=? WHERE id=? AND payload=?",
                                         (json.dumps(revised, allow_nan=False), identifier, json.dumps(old, allow_nan=False)))
            if changed.rowcount != 1:
                raise ValueError("Concurrent application record update; reload")
        return revised


def service(name):
    api = FastAPI(title=name)

    @api.middleware("http")
    async def private_test_service(request: WebRequest, call_next):
        if request.client is None or request.client.host not in ("127.0.0.1", "::1", "testclient"):
            return JSONResponse({"detail": "Mini applications are local development services"}, status_code=403)
        if request.method == "POST" and request.headers.get("origin"):
            return JSONResponse({"detail": "Use the local CLI/HTTP client"}, status_code=403)
        return await call_next(request)

    @api.exception_handler(ValueError)
    async def invalid(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @api.exception_handler(MonitoringUnavailable)
    async def unavailable(_, exc):
        return JSONResponse({"detail": "Collector unavailable; inference continuation was not authorized"}, status_code=503)

    @api.get("/health")
    def health():
        return {"status": "ready", "service": name}

    return api
