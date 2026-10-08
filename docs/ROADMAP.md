# Roadmap: govern connected AI systems in production

Updated 2026-10-07. The user's runtime-monitoring direction replaces the earlier
RAG-judge/release-approval recommendation. The product connects developers'
existing systems through hooks, monitors risk signals and supports mitigation.

## v0.2: runtime foundation

Implemented: provider-independent HTTP contract, Python prediction/tool hooks,
scoped revocable keys, versioned policies, durable alerts, operator ownership and
disposition. Checks support vision confidence, custom numeric metrics, label/tool
allowlists, RAG citation identity, bounded text patterns, serving errors and
delayed forecast errors. Rolling mean shift is a simple signal, not a statistical
drift detector.

Observe mode records decisions. Explicit enforce mode can withhold outputs and
deny tools before execution. Private remote hosting uses a separate admin token
and explicit hosts/origins. This foundation supports integration development and
controlled pilots; production throughput, availability and detector accuracy
have not been established.

See [integration](RUNTIME_MONITORING.md), [research](PRODUCT_RESEARCH.md) and
[progress](PROGRESS.md) for capabilities, limitations and validation.

## Next milestone: a three-system testbed and dependable delivery

Completed 2026-10-08 UTC: three independent mini projects run actual digit,
NOAA forecast and documentation RAG models through normal HTTP hooks. The
isolated launcher saves evidence and stops its services, with optional bounded
dashboard exploration. Natural errors and deliberate faults are separated.
Bounded background sending, exact-body retry, heartbeats, incident grouping,
operator/app action records, local test-sink escalation, backup/restore and
conservative explicit retention are implemented. See the
[delivery plan](PILOT_PLAN.md), [measured evidence](TESTBED_EVIDENCE.md) and
[private pilot operations](PILOT_OPERATIONS.md).

| Priority | Work | Acceptance evidence |
| --- | --- | --- |
| Done | Connect three mini applications | Actual trained/generated outputs; split/provenance records; HTTP hooks; latency, errors, coverage and executed actions |
| Done | Bounded delivery and coverage | RAM buffering, exact retry, visible overflow, stale heartbeat status and real outage/restart tests; persistent outbox remains future work |
| Done | Private incident operations | Grouping, cooldowns, local test-sink retry audit, ownership and explicit operator attestation; external destinations remain future work |
| 4 | Task-specific quality | Actual labels/outcomes for vision/forecasting; validated drift tests; calibrated RAG grounding; measured misses/false positives |
| 5 | Private deployment operations | Retention, capacity/restore tests, TLS setup, authenticated operator identities and scoped permissions before broader access |

The next investment is a metadata-only persistent outbox, authenticated
operator roles and domain-calibrated checks. Keep text replay coverage explicit;
do not introduce raw-prompt retention accidentally. A customer pilot follows
when a team is available. Add detectors based on measured needs, not a universal
risk score. Existing observability outputs can supply numeric metrics.
OpenTelemetry ingestion, native async/JavaScript SDKs and batch uploads remain
future work; direct HTTP already supports other languages.

## Explicit boundaries

No inventory/discovery, tenant isolation, SSO, RBAC or compliance certification.
No universal hallucination/injection detector, full image/audio understanding,
demographic fairness computation or automatic retraining. No automatic rollback,
fallback model or human-review queue in the collector: mini applications now
demonstrate persisted review and explicitly selected subsequent fallback.
No deployment, paid model calls or external notifications have been performed.

The earlier RAG workbench and subscription experiment remain available; four
exploratory cases do not validate runtime detectors.
