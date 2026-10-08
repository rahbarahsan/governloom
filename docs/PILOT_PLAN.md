# Plan: test GovernLoom against three independent AI applications

Status: implemented as a local private-pilot checkpoint, 2026-10-08 UTC.
No participating customer team is required. Three repository-owned mini projects
run actual models through the public hook/API. The six stages below now have
working code and local evidence; deployment/SSO, durable event outbox and customer
calibration remain later requirements. See [actual-model evidence](TESTBED_EVIDENCE.md),
[delivery/incident behavior](RUNTIME_DELIVERY.md) and [operations](PILOT_OPERATIONS.md).

## Outcome and scope

An engineer can start the collector and a mini application, generate ordinary
traffic, inspect risk evidence, and observe a concrete mitigation. The same
workflow must work across vision, forecasting and RAG without changing the
collector for each model provider. Keep the mini projects outside the collector
package, with their own dependencies, model code, service endpoints and storage.

The projects validate integration, operational reliability and narrowly defined
checks. Their model outputs and measured errors are real. Corruptions, outages
and deliberate response changes are separate, labeled fault scenarios. Results
are evidence from our own test systems, not customer adoption or universal risk
detection. No organization-wide inventory is part of this plan.

## Three mini projects

| Project | Actual model and inputs | GovernLoom signals | Application mitigation |
| --- | --- | --- | --- |
| Digit recognition service | Train a small random forest on public 8x8 handwritten digit images; serve held-out images and accept user-supplied pixel arrays | Confidence, predicted label, latency; correctness only after known labels arrive | Put uncertain predictions in a persisted review queue; explicit enforcement withholds a blocked result |
| CO2 forecasting service | Fit a trend/seasonal regression to chronological NOAA monthly observations; compare with seasonal-naive forecasts | Prediction, horizon, latency, linked actual outcome and absolute error in ppm | Flag an observed error, record investigation, and test a configured fallback for subsequent predictions |
| Documentation RAG service | Retrieve passages from actual GovernLoom documentation with TF-IDF; generate answers through the existing opt-in local subscription adapter | Retrieved/cited IDs, transient input/output text, latency and supplied usage metrics | Withhold a blocked response; deny an unauthorized write operation before execution; retain an operator review record |

### Vision data and evaluation

Use scikit-learn's bundled digits dataset. It contains actual digit images, not
generated labels or scripted predictions. The bundled set is a copy of the UCI
test subset; our train/calibration/test split within it is a new internal split,
not the original UCI benchmark protocol.
[Loader documentation](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html).

Attribute E. Alpaydin and C. Kaynak, *Optical Recognition of Handwritten Digits*
(1998), UCI, DOI 10.24432/C50P49. UCI lists CC BY 4.0. Obtain the images through
the installed library; preserve attribution and transformation details rather
than copying an unattributed image corpus into the repository.
[Dataset and license](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits).

Use seeded, stratified train/calibration/test partitions and record their index
hashes. Fit on training only; select the review threshold on calibration and
freeze it before held-out evaluation. Report accuracy, review fraction, error
capture and confident wrong predictions. Low confidence is a signal, not a
ground-truth error label. Test occlusion/noise separately using fixed seeds;
report clean and corrupted results independently.

### Forecasting data and evaluation

Download NOAA's monthly CO2 text file once into ignored local data storage.
Preserve its header, source URL, retrieval time and SHA-256; reuse that snapshot
for a report. Raw remote data will not be fetched automatically during ordinary
tests or bundled into the collector.
[NOAA data page](https://gml.noaa.gov/ccgg/trends/data.html),
[monthly file and attribution notice](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt).

The source contains interpolation/missing-value indicators and documents the
2022-2023 observation-site change. Preserve those distinctions; do not count
interpolated or unavailable outcomes as independently observed ground truth.
Include NOAA/Scripps attribution as indicated by the source header.

Use an initial training period, subsequent calibration period, then chronological
walk-forward testing. Every fit can use only observations available at its
forecast origin. Freeze model settings and alert tolerance after calibration;
record training cutoff and model fingerprint for every prediction. Start with
one-month forecasts; add longer horizons as separate comparisons. Actual values
are submitted later through an outcome endpoint, linked to the original event.
Historical replay remains labeled historical, even when replayed in real time.

Report MAE/RMSE, baseline comparison, errors above tolerance, alert coverage and
missing outcomes. Artificial forecast offsets are fault injections and must not
enter natural-model error totals. A late outcome cannot retroactively prevent
the original prediction; test mitigation on subsequent requests.

### RAG data and evaluation

Use the real README, runtime integration guide and selected source API docs,
covered by this repository's license. Record git revision, source hashes, passage
boundaries, retrieval settings, model selector and prompt version. Keep reference
labels out of generation prompts. Ask answerable questions, unanswerable questions
and hostile-instruction questions; preserve actual responses and omissions.

Reuse the bounded local subscription adapter with explicit opt-in, deadline and
request cap. It uses the existing local login; no account credential is exported
to a mini-project image or GitHub Actions. This adapter is a development target,
not a hosted multi-user inference service. Support a replaceable generator
interface for a user-configured model later.
[Official non-interactive execution documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

Citation membership and existing text patterns remain narrow checks. Report
unsupported answers they miss. Invalid-citation mutations and test credential
strings are clearly labeled post-generation faults, not natural model behavior.
Inspect claim evidence separately; do not present an uncalibrated model judgment
as independently reviewed truth. CI uses a fake generator for transport tests
only; real generation evidence comes from bounded local captures.

## Delivery sequence

| Stage | Deliverable | Exit checks |
| --- | --- | --- |
| 1 | First vertical slice: vision service plus real HTTP collector | Train real model; serve held-out image; receive hook event; produce risk evidence; execute review/withhold action; persist/reload records; stop processes cleanly |
| 2 | Forecast and RAG services using the same integration boundary | Real predictions and answers; matched delayed outcomes; no cross-application access; ordinary traffic and injected faults reported separately |
| 3 | Repeatable testbed launcher and report | One command starts isolated services, verifies readiness, runs bounded scenarios, saves evidence and shuts down its own processes; optional mode leaves a dashboard open for exploration |
| 4 | Reliable observation delivery and coverage | Background sending, bounded queues, exact-body retry, backoff, shutdown/drain behavior, heartbeat and visible losses; collector outage/restart and saturation tests |
| 5 | Incident handling and measured mitigation | Group repeat alerts, ownership, cooldown/escalation rules, audited retry, and application-confirmed action outcomes; prove tool denial before a side effect |
| 6 | Private pilot operations and release evidence | Explicit retention, backup/restore, capacity tests, TLS deployment guide and operator identity requirements; publish measured limits and unresolved gaps |

Implementation locations: `examples/vision/`, `examples/forecasting/`,
`examples/rag/`, shared testbed tooling under `examples/`, and separate optional
ML requirements. Core installation and existing demo
must continue to work without installing example-model dependencies.

Use one focused checkpoint for the vision vertical slice, one for each additional
application, then separate launcher/evidence, delivery-reliability and incident
operations checkpoints. Add CI coverage alongside each stage. Do not defer all
verification to the end or ship three scaffolds with no running model.

## Integration and operational design

The collector remains on port 8000; proposed mini services use 8101/8102/8103 with
configurable ports. Each owns its own application state and one scoped ingestion
key. Provision through public admin APIs. Keep keys in process memory/environment,
never reports, logs or tracked files. Bind locally for the testbed. Model calls
must remain in the mini applications; they must not import the collector's
Monitor/store implementation to manufacture receipts.

Two delivery paths are required:

- Observation sends telemetry asynchronously with bounded overhead. A queued
  event is not a received event, and its later decision cannot block a response
  that was already returned.
- Enforcement obtains a synchronous decision at the actual input/output/tool
  boundary, with a deadline and explicit outage behavior. Fail-open/fail-closed
  choices are per integration; no background queue may masquerade as enforcement.

Retry only retryable failures, preserve event ID/timestamp/body, apply bounded
backoff with jitter, and expose failed authentication, invalid events and rate
limits distinctly. Define queue size, maximum age, overflow policy and shutdown
drain deadline. Start with a bounded in-memory queue. If adding a durable outbox,
persist permitted metadata only; do not silently introduce raw prompt/output
retention. Text checks whose evidence cannot be replayed must show coverage gaps.

Add per-agent boot IDs, event counters and separate heartbeats, with configurable
expected activity/cadence. A batch forecaster's quiet interval is not necessarily
an outage. Distinguish emitted, queued, accepted, dropped and unevaluated events;
state any sampling. Missing forecasts/labels need explicit completeness reports.

Incidents group by application, environment, deployment, rule and time window,
while retaining event-level evidence. Record the originating policy, first/last
seen, count, owner and escalation history. An application acknowledgment includes
action type and related event/alert ID; report requested, acknowledged and verified
states separately. An operator marking mitigated remains an assertion unless a
defined outcome check supplies evidence. External notifications use a test sink
first; no messages to real recipients are part of this plan.

## Evidence and acceptance gates

Every run records dataset/corpus/model/policy hashes, dependency versions, split
definitions, request counts, scenario labels and collector receipts. Save private
captures under ignored data storage and publish only deliberately reviewed reports.
Include hook-off versus hook-on latency distributions (p50/p95/p99), sample counts,
event acceptance/loss, evaluation coverage, alert grouping and mitigation outcomes.
Keep inference latency and hook overhead separate; use warmup and comparable
requests. Repeated load-test requests do not increase independent accuracy samples.

Required integration gates:

- Clean traffic, model mistakes, missing evidence, corrupted input, invalid
  citations, unauthorized tools and delayed outcomes are independently observable.
- Exact retries create one event/alert set; restart/outage/overflow exposes any
  loss. No zero-loss guarantee without a tested persistence mechanism.
- Enforcement blocks before a disallowed side effect and withholds the flagged
  output; observation preserves the model's return behavior.
- Keys remain scoped/revocable, raw images/audio are not uploaded, transient text
  is not stored in collector events, and reports contain no credentials.
- An incident's ownership/action audit survives restart, and its evidence remains
  linked to the original policy/model versions.
- Existing backend/browser/build checks pass; add example tests and isolated
  multi-process tests. CI performs no subscription inference or mutable-data fetch.

Select numeric latency/coverage targets after baseline measurement and document
them before stress testing. Measure each task separately. Threshold boundaries
can be tested exactly; detector precision/recall needs appropriately labeled
held-out examples and explicit denominators. The testbed cannot establish a
customer's acceptable risk, regulatory compliance or production SLA.

## What is needed from the user

No participating team or shared provider key is needed to begin. Use the public
vision/forecasting data and repository documentation described above. Existing
authorization covers bounded local subscription inference; the RAG runner must
still require explicit opt-in and record usage. Deployment, paid model usage,
external notifications and customer data remain separate future decisions.

After the three-system testbed and reliability gates pass, a participating team
can bring a real service. That later pilot adds domain-specific thresholds,
business outcomes and operator feedback; it is not a prerequisite for this work.
