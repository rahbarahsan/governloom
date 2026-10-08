# Release verification

## Actual-model/private-pilot checkpoint (2026-10-08 UTC)

67 backend/example tests pass (86.34 seconds), including actual-model services,
bounded launcher cleanup, background delivery/heartbeat, real outage/restart,
lost receipts, incident/actions, local sink retry and live-WAL backup/restore.
Four Chromium workflows pass (26.9 seconds), including incident ownership,
delivery coverage, action acknowledgment and reload. Production bundle,
compilation, dependency and diff checks pass. The rebuilt wheel's installed SDK,
operations and API import without optional model dependencies; CI also checks it.

Three real subscription requests, 360 held-out digit cases and 48 observed
historical forecast outcomes completed through HTTP: 1,246 events accepted,
with faults/warmups outside independent quality denominators. See
[actual-model evidence](TESTBED_EVIDENCE.md) and the
[reviewed report](experiments/testbed-2026-10-08.json). Model misses and retrieval
limitations are preserved; no independent human calibration is claimed.
[Delivery stress evidence](experiments/capacity-2026-10-08.json) records the preset
enqueue gate, bounded saturation and explicit losses. [Operations](PILOT_OPERATIONS.md)
records actual restore counts/checksum and conservative retention limits.

Sandbox home/temp/Vite access failures were rerun with appropriate access or
workspace paths. Application failures (launcher field mismatch and ambiguous
browser selector) were corrected before passing validation. CI uses no remote
dataset fetch, subscription inference or secrets. No deployment or external
recipient notifications occurred. Earlier validation below is historical.

## Runtime foundation v0.2 (2026-10-07)

- Complete backend suite: **49 passed**, 20.08 seconds, Python 3.13.1 on Windows.
  Fifteen new runtime checks cover scoped/revoked credentials, private admin auth,
  transient text privacy, bad payloads, duplicate/concurrent replays, rate limits,
  preserved policy versions, missing evidence, numeric boundaries, classification,
  vision, RAG signals, delayed forecast outcomes, mean-window warmup/model isolation,
  target errors, collector outages and input/tool/output enforcement.
- The HTTP integration starts an actual Uvicorn subprocess on an isolated port
  and database, calls the public Python hook, verifies output withholding/tool
  denial before execution, links forecast outcomes, and records disposition.
  A separate HTTP server verifies that collector redirects are rejected.
- **4 browser workflows passed**, 26.3 seconds. New workflow configures a vision
  policy and key, sends an event, inspects evidence, records mitigation, reloads
  and revokes the key. The three earlier evaluation workflows still pass.
- TypeScript/Vite production build, compileall and pip check pass.
- v0.2 wheel built and installed in the separate clean environment; public hook,
  event schema and version imports pass from the installed package. A first
  no-build-isolation attempt found no local setuptools; normal isolated build
  succeeded. No runtime dependency was added for the hook.
- These checks establish software integration behavior using test callables and
  fixtures, not real-world model quality, detector precision/recall, production
  availability or a customer deployment. No paid inference was performed.
- [GitHub Actions run 37629734622](https://github.com/rahbarahsan/governloom/actions/runs/37629734622)
  passed for commit `59351beaf984ce96f820e5d13ad366139b9531e9`: Ubuntu Python
  3.11/3.13 suites and dependency checks, TypeScript/Vite build, all Chromium
  workflows and artifact upload. Local server/listener audit found zero remaining
  project servers and no listeners on 8000/5173. Only the original untracked
  user brief remains outside the delivered commits.

## Original v0.1 verification

Local execution on 2026-10-06: Windows, Python 3.13.1, Node 22.14.0, npm 11.6.2,
Playwright Chromium. These are actual local results.

The first [GitHub Actions run](https://github.com/rahbarahsan/governloom/actions/runs/37562245561)
also completed successfully on Ubuntu: Python 3.11 core, Python 3.13 core, and the
Chromium/browser build and workflow job, including evidence artifact upload.
It verified code commit `ab793004bf854dd6d1cf9e969ec7b8cc560cab61`. That remote
result applies to that commit; later local checks are recorded separately below.

## Post-release real-model slice (2026-10-07)

- `.\.venv\Scripts\python.exe -m pytest -q`: **34 passed**, 23.19 seconds.
  Seven new checks cover subscription-only auth, bounded capture, failure/deadline
  handling, rejected tool use, forged evidence and imported real-model workflow
  integration using a no-network fake. The existing upstream deprecation remains.
- `npm --prefix web run build`: TypeScript and Vite build passed.
- `npm --prefix web run test:e2e`: **3 passed**, 29.3 seconds. Generated screenshot
  changes were discarded; the committed presentation images remain the v0.1 capture.
- `.\.venv\Scripts\python.exe -m compileall -q src scripts`,
  `.\.venv\Scripts\python.exe -m pip check`, `git diff --check`: passed.
- Live local command:
  `.\.venv\Scripts\python.exe scripts/run_subscription_eval.py --allow-subscription --model gpt-6.1-sol --max-requests 8 --timeout-seconds 180 --output data/subscription-2026-10-07-b`:
  **8 real model turns completed**, two imported four-case runs completed,
  comparison compatible on four matched cases, judge quotes/source positions valid.
  No API key supplied; installed CLI authenticated with ChatGPT.
- The first capture failed before inference because the CLI rejected built-in
  provider override settings. Removed those settings and used a fresh output
  directory; no failed result was relabeled as successful.
- Model-selector and CLI provenance, exact prompts/responses, observed usage,
  dataset and source hashes, limitations and findings are recorded in
  [the real-model experiment](SUBSCRIPTION_EVAL.md). Human calibration remains
  unavailable; this is an exploratory integration result, not a quality benchmark.
- No capture/browser API, worker or dashboard servers remain running after checks.

## Checks executed

Commands use PowerShell from the repository root unless a directory is noted.

| Command / check | Actual result |
| --- | --- |
| `python -m venv .venv` and `.\.venv\Scripts\python.exe -m pip install -e '.[dev]'` | Setup passed |
| `.\.venv\Scripts\python.exe -m pytest -q` | **27 passed**, 17.03 seconds |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| `.\.venv\Scripts\python.exe -m compileall -q src scripts` | Passed |
| `npm install` in `web` | Installed; npm reported 0 vulnerabilities |
| `npm run build` in `web` | TypeScript and Vite production build passed |
| `npx playwright install chromium` in `web` | Installed successfully |
| `npm run test:e2e` in `web` | **3 passed**, 22.4 seconds |
| `.\.venv\Scripts\python.exe scripts\verify_demo.py` | Six completed 20-case runs; matched comparisons passed |
| `git diff --check` | Passed; only local Git LF/CRLF notices |
| Built dashboard using FastAPI TestClient | `/`, JavaScript asset, `/api/health` all 200 |
| `.\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir data\dist` | Wheel built successfully |
| Wheel archive inspection | Core, 16 policy documents, 40 fixed cases, root license present |

Backend tests cover prerequisites, unavailable telemetry, numeric values,
denominators, source ranges/hashes, immutable evidence, audited edits,
rejection/publication, grouped splits, atomic claims, cancellation, stale owner
fencing, comparisons, trace import and disabled/budgeted provider boundaries.

Recovery is tested both through persisted lease state and an actual subprocess:
kill the worker after at least three finalized cases, allow its test lease to
expire, start another process, preserve existing results, and finalize exactly
20 unique case results. The production lease is 30 seconds; the process test uses
a 1-second lease and a slow local target. No paid target is called.

Browser checks use a real API and separate worker process:

1. Manual case/trace file import, named review, publication, imported-target
   evaluation, unavailable latency, and trace download.
2. Bundled corpus, edited review, bulk review, frozen publication, clean/faulty
   execution, source highlighting, compatible comparison and persisted reload.
3. Application creation, UTF-8 Markdown upload, unsupported generator input,
   empty states and 390-pixel mobile layout without horizontal overflow.

Screenshots from the passing workflow are preserved as
[findings](screenshots/findings.png), [runs](screenshots/runs.png), and
[mobile](screenshots/mobile.png). The mobile and run views were inspected locally.

## Fresh environment

These documented install steps were repeated in an isolated environment:

```powershell
python -m venv data\clean-env
.\data\clean-env\Scripts\python.exe -m pip install -r requirements.lock
.\data\clean-env\Scripts\python.exe -m pip install --no-deps -e ".[dev]"
.\data\clean-env\Scripts\python.exe -m governloom.cli --db sqlite:///data/clean-setup.db demo
.\data\clean-env\Scripts\python.exe -m pip check
```

All succeeded, including six completed runs and a compatible 20-case comparison.
The Python wheel was also installed into this environment with `--no-deps
--force-reinstall` and the CLI demo repeated against a separate `wheel-demo.db`.
The wheel carries the corpus/fixtures; the web build remains in the checkout.

## Known-fault results

[Machine-readable evidence](release-evidence.json) records the fixture checksum,
dataset checksum, evaluator/target versions, sample counts, result denominators
and confusion counts. Labels are repository-authored template fixtures with
automated source verification, not independent human validation.

| Target | Selected cases | Known positive cases | Detected positives | False positives | Missed positives |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clean | 20 | 0 | 0 | 0 | 0 |
| Irrelevant retrieval | 20 | 20 | 20 | 0 | 0 |
| Outdated source | 20 | 20 | 20 | 0 | 0 |
| Unsupported statement | 20 | 10 | 0 | 0 | 10 |
| Invalid citation | 20 | 10 | 10 | 0 | 0 |
| Timeout | 20 | 20 | 20 | 0 | 0 |

Citation and unsupported-statement faults alter the ten answer cases; the other
ten retain clean clarification/abstention outputs. Literal checks miss all ten
unsupported additions. Semantic grounding is insufficient evidence on all 20
cases in every run. Token usage/cost are likewise unavailable without telemetry.

These synthetic results check the engineering workflow and reveal its blind
spots. They are not accuracy estimates for real models or arbitrary corpora.
No independent model calibration, public dataset study or deployment occurred.

## Failures fixed during delivery

An empty CSS import caused an initial build warning and was removed. The browser
harness initially used a Windows-incompatible executable path; it now quotes an
absolute path. Explicit accessible names fixed the target selector. Additional
checks found a case-sensitive assertion and an unreachable demo loader after
application creation; both were corrected and the three workflows rerun.
Fast run completion now refreshes the selected run, Unicode references use
code-point slicing, range bounds are validated, null edits can clear labels,
and concurrent publication assigns unique dataset versions.

The backend emits one upstream Starlette/httpx deprecation warning. Playwright
emits environment color warnings. Neither failed the recorded checks; no passing
claim hides an unresolved application or test failure.

## Post-release README GIF

`node web/scripts/capture-demo.mjs` launched an isolated API, worker and Chromium,
exercised review/publication, clean and invalid-citation runs, comparison and
highlighted evidence, then encoded eleven real viewport captures. All workflow
assertions passed and no browser errors were observed. The resulting GIF is
1280 × 900, loops for 23.2 seconds, and is 489,817 bytes. The encoder decoded all
frames to verify compositing, timing and agreement with captured content.

The review and evidence frames were inspected visually. Node syntax, Python
compilation, optional Pillow installation, dependency consistency and Git whitespace
checks passed. Runtime code was unchanged, so the backend/browser suites were not
repeated solely for this documentation media update. Reproduction details and a
static alternative are in [media instructions](media/README.md).
