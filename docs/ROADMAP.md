# Roadmap: govern connected AI systems

Updated 2026-10-08. Connect the developer's existing AI system through a hook,
monitor task-specific signals and support mitigation. No organization-wide
inventory or participating customer team is required for local development.

## v0.3: evidence and dependable private operations

Delivered on top of the v0.2 runtime/testbed foundation:

| Work | Evidence |
| --- | --- |
| Actual runtime GIF | Live digit inference, withholding, named mitigation, durable heartbeat and labeled recorded RAG replay |
| Crash-safe metadata outbox | Frozen-body replay, leases, persisted counters/deadlines/bounds; hard producer death after collector commit produces one alert |
| Named operator roles | Scoped viewer/reviewer/operator/admin accounts, revocable sessions, server-supplied actors; backend and browser access checks |
| Grounding evidence | Frozen source hashes, claim/quote validation, explicit coverage gaps and immutable profile approval; real subscription judgments and a natural answer |
| Distribution signals | Reference snapshots, non-overlapping ECDF windows, conservative alpha spending; actual vision/forecast control measurements |

See [progress](PROGRESS.md), [access](OPERATOR_ACCESS.md),
[delivery](RUNTIME_DELIVERY.md), [detector contracts](DETECTOR_EVIDENCE.md),
[measured detector evidence](DETECTOR_VALIDATION.md) and
[original three-system evidence](TESTBED_EVIDENCE.md).

The vision confidence gate still misses one natural error and flags 52 correct
predictions. Small engineering RAG calibration is not independent human validation.
Serially dependent NOAA replay has no nominal false-alert guarantee.
Experimental semantic/distribution signals flag or request review; they cannot block.
Text cannot be replayed from the metadata outbox. These are delivered limitations.

## Recommended v0.4: dependable incident delivery and domain validation

Prioritize the path from a detected risk to an investigated, evidenced mitigation.
Build/test it with the existing mini applications before a customer pilot.

1. **Durable incident delivery.** Signed webhooks, per-destination secrets,
   restricted destinations, retry/dead-letter/replay and authenticated delivery
   audit. Validate with owned local sinks first; actual external recipients require
   explicit authorization. An accepted notification is not completed mitigation.
2. **Domain validation.** More diverse grouped RAG claims and retrieval failures,
   judge error analysis and independent label review when available. For forecasts,
   use temporal/block calibration and outcome lateness; report sensitivity, misses
   and false alerts on an untouched chronological holdout. For vision, monitor
   actual-label quality alongside confidence and sampling shift.
3. **Integration tooling.** Native async Python and TypeScript SDKs, batch delivery,
   stable event contracts and OpenTelemetry adapters. Preserve synchronous
   enforcement, explicit outage behavior and visible coverage gaps.
4. **Operational hardening.** Longer restart/load/restore drills, outbox disk-space
   handling and explicit retention horizons. Add SSO/MFA and finer administrative
   permissions when the access/deployment scope justifies them.

Acceptance: restart/replay without duplicate incidents; visible terminal delivery
failure; version-bound calibration; held-out false-positive/miss reports; actual
application action evidence; no hidden text retention or overall governance score.

## Boundaries

No inventory/discovery, organization/tenant isolation or compliance certification.
No universal hallucination/injection detector, full image/audio understanding,
automatic fairness computation or retraining. The collector does not automatically
roll back a model, choose a fallback or inspect independent application state.
Mini applications demonstrate persisted review and explicitly chosen fallback.
No hosted deployment, paid API usage or real-recipient notification has occurred.
