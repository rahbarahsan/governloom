# Contributing

Start with [the quickstart](docs/QUICKSTART.md), [decisions](docs/DECISIONS.md) and
[roadmap](docs/ROADMAP.md). Use issue templates to describe concrete developer
problems, reproduction, versions and sanitized evidence. Never attach credentials,
private prompts, raw databases or customer data. For vulnerabilities use
[SECURITY.md](SECURITY.md).

Discuss substantial feature scope in an issue first; small fixes can go directly
to a pull request. Keep changes focused and explain their observable behavior and
validation. Preserve immutable evidence, existing event semantics and explicit
missing-data states. Model-quality claims need grouped held-out measurements with
misses, false positives and provenance; software fixtures do not establish quality.

## Checks

Prepare Python/dashboard dependencies with the quickstart. From the root:

```sh
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m scripts.export_contracts --check
npm --prefix web run build
npm --prefix web exec -- playwright install chromium
npm --prefix web run test:e2e
npm --prefix sdks/typescript ci
npm --prefix sdks/typescript run build
npm --prefix sdks/typescript test
```

On macOS/Linux use `.venv/bin/python`. Core checks support Python 3.11/3.13;
actual-model examples use Python 3.13 and optional pinned model dependencies.
Browser checks own local services; ports 8000/5173 must be free. The Node SDK's
Python integration requires its build and Node; a dedicated CI job supplies both.
CI never calls a model provider or subscription login.

The distribution job installs a fresh wheel into a separate environment and
runs an actual standalone model consumer, then builds the container and checks
named access, built-dashboard serving, deadlines and exact replay across restart.
Run `python scripts/check_onboarding.py --directory data/onboarding-check` in a
new directory; it owns and stops its collector. See [container checks](docs/CONTAINER.md).
Six CI jobs cover the two core Python versions, browser, examples, SDK and distribution.
The examples job also derives a policy from actual digit-model traces and verifies
an incident without a prewritten policy. Discovery's browser workflow covers import,
owner correction, calibration and observation activation. See [discovery](docs/DISCOVERY.md).

Regenerate changed event models with `python -m scripts.export_contracts` and
review compatibility. Add meaningful boundary checks; documentation edits do not
need implementation-mirroring tests. Keep raw artifacts in ignored `data/`.
Contributions use [Apache-2.0](LICENSE); retain third-party licenses/attribution.
