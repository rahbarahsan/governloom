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

No participating team is available. First build three independent mini projects
with actual models: digit recognition, chronological forecasting on public NOAA
observations, and RAG over real project documentation. Connect them through the
normal hook/HTTP boundary and measure natural model errors separately from
deliberate fault scenarios. See the [delivery plan](PILOT_PLAN.md) for datasets,
attribution, stages, acceptance gates and operational design.

| Priority | Work | Acceptance evidence |
| --- | --- | --- |
| 1 | Build and connect the three mini applications | Actual trained/generated outputs; split/provenance records; real HTTP hooks; p50/p95/p99 added latency, errors, coverage and executed mitigation |
| 2 | Reliable delivery and coverage | Bounded async buffering, backoff/idempotent retry, overflow visibility, heartbeat/missing-signal alerts; outage tests |
| 3 | Incident operations | Group repeated alerts, cooldowns, controlled webhook destinations, retry audit, ownership and mitigation verification |
| 4 | Task-specific quality | Actual labels/outcomes for vision/forecasting; validated drift tests; calibrated RAG grounding; measured misses/false positives |
| 5 | Private deployment operations | Retention, capacity/restore tests, TLS setup, authenticated operator identities and scoped permissions before broader access |

The next investment is dependable telemetry and incident response exercised
against these actual model services. A customer pilot follows when a team is
available. Add detectors based on measured needs, rather than an
unvalidated universal risk score. Existing observability outputs can supply
numeric metrics. Later adapters should complement existing tracing stacks.
OpenTelemetry ingestion, native async/JavaScript SDKs and batch uploads remain
future work; direct HTTP already supports other languages.

## Explicit boundaries

No inventory/discovery, tenant isolation, SSO, RBAC or compliance certification.
No universal hallucination/injection detector, full image/audio understanding,
demographic fairness computation or automatic retraining. No automatic rollback,
fallback model or human-review queue: applications implement those actions.
No deployment, paid model calls or external notifications have been performed.

The earlier RAG workbench and subscription experiment remain available; four
exploratory cases do not validate runtime detectors.
