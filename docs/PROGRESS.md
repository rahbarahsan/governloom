# Release progress

## Specification and state

The supplied specification is `governloom-build-brief.md` (no BUILD_BRIEF.md exists).
No repository or ancestor AGENTS.md was found. The README is expanded; the existing
Apache-2.0 license and untracked brief are preserved. No deployment or paid calls authorized.

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

First-release delivery is complete. Follow README setup to run it. If changing
code, run the backend suite, web build, and browser suite before updating evidence:
`.\.venv\Scripts\python.exe -m pytest -q`, `npm --prefix web run build`,
`npm --prefix web run test:e2e`. `docs/VALIDATION.md` records exact release results.

The next optional expansion is independent review/calibration and a second
application/corpus. It requires new evidence and, for paid providers, explicit
configuration and spending authorization. No automatic restart is configured.

The user authorized pushing the focused delivery commits to `origin/main`.
Use `git status -sb` to inspect remote synchronization if resuming. No force-push,
deployment, or paid provider work is authorized. The supplied brief remains an
untracked user file and is deliberately excluded from delivery commits.

## Blockers

None for the first release. No paid provider, independent human label validation,
real-model quality study or deployment is claimed. The unsupported
extra-claim blind spot is visible in the dashboard and measured in release evidence.
