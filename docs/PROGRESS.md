# Release progress

## Active follow-through (2026-10-08)

User approved all four next steps: replace the GIF with actual runtime capture,
restart-safe metadata delivery, named authenticated operator roles, and stronger
grounding/drift checks with measured misses and false positives. Work is active;
the previous delivered checkpoint below remains the baseline. Implement and test
each boundary, keep focused commits, then regenerate the GIF against the final UI,
run the full checks, push and stop owned servers. Raw text/credentials must never
enter the durable outbox. Engineering calibration is not independent human review.
Research: OWASP password/session guidance and the DKW–Massart concentration bound
were checked against primary sources. No customer participation is required.

First slice complete: `governloom.outbox.DurableObservationHook` freezes metadata
in SQLite, resumes pending deliveries, persists counters/deadlines/attempts, fences
leases, bounds pending bodies/terminal IDs, and rejects text/known sensitive metadata.
Three outbox checks pass (9.83 s), including hard producer death after real HTTP
collector commit, replay with one alert, concurrent admission, expiry and auth failure.
Logical bounds do not constitute a disk quota. Next: server-side named identities.

Named access is implemented: private bootstrap, salted password hashes, revocable
eight-hour sessions, scoped viewer/reviewer/operator/admin roles, server-bound
actors, list/export/object-route scope checks, login throttling and password change.
Existing-account databases cannot fall back to local mode. Four auth/API checks
pass (14.13 s), the outbox/auth/API combination passes seven checks (31.13 s), and
the new Chromium role workflow passes (13.3 s). Dashboard production build passes.
An audit-action test label and a collapsed-details browser selector were corrected;
the role checks themselves held. Next: immutable detector profiles and calibration.

## Delivered runtime checkpoint (2026-10-08 UTC)

Latest steering: the user approved implementation of the plan. No participating
team is available; build independent mini projects to test GovernLoom instead.
The detailed plan is docs/PILOT_PLAN.md: real digit classification, historical
NOAA forecasting and model-backed RAG over actual project documentation. These
projects and the six-stage local sequence are implemented. Vision/forecasting/RAG
have actual-model evidence; launcher, bounded background delivery/heartbeats,
grouped incidents/actions, local escalation, backup/restore and conservative
retention have working checks. Final validation and focused commits are pushed.
A customer pilot is later, not an input blocking development.

Primary data sources, attribution and official local subscription execution docs
were checked. Optional scikit-learn 1.9.1/NumPy 2.5.3 and dependencies were installed
locally for feasibility preparation; core dependency files were not changed.
No new model inference, dataset download or service was started during planning.
That was a planning-only checkpoint; runtime code has since advanced below.

Implementation checkpoint: the vision mini service now trains a real 64-tree
digit classifier and connects through HTTP. Its 360 held-out cases produce
342 correct predictions, 18 errors, 69 review flags, 17 captured errors and one
confident error missed, at a calibration-selected confidence threshold 0.59375.
Two actual-model tests pass (12.86 seconds), including result withholding,
persisted review resolution, label feedback and actual service restart.
Forecasting now serves predictions and linked outcomes through the same HTTP
boundary, records investigations and supports an explicitly configured fallback.
Four example tests pass (20.21 seconds); CI uses a labeled synthetic forecast
fixture and never fetches remote data. The separate actual NOAA snapshot has SHA-256
c9a91a170d09d16afaaad56c4f383ed4fcb7fa0da967998694842d5c8168bcf3.
Direct model evaluation on its 48 observed 2021-2024 outcomes measures MAE
0.75654 ppm and RMSE 0.95067 ppm, versus seasonal-naive MAE 2.59771 ppm.
The frozen 2019-2020 calibration tolerance is 0.97433 ppm; 15 held-out errors
exceed it. These are revised-snapshot historical results, not live forecasting
or a historical data-vintage simulation. Raw snapshot and provenance stay in
ignored data/miniapps/. The RAG service now retrieves actual documentation and
uses the bounded opt-in subscription generator, with explicit post-generation
faults and tool denial before a write. Five example tests pass (24.79 seconds),
including an explicitly fake CI generator with real collector HTTP. A sandbox
temporary-directory permission failure was resolved by using a fresh ignored
workspace basetemp; it was not an application failure. The later launcher run
below records actual RAG generation. Software tests do not establish model quality.

Working continuation: the isolated launcher completed all 360 vision cases and
48 NOAA forecast/outcome pairs in data/testbed-2026-10-08-b/. Exactly 15 natural
forecast outcomes were flagged; deliberate offset and fallback passed. RAG
stopped before inference because the sandboxed CLI could not find its home/login
configuration. All owned services stopped; failed-run reports are retained.
A fresh authorized elevated run completed in data/testbed-2026-10-08-c/ with
exactly three completed local subscription requests. All 1,246 events were
accepted (vision 1,138; forecasting 99; RAG 9) and all owned services stopped.
Natural RAG responses: one answer about tool enforcement, one cautious partial
abstention about text retention, and one refusal to invent a medical approval.
Both post-generation faults were withheld; the unauthorized write was denied
before its marker file existed. Citation membership passed natural answers, but
does not establish claim support. The partial abstention exposes retrieval
coverage limits. An earlier launcher attribute mismatch was
fixed after vision completed; that capture is data/testbed-2026-10-08/.
Three focused application commits 007c99f, e6e6347, cc8fc12 are pushed. All GitHub
Actions jobs passed for cc8fc12 at
https://github.com/rahbarahsan/governloom/actions/runs/37714232976.
Background observation is implemented: bounded RAM queue,
exact-body retry, separate synchronous enforcement, loss counters and scoped
heartbeats. Six delivery tests pass (5.28 seconds), including a real collector
outage/restart, receipt loss without duplicate alerts and quiet batch cadence.
Launcher and reviewed actual-model evidence are committed in a3f669c. Six example
tests include a bounded launcher with no subscription calls/downloads and clean
shutdown. Delivery/incident docs, dashboard coverage and backup/retention/capacity
checks are complete. Incident
grouping, action acknowledgment/operator verification and local test-sink retry
checks pass; two initially incorrect audit-kind assertions were corrected to
the existing review_event audit store. No messages to real recipients were sent.

Final local validation: **67 tests pass (86.34 seconds)**, four browser workflows
pass (26.9 seconds), TypeScript/production bundle, compilation and pip check pass.
Browser checks cover visible cadence counters, incident ownership, app action
acknowledgment and reload. A sandbox Vite resolution failure was rerun with
required access; its own leftover collector was verified/stopped. A selector
matching both a paragraph and hidden option was corrected before successful rerun.
Steady local delivery: 100/100 accepted at 100 attempts/second, enqueue p95 0.449 ms.
Burst: 16 accepted/984 explicitly dropped, max queue 16 and 7,936 serialized bytes;
all 116 accepted events present, one grouped incident/cooldown escalation.
Live-WAL backup tests pass; actual testbed restore preserved 1,246 events and 130
entities, integrity ok. Retention preview on that DB found zero eligible old
observations and applied no deletion. Tests execute pruning only in disposable DBs.
Full reports: docs/TESTBED_EVIDENCE.md, docs/experiments/testbed-2026-10-08.json,
docs/experiments/capacity-2026-10-08.json; integration docs: RUNTIME_DELIVERY.md;
operations: PILOT_OPERATIONS.md. Raw captures/backups remain ignored in data/.
The updated 0.2 wheel builds (57,297 bytes), and its installed SDK, operations
and API import from an isolated target directory without model dependencies.
An initial non-isolated build lacked setuptools; normal isolated build succeeded.
Packaging smoke is now part of Python 3.11/3.13 CI. Next work after delivery:
metadata-only durable outbox with explicit text coverage gaps, authenticated
operator roles, domain-calibrated detectors, then a real customer pilot if one
becomes available. No deployment, paid API calls or external recipients.

Delivered checkpoints: a3f669c (launcher/actual-model evidence), ba2ec7d
(bounded delivery/incident integration), 70c5404 (operations/capacity/release docs).
All are pushed to origin/main. GitHub Actions for code head
70c54049ec68851f972bc8c153599521b3fa94d5 completed successfully: Python 3.11,
Python 3.13, optional actual-model integration and Chromium jobs, including
wheel build/install/import smoke. Run:
https://github.com/rahbarahsan/governloom/actions/runs/37717404315.
Process and listener checks confirm no project servers and no listeners on
8000/5173. The only untracked file remains the user's original
governloom-build-brief.md; it was not modified or committed. This documentation
checkpoint records delivery without changing the validated code.

This section supersedes the earlier claim-evaluation roadmap below. The user
clarified the product: a developer connects an existing AI system through a hook;
GovernLoom monitors production signals, flags risks and supports mitigation.
There is no organization-wide inventory requirement. Vision, RAG, forecasting,
classification and custom systems must share a provider-independent contract.

Implemented: authenticated HTTP event ingestion, Python callable/tool hooks,
immutable configurable runtime policies, transient text scanning, scoped revocable
keys, delayed forecast outcome linkage, rolling numeric signals, durable alerts,
operator ownership/disposition audit, and a live dashboard. The legacy evaluation
workbench remains available. No model provider is needed to monitor a customer's
own running model, and no synthetic target is used in the monitoring product flow.

Earlier foundation checks: 49 backend tests pass (20.08 seconds), including 15 runtime checks
and a real TCP collector process. Coverage includes
vision output withholding, tool blocking before execution, delayed forecast
error, idempotent concurrent replays, privacy, auth, rate limits, and collector
redirect rejection. All four real-browser workflows pass (26.3 seconds), including
policy/key setup, live vision risk evidence, operator mitigation, reload and key
revocation. Earlier navigation assumptions and a missing operator after reload
were fixed in the browser tests. TypeScript/production bundle, compilation and
dependency check pass. The v0.2 wheel builds and public hook/schema/version
imports pass from its installation in the separate clean environment. Research,
runtime integration docs and roadmap now reflect the user's actual product scope.
Checkpoint `4f9fd5a` contains the runtime engine/hook; `cd70907` contains the
dashboard/browser integration; `59351be` contains product research, integration
docs and the revised roadmap. All three are pushed to origin/main. Local
validation and packaging review are complete. Process/listener checks confirm
zero project servers and no listeners on ports 8000/5173. The original brief is
the only untracked file. Remote Python 3.11/3.13 and Chromium checks all passed
for `59351beaf984ce96f820e5d13ad366139b9531e9` in
https://github.com/rahbarahsan/governloom/actions/runs/37629734622.
The v0.2 runtime foundation is delivered. A final documentation checkpoint records
the successful remote result without changing runtime code. Next executable
work: the real-system pilot/reliability milestone in docs/ROADMAP.md; choose
metrics with a consenting team and measure latency, coverage and useful alerts.
Do not claim production scale, risk-detection accuracy, comprehensive PII detection
or compliance certification. Once shipped, follow docs/ROADMAP.md: connect a real
customer system and improve reliable telemetry/incident operations.

Original untracked `governloom-build-brief.md` remains untouched. No deployment
or paid inference is authorized. No manual server should remain after delivery.

## Specification and state

The supplied specification is `governloom-build-brief.md` (no BUILD_BRIEF.md exists).
No repository or ancestor AGENTS.md was found. The README is expanded; the existing
Apache-2.0 license and untracked brief are preserved. Local ChatGPT-subscription
inference is now explicitly authorized; no deployment or paid API calls are authorized.

## Completed

- Repository and toolchain inspected: Python 3.13.1, Node 22.14.0, npm 11.6.2.
- Core schemas, immutable versioned source import, validated JSONL case/trace import,
  audited optimistic review, frozen datasets, metric prerequisites and scoring implemented.
- Original 16-document fictional policy corpus and 40 scenario fixtures implemented;
  20 calibration and 20 held-out cases grouped by topic. No independent human review claimed.
- CLI vertical slice completed; all five fault modes exercised with clean baseline.
- Persistent atomic worker with cancellation, leases, owner fencing and unique result
  finalization implemented. API added for the full workflow, evidence and JSONL export.
- Git checkpoint `f3a5b2c`: core, API and worker milestone committed; supplied
  untracked brief left untouched.
- Git checkpoint `8477c71`: review/recovery hardening, fixed fixtures and provider tests.
- Git checkpoint `0806e5a`: dashboard implementation.
- Git checkpoint `0257121`: real browser workflows and screenshots.
- Git checkpoint `d08086e`: Python and browser CI definitions.
- Git checkpoint `ab79300`: release documentation and measured delivery evidence.
- React/TypeScript dashboard implemented: applications/imports, review/edit/audit,
  publication, bounded jobs, per-dimension coverage, evidence and comparison.
- Fixed 40-case JSONL suite shipped separately from runtime generation.
- Paid provider routes/adapters remain unavailable. Budgeted interfaces tested with
  a deterministic no-network fake, including evidence validation and failures.
- Actual worker kill/restart and stale-owner fencing checks pass.
- Locked setup, Python wheel, CI definitions, README, schema/measurement docs,
  attribution, screenshots and machine-readable release evidence completed.

## Validation

- `git status --short`: initial state contained only the untracked build brief.
- `python --version; node --version; npm --version`: passed.
- `python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e '.[dev]'`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: **15 passed** (core milestone).
- API milestone: **17 passed**, with one upstream Starlette/httpx deprecation warning.
- `npm install` in `web`: passed, 0 vulnerabilities reported.
- `npm run build` in `web`: TypeScript and production bundle passed; removed an
  empty CSS import that caused a warning on the initial build.
- `npx playwright install chromium`: passed.
- Final `.\.venv\Scripts\python.exe -m pytest -q`: **27 passed** in 17.03 seconds;
  one upstream Starlette/httpx deprecation warning remains.
- Final `npm run test:e2e` in `web`: **3 passed** in 22.4 seconds. Real API and
  separate worker: manual imports/telemetry/download, demo review/run/comparison/
  persistence, UTF-8 import and mobile empty states. Failures found earlier were fixed.
- Final `npm run build`: passed. API static index/JavaScript asset/health all returned 200.
- `.\.venv\Scripts\python.exe -m pip check`: passed, also in the fresh install.
- `python -m venv data\clean-env`, install `requirements.lock`, install editable
  package with `--no-deps`, CLI demo against `data/clean-setup.db`: all passed.
- `.\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir data\dist`:
  passed. Wheel contains core, 16 policies, 40 fixtures and the root license.
- Installed the built wheel into `data/clean-env` and ran six more complete
  demo runs against `data/wheel-demo.db`; comparison matched 20 cases.
- `.\.venv\Scripts\python.exe scripts\verify_demo.py`: six runs passed;
  per-fault results and denominators saved in `docs/release-evidence.json`.
- `.\.venv\Scripts\python.exe -m compileall -q src scripts` and `git diff --check`: passed.
- Post-release GIF capture: `node web/scripts/capture-demo.mjs` passed against an
  isolated real API/worker/browser. Eleven states encoded into a looping 1280 × 900
  GIF: 23.2 seconds, 489,817 bytes. Source review, approvals, publication, both runs,
  comparison and highlighted evidence assertions passed; no browser errors.
- Optional media setup `pip install -r scripts/requirements-media.txt`,
  `node --check web/scripts/capture-demo.mjs`, encoder compilation, decoded-frame/
  timing/size validation and `git diff --check` passed. Media dependency is separate
  from runtime requirements. Review/evidence capture frames inspected visually.
- First GitHub Actions run **passed** on Ubuntu: Python 3.11 core, Python 3.13
  core, Chromium browser workflow and artifact upload. Verified commit `ab79300`;
  run https://github.com/rahbarahsan/governloom/actions/runs/37562245561.
- Six focused delivery commits pushed to `origin/main`, followed by a documentation
  checkpoint for the passing remote CI and README badge. No history rewritten.
- `.\.venv\Scripts\python.exe -m governloom.cli --db sqlite:///data/vertical-slice.db demo`:
  six completed runs, 20 cases each. Findings: clean 0, irrelevant retrieval 20,
  outdated source 20, unsupported statement 0 (documented blind spot), invalid
  citation 10, timeout 20. Compatible comparison on 20 matched cases passed.

## Next executable step

2026-10-07: after the user challenged the synthetic demo's realism, they authorized
using their existing OpenAI subscription instead of sharing an API key. The
installed Codex CLI reports ChatGPT authentication. Added an opt-in local
subscription transport and `scripts/run_subscription_eval.py`: four natural
questions using two existing policies, observed trace import/worker evaluation,
two explicitly synthetic unsupported additions, and four separate claim judgments.
The answer prompt excludes reference answers and expected labels. Captures keep
model selector, CLI version, prompt/rubric versions, source/dataset hashes,
exact responses, evidence and usage. No auth token file is read/copied/published.

The first attempt rejected unsupported built-in provider retry configuration
before inference. Removed that configuration and preserved the failed capture
in ignored `data/subscription-2026-10-07/`. A fresh invocation completed all
eight real turns in `data/subscription-2026-10-07-b/`; the isolated database is
`workbench.db`. Published the non-secret report in
`docs/experiments/subscription-2026-10-07.json`. Reproduce with:

`.\.venv\Scripts\python.exe scripts/run_subscription_eval.py --allow-subscription --model gpt-6.1-sol --max-requests 8 --timeout-seconds 180 --output data/new-subscription-capture`

Results: 4/4 response behaviors match authored fixtures; both paraphrased answers
fail literal agreement while citation checks pass. Separate real judge turns
mark both original factual claims supported and both appended claims unsupported,
with exact source passage validation. Existing deterministic checks do not
distinguish the additions. Comparison is compatible on four matched cases.
Human calibration, immutable backend model snapshot and subscription monetary
cost remain unavailable. Fictional corpus and four exploratory cases do not
establish real-world evaluation reliability. Dashboard semantic metric stays
unavailable; estimates remain in the report. See `docs/SUBSCRIPTION_EVAL.md`.

New tests cover API-key rejection/removal, request limits, durable errors,
deadline termination, attempted tool use, forged judge quotes, and real-workflow
trace import with a no-network fake. **34 backend tests pass** (23.19 seconds);
web production build, compilation, pip check and diff check pass. **3 browser
workflows pass** (29.3 seconds). Script starts no servers; normal API/worker/tests make no
subscription calls. Transport reservations count CLI invocations, not internal
HTTP retries; the CLI can retry transport within the fixed deadline.

Checkpoint `67ae6b9` commits capture transport, experiment script and tests.
The recorded report was independently re-read to verify eight completed turns,
both completed four-case runs, frozen dataset checksum and exact judge evidence.
Test-created screenshot changes were discarded. Process and listener checks
confirm no remaining capture, API, worker or dashboard server. Documentation
and the non-secret recorded experiment form a separate delivery checkpoint.

Next work: blinded independent label export/import and adjudication, then
dashboard claim-evidence integration with explicit uncalibrated states and
a larger second application. Do not treat model estimates as human labels.

Post-release presentation: a real 23.2-second demo GIF (11 frames, 489,817 bytes)
is added to the README with a still preview and reproducible capture scripts.
Capture verifies the review/publish/clean/faulty/compare/evidence workflow and
decoded animation frames. It uses an isolated database and no paid provider.

The recommended v0.2 scope is now recorded in `docs/ROADMAP.md`: claim-level
grounding, independently reviewed calibration, a second application/corpus,
and a local launcher/finding filters. The subscription experiment above is
the first implemented slice; the remaining scope is proposed. Continue with
blinded label export/import and a calibration report; no real-model quality
claim without actual independent labels.

First-release delivery is complete. Follow README setup to run it. If changing
code, run the backend suite, web build, and browser suite before updating evidence:
`.\.venv\Scripts\python.exe -m pytest -q`, `npm --prefix web run build`,
`npm --prefix web run test:e2e`. `docs/VALIDATION.md` records exact release results.

The next optional expansion is independent review/calibration and a second
application/corpus. It requires new evidence and, for paid providers, explicit
configuration and spending authorization. No automatic restart is configured.

The user authorized pushing the focused delivery commits to `origin/main`.
Use `git status -sb` to inspect remote synchronization if resuming. No force-push,
deployment, or paid API provider work is authorized. Local subscription inference
is authorized as described above. The supplied brief remains an
untracked user file and is deliberately excluded from delivery commits.

## Current blockers and scope limits

None for the completed local three-application delivery sequence. No participating
team is required to reproduce it. Persistent event delivery, authenticated roles,
customer-specific retention and domain calibration remain future work; the
current checkpoint establishes measured integration behavior, not a production
SLA or regulatory certification. Independent human calibration is unavailable.
The legacy citation-membership/extra-claim blind spot is still explicit. No
paid API usage, external recipients or deployment occurred.
