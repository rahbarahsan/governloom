"""Owned loopback receiver: verifies signatures and persists idempotent acceptance."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

from examples.common import service
from governloom.webhooks import verify_webhook


def create_app():
    api = service("Signed incident receiver")
    path = Path(os.environ["RECEIVER_DB"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS notifications (id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL)")

    @api.get("/health")
    def health():
        return {"status": "ok", "service": "signed-local-receiver"}

    @api.post("/incidents")
    async def receive(request: Request):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 20_000:
                return JSONResponse({"detail": "Notification exceeds 20 KB"}, status_code=413)
        try:
            secret = Path(os.environ["RECEIVER_SECRET_FILE"]).read_text(encoding="ascii")
            identifier = verify_webhook(secret, request.headers, bytes(data))
            body = json.loads(data)
            if body.get("id") != identifier or body.get("schema_version") != 1 or body.get("type") != "governloom.incident.escalated":
                raise ValueError()
        except (OSError, ValueError, TypeError):
            return JSONResponse({"detail": "Notification verification failed"}, status_code=401)
        digest = hashlib.sha256(data).hexdigest()
        with sqlite3.connect(path) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT digest FROM notifications WHERE id=?", (identifier,)).fetchone()
            if existing and existing[0] != digest:
                return JSONResponse({"detail": "Conflicting notification ID"}, status_code=409)
            if not existing:
                db.execute("INSERT INTO notifications VALUES(?,?,?)", (identifier, digest, data.decode()))
        if not existing and os.environ.get("RECEIVER_LOSE_FIRST_ACK") == "1":
            return JSONResponse({"detail": "Declared lost receipt after durable acceptance"}, status_code=503)
        return {"accepted_id": identifier, "duplicate": existing is not None}

    @api.get("/notifications")
    def notifications():
        with sqlite3.connect(path) as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM notifications ORDER BY rowid")]

    return api
