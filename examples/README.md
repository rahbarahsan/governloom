# Three real AI mini applications

These are independent serving applications using GovernLoom's public hook and
HTTP API. They do not import collector storage to manufacture monitoring results.
Model dependencies remain separate from the collector package.

```powershell
.\.venv\Scripts\python.exe -m pip install -r examples/requirements.txt
.\.venv\Scripts\python.exe -m examples.forecasting.download data/miniapps/noaa-snapshot.txt
.\.venv\Scripts\python.exe -m examples.testbed --noaa-snapshot data/miniapps/noaa-snapshot.txt --output data/testbed-new --allow-subscription --model gpt-6.1-sol
```

The explicit download preserves NOAA headers and provenance. Each run requires a
new output directory and starts an isolated collector plus three loopback
services on available ports. The runner provisions scoped keys in process memory,
exercises real predictions, delayed outcomes, review/withholding and denied tool
use, writes a report and stops all owned processes even after failure.
Subscription generation uses your existing local Codex ChatGPT login, at most
three CLI invocations with 180-second deadlines. It does not export credentials
or use an API key. Omit `--allow-subscription` to run vision/forecasting only;
RAG is then explicitly recorded as **not run**.

For optional dashboard exploration, first set your own `GOVERNLOOM_ADMIN_TOKEN`
of at least 32 characters and build the web bundle. Add `--explore-seconds 60`
(maximum 600). The runner prints the local URL, never the token, and keeps its
services ready for that bounded interval before shutdown. Enter the token in
the dashboard. Ctrl+C also stops owned processes. The default leaves no servers.

See [vision](vision/README.md), [forecasting](forecasting/README.md), and
[RAG](rag/README.md) for independent serving and model limitations. Vision's
`/baseline` is deliberately unmonitored for paired HTTP overhead measurements;
it is a local benchmark endpoint, not a production serving path. Raw captures,
application databases and logs belong under ignored `data/`. Publish only
reviewed reports, never ingestion keys, authentication files or user data.

CI tests real digit training and public HTTP integration. It uses an explicitly
synthetic series and fake generator for forecast/RAG software checks, with no
remote downloads, login, inference or model-quality claims for those fixtures.
## Interactive digit service and reviewed detectors

`ENABLE_BROWSER=1` enables local same-origin browser controls at `/` in the digit
service. It loads original held-out pixels, calls the real `/predict` boundary,
shows withheld responses and resolves reviews against benchmark labels.
Cross-origin POSTs and unrecognized hosts are rejected. This is a local engineering
UI, not an end-user production authentication layer.

`ENABLE_BACKGROUND=1` enables separate observation/heartbeats; also set
`ENABLE_DURABLE=1` and `VISION_OUTBOX` to use restart-safe metadata delivery.
Synchronous enforcement stays separate. RAG's optional `RAG_GROUNDING_PROFILE`
enables its bounded upstream judge; source/profile versions must match exactly.
See [detector contract](../docs/DETECTOR_EVIDENCE.md) and
[actual validation](../docs/DETECTOR_VALIDATION.md). The runtime GIF combines live
digit inference with labeled replay of recorded real RAG evidence.
