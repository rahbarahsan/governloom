"""Crash-safe, bounded metadata observation. Text uses the transient hook instead."""
import hashlib
import json
import math
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .hook import MonitoringUnavailable, RuntimeHook
from .monitoring import EMAIL_PATTERN, SECRET_PATTERN, RuntimeEvent
from .schemas import uid

COUNTERS = ("emitted", "queued", "accepted", "dropped", "failed", "retries", "expired", "auth_failed", "rate_limited", "invalid")
GOVERNLOOM_CREDENTIAL = re.compile(r"\b(?:gl_|go_)[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


class DurableObservationHook(RuntimeHook):
    """At-least-once delivery; collector deduplicates exact frozen event bodies.

    close() preserves pending records. Terminal records are bounded and contain
    IDs/status only. Credentials are supplied afresh and never persisted.
    """
    def __init__(self, endpoint, key, *, outbox, queue_size=256, max_queue_bytes=1_000_000,
                 max_age_seconds=3600, max_attempts=10, backoff_seconds=1, auto_start=True, **kwargs):
        if kwargs.pop("mode", "observe") != "observe":
            raise ValueError("Durable observation cannot enforce a policy")
        super().__init__(endpoint, key, mode="observe", **kwargs)
        if type(queue_size) is not int or not 1 <= queue_size <= 10000:
            raise ValueError("Queue size must be 1..10000")
        if type(max_queue_bytes) is not int or not 1 <= max_queue_bytes <= 64_000_000:
            raise ValueError("Queue bytes must be 1..64000000")
        if not math.isfinite(max_age_seconds) or not 0 < max_age_seconds <= 86400:
            raise ValueError("Event age must be positive and at most one day")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 100:
            raise ValueError("Attempts must be 1..100")
        if not math.isfinite(backoff_seconds) or not 0 <= backoff_seconds <= 60:
            raise ValueError("Backoff must be 0..60 seconds")
        self.path = Path(outbox).resolve()
        if SECRET_PATTERN.search(self.endpoint) or EMAIL_PATTERN.search(self.endpoint) or GOVERNLOOM_CREDENTIAL.search(self.endpoint):
            raise ValueError("Collector endpoint must not contain sensitive metadata")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.owner = uid()
        self.closed = False
        self.stop = threading.Event()
        # Bind endpoint and credential digest, bounds and retry policy. Reopening
        # cannot accidentally send another application's pending data.
        config = json.dumps([self.endpoint, hashlib.sha256(key.encode()).hexdigest(), queue_size,
                            max_queue_bytes, max_age_seconds, max_attempts, backoff_seconds])
        self.capacity, self.byte_bound = queue_size, max_queue_bytes
        self.max_age, self.max_attempts, self.backoff = max_age_seconds, max_attempts, backoff_seconds
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA journal_size_limit=1048576")
            db.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, config TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS counts (name TEXT PRIMARY KEY, value INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body BLOB, size INTEGER NOT NULL, created REAL NOT NULL, deadline REAL NOT NULL, next REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, owner TEXT, lease REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending')")
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT config FROM settings WHERE id=1").fetchone()
            if existing and existing[0] != config:
                raise ValueError("Outbox binding/configuration differs; drain it before rotating keys or changing bounds")
            db.execute("INSERT OR IGNORE INTO settings VALUES (1, ?)", (config,))
            db.executemany("INSERT OR IGNORE INTO counts VALUES (?,0)", [(name,) for name in COUNTERS])
        self.worker = threading.Thread(target=self._run, name="governloom-durable-observation", daemon=True)
        if auto_start:
            self.worker.start()

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _count(db, name):
        db.execute("UPDATE counts SET value=value+1 WHERE name=?", (name,))

    @property
    def counters(self):
        with self._db() as db:
            return dict(db.execute("SELECT name,value FROM counts"))

    @property
    def stats(self):
        with self._db() as db:
            db.execute("BEGIN")
            counts = dict(db.execute("SELECT name,value FROM counts"))
            pending, size = db.execute("SELECT COUNT(*),COALESCE(SUM(size),0) FROM events WHERE status='pending'").fetchone()
        return {**counts, "pending": pending, "bytes_pending": size, "worker_alive": self.worker.is_alive(),
                "closed": self.closed, "durable": True, "text_coverage": "unavailable"}

    def terminal_records(self):
        with self._db() as db:
            return [{"event_id": row[0], "status": row[1], "attempts": row[2]}
                    for row in db.execute("SELECT id,status,attempts FROM events WHERE status!='pending' ORDER BY created DESC LIMIT 1000")]

    def emit(self, *, enforce=True, **fields):
        if fields.get("text") is not None or fields.get("grounding") is not None:
            raise ValueError("Durable outbox accepts metadata only; use RuntimeHook for transient text checks")
        event = RuntimeEvent(**{**fields, "client_mode": "observe"}).model_dump(mode="json")
        body = json.dumps(event, ensure_ascii=False, allow_nan=False).encode()
        if SECRET_PATTERN.search(body.decode()) or EMAIL_PATTERN.search(body.decode()) or GOVERNLOOM_CREDENTIAL.search(body.decode()) or self.key in body.decode():
            raise ValueError("Outbox metadata must not contain personal data or credentials")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._count(db, "emitted")
            old = db.execute("SELECT body,status FROM events WHERE id=?", (event["event_id"],)).fetchone()
            if old:
                if old[0] != body:
                    raise ValueError("Outbox event ID already used; IDs must be unique")
                return {"action": "queued", "event_id": event["event_id"], "duplicate": True}
            pending, size = db.execute("SELECT COUNT(*),COALESCE(SUM(size),0) FROM events WHERE status='pending'").fetchone()
            reason = "closed" if self.closed else "overflow" if pending >= self.capacity or size + len(body) > self.byte_bound else None
            if reason:
                self._count(db, "dropped")
                return {"action": "dropped", "event_id": event["event_id"], "reason": reason}
            instant = time.time()
            db.execute("INSERT INTO events (id,body,size,created,deadline,next) VALUES (?,?,?,?,?,?)",
                       (event["event_id"], body, len(body), instant, instant + self.max_age, instant))
            self._count(db, "queued")
        return {"action": "queued", "event_id": event["event_id"], "trace_id": event["trace_id"]}

    def _finish(self, db, identifier, status):
        db.execute("UPDATE events SET status=?,body=NULL,size=0,owner=NULL,lease=0 WHERE id=?", (status, identifier))
        self._count(db, status)
        db.execute("DELETE FROM events WHERE status!='pending' AND id NOT IN (SELECT id FROM events WHERE status!='pending' ORDER BY created DESC,id LIMIT 1000)")

    def _claim(self):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            instant = time.time()
            row = db.execute("SELECT id,body,attempts,deadline FROM events WHERE status='pending' AND next<=? AND lease<=? ORDER BY created,id LIMIT 1", (instant, instant)).fetchone()
            if not row:
                return None
            identifier, body, attempts, deadline = row
            if instant >= deadline or attempts >= self.max_attempts:
                self._finish(db, identifier, "expired" if instant >= deadline else "failed")
                return None
            if attempts:
                self._count(db, "retries")
            db.execute("UPDATE events SET attempts=attempts+1,owner=?,lease=? WHERE id=?", (self.owner, instant + self.timeout + 5, identifier))
            return identifier, body, attempts + 1, deadline

    def _run(self):
        while not self.stop.is_set():
            row = self._claim()
            if not row:
                self.stop.wait(0.05)
                continue
            identifier, body, attempt, deadline = row
            status, delay, code = "accepted", 0, None
            try:
                receipt = self.transport(json.loads(body))
                if not isinstance(receipt, dict) or receipt.get("event_id") != identifier or receipt.get("action") not in ("allow", "flag", "review", "block"):
                    raise MonitoringUnavailable("Invalid collector receipt", retryable=False)
                self.last_receipt = receipt
            except MonitoringUnavailable as exc:
                code = exc.status_code
                delay = max(self.backoff * 2 ** min(attempt - 1, 10), exc.retry_after_seconds or 0)
                status = "pending" if exc.retryable and attempt < self.max_attempts else "failed"
                if status == "pending" and time.time() + delay >= deadline:
                    status = "expired"
            except Exception:
                status = "failed"
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                owner = db.execute("SELECT owner,status FROM events WHERE id=?", (identifier,)).fetchone()
                if owner != (self.owner, "pending"):
                    continue  # Expired leases cannot finalize another worker's claim.
                if code in (401, 403):
                    self._count(db, "auth_failed")
                elif code == 429:
                    self._count(db, "rate_limited")
                elif status == "failed":
                    self._count(db, "invalid")
                if status == "pending":
                    db.execute("UPDATE events SET next=?,owner=NULL,lease=0 WHERE id=?", (time.time() + delay, identifier))
                else:
                    self._finish(db, identifier, status)

    def close(self, drain_seconds=5):
        if not math.isfinite(drain_seconds) or not 0 <= drain_seconds <= 300:
            raise ValueError("Drain deadline must be 0..300 seconds")
        self.closed = True
        deadline = time.monotonic() + drain_seconds
        while self.stats["pending"] and self.worker.is_alive() and time.monotonic() < deadline:
            self.stop.wait(0.05)
        self.stop.set()
        if self.worker.ident is not None:
            self.worker.join(max(0, deadline - time.monotonic()))
        return self.stats

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
