"""Named, revocable private-collector identities; deny-by-default application scope."""
import hashlib
import hmac
import re
import secrets
import time

from pydantic import Field
from sqlalchemy import delete, select

from .schemas import Record, now, uid
from .storage import Entity

ITERATIONS = 600_000
SESSION_SECONDS = 8 * 3600


class AccessDenied(ValueError):
    pass


class LoginRequired(ValueError):
    pass


class Login(Record):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class UserCreate(Login):
    role: str = Field(pattern=r"^(admin|operator|reviewer|viewer)$")
    application_ids: list[str] = Field(default_factory=list, max_length=100)


class PasswordChange(Record):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=15, max_length=1024)


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS).hex()


def public_user(row):
    return {name: row[name] for name in ("id", "username", "role", "application_ids", "active", "revision")}


class Operators:
    def __init__(self, workbench):
        self.workbench, self.store = workbench, workbench.store

    def create(self, body: UserCreate, actor, *, bootstrap=False):
        username = body.username.casefold()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,63}", username):
            raise ValueError("Username must be a short account identifier")
        if len(body.password) < 15:
            raise ValueError("Use a password of at least 15 characters")
        if body.role != "admin" and not body.application_ids:
            raise ValueError("Non-admin accounts need explicit application grants")
        if body.role == "admin" and body.application_ids:
            raise ValueError("Administrators have global scope; omit application grants")
        for identifier in body.application_ids:
            self.store.get("application", identifier)
        identifier = hashlib.sha256(("operator:" + username).encode()).hexdigest()[:32]
        salt = secrets.token_hex(16)
        row = {"id": identifier, "username": username, "role": body.role,
               "application_ids": sorted(set(body.application_ids)), "active": True, "revision": 1,
               "salt": salt, "password_hash": password_hash(body.password, salt), "created_at": now()}
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            if bootstrap and session.scalar(select(Entity.id).where(Entity.kind == "operator_user").limit(1)):
                raise ValueError("Bootstrap is only allowed before the first account exists")
            if session.get(Entity, identifier):
                raise ValueError("Username already exists")
            session.add(Entity(id=identifier, kind="operator_user", payload=row))
            self.workbench.audit(session, None, identifier, 1, "operator_created", actor, public_user(row))
        return public_user(row)

    def login(self, body: Login, client):
        # Persistent per-client minute bucket also throttles unknown usernames.
        bucket_id = hashlib.sha256(("login:" + client).encode()).hexdigest()[:32]
        instant = time.time()
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, bucket_id)
            bucket = row.payload if row and row.payload["until"] > instant else {"id": bucket_id, "attempts": 0, "until": instant + 60}
            if bucket["attempts"] >= 10:
                raise AccessDenied("Login rate limit reached; wait one minute")
            bucket = {**bucket, "attempts": bucket["attempts"] + 1}
            if row:
                row.payload = bucket
            else:
                session.add(Entity(id=bucket_id, kind="login_limit", payload=bucket))
            session.execute(delete(Entity).where(Entity.kind == "login_limit", Entity.payload["until"].as_float() < instant - 60))
        identifier = hashlib.sha256(("operator:" + body.username.casefold()).encode()).hexdigest()[:32]
        try:
            user = self.store.get("operator_user", identifier)
        except ValueError:
            user = None
        salt = user["salt"] if user else "00" * 16
        calculated = password_hash(body.password, salt)
        if not user or not hmac.compare_digest(calculated, user["password_hash"]) or not user["active"]:
            raise LoginRequired("Invalid username or password")
        session_id, token = uid(), secrets.token_urlsafe(32)
        bearer = f"go_{session_id}.{token}"
        payload = {"id": session_id, "user_id": user["id"], "revision": user["revision"], "expires": instant + SESSION_SECONDS,
                   "digest": hashlib.sha256(bearer.encode()).hexdigest()}
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            current = session.get(Entity, user["id"]).payload
            if not current["active"] or current["revision"] != user["revision"]:
                raise LoginRequired("Account changed; sign in again")
            session.execute(delete(Entity).where(Entity.kind == "operator_session", Entity.payload["expires"].as_float() <= instant))
            old = list(session.scalars(select(Entity).where(Entity.kind == "operator_session", Entity.payload["user_id"].as_string() == user["id"]).order_by(Entity.payload["expires"].as_float().desc())))
            for item in old[19:]:
                session.delete(item)
            session.add(Entity(id=session_id, kind="operator_session", payload=payload))
            self.workbench.audit(session, None, user["id"], user["revision"], "operator_login", user["username"], {"session_id": session_id})
        return {"token": bearer, "expires_at": payload["expires"], "user": public_user(user)}

    def authenticate(self, token):
        try:
            if not token.startswith("go_") or len(token) > 200:
                raise ValueError()
            identifier = token.split(".")[0][3:]
            record = self.store.get("operator_session", identifier)
            if record["expires"] <= time.time() or not hmac.compare_digest(record["digest"], hashlib.sha256(token.encode()).hexdigest()):
                raise ValueError()
            user = self.store.get("operator_user", record["user_id"])
            if not user["active"] or user["revision"] != record["revision"]:
                raise ValueError()
            return public_user(user), identifier
        except (ValueError, KeyError):
            raise LoginRequired("Sign in with an active operator account") from None

    def logout(self, identifier, user):
        with self.store.session() as session:
            session.execute(delete(Entity).where(Entity.kind == "operator_session", Entity.id == identifier))
            self.workbench.audit(session, None, user["id"], user["revision"], "operator_logout", user["username"], {})
        return {"signed_out": True}

    def revoke(self, identifier, actor):
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, identifier)
            if not row or row.kind != "operator_user":
                raise ValueError("Unknown operator")
            admins = list(session.scalars(select(Entity).where(Entity.kind == "operator_user")))
            if row.payload["role"] == "admin" and not any(item.id != identifier and item.payload["active"] and item.payload["role"] == "admin" for item in admins):
                raise ValueError("Cannot revoke the last active administrator")
            row.payload = {**row.payload, "active": False, "revision": row.payload["revision"] + 1}
            self.workbench.audit(session, None, identifier, row.payload["revision"], "operator_revoked", actor, {})
        return public_user(row.payload)

    def change_password(self, user, body):
        old = self.store.get("operator_user", user["id"])
        if not hmac.compare_digest(old["password_hash"], password_hash(body.current_password, old["salt"])):
            raise LoginRequired("Current password is incorrect")
        salt = secrets.token_hex(16)
        hashed = password_hash(body.new_password, salt)
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.get(Entity, user["id"])
            if not row.payload["active"] or row.payload["revision"] != user["revision"]:
                raise LoginRequired("Account changed; sign in again")
            row.payload = {**row.payload, "salt": salt, "password_hash": hashed, "revision": row.payload["revision"] + 1}
            self.workbench.audit(session, None, user["id"], row.payload["revision"], "operator_password_changed", user["username"], {})
        return {"signed_out": True}

    @staticmethod
    def scope(user, application_id):
        if user["role"] != "admin" and application_id not in user["application_ids"]:
            raise AccessDenied("Account does not have access to this application")

    def authorize(self, user, method, path, query, body):
        if user["role"] == "admin":
            return
        # Every supported non-admin route has an application binding. Everything
        # else (bootstrap, account management, demo, dispatch, future routes) denies.
        application_ids = []
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[1] == "applications":
            application_ids.append(parts[2])
        elif path == "/api/runs":
            if method == "GET":
                if query.get("application_id"):
                    application_ids.append(query["application_id"])
                else:
                    return  # Response is explicitly filtered in the endpoint.
            else:
                application_ids.append(self.store.get("dataset", body.get("dataset_id", ""))["application_id"])
        elif path == "/api/applications" and method == "GET":
            return  # Response is explicitly filtered in the endpoint.
        elif path == "/api/export":
            raise AccessDenied("Specify an export kind and application")
        elif len(parts) == 3 and parts[1] == "export":
            application_ids.append(query.get("application_id"))
        elif path == "/api/compare":
            application_ids.extend(self.workbench.run(query.get(name, ""))["application_id"] for name in ("left", "right"))
        elif len(parts) >= 3 and parts[1] == "runs":
            application_ids.append(self.workbench.run(parts[2])["application_id"])
        else:
            kinds = {"monitor-policies": "monitor_policy", "runtime-alerts": "runtime_alert", "runtime-incidents": "runtime_incident",
                     "runtime-actions": "runtime_action", "ingest-keys": "ingest_key", "cases": "case", "datasets": "dataset", "detector-profiles": "detector_profile"}
            if len(parts) >= 3 and parts[1] in kinds:
                application_ids.append(self.store.get(kinds[parts[1]], parts[2])["application_id"])
        if not application_ids:
            raise AccessDenied("This operation requires an administrator")
        for identifier in application_ids:
            self.scope(user, identifier)
        if method in ("GET", "HEAD"):
            return
        if user["role"] == "viewer":
            raise AccessDenied("Viewer accounts cannot modify records")
        if user["role"] == "reviewer" and not (path.endswith("/review") or path.endswith("/verify") or path.endswith("/approve")):
            raise AccessDenied("Reviewer accounts can review findings and verify actions")
