# Connect an existing AI system

The collector accepts selected telemetry from any AI system. Risk coverage depends
on the evidence you supply: images/arrays/audio and provider credentials are not
automatically uploaded. Keep raw-input selection and outage behavior explicit.
Create the application's policy and ingestion key in the dashboard first.

The Python package is installed from this checkout (`pip install -e .`), not an
assumed PyPI release. Node packaging below is also from source; no npm publication
has occurred. Use HTTPS for a remote collector and keep its key server-side.

## Synchronous Python

```python
import os
from governloom.hook import RuntimeHook, PolicyViolation

hook = RuntimeHook(os.environ["GOVERNLOOM_ENDPOINT"], os.environ["GOVERNLOOM_INGEST_KEY"],
                   mode="enforce", on_unavailable="raise")
predict = hook.wrap(existing_model.predict, task_type="vision", model_version="your-model-v1",
    application_version="your-service-v1",
    output_mapper=lambda result: {"metrics": {"confidence": float(result.confidence)}})
try:
    result = predict(image)
except PolicyViolation as risk:
    enqueue_application_review(risk.receipt)
```

`existing_model`, `image` and `enqueue_application_review` are your application's
objects. The wrapper calls the actual model. Input blocks prevent invocation;
output blocks withhold a result after inference. `mode="observe"` reports the
decision without blocking. An explicit `on_unavailable="continue"` allows a call
through an outage and increments missing-coverage counters; it cannot establish
that an unchecked output was safe. Use `DurableObservationHook` for metadata-only
background delivery; enforcement stays on the synchronous path.

## Native async Python

Install the optional transport with `pip install -e ".[async]"`:

```python
from governloom.async_hook import AsyncRuntimeHook

async with AsyncRuntimeHook(endpoint, key, mode="enforce") as hook:
    answer = hook.wrap(existing_rag.answer, task_type="rag", model_version="your-model-v1",
        application_version="your-rag-v1", output_mapper=lambda result: {
            "text": result.answer, "citations": result.citations, "source_ids": result.retrieved_ids})
    result = await answer(question)
```

The underlying target must be async. Sync/async telemetry mappers are supported.
Receipts are local to each async task, and the context manager closes its owned
HTTP client. Cancellation propagates; target exceptions retain their original
identity. Citation membership checks establish IDs, not factual grounding. To
check claim support, supply a reviewed version-bound profile and upstream judgment
as described in [detector evidence](DETECTOR_EVIDENCE.md).

## Node/TypeScript

Build the SDK in this checkout:

```sh
npm --prefix sdks/typescript ci
npm --prefix sdks/typescript run build
```

In your application's directory, install the local package with
`npm install /path/to/governloom/sdks/typescript`. Node 22+ provides its fetch and
timeout transport; it has no runtime npm dependencies.

```typescript
import {RuntimeHook, PolicyViolation} from "@governloom/runtime";

const hook = new RuntimeHook(process.env.GOVERNLOOM_ENDPOINT!,
  process.env.GOVERNLOOM_INGEST_KEY!, {mode: "enforce", onUnavailable: "raise"});
const predict = hook.wrap(existingModel.predict.bind(existingModel),
  {task_type: "classification", model_version: "your-model-v1", application_version: "service-v1"},
  {output: result => ({labels: [result.label], metrics: {confidence: result.confidence}})});
```

Async targets and mappers are supported. `wrapTool(target, scope, "write")` checks
before the side effect. A block throws `PolicyViolation` with its receipt; enqueue
an actual application review/acknowledgment as appropriate. Redirects are rejected
without forwarding ingestion credentials. Errors do not include response bodies
or credentials. `onUnavailable: "continue"` returns an unavailable receipt for
unchecked events; monitor `unavailableCount`. Retry of a target or side effect is
your application's decision, never automatic SDK behavior.

## Batch observations and stable retries

`POST /api/runtime/events/batch` accepts 1–100 **observation** events. The response
has per-item `status` and `receipt`/`error`; a successful HTTP response does not
mean every item succeeded. Conflicts/rate limits can coexist with accepted items.
Invalid schemas reject the batch before processing. Exact duplicate bodies return
their original receipt. Never batch decisions needed before a call/tool side effect.

Prepare once before sending so ID, timestamp and body stay identical:

```python
from governloom.contract import prepare_event
events = [prepare_event(trace_id="opaque-trace-1", phase="output", task_type="forecasting",
    model_version="forecast-v1", application_version="service-v1", metrics={"prediction": 12.5})]
async with AsyncRuntimeHook(endpoint, key) as hook:
    result = await hook.emit_batch(events)
    # Retain these exact events and retry only entries that need delivery.
```

TypeScript uses `prepareEvent(fields)` and `await hook.emitBatch(events)`. Do not
regenerate `occurred_at` under an existing event ID. Prepared text-bearing bodies
must not enter the metadata-only durable outbox. Both SDKs validate receipts and
leave retry scheduling to the caller; the durable Python observation hook handles
persisted metadata retry automatically.

The version-one event schema is [runtime-event-v1.schema.json](contracts/runtime-event-v1.schema.json).
The API's `/docs` describes receipts and route schemas. Minor releases preserve
existing fields/semantics; clients should tolerate additional response fields.

## Forecast outcomes

Keep the output receipt's `event_id`, `trace_id`, environment and model/application
versions. When the actual outcome arrives, emit `phase="outcome"` with
`related_event_id` and matching scope. If the prediction metric is `prediction`
and the outcome metric is `actual`, the collector derives `absolute_error`.
Configure a domain-approved tolerance and expected outcome timing separately.
Missing/delayed actuals cannot be treated as zero error or a clear detector result.

## Existing OpenTelemetry spans

`governloom.otel.span_event` accepts a completed Python `ReadableSpan` and projects
its trace/span identity, completion timestamp and latency. Select numeric mappings:

```python
from governloom.otel import span_event
event = span_event(span, task_type="vision", model_version="model-v1",
    application_version="service-v1", metric_attributes={"confidence": "model.confidence"})
receipt = await observation_hook.emit(**event)
```

Here `observation_hook` is an async hook in observe mode. Feed the adapter from your
existing span-processing integration; it is not an OTLP server or automatic global
instrumentation. Prompt, user and arbitrary span attributes are omitted. Missing
mapped signals remain unavailable. A completed span supports retrospective
observation, not enforcement before its operation. ReadableSpan interface fixtures
exercise this adapter; an installed OpenTelemetry SDK was not used in this capture.
See [official Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/).
