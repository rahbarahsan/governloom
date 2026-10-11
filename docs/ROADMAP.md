# Roadmap: govern connected AI systems

Updated 2026-10-11. Connect a developer's existing AI system through explicit
telemetry, monitor task-specific risks and support an evidenced response.

## v0.4: first public developer launch

Delivered and verified. All five [release CI jobs](https://github.com/rahbarahsan/governloom/actions/runs/38094170488)
passed at `864e2d3`:

| Work | Delivered boundary |
| --- | --- |
| Reliable incident delivery | Registered host-allowed receivers, Standard Webhooks signing, transactionally frozen bodies, retry/restart, visible dead letters and scoped replay |
| First useful workflow | One-command real digit-model quickstart with named access, owned signed receiver, deliberate receipt loss, application outcome and scripted mitigation |
| Integration tooling | Sync/native async Python, Node/TypeScript, bounded observation batches, frozen event preparation, v1 schema and selected numeric Python span adapter |
| Detection trade-offs | Calibration-only false-positive budget selection, untouched held-out comparison and explicit budget violation/misses |
| Open-source onboarding | Short README, measured launch evidence, SDK/receiver guides, contributor/conduct/security policies and issue templates |
| Verification | Core matrix, actual mini applications, native SDK/real collector integration and browser workflows in CI; updated runtime GIF |

See [quickstart](QUICKSTART.md), [integrations](INTEGRATIONS.md),
[launch evidence](LAUNCH_EVIDENCE.md), [webhooks](WEBHOOKS.md) and [progress](PROGRESS.md).
Package registry publication, hosted deployment, announcements and customer
adoption have not occurred. This release supplies a reviewable developer launch.

## v0.3 and v0.2 foundations

Runtime hooks/scoped ingestion, immutable policies and alerts, grouped incidents,
application action acknowledgment, metadata outbox/heartbeats, named roles and
reviewed grounding/distribution profiles. Vision, NOAA forecasting and model-backed
documentation RAG have actual-model evidence. [Earlier detector evidence](DETECTOR_VALIDATION.md)
and [three-system results](TESTBED_EVIDENCE.md) preserve the measured limitations.

## v0.5: outcome coverage and connected-system validation

Implemented; final push and six-job release CI are pending. The release adds:

- Numeric feedback deadlines, persisted missing/late outcome coverage and an
  incident watchdog, demonstrated against the real forecast mini-application.
- Chronological block thresholds, per-label vision analysis and frozen grouped
  RAG source-support/retrieval-gap evaluation with explicit unresolved evidence.
- Signing rotation, database-plus-secret recovery, conservative delivery retention
  and real SQLite capacity failure/rollback plus a bounded 600-event HTTP drill.
- Fresh installed-wheel standalone consumer and a non-root container build/restart
  CI path, with an updated twelve-frame runtime GIF.

[Measured results](V05_EVIDENCE.md) preserve the retrieval defect and its correction,
remaining misses, authored labels and empirical forecast limitations. An owned
consumer verifies packaging; independent developer feedback remains unavailable.

## Recommended v0.6: improve real deployment evidence

1. **Independent onboarding feedback.** Observe developers connecting their own
   services; measure setup completion, integration effort and recurring use.
   Owned mini applications remain the fallback when participants are unavailable.
2. **Domain validation.** Broader grouped RAG claims, retrieval failures and judge
   error analysis; independent label review when available. For forecasts use
   temporal/block calibration, outcome lateness and untouched chronological holdouts.
   For vision evaluate additional data/sampling groups and domain label quality.
   Improve the three remaining grouped retrieval misses without reusing held-out
   answers as calibration; collect fresh realistic questions and source changes.
3. **Longer operational drills.** Sustained restart/load/restore testing, disk-space
   exhaustion and backup/rotation during longer runs. Delivered-notification
   retention exists; audit, dead-letter and resolved-expectation growth still
   need measured storage budgets.
   Receiver delivery latency and application action evidence need separate budgets.
4. **Distribution/deployment.** Consider registry publication after clean setup
   feedback; validate the container with deployment-specific requirements.
   Add broader OTel integration, SSO/MFA
   and finer permissions where real deployment/access requirements justify them.

Success means independent users can connect systems, understand coverage gaps
and investigate/respond to risks. Stars are not a usage or reliability measure.

## Current evidence limits

The original vision gate catches 17 of 18 errors with 52 false positives; the new
budget gate catches 15 with 26 false positives and three misses. Its held-out
false-positive rate exceeds the 5% empirical calibration budget. RAG evidence
remains small/authored; NOAA replay is serially dependent and revised. No
independent human validation or production-scale guarantee is claimed.

Notification receipt is not completed mitigation. Operator verification remains
an attestation. Retention only removes delivered notifications for closed incidents;
full recovery bundles include signing secrets. Neither supplies a disk quota.
The metadata outbox cannot replay raw text.

No organization-wide inventory/discovery, tenants, compliance certification,
universal hallucination/injection detector, automatic fairness computation or
retraining. The collector does not independently roll back a model or inspect
application state. No paid API work or external-recipient notifications occurred.
