# Decisions

- v0.6 explores one explicitly connected application before asking the owner to
  confirm its inferred behavior. Local inspection never executes target code;
  optional semantic analysis is bounded and tool-disabled. Exact source references
  verify provenance, not interpretation. Generated scenarios remain unreviewed.
- Evidence, owner corrections and calibration plans are immutable. Dataset hashes
  normalize equivalent integral JSON numbers so Python/JavaScript round trips
  preserve mathematical values. Prompt/answer bodies are excluded from stored trace
  projections; selected source text is retained privately for review.
- Automatic recipes select only on calibration data. Forecast point residuals are
  empirical; classification gates require confirmed labels; RAG identity checks
  never imply semantic support. Held-out budget violations remain visible.
- Generated policy activation is transactional, idempotent and observation-only.
  Current-policy and current-understanding checks prevent stale proposals from
  silently taking effect. Version-bound rules expose insufficient evidence when
  a different live model/application is observed. Real runtime versions are required
  by the prepared mapper; historical versions are never stamped onto new outputs.
- v0.5 numeric deadlines track declared feedback coverage, with collector receipt
  time for lateness. They do not infer forecast error from missing actuals.
  The bounded watchdog creates one frozen-policy incident across restart/races;
  a received actual resolves coverage without silently closing operator review.
- Forecast gates score maxima in chronological non-overlapping calendar blocks.
  Missing calibration months are rejected and missing held-out months remain
  unavailable in their block. Dependence and revised data invalidate nominal
  probability claims; this is an empirical gate, not formal block randomization.
- Signing rotation emits both signatures during a bounded overlap; emergency
  revocation affects future dispatches. Recovery snapshots the database plus its
  referenced secrets; retention removes only delivered notifications for closed
  incidents, preserves audit/evidence and supplies no total storage quota.
- Broader RAG labels require explicit contradiction for unsupported claims and
  preserve unknowns. Frozen prompt/schema replay corrects a corpus-selection bug
  without additional model calls or regenerating the natural answer. Authored
  controls and the same generator/judge model do not establish independent quality.
- An owned standalone application in a fresh installed-wheel environment proves
  public integration and packaging. It does not substitute for independent human
  onboarding feedback. Container CI verifies a separate installed deployment path.

- v0.4 signed notifications use Standard Webhooks 1.0 HMAC-SHA256 (ID, current
  attempt timestamp and immutable raw body). Transactional per-destination
  deliveries retain one ID/body across restart/replay; receivers must persistently
  deduplicate. Receipt loss means at-least-once delivery, not exactly-once HTTP.
- Destination URLs must match a collector-host allowlist. Remote HTTPS resolves
  exclusively to public addresses and dials a validated address while retaining
  original TLS SNI/Host. Redirects/proxies are disabled. Explicit literal loopback
  HTTP supports owned local receivers. Signing secrets live in a separate private
  host directory; full recovery requires both database and secret backup.
- Webhook notification bodies contain incident IDs, severity and counts only;
  they exclude prompts, source passages, reviewer names and credentials. Separate
  workers isolate network latency from ingestion. Eight attempts/24 hours bound
  automatic delivery; dead-letter replay is an authenticated, audited operation.
  A 2xx receipt confirms receiver acceptance, never completed mitigation.
- Runtime batches accept at most 100 observation events with per-item results.
  Enforcement stays synchronous at each application boundary. Clients prepare IDs
  and timestamps once before replay. Async Python and Node SDKs retain explicit
  outage behavior and never automatically upload inputs or retry side effects.

- Evidence detectors require immutable approved profiles with declared scope,
  source/reference hashes and grouped calibration results. Upstream judgments
  remain replaceable/provider independent; quote checks verify provenance, not
  semantic entailment. Text and explanations never enter collector storage.
- Distribution checks use finite-sample ECDF distance and conservative DKW/union
  bounds with non-overlapping windows and lifetime alpha spending per profile.
  Known dependent forecast replay is labeled empirical, not nominal significance.
  Experimental grounding/distribution findings can flag/review, not block.

- Durable observation freezes metadata in a separate SQLite outbox and preserves
  pending work on shutdown; text checks remain transient. Exact collector replay
  handles producer death after remote commit. Logical limits are not disk quotas.
- Named operator mode uses local accounts, hashed revocable sessions and explicit
  application grants. Authentication supplies audit actors, not request claims.
  Existing account databases refuse unauthenticated startup. Local development
  and ingestion credentials remain separate access paths.

- SQLite + SQLAlchemy stores versioned JSON domain records, with separate run
  and result tables for atomic leases and unique (run, case) finalization.
  The legacy evaluation path supports one local worker. The runtime collector
  uses serialized SQLite ingestion for controlled private pilots.
- Frozen datasets embed cases and sources; runs also snapshot application,
  target, traces, evaluator settings and limits. Later review cannot change
  published evidence. All timestamps use UTC.
- The no-key generator accepts an explicit pipe-separated fact format inside
  UTF-8 Markdown/text. Arbitrary prose is importable for manual cases, but
  automatic semantic generation and judging stay unavailable.
- The reference target uses lexical retrieval and literal answers. Literal
  agreement and citation checks have narrow interpretations; no overall score
  or semantic grounding claim is produced.
- The fixed 40-case JSONL suite is separate from runtime candidate generation.
  Its hashes/passages are validated rather than regenerated when sources change.
  It has repository-authored template provenance, not independent human labels.
- SQLite write transactions serialize dataset version assignment. Worker state
  changes fence the lease owner before reading or finalizing a case. Hard process
  termination is tested in addition to simulated lease recovery.
- No API route enables paid work. Provider interfaces reserve a bounded request
  before a trusted adapter is called; failed requests retain reservations. Only a
  no-network fake exercises this seam. Judge calibration remains unavailable.

- Runtime integrations wrap existing customer callables or emit HTTP events,
  independent of provider and model modality. Mappers select telemetry; binary
  artifacts are not auto-uploaded. Main event text is scanned transiently.
- Runtime decisions and alerts commit atomically with the event. Stable event IDs
  make exact replays idempotent; different payloads with the same ID are rejected.
  Policies are immutable and retained; scoped key hashes authorize ingestion,
  while a separate admin token protects private remote administration.
- Observe/enforce and collector-outage behavior are explicit application choices.
  Tool checks happen before the side effect. Requested actions and operator
  dispositions are not evidence of verified enforcement or completed mitigation.
