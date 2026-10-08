# Release progress

## Current direction: runtime governance (2026-10-07)

Latest steering: the user approved implementation of the plan. No participating
team is available; build independent mini projects to test GovernLoom instead.
The detailed plan is docs/PILOT_PLAN.md: real digit classification, historical
NOAA forecasting and model-backed RAG over actual project documentation. These
projects are now being implemented. First executable implementation step:
examples/vision/ with a trained model, held-out inputs, public HTTP hook and a
persisted review/withhold action; then forecasting, RAG and the isolated launcher.
Reliability and incident work follow the sequence and acceptance gates in that
plan. A customer pilot is a later milestone, not an input blocking development.

Primary data sources, attribution and official local subscription execution docs
were checked. Optional scikit-learn 1.9.1/NumPy 2.5.3 and dependencies were installed
locally for feasibility preparation; core dependency files were not changed.
No new model inference, dataset download or service was started during planning.
Existing runtime code is unchanged; earlier v0.2 validation still applies to it.

Implementation checkpoint: the vision mini service now trains a real 64-tree
digit classifier and connects through HTTP. Its 360 held-out cases produce
342 correct predictions, 18 errors, 69 review flags, 17 captured errors and one
confident error missed, at a calibration-selected confidence threshold 0.59375.
Two actual-model tests pass (12.86 seconds), including result withholding,
persisted review resolution, label feedback and actual service restart.
Forecasting is being implemented against a downloaded NOAA snapshot with SHA-256
c9a91a170d09d16afaaad56c4f383ed4fcb7fa0da967998694842d5c8168bcf3.
Next: forecasting HTTP/outcome checks, RAG service, then isolated launcher and
measured evidence. No new inference-quality claim is implied by software tests.

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

Current checks: 49 backend tests pass (20.08 seconds), including 15 runtime checks
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

## Blockers

None for the first release or the local real-inference experiment. Independent
human reviewers, dashboard claim-evidence integration, and a larger second
application are outstanding. No paid API usage, human calibration, real-model
quality study or deployment is claimed. The unsupported extra-claim blind spot
remains visible in the dashboard and measured in release evidence; the new
report records separate uncalibrated judge estimates.
