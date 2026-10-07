# Interpreting measurements

There is no combined governance score. Each metric has a purpose, required
inputs, direction, threshold, evaluator version and limitations. Recommendations
use declared application behavior, supported fields and available labels.
Actual evaluation checks prerequisites on every case/trace.

- **Enabled:** a suggested dimension with available prerequisites for at least
  one case. A run can explicitly select/omit it.
- **Suggested:** an available optional observation, such as priced cost.
- **Unavailable:** missing prerequisites or no semantic judge. Selected
  unavailable checks produce explicit non-score results.

Default runs include all dimensions to expose gaps. Token/cost checks have no
quality threshold; passed means measurement availability, not acceptable spend.

## States and denominators

`passed`/`failed` are scored or observed results. `skipped` means inapplicable
(such as answer citation checks on abstention). `insufficient_evidence` means
missing inputs, unmatched traces or unavailable judges. `evaluator_error` means
the evaluator crashed. An observed target timeout is distinct from a judge crash.

Every dimension shows passed/scored, failed, skipped, insufficient, evaluator
errors and pending/selected. Scored = passed + failed. A pass rate is null with
no scores and must be read with coverage. No absent latency, usage or cost is zero.

| Dimension | Measurement | Limitation |
| --- | --- | --- |
| Task success | Exact expected vs observed behavior | Answer/abstain/clarify only |
| Reference agreement | Normalized reference substring | Misses paraphrases and unsupported additions |
| Citation existence | Nonempty answer citation list | Does not establish correctness |
| Citation consistency | IDs exist and match reviewed evidence | Document-level, no claim entailment |
| Retrieval recall | Relevant retrieved / all relevant | Explicit exhaustive relevance judgments required |
| Retrieval precision | Relevant retrieved / all retrieved | Same requirement; empty retrieval with nonempty judgments scores 0 |
| Latency | Observed ms; threshold <=1,000 | Local timing; demo timeout is simulated |
| Errors | Observed error 1 or success 0 | Explicit error channel observation required |
| Token usage | Supplied input + output tokens | No estimates substituted |
| Cost | Usage × configured prices | Needs counts and both prices |
| Semantic grounding | Unavailable | Needs pinned judge/rubric and independent calibration |

Answer-specific checks skip non-answer cases. Retrieval checks can still measure
which policy document supports a boundary scenario.

## Comparison

Match finalized IDs with unchanged case revision/content. Fully compatible
comparisons require the same application, dataset checksum and selected
evaluator definitions, input availability and prices. Changed labels, different
samples or incomplete jobs produce reasons and matched/selected counts.
Individually compatible dimensions can still show changes in incomplete
comparisons; incompatible definitions are excluded. Latency changes are
observations, not automatically improvements.

## Fixtures and model work

Northstar has eight topics, five cases each and six scenario categories. The
fixed JSONL suite separates 20 calibration/20 held-out cases by topic. Labels
are repository-authored template fixtures, passage-verified by automated tests.
No independent human review occurred. UI decisions attribute the user's actor;
CLI acceptance explicitly identifies scripted fixture acceptance.

Known-fault traces exercise detection and its misses. They cannot establish
real-model quality or generalization. Fake-provider checks establish budgets,
schema/reference validation and failure handling only. No paid adapter exists.

A future model judge must retain model/rubric versions, evidence and calibration,
compare with independent human labels, hold thresholds fixed on held-out data,
and report precision/recall, disagreements, counts and uncertainty. Do not use
held-out labels for tuning. The small fixtures cannot substitute for that study.
