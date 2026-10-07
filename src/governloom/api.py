import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .demo import seed, seed_gold
from .metrics import recommend
from .schemas import Application, Record, Review, RunRequest
from .service import Workbench
from .storage import Store


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


def create_app(store=None):
    api = FastAPI(title="GovernLoom", version="0.1.0")
    workbench = Workbench(store or Store())
    api.state.workbench = workbench
    api.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
    api.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @api.middleware("http")
    async def local_mutations(request: Request, call_next):
        # Block cross-origin browser writes even though there is no account/auth layer.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin not in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"):
                return JSONResponse({"detail": "Only local dashboard origins may write"}, status_code=403)
            if int(request.headers.get("content-length", "0")) > 6_000_000:
                return JSONResponse({"detail": "Request exceeds 6 MB local import limit"}, status_code=413)
        return await call_next(request)

    @api.exception_handler(ValueError)
    async def validation_error(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @api.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "scope": "single-user local-only", "provider_available": False}

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
