# v0.6 discovery evidence — 2026-10-21

Reviewed report: [v06-2026-10-21.json](experiments/v06-2026-10-21.json).
Three owned applications were inspected without supplying a monitoring policy.
These sources contain useful task declarations and familiar field names; this is
not a blind external discovery benchmark or independent usability study.

## What actually ran

The local explorer read application sources and sample observations without
executing the inspected files. Exactly **three** existing-ChatGPT-login requests
completed, one for each application, using `gpt-6.1-sol`. They returned 21 hypotheses
and 23 candidate scenarios. All 44 exact source references passed quote validation.
This verifies provenance, not the semantic accuracy of those interpretations.
Scenarios remain unreviewed and are excluded from calibration/held-out denominators.
No API key, paid API fallback, external recipient or additional RAG generation was used.

The semantic capture took 124.749 seconds, including model analysis and public-HTTP
monitoring workflows. Frozen replay through the public `DiscoveredObserver` took
3.951 seconds with zero new requests. Both own and stop their collector. Raw
bundles, prompts and databases remain private under `data/`; selected source
quotes in the public report are from our own repository.

| Application | Frozen evidence | Result |
| --- | --- | --- |
| Actual digit classifier | 269 calibration / 360 held-out examples from the existing UCI split | Correctly inferred vision; proposed confidence threshold 0.4375 at a 5% calibration false-positive budget; actual new inference produced a flag and incident |
| Actual NOAA rolling forecaster | 24 calibration months / 48 held-out months from the existing frozen snapshot | Correctly inferred forecasting; proposed residual threshold 0.994920 ppm; actual prediction and linked observed actual produced a flag and incident |
| Documentation RAG | One recorded real answer and citation metadata from v0.5 | Correctly inferred RAG; separate calibration/held-out evidence unavailable, so activation remained unavailable |

Three task matches out of three cue-rich owned systems do not estimate general
discovery accuracy. Scripted acceptance needed no task/mapping corrections;
that does not establish that real owners need no corrections or measure their effort.
Boundary tests separately exercise wrong task inference, ambiguous fields and
owner correction history.

## Quality trade-offs remain visible

Vision's proposed gate captures 15 of 18 held-out errors, misses three and flags
26 correct predictions. Its 7.60% held-out false-positive rate exceeds the 5%
calibration budget. This is the existing model/split, not a new independent dataset.

The forecast recipe uses a nearest-rank empirical **point-residual** quantile.
It differs from v0.5's quarterly block gate and the original interpolated monthly
quantile. Fourteen of 48 held-out months exceed its threshold; MAE is 0.756540 ppm,
RMSE 0.950666 ppm and signed prediction-minus-actual bias is -0.119357 ppm.
Exceedances are not independently labeled harmful forecasts. Dependence and revised
snapshots invalidate nominal false-alert/coverage claims. The fixed pipeline code
plus snapshot define the monitored rolling pipeline version; per-origin refitted
coefficient hashes remain in the source observations separately.

Both held-out budget violations produce explicit proposal warnings. We did not
retune thresholds on held-out outcomes. A single RAG answer cannot justify
calibration, retrieval recall or semantic accuracy. Its existing insufficient-
evidence judgment is preserved; no new answer was generated.

## Software boundaries

Checks cover immutable evidence/proposals, calibration-only selection, temporal
and group leakage, missing actuals, exact duplicate handling, live-version binding,
concurrent/idempotent activation, stale policy/understanding conflicts, named roles,
private trace text exclusion, credential-free validation errors and source quote/
checksum validation. RAG identity controls remain distinct from semantic labels.

Final local full Python verification passed 114 checks (159.59 seconds), including
14 discovery boundary checks. A subsequent numeric-class-label regression expanded
that boundary suite to 15 passing checks; it prevents equivalent 1/1.0 labels
from manufacturing errors. All six Chromium
workflows passed, including evidence import, owner correction, proposal review,
flag-only activation and a live incident. Final release CI/package checks are
recorded in [progress](PROGRESS.md) when complete.

The browser-to-Python capture exposed equivalent `100.0`/`100` JSON number
representations in dataset hashing. The new dataset hash normalizes integral
numbers, with a regression check. Windows capture stdin also now explicitly
decodes UTF-8; the actual cross-language workflow verifies both boundaries.

The updated GIF uses frozen real semantic analysis with no new requests, named
scripted confirmation and actual NOAA inference/feedback through the prepared
mapper. It demonstrates software behavior, not human usability or production
governance effectiveness. No package/image publication or hosted deployment occurred.

Reproduce real owned-model workflows with `python -m examples.discovery_testbed
--directory data/new-discovery --forecast-snapshot data/miniapps/noaa.txt` after
preparing optional model dependencies and an explicit frozen NOAA snapshot.
`--subscription` adds at most three explicitly bounded model requests. Ordinary
CI uses actual bundled digits without downloads or model-provider calls.
