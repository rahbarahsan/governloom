# Subscription-backed real-model experiment

This is the first real-inference slice following v0.1. It runs a small support
assistant using the local Codex CLI's existing ChatGPT login, then evaluates
the captured responses through GovernLoom's ordinary trace-import and worker
path. An API key is not needed. Subscription allowance is consumed.

## Reproduce

Install the repository dependencies and the Codex CLI, sign in with ChatGPT,
and confirm `codex login status`. From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/run_subscription_eval.py --allow-subscription --model gpt-6.1-sol --max-requests 8 --timeout-seconds 180 --output data/new-subscription-capture
```

Choose a fresh output directory and a model selector available to your account.
On macOS/Linux use `.venv/bin/python`. This path is for trusted local execution;
it is not exposed through the API or configured in public CI. The installed
CLI retains and manages authentication. The application never reads, copies,
or publishes the authentication token file.

The CLI supports subscription authentication and non-interactive structured
output with saved authentication:
[OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth),
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

## What happens

1. Import two original Northstar policy documents and four exploratory cases:
   invoice timing, security-key reset, an undocumented payment exception, and
   an assumed unlimited-credit entitlement. Record source hashes and references.
   Accept repository fixtures with a clearly scripted actor and freeze them.
2. Invoke a fresh real model turn for each question. Pass all two documents as
   context; this deliberately simple context selection is recorded in retrieval
   telemetry. No reference answer, expected behavior, or fixture label enters
   the answer prompt. Preserve wording, behavior, citations, CLI usage and wall time.
3. Import observed traces and execute a four-case evaluation with the worker.
4. Add a free-lifetime-membership statement to the two answerable responses.
   These are synthetic string edits after inference, not naturally observed
   hallucinations. Clear their latency/usage/error telemetry instead of claiming
   that a second model call produced them. Import and evaluate this control batch.
5. In four additional separate turns, request claim judgments on the two
   original answers and their edited counterparts. The judge sees only answers,
   documents, and a fixed rubric. Validate quoted evidence against exact frozen
   passages and hashes. Keep raw judge output beside validated source positions.

The model selector, prompt/rubric versions, CLI version, exact requests, raw
responses, usage and dataset checksum are preserved in `report.json`. Local
per-request diagnostics remain in the ignored `data/` directory. The record
does not claim an immutable model snapshot: the CLI exposes the requested
selector, and the backend behind that selector can change.

## Bounds and failure behavior

- Explicit `--allow-subscription`, model and invocation limit are mandatory.
  This experiment needs eight turns; a session can allow at most twenty.
- Existing API-key login is rejected. API-key environment overrides and Codex
  access-token overrides are removed for the child process. Authentication is
  checked using the CLI status command, without exposing credentials.
- User configuration is omitted for inference; the CLI uses a read-only
  workspace, the shell tool is disabled, and captured tool activity is rejected.
  Questions and documents are explicitly treated as data.
- Input is bounded to 32 KB, each turn has a 1–300-second deadline (180 by default),
  and the script makes no automatic retries. A failed invocation consumes its
  reservation. The CLI can manage transport retries inside that deadline;
  the limit counts CLI invocations rather than HTTP requests.
- Timeout/interruption kills the directly launched native inference process.
  A partial report and request record preserve errors; failures are never passes.
  Existing capture directories cannot be overwritten. Normal tests use a fake
  transport and never consume subscription allowance.

## Interpretation

The recorded 2026-10-07 experiment completed eight real turns using model selector
`gpt-6.1-sol` and `codex-cli 0.160.1`. Full prompts, answers, validated judge
evidence and evaluation results are in
[the recorded experiment](experiments/subscription-2026-10-07.json).

| Observation | Recorded result |
| --- | --- |
| Expected answer / abstain / clarify behavior | 4 of 4 matched repository fixture expectations |
| Literal reference agreement | Both answerable responses failed the substring check; both were paraphrases |
| Citation existence and expected document consistency | Both answerable responses passed |
| Exploratory judge on original answers | Both factual answer claims were marked supported with valid source quotations |
| Exploratory judge on synthetic additions | Both appended free-membership claims were marked unsupported |
| Retrieval precision with both documents included | 0.5 per case under the fixture's single relevant-document label |
| Observed CLI wall time | 4.46–6.44 seconds for answer turns; all exceed the default 1-second threshold |
| Imported run comparison | Compatible, four matched cases |
| Human calibration / monetary cost | Unavailable |

The existing checks did not distinguish either unsupported addition: literal
agreement was already failing on the original paraphrases, while citation checks
continued to pass. The separate judge estimates show a promising result on two
deliberately easy controls, not an accuracy benchmark. Relevance labels and the
default latency threshold are fixture/development assumptions, not validated
production criteria.

This proves that actual LLM answers can enter the workbench and be checked.
It also lets us observe whether a real judge identifies a particular unsupported
addition. Exact quotation validation proves that a passage exists; it does not
prove that the judge's reasoning is correct or that every factual claim was
extracted. A model judging outputs from the same model family is not independent
human validation.

The fixture expectations have repository-authored provenance. All four cases
are exploratory; there is no held-out quality study or independent review.
Claim judgments remain a report artifact. Dashboard `semantic_grounding`
remains unavailable until judge integration and calibration are implemented.
CLI usage includes harness/prompt overhead; CLI wall time includes process and
network overhead. Neither represents production application performance.
Subscription monetary cost is unavailable, not zero.

The next release work is independent label collection and calibrated claim
evaluation on a larger real application. See [the roadmap](ROADMAP.md).
