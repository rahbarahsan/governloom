"""Model-independent runtime monitoring and explicit policy decisions."""

import hashlib
import copy
import hmac
import math
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import ConfigDict, Field, model_validator
from sqlalchemy import func, select, update

from .schemas import Record, now, uid
from .service import checksum
from .storage import Entity, RuntimeObservation


class MonitorRecord(Record):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class RuntimeEvent(MonitorRecord):
    event_id: str = Field(default_factory=uid, min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=128)
    phase: Literal["input", "output", "tool", "error", "outcome"]
    task_type: Literal["vision", "rag", "forecasting", "classification", "generative", "custom"]
    environment: str = Field(default="production", min_length=1, max_length=64)
    model_version: str = Field(min_length=1, max_length=200)
    application_version: str = Field(min_length=1, max_length=200)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: dict[str, float] = Field(default_factory=dict, max_length=40)
    labels: list[str] | None = Field(default=None, max_length=100)
    text: str | None = Field(default=None, max_length=32_000)
    tool_name: str | None = Field(default=None, max_length=200)
    citations: list[str] | None = Field(default=None, max_length=100)
    source_ids: list[str] | None = Field(default=None, max_length=100)
    related_event_id: str | None = Field(default=None, max_length=128)
    error_type: str | None = Field(default=None, max_length=200)
    client_mode: Literal["observe", "enforce"] = "observe"

    @model_validator(mode="after")
    def valid_payload(self):
        for identifier in (self.event_id, self.trace_id, self.related_event_id):
            if identifier and (not re.fullmatch(r"[a-zA-Z0-9_.:-]+", identifier) or SECRET_PATTERN.search(identifier)):
                raise ValueError("Event/trace identifiers must be opaque IDs, not personal data or secrets")
        if self.occurred_at.tzinfo is None or self.occurred_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Event timestamps need a timezone and cannot be more than five minutes ahead")
        if any(not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.-]{0,63}", name) for name in self.metrics):
            raise ValueError("Metric names must be short identifiers")
        for values in (self.labels, self.citations, self.source_ids):
            if values and any(not value.strip() or len(value) > 200 for value in values):
                raise ValueError("Labels/source identifiers must be nonempty and at most 200 characters")
        if self.phase == "tool" and not self.tool_name:
            raise ValueError("Tool events require a tool name")
        return self


class RuntimeRule(MonitorRecord):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    name: str = Field(min_length=1, max_length=200)
    detector: Literal["metric_threshold", "mean_shift", "label_allowlist", "tool_allowlist", "citation_integrity", "secrets", "email_exposure", "prompt_injection_signal", "target_error"]
    phase: Literal["input", "output", "tool", "error", "outcome", "any"] = "any"
    task_type: Literal["vision", "rag", "forecasting", "classification", "generative", "custom", "any"] = "any"
    environment: str | None = Field(default=None, max_length=64)
    metric: str | None = Field(default=None, max_length=64)
    comparator: Literal["gt", "gte", "lt", "lte"] = "gt"
    threshold: float | None = None
    baseline: float | None = None
    window_size: int = Field(default=20, ge=2, le=1000)
    allowed: list[str] = Field(default_factory=list, max_length=100)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    action: Literal["flag", "review", "block"] = "flag"
    mitigation: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_detector(self):
        if self.detector in ("metric_threshold", "mean_shift") and (not self.metric or self.threshold is None):
            raise ValueError("Numeric rules require a metric and threshold")
        if self.detector == "mean_shift" and (self.baseline is None or self.threshold < 0):
            raise ValueError("Mean-shift rules require a baseline and nonnegative distance threshold")
        if self.detector in ("label_allowlist", "tool_allowlist") and not self.allowed:
            raise ValueError("Allowlist rules require explicitly allowed values")
        if any(not value.strip() or len(value) > 200 for value in self.allowed):
            raise ValueError("Allowed values must be nonempty short labels")
        return self


class MonitorPolicy(MonitorRecord):
    name: str = Field(min_length=1, max_length=120)
    actor: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=4000)
    rules: list[RuntimeRule] = Field(min_length=1, max_length=30)
    expected_events_per_minute: int = Field(default=600, ge=1, le=10000)

    @model_validator(mode="after")
    def unique_rules(self):
        if len({rule.id for rule in self.rules}) != len(self.rules):
            raise ValueError("Rule identifiers must be unique")
        return self


class AlertReview(MonitorRecord):
    actor: str = Field(min_length=1, max_length=200)
    owner: str = Field(min_length=1, max_length=200)
    status: Literal["open", "acknowledged", "mitigated", "false_positive"]
    rationale: str = Field(min_length=1, max_length=4000)
    expected_revision: int = Field(ge=1)


class IngestUnauthorized(ValueError):
    pass


class IngestConflict(ValueError):
    pass


class IngestRateLimit(ValueError):
    pass


class Monitor:
    def __init__(self, workbench):
        self.workbench = workbench
        self.store = workbench.store

    def policy(self, application_id, body: MonitorPolicy):
        self.store.get("application", application_id)
        record = {**body.model_dump(), "id": uid(), "application_id": application_id,
                  "created_at": now(), "engine_version": "runtime-rules-v1"}
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            pointer_id = checksum(["monitor_config", application_id])[:32]
            old = session.get(Entity, pointer_id)
            pointer = {"id": pointer_id, "application_id": application_id, "policy_id": record["id"]}
            session.add(Entity(id=record["id"], kind="monitor_policy", application_id=application_id, payload=record))
            if old:
                old.payload = pointer
            else:
                session.add(Entity(id=pointer_id, kind="monitor_config", application_id=application_id, payload=pointer))
            self.workbench.audit(session, application_id, record["id"], 1, "monitor_policy_activated", body.actor, record)
        return record

    def active_policy(self, application_id):
        configs = self.store.list("monitor_config", application_id)
        return self.store.get("monitor_policy", configs[0]["policy_id"]) if configs else None

    def issue_key(self, application_id, name, actor):
        self.store.get("application", application_id)
        if not name.strip() or not actor.strip() or len(name) > 200 or len(actor) > 200:
            raise ValueError("Key name and actor must be nonempty and at most 200 characters")
        identifier, secret = uid(), secrets.token_urlsafe(32)
        token = f"gl_{identifier}.{secret}"
        record = {"id": identifier, "application_id": application_id, "name": name, "active": True,
                  "created_at": now(), "digest": hashlib.sha256(token.encode()).hexdigest()}
        with self.store.session() as session:
            session.add(Entity(id=identifier, kind="ingest_key", application_id=application_id, payload=record))
            self.workbench.audit(session, application_id, identifier, 1, "ingest_key_created", actor, {"name": name})
        return {"key": token, **{key: value for key, value in record.items() if key != "digest"}}

    def keys(self, application_id):
        return [{key: value for key, value in row.items() if key != "digest"} for row in self.store.list("ingest_key", application_id)]

    def revoke_key(self, key_id, actor):
        if not actor.strip():
            raise ValueError("Actor is required")
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, key_id)
            if row is None or row.kind != "ingest_key":
                raise ValueError("Unknown ingestion key")
            row.payload = {**row.payload, "active": False}
            self.workbench.audit(session, row.application_id, key_id, 1, "ingest_key_revoked", actor, {})
        return {"id": key_id, "active": False}

    def authenticate(self, token, session):
        try:
            identifier = token.split(".", 1)[0].removeprefix("gl_")
            row = session.get(Entity, identifier)
            if row is None or row.kind != "ingest_key" or not row.payload["active"]:
                raise IngestUnauthorized("Invalid ingestion credentials")
            if not hmac.compare_digest(row.payload["digest"], hashlib.sha256(token.encode()).hexdigest()):
                raise IngestUnauthorized("Invalid ingestion credentials")
            return row
        except (AttributeError, KeyError):
            raise IngestUnauthorized("Invalid ingestion credentials") from None

    def ingest(self, token, event: RuntimeEvent):
        # Text is scanned transiently. The DB only receives lengths and detector
        # evidence; raw prompt/output text never enters persisted observations.
        incoming = event.model_dump(mode="json")
        digest = checksum(incoming)
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            key = self.authenticate(token, session)
            application_id = key.application_id
            existing = session.scalar(select(RuntimeObservation).where(RuntimeObservation.application_id == application_id,
                                                                        RuntimeObservation.event_id == event.event_id))
            if existing:
                if existing.payload_hash != digest:
                    raise IngestConflict("Event ID was reused with different content")
                return {**existing.payload["receipt"], "duplicate": True}
            config_id = checksum(["monitor_config", application_id])[:32]
            config = session.get(Entity, config_id)
            if config is None:
                raise ValueError("Configure an active monitoring policy before sending events")
            policy = session.get(Entity, config.payload["policy_id"]).payload
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            recent = session.scalar(select(func.count()).select_from(RuntimeObservation).where(
                RuntimeObservation.application_id == application_id, RuntimeObservation.received_at >= cutoff))
            if recent >= policy["expected_events_per_minute"]:
                raise IngestRateLimit("Configured per-application event rate limit exceeded")
            related = None
            if event.related_event_id:
                related = session.scalar(select(RuntimeObservation).where(RuntimeObservation.application_id == application_id,
                                                                          RuntimeObservation.event_id == event.related_event_id))
                if related is None or related.trace_id != event.trace_id:
                    raise ValueError("Outcome reference must identify an event from this application and trace")
                original = related.payload["event"]
                if event.phase != "outcome" or original["phase"] != "output" or any(
                    original[field] != getattr(event, field)
                    for field in ("task_type", "environment", "model_version", "application_version")
                ):
                    raise ValueError("Outcome references require matching prediction task, environment and versions")
            metrics = dict(event.metrics)
            if event.phase == "outcome" and related and "actual" in metrics and "prediction" in related.payload["event"]["metrics"]:
                metrics["absolute_error"] = abs(metrics["actual"] - related.payload["event"]["metrics"]["prediction"])
                if not math.isfinite(metrics["absolute_error"]):
                    raise ValueError("Derived outcome error exceeds the numeric range")
            checks = [self.evaluate_rule(rule, event, metrics, application_id, session) for rule in policy["rules"]]
            triggered = [check for check in checks if check["status"] == "triggered"]
            priority = {"flag": 0, "review": 1, "block": 2}
            action = max((check["action"] for check in triggered), key=priority.get, default="allow")
            receipt = {"event_id": event.event_id, "trace_id": event.trace_id, "phase": event.phase,
                       "application_id": application_id, "policy_id": policy["id"],
                       "engine_version": policy["engine_version"], "action": action, "checks": checks,
                       "alert_ids": [], "received_at": now(), "duplicate": False}
            stored = {key: value for key, value in incoming.items() if key != "text"}
            stored["metrics"] = metrics
            stored["text_supplied"] = event.text is not None
            stored["text_characters"] = len(event.text) if event.text is not None else None
            # Text-like auxiliary identifiers are also bounded and redact known
            # secret/email signatures before storage, not just main content.
            stored = sanitize(stored)
            observation = RuntimeObservation(application_id=application_id, event_id=event.event_id, trace_id=event.trace_id,
                                             received_at=receipt["received_at"], payload_hash=digest,
                                             payload={"event": stored, "receipt": copy.deepcopy(receipt)})
            session.add(observation)
            session.flush()
            for check in triggered:
                alert_id = checksum([application_id, event.event_id, check["rule_id"]])[:32]
                alert = {"schema_version": 1, "id": alert_id, "application_id": application_id, "event_id": event.event_id,
                         "trace_id": event.trace_id, "cursor": observation.cursor, "policy_id": policy["id"],
                         "rule_id": check["rule_id"], "name": check["name"], "severity": check["severity"],
                         "requested_action": check["action"], "mitigation": check["mitigation"], "evidence": check["evidence"],
                         "status": "open", "owner": None, "revision": 1, "created_at": now(), "updated_at": now(),
                         "environment": event.environment, "task_type": event.task_type}
                session.add(Entity(id=alert_id, kind="runtime_alert", application_id=application_id, payload=sanitize(alert)))
                receipt["alert_ids"].append(alert_id)
            receipt["cursor"] = observation.cursor
            observation.payload = {"event": stored, "receipt": sanitize(receipt)}
        return sanitize(receipt)

    def evaluate_rule(self, rule, event, metrics, application_id, session):
        result = {"rule_id": rule["id"], "name": rule["name"], "severity": rule["severity"], "action": rule["action"],
                  "mitigation": rule["mitigation"], "status": "not_applicable", "evidence": {}}
        if rule["phase"] not in ("any", event.phase) or rule["task_type"] not in ("any", event.task_type) or rule["environment"] not in (None, event.environment):
            return result
        detector = rule["detector"]
        evidence, triggered = {}, False
        missing = False
        if detector == "metric_threshold":
            missing = rule["metric"] not in metrics
            if not missing:
                value = metrics[rule["metric"]]
                threshold = rule["threshold"]
                triggered = {"gt": value > threshold, "gte": value >= threshold,
                             "lt": value < threshold, "lte": value <= threshold}[rule["comparator"]]
                evidence = {"metric": rule["metric"], "value": value, "comparator": rule["comparator"], "threshold": threshold}
        elif detector == "mean_shift":
            values = []
            # Bound the scan and isolate windows by deployment/model/phase.
            rows = session.scalars(select(RuntimeObservation).where(RuntimeObservation.application_id == application_id)
                                   .order_by(RuntimeObservation.cursor.desc()).limit(1000))
            for row in rows:
                previous = row.payload["event"]
                if (previous["environment"], previous["model_version"], previous["application_version"], previous["task_type"], previous["phase"]) == (event.environment, event.model_version, event.application_version, event.task_type, event.phase) and rule["metric"] in previous["metrics"]:
                    values.append(previous["metrics"][rule["metric"]])
                    if len(values) >= rule["window_size"] - 1:
                        break
            if rule["metric"] in metrics:
                values = [metrics[rule["metric"]], *values]
            missing = rule["metric"] not in metrics or len(values) < rule["window_size"]
            if not missing:
                mean = sum(value / len(values) for value in values)
                triggered = abs(mean - rule["baseline"]) > rule["threshold"]
                evidence = {"metric": rule["metric"], "window_mean": mean, "baseline": rule["baseline"],
                            "distance_threshold": rule["threshold"], "samples": len(values), "limitation": "Mean-shift signal, not a validated drift test"}
        elif detector in ("tool_allowlist", "label_allowlist"):
            values = [event.tool_name] if detector == "tool_allowlist" and event.tool_name else event.labels if detector == "label_allowlist" else None
            missing = values is None
            if not missing:
                unexpected = [value for value in values if value not in rule["allowed"]]
                triggered = bool(unexpected)
                evidence = {"unexpected": unexpected, "allowed": rule["allowed"]}
        elif detector == "citation_integrity":
            missing = event.citations is None or event.source_ids is None
            if not missing:
                unknown = sorted(set(event.citations) - set(event.source_ids))
                triggered = not event.citations or bool(unknown)
                evidence = {"citation_count": len(event.citations), "unknown_source_ids": unknown,
                            "limitation": "Document identity only; does not establish factual support"}
        elif detector in ("secrets", "email_exposure", "prompt_injection_signal"):
            missing = event.text is None
            if not missing:
                expression = SECRET_PATTERN if detector == "secrets" else EMAIL_PATTERN if detector == "email_exposure" else INJECTION_PATTERN
                matched = list(expression.finditer(event.text))
                triggered = bool(matched)
                evidence = {"signal": detector, "match_count": len(matched), "content": "not retained",
                            "limitation": "Pattern signal; false positives and missed patterns are possible"}
        elif detector == "target_error":
            missing = event.phase != "error"
            triggered = event.phase == "error"
            evidence = {"error_type": event.error_type or "unspecified"}
        result.update(status="insufficient_evidence" if missing else "triggered" if triggered else "clear", evidence=evidence)
        return result

    def events(self, application_id, after=0, limit=100):
        self.store.get("application", application_id)
        with self.store.session() as session:
            query = select(RuntimeObservation).where(RuntimeObservation.application_id == application_id, RuntimeObservation.cursor > after)
            rows = list(session.scalars(query.order_by(RuntimeObservation.cursor).limit(limit)))
            return {"events": [{"cursor": row.cursor, **row.payload} for row in rows],
                    "next_cursor": rows[-1].cursor if rows else after}

    def alerts(self, application_id, status=None, limit=100):
        with self.store.session() as session:
            query = select(Entity).where(Entity.kind == "runtime_alert", Entity.application_id == application_id)
            if status is not None:
                query = query.where(Entity.payload["status"].as_string() == status)
            return [row.payload for row in session.scalars(query.order_by(Entity.payload["created_at"].as_string().desc()).limit(limit))]

    def review_alert(self, alert_id, body: AlertReview):
        old = self.store.get("runtime_alert", alert_id)
        if old["revision"] != body.expected_revision:
            raise ValueError("Stale alert revision; reload")
        revised = {**old, **body.model_dump(exclude={"expected_revision"}), "revision": old["revision"] + 1, "updated_at": now()}
        with self.store.session() as session:
            changed = session.execute(update(Entity).where(Entity.id == alert_id, Entity.payload == old).values(payload=sanitize(revised)))
            if changed.rowcount != 1:
                raise ValueError("Concurrent alert update; reload")
            self.workbench.audit(session, old["application_id"], alert_id, revised["revision"], "runtime_alert_review", body.actor,
                                 sanitize({"status": body.status, "owner": body.owner, "rationale": body.rationale}))
        return sanitize(revised)


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
SECRET_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b")
INJECTION_PATTERN = re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|reveal\s+(?:the\s+)?system\s+prompt", re.I)


def sanitize(value):
    if isinstance(value, str):
        return EMAIL_PATTERN.sub("[redacted email]", SECRET_PATTERN.sub("[redacted secret]", value))
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    return value
