# Schemas and imports

Importable cases/traces have `schema_version: 1`. Unknown fields/versions and
nonfinite measurements are rejected. JSONL batches validate before writing;
limits are 2,000 records and 5 MB of text. Blank lines are ignored. The UI
decodes source files strictly as UTF-8; source content is limited to 2 MB.

## Sources and positions

Use the file input or `POST /api/applications/{id}/sources`:

```json
{"schema_version":1,"document_id":"refund-policy","version":"2","filename":"policy.md","content":"Refunds are available within 30 days.\n"}
```

Application/document/version determines a stable source ID. Identical content
is idempotent; changed content requires a new version. Hashes cover the exact
decoded UTF-8 content passed to the service. Bundled files are read with Python
text newline normalization.

Offsets are zero-based **Unicode code-point positions**, with an exclusive end,
not byte offsets or JavaScript UTF-16 indices. Validation checks ownership,
hash, bounds and exact passage text. The UI highlights using code-point slicing.

The deterministic generator accepts only this structured format:

```text
- fact_id | topic | question | answer
```

Embedded pipes and multiline facts are unsupported. Other prose remains
available for manual references. The local target treats the **most recently
imported** version of each document as current; it does not sort arbitrary
version strings numerically. The outdated fault selects earlier imports.

## Cases

Replace IDs/hashes/ranges with your source values. Import one JSON object per
line; this example is pretty-printed for readability:

```json
{
  "schema_version": 1,
  "id": "my-refund-case",
  "application_id": "APPLICATION_ID",
  "question": "When can I request a refund?",
  "category": "answerable",
  "expected_behavior": "answer",
  "reference_answer": "within 30 days",
  "references": [{"schema_version":1,"source_id":"SOURCE_ID","start":29,"end":36,"quote":"30 days","content_hash":"SOURCE_SHA256"}],
  "relevant_source_ids": ["SOURCE_ID"],
  "provenance": "manually authored; awaiting review",
  "review_status": "unreviewed",
  "group_id": "refund-topic",
  "split": "held_out",
  "revision": 1
}
```

Categories: `answerable`, `missing_information`, `out_of_scope`,
`contradictory_outdated`, `misleading_premise`, `multi_turn_correction`.
Behavior: `answer`, `abstain`, `clarify`. Splits: `calibration`, `held_out`,
`exploratory`. Answer cases require a nonblank reference answer. All approvals
require valid evidence, including boundary scenarios.

Imports reset review status/revision and cannot bypass review. Exact normalized
question/behavior/answer duplicates are skipped. Each `group_id` belongs to one
split, preventing close paraphrases in a declared group crossing splits.
Templates use topic groups; manual authors must assign truthful grouping.
Semantic duplicate detection is unavailable.

`relevant_source_ids` is an **explicit exhaustive document relevance judgment**
within the corpus, not an inferred citation. Omit/null it without such labels.
Empty judgments are insufficient for precision/recall in this release.

Review requires an actor and `expected_revision`; stale edits fail. Explicit
null can clear a reference answer for non-answer behavior. Audit events retain
revisions; edits do not mutate published datasets. Later publication creates a
new immutable version.

## Traces

```json
{"schema_version":1,"id":"trace-1","case_id":"my-refund-case","application_version":"1","model_version":"local-v1","prompt_version":"1","answer":"Refunds are available within 30 days.","behavior":"answer","citations":["SOURCE_ID"],"retrieved_ids":["SOURCE_ID"],"latency_ms":125.0,"error":null,"error_observed":true,"input_tokens":100,"output_tokens":20}
```

Case IDs must belong to the destination application. Application/model/prompt
versions must match its record. Each batch contains at most one trace per case;
runs explicitly select a batch. Missing traces are insufficient evidence.
Unknown citation/retrieval IDs are retained for fault detection, not trusted.

`error_observed: true` means an error channel was observed, including explicit
success. False/omitted makes the error metric unavailable even if `error` is
null. Latency/tokens must be nonnegative and finite. Costs require both token
counts and both configured per-million prices.

`GET /api/runs/{id}/traces` downloads raw version 1 JSONL for reimport into the
same application. Citation values are versioned source IDs, not document names.

## Export archives

Dashboard/CLI exports cover sources, cases, datasets, trace batches, events and
runs. Snapshot/log exports are archives, not mutable import formats. Case and
raw trace JSONL have validated reimport paths. Dataset checksums exclude
publication ID/time/actor/version and include case revisions and source content.

OpenAPI `/docs` is the executable request schema. Unknown schema fields produce
422; domain errors produce 400. Credentials have no client schema fields.
