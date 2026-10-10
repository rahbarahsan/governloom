"""Durable, thin incident notifications with Standard Webhooks HMAC signing."""

import base64
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
import secrets
import socket
import ssl
import time
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field
from sqlalchemy import or_, select

from .hook import retry_delay
from .monitoring import IngestConflict, MonitorRecord
from .schemas import now, uid
from .storage import Entity


class DestinationCreate(MonitorRecord):
    name: str = Field(min_length=1, max_length=120)
    endpoint: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=200)


class DeliveryChange(MonitorRecord):
    actor: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=1)


def allowed_endpoints():
    return {value.strip() for value in os.environ.get("GOVERNLOOM_WEBHOOK_ALLOWLIST", "").split(",") if value.strip()}


def validate_endpoint(endpoint, allowed):
    """An operator cannot turn the collector into an arbitrary network client."""
    if endpoint not in allowed:
        raise ValueError("Destination must appear in the host's GOVERNLOOM_WEBHOOK_ALLOWLIST")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid webhook URL") from None
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.path.startswith("/") or any(ord(c) <= 32 or ord(c) >= 127 for c in endpoint)):
        raise ValueError("Use an ASCII URL with a path and no credentials, query or fragment")
    if parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and port:
        return parsed  # Explicitly allowlisted, owned local receiver for development.
    if parsed.scheme != "https":
        raise ValueError("Webhook destinations require HTTPS; development HTTP requires literal 127.0.0.1 and a port")
    return parsed


def resolved_addresses(parsed):
    addresses = list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(
        parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(value).is_global for value in addresses):
        raise ValueError("HTTPS destinations must resolve exclusively to public addresses")
    return addresses


def signing_headers(secret, identifier, body, timestamp=None):
    timestamp = int(time.time()) if timestamp is None else timestamp
    key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
    if len(key) != 32:
        raise ValueError("Webhook keys require 32 bytes")
    message = f"{identifier}.{timestamp}.".encode() + body
    signature = base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()
    return {"webhook-id": identifier, "webhook-timestamp": str(timestamp), "webhook-signature": "v1," + signature}


def verify_webhook(secret, headers, body, *, instant=None, tolerance=300):
    """Verify raw bytes before parsing; receivers must persist IDs for deduplication."""
    headers = {name.lower(): value for name, value in headers.items()}
    try:
        identifier = headers["webhook-id"]
        timestamp = int(headers["webhook-timestamp"])
        if not identifier or len(identifier) > 128 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-" for c in identifier):
            raise ValueError()
        if abs((time.time() if instant is None else instant) - timestamp) > tolerance:
            raise ValueError()
        expected = signing_headers(secret, identifier, body, timestamp)["webhook-signature"]
        if not any(hmac.compare_digest(expected, signature) for signature in headers["webhook-signature"].split()):
            raise ValueError()
        return identifier
    except (KeyError, ValueError, TypeError):
        raise ValueError("Invalid webhook signature or timestamp") from None


def send(endpoint, body, headers, timeout, allowed):
    parsed = validate_endpoint(endpoint, allowed)
    address = "127.0.0.1" if parsed.scheme == "http" else resolved_addresses(parsed)[0]
    # Resolve once, validate all answers, then dial that address. Preserve TLS SNI
    # and Host for the original hostname. No proxies or redirects are involved.
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port or 443, timeout=timeout)
    raw_socket = socket.create_connection((address, parsed.port or 443), timeout=timeout)
    try:
        connection.sock = ssl.create_default_context().wrap_socket(raw_socket, server_hostname=parsed.hostname) if parsed.scheme == "https" else raw_socket
        connection.request("POST", parsed.path, body=body, headers={**headers, "Content-Type": "application/json", "User-Agent": "GovernLoom-webhooks/1"})
        response = connection.getresponse()
        return response.status, response.getheader("Retry-After")
    finally:
        connection.close()
        raw_socket.close()


def enqueue(session, notification):
    """Called in the incident/escalation transaction; never perform network I/O."""
    destinations = session.scalars(select(Entity).where(Entity.kind == "webhook_destination",
        Entity.application_id == notification["application_id"], Entity.payload["active"].as_boolean() == True))
    for destination in destinations:
        identifier = hashlib.sha256(f"{notification['id']}:{destination.id}".encode()).hexdigest()[:32]
        body = json.dumps({"schema_version": 1, "type": "governloom.incident.escalated", "id": identifier,
            "timestamp": notification["created_at"], "data": {key: notification[key] for key in
                ("application_id", "incident_id", "count", "severity")}}, separators=(",", ":"), sort_keys=True)
        pending = session.scalar(select(Entity.id).where(Entity.kind == "webhook_delivery",
            Entity.application_id == notification["application_id"], Entity.payload["status"].as_string().in_(["pending", "delivering"]))
            .offset(999).limit(1))
        record = {"id": identifier, "application_id": notification["application_id"], "destination_id": destination.id,
            "incident_id": notification["incident_id"], "escalation_id": notification["id"], "body": body,
            "body_sha256": hashlib.sha256(body.encode()).hexdigest(), "status": "pending" if pending is None else "dead_letter",
            "reason": None if pending is None else "Pending delivery capacity exceeded", "created_at": now(), "revision": 1,
            "attempts": 0, "total_attempts": 0, "replays": 0, "next_attempt_at": time.time(),
            "expires_at": time.time() + 86400, "lease_until": 0}
        session.add(Entity(id=identifier, kind="webhook_delivery", application_id=notification["application_id"], payload=record))


class Webhooks:
    def __init__(self, workbench, *, allowed=None, secrets_directory=None, transport=send):
        self.workbench, self.store = workbench, workbench.store
        self.allowed = allowed_endpoints() if allowed is None else set(allowed)
        self.secrets_directory = Path(secrets_directory or os.environ.get("GOVERNLOOM_WEBHOOK_SECRETS", "data/webhook-secrets"))
        self.transport = transport

    def destinations(self, application_id):
        self.store.get("application", application_id)
        return [{k: v for k, v in row.items() if k != "secret_ref"} for row in self.store.list("webhook_destination", application_id)]

    def create(self, application_id, body):
        self.store.get("application", application_id)
        validate_endpoint(body.endpoint, self.allowed)
        if urlsplit(body.endpoint).scheme == "https":
            resolved_addresses(urlsplit(body.endpoint))
        identifier, secret = uid(), "whsec_" + base64.b64encode(secrets.token_bytes(32)).decode()
        self.secrets_directory.mkdir(parents=True, exist_ok=True)
        path = self.secrets_directory / identifier
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as target:
            target.write(secret)
            target.flush()
            os.fsync(target.fileno())
        record = {"id": identifier, "application_id": application_id, "name": body.name, "endpoint": body.endpoint,
            "active": True, "secret_ref": identifier, "created_at": now(), "revision": 1}
        try:
            with self.store.session() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                count = len(list(session.scalars(select(Entity.id).where(Entity.kind == "webhook_destination", Entity.application_id == application_id,
                    Entity.payload["active"].as_boolean() == True))))
                if count >= 20:
                    raise ValueError("At most 20 active destinations per application")
                session.add(Entity(id=identifier, kind="webhook_destination", application_id=application_id, payload=record))
                self.workbench.audit(session, application_id, identifier, 1, "webhook_destination_created", body.actor, {"name": body.name})
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return {**{k: v for k, v in record.items() if k != "secret_ref"}, "secret": secret}

    def disable(self, identifier, body):
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, identifier)
            if row is None or row.kind != "webhook_destination":
                raise ValueError("Unknown webhook destination")
            if row.payload["revision"] != body.expected_revision:
                raise IngestConflict("Stale destination revision")
            row.payload = {**row.payload, "active": False, "revision": row.payload["revision"] + 1}
            self.workbench.audit(session, row.application_id, identifier, row.payload["revision"], "webhook_destination_disabled", body.actor, {})
            return {k: v for k, v in row.payload.items() if k != "secret_ref"}

    def deliveries(self, application_id, limit=100):
        self.store.get("application", application_id)
        with self.store.session() as session:
            rows = session.scalars(select(Entity).where(Entity.kind == "webhook_delivery", Entity.application_id == application_id)
                .order_by(Entity.payload["created_at"].as_string().desc()).limit(limit))
            return [{k: v for k, v in row.payload.items() if k not in ("body", "lease")} for row in rows]

    def replay(self, identifier, body):
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, identifier)
            if row is None or row.kind != "webhook_delivery":
                raise ValueError("Unknown webhook delivery")
            if row.payload["revision"] != body.expected_revision:
                raise IngestConflict("Stale delivery revision")
            destination = session.get(Entity, row.payload["destination_id"])
            if row.payload["status"] != "dead_letter" or not destination.payload["active"]:
                raise ValueError("Replay requires a failed delivery and active destination")
            validate_endpoint(destination.payload["endpoint"], self.allowed)
            row.payload = {**row.payload, "status": "pending", "attempts": 0, "replays": row.payload["replays"] + 1,
                "revision": row.payload["revision"] + 1, "next_attempt_at": time.time(), "expires_at": time.time() + 86400, "reason": None,
                "lease": None, "lease_until": 0}
            self.workbench.audit(session, row.application_id, row.id, row.payload["revision"], "webhook_delivery_replayed", body.actor, {})
            return {k: v for k, v in row.payload.items() if k not in ("body", "lease")}

    def dispatch(self, *, limit=10, actor="webhook-worker", max_attempts=8, timeout=5):
        if not 1 <= limit <= 100 or not 1 <= max_attempts <= 30 or not 0 < timeout <= 30:
            raise ValueError("Invalid webhook dispatch bounds")
        result = {"delivered": 0, "pending": 0, "dead_letter": 0}
        for _ in range(limit):
            instant, lease = time.time(), uid()
            with self.store.session() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                row = session.scalar(select(Entity).where(Entity.kind == "webhook_delivery", or_(
                    (Entity.payload["status"].as_string() == "pending") & (Entity.payload["next_attempt_at"].as_float() <= instant),
                    (Entity.payload["status"].as_string() == "delivering") & (Entity.payload["lease_until"].as_float() <= instant)))
                    .order_by(Entity.payload["created_at"].as_string()).limit(1))
                if row is None:
                    break
                record = row.payload
                destination = session.get(Entity, record["destination_id"]).payload
                if record["attempts"] >= max_attempts or instant >= record["expires_at"] or not destination["active"]:
                    row.payload = {**record, "status": "dead_letter", "reason": "Attempt/age bound or disabled destination", "revision": record["revision"] + 1,
                        "lease": None, "lease_until": 0}
                    self.workbench.audit(session, row.application_id, row.id, row.payload["revision"], "webhook_delivery_result", actor, {"status": "dead_letter"})
                    result["dead_letter"] += 1
                    continue
                record = {**record, "status": "delivering", "lease": lease, "lease_until": instant + timeout + 30,
                    "attempts": record["attempts"] + 1, "total_attempts": record["total_attempts"] + 1, "revision": record["revision"] + 1}
                row.payload = record
                self.workbench.audit(session, row.application_id, row.id, record["revision"], "webhook_delivery_attempt", actor, {"attempt": record["total_attempts"]})
            status, hint, reason = None, 0, None
            retryable = True
            try:
                secret_ref = destination["secret_ref"]
                if not secret_ref.isalnum():
                    raise ValueError("Invalid secret reference")
                secret = (self.secrets_directory / secret_ref).read_text(encoding="ascii")
                data = record["body"].encode()
                status, retry_header = self.transport(destination["endpoint"], data, signing_headers(secret, record["id"], data), timeout, self.allowed)
                hint = retry_delay(retry_header) or 0
                retryable = status in (408, 425, 429) or status >= 500
                reason = None if 200 <= status < 300 else "Receiver rejected notification"
            except ValueError:
                retryable, reason = False, "Destination/signing configuration rejected"
            except (OSError, http.client.HTTPException):
                reason = "Receiver unavailable or secret file inaccessible"
            outcome = "delivered" if status is not None and 200 <= status < 300 else "pending" if retryable and record["attempts"] < max_attempts else "dead_letter"
            if outcome == "pending" and time.time() + hint >= record["expires_at"]:
                outcome, reason = "dead_letter", "Retry-After exceeds delivery deadline"
            with self.store.session() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                row = session.get(Entity, record["id"])
                if row.payload.get("lease") != lease or row.payload["status"] != "delivering":
                    continue
                row.payload = {**row.payload, "status": outcome, "lease_until": 0, "revision": row.payload["revision"] + 1,
                    "http_status": status, "reason": reason, "updated_at": now(),
                    "next_attempt_at": time.time() + max(hint, min(3600, 2 ** record["attempts"]) * (1 + secrets.randbelow(100) / 100))}
                self.workbench.audit(session, row.application_id, row.id, row.payload["revision"], "webhook_delivery_result", actor, {"status": outcome, "http_status": status})
            result[outcome] += 1
        return result
