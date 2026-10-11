export type Task = "vision" | "rag" | "forecasting" | "classification" | "generative" | "custom";
export type Phase = "input" | "output" | "tool" | "error" | "outcome";
export type Telemetry = {metrics?: Record<string, number>; labels?: string[]; text?: string; tool_name?: string; citations?: string[]; source_ids?: string[]; related_event_id?: string; outcome_due_at?: string; error_type?: string; grounding?: Record<string, unknown>};
export type Scope = {task_type: Task; model_version: string; application_version: string; environment?: string};
export type RuntimeEvent = Scope & Telemetry & {phase: Phase; trace_id: string; event_id?: string; occurred_at?: string};
export type Receipt = {event_id: string; action: "allow" | "flag" | "review" | "block" | "unavailable"; checks: unknown[]; alert_ids?: string[]; incident_ids?: string[]; duplicate?: boolean};
export type BatchResult = {schema_version: 1; results: {event_id: string; status: number; receipt?: Receipt; error?: string}[]};

export function prepareEvent(fields: RuntimeEvent): RuntimeEvent & {event_id: string; occurred_at: string} {
  if (fields.metrics && Object.values(fields.metrics).some(value => !Number.isFinite(value))) throw new Error("Metrics must be finite numbers");
  // Deep-copy selected telemetry so caller mutation cannot change a retry body.
  return JSON.parse(JSON.stringify({...fields, event_id: fields.event_id ?? crypto.randomUUID(), occurred_at: fields.occurred_at ?? new Date().toISOString()}));
}

export class MonitoringUnavailable extends Error {
  constructor(message: string, public status?: number, public retryable = true) {super(message);}
}
export class PolicyViolation extends Error {
  constructor(public receipt: Receipt) {super("Runtime policy requested a block; inspect its GovernLoom alert");}
}

export class RuntimeHook {
  readonly endpoint: string;
  readonly mode: "observe" | "enforce";
  readonly onUnavailable: "raise" | "continue";
  readonly timeoutMs: number;
  unavailableCount = 0;
  private key: string;
  constructor(endpoint: string, key: string, options: {mode?: "observe" | "enforce"; onUnavailable?: "raise" | "continue"; timeoutMs?: number} = {}) {
    const url = new URL(endpoint);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash || (url.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))) throw new Error("Use an HTTPS collector; HTTP is restricted to loopback");
    if (!key.startsWith("gl_") || /[\r\n]/.test(key)) throw new Error("Use a GovernLoom ingestion key");
    this.mode = options.mode ?? "observe"; this.onUnavailable = options.onUnavailable ?? "raise"; this.timeoutMs = options.timeoutMs ?? 1000;
    if (!["observe", "enforce"].includes(this.mode) || !["raise", "continue"].includes(this.onUnavailable) || !Number.isFinite(this.timeoutMs) || this.timeoutMs <= 0 || this.timeoutMs > 30000) throw new Error("Invalid runtime hook options");
    this.endpoint = endpoint.replace(/\/$/, ""); this.key = key;
  }
  private async request(path: string, body: unknown): Promise<unknown> {
    try {
      const response = await fetch(this.endpoint + path, {method: "POST", redirect: "manual", signal: AbortSignal.timeout(this.timeoutMs), headers: {Authorization: "Bearer " + this.key, "Content-Type": "application/json"}, body: JSON.stringify(body)});
      if (response.status !== 200) throw new MonitoringUnavailable(`Collector rejected request (HTTP ${response.status})`, response.status, [408, 429].includes(response.status) || response.status >= 500);
      const reader = response.body?.getReader(); if (!reader) throw new MonitoringUnavailable("Collector returned no receipt", undefined, false);
      const chunks: Uint8Array[] = []; let size = 0;
      try {
        while (true) {const {done, value} = await reader.read(); if (done) break; size += value.length; if (size > 1_000_000) throw new MonitoringUnavailable("Collector receipt exceeds size limit", undefined, false); chunks.push(value);}
      } finally {await reader.cancel();}
      const data = new Uint8Array(size); let position = 0; for (const chunk of chunks) {data.set(chunk, position); position += chunk.length;}
      try {return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(data));} catch {throw new MonitoringUnavailable("Collector returned invalid JSON", undefined, false);}
    } catch (error) {if (error instanceof MonitoringUnavailable) throw error; throw new MonitoringUnavailable("Collector unavailable");}
  }
  async emit(fields: RuntimeEvent, enforce = true): Promise<Receipt> {
    const event = {...prepareEvent(fields), client_mode: this.mode};
    if (event.metrics && Object.values(event.metrics).some(value => !Number.isFinite(value))) throw new Error("Metrics must be finite numbers");
    let receipt: Receipt;
    try {
      receipt = await this.request("/api/runtime/events", event) as Receipt;
      if (!receipt || receipt.event_id !== event.event_id || !["allow", "flag", "review", "block"].includes(receipt.action)) throw new MonitoringUnavailable("Collector returned an invalid receipt", undefined, false);
    } catch (error) {
      if (!(error instanceof MonitoringUnavailable)) throw error;
      this.unavailableCount++;
      if (this.onUnavailable === "raise") throw error;
      return {event_id: event.event_id, action: "unavailable", checks: []};
    }
    if (enforce && this.mode === "enforce" && receipt.action === "block") throw new PolicyViolation(receipt);
    return receipt;
  }
  async emitBatch(events: RuntimeEvent[]): Promise<BatchResult> {
    if (this.mode !== "observe" || events.length < 1 || events.length > 100) throw new Error("Batch delivery requires observe mode and 1..100 events");
    const bodies = events.map(event => ({...prepareEvent(event), client_mode: "observe"}));
    return await this.request("/api/runtime/events/batch", {events: bodies}) as BatchResult;
  }
  async acknowledgeAction(fields: {alert_id: string; action_type: "withheld" | "review_queued" | "tool_denied" | "fallback_selected"; evidence_id: string}): Promise<unknown> {
    return this.request("/api/runtime/actions", fields);
  }
  wrap<A extends unknown[], R>(target: (...args: A) => Promise<R>, scope: Scope, mappers: {input?: (...args: A) => Telemetry | Promise<Telemetry>; output?: (result: R) => Telemetry | Promise<Telemetry>} = {}): (...args: A) => Promise<R> {
    return async (...args: A) => {
      const trace_id = crypto.randomUUID();
      await this.emit({...await mappers.input?.(...args), ...scope, trace_id, phase: "input"});
      const started = performance.now(); let result: R;
      try {result = await target(...args);} catch (error) {
        try {await this.emit({...scope, trace_id, phase: "error", error_type: error instanceof Error ? error.name : "TargetError", metrics: {latency_ms: performance.now() - started}}, false);} catch {}
        throw error;
      }
      const after = await mappers.output?.(result);
      await this.emit({...after, ...scope, trace_id, phase: "output", metrics: {...after?.metrics, latency_ms: performance.now() - started}});
      return result;
    };
  }
  wrapTool<A extends unknown[], R>(target: (...args: A) => Promise<R>, scope: Scope, toolName: string): (...args: A) => Promise<R> {
    return async (...args: A) => {await this.emit({...scope, trace_id: crypto.randomUUID(), phase: "tool", tool_name: toolName}); return target(...args);};
  }
}
