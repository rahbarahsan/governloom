import json
import os
import hmac
from pathlib import Path

from fastapi import FastAPI, Request, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .demo import seed, seed_gold
from .metrics import recommend
from .monitoring import Monitor, MonitorPolicy, RuntimeEvent, AlertReview, Heartbeat, ActionAcknowledgment, ActionVerification, IngestConflict, IngestRateLimit, IngestUnauthorized
from .schemas import Application, Record, Review, RunRequest
from .service import Workbench
from .storage import Store
from . import __version__
from .auth import Operators, UserCreate, Login, PasswordChange, AccessDenied, LoginRequired, public_user
from .detectors import Profiles, DetectorProfile, ProfileApproval


class SourceImport(Record):
    document_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    filename: str
    content: str = Field(max_length=2_000_000)


class TextImport(Record):
    text: str = Field(max_length=5_000_000)


class Publish(Record):
    actor: str = Field(min_length=1)


class RunCreate(RunRequest):
    trace_batch_id: str | None = None


class KeyCreate(Record):
    name: str = Field(min_length=1, max_length=200)
    actor: str = Field(min_length=1, max_length=200)


class TestSinkDispatch(Record):
    endpoint: str = Field(min_length=1, max_length=200)
    actor: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=100)


def create_app(store=None):
    api = FastAPI(title="GovernLoom", version=__version__)
    workbench = Workbench(store or Store())
    monitor = Monitor(workbench)
    profiles = Profiles(workbench)
    api.state.workbench = workbench
    operators = Operators(workbench)
    has_operators = bool(workbench.store.list("operator_user"))
    auth_mode = os.environ.get("GOVERNLOOM_AUTH_MODE", "operators" if has_operators else "local")
    if auth_mode not in ("local", "operators"):
        raise ValueError("GOVERNLOOM_AUTH_MODE must be local or operators")
    if has_operators and auth_mode == "local":
        raise ValueError("A collector with named accounts cannot start in unauthenticated local mode")
    admin_token = os.environ.get("GOVERNLOOM_ADMIN_TOKEN")
    if admin_token and len(admin_token) < 32:
        raise ValueError("GOVERNLOOM_ADMIN_TOKEN must contain at least 32 characters")
    allowed_hosts = os.environ.get("GOVERNLOOM_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    allowed_origins = os.environ.get("GOVERNLOOM_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000").split(",")
    api.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    api.add_middleware(CORSMiddleware, allow_origins=allowed_origins,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])

    @api.middleware("http")
    async def local_mutations(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method == "POST":
            chunks, length = [], 0
            async for chunk in request.stream():
                length += len(chunk)
                if length > 6_000_000:
                    return JSONResponse({"detail": "Request exceeds 6 MB limit"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        # Collector keys authorize only ingestion. Administration has a separate
        # shared token for private hosting, or is restricted to local clients.
        public_paths = ("/api/runtime/events", "/api/runtime/heartbeats", "/api/runtime/actions", "/api/health", "/api/auth/config", "/api/auth/login")
        if request.url.path.startswith("/api/") and request.url.path not in public_paths and request.method != "OPTIONS":
            if auth_mode == "operators":
                try:
                    user, session_id = operators.authenticate(request.headers.get("authorization", "").removeprefix("Bearer "))
                    request.state.user, request.state.operator_session = user, session_id
                    body = {}
                    if request.method == "POST":
                        raw = await request.body()
                        if len(raw) > 6_000_000:
                            return JSONResponse({"detail": "Request exceeds 6 MB limit"}, status_code=413)
                        if raw:
                            body = json.loads(raw)
                        if not isinstance(body, dict):
                            raise ValueError("Request body must be an object")
                        if "actor" in body:
                            body["actor"] = user["username"]
                            request._body = json.dumps(body).encode()
                    if not request.url.path.startswith("/api/auth/"):
                        operators.authorize(user, request.method, request.url.path, request.query_params, body)
                except LoginRequired as exc:
                    return JSONResponse({"detail": str(exc)}, status_code=401)
                except AccessDenied as exc:
                    return JSONResponse({"detail": str(exc)}, status_code=403)
                except ValueError:
                    return JSONResponse({"detail": "Invalid request or unknown record"}, status_code=400)
            elif admin_token:
                supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
                if not hmac.compare_digest(supplied.encode(), admin_token.encode()):
                    return JSONResponse({"detail": "Collector administration requires an admin access token"}, status_code=401)
            elif request.client is None or request.client.host not in ("127.0.0.1", "::1", "localhost", "testclient", "testserver"):
                return JSONResponse({"detail": "Remote administration requires GOVERNLOOM_ADMIN_TOKEN"}, status_code=403)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin not in allowed_origins:
                return JSONResponse({"detail": "Dashboard origin is not allowed"}, status_code=403)
            try:
                content_length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
            if content_length < 0:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
            if content_length > 6_000_000:
                return JSONResponse({"detail": "Request exceeds 6 MB local import limit"}, status_code=413)
        response = await call_next(request)
        if auth_mode == "operators" and request.method == "POST" and hasattr(request.state, "user") and 200 <= response.status_code < 300:
            user = request.state.user
            with workbench.store.session() as session:
                workbench.audit(session, None, user["id"], user["revision"], "operator_request", user["username"], {"method": "POST", "path": request.url.path})
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @api.exception_handler(RequestValidationError)
    async def safe_validation_error(request: Request, exc):
        if request.url.path in ("/api/runtime/events", "/api/runtime/heartbeats", "/api/runtime/actions") or request.url.path.startswith("/api/auth/"):
            return JSONResponse({"detail": [{"loc": error["loc"], "msg": error["msg"]} for error in exc.errors()]}, status_code=422)
        return await request_validation_exception_handler(request, exc)

    @api.exception_handler(ValueError)
    async def validation_error(_, exc):
        status = 401 if isinstance(exc, (IngestUnauthorized, LoginRequired)) else 403 if isinstance(exc, AccessDenied) else 409 if isinstance(exc, IngestConflict) else 429 if isinstance(exc, IngestRateLimit) else 400
        return JSONResponse({"detail": str(exc)}, status_code=status)

    @api.get("/api/auth/config")
    def auth_config():
        return {"mode": auth_mode, "named_identity": auth_mode == "operators"}

    @api.post("/api/auth/login")
    def operator_login(body: Login, request: Request):
        if auth_mode != "operators":
            raise AccessDenied("Named accounts require operator authentication mode")
        return operators.login(body, request.client.host if request.client else "unknown")

    @api.get("/api/auth/me")
    def operator_me(request: Request):
        if auth_mode != "operators":
            raise AccessDenied("Named accounts require operator authentication mode")
        return request.state.user

    @api.post("/api/auth/logout")
    def operator_logout(request: Request):
        if auth_mode != "operators":
            raise AccessDenied("Named accounts require operator authentication mode")
        return operators.logout(request.state.operator_session, request.state.user)

    @api.post("/api/auth/password")
    def operator_password(body: PasswordChange, request: Request):
        if auth_mode != "operators":
            raise AccessDenied("Named accounts require operator authentication mode")
        return operators.change_password(request.state.user, body)

    def require_operator_admin(request):
        if auth_mode != "operators" or request.state.user["role"] != "admin":
            raise AccessDenied("Named administrator account required")

    @api.get("/api/auth/users")
    def operator_users(request: Request):
        require_operator_admin(request)
        return [public_user(row) for row in workbench.store.list("operator_user")]

    @api.post("/api/auth/users", status_code=201)
    def create_operator(body: UserCreate, request: Request):
        require_operator_admin(request)
        return operators.create(body, request.state.user["username"])

    @api.post("/api/auth/users/{identifier}/revoke")
    def revoke_operator(identifier: str, request: Request):
        require_operator_admin(request)
        return operators.revoke(identifier, request.state.user["username"])

    @api.post("/api/runtime/events")
    def ingest_runtime_event(body: RuntimeEvent, authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise IngestUnauthorized("Ingestion credentials are required")
        return monitor.ingest(authorization.removeprefix("Bearer "), body)

    @api.post("/api/runtime/heartbeats")
    def runtime_heartbeat(body: Heartbeat, authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise IngestUnauthorized("Ingestion credentials are required")
        return monitor.heartbeat(authorization.removeprefix("Bearer "), body)

    @api.get("/api/applications/{application_id}/runtime-agents")
    def runtime_agents(application_id: str):
        return monitor.agents(application_id)

    @api.get("/api/applications/{application_id}/runtime-incidents")
    def runtime_incidents(application_id: str, limit: int = Query(default=100, ge=1, le=500)):
        return monitor.incidents(application_id, limit)

    @api.post("/api/runtime-incidents/{identifier}/review")
    def review_incident(identifier: str, body: AlertReview):
        return monitor.review_incident(identifier, body)

    @api.post("/api/runtime/actions")
    def acknowledge_action(body: ActionAcknowledgment, authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise IngestUnauthorized("Ingestion credentials are required")
        return monitor.acknowledge_action(authorization.removeprefix("Bearer "), body)

    @api.get("/api/applications/{application_id}/runtime-actions")
    def runtime_actions(application_id: str, limit: int = Query(default=100, ge=1, le=500)):
        return runtime_records("runtime_action", application_id, limit)

    @api.post("/api/runtime-actions/{identifier}/verify")
    def verify_action(identifier: str, body: ActionVerification):
        return monitor.verify_action(identifier, body)

    @api.get("/api/applications/{application_id}/runtime-escalations")
    def runtime_escalations(application_id: str, limit: int = Query(default=100, ge=1, le=500)):
        return runtime_records("runtime_escalation", application_id, limit)

    def runtime_records(kind, application_id, limit):
        from sqlalchemy import select
        from .storage import Entity
        workbench.store.get("application", application_id)
        with workbench.store.session() as session:
            rows = session.scalars(select(Entity).where(Entity.kind == kind, Entity.application_id == application_id)
                .order_by(Entity.payload["created_at"].as_string().desc()).limit(limit))
            return [row.payload for row in rows]

    @api.post("/api/runtime-escalations/dispatch-test-sink")
    def dispatch_escalations(body: TestSinkDispatch):
        from .escalation import dispatch_test_sink
        return dispatch_test_sink(monitor, body.endpoint, body.actor, body.limit)

    @api.get("/api/applications/{application_id}/monitor-policy")
    def monitor_policy(application_id: str):
        return monitor.active_policy(application_id)

    @api.get("/api/applications/{application_id}/detector-profiles")
    def detector_profiles(application_id: str):
        workbench.store.get("application", application_id)
        approvals = workbench.store.list("profile_approval", application_id)
        approved = {row["profile_id"]: row for row in approvals}
        return [{**row, "approval": approved.get(row["id"])} for row in workbench.store.list("detector_profile", application_id)]

    @api.post("/api/applications/{application_id}/detector-profiles", status_code=201)
    def create_detector_profile(application_id: str, body: DetectorProfile):
        return profiles.create(application_id, body)

    @api.get("/api/detector-profiles/{identifier}")
    def detector_profile(identifier: str):
        return workbench.store.get("detector_profile", identifier)

    @api.post("/api/detector-profiles/{identifier}/approve", status_code=201)
    def approve_detector_profile(identifier: str, body: ProfileApproval):
        return profiles.approve(identifier, body)

    @api.get("/api/monitor-policies/{policy_id}")
    def historical_monitor_policy(policy_id: str):
        return workbench.store.get("monitor_policy", policy_id)

    @api.post("/api/applications/{application_id}/monitor-policy", status_code=201)
    def activate_monitor_policy(application_id: str, body: MonitorPolicy):
        return monitor.policy(application_id, body)

    @api.get("/api/applications/{application_id}/ingest-keys")
    def ingest_keys(application_id: str):
        return monitor.keys(application_id)

    @api.post("/api/applications/{application_id}/ingest-keys", status_code=201)
    def create_ingest_key(application_id: str, body: KeyCreate):
        return monitor.issue_key(application_id, body.name, body.actor)

    @api.post("/api/ingest-keys/{key_id}/revoke")
    def revoke_ingest_key(key_id: str, body: Publish):
        return monitor.revoke_key(key_id, body.actor)

    @api.get("/api/applications/{application_id}/runtime-events")
    def runtime_events(application_id: str, after: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
        return monitor.events(application_id, after, limit)

    @api.get("/api/applications/{application_id}/runtime-alerts")
    def runtime_alerts(application_id: str, status: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
        return monitor.alerts(application_id, status, limit)

    @api.post("/api/runtime-alerts/{alert_id}/review")
    def review_runtime_alert(alert_id: str, body: AlertReview):
        return monitor.review_alert(alert_id, body)

    @api.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "scope": "private collector", "provider_available": False,
                "runtime_monitoring": True}

    @api.get("/api/applications")
    def applications(request: Request):
        rows = workbench.store.list("application")
        if auth_mode == "operators" and request.state.user["role"] != "admin":
            rows = [row for row in rows if row["id"] in request.state.user["application_ids"]]
        return rows

    @api.post("/api/applications", status_code=201)
    def create_application(application: Application):
        return workbench.create_application(application)

    @api.post("/api/demo", status_code=201)
    def demo():
        application = seed(workbench)
        # Idempotent load; candidates stay unreviewed until an explicit reviewer decision.
        seed_gold(workbench, application["id"])
        return application

    @api.get("/api/applications/{application_id}/sources")
    def sources(application_id: str):
        return workbench.store.list("source", application_id)

    @api.post("/api/applications/{application_id}/sources", status_code=201)
    def import_source(application_id: str, body: SourceImport):
        return workbench.import_source(application_id, body.document_id, body.version, body.filename, body.content)

    @api.get("/api/applications/{application_id}/cases")
    def cases(application_id: str):
        return workbench.store.list("case", application_id)

    @api.post("/api/applications/{application_id}/cases/import", status_code=201)
    def import_cases(application_id: str, body: TextImport):
        return workbench.import_cases(application_id, body.text)

    @api.post("/api/applications/{application_id}/cases/generate", status_code=201)
    def generate(application_id: str):
        return workbench.generate(application_id)

    @api.post("/api/cases/{case_id}/review")
    def review(case_id: str, body: Review):
        return workbench.review(case_id, body)

    @api.get("/api/applications/{application_id}/review-events")
    def review_events(application_id: str):
        return workbench.store.list("review_event", application_id)

    @api.get("/api/applications/{application_id}/datasets")
    def datasets(application_id: str):
        return workbench.store.list("dataset", application_id)

    @api.get("/api/datasets/{dataset_id}")
    def dataset(dataset_id: str):
        return workbench.store.get("dataset", dataset_id)

    @api.post("/api/applications/{application_id}/datasets", status_code=201)
    def publish(application_id: str, body: Publish):
        return workbench.publish(application_id, body.actor)

    @api.get("/api/applications/{application_id}/metrics")
    def metrics(application_id: str):
        return recommend(workbench.store.get("application", application_id), workbench.store.list("case", application_id))

    @api.post("/api/applications/{application_id}/traces/import", status_code=201)
    def import_traces(application_id: str, body: TextImport):
        return workbench.import_traces(application_id, body.text)

    @api.get("/api/applications/{application_id}/trace-batches")
    def trace_batches(application_id: str):
        return workbench.store.list("trace_batch", application_id)

    @api.post("/api/runs", status_code=201)
    def queue(body: RunCreate):
        return workbench.queue(RunRequest.model_validate(body.model_dump(exclude={"trace_batch_id"})), body.trace_batch_id)

    @api.get("/api/runs")
    def runs(request: Request, application_id: str | None = None):
        rows = workbench.runs(application_id)
        if auth_mode == "operators" and request.state.user["role"] != "admin":
            rows = [row for row in rows if row["application_id"] in request.state.user["application_ids"]]
        return rows

    @api.get("/api/runs/{run_id}")
    def run(run_id: str):
        return workbench.run(run_id)

    @api.post("/api/runs/{run_id}/cancel")
    def cancel(run_id: str):
        return workbench.cancel(run_id)

    @api.get("/api/runs/{run_id}/traces")
    def export_traces(run_id: str):
        run = workbench.run(run_id)
        return Response("".join(json.dumps(result["trace"], ensure_ascii=False) + "\n"
                                for result in run["results"] if result["trace"] is not None),
                        media_type="application/x-ndjson", headers={"Content-Disposition": f'attachment; filename="{run_id}-traces-v1.jsonl"'})

    @api.get("/api/compare")
    def compare(left: str, right: str):
        return workbench.compare(left, right)

    @api.get("/api/export/{kind}")
    def export(kind: str, application_id: str):
        if kind not in ("source", "case", "dataset", "trace_batch", "review_event", "run"):
            raise ValueError("Unsupported export kind")
        rows = [workbench.run(r["id"]) for r in workbench.runs(application_id)] if kind == "run" else workbench.store.list(kind, application_id)
        return Response("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), media_type="application/x-ndjson",
                        headers={"Content-Disposition": f'attachment; filename="governloom-{kind}-v1.jsonl"'})

    dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if dist.exists():
        api.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @api.get("/")
        def dashboard():
            return FileResponse(dist / "index.html")

    return api


app = create_app()
