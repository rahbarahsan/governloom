# Decisions

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
