# GovernLoom

[![checks](https://github.com/rahbarahsan/governloom/actions/workflows/checks.yml/badge.svg)](https://github.com/rahbarahsan/governloom/actions/workflows/checks.yml)

Connect your existing AI system, flag task-specific risks, deliver incidents and
record the application's response. Vision, RAG, forecasting, classification and
custom systems share a provider-independent event contract.

Your model performs inference; GovernLoom evaluates the evidence you select.
Binary inputs and provider credentials are not automatically uploaded. Missing
evidence stays visible; a clear check is not a safety certification.

## Try a real incident

Install **Python 3.13+ and Node 22+**, clone this repository and run:

```sh
python scripts/quickstart.py
```

One command installs dependencies, builds the console and starts an isolated
actual digit-recognition service, named-account collector and signed receiver.
A real low-confidence prediction is withheld; a lost receipt exercises retry/
deduplication; application review, linked outcome and mitigation are recorded.
The terminal prints URLs and a private credentials-file path. **Ctrl+C stops all
owned services.** No provider key/login or paid model request is needed: the
example trains and runs a real classifier using bundled public digits.

[Quickstart](docs/QUICKSTART.md) · [Connect your own system](docs/INTEGRATIONS.md)
· [Signed incident delivery](docs/WEBHOOKS.md)

![Actual digit inference, named mitigation, signed delivery and recorded real RAG evidence.](docs/media/demo.gif)

[Still preview](docs/media/demo-poster.png) · [Capture provenance](docs/media/README.md)

Operator actions are scripted. RAG scenes replay a recorded real model answer
and judgment; they are labeled, with no new inference or independent validation.

## What ships in v0.4

- Python, native async Python and Node/TypeScript hooks, explicit observe/enforce
  behavior, linked outcomes, observation batches and selected OpenTelemetry spans.
- Policies, scoped keys, live alerts, grouped incidents and application action
  evidence with named viewer/reviewer/operator/admin access.
- Signed incident webhooks with host-controlled destinations, persisted retry,
  restart recovery, visible failures and audited replay.
- Restart-safe metadata outbox, delivery/heartbeat coverage and reviewed grounding/
  distribution profiles with immutable provenance and explicit evidence gaps.

[Release notes](CHANGELOG.md) · [Roadmap](docs/ROADMAP.md)
· [Earlier evaluation workbench](docs/LEGACY_WORKBENCH.md)

## Evidence and limits

The original digit gate catches 17 of 18 natural errors and flags 52 correct
predictions. The new calibration-budget gate catches 15 errors and flags 26
correct predictions on the same 360 held-out cases. Confidence is not accuracy.
RAG calibration is small
and engineering-authored; source membership alone is not grounding. Historical
NOAA residuals are dependent and have no nominal false-alert guarantee.

[Launch measurements](docs/LAUNCH_EVIDENCE.md), [detector results](docs/DETECTOR_VALIDATION.md)
and [three-system evidence](docs/TESTBED_EVIDENCE.md) report denominators and limits.
One fresh-install Windows capture reached a real incident in 119.475 seconds;
that is an observed environment, not a setup-time guarantee.

Controlled self-hosted integrations are the demonstrated scope. Production
scale/availability, tenant isolation and SSO/MFA are not established. Notification
receipt is separate from mitigation, and operator verification is an attestation.
Protect SQLite and separate signing secrets. See [access](docs/OPERATOR_ACCESS.md),
[operations](docs/PILOT_OPERATIONS.md) and [security reporting](SECURITY.md).

The core collector/hook supports Python 3.11+ without model dependencies.
Python and Node packages are built from this checkout; neither has been published
to a registry. No hosted deployment has occurred.

## Contribute

[Contributing and checks](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md)
· [Decisions](docs/DECISIONS.md) · [Resume progress](docs/PROGRESS.md)

Use issue templates for reproducible developer problems. Keep keys, private
prompts and customer data out of public reports. Original code uses
[Apache-2.0](LICENSE); [third-party attribution](docs/THIRD_PARTY.md) covers
datasets and dependencies.
