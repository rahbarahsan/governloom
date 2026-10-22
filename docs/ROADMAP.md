# Roadmap: govern connected AI systems

Updated 2026-10-21. Connect a developer's existing AI system through explicit
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

Delivered at `aca7c10`. All six [release CI jobs](https://github.com/rahbarahsan/governloom/actions/runs/38116779187)
passed, including fresh installed-wheel onboarding and container restart. The release adds:

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

## v0.6: explore, confirm and prepare monitoring

Delivered at `4e58313`; all six [release CI jobs](https://github.com/rahbarahsan/governloom/actions/runs/39559521550)
passed. The owner's role is to review and correct
an evidence-backed draft rather than supply a prewritten policy or metric design.

1. Bounded local source/OpenAPI/trace inspection with no target execution, optional
   model-assisted purpose/boundary/scenario analysis and exact source references.
2. Immutable owner confirmations, corrected telemetry mappings and frozen evaluation
   datasets with explicit unavailable states, split checks and selected observations.
3. Calibration-only numeric forecast/classification proposals and RAG citation identity
   checks; held-out misses, false positives, budget violations and blind spots remain visible.
4. Guarded observation-only activation and a reusable public mapping adapter that
   preserves live versions. New understanding or replaced policies invalidate stale activation.
5. Actual owned digit/NOAA discovery-to-incident workflows, an honest recorded RAG
   evidence gap, updated browser workflow/GIF and installed-package/CI checks.

[Discovery guide](DISCOVERY.md) · [Measurements](V06_EVIDENCE.md).
Three source-cued owned task matches do not establish general discovery accuracy.
Model-generated scenarios are unreviewed and do not become ground truth automatically.

## v0.7: guided starter policies and measurable coverage

Implemented: versioned source-backed starter catalogue, automatic recommendations
from confirmed capabilities, metric definitions/results with denominators, owner
permissions/SLA/relevance decisions, selected observation controls and recorded
deferrals. Runtime incidents preserve frozen control sources. Existing actual
vision/forecasting and retrieval plus a new local trained tool router verify the
workflow; package/browser/CI delivery checks are tracked in [progress](PROGRESS.md).
See [catalogue guide](POLICY_CATALOGUE.md) and [release evidence](V07_EVIDENCE.md).

## Recommended v0.8: validate and deepen guided monitoring

First, test discovery and policy recommendations on fresh layouts/field names,
then build reviewed scenario datasets and improve the demonstrated retrieval miss.
Keep the following work incremental rather than promising universal evaluation:

1. **Fresh application tests.** Add owned applications with different layouts,
   field names and missing dependencies; measure wrong inferences, corrections,
   unresolved questions and telemetry mapping failures without task declarations.
   Independent developer feedback is useful when available, not a delivery prerequisite.
2. **Reviewed scenario datasets.** Help owners review model-proposed cases with
   source evidence; freeze approved labels and new held-out groups. Preserve real,
   synthetic and unresolved examples separately. Improve actual retrieval misses
   using fresh evaluation questions rather than tuning to old held-out answers.
3. **Domain evidence.** Add multi-series/horizon forecast and deployment subgroup
   recipes, broader source-language/framework adapters and explicit metric prerequisites.
   Validate recommendations against outcome availability and real response costs.
4. **Operating budgets.** Longer load/restart/recovery studies, discovery/audit/history
   storage budgets and deployment requirements. Broader OTel, SSO/MFA and registry
   publication should follow demonstrated integration/distribution needs.

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
