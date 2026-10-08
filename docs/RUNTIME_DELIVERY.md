# Delivery coverage and incident handling

Use `RuntimeHook` for synchronous decisions at input/output/tool boundaries.
Use `ObservationHook` for background telemetry; its later decision cannot
change an already returned result. Both use the same event contract/scoped key.

```python
from governloom.delivery import ObservationHook, HeartbeatReporter

observe = ObservationHook(collector_https_url, scoped_key,
    timeout_seconds=1, queue_size=256, max_queue_bytes=1_000_000,
    max_age_seconds=30, max_attempts=4, backoff_seconds=0.1)
heartbeat = HeartbeatReporter(observe, "your-opaque-agent-id", interval_seconds=30)
try:
    predict = observe.wrap(your_actual_predict, task_type="vision",
        model_version="your-model", application_version="your-release",
        output_mapper=lambda result: {"metrics": {"confidence": float(result.confidence)}})
    result = predict(your_image)
    # Export observe.stats through your own operations monitoring as well.
finally:
    heartbeat.close()
    shutdown = observe.close(drain_seconds=5)
```

## Queue, retry and shutdown

`emit` returns `queued` or `dropped`, not a collector decision. IDs/timestamps
and serialized bodies are frozen once and preserved on retries. Overflow drops
the new event. Count/serialized-byte bounds include the in-flight event. Text
lives only in RAM until sending/discarding; there is no persistent event outbox.

Retries cover transport failures and HTTP 408/429/500/502/503/504, with exponential
backoff and jitter. Authentication, invalid input/conflicts, redirects and invalid
receipts are terminal. Numeric/date `Retry-After` hints are respected; an event
whose hint exceeds its age budget expires. These formats follow
[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after).
The transport timeout bounds each attempt, not total target latency.

Counters distinguish emitted, queued, accepted, dropped, failed, expired,
retries, auth_failed, rate_limited, invalid and pending. Retry/error categories
count attempts; terminal categories count events. At a stable snapshot:
`emitted = accepted + dropped + failed + expired + pending`.
`queued` is cumulative admission, not current backlog. A lost receipt leaves
delivery uncertain until exact replay succeeds; a final failure might already
exist at the collector.

Close stops admission and drains until its deadline, then discards waiting
events. An in-flight request cannot be cancelled; `worker_alive`/pending remain
visible until timeout/completion. Custom transports must supply finite deadlines.
A process crash loses RAM events. Counters are client reports, not independently
verified completeness.

## Heartbeats

`POST /api/runtime/heartbeats` uses the application ingestion key. The reporter
sends separately from inference traffic, with opaque agent/boot IDs, sequence,
aware timestamp and cumulative counters. Exact replay is idempotent; stale
sequences/counter rollback are rejected. A new boot starts at sequence one.
The reporter preserves a body until acknowledgment. At most 1,000 current agent
IDs per application are stored; previous-boot counter histories are not retained.

Policy `heartbeat_timeout_seconds` defaults to 120 (maximum one day). Admin agent
API/dashboard marks overdue heartbeats **stale**, even with no prediction traffic.
Missing agents do not prove integration completeness. Set cadence for batch
systems and a distinct stable agent ID per process slot.

The actual vision service supports `ENABLE_BACKGROUND=1`, `/observe-background`
and `/delivery`, with independent two-second heartbeats. It returns the real
classifier result plus delivery admission; it cannot withhold a returned result.

## Incidents and application actions

Triggers keep event-level alerts. Repeats group by application, environment,
task, model/application version, policy and rule within fixed
`incident_window_seconds` buckets (default 300). Boundaries and policy changes
split groups. Incidents retain first/latest evidence, count, owner and revision.
Owner/disposition changes are audited; new triggers reopen mitigated/false-positive
groups. Dashboard shows recent incidents/actions (100 per view), current agent
coverage and individual alerts. Admin history limits go up to 500; events use
cursor pagination.

Application `acknowledge_action` supplies an alert ID, action type and opaque
evidence ID **after** its actual action. Types: withheld, review_queued,
tool_denied, fallback_selected. Keys cannot acknowledge another application's
alert; replay is idempotent. Mini applications acknowledge after saving review,
withholding output, denying a write or selecting a subsequent fallback.
Acknowledgment transport failure appears as a service error; local action
records remain available for retry.

Admin verification requires a matching criterion, operator, rationale and
SHA-256 of inspected evidence. State **verified_by_operator** explicitly means
attestation. The collector does not inspect application files or authenticate
the asserted actor behind a shared token. Alert disposition is separate.

## Local escalation sink

Policies set `escalate_after_count` (default 3) and
`escalation_cooldown_seconds` (default 300). Repeats enqueue durable notifications;
cooldown limits repeats. At most 1,000 pending per application are admitted;
incident records expose queue drops.

With a separate `MINI_STATE`, start:

```powershell
.\.venv\Scripts\python.exe -m uvicorn examples.test_sink:create_app --factory --host 127.0.0.1 --port 8110
```

Admin POST `/api/runtime-escalations/dispatch-test-sink` with `endpoint` set to
`http://127.0.0.1:8110/governloom-test-sink`, plus `actor` and `limit`. That exact
loopback path and sink identity handshake are required; collector credentials
are never forwarded. Leases serialize dispatch; stable-ID retries are audited.
At most five attempts, bounded backoff and Retry-After; hints over one day fail
explicitly. Invoke again for due retries; no automatic dispatcher runs.
`SINK_LOSE_FIRST_ACK=1` commits then returns 503 to prove deduplication. No
messages to real recipients, Slack or email are part of this checkpoint.
