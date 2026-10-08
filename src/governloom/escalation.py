"""Audited notification delivery to an explicitly identified local test sink."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from sqlalchemy import or_, select

from .hook import NoRedirect, retry_delay
from .schemas import now, uid
from .storage import Entity


def dispatch_test_sink(monitor, endpoint, actor, limit=10):
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port or
        parsed.path != "/governloom-test-sink" or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Use http://127.0.0.1:<port>/governloom-test-sink")
    if not actor.strip() or len(actor) > 200 or not 1 <= limit <= 100:
        raise ValueError("Specify an actor and dispatch limit 1..100")
    opener = build_opener(NoRedirect())
    # Prevent accidental POSTs to an unrelated local service. No admin/ingest
    # credentials are ever sent to the sink.
    try:
        with opener.open(endpoint, timeout=2) as response:
            identity = json.loads(response.read(4097))
        if identity != {"service": "governloom-test-sink", "schema_version": 1}:
            raise ValueError("Endpoint is not the identified test sink")
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise ValueError("Test sink identity check failed; queue left untouched") from None
    result = {"delivered": 0, "retry_pending": 0, "failed": 0}
    for _ in range(limit):
        instant, lease = time.time(), uid()
        with monitor.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.scalar(select(Entity).where(Entity.kind == "runtime_escalation", or_(
                (Entity.payload["status"].as_string() == "pending") & (Entity.payload["next_attempt_at"].as_float() <= instant),
                (Entity.payload["status"].as_string() == "delivering") & (Entity.payload["lease_until"].as_float() <= instant)))
                .order_by(Entity.payload["created_at"].as_string()).limit(1))
            if row is None:
                break
            if row.payload["attempts"] >= 5:
                row.payload = {**row.payload, "status": "failed", "reason": "Attempt bound exhausted after abandoned lease", "finished_at": now()}
                monitor.workbench.audit(session, row.application_id, row.id, 5, "runtime_escalation_result", actor,
                    {"status": "failed", "reason": "Abandoned lease exhausted attempt bound"})
                result["failed"] += 1
                continue
            record = {**row.payload, "status": "delivering", "lease": lease, "lease_until": instant + 30,
                "attempts": row.payload["attempts"] + 1}
            row.payload = record
            monitor.workbench.audit(session, row.application_id, row.id, record["attempts"], "runtime_escalation_attempt", actor,
                {"incident_id": record["incident_id"], "attempt": record["attempts"]})
        payload = {key: record[key] for key in ("id", "application_id", "incident_id", "created_at", "count", "owner", "severity")}
        status, retryable = None, True
        retry_after = 0
        delivered = False
        try:
            request = Request(endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with opener.open(request, timeout=2) as response:
                status = response.status
                acknowledgment = json.loads(response.read(4097))
            delivered = status == 200 and acknowledgment.get("accepted_id") == record["id"]
        except HTTPError as exc:
            status = exc.code
            retryable = status in (408, 429, 500, 502, 503, 504)
            retry_after = retry_delay(exc.headers.get("Retry-After")) or 0
            if retry_after > 86400:
                retryable = False  # Explicitly fail instead of retrying before a long server hint.
            exc.close()
        except (URLError, TimeoutError, OSError, ValueError):
            pass
        outcome = "delivered" if delivered else "pending" if retryable and record["attempts"] < 5 else "failed"
        with monitor.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, record["id"])
            if row.payload.get("lease") != lease:
                continue
            row.payload = {**row.payload, "status": outcome, "http_status": status, "lease_until": 0,
                "next_attempt_at": time.time() + max(min(60, 2 ** record["attempts"]), retry_after if retry_after <= 86400 else 0), "finished_at": now()}
            monitor.workbench.audit(session, row.application_id, row.id, record["attempts"], "runtime_escalation_result", actor,
                {"status": outcome, "http_status": status, "attempt": record["attempts"]})
        result["retry_pending" if outcome == "pending" else outcome] += 1
    return result
