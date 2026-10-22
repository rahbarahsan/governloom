# v0.7 owned validation evidence

The release adds guided policy/metric selection to connected-application discovery.
The bundled definitions are original starter controls linked to selected NIST AI
RMF 1.0 and OWASP LLM Top 10 2025 objectives. They do not certify compliance.
See [methods and public interfaces](POLICY_CATALOGUE.md).

## Four owned applications

The final HTTP run is `data/v07-policy-release/report.json` locally. A sanitized
summary is [published here](experiments/v07-2026-10-21.json). All four applications
prepared observation policies without supplied policy JSON and produced incidents
whose references matched the frozen catalogue. New provider requests: **zero**.

| Application | Measurement | Limits |
| --- | --- | --- |
| Actual digit classifier | 342/360 correct; gate catches 15/18 errors, flags 26/342 correct cases; alert precision 15/41 (36.59%), error recall 83.33%, FPR 7.60% | Exceeds its 5% calibration FPR budget; three confident errors missed |
| Actual NOAA rolling forecast | 48 held-out pairs: MAE 0.75654 ppm, RMSE 0.95067 ppm, signed bias -0.11936 ppm | Dependent revised snapshot; empirical threshold, no nominal guarantee |
| Actual local TF-IDF retrieval | Macro document recall@5 50% over four held-out questions | Authored document relevance labels; repeated ranked document positions retained; no new answer generation |
| Trained local intent router | Two out-of-permission attempts among four held-out model-selected tool calls | Small authored requests/training; no independent agent accuracy benchmark |

Citation incidents are deliberate empty-citation controls. The tool run separately
records one deliberate disallowed call in addition to model-selected attempts.
An independent application authorization check prevents deletion; GovernLoom's
observation flag does not perform that prevention. Historical captures and local
model outputs are not evidence of general discovery accuracy or owner usability.

## Verification

- Complete Python regression: **131 passed** in 153.84 seconds. A subsequent
  corrected-field normalization fix passed **31 discovery/guidance checks** in
  13.09 seconds; release CI reruns the full final tree.
  This includes known-value metrics, absent labels, zero denominators, large finite
  residuals, label-cardinality bounds, corrected list mappings, mixed versions,
  split leakage, source instructions, scoped catalogue access and historical plans.
- **Seven Chromium workflows passed** in 47.2 seconds, including source-backed
  proposal activation, confirmed tool permissions, reasoned deferral persistence
  and incident control references. Production dashboard build passed.
  CI subsequently exposed a startup application-selection race. The fix discards
  stale refresh responses; a new delayed-response regression and the composite
  policy workflow passed locally (25.2 seconds). Final CI includes eight workflows.
- Node SDK build and HTTP contract passed. A fresh tarball installed offline in a
  separate consumer passed clear/flag checks against a real collector and retained
  the OWASP tool-control reference. Both Node collector checks passed in 7.03 seconds.
- A fresh installed 0.7.0 wheel ran an actual classifier discovery consumer with
  360 held-out cases and produced an incident without prewritten policy. The
  existing installed enforcement consumer also passed. The final package rerun
  took 91.571 seconds to set up and 103.395 seconds to the first incident in the
  legacy consumer; this is one owned Windows environment. The final wheel was
  rebuilt after the corrected-field fix. SHA-256:
  `1658d3d8613622a3ab2a63ad0e3b50a451c4e9f13f67e684752364e0a74e6ba4`.
  All 31 discovery/guidance checks also passed from that installed final wheel
  in 11.24 seconds, with imports verified outside the editable source package.
  Release CI results are recorded in [progress](PROGRESS.md).
- Runtime event schema and dependency checks passed. Owned example/browser services
  were cleaned up after each run. No registry publication, hosted deployment or
  external-recipient notifications are part of this release.

## Interpretation

Label confirmation records the owner's understanding; it is not independent
human review. Accuracy, detector alert precision, retrieval coverage and policy
violations are distinct measurements. Unsupported semantic grounding, fairness,
successful unauthorized actions and full production traffic coverage stay visible
as gaps. Applicable unmeasured objectives do not silently become passing controls.

Policies retain model/application scopes, held-out failures and immutable reference
versions. Source excerpts and hashes establish provenance, not complete program
understanding. The refreshed browser GIF uses frozen earlier model analysis and
actual NOAA inference; it does not make new discovery or judge requests.
