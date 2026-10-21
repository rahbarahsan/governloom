# Explore an application and prepare its monitoring

GovernLoom v0.6 inspects one explicitly selected application, drafts its likely
behavior and suggests measurements from available evidence. The owner confirms
or corrects that draft. A frozen evaluation dataset and an observation policy
follow; no prewritten policy or metric questionnaire is required.

## Collect evidence locally

Install the Python package from this checkout and export representative observations
as UTF-8 JSONL. Inspect the application directory without running its code:

```sh
governloom explore ./your-app --traces samples.jsonl --output data/discovery.json
```

Use `python -m governloom.cli` if the console command is outside your PATH.
The command reads visible Python, JavaScript/TypeScript, JSON, Markdown, TOML and
YAML files. Python calls/imports are parsed; JavaScript signatures are heuristic.
Optional `--openapi schema.json` adds a local OpenAPI document. There is no remote
fetch, package installation, target import, target execution or automatic code edit.
Source declarations do not establish production behavior or full instrumentation.

The default analyzer uses source signatures and trace schemas. For richer purpose,
boundary and candidate-scenario analysis, opt in explicitly:

```sh
governloom explore ./your-app --traces samples.jsonl --output data/discovery-ai.json --subscription --model gpt-6.1-sol
```

This optional development adapter uses an existing local ChatGPT Codex CLI login,
one tool-disabled request, an explicit model selector and a 180-second deadline.
API-key authentication/fallback is rejected; the collector never starts inference.
Selected source excerpts leave the machine through that configured provider path.
The adapter accepts exact source quotes and records model/prompt provenance.
Quote validity establishes provenance, not semantic correctness. Its scenarios
remain unreviewed and never become evaluation truth or executable tests automatically.
The request/session interface can be supplied by another trusted integration;
the shipped CLI adapter is specifically the existing-login path described here.
See [official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
and [authentication](https://learn.chatgpt.com/docs/auth).

## Confirm the draft in the console

Open **Applications → Explore your application**, choose a name and import the
reviewed bundle. Named administrator access creates the workspace. Existing
application operators can import additional bundles under **Application discovery**.

Review the inferred description, candidate task and exact source evidence.
Mappings are prefilled when a field has one unambiguous match. Select alternatives
for ambiguous/custom field names. Confirm that actual values/reference labels
mean observed outcomes before enabling outcome-based calibration. Describe business
consequences only where the evidence cannot establish them.

Confirmation and correction history are immutable. New evidence creates another
snapshot. A newer confirmed understanding invalidates activation of older proposals.
Viewer/reviewer accounts can inspect evidence; operators/admins configure this
workflow. Named authentication supplies the audit actor, not submitted actor text.

## Observation format and automatic recipes

Each JSONL object can use nested objects. Field mappings use dot-separated paths;
array traversal is not supported. Common aliases such as `y_pred`, `y_true`,
`predicted_value`, `actual_value`, `true_label` and `retrieved_ids` are recognized.
Custom scalar columns can be selected during confirmation.

```json
{"timestamp":"2024-01-01","prediction":12.4,"actual":13.1,"split":"calibration","model_version":"forecast-v1","application_version":"service-v1","environment":"staging"}
```

This is one format example, not a sufficient evaluation dataset. Supply actual
observations rather than repeated placeholder records.

| Application | Required evidence | Prepared measurement and policy |
| --- | --- | --- |
| Numeric forecasting | Prediction/observed actual, date or aware timestamp, one model/application scope; at least 20 calibration pairs and five held-out pairs | MAE, RMSE, signed bias, missing values and a calibration-only empirical residual quantile; flag linked outcome errors above it |
| Vision/classification | Confidence in [0,1], predicted/reference labels, versions; calibration has at least 20 correct controls and one error, plus five held-out cases | Error capture/misses, false positives and a confidence gate selected on calibration correct controls; flag low confidence |
| RAG | Citations and retrieved source IDs across separate splits, versions | Citation membership/absence counts and flag-only identity checks; claim support and retrieval recall remain unavailable without their additional evidence |

Supplied `split` values must be `calibration`/`held_out`. Forecast calibration must
strictly precede held-out timestamps; duplicate timestamps are rejected for this
single-series recipe. Otherwise the oldest two thirds are calibration and the
newest third held out. Classification/RAG use a deterministic group split when
none is supplied. Explicit group overlap and exact duplicate observations crossing
splits are rejected. Near-duplicate/semantic grouping requires supplied group IDs.

Missing values remain unavailable. Forecast thresholds represent historical
residual exceedances, not independently labeled harm or false positives. This
point-residual recipe is separate from the earlier [block experiment](V05_EVIDENCE.md).
Serial dependence invalidates nominal probability claims. Classification labels
remain application-supplied; confidence does not guarantee correctness. RAG source
membership does not prove answer grounding. Measured latency is shown when mapped;
missing latency and unknown outcome deadlines require instrumentation.

The proposal shows counts, held-out results, budget warnings, version scope,
limitations and outstanding business decisions. Changing the exploratory alert
fraction creates another immutable proposal; it does not turn the held-out set
into independent fresh evidence. Repeated human tuning against held-out results
can invalidate its evaluation role; collect a fresh holdout when choosing policies
from those comparisons.

## Connect the reviewed mapping

After reviewing the frozen plan, explicitly activate its **flags-only observation
policy**. Replacing an active policy needs explicit review and a matching current
policy ID. Concurrent/repeated activation creates one policy. A previously activated
plan cannot silently overwrite a later policy. No automatic mitigation or blocking
is introduced.

Download the full frozen monitoring plan and use its prepared mapping:

```python
import json
import os
from governloom.discovered_hook import DiscoveredObserver

with open("monitoring-plan.json", encoding="utf-8") as source:
    plan = json.load(source)
observer = DiscoveredObserver(os.environ["GOVERNLOOM_ENDPOINT"],
    os.environ["GOVERNLOOM_INGEST_KEY"], plan)

prediction = observer.output(application_observation)
# When the numeric actual becomes available:
observer.outcome(actual_observation, prediction)
```

The application's dictionaries contain the confirmed field paths, including real
live model/application versions. The mapper never stamps an old calibration version
onto a new model; version mismatches yield insufficient evidence at the collector.
Keep the prediction receipt to link actuals. Optional aware `outcome_due_at` on
`output` enables the existing [deadline worker](EXPECTED_OUTCOMES.md). The owner
chooses that real feedback deadline; no SLA is invented from historical dates.
Store event IDs/bodies explicitly if retrying; the adapter does not retry side effects.

## Access, bounds and remaining work

Hidden paths, dependency/build/data directories, sensitive filenames and
symlinks/reparse points are excluded. Source files are bounded to 50 KB; evidence
contains at most 60 artifacts, 500 KB locally collected source text, 2,000 traces,
200 distinct telemetry paths and a 3 MB imported bundle. Scans inspect at most
5,000 file entries. Excluded/unparsed files are reported; this is not complete
program analysis. CLI output refuses overwrite and uses owner-only Unix mode;
configure private NTFS permissions on Windows.

Review bundles before import. Credential-pattern and assignment filtering are
best-effort, not a guarantee that source files contain no sensitive information.
The collector retains selected source text for evidence review and bounded scalar/
ID telemetry columns. Unselected prompt/answer bodies are discarded. This differs
from transient runtime text checks. Evidence/history has no automatic retention
or total disk quota; protect the database/backups and plan storage budgets.

Task discovery is inferred, not certain. Current automatic recipes cover the
listed contracts; code in other languages can still be shared as semantic context
only when supported by collection, or integrated through explicit traces. Arbitrary
binary models/images are not inspected. Guided semantic case review, broader
domain recipes, production representativeness and independent owner studies remain
future work. [Measurements](V06_EVIDENCE.md) distinguish real-model integration
from authored software tests and scripted owner acceptance.
