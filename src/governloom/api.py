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
from .monitoring import Monitor, MonitorPolicy, RuntimeEvent, AlertReview, IngestConflict, IngestRateLimit, IngestUnauthorized
from .schemas import Application, Record, Review, RunRequest
from .service import Workbench
from .storage import Store
from . import __version__


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


def create_app(store=None):
    api = FastAPI(title="GovernLoom", version=__version__)
    workbench = Workbench(store or Store())
    monitor = Monitor(workbench)
    api.state.workbench = workbench
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
        # Collector keys authorize only ingestion. Administration has a separate
        # shared token for private hosting, or is restricted to local clients.
        if request.url.path.startswith("/api/") and request.url.path not in ("/api/runtime/events", "/api/health") and request.method != "OPTIONS":
            if admin_token:
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
        return await call_next(request)

    @api.exception_handler(RequestValidationError)
    async def safe_validation_error(request: Request, exc):
        if request.url.path == "/api/runtime/events":
            return JSONResponse({"detail": [{"loc": error["loc"], "msg": error["msg"]} for error in exc.errors()]}, status_code=422)
        return await request_validation_exception_handler(request, exc)

    @api.exception_handler(ValueError)
    async def validation_error(_, exc):
        status = 401 if isinstance(exc, IngestUnauthorized) else 409 if isinstance(exc, IngestConflict) else 429 if isinstance(exc, IngestRateLimit) else 400
        return JSONResponse({"detail": str(exc)}, status_code=status)

    @api.post("/api/runtime/events")
    def ingest_runtime_event(body: RuntimeEvent, authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise IngestUnauthorized("Ingestion credentials are required")
        return monitor.ingest(authorization.removeprefix("Bearer "), body)

    @api.get("/api/applications/{application_id}/monitor-policy")
    def monitor_policy(application_id: str):
        return monitor.active_policy(application_id)

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
    def applications():
        return workbench.store.list("application")

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
    def runs(application_id: str | None = None):
        return workbench.runs(application_id)

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
