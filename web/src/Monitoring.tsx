import { useCallback, useEffect, useRef, useState } from "react";
import { api, date, title } from "./api";
import { Badge } from "./components";
import type { Application } from "./types";

type Rule = {
  id: string;
  name: string;
  detector: string;
  phase: string;
  task_type: string;
  metric?: string;
  comparator?: string;
  threshold?: number;
  baseline?: number;
  window_size?: number;
  allowed?: string[];
  severity: string;
  action: string;
  mitigation: string;
};
type Policy = {
  id: string;
  name: string;
  rules: Rule[];
  actor: string;
  rationale: string;
  expected_events_per_minute: number;
  created_at: string;
};
type Key = { id: string; name: string; active: boolean; created_at: string };
type Check = {
  rule_id: string;
  name: string;
  status: string;
  action: string;
  severity: string;
  mitigation: string;
  evidence: Record<string, unknown>;
};
type RuntimeRow = {
  cursor: number;
  event: {
    event_id: string;
    trace_id: string;
    phase: string;
    task_type: string;
    environment: string;
    model_version: string;
    application_version: string;
    client_mode: string;
    metrics: Record<string, number>;
    text_supplied: boolean;
    text_characters: number | null;
  };
  receipt: {
    action: string;
    checks: Check[];
    received_at: string;
    policy_id: string;
  };
};
type Alert = {
  id: string;
  event_id: string;
  trace_id: string;
  name: string;
  severity: string;
  requested_action: string;
  mitigation: string;
  evidence: Record<string, unknown>;
  status: string;
  owner: string | null;
  revision: number;
  created_at: string;
  rationale?: string;
  task_type: string;
  environment: string;
};
type Incident = {
  id: string;
  name: string;
  environment: string;
  model_version: string;
  count: number;
  status: string;
  owner: string | null;
  revision: number;
  first_seen: string;
  last_seen: string;
  escalations_queued: number;
};
type Agent = {
  id: string;
  status: string;
  received_at: string;
  heartbeat: {
    agent_id: string;
    boot_id: string;
    counters: Record<string, number>;
  };
};
type ActionRecord = {
  id: string;
  action_type: string;
  status: string;
  event_id: string;
  limitation: string;
  verification: {
    actor: string;
    criterion: string;
    evidence_sha256: string;
  } | null;
};

const presets: Record<string, Omit<Rule, "id">> = {
  latency: {
    name: "Slow prediction",
    detector: "metric_threshold",
    phase: "output",
    task_type: "any",
    metric: "latency_ms",
    comparator: "gt",
    threshold: 2000,
    severity: "medium",
    action: "flag",
    mitigation: "Inspect serving latency and consider fallback capacity.",
  },
  vision: {
    name: "Low vision confidence",
    detector: "metric_threshold",
    phase: "output",
    task_type: "vision",
    metric: "confidence",
    comparator: "lt",
    threshold: 0.8,
    severity: "medium",
    action: "review",
    mitigation:
      "Route uncertain predictions to a human or a validated fallback.",
  },
  labels: {
    name: "Unexpected classification label",
    detector: "label_allowlist",
    phase: "output",
    task_type: "classification",
    allowed: ["approved", "rejected"],
    severity: "medium",
    action: "review",
    mitigation:
      "Inspect the unexpected label and route to the application's review path.",
  },
  forecast: {
    name: "Forecast error above tolerance",
    detector: "metric_threshold",
    phase: "outcome",
    task_type: "forecasting",
    metric: "absolute_error",
    comparator: "gt",
    threshold: 10,
    severity: "high",
    action: "flag",
    mitigation:
      "Inspect linked prediction/outcome and review model assumptions.",
  },
  shift: {
    name: "Prediction mean shift",
    detector: "mean_shift",
    phase: "output",
    task_type: "any",
    metric: "prediction",
    baseline: 0,
    threshold: 1,
    window_size: 20,
    severity: "medium",
    action: "flag",
    mitigation:
      "Investigate the distribution change; validate drift with domain-specific tests.",
  },
  rag: {
    name: "Missing or invalid source citations",
    detector: "citation_integrity",
    phase: "output",
    task_type: "rag",
    severity: "high",
    action: "review",
    mitigation: "Withhold unsupported citations and review retrieval evidence.",
  },
  tools: {
    name: "Tool outside allowlist",
    detector: "tool_allowlist",
    phase: "tool",
    task_type: "any",
    allowed: ["search"],
    severity: "high",
    action: "block",
    mitigation: "Deny the tool call and review permission boundaries.",
  },
  secrets: {
    name: "Secret-like output",
    detector: "secrets",
    phase: "output",
    task_type: "any",
    severity: "critical",
    action: "block",
    mitigation:
      "Withhold the response, verify exposure, and rotate any confirmed leaked credential.",
  },
  email: {
    name: "Email-like output",
    detector: "email_exposure",
    phase: "output",
    task_type: "any",
    severity: "medium",
    action: "review",
    mitigation: "Review whether the personal-data disclosure is authorized.",
  },
  injection: {
    name: "Prompt-injection pattern signal",
    detector: "prompt_injection_signal",
    phase: "input",
    task_type: "any",
    severity: "medium",
    action: "flag",
    mitigation:
      "Inspect the suspicious instruction; this pattern signal is not a reliable security verdict.",
  },
  error: {
    name: "Prediction failure",
    detector: "target_error",
    phase: "error",
    task_type: "any",
    severity: "high",
    action: "flag",
    mitigation:
      "Inspect serving health and activate the application's fallback if appropriate.",
  },
};

export default function Monitoring({
  application,
}: {
  application: Application;
}) {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [keys, setKeys] = useState<Key[]>([]);
  const [newKey, setNewKey] = useState("");
  const [keyName, setKeyName] = useState("");
  const [actor, setActor] = useState("");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<ActionRecord[]>([]);
  const [events, setEvents] = useState<RuntimeRow[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("open");
  const cursor = useRef(0);
  const fetching = useRef(false);
  const refresh = useCallback(async () => {
    if (fetching.current) return;
    fetching.current = true;
    try {
      const [p, k, a, feed, grouped, coverage, confirmations] =
        await Promise.all([
          api<Policy | null>(`/applications/${application.id}/monitor-policy`),
          api<Key[]>(`/applications/${application.id}/ingest-keys`),
          api<Alert[]>(
            `/applications/${application.id}/runtime-alerts${status === "all" ? "" : `?status=${status}`}`,
          ),
          api<{ events: RuntimeRow[]; next_cursor: number }>(
            `/applications/${application.id}/runtime-events?after=${cursor.current}&limit=100`,
          ),
          api<Incident[]>(`/applications/${application.id}/runtime-incidents`),
          api<Agent[]>(`/applications/${application.id}/runtime-agents`),
          api<ActionRecord[]>(
            `/applications/${application.id}/runtime-actions`,
          ),
        ]);
      setPolicy(p);
      setKeys(k);
      setAlerts(a);
      setIncidents(grouped);
      setAgents(coverage);
      setActions(confirmations);
      cursor.current = feed.next_cursor;
      if (feed.events.length)
        setEvents((current) => [...current, ...feed.events].slice(-100));
    } finally {
      fetching.current = false;
    }
  }, [application.id, status]);
  useEffect(() => {
    void refresh().catch((error: Error) => setError(error.message));
    const timer = window.setInterval(() => {
      if (!document.hidden)
        void refresh().catch((error: Error) => setError(error.message));
    }, 2000);
    return () => clearInterval(timer);
  }, [refresh]);
  async function action(task: () => Promise<void>, message: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await refresh();
      setNotice(message);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }
  const incomplete = events.reduce(
    (count, row) =>
      count +
      row.receipt.checks.filter(
        (check) => check.status === "insufficient_evidence",
      ).length,
    0,
  );
  return (
    <div className="monitoring">
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert success" role="status">
          {notice}
        </div>
      )}
      <section className="stats">
        <div>
          <span>Active policy</span>
          <strong>{policy ? "Connected" : "Configure"}</strong>
        </div>
        <div>
          <span>Recent events shown</span>
          <strong>{events.length}</strong>
        </div>
        <div>
          <span>Alerts in selected view</span>
          <strong>{alerts.length}</strong>
        </div>
        <div>
          <span>Checks missing evidence</span>
          <strong>{incomplete}</strong>
        </div>
      </section>
      <section className="panel">
        <h2>Connect your AI system</h2>
        <p>
          Use a Python hook or the HTTP event endpoint with any model provider.
          Report the numeric metrics and evidence appropriate to your task;
          images, arrays and audio are not uploaded automatically.
        </p>
        <p className="small muted">
          Text submitted for checks is scanned transiently and is not retained.
          Pattern signals can miss risks or flag benign data. A clear check is
          not proof of safety.
        </p>
        <label>
          Monitoring operator
          <input
            value={actor}
            onChange={(event) => setActor(event.target.value)}
          />
        </label>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void action(async () => {
              const result = await api<{ key: string }>(
                `/applications/${application.id}/ingest-keys`,
                { name: keyName, actor },
              );
              setNewKey(result.key);
            }, "Scoped ingestion key issued. Copy it now; it is not shown again.");
          }}
        >
          <label>
            Connection key name
            <input
              required
              value={keyName}
              onChange={(event) => setKeyName(event.target.value)}
              placeholder="production-service"
            />
          </label>
          <button disabled={busy || !actor.trim()}>Create ingestion key</button>
        </form>
        {newKey && (
          <div className="issued-key">
            <label>
              New ingestion key
              <input readOnly type="password" value={newKey} />
            </label>
            <button
              className="secondary"
              onClick={() =>
                void navigator.clipboard
                  .writeText(newKey)
                  .then(() => setNotice("Key copied."))
              }
            >
              Copy key
            </button>
            <button className="secondary" onClick={() => setNewKey("")}>
              Hide key
            </button>
          </div>
        )}
        {keys.map((key) => (
          <div className="row between" key={key.id}>
            <span>
              {key.name} · {key.active ? "active" : "revoked"}
            </span>
            <button
              className="secondary"
              disabled={busy || !key.active || !actor.trim()}
              onClick={() =>
                void action(async () => {
                  await api(`/ingest-keys/${key.id}/revoke`, { actor });
                }, "Key revoked.")
              }
            >
              Revoke {key.name}
            </button>
          </div>
        ))}
        <details>
          <summary>Python hook integration</summary>
          <pre>{`import os\nfrom governloom.hook import RuntimeHook\n\nhook = RuntimeHook(\n    "http://127.0.0.1:8000",\n    os.environ["GOVERNLOOM_INGEST_KEY"],\n    mode="observe",\n    on_unavailable="raise",\n)\n\n# Wrap your existing callable. Explicitly choose telemetry.\nmonitored_predict = hook.wrap(\n    your_predict_function,\n    task_type="vision",\n    model_version="your-model-version",\n    application_version="your-release",\n    output_mapper=lambda result: {\n        "metrics": {"confidence": float(result.confidence)},\n        "labels": [result.label],\n    },\n)\nresult = monitored_predict(your_input)\n\n# HTTP API: POST /api/runtime/events\n# Authorization: Bearer <your scoped ingestion key>\n# Set mode="enforce" to raise PolicyViolation on block actions.\n# Flags/review requests need application/operator handling.`}</pre>
        </details>
      </section>
      <section className="panel">
        <h2>Active runtime policy</h2>
        {policy ? (
          <>
            <h3>{policy.name}</h3>
            <p className="small">
              {date(policy.created_at)} · version {policy.id.slice(0, 12)} ·{" "}
              {policy.expected_events_per_minute} events/minute limit
            </p>
            {policy.rules.map((rule) => (
              <div className="gate-check" key={rule.id}>
                <strong>{rule.name}</strong>
                <p>
                  {title(rule.detector)} · {rule.task_type} / {rule.phase} ·{" "}
                  {rule.action}
                </p>
                <p className="small">{rule.mitigation}</p>
              </div>
            ))}
          </>
        ) : (
          <p>No active policy. Configure one before sending events.</p>
        )}
        <PolicyForm
          busy={busy}
          actor={actor}
          save={(body) =>
            action(async () => {
              await api(`/applications/${application.id}/monitor-policy`, body);
            }, "New runtime policy activated; historical decisions retain their previous policy.")
          }
        />
      </section>
      <section className="panel">
        <h2>Delivery coverage</h2>
        <p className="small muted">
          Heartbeats are separate from inference traffic. Counters are reported
          by each application; queued events have not yet been accepted.
        </p>
        {!agents.length && (
          <p>No agent heartbeat received. Delivery coverage is unknown.</p>
        )}
        {agents.map((agent) => (
          <details key={agent.id}>
            <summary>
              {agent.heartbeat.agent_id} · {agent.status} · accepted{" "}
              {agent.heartbeat.counters.accepted ?? "unknown"} · dropped{" "}
              {agent.heartbeat.counters.dropped ?? "unknown"}
            </summary>
            <p>
              Boot {agent.heartbeat.boot_id} · last heartbeat{" "}
              {date(agent.received_at)}
            </p>
            <pre>{JSON.stringify(agent.heartbeat.counters, null, 2)}</pre>
          </details>
        ))}
      </section>
      <section className="panel">
        <h2>Grouped incidents</h2>
        <p className="small muted">
          Repeats share an incident within a fixed time window and
          policy/deployment. Individual alerts retain their evidence.
        </p>
        {!incidents.length && <p>No grouped incidents received.</p>}
        {incidents.map((incident) => (
          <IncidentCard
            key={`${incident.id}-${incident.revision}`}
            incident={incident}
            busy={busy}
            actor={actor}
            save={(body) =>
              action(async () => {
                await api(`/runtime-incidents/${incident.id}/review`, body);
              }, "Incident ownership and disposition recorded.")
            }
          />
        ))}
      </section>
      <section className="panel">
        <h2>Application actions</h2>
        <p className="small muted">
          A requested block does not prove enforcement. Acknowledgments are
          application assertions; verification identifies an operator who
          inspected evidence.
        </p>
        {!actions.length && (
          <p>No application action acknowledgment received.</p>
        )}
        {actions.map((record) => (
          <details key={record.id}>
            <summary>
              {title(record.action_type)} · {title(record.status)}
            </summary>
            <p>{record.limitation}</p>
            <p className="small">Event {record.event_id}</p>
            {record.verification && (
              <pre>{JSON.stringify(record.verification, null, 2)}</pre>
            )}
          </details>
        ))}
      </section>
      <section className="panel">
        <div className="row between">
          <h2>Live risk alerts</h2>
          <label>
            Alert status
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {[
                "open",
                "acknowledged",
                "mitigated",
                "false_positive",
                "all",
              ].map((value) => (
                <option key={value} value={value}>
                  {title(value)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!alerts.length && (
          <p className="muted">
            No alerts in this view. Inspect check coverage in the event stream
            before interpreting that as low risk.
          </p>
        )}
        {alerts.map((alert) => (
          <AlertCard
            key={`${alert.id}-${alert.revision}`}
            alert={alert}
            actor={actor}
            busy={busy}
            save={(body) =>
              action(async () => {
                await api(`/runtime-alerts/${alert.id}/review`, body);
              }, "Alert ownership and disposition recorded.")
            }
          />
        ))}
      </section>
      <section className="panel">
        <h2>Live event stream</h2>
        <p className="small muted">
          Refreshes every two seconds while visible. Shows the last 100 fetched
          events; older backlogs are fetched in pages. Requested block actions
          do not prove that a client enforced them.
        </p>
        {!events.length && (
          <p>Waiting for your hooked application to send activity.</p>
        )}
        {events
          .slice()
          .reverse()
          .map((row) => (
            <details className="runtime-event" key={row.cursor}>
              <summary>
                {row.event.task_type} · {row.event.phase} · {row.receipt.action}{" "}
                · {row.event.model_version} · {date(row.receipt.received_at)}
              </summary>
              <p className="small">
                Trace {row.event.trace_id} · {row.event.environment} · client
                mode {row.event.client_mode} · policy{" "}
                {row.receipt.policy_id.slice(0, 12)}
              </p>
              <pre>{JSON.stringify(row.event.metrics, null, 2)}</pre>
              {row.receipt.checks.map((check) => (
                <article className="gate-check" key={check.rule_id}>
                  <div className="row between">
                    <strong>{check.name}</strong>
                    <Badge value={check.status} />
                  </div>
                  <pre>{JSON.stringify(check.evidence, null, 2)}</pre>
                </article>
              ))}
            </details>
          ))}
      </section>
    </div>
  );
}

function PolicyForm({
  busy,
  actor,
  save,
}: {
  busy: boolean;
  actor: string;
  save: (body: unknown) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [rationale, setRationale] = useState("");
  const [limit, setLimit] = useState(600);
  const [heartbeatTimeout, setHeartbeatTimeout] = useState(120);
  const [incidentWindow, setIncidentWindow] = useState(300);
  const [escalateCount, setEscalateCount] = useState(3);
  const [cooldown, setCooldown] = useState(300);
  const [preset, setPreset] = useState("latency");
  const [rules, setRules] = useState<Rule[]>([]);
  function edit(index: number, values: Partial<Rule>) {
    setRules(
      rules.map((rule, i) => (i === index ? { ...rule, ...values } : rule)),
    );
  }
  return (
    <details>
      <summary>Configure and activate a new policy</summary>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save({
            name,
            actor,
            rationale,
            expected_events_per_minute: limit,
            heartbeat_timeout_seconds: heartbeatTimeout,
            incident_window_seconds: incidentWindow,
            escalate_after_count: escalateCount,
            escalation_cooldown_seconds: cooldown,
            rules,
          });
        }}
      >
        <label>
          Runtime policy name
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          Policy rationale
          <textarea
            required
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
          />
        </label>
        <label>
          Event rate limit per minute
          <input
            required
            type="number"
            min={1}
            max={10000}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <div className="row">
          <label>
            Heartbeat timeout (seconds)
            <input
              required
              type="number"
              min={1}
              max={86400}
              value={heartbeatTimeout}
              onChange={(event) =>
                setHeartbeatTimeout(Number(event.target.value))
              }
            />
          </label>
          <label>
            Incident window (seconds)
            <input
              required
              type="number"
              min={1}
              max={86400}
              value={incidentWindow}
              onChange={(event) =>
                setIncidentWindow(Number(event.target.value))
              }
            />
          </label>
          <label>
            Escalate after event count
            <input
              required
              type="number"
              min={1}
              max={10000}
              value={escalateCount}
              onChange={(event) => setEscalateCount(Number(event.target.value))}
            />
          </label>
          <label>
            Escalation cooldown (seconds)
            <input
              required
              type="number"
              min={1}
              max={86400}
              value={cooldown}
              onChange={(event) => setCooldown(Number(event.target.value))}
            />
          </label>
        </div>
        <div className="row">
          <label>
            Rule template
            <select
              value={preset}
              onChange={(event) => setPreset(event.target.value)}
            >
              {Object.entries(presets).map(([key, value]) => (
                <option key={key} value={key}>
                  {value.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="secondary"
            disabled={rules.length >= 30}
            onClick={() =>
              setRules([
                ...rules,
                {
                  ...presets[preset],
                  id: `rule_${crypto.randomUUID().replaceAll("-", "")}`,
                },
              ])
            }
          >
            Add runtime rule
          </button>
        </div>
        <p className="small muted">
          Templates are starting points. Set thresholds and mitigation actions
          for your system. Mean shift is an operational signal, not a
          statistical accuracy guarantee.
        </p>
        {rules.map((rule, index) => (
          <fieldset key={rule.id}>
            <legend>{rule.name}</legend>
            <div className="form-grid">
              <label>
                Rule name
                <input
                  required
                  value={rule.name}
                  onChange={(event) =>
                    edit(index, { name: event.target.value })
                  }
                />
              </label>
              <label>
                Task type
                <select
                  value={rule.task_type}
                  onChange={(event) =>
                    edit(index, { task_type: event.target.value })
                  }
                >
                  {[
                    "any",
                    "vision",
                    "rag",
                    "forecasting",
                    "classification",
                    "generative",
                    "custom",
                  ].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label>
                Event phase
                <select
                  value={rule.phase}
                  onChange={(event) =>
                    edit(index, { phase: event.target.value })
                  }
                >
                  {["any", "input", "output", "tool", "error", "outcome"].map(
                    (value) => (
                      <option key={value}>{value}</option>
                    ),
                  )}
                </select>
              </label>
              <label>
                Risk severity
                <select
                  value={rule.severity}
                  onChange={(event) =>
                    edit(index, { severity: event.target.value })
                  }
                >
                  {["low", "medium", "high", "critical"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label>
                Requested action
                <select
                  value={rule.action}
                  onChange={(event) =>
                    edit(index, { action: event.target.value })
                  }
                >
                  {["flag", "review", "block"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              {rule.metric !== undefined && (
                <>
                  <label>
                    Metric name
                    <input
                      required
                      value={rule.metric}
                      onChange={(event) =>
                        edit(index, { metric: event.target.value })
                      }
                    />
                  </label>
                  <label>
                    Threshold
                    <input
                      required
                      type="number"
                      step="any"
                      value={rule.threshold}
                      onChange={(event) =>
                        edit(index, { threshold: Number(event.target.value) })
                      }
                    />
                  </label>
                </>
              )}
              {rule.detector === "metric_threshold" && (
                <label>
                  Comparison
                  <select
                    value={rule.comparator}
                    onChange={(event) =>
                      edit(index, { comparator: event.target.value })
                    }
                  >
                    {["gt", "gte", "lt", "lte"].map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
              )}
              {rule.detector === "mean_shift" && (
                <>
                  <label>
                    Baseline mean
                    <input
                      required
                      type="number"
                      step="any"
                      value={rule.baseline}
                      onChange={(event) =>
                        edit(index, { baseline: Number(event.target.value) })
                      }
                    />
                  </label>
                  <label>
                    Window observations
                    <input
                      required
                      type="number"
                      min={2}
                      max={1000}
                      value={rule.window_size}
                      onChange={(event) =>
                        edit(index, { window_size: Number(event.target.value) })
                      }
                    />
                  </label>
                </>
              )}
              {rule.allowed && (
                <label>
                  Allowed values (comma separated)
                  <input
                    required
                    value={rule.allowed.join(",")}
                    onChange={(event) =>
                      edit(index, {
                        allowed: event.target.value
                          .split(",")
                          .map((value) => value.trim()),
                      })
                    }
                  />
                </label>
              )}
            </div>
            <label>
              Mitigation guidance
              <textarea
                required
                value={rule.mitigation}
                onChange={(event) =>
                  edit(index, { mitigation: event.target.value })
                }
              />
            </label>
            <button
              type="button"
              className="secondary"
              onClick={() => setRules(rules.filter((_, i) => i !== index))}
            >
              Remove {rule.name}
            </button>
          </fieldset>
        ))}
        <button disabled={busy || !actor.trim() || !rules.length}>
          Activate runtime policy
        </button>
      </form>
    </details>
  );
}

function IncidentCard({
  incident,
  actor,
  busy,
  save,
}: {
  incident: Incident;
  actor: string;
  busy: boolean;
  save: (body: unknown) => void;
}) {
  const [owner, setOwner] = useState(incident.owner ?? "");
  const [status, setStatus] = useState(incident.status);
  const [rationale, setRationale] = useState("");
  return (
    <article className="runtime-incident">
      <h3>
        {incident.name} · {incident.count} events
      </h3>
      <p>
        {incident.environment} · {incident.model_version} ·{" "}
        {title(incident.status)} · {incident.escalations_queued} escalations
        queued
      </p>
      <p className="small">
        First {date(incident.first_seen)} · latest {date(incident.last_seen)}
      </p>
      <details>
        <summary>Assign or review incident</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save({
              actor,
              owner,
              status,
              rationale,
              expected_revision: incident.revision,
            });
          }}
        >
          <label>
            Incident owner
            <input
              required
              maxLength={200}
              value={owner}
              onChange={(event) => setOwner(event.target.value)}
            />
          </label>
          <label>
            Incident disposition
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {["open", "acknowledged", "mitigated", "false_positive"].map(
                (value) => (
                  <option key={value} value={value}>
                    {title(value)}
                  </option>
                ),
              )}
            </select>
          </label>
          <label>
            Incident rationale
            <textarea
              required
              maxLength={4000}
              value={rationale}
              onChange={(event) => setRationale(event.target.value)}
            />
          </label>
          <button disabled={busy || !actor.trim()}>
            Save incident disposition
          </button>
        </form>
      </details>
    </article>
  );
}

function AlertCard({
  alert,
  actor,
  busy,
  save,
}: {
  alert: Alert;
  actor: string;
  busy: boolean;
  save: (body: unknown) => Promise<void>;
}) {
  const [owner, setOwner] = useState(alert.owner ?? "");
  const [status, setStatus] = useState(alert.status);
  const [reason, setReason] = useState(alert.rationale ?? "");
  return (
    <article className="runtime-alert">
      <div className="row between">
        <h3>{alert.name}</h3>
        <Badge value={alert.severity} />
      </div>
      <p>
        {alert.task_type} · {alert.environment} · requested action:{" "}
        {alert.requested_action}
      </p>
      <p>{alert.mitigation}</p>
      <details>
        <summary>Risk evidence</summary>
        <pre>{JSON.stringify(alert.evidence, null, 2)}</pre>
        <small>
          Trace {alert.trace_id} · event {alert.event_id} ·{" "}
          {date(alert.created_at)}
        </small>
      </details>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save({
            actor,
            owner,
            status,
            rationale: reason,
            expected_revision: alert.revision,
          });
        }}
      >
        <div className="form-grid">
          <label>
            Alert owner
            <input
              required
              value={owner}
              onChange={(event) => setOwner(event.target.value)}
            />
          </label>
          <label>
            Alert disposition
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {["open", "acknowledged", "mitigated", "false_positive"].map(
                (value) => (
                  <option key={value} value={value}>
                    {title(value)}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>
        <label>
          Disposition rationale
          <textarea
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        <button disabled={busy || !actor.trim()}>Save alert disposition</button>
      </form>
    </article>
  );
}
