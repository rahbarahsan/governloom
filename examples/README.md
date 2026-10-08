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

See [vision](vision/README.md), [forecasting](forecasting/README.md), and
[RAG](rag/README.md) for independent serving and model limitations. Vision's
`/baseline` is deliberately unmonitored for paired HTTP overhead measurements;
it is a local benchmark endpoint, not a production serving path. Raw captures,
application databases and logs belong under ignored `data/`. Publish only
reviewed reports, never ingestion keys, authentication files or user data.

CI tests real digit training and public HTTP integration. It uses an explicitly
synthetic series and fake generator for forecast/RAG software checks, with no
remote downloads, login, inference or model-quality claims for those fixtures.
