# Decisions

- SQLite + SQLAlchemy stores versioned JSON domain records, with separate run
  and result tables for atomic leases and unique (run, case) finalization.
  Single user and one local worker are the supported deployment scope.
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
