# Proposed v0.2: claim grounding and human calibration

Status: v0.1 remains the shipped release. The first real-inference experiment
is implemented and recorded; the release scope below remains incomplete with
no promised date. The user authorized local ChatGPT-subscription usage; no
paid API usage or deployment is authorized.

## Outcome

A reviewer can identify which answer claims lack support, inspect the cited
passages, and see how often the evaluator agrees or disagrees with independently
reviewed labels. The no-key workflow must continue to run without a judge.

The current release misses all ten unsupported additions in its held-out fault
run. Exact reference substrings and valid document IDs do not establish claim
support. Closing that measured gap is the strongest next product improvement;
the evidence is in `release-evidence.json`, not a general model benchmark.

The [subscription-backed experiment](SUBSCRIPTION_EVAL.md) now captures actual
answers without sharing an API key. On four exploratory cases, the existing
literal check rejected both paraphrases. Separate real-model claim judgments
marked both original answer claims supported and both synthetic additions
unsupported. Eight model turns and exact source evidence are recorded. These
are uncalibrated estimates; dashboard semantic scoring and independent review
are still pending. This is the initial real-model vertical slice, not completed v0.2.

## Recommended scope

| Priority | Deliverable | Release evidence |
| --- | --- | --- |
| 1 | Claim-level grounding evaluator through one explicitly configured provider adapter | Pin judge/model/rubric versions; preserve each claim, source passages, verdict and explanation; retain unsupported/insufficient/error states separately |
| 2 | Independent review and calibration workflow | Export blinded outputs for a separate reviewer; import attributed labels; preserve disagreements and adjudications; calibrate on development groups, then freeze thresholds before held-out scoring |
| 3 | Second application and corpus | An independently implemented documentation assistant and user-provided or redistribution-approved documentation; record provenance/license; include clean outputs and deliberately unsupported statements |
| 4 | Easier local operation | One command starts API/worker/dashboard on the same database, reports readiness, and stops them cleanly; add finding search and filters by category/metric/status |

Keep this to one adapter and one semantic dimension initially. Semantic outputs
are estimates. A local model can be an optional provider if the user configures
one; a paid provider needs explicit spending authorization and a positive cap.
Both need bounded requests/tokens/timeouts, cancellation and recorded usage.
No adapter should activate just because credentials exist in the environment.

## Acceptance criteria

- An answer containing the reviewed reference answer plus an unsupported extra
  statement produces an inspectable claim verdict and supporting passage links.
  A fake-provider fixture checks integration only; it is not evidence of real
  semantic quality.
- Separate reviewer labels have actual provenance. Missing independent labels
  leave calibration unavailable; scripted approvals cannot satisfy this gate.
- Hold source/topic groups apart and keep thresholds fixed on held-out data.
  Report precision, recall, confusion counts, denominators, uncertainty and
  disagreements for clean and faulty outputs, separately for each application.
  Do not promise a precision/recall target before measuring it.
- Preserve every selected model/rubric version, dataset/source snapshot, request
  budget, judge response and per-claim evidence. Missing or contradictory
  evidence is explicit; judge errors never become zero or a pass.
- The second corpus is sourced and licensed before redistribution. Preliminary
  results on two small corpora do not establish general RAG reliability.
- The existing no-key demo, immutable publication, cancellation/recovery and
  matched comparisons still pass backend and browser checks. Disabled providers
  make zero calls; budget failures do not retry or overspend.

## Delivery order

1. Build the independent-label import/export and calibration report first.
   Define the claim rubric and adversarial clean/unsupported examples.
2. Integrate one bounded judge adapter; verify failures with a fake and measure
   actual agreement only when a real provider and reviewers are available.
3. Exercise the frozen rubric on the second application and held-out groups.
4. Ship the launcher and finding filters alongside documented results and misses.

Local subscription-backed inference is available through an explicit CLI
experiment. Independent human reviewers and an integrated calibrated judge
are still missing. Next, build blinded label export/import and adjudication,
then connect claim evidence to dashboard results while keeping uncalibrated
estimates visibly separate. Exercise a larger independently sourced application
before interpreting judge agreement as evidence of general reliability.

Enterprise authentication, multi-tenancy, distributed workers, PDF/OCR, remote
connectors, autonomous paid work and compliance certification stay outside v0.2.

## Why calibrate

The MT-Bench/Chatbot Arena study evaluates LLM judges against human preferences
and discusses judge biases. It supports measuring agreement rather than assuming
it; its results do not transfer automatically to our grounding rubric or corpus.
[Primary paper: Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685).
