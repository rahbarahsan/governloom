# Launch evidence — 2026-10-10

Reviewed machine-readable report:
[launch-2026-10-10.json](experiments/launch-2026-10-10.json).
The reports are local development captures, not independent customer deployments.
The first capture predates the new gate and final version/docs. The later capture
follows committed release code (`20656e1`) and records its Python source snapshot
hash as well as the Git revision.
Credentials, raw SQLite, signing keys and logs remain in ignored `data/`.

## First success and delivery

The fresh Python environment was created by the public `scripts/quickstart.py`
command; it installed dependencies and built the dashboard. Setup took 104.144 s
and the first actual model incident arrived 119.475 s after setup started.
This one Windows/Python 3.13/Node 22 environment had network package access; the
result is not a ten-minute setup guarantee on every machine.

Both captures used actual local digit inference, collector HTTP and a signed
receiver. The receiver committed a notification, deliberately returned 503 for
the lost receipt, then deduplicated the retry: **two attempts, one notification**.
Application review resolved against the public label, a linked outcome was sent,
and a named scripted operator attested to the inspected withheld-response hash.
Delivery alone did not mark the incident mitigated. All owned services stopped.

A separate automated drill kills a worker with `os._exit(23)` immediately after
receiver acceptance, then recovers its lease and proves one persisted receiver
notification. Other checks cover concurrent claims, stale-owner fencing after
terminal/replay state changes, Retry-After, deadline exhaustion, redirect/DNS
guards and named-role scope. These verify software behavior, not detector quality.

## Observed local overhead

The fresh-install development capture measured 32 confidence-clear controls through
the same real digit service. Serial median HTTP latency was 76.618 ms without the
hook and 178.808 ms with synchronous input/output checks; median paired overhead
was 98.558 ms and monitored p95 (lower empirical quantile) was 250.472 ms. The other capture's measurements
are retained separately in the report, not pooled into this comparison.

These include model inference, local HTTP and SQLite work on one host. They do not
establish sustained ingestion throughput, multi-user load or production availability.
Use background metadata observation when boundary enforcement is unnecessary;
measure the latency/coverage trade-off for your own service before rollout.

## Calibrated vision trade-off

The new `governloom.calibration.calibrate_threshold` chooses a threshold using
only calibration labels and an explicit empirical false-positive budget. The
example freezes original UCI labels, model version and disjoint index sets before
evaluating the 360-case held-out split. Held-out outcomes never tune the threshold.

| Gate | Captured errors | Missed errors | Correct predictions flagged | Correct predictions clear |
| --- | ---: | ---: | ---: | ---: |
| Original 20th confidence-percentile gate | 17 | 1 | 52 | 290 |
| 5% empirical calibration false-positive budget | 15 | 3 | 26 | 316 |

The model makes 18 errors and 342 correct predictions. The new gate halves false
alarms while missing two more errors. Its calibration false-positive rate is
13/261 = 4.98%; its held-out rate is 26/342 = 7.60%, exceeding the nominal 5%
calibration target. **An empirical calibration budget is not a held-out or
production guarantee.** Public benchmark/writer dependence and domain shift
remain limitations. The quickstart enforces to demonstrate withholding; begin a
new-domain integration in observe mode and calibrate against its actual labels.

RAG's [existing real judgments](DETECTOR_VALIDATION.md) have only four held-out
authored claims, plus one natural generated answer. No additional judge calls
or independent human labels were collected in this release. NOAA replay remains
historical, revised and serially dependent. These limits remain visible; no
universal hallucination, fairness or governance score is claimed.

## Reproduce

```sh
python scripts/quickstart.py --check --venv data/new-launch-venv
.venv/Scripts/python.exe -m examples.vision.calibration
```

For prepared environments use `--skip-install`; on macOS/Linux use
`.venv/bin/python`. Each run creates a fresh ignored workspace and stops its
owned services. Review any report before publishing it. CI runs a headless real
digit workflow, native SDK integration and Chromium checks without provider calls.

For actual remote integrations, independently measure receiver processing,
application action evidence, outage recovery, clock skew and task-specific error
budgets. Package registry publication, hosted deployment and a customer pilot are
later work, not results demonstrated by these captures.
