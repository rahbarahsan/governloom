# Release 0.1 verification

Local execution on 2026-10-06: Windows, Python 3.13.1, Node 22.14.0, npm 11.6.2,
Playwright Chromium. These are actual local results. The included GitHub Actions
matrix has not been executed remotely; Linux/Python 3.11 is not claimed as tested.

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
