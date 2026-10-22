# Guided starter policies and measurable coverage

GovernLoom v0.7 recommends policies for one connected application. Import discovery
evidence, review the inferred behavior and mappings, confirm consequential choices,
then evaluate the proposed controls. Ready controls can be selected independently;
missing grounding evidence does not prevent a citation or tool-permission check.

## Where the policies come from

The bundled catalogue is maintained in the repository and versioned with a content
checksum. Five packs contain nine controls with input requirements, metric methods,
threshold selection, suggested investigation and limitations. Optional model
analysis cannot edit these trusted definitions.

- [NIST AI RMF 1.0, MEASURE 1.1](https://airc.nist.gov/airmf-resources/playbook/measure/)
  motivates context-specific metric selection and documentation of unmeasured
  risks across the packs. The Playbook is guidance; the framework is under revision.
- [OWASP LLM09:2025, Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/)
  contextualizes RAG evidence inspection. Citation identity covers only a narrow
  part of this risk and does not establish factual support.
- [OWASP LLM06:2025, Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
  contextualizes explicit tool permissions. Recorded attempts do not prove action
  success; downstream authorization and high-impact approvals remain necessary.

These are original GovernLoom starter controls mapped to selected objectives, not
verbatim standard policies, complete framework coverage or compliance certification.
ISO clause mappings are not supplied. Framework revisions never silently change
a frozen plan or active policy.

## What is calculated

| Pack | Measurements | Runtime proposal |
| --- | --- | --- |
| Common | Per-field presence, missing versions, latency p50/p95 | Latency flag with an owner-confirmed SLA |
| Forecasting | MAE, RMSE, signed prediction-minus-actual bias, exceedance rate | Residual above a calibration-only empirical quantile |
| Vision/classification | Accuracy, per-class precision/recall, confusion counts, gate precision/error recall/false-positive rate | Calibrated low-confidence flag |
| RAG | Missing/unknown citation rates; macro retrieval recall@k with confirmed relevance labels | Missing/unknown citation flag |
| Tools | Out-of-allowlist attempt count/rate | Tool outside owner-confirmed allowed names |

The common pack links to live pending/overdue/resolved counts in the existing
outcome coverage view. These cover explicitly tracked predictions for the
application; they are not reconstructed from historical actuals or frozen into a
discovery dataset. The check timestamp is separate. Start the monitor worker for
persisted deadline incidents; see [expected outcomes](EXPECTED_OUTCOMES.md).

Each frozen result records evaluator version, dataset checksum, split, value,
denominator and excluded count. A gate's denominator may be flagged predictions,
all errors or all correct predictions: excluded counts include cases outside that
population, not only invalid data. Undefined precision/recall stays unavailable.
Confusion matrices have predicted classes as rows and actual classes as columns.
Per-class reports support at most 100 distinct labels; accuracy remains available
above that bound and the detailed reports explain their unavailable state.

Retrieval IDs preserve rank, including repeated document positions. Recall@k uses
unique relevant IDs in the first k positions and macro-averages evaluable queries.
Empty relevant sets have undefined recall and are excluded. Default k is five.
Retrieved documents alone are not relevance judgments.

## Owner decisions and defaults

Discovery suggests mappings; ambiguous fields require correction. Owners confirm
that actuals/reference labels are observed outcomes before quality calibration.
Relevance judgments have a separate confirmation. Confirmation records provenance;
it is not independent label validation.

Forecast alert fraction and classification false-positive budget have separate
API names and exploratory 10% defaults. They have different meanings, and neither
defines acceptable harm. Thresholds use calibration data only; held-out results
and exceeded budgets remain visible. Dependent forecasting replays do not establish
nominal false-alert probabilities.

Owners supply tool permissions and any serving SLA. Observed or advertised tools
are never automatically authorized. The initial permission control requires a
nonempty allowlist; a deny-all discovery recipe is not provided. Numeric outcome
deadlines come from the application's feedback process using `outcome_due_at`;
historical dates do not establish deadlines.

Inspect each recommendation's evidence, methods, gaps, response and references.
Save changed selections or deferral rationales into a new immutable plan. Activation
requires a ready selected runtime control, current confirmed understanding,
unchanged active policy and explicit acknowledgment. Generated policies flag only.
Descriptive accuracy or retrieval recall alone does not create a quality gate.

Semantic grounding, fairness, successful unauthorized actions, business harm and
full production coverage are not inferred by this catalogue. Existing approved
grounding profiles retain their [evidence workflow](DETECTOR_EVIDENCE.md).
Model-generated scenarios remain suggestions, not evaluation labels.

## Public interfaces

`GET /api/policy-catalogue` uses collector administration authentication; all
authenticated operator roles can read definitions. It contains no application
evidence. Application discovery and plan routes retain scope restrictions.

Confirmation accepts optional `allowed_tools`, `latency_sla_ms` and
`relevance_meaning_confirmed`. New mapping roles are `tool_name` and
`relevant_source_ids`; `source_ids` supplies ordered retrieval results.

Plan creation accepts `forecast_alert_fraction`,
`classification_false_positive_budget`, `retrieval_k`, optional `selected_controls`
and `dismissed_controls` (control ID to explanation). Omitted selection chooses
ready controls except explicit deferrals. Explicit selection of an unready control
prevents activation. Legacy `alert_fraction` is a fallback when the task-specific
budget is omitted.

Plans add `catalogue`, `recommendations`, `metric_results`, `calibration_settings`,
`control_decisions` and `live_metric_sources`. Existing v0.6 fields remain readable.
Activated rules, checks, alerts and incidents carry `control_reference` with the
frozen catalogue checksum, control ID/version and source details. The version-one
runtime event contract is unchanged.

Python `DiscoveredObserver.tool(observation)` applies confirmed mappings and live
versions. Node `RuntimeHook.emit` or `wrapTool` emits the same tool events.
Observation flags never prevent side effects by themselves.

## Reproduce the owned examples

```powershell
python -m examples.policy_testbed --directory data/policy-demo
python -m examples.policy_testbed --directory data/policy-demo-all --forecast-snapshot data/miniapps/noaa-2026-10-07.txt
```

Install [example dependencies](../examples/requirements.txt). The run checks actual
digit classification, local retrieval and a trained [tool router](../examples/tools/README.md).
No prewritten monitoring policy or provider calls are needed. Relevance labels are
authored; citation faults are deliberate controls, not fresh generated answers.
Fresh-wheel CI also runs an actual-model discovery consumer. See
[release evidence](V07_EVIDENCE.md) for results and limitations.
