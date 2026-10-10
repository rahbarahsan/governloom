# GovernLoom Node runtime hook

Node 22+, TypeScript declarations, native fetch; no runtime npm dependencies.
Build with `npm ci && npm run build`, then install this directory in your application
with `npm install /path/to/governloom/sdks/typescript`. This source package has not
been published to npm.

```typescript
import {RuntimeHook, prepareEvent} from "@governloom/runtime";
const hook = new RuntimeHook(endpoint, ingestionKey, {mode: "observe"});
const event = prepareEvent({trace_id: "opaque-trace", phase: "output", task_type: "custom",
  model_version: "model-v1", application_version: "service-v1", metrics: {latency_ms: 12}});
const receipt = await hook.emit(event);
```

Keep keys server-side. HTTPS is required remotely; loopback HTTP is for development.
`wrap` awaits input/output decisions around an async target; `wrapTool` checks before
its side effect. Enforce mode throws `PolicyViolation` on a block; collector failures
raise by default. Explicit `onUnavailable: "continue"` makes missing coverage visible
through an unavailable receipt and counter. No target retry, binary upload or model
inference occurs inside this SDK.

For observation batches use `emitBatch` with 1–100 events. Prepare bodies once before
replay and inspect every per-item status. Batch observation cannot enforce a call's
boundary. The [repository integration guide](../../docs/INTEGRATIONS.md) covers
application review/acknowledgment, linked outcomes and the versioned schema.
