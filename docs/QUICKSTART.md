# First real incident

From a checkout, install Python 3.13+ and Node 22+, then run one command from the
repository root on Windows, macOS or Linux:

```sh
python scripts/quickstart.py
```

The script prepares a local Python environment, installs pinned model/collector
dependencies, builds the dashboard and starts an isolated named-account collector,
actual digit-recognition service, signed incident receiver and delivery worker.
Initial dependency installation needs internet access. Subsequent model inference
uses bundled public digits and a locally trained classifier: no provider login,
provider key, paid request or remote dataset download is involved.

The terminal prints console/digit-service URLs and the path to a **private**
`data/quickstart-.../credentials.json`. Read that file locally to sign in as
`quickstart-admin`. It contains a generated password and scoped ingestion key;
keep it private. Credentials are not command arguments or public evidence.
Unix files use owner-only permissions; on Windows restrict the checkout/data
directory to your account using NTFS permissions.

## What to inspect

1. **Monitoring:** a real natural low-confidence prediction is withheld. The
   confidence threshold came from a separate calibration split with an explicit
   5% empirical false-positive budget. The held-out rate exceeds that budget;
   inspect [the measured trade-off](LAUNCH_EVIDENCE.md) before adapting the gate.
2. **Incident delivery:** the signed receiver commits its notification, deliberately
   loses its first receipt, then deduplicates the retry. Inspect two sender attempts
   and one receiver notification. The incident has its own identity and status.
3. **Application response:** the digit service records a review, resolves it against
   its actual public benchmark label and sends a linked outcome. An authenticated
   scripted operator records the inspected withheld-response hash and mitigation.
4. **Actual digit service:** load held-out digit pixels and run another prediction.
   Further uncertain predictions reopen the grouped incident and require review.

The initial operator actions are scripted, and their verification is an attestation.
They are not independent human review. The selected two digits illustrate behavior;
the separate 360-case report measures model quality and the gate's misses/false alarms.

Keep the terminal open while exploring. **Ctrl+C stops every owned service.** Private
databases, credentials, secrets, logs and the non-secret `report.json` remain under
ignored `data/`. Run again for a fresh isolated workspace; existing directories are
never overwritten. Nothing is deployed or sent to an external recipient.

For a finite installation/integration check that stops automatically:

```sh
python scripts/quickstart.py --check
```

For an already prepared development environment, add `--skip-install`. To exercise
a separate clean Python environment, use `--venv data/fresh-venv`. Reports record
setup time, first-incident time, delivery attempts, mitigation and serial HTTP
overhead. The script does not publish these reports automatically.

## Connect your own system

Create an application, configure task-specific rules and issue its ingestion key.
Use the [integration guide](INTEGRATIONS.md) for synchronous Python, native async
Python, Node/TypeScript, linked outcomes or selected OpenTelemetry span evidence.
Use [incident delivery](WEBHOOKS.md) to connect your receiver. A receiver does not
automatically roll back a model or establish that mitigation happened.

The quickstart's Python 3.13 requirement comes from its pinned actual-model setup.
The core collector and Python hook continue to support Python 3.11+ without those
model dependencies. An independently prepared core installation can follow
[runtime monitoring](RUNTIME_MONITORING.md).

## Troubleshooting

- Missing Node/npm: install Node 22+ including npm and rerun. The dashboard needs it;
  the Python SDK/collector can be used separately.
- Dependency/proxy failure: retain the install error, fix network access and rerun.
  The script creates no model/provider subscription session.
- Application startup failure: inspect the private workspace's `logs/`. Every
  service uses a free loopback port; failed startup still stops owned children.
- Notification remains pending: inspect `worker.log`, the exact destination
  allowlist and the signing-secret directory. Failed deliveries are visible and
  can be replayed by an operator after the receiver is repaired.
- Restore/recovery: retain both collector database and private webhook secret
  directory. A collector database alone cannot reconstruct signing secrets.
