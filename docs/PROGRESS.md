# Release progress

## Specification and state

The supplied specification is `governloom-build-brief.md` (no BUILD_BRIEF.md exists).
No repository or ancestor AGENTS.md was found. Existing README, Apache-2.0
license, and untracked brief are preserved. No deployment or paid calls authorized.

## Completed

- Repository and toolchain inspected: Python 3.13.1, Node 22.14.0, npm 11.6.2.
- Core schemas, immutable versioned source import, validated JSONL case/trace import,
  audited optimistic review, frozen datasets, metric prerequisites and scoring implemented.
- Original 16-document fictional policy corpus and 40 scenario fixtures implemented;
  20 calibration and 20 held-out cases grouped by topic. No independent human review claimed.
- CLI vertical slice completed; all five fault modes exercised with clean baseline.
- Persistent atomic worker with cancellation, leases, owner fencing and unique result
  finalization implemented. API added for the full workflow, evidence and JSONL export.

## Validation

- `git status --short`: initial state contained only the untracked build brief.
- `python --version; node --version; npm --version`: passed.
- `python -m venv .venv; .\\.venv\\Scripts\\python.exe -m pip install -e '.[dev]'`: passed.
- `.\\.venv\\Scripts\\python.exe -m pytest -q`: **15 passed** (core milestone).
- `.\\.venv\\Scripts\\python.exe -m governloom.cli --db sqlite:///data/vertical-slice.db demo`:
  six completed runs, 20 cases each. Findings: clean 0, irrelevant retrieval 20,
  outdated source 20, unsupported statement 0 (documented blind spot), invalid
  citation 10, timeout 20. Compatible comparison on 20 matched cases passed.

## Next executable step

Run API tests, then build the React/TypeScript dashboard and browser workflow checks.
Complete packaging, README, schema/measurement docs, CI, and recorded release evidence.

## Blockers

None identified. Network installation may require sandbox escalation.
