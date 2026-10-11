# v0.5: connected-system validation — 2026-10-11

Reviewed report: [v05-2026-10-11.json](experiments/v05-2026-10-11.json).
These are owned development captures. No external developer or independent human
label reviewer participated. Captures preceded final version/commits; the fresh
consumer's package label was still 0.4.0 while containing the development changes.
Release package/container checks are separate. Raw keys, databases and prompts
remain private under ignored `data/`. Public report fields were selected and
checked for credential patterns.

All six [release CI jobs](https://github.com/rahbarahsan/governloom/actions/runs/38116779187)
passed at `aca7c10`: Python 3.11/3.13 core (89 passed and two optional skips each),
actual-model examples (10 passed plus the headless quickstart), SDK integration,
five Chromium workflows and distribution. The fresh Linux consumer installed
**0.5.0**, reached its real incident in 29.856 seconds and stopped its collector.
The container built and passed both create/restart checks as UID 10001 with a
read-only root, named access, built dashboard, persisted deadline and exact replay.
These software checks do not establish production scale or independent usability.

## Installed consumer and operational boundary

A fresh venv installed a built wheel, locked dependencies and model libraries.
A copied standalone consumer ran from a separate working directory, imported the
installed public hook and trained its own scaled logistic classifier on bundled
UCI digits. It made 15 errors on 450 held-out digits; the check selected one natural
error with confidence 0.446492 and proved output withholding after one target call.
This selection and the illustrative 0.95 gate do not measure detector accuracy.
Setup took 130.500 seconds, with the first incident at 148.598 seconds from start.
This is one Windows installation, not independent onboarding feedback or a guarantee.

The owned forecast/receiver drill completed in 18.680 seconds. Deliberately delayed
numeric feedback produced one overdue alert; a receiver holding the old signing
key accepted during rotation overlap. It committed then returned 503, and retry
produced two sender attempts but one persisted notification. After its key update,
the actual arrived 4.580 seconds late. Coverage resolved; the incident remained
open. No real production deadline was missed in this integration drill.

Six hundred controlled observation events in serial loopback HTTP batches took
3.996 seconds. They are software telemetry, not model predictions or sustained
production throughput. Offline bundle restore preserved 602 observations,
30 entities and two signing keys, with integrity/count/hash verification and no
automatic worker startup. Additional tests exercise concurrent deadline workers,
overlap expiry/emergency revocation, secret tampering, conservative retention and
actual SQLite `SQLITE_FULL` rollback/recovery using a page cap, not OS disk filling.

## Chronological forecasts

The same frozen revised NOAA monthly snapshot trains rolling models strictly on
prior observed months. Eight non-overlapping quarterly calibration blocks from
2019–2020 select the maximum order-statistic threshold at alpha 0.2:
**1.496969 ppm**. The 2021–2024 chronological holdout is never used to tune it.
Missing calibration months are rejected; missing held-out months remain in their
calendar block and make its block check unavailable.

Of 48 observed held-out months, six exceed the block threshold; five of sixteen
quarterly blocks exceed it (31.25%). The original monthly 90th-percentile gate
flagged fifteen months. These are residual exceedances, not independently labeled
unsafe forecasts. Dependence between blocks, nonstationarity and data revisions
invalidate a nominal coverage interpretation; the report records
`nominal_probability_valid=false`. It is not an implementation or proof of the
block-randomization method in [dependent-data conformal research](https://arxiv.org/abs/1802.06300).

## Grouped RAG judgments and retrieval failures

Four calibration and four held-out documents/topics each contain an authored
supported statement, an explicit contradiction and an unresolved statement.
Engineering labels, sources, groups and the zero-contradiction threshold were
frozen before inference. The v2 rubric requires an explicit quoted contradiction
for `unsupported`; unresolved facts stay `insufficient_evidence`.

Exactly fourteen existing-ChatGPT-login requests completed: eight grouped judgments,
four relevant-document removal checks, one natural generated answer and its judge.
No API key or paid API fallback was used. Replay after the retrieval fix made zero
new requests. Authentication/capture behavior follows [official Codex non-interactive
documentation](https://learn.chatgpt.com/docs/non-interactive-mode) and
[authentication guidance](https://learn.chatgpt.com/docs/auth).

| Split | Authored claims | Contradictions flagged | Contradictions missed | Supported claims falsely flagged | Supported claims clear | Unknown claims kept unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | 12 | 4 | 0 | 0 | 4 | 4 |
| Held-out documents | 12 | 4 | 0 | 0 | 4 | 4 |

There were no label disagreements on these simple controls. Four declared
retrieval gaps also stayed unresolved, including through actual collector HTTP.
This small, obvious set does not establish broad semantic accuracy. The judge
and natural generator use the same model; no independent labels were collected.

Inspection exposed a genuine corpus-selection defect: a local variable overwrote
the caller's requested document list. The original retriever returned none of
the eight specifically expected documents. The fix honors the explicit corpus;
replaying the unchanged questions against the frozen eight documents retrieves
five of eight expected documents. Three misses remain. Document membership is
only a preliminary retrieval measure; it does not prove sufficient passages.

The original natural answer used the unintended legacy three-document corpus.
It gave general outcome-linking advice but could not establish the new deadline
workflow. Its frozen judgment includes unresolved evidence; corrected HTTP replay
preserves an `insufficient_evidence` receipt. The answer was not regenerated or
counted as proof of the corrected retriever's answer quality.

## Vision groups and remaining work

The frozen 5% calibration gate's natural 360-digit holdout still has 15 captured
errors, three misses, 26 false alarms and 316 clear correct predictions. The report
breaks these down by all ten digit labels. Declared occlusion yields 220 flagged
wrong and 140 flagged correct classifications. Noise yields 325 flagged wrong,
two missed wrong and 33 flagged correct classifications. Original labels under
corruption are engineering references; recognizability is not independently
reviewed. These are neither new-domain validation nor a fairness certification.

The twelve-frame GIF now includes actual forecast/late-feedback coverage and
open incident review. The owned capture makes no new model requests.
Container build/restart CI and installed-package checks verify software delivery,
not production safety. Next evidence should cover independent usability, realistic
retrieval/answer tasks, actual deployment sampling, longer failure/load studies
and task-specific label review. Packages/images remain unpublished; no hosted
deployment or external-recipient notification occurred.
