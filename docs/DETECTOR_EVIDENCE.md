# Task-specific detector evidence

These opt-in checks complement numeric thresholds, citation identity and text
patterns. They produce inspectable flag/review signals, never automatic blocks.
They cannot certify an AI system or establish every kind of risk.

## Freeze and review a profile

An operator posts a profile to `POST /api/applications/{id}/detector-profiles`
or imports its JSON under **Detector evidence**. Every profile includes an exact
task/environment/model/application version and event phase (default output;
choose outcome for forecast residuals), immutable calibration dataset and label
hashes, disjoint calibration/held-out topic groups and held-out confusion
counts (captured risks, misses, false positives, clear controls, unavailable).
Engineering, observed-outcome and independent-human provenance are distinct.
The operator is responsible for the submitted evidence; a hash alone does not
prove label quality or independent review.

A reviewer inspects/downloads the profile, then approves its checksum with a
rationale. Approval is a separate immutable record. Changing references, scope,
rubric or thresholds requires a new profile; old receipts remain attributable.
Configure a policy template and supply its profile ID. Unapproved, wrong-scope,
missing-metric and incomplete-window events report insufficient evidence.

The exact JSON schema is in `/openapi.json` (`DetectorProfile`, `Calibration`,
`Grounding`) and the typed Python models in `governloom.detectors`. The reproducible
validation runner saves profile request bodies in its private `report.json`.

## Claim support for RAG

A profile freezes `corpus_sha256`, `source_hashes` (source ID → SHA-256 of passage
text), `judge_version`, `rubric_version` and `unsupported_fraction_threshold`.
Your upstream judge sends `grounding` with the event's transient answer text:

```json
{
  "profile_id": "the-approved-profile-id",
  "corpus_sha256": "64-character-corpus-sha256",
  "judge_version": "your-judge-version",
  "rubric_version": "your-frozen-rubric",
  "answer_sha256": "sha256-of-the-exact-utf8-answer",
  "claims": [{
    "claim": "Exact non-overlapping excerpt from the answer.",
    "verdict": "supported",
    "explanation": "Why the passage supports the claim.",
    "evidence": [{"source_id": "passage-1", "quote": "Exact source quote."}]
  }],
  "sources": [{"id": "passage-1", "content": "The exact frozen passage text."}]
}
```

The example hashes are placeholders; compute real hashes before submission.
Verdicts are supported/unsupported/insufficient_evidence. The collector validates
answer/source hashes, exact claim excerpts, exact source quotes, citation/source
identity and non-overlapping coverage. A supported verdict must quote a cited
source from the frozen registry. Clear requires at least 95% of non-whitespace
answer characters covered and no unresolved claim. An unsupported claim above the
frozen threshold requests review even when the remaining answer has a coverage gap.
This is character coverage of supplied excerpts, not proof of exhaustive factual
claim extraction or entailment. Exact quotes can still be semantically misjudged.

The collector stores only counts, positions, hashes, profile/rubric provenance
and findings. Answer, passage, quote and explanation text are transient. The
client/application can retain private source evidence for inspection; collector
positions require that frozen source. The durable metadata hook rejects this
payload: grounding cannot be recovered from a text-free outbox. The collector
does not choose/call a provider. Integrate your own judge or use the mini RAG
application's explicitly enabled local subscription adapter for development.
`RAG_GROUNDING_PROFILE` enables that adapter; `RAG_JUDGE_MAX_REQUESTS` bounds
calls. The demo records target `latency_ms` separately from `judge_latency_ms`.
A judge failure is an application error, never a clear grounding result.

## Distribution change for vision and forecasting

A profile freezes a named numeric metric, 20–1,000 reference observations,
`window_size` (20–1,000), `alpha` and minimum ECDF distance. Only complete,
non-overlapping windows are checked. State commits with each receipt; exact replay
does not add another sample. Scope/version changes cannot silently join a window.
Window number persists across policies using the same profile. Creating another
profile starts another explicitly separate statistical budget.

The measured distance is `sup_x |F_reference(x) - F_window(x)|`, including ties.
For completed window `k`, spend `alpha_k = alpha / (k * (k+1))`. The threshold is:

```
sqrt(log(4/alpha_k)/(2*n_reference))
  + sqrt(log(4/alpha_k)/(2*n_window))
```

This conservative construction uses two one-sample DKW–Massart bounds, the triangle
inequality and a union bound. The spends sum to at most alpha over the lifetime of
that profile. A finding requires distance above both this threshold and the frozen
minimum effect. If the bound reaches one, detection is unavailable at that budget
and sample size. The check can become insensitive as its budget is spent; create a
new reviewed reference only with an explicit monitoring-horizon decision.

The probability interpretation assumes independent identically distributed
samples within the reference/current populations. It does not follow for temporal
residuals, correlated images or biased sampling. `sampling_assumption=dependent_replay`
marks the threshold as an empirical replay signal, explicitly setting
`nominal_probability_valid=false`. The NOAA benchmark uses this setting. Forecast
outcomes must be observed, never imputed to zero; delayed actuals delay detection.
A changed confidence/residual distribution does not identify cause or certify
accuracy. Inspect actual labels/outcomes before selecting mitigation.

The ECDF distance is cross-checked against SciPy on real mini-app outputs. IID
negative controls and analytical tied-sample checks exercise the software; they
do not establish a customer's false-alert rate. Reference: [DKW–Massart proof](https://arxiv.org/abs/2403.16651)
and [SciPy two-sample KS documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html).

## Reproduce actual-model validation

```powershell
.venv\Scripts\python.exe -m examples.detector_validation `
  --directory data/new-detector-capture `
  --forecast-data data/miniapps/noaa-2026-10-07.txt
```

Add `--subscription` only for the explicitly bounded ChatGPT-login path: eight
authored documentation judgments plus one actual RAG answer and one judgment.
No API key, remote dataset download or external notification is used. Every owned
service stops at the end. Captures/profile evidence stay in ignored `data/`.
CI uses actual bundled digits, synthetic forecast fixtures and an explicitly fake
judge; it never spends subscription requests. Published measurements are separate
from software pass counts.
