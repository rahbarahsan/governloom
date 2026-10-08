# Documentation RAG service

This application retrieves actual README/runtime/research passages using TF-IDF
and generates answers with the existing local Codex ChatGPT login. It refuses
generation without explicit opt-in. There is no scripted answer fallback.
Install the separate `examples/requirements.txt` dependencies first.

Set `GOVERNLOOM_ENDPOINT`, a scoped `GOVERNLOOM_INGEST_KEY`, `MINI_STATE`,
`ALLOW_SUBSCRIPTION=1`, `RAG_MODEL`, `RAG_MAX_REQUESTS` (default 3, maximum 20),
and a **new** ignored `RAG_CAPTURE` directory. Run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn examples.rag.app:create_app --factory --host 127.0.0.1 --port 8103
```

POST `/answer` with `question` and optional `mode` (`enforce` by default).
GET `/manifest` records corpus hashes, passage boundaries, revision and settings.
The application keeps answers/evidence in its own SQLite database; collector
text scanning is transient. An input block can prevent inference; an output
block withholds the generated answer and creates an application review record.
The generator interface is replaceable; the subscription adapter is a bounded
development target, not a production inference provider.

POST `/faults` with a completed natural `event_id` and `mutation` of
`invalid_citation` or `credential` mutates a real captured response **after**
generation. These labeled fault checks make no extra model calls. POST
`/tools/write` attempts a fixed local marker write through the enforcing tool
hook; configure a tool allowlist permitting only `search` to block it before
the side effect. Both endpoints are local testbed tools.

Citation membership cannot prove factual support. Three exploratory model
questions cannot calibrate detector precision or establish a production SLA.
CI substitutes an explicitly fake generator to test integration; it never
uses a subscription login or asserts fake answers as model-quality evidence.
