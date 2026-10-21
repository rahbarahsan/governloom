"""Immutable application evidence, owner corrections and observation proposals."""
import ast
import json
import math
import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from .schemas import Record, now
from .service import checksum
from .storage import Entity

Task = Literal["forecasting", "vision", "classification", "rag", "custom"]
ALIASES = {
    "prediction": ("prediction", "predicted_value", "y_pred", "forecast"),
    "actual": ("actual", "actual_value", "y_true", "observed_value"),
    "confidence": ("confidence", "max_probability"),
    "predicted_label": ("predicted_label", "prediction_label", "label"),
    "actual_label": ("actual_label", "true_label", "target_label"),
    "timestamp": ("timestamp", "occurred_at", "date"),
    "group": ("group_id", "sample_id", "series_id"),
    "split": ("split",), "citations": ("citations",),
    "source_ids": ("source_ids", "retrieved_ids"),
    "latency_ms": ("latency_ms",), "model_version": ("model_version",),
    "application_version": ("application_version",), "environment": ("environment",),
}
SECRET = re.compile(r"(?:sk-[A-Za-z0-9_-]{16,}|(?:gl|go)_[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{16,}|whsec_[A-Za-z0-9+/=_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,})", re.I)


def redact(text):
    return SECRET.sub("[REDACTED]", text)


class Artifact(Record):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=50_000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    original_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid(self):
        path = PurePosixPath(self.path)
        if path.is_absolute() or ".." in path.parts or "\\" in self.path or ":" in self.path or any(part.startswith(".") for part in path.parts):
            raise ValueError("Artifact paths must be relative visible paths")
        if checksum(self.content) != self.sha256:
            raise ValueError("Artifact checksum differs from its content")
        if SECRET.search(self.content):
            raise ValueError("Remove credential patterns before importing source evidence")
        return self


class DiscoveryImport(Record):
    actor: str = Field(min_length=1, max_length=200)
    artifacts: list[Artifact] = Field(default_factory=list, max_length=60)
    traces: list[dict] = Field(default_factory=list, max_length=2000)
    exclusions: list[str] = Field(default_factory=list, max_length=100)
    semantic: dict | None = None

    @model_validator(mode="after")
    def bounded(self):
        if not self.artifacts and not self.traces:
            raise ValueError("Supply application artifacts or sample traces")
        if len({item.path for item in self.artifacts}) != len(self.artifacts):
            raise ValueError("Artifact paths must be unique")
        encoded = json.dumps(self.model_dump(), allow_nan=False)
        if len(encoded.encode()) > 3_000_000:
            raise ValueError("Discovery evidence exceeds 3 MB")
        if len({path for row in self.traces for path in flatten(row)}) > 200:
            raise ValueError("Select at most 200 distinct telemetry paths")
        if SECRET.search(encoded):
            raise ValueError("Remove credential patterns before importing evidence")
        return self


class Confirmation(Record):
    actor: str = Field(min_length=1, max_length=200)
    expected_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    task_type: Task
    purpose: str = Field(min_length=1, max_length=2000)
    mappings: dict[str, str] = Field(default_factory=dict, max_length=20)
    rationale: str = Field(min_length=1, max_length=2000)
    outcome_meaning_confirmed: bool = False

    @model_validator(mode="after")
    def valid(self):
        if not set(self.mappings) <= ALIASES.keys() or any(not value or len(value) > 200 for value in self.mappings.values()):
            raise ValueError("Use supported telemetry roles and existing dot-separated field paths")
        return self


class CalibrationRequest(Record):
    actor: str = Field(min_length=1, max_length=200)
    confirmation_id: str = Field(min_length=1, max_length=64)
    alert_fraction: float = Field(default=.1, ge=.01, le=.5)


class Activation(Record):
    actor: str = Field(min_length=1, max_length=200)
    expected_policy_id: str | None = Field(max_length=64)
    acknowledge_limitations: bool
    rationale: str = Field(min_length=1, max_length=2000)


def flatten(value, prefix="", depth=0):
    if depth > 8:
        return {}
    result = {}
    for key, item in value.items():
        if not isinstance(key, str) or "." in key or len(key) > 100:
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path, depth + 1))
        else:
            result[path] = item
        if len(result) > 200:
            raise ValueError("Select at most 200 fields per sample trace")
    return result


def infer_mappings(traces):
    paths = {key for row in traces for key in flatten(row)}
    mappings, ambiguities = {}, {}
    for role, aliases in ALIASES.items():
        matches = sorted(path for path in paths if path.rsplit(".", 1)[-1] in aliases)
        if len(matches) == 1:
            mappings[role] = matches[0]
        elif matches:
            ambiguities[role] = matches
    return mappings, ambiguities, sorted(paths)


def project(traces, mappings):
    """Retain selected scalar metadata; never keep arbitrary prompt/answer bodies."""
    rows = []
    for index, source in enumerate(traces):
        flat = flatten(source)
        values = {}
        for role, path in mappings.items():
            value = flat.get(path)
            if role in ("prediction", "actual", "confidence", "latency_ms"):
                values[role] = value if type(value) in (int, float) and math.isfinite(value) else None
            elif role in ("citations", "source_ids"):
                values[role] = [redact(item) for item in value] if isinstance(value, list) and len(value) <= 100 and all(isinstance(item, str) and len(item) <= 128 for item in value) else None
            else:
                values[role] = redact(str(value)) if type(value) in (str, int, float, bool) and len(str(value)) <= 200 else None
        rows.append({"case_id": checksum([index, source])[:24], "source_index": index,
                     "source_sha256": checksum(source), "values": values})
    return rows


def analyze(artifacts, traces):
    mappings, ambiguities, paths = infer_mappings(traces)
    findings, candidates, invalid = [], set(), []
    def finding(artifact, line, message):
        lines = artifact["content"].splitlines()
        findings.append({"kind": "observed_source", "message": message, "path": artifact["path"],
                         "sha256": artifact["sha256"], "line": line, "excerpt": lines[line-1][:300] if lines else ""})
    for artifact in artifacts:
        content = artifact["content"]
        if artifact["path"].endswith(".py"):
            try:
                tree = ast.parse(content)
            except (SyntaxError, ValueError, RecursionError):
                invalid.append(artifact["path"])
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = ast.unparse(node.func)
                    short = name.rsplit(".", 1)[-1].lower()
                    if short in ("predict", "predict_proba", "forecast", "retrieve", "search", "generate", "emit", "wrap", "wrap_tool"):
                        finding(artifact, node.lineno, f"Call boundary: {name}")
                    if short in ("predict_proba",):
                        candidates.add("classification")
                    if short in ("retrieve",):
                        candidates.add("rag")
                    for keyword in node.keywords:
                        if keyword.arg == "task_type" and isinstance(keyword.value, ast.Constant) and keyword.value.value in ("forecasting", "vision", "classification", "rag"):
                            candidates.add(keyword.value.value)
                            finding(artifact, node.lineno, f"Declared telemetry task: {keyword.value.value}")
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = " ".join(alias.name for alias in node.names)
                    if any(word in names for word in ("Classifier", "LogisticRegression")):
                        candidates.add("classification")
                        finding(artifact, node.lineno, f"Classifier import: {names}")
        elif artifact["path"].endswith(".json"):
            try:
                schema = json.loads(content)
                if isinstance(schema, dict) and "openapi" in schema:
                    finding(artifact, 1, f"OpenAPI operations: {', '.join(list(schema.get('paths', {}))[:12])}")
            except ValueError:
                invalid.append(artifact["path"])
    if "prediction" in mappings and "actual" in mappings:
        candidates.add("forecasting")
    if "confidence" in mappings:
        candidates.add("classification")
    if "citations" in mappings or "source_ids" in mappings:
        candidates.add("rag")
    if "vision" in candidates:
        candidates.discard("classification")
    task = next(iter(candidates)) if len(candidates) == 1 else "custom"
    summary = {
        "forecasting": "Appears to produce numeric predictions with outcome feedback. Confirm the target, units, horizon and meaning of actuals.",
        "classification": "Appears to classify inputs. Confirm what the labels mean and whether reference labels reflect real outcomes.",
        "vision": "Appears to classify visual inputs. Confirm the deployment population and meaning of reference labels.",
        "rag": "Appears to retrieve sources and produce answers. Confirm which sources are authoritative and what actions it may take.",
        "custom": "The available evidence does not identify one task reliably. Review the candidate tasks and field ambiguities.",
    }[task]
    return {"method": "bounded-python-ast-and-trace-schema-v1", "task_type": task,
            "candidate_tasks": sorted(candidates), "summary": summary, "status": "inferred_requires_confirmation",
            "mappings": mappings, "ambiguous_mappings": ambiguities, "available_paths": paths,
            "findings": findings[:100], "unparsed_artifacts": invalid,
            "unknowns": ["Business consequences and acceptable errors are not established by code.",
                         "Source declarations do not prove that every production path is instrumented.",
                         "Field names suggest meaning; owner confirmation is required before outcome-based calibration."]}


def validate_semantic(semantic, artifacts):
    """Semantic suggestions carry exact references and can never activate rules."""
    if semantic is None:
        return None
    if set(semantic) != {"summary", "hypotheses", "scenarios", "model", "prompt_sha256"}:
        raise ValueError("Invalid semantic analysis fields")
    by_path = {item["path"]: item for item in artifacts}
    if not isinstance(semantic["summary"], str) or len(semantic["summary"]) > 3000:
        raise ValueError("Semantic summary must be bounded")
    for collection in ("hypotheses", "scenarios"):
        rows = semantic[collection]
        if not isinstance(rows, list) or len(rows) > 12:
            raise ValueError("Semantic suggestions exceed the bound")
        for item in rows:
            if set(item) != {"description", "path", "quote"} or not isinstance(item["description"], str) or len(item["description"]) > 2000:
                raise ValueError("Invalid semantic suggestion")
            artifact = by_path.get(item["path"])
            if not artifact or not isinstance(item["quote"], str) or not item["quote"].strip() or len(item["quote"]) > 2000 or item["quote"] not in artifact["content"]:
                raise ValueError("Semantic suggestion lacks an exact frozen source quote")
    if not isinstance(semantic["model"], str) or len(semantic["model"]) > 200 or not isinstance(semantic["prompt_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", semantic["prompt_sha256"]):
        raise ValueError("Semantic provenance is required")
    return {**semantic, "status": "model_generated_unreviewed", "limitation": "Exact quotes verify provenance, not correctness of the interpretation or expected behavior."}


class Discovery:
    def __init__(self, workbench):
        self.workbench, self.store = workbench, workbench.store

    def scoped(self, application_id, kind, identifier):
        record = self.store.get(kind, identifier)
        if record["application_id"] != application_id:
            raise ValueError("Discovery record belongs to another application")
        return record

    def save(self, application_id, kind, payload, actor):
        record = {**payload, "application_id": application_id, "created_at": now()}
        record["checksum"] = checksum(payload)
        record["id"] = checksum([application_id, kind, record["checksum"]])[:32]
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            old = session.get(Entity, record["id"])
            if old:
                return old.payload
            session.add(Entity(id=record["id"], kind=kind, application_id=application_id, payload=record))
            self.workbench.audit(session, application_id, record["id"], 1, kind + "_created", actor, {"checksum": record["checksum"]})
        return record

    def create(self, application_id, body: DiscoveryImport):
        self.store.get("application", application_id)
        artifacts = [item.model_dump() for item in body.artifacts]
        analysis = analyze(artifacts, body.traces)
        semantic = validate_semantic(body.semantic, artifacts)
        # Store only selected metadata. Unselected raw trace bodies are discarded.
        # Ambiguous columns remain available as projections so corrections can select them.
        private_fields = {"prompt", "answer", "text", "content", "messages", "body", "password", "secret", "token", "headers", "email"}
        selected = {path: path for path in analysis["available_paths"] if not private_fields.intersection(path.lower().split('.'))}
        columns = {}
        for path in selected:
            roles = [role for role, aliases in ALIASES.items() if path.rsplit('.', 1)[-1] in aliases]
            if roles:
                role = roles[0]
                columns[path] = [row["values"][role] for row in project(body.traces, {role: path})]
            else:
                values = [flatten(row).get(path) for row in body.traces]
                columns[path] = [value if type(value) in (int, float) and math.isfinite(value) else
                    redact(value) if isinstance(value, str) and len(value) <= 128 else None for value in values]
        analysis["available_paths"] = sorted(columns)
        return self.save(application_id, "discovery", {"analysis": analysis, "semantic": semantic, "artifacts": artifacts,
            "trace_columns": columns, "trace_hashes": [checksum(row) for row in body.traces],
            "exclusions": body.exclusions, "actor": body.actor}, body.actor)

    def confirm(self, application_id, identifier, body: Confirmation):
        discovery = self.scoped(application_id, "discovery", identifier)
        if body.expected_checksum != discovery["checksum"]:
            raise ValueError("Discovery checksum changed; reload evidence")
        if any(path not in discovery["trace_columns"] for path in body.mappings.values()):
            raise ValueError("Mapping is unavailable; collect that field in a new discovery bundle")
        inferred = discovery["analysis"]
        corrections = {key: {"inferred": inferred.get(key), "confirmed": value} for key, value in
                       {"task_type": body.task_type, "mappings": body.mappings}.items() if inferred.get(key) != value}
        return self.save(application_id, "discovery_confirmation", {**body.model_dump(), "discovery_id": identifier,
            "corrections": corrections, "purpose_is_owner_confirmed": True}, body.actor)

    def calibrate(self, application_id, body: CalibrationRequest):
        from .discovery_calibration import prepare
        confirmation = self.scoped(application_id, "discovery_confirmation", body.confirmation_id)
        discovery = self.scoped(application_id, "discovery", confirmation["discovery_id"])
        result = prepare(discovery, confirmation, body.alert_fraction)
        return self.save(application_id, "discovery_plan", {"confirmation_id": confirmation["id"], "discovery_id": discovery["id"],
            "actor": body.actor, "alert_fraction": body.alert_fraction, **result}, body.actor)

    def activate(self, application_id, identifier, body: Activation):
        from .monitoring import Monitor, MonitorPolicy, IngestConflict
        plan = self.scoped(application_id, "discovery_plan", identifier)
        if not body.acknowledge_limitations or plan["status"] != "ready" or not plan["policy"]:
            raise ValueError("Review limitations and supply a ready calibrated plan")
        policy = MonitorPolicy(**{**plan["policy"], "actor": body.actor, "rationale": body.rationale})
        if any(rule.action != "flag" for rule in policy.rules):
            raise ValueError("Discovery activation is observation-only")
        activation_id = checksum(["discovery_activation", identifier])[:32]
        with self.store.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            old = session.get(Entity, activation_id)
            if old:
                return old.payload
            pointer = session.get(Entity, checksum(["monitor_config", application_id])[:32])
            active = pointer.payload["policy_id"] if pointer else None
            if active != body.expected_policy_id:
                raise IngestConflict("Active policy changed; review it before replacing it")
            record = Monitor(self.workbench).stage_policy(session, application_id, policy)
            activation = {"id": activation_id, "application_id": application_id, "plan_id": identifier,
                "policy_id": record["id"], "replaced_policy_id": active, "created_at": now(), "actor": body.actor,
                "mode": "observation", "dataset_sha256": plan["dataset"]["sha256"]}
            session.add(Entity(id=activation_id, kind="discovery_activation", application_id=application_id, payload=activation))
            self.workbench.audit(session, application_id, identifier, 1, "discovery_plan_activated", body.actor, activation)
        return activation
