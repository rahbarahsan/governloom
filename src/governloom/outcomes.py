"""Explicit expected numeric outcomes; missing evidence never means zero error."""
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import func, select

from .schemas import now
from .service import checksum
from .storage import Entity


def expectation_id(application_id, event_id):
    return checksum(["runtime_expectation", application_id, event_id])[:32]


def register(session, application_id, event, observation, policy):
    if event.outcome_due_at is None:
        return
    pending = session.scalar(select(func.count()).select_from(Entity).where(
        Entity.kind == "runtime_expectation", Entity.application_id == application_id,
        Entity.payload["status"].as_string().in_(["pending", "overdue"])))
    if pending >= 10_000:
        raise ValueError("At most 10000 unresolved outcome expectations per application")
    identifier = expectation_id(application_id, event.event_id)
    record = {"id": identifier, "application_id": application_id, "event_id": event.event_id,
        "trace_id": event.trace_id, "cursor": observation.cursor, "policy_id": policy["id"],
        "due_at": event.outcome_due_at.astimezone(timezone.utc).isoformat(), "created_at": observation.received_at,
        "status": "pending", "actual_event_id": None, "resolved_at": None, "late_seconds": None,
        "alert_id": None, "context": {key: getattr(event, key) for key in
            ("environment", "model_version", "application_version", "task_type")}}
    from .monitoring import sanitize
    session.add(Entity(id=identifier, kind="runtime_expectation", application_id=application_id, payload=sanitize(record)))


def resolve(session, application_id, event, received_at):
    if not event.related_event_id or event.phase != "outcome" or "actual" not in event.metrics:
        return
    row = session.get(Entity, expectation_id(application_id, event.related_event_id))
    if row is None or row.payload["status"] == "resolved":
        return
    delay = max(0., (datetime.fromisoformat(received_at) - datetime.fromisoformat(row.payload["due_at"])).total_seconds())
    row.payload = {**row.payload, "status": "resolved", "actual_event_id": event.event_id,
        "resolved_at": received_at, "late_seconds": delay}


class Outcomes:
    def __init__(self, monitor):
        self.monitor, self.store = monitor, monitor.store

    def coverage(self, application_id, limit=100):
        self.store.get("application", application_id)
        instant = datetime.now(timezone.utc).isoformat()
        with self.store.session() as session:
            base = select(Entity).where(Entity.kind == "runtime_expectation", Entity.application_id == application_id)
            counts = {status: session.scalar(select(func.count()).select_from(base.where(
                Entity.payload["status"].as_string() == status).subquery())) for status in ("pending", "overdue", "resolved")}
            due = session.scalar(select(func.count()).select_from(base.where(
                Entity.payload["status"].as_string() == "pending", Entity.payload["due_at"].as_string() <= instant).subquery()))
            counts["pending"] -= due
            counts["overdue"] += due
            rows = session.scalars(base.order_by(Entity.payload["due_at"].as_string().desc()).limit(limit))
            return {"counts": counts, "unswept_overdue": due, "checked_at": instant,
                "expectations": [{**row.payload, "status": "overdue" if row.payload["status"] == "pending" and row.payload["due_at"] <= instant else row.payload["status"]} for row in rows],
                "limitation": "Opt-in numeric actuals only. Lateness measures collector receipt, not when the outcome became observable. Start monitor-worker to persist deadline alerts."}

    def sweep(self, *, limit=100, instant=None):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Specify a sweep limit from 1 to 1000")
        instant = instant or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            raise ValueError("Sweep timestamp needs a timezone")
        timestamp = instant.astimezone(timezone.utc).isoformat()
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            rows = list(session.scalars(select(Entity).where(Entity.kind == "runtime_expectation",
                Entity.payload["status"].as_string() == "pending", Entity.payload["due_at"].as_string() <= timestamp)
                .order_by(Entity.payload["due_at"].as_string()).limit(limit)))
            for row in rows:
                record = row.payload
                policy = session.get(Entity, record["policy_id"]).payload
                identifier = checksum(["outcome_deadline", row.id])[:32]
                alert = {"schema_version": 1, "id": identifier, "application_id": row.application_id,
                    "event_id": record["event_id"], "trace_id": record["trace_id"], "cursor": record["cursor"],
                    "policy_id": policy["id"], "rule_id": "outcome_deadline", "name": "Expected outcome overdue",
                    "severity": "medium", "requested_action": policy.get("outcome_deadline_action", "review"),
                    "mitigation": policy.get("outcome_deadline_mitigation", "Investigate actual-outcome delivery; do not substitute zero error."),
                    "evidence": {"due_at": record["due_at"], "checked_at": timestamp, "actual_received": False,
                        "interpretation": "Missing numeric actual evidence; prediction correctness remains unknown"},
                    "status": "open", "owner": None, "revision": 1, "created_at": timestamp, "updated_at": timestamp,
                    "environment": record["context"]["environment"], "task_type": record["context"]["task_type"]}
                incident = self.monitor.group_alert(session, alert, SimpleNamespace(**record["context"]), policy)
                alert["incident_id"] = incident["id"]
                session.add(Entity(id=identifier, kind="runtime_alert", application_id=row.application_id, payload=alert))
                row.payload = {**record, "status": "overdue", "alert_id": identifier}
                self.monitor.workbench.audit(session, row.application_id, row.id, 1, "outcome_deadline_missed", "monitor-worker", {"alert_id": identifier})
        return {"flagged": len(rows), "checked_at": timestamp, "limit": limit}
