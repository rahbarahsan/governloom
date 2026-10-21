# Discovery capture

`demo.gif` records six actual Chromium states at 1280 x 900 over 24 seconds
(400,242 bytes). It shows a named operator importing application evidence,
reviewing a frozen real model analysis and exact source quote, confirming the
meaning of outcomes, evaluating a monitoring proposal, reviewing a held-out
budget warning and activating observation flags. An actual NOAA forecast and
linked observed actual then produce an open incident through the prepared mapper.

`demo-poster.png` is a still alternative; `demo.json` records source/model/prompt
hashes, timing, dataset checksum and the actual forecast/actual values. Pixels
and measured values are not retouched. The encoder verifies all decoded frames,
loop metadata, 20-30-second timing, equal dimensions and a size below 5 MB.

Semantic analysis replays the frozen v0.6 capture; the GIF makes **zero new model
requests**. Account `demo-operator` takes scripted actions. This does not measure
independent owner effort, semantic interpretation accuracy or production safety.
The forecast is an illustrative held-out selection above the frozen threshold;
quality denominators come from the separate [release measurements](../V06_EVIDENCE.md).
No credentials appear in the frames or public manifest.

## Reproduce

Prepare the optional model/media dependencies, Chromium and built dashboard:

```powershell
.venv\Scripts\python.exe -m pip install -r scripts/requirements-media.txt -r examples/requirements.txt
npm --prefix web run build
.venv\Scripts\python.exe -m scripts.capture_discovery `
  --directory data/new-discovery-gif `
  --evidence data/v06-discovery-2026-10-21-b `
  --snapshot data/miniapps/noaa-2026-10-07.txt
```

Use `.venv/bin/python` on macOS/Linux. The evidence directory contains frozen
discovery bundles from `examples.discovery_testbed`; creating a new semantic
capture requires its separate explicit subscription opt-in. The NOAA snapshot
is explicitly downloaded beforehand and retains its source attribution.

The capture owns an isolated named-account collector and browser, and executes
the owned forecast model in a bounded subprocess. Services stop even after browser
failure. Private bundles, PNG frames, configuration and logs stay under ignored
`data/`. The Python subprocess decodes JSON as UTF-8; dataset hashing normalizes
equivalent integral JSON numbers across languages.

The [v0.5 runtime GIF](https://github.com/rahbarahsan/governloom/blob/aca7c10/docs/media/demo.gif)
preserves the earlier twelve-frame digit, signed-delivery, forecast deadline and
recorded RAG workflow. `scripts/capture_runtime.py` can reproduce that path;
`web/scripts/capture-demo.mjs` remains the legacy fictional workbench recorder.
Both replace the current `demo.gif` when run. Pillow is documentation-only.
