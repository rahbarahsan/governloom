# Runtime AI governance: product rationale

Research date: 2026-10-07. The user clarified the product: connect an existing AI
system through a hook, monitor production signals, flag risks and support
mitigation. Vision, RAG, forecasting and other tasks share an integration
contract. Organization-wide inventory is outside this workflow. Connected
application records only scope policies and credentials.

## Evidence and implications

- NIST AI RMF connects measurement with risk management, monitoring and response.
  Our inference: an incident needs evidence, an accountable owner and a recorded
  response. This is voluntary guidance, not certification.
  [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/).
- OWASP documents prompt injection and misinformation as distinct risks. Our
  inference: suspicious instruction patterns and citation identity need separate,
  narrowly described checks; neither proves factual correctness or protection
  against injection.
  [Prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/),
  [Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/).
- Langfuse provides tracing/evaluation; Evidently provides predictive monitoring,
  data quality and statistical drift tests. Our positioning hypothesis is a small
  policy-to-action integration and accountable mitigation across tasks. This is
  not validated customer demand or a claim that competitors lack governance.
  [Langfuse](https://langfuse.com/docs/evaluation/overview),
  [Evidently](https://www.evidentlyai.com/ml-monitoring).
- Ground truth can arrive after predictions. Evidently's older architecture guide
  separates input/prediction signals from subsequent quality measurements. Our
  implementation accepts outcomes linked to predictions rather than treating
  confidence as accuracy.
  [Delayed ground truth](https://docs-old.evidentlyai.com/user-guide/monitoring/batch_monitoring).
- OpenTelemetry defines shared telemetry naming conventions. A future adapter
  should reuse applicable conventions. Our current contract is custom JSON;
  no OTLP or OpenTelemetry compatibility is claimed.
  [OpenTelemetry](https://opentelemetry.io/docs/concepts/semantic-conventions/).

## Architecture decision

Use a common envelope: opaque event/trace IDs, task/phase, model/deployment
versions, timestamp, numeric metrics and optional structured evidence. HTTP
supports any language/provider. Python hooks wrap existing callables and tools;
explicit mappers select telemetry. Binary inputs and provider keys are unnecessary.

Versioned policies evaluate bounded signals synchronously. Receipts distinguish
clear, triggered, not applicable and insufficient evidence. Durable alerts retain
rule evidence and mitigation guidance. Operators record ownership/disposition
with optimistic concurrency and audit history.

Observation records risk without changing predictions. Enforcement requires an
application-side integration: block before input/tool execution or withhold a
flagged output. A collector cannot undo a completed side effect. A requested
block is not proof that a client enforced it.

## Validation and next discovery

Real HTTP and browser tests verify integration behavior, not detector accuracy.
Next, a consenting team should connect its actual deployed service. Measure added
latency, missing telemetry, useful alerts, false positives and time to mitigation.
Agree task-specific thresholds with that team. Forecast quality needs outcomes;
vision accuracy needs labels; RAG grounding needs calibrated evidence checks.
No universal detector or general accuracy claim follows from this implementation.
