# Connect an existing AI system

GovernLoom observes signals from your running model without needing its provider
key. Use HTTP from any language, or a Python hook for synchronous callables/tools.
Task types include vision, RAG, forecasting, classification, generative and custom.
You choose relevant metrics. Integration does not automatically detect every risk.

## Start and connect

Follow README installation, then run from the repository root:

```powershell
npm --prefix web run build
.\.venv\Scripts\python.exe -m uvicorn governloom.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Monitoring evaluates synchronously; it does not need
the legacy evaluation worker. Existing SQLite databases gain the new runtime
table on startup. Back up a stopped database before upgrading; existing cases
and runs remain intact. There is no automatic downgrade.

1. Under Applications, create/select a connection for your existing system.
2. Sign in when named access is configured; the server supplies your audit name.
   Under Monitoring, configure a policy using templates,
   edit limits/actions/mitigation guidance, and activate it.
3. Create a scoped ingestion key. Copy it once into your serving environment as
   `GOVERNLOOM_INGEST_KEY`; keep it server-side. Only its hash is stored. Revoke
   it in the console when necessary.
4. Hook the actual prediction/tool boundary. Inspect receipts and alerts.
   Record alert ownership/disposition after taking action.

## Python: vision or classification

Install GovernLoom from this checkout in the serving environment. Substitute the
callable you already use and adapt the mapper to its real result:

```python
import os
from governloom.hook import RuntimeHook, PolicyViolation

hook = RuntimeHook(
    "http://127.0.0.1:8000", os.environ["GOVERNLOOM_INGEST_KEY"],
    mode="observe", timeout_seconds=1, on_unavailable="raise",
)
predict = hook.wrap(
    your_predict_function,
    task_type="vision", model_version="your-model-version",
    application_version="your-serving-release",
    output_mapper=lambda result: {
        "metrics": {"confidence": float(result.confidence)},
        "labels": [str(result.label)],
    },
)
result = predict(your_image)
```

Your image is passed to your callable and not uploaded. Only selected confidence,
labels and measured serving latency are sent. Confidence is not measured accuracy.
Use classification or custom for other tasks; custom numeric metrics also support
segmentation, anomaly detection and audio without adding provider dependencies.
Ground-truth metrics must use actual labels/outcomes, computed upstream.

## RAG: selected citations and optional transient text

```python
answer = hook.wrap(
    your_rag_function,
    task_type="rag", model_version="your-model-version",
    application_version="your-serving-release",
    output_mapper=lambda result: {
        "citations": result.cited_document_ids,
        "source_ids": result.retrieved_document_ids,
        "text": result.answer,  # optional: scanned, not stored
        "metrics": {"retrieved_count": len(result.retrieved_document_ids)},
    },
)(your_question)
```

An input mapper can explicitly supply input text. Source-ID membership does not
establish claim support. Text checks detect a few secret/email/instruction
patterns; misses and false positives are possible. An optional approved claim-support
profile accepts transient upstream judge evidence and frozen passage hashes;
see [detector evidence](DETECTOR_EVIDENCE.md). The collector does not call a provider.

## Forecasting: outcomes arrive later

Save the returned event/trace ID with your prediction. Later, submit its actual
outcome using matching task/environment/model/application version and trace.
The original event must be an output from the same application.

```python
context = dict(trace_id=your_opaque_prediction_id, task_type="forecasting",
               model_version="your-model-version", application_version="your-release")
receipt = hook.emit(**context, phase="output", metrics={"prediction": float(your_prediction)})
# Store receipt["event_id"] alongside your prediction. Later:
outcome = hook.emit(**context, phase="outcome", related_event_id=receipt["event_id"],
                    metrics={"actual": float(your_actual_outcome)})
```

The collector derives absolute_error when both numbers exist. A policy can flag
it above a domain-specific tolerance. This is per-prediction error, not aggregate
MAE/MAPE or proof of causal drift. Send externally computed aggregate quality
metrics as custom metrics when needed.

## HTTP from any language

`POST /api/runtime/events`, Content-Type application/json, and
`Authorization: Bearer <application ingestion key>`:

```json
{
  "event_id": "your-stable-unique-event-id",
  "trace_id": "your-opaque-request-id",
  "phase": "output",
  "task_type": "custom",
  "environment": "production",
  "model_version": "your-model-version",
  "application_version": "your-release",
  "metrics": {"latency_ms": 43.2, "your_quality_metric": 0.82},
  "client_mode": "observe"
}
```

Phases: input/output/tool/error/outcome. Optional fields: timezone-aware occurred_at,
text, labels, citations, source_ids, tool_name, error_type, related_event_id.
Up to 40 finite metrics and 32,000 text characters; opaque IDs only. Never put
personal data or secrets in metadata. See /docs for the complete schema.

Receipts contain action (allow/flag/review/block), policy/engine versions, checks,
alert IDs and a cursor. Check statuses are clear/triggered/not_applicable/
insufficient_evidence. Missing telemetry is not clear. Overall allow means no
configured rule triggered, and does not assert sufficient coverage.

Replaying the exact serialized event, including its original timestamp, returns
the same receipt without another alert. Changed content with the same ID returns
409; invalid credentials 401; rate limit 429; invalid schema 422. Policy limit
defaults to 600 events/minute; a wrapped call usually emits two events. This is
not a throughput guarantee. The synchronous hook does not retry; preserve the
exact body yourself. Optional ObservationHook supplies bounded background retry;
see [delivery coverage](RUNTIME_DELIVERY.md).

## Actions and outages

- Observe mode returns predictions even when a block is requested.
- Enforce mode raises PolicyViolation on block: input blocks prevent target
  invocation; output blocks withhold results. Catch it to implement your fallback
  or review process. Flag/review require your own handling.
- wrap_tool sends a tool event before invocation. Place it at the actual
  side-effect boundary. Output monitoring cannot undo earlier side effects.
- on_unavailable="raise" is the default: rejection/timeout prevents continuation.
  Explicit "continue" permits operation, increments hook.unavailable_count and
  sets last_receipt.action to unavailable. Export this through your operations
  monitoring. Background observation has bounded RAM or an opt-in metadata-only
  SQLite outbox with visible losses and expiry. See [delivery](RUNTIME_DELIVERY.md).
- Target exceptions are preserved; error telemetry records type, not message.
  Collector failure while reporting the target error does not replace it.

Use separate hook instances if concurrent callers need reliable last_receipt
inspection. Enforcement is synchronous; async frameworks can use their HTTP client.
A collector decision is not proof that a client enforced it. An operator's
"mitigated" disposition is asserted, not automatically verified.

## Policies, evidence and privacy

Policies are immutable; activation creates a version. Events retain their policy
ID. Retrieve historical policy with GET /api/monitor-policies/{id}. Alerts preserve
rule evidence, severity, mitigation and revision. Review requires actor, owner,
disposition, rationale and expected_revision; stale/concurrent edits fail.
Audit records are at the application's review-events endpoint. Named access binds
actors to authenticated accounts; local development actor names remain assertions.
Owner assignments and mitigation/verification attestations are not independent proof.

Mean shift uses arrival order and a bounded scan of the previous 1,000 events,
isolated by task/phase/environment/model/application version. It requires a full
window and is not a statistical drift test. Approved distribution profiles add
frozen references, sample assumptions and lifetime alert budgets. Late events and changed policies
need care when interpreting windows.

Main text is transient and excluded from stored events/alerts. Selected metadata,
metrics, text length, payload hash and findings are stored. Known email/secret
patterns are redacted in auxiliary values too; this is not anonymization of
arbitrary metadata. A hash is not encryption. Configure reverse-proxy/client
logging appropriately. Legacy source/trace imports intentionally store submitted
content and have different semantics.

## Private hosting and pilot limits

Default bind is loopback. Use [named operator access](OPERATOR_ACCESS.md) for
administration, explicit GOVERNLOOM_ALLOWED_HOSTS/GOVERNLOOM_ALLOWED_ORIGINS and a
TLS reverse proxy. Remote hook URLs require HTTPS and reject redirects. Legacy
private development without accounts can use GOVERNLOOM_ADMIN_TOKEN (32+ characters)
under Collector access. It cannot bypass named accounts. Sessions/tokens stay in
page memory; never use them as ingestion keys. Keep the collector private.

SQLite serializes ingestion transactions. Application scopes and grouped incidents
are supported, but there is no distributed ingestion, organization/tenant isolation
or automatic retention. Storage grows with traffic; choose pilot
duration and retention/backup plans before sending production data. The dashboard
polls every two seconds and shows bounded pages, not an SLA. External notifications,
automatic rollback and hosted deployment are not configured. These checks do not
establish universal safety, fairness or regulatory compliance.
