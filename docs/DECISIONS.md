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
