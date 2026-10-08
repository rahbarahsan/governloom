# Runtime capture

`demo.gif` records ten actual Chromium states at 1280 × 900 over 24.6 seconds.
It shows named sign-in, actual held-out UCI digit inference, response withholding,
application review/outcome, attributed incident mitigation, durable metadata
coverage, and grounding evidence from a recorded real RAG answer/judgment.
Values are not retouched. `demo-poster.png` is a still alternative; `demo.json`
records timing, model/source provenance and the zero-new-inference replay.

The digits are illustrative selections from the frozen held-out set, not a
blind quality evaluation. Quality counts come from the separate complete benchmark.
RAG is explicitly `recorded-rag-replay`; its passage hashes and judge version
match the earlier actual-model capture. No generation/judge request is made for
this recording. Named account `demo-operator` takes scripted actions; this is not
independent human validation or independently verified mitigation. Credentials
are generated privately, never recorded in frames or public metadata.

## Reproduce

Complete root setup, optional model requirements and Playwright Chromium install:

```powershell
.venv\Scripts\python.exe -m pip install -r scripts/requirements-media.txt -r examples/requirements.txt
npm --prefix web run build
.venv\Scripts\python.exe -m scripts.capture_runtime `
  --directory data/new-runtime-gif `
  --evidence data/detectors-2026-10-08-b
```

The evidence directory needs a completed grounding run, including its private RAG
database and target/judge captures. Another checkout can generate one via
[detector validation](../DETECTOR_EVIDENCE.md); that step has a separate explicit
subscription opt-in. On macOS/Linux use `.venv/bin/python`.

The capture owns a fresh collector and actual digit service on free loopback ports,
uses an isolated account database and stops both even on browser failure.
PNG frames, private configuration, logs and manifests remain in the ignored capture
directory. The Pillow encoder verifies frame count/looping, 20–30-second timing,
size under 5 MB and agreement of every decoded frame with its screenshot.
Pillow is documentation-only. `web/scripts/capture-demo.mjs` remains the fictional
v0.1 fixture recorder; running it replaces the runtime GIF.
