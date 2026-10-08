# Actual detector validation — 2026-10-08

Full reviewed report: [detectors-2026-10-08.json](experiments/detectors-2026-10-08.json).
The isolated runner completed and stopped all owned services. Source/label/profile
hashes and software versions are retained. Private prompts and SQLite databases
remain in `data/detectors-2026-10-08-b/`. This was a development working-tree
capture; its recorded Git revision precedes the detector code, so the end-of-capture
code hash and frozen evidence must accompany that revision.

| Check | Held-out/control units | Risks flagged | Risks missed | False positives | Clear controls | Unavailable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vision confidence distribution | 9 windows × 120 digits | 6 | 0 | 0 | 3 | 0 |
| Forecast residual replay | 4 windows × 24 months | 2 | 0 | 0 | 2 | 0 |
| RAG claim support, held-out topics | 4 authored claims | 2 | 0 | 0 | 2 | 0 |
| RAG claim support, calibration topics | 4 authored claims | 2 | 0 | 0 | 1 | 1 |

Vision uses the actual trained 64-tree classifier and its disjoint frozen
calibration/held-out partitions. Perturbations are declared occlusion and noise,
not natural errors. Normal windows contain all 360 held-out digits. Drift distance
matches SciPy's independent ECDF implementation. These window detections do not
mean every wrong digit was caught: the underlying confidence-review gate still
misses one of 18 natural errors and flags 52 correct predictions. Sampling/writer
dependence is not certified by this benchmark.

Forecast references are the 24 observed 2019–2020 errors; held-out outcomes are
2021–2024. A declared +5 ppm prediction offset creates the positive controls.
References/rule parameters are frozen before held-out evaluation. Residuals are
serially dependent, so these are empirical replay detections with
`nominal_probability_valid=false`, not a statistically guaranteed false-alert
rate. The data is the same revised NOAA snapshot described in
[testbed evidence](TESTBED_EVIDENCE.md), not a historical data-vintage simulation.

RAG uses actual repository passages and `gpt-6.1-sol`, Codex CLI 0.160.1. Four
paired topics are disjoint across calibration (key storage, binary inputs) and
held-out (enforcement, citation support). Eight claims are explicitly authored
supported/contradictory controls; labels are engineering judgments, not independent
human review. The zero-unsupported-claim threshold was predeclared and checked
only on calibration. The key-storage supported claim was unresolved because its
passage did not explicitly name the storage component: the result stayed
unavailable. No threshold was tuned on held-out outcomes.

An additional natural RAG answer went through the independent service's normal
HTTP generation/grounding path. It described tool enforcement but opened with the
overbroad claim that an enforce-mode block raises before target invocation. The
judge identified that sentence as unsupported and quoted the source distinction:
output blocks withhold results after inference. Two other excerpts were supported,
coverage was 100%, and the collector requested review. The application returned
the answer with a persisted review/action acknowledgment, as configured; this
experimental semantic detector cannot block. The finding agrees with the actual
Python hook's input/output ordering, but this single engineering inspection is not
an independent accuracy study.

Exactly **10 subscription requests started and completed**: eight benchmark
judgments, one generated natural answer and its judgment. The collector made no
provider calls. The first failed preparation run attempted to read calibration
dates through the held-out outcome accessor; that was corrected to use calibration
observations and made zero subscription calls. No dataset download, paid API
request or real-recipient notification occurred.

Next evidence investment: more diverse grouped claims, independent label review,
retrieval coverage and judge error analysis; temporally appropriate forecast
calibration; real deployment sampling/alert budgets and longer workload studies.
