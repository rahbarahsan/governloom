import { useCallback, useEffect, useState, useContext } from "react";
import { AuthContext } from "./AuthContext";
import {
  api,
  date,
  number,
  title,
  setAdminToken,
  downloadEvidence,
} from "./api";
import Monitoring from "./Monitoring";
import {
  ApplicationForm,
  Badge,
  CaseEditor,
  Evidence,
  Imports,
} from "./components";
import type {
  Application,
  Case,
  Comparison,
  Dataset,
  Metric,
  ReviewEvent,
  Run,
  Source,
  TraceBatch,
} from "./types";

type View = "monitoring" | "applications" | "datasets" | "runs" | "findings";
const targets = [
  "clean",
  "irrelevant_retrieval",
  "outdated_source",
  "unsupported_statement",
  "invalid_citation",
  "timeout",
  "imported",
];

export default function App() {
  const identity = useContext(AuthContext);
  const [view, setView] = useState<View>("monitoring");
  const [accessToken, setAccessToken] = useState("");
  const [applications, setApplications] = useState<Application[]>([]);
  const [appId, setAppId] = useState(
    localStorage.getItem("governloom-app") ?? "",
  );
  const [sources, setSources] = useState<Source[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [batches, setBatches] = useState<TraceBatch[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [selectedCase, setSelectedCase] = useState("");
  const [caseFilter, setCaseFilter] = useState("all");
  const [actor, setActor] = useState(
    identity?.username ?? localStorage.getItem("governloom-reviewer") ?? "",
  );
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [datasetId, setDatasetId] = useState("");
  const [target, setTarget] = useState("clean");
  const [split, setSplit] = useState("held_out");
  const [sampleSize, setSampleSize] = useState(100);
  const [maxRequests, setMaxRequests] = useState(100);
  const [samplingSeed, setSamplingSeed] = useState(0);
  const [traceBatchId, setTraceBatchId] = useState("");
  const [selectedMetrics, setSelectedMetrics] = useState<string[] | null>(null);
  const [inputPrice, setInputPrice] = useState("");
  const [outputPrice, setOutputPrice] = useState("");
  const [leftRun, setLeftRun] = useState("");
  const [rightRun, setRightRun] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [findingFilter, setFindingFilter] = useState("failed");
  const application = applications.find((a) => a.id === appId);

  const refresh = useCallback(async () => {
    const apps = await api<Application[]>("/applications");
    setApplications(apps);
    if (appId && !apps.some(app => app.id === appId) || !appId && apps.length) {
      setAppId(apps[0]?.id ?? "");
      return;
    }
    if (!appId) return;
    const [s, c, d, m, r, e, b] = await Promise.all([
      api<Source[]>(`/applications/${appId}/sources`),
      api<Case[]>(`/applications/${appId}/cases`),
      api<Dataset[]>(`/applications/${appId}/datasets`),
      api<Metric[]>(`/applications/${appId}/metrics`),
      api<Run[]>(`/runs?application_id=${appId}`),
      api<ReviewEvent[]>(`/applications/${appId}/review-events`),
      api<TraceBatch[]>(`/applications/${appId}/trace-batches`),
    ]);
    setSources(s);
    setCases(c);
    setDatasets(d.sort((a, b) => b.version - a.version));
    setMetrics(m);
    setRuns(r);
    setEvents(e);
    setBatches(b);
    setActiveRun((previous) => {
      const latest = previous && r.find((run) => run.id === previous.id);
      return previous && latest
        ? { ...previous, ...latest, snapshot: previous.snapshot }
        : previous;
    });
  }, [appId]);

  useEffect(() => {
    void refresh().catch((e) => setError(String(e.message)));
  }, [refresh]);
  useEffect(() => {
    localStorage.setItem("governloom-app", appId);
    setSelectedCase("");
    setActiveRun(null);
    setDatasetId("");
    setComparison(null);
    setLeftRun("");
    setRightRun("");
    setSelectedMetrics(null);
  }, [appId]);
  useEffect(() => {
    localStorage.setItem("governloom-reviewer", actor);
  }, [actor]);
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (!runs.some((r) => ["queued", "running"].includes(r.status))) return;
      void refresh().catch((e) => setError(e.message));
      if (activeRun)
        void api<Run>(`/runs/${activeRun.id}`)
          .then(setActiveRun)
          .catch((e) => setError(e.message));
    }, 1000);
    return () => clearInterval(interval);
  }, [runs, activeRun, refresh]);

  async function perform(task: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  async function loadRun(id: string) {
    try {
      setActiveRun(await api<Run>(`/runs/${id}`));
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }
  const approved = cases.filter((c) => c.review_status === "approved").length;
  const pending = cases.filter((c) => c.review_status === "unreviewed").length;
  const currentCase =
    cases.find((c) => c.id === selectedCase) ??
    cases.find((c) => caseFilter === "all" || c.review_status === caseFilter);
  const selectedDataset =
    datasets.find((d) => d.id === datasetId) ?? datasets[0];

  return (
    <div
      className="shell"
      onClick={(event) => {
        const link = (event.target as HTMLElement).closest("a");
        if (
          link &&
          link.origin === window.location.origin &&
          link.pathname.startsWith("/api/")
        ) {
          event.preventDefault();
          void downloadEvidence(link.pathname + link.search).catch(
            (error: Error) => setError(error.message),
          );
        }
      }}
    >
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("applications");
          }}
        >
          <span className="brand-mark">G</span> GovernLoom
        </a>
        <div className="sidebar-sub">RUNTIME GOVERNANCE</div>
        <nav aria-label="Main navigation">
          {(
            [
              "monitoring",
              "applications",
              "datasets",
              "runs",
              "findings",
            ] as View[]
          ).map((tab, i) => (
            <button
              key={tab}
              className={view === tab ? "nav active" : "nav"}
              onClick={() => setView(tab)}
              aria-current={view === tab ? "page" : undefined}
            >
              <span>0{i}</span>
              {title(tab)}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="dot" /> Local workspace
          <p>
            Self-hosted · SQLite
            <br />
            Hooks · policies · risk alerts
          </p>
          <span className="version">Release 0.2 · runtime foundation</span>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <span className="muted">Workspace / </span>
            {application?.name ?? "Get started"}
          </div>
          <label className="app-switch">
            Application
            <select
              aria-label="Active application"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
            >
              <option value="">Select an application</option>
              {applications.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </label>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {application?.demo
                  ? "FICTIONAL DEMO WORKSPACE"
                  : view === "monitoring"
                    ? "RUNTIME AI GOVERNANCE"
                    : "LOCAL EVALUATION"}
              </div>
              <h1>
                {view === "monitoring"
                  ? "Monitor your AI in operation."
                  : view === "applications"
                    ? "Start with evidence."
                    : view === "datasets"
                      ? "Make the labels reviewable."
                      : view === "runs"
                        ? "Measure what you can prove."
                        : "Follow the evidence."}
              </h1>
              <p className="muted">
                {view === "monitoring"
                  ? "Connect your system, flag policy risks, and track mitigation as events arrive."
                  : view === "applications"
                    ? "Define your application, import sources, and choose useful measurements."
                    : view === "datasets"
                      ? "Review candidates before freezing a version for evaluation."
                      : view === "runs"
                        ? "Run a bounded sample against an immutable dataset, then compare results."
                        : "Inspect individual failures, unavailable checks, and source passages."}
              </p>
            </div>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => void perform(refresh, "Workspace refreshed.")}
            >
              Refresh
            </button>
          </div>
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button className="text-button" onClick={() => setError("")}>
                Dismiss
              </button>
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              {notice}
            </div>
          )}
          {!identity && <details className="panel collector-access">
            <summary>Collector access</summary>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setAdminToken(accessToken);
                void perform(refresh, "Collector access updated.");
              }}
            >
              <label>
                Admin access token
                <input
                  type="password"
                  autoComplete="off"
                  value={accessToken}
                  onChange={(event) => setAccessToken(event.target.value)}
                />
              </label>
              <p className="small muted">
                Required for a privately hosted collector configured with an
                admin token. Kept only in this page's memory.
              </p>
              <button className="secondary">Connect to collector</button>
            </form>
          </details>}
          {!application && (
            <section className="welcome panel">
              <div className="eyebrow">CONNECT YOUR EXISTING SYSTEM</div>
              <h2>Flag risks while your AI is running.</h2>
              <p>
                Create an application connection below, configure a runtime
                policy, and install a hook in your inference or tool-call path.
                Vision, forecasting, RAG and custom tasks share the same event
                API.
              </p>
              <button
                disabled={busy}
                onClick={() =>
                  void perform(async () => {
                    const a = await api<Application>("/demo", {});
                    setAppId(a.id);
                  }, "Demo sources and unreviewed fixtures loaded.")
                }
              >
                Load no-key demo
              </button>
              <p className="muted small">
                Literal retrieval and template candidates. No independent human
                validation or semantic judge.
              </p>
            </section>
          )}
          {view === "monitoring" && application && (
            <Monitoring key={application.id} application={application} />
          )}
          {(view === "applications" ||
            (view === "monitoring" && !application)) && (
            <>
              <ApplicationForm
                create={(body) =>
                  perform(async () => {
                    const a = await api<Application>("/applications", body);
                    setAppId(a.id);
                  }, "Application created.")
                }
              />
              {application && (
                <>
                  {!application.demo && (
                    <div className="panel row between">
                      <p className="muted small" style={{ margin: 0 }}>
                        Explore the bundled fictional corpus in a separate
                        application.
                      </p>
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() =>
                          void perform(async () => {
                            const demo = await api<Application>("/demo", {});
                            setAppId(demo.id);
                          }, "Demo sources and unreviewed fixtures loaded.")
                        }
                      >
                        Load no-key demo
                      </button>
                    </div>
                  )}
                  <section className="stats">
                    <div>
                      <span>Source versions</span>
                      <strong>{sources.length}</strong>
                    </div>
                    <div>
                      <span>Candidate cases</span>
                      <strong>{cases.length}</strong>
                    </div>
                    <div>
                      <span>Awaiting review</span>
                      <strong>{pending}</strong>
                    </div>
                    <div>
                      <span>Frozen versions</span>
                      <strong>{datasets.length}</strong>
                    </div>
                  </section>
                  <section className="panel">
                    <div className="row between">
                      <h2>{application.name}</h2>
                      {application.demo && <Badge value="demo" />}
                    </div>
                    <p>{application.purpose}</p>
                    <p className="muted">{application.expected_behavior}</p>
                    <div className="tags">
                      <span>Owner: {application.owner}</span>
                      <span>Application {application.application_version}</span>
                      <span>Model {application.model_version}</span>
                      <span>Prompt {application.prompt_version}</span>
                    </div>
                  </section>
                  <Imports application={application} perform={perform} />
                  <section className="panel">
                    <div className="row between">
                      <h2>Source library</h2>
                      <a href={`/api/export/source?application_id=${appId}`}>
                        Export JSONL ↗
                      </a>
                    </div>
                    {!sources.length && (
                      <p className="empty">Import a source to begin.</p>
                    )}
                    {sources.map((s) => (
                      <details className="source-row" key={s.id}>
                        <summary>
                          <strong>{s.filename}</strong>
                          <span>
                            v{s.version} · {s.content.length} characters ·{" "}
                            {date(s.created_at)}
                          </span>
                        </summary>
                        <pre className="source-text">{s.content}</pre>
                        <small>
                          ID {s.id}
                          <br />
                          SHA-256 {s.content_hash}
                        </small>
                      </details>
                    ))}
                  </section>
                  <div className="section-heading">
                    <h2>Recommended measurements</h2>
                    <span className="muted small">
                      Prerequisites determine availability
                    </span>
                  </div>
                  <div className="metric-grid">
                    {metrics.map((m) => (
                      <article className="panel metric" key={m.id}>
                        <div className="row between">
                          <h3>{title(m.id)}</h3>
                          <Badge value={m.state} />
                        </div>
                        <p>{m.purpose}</p>
                        <details>
                          <summary>Why this applies</summary>
                          <p>{m.reason}</p>
                          <p>
                            <strong>Needs:</strong>{" "}
                            {m.required_inputs.join(", ")}
                          </p>
                          <p>
                            <strong>Method:</strong> {m.method} · {m.direction}{" "}
                            is better
                            {m.threshold !== null
                              ? ` · threshold ${m.threshold}`
                              : " · observation only"}
                          </p>
                          <p className="muted">{m.limitations}</p>
                        </details>
                      </article>
                    ))}
                  </div>
                  <button onClick={() => setView("datasets")}>
                    Continue to dataset review →
                  </button>
                </>
              )}
            </>
          )}
          {application && view === "datasets" && (
            <>
              <section className="stats">
                <div>
                  <span>Approved</span>
                  <strong>{approved}</strong>
                </div>
                <div>
                  <span>Unreviewed</span>
                  <strong>{pending}</strong>
                </div>
                <div>
                  <span>Rejected</span>
                  <strong>{cases.length - approved - pending}</strong>
                </div>
                <div>
                  <span>Scenario categories</span>
                  <strong>
                    {new Set(cases.map((c) => c.category)).size} / 6
                  </strong>
                </div>
              </section>
              <div className="panel">
                <div className="row between">
                  <h2>Review & publish</h2>
                  <a href={`/api/export/case?application_id=${appId}`}>
                    Export cases ↗
                  </a>
                </div>
                <p className="muted small">
                  Approval records your decision; it does not imply independent
                  validation. Published cases and source hashes are frozen.
                  Edits create a new revision and require a new publication.
                </p>
                <div className="row wrap">
                  <label>
                    Reviewer name
                    <input
                      value={actor}
                      onChange={(e) => setActor(e.target.value)}
                      placeholder="Your name"
                    />
                  </label>
                  <button
                    className="secondary"
                    disabled={busy || !actor.trim() || !pending}
                    onClick={() =>
                      void perform(async () => {
                        for (const c of cases.filter(
                          (c) => c.review_status === "unreviewed",
                        ))
                          await api(`/cases/${c.id}/review`, {
                            actor,
                            expected_revision: c.revision,
                            decision: "approved",
                          });
                      }, "Remaining candidates approved by the named reviewer.")
                    }
                  >
                    Approve remaining {pending} cases
                  </button>
                  <button
                    disabled={busy || !approved || !actor.trim()}
                    onClick={() =>
                      void perform(async () => {
                        const d = await api<Dataset>(
                          `/applications/${appId}/datasets`,
                          { actor },
                        );
                        setDatasetId(d.id);
                      }, "Immutable dataset published.")
                    }
                  >
                    Publish approved dataset
                  </button>
                </div>
              </div>
              <div className="tags category-coverage">
                {Array.from(new Set(cases.map((c) => c.category)))
                  .sort()
                  .map((cat) => (
                    <span key={cat}>
                      {title(cat)} ·{" "}
                      {cases.filter((c) => c.category === cat).length}
                    </span>
                  ))}
              </div>
              {cases.length ? (
                <div className="review-layout">
                  <section className="panel case-list">
                    <div className="row between">
                      <h3>Candidate queue</h3>
                      <select
                        aria-label="Review filter"
                        value={caseFilter}
                        onChange={(e) => {
                          setCaseFilter(e.target.value);
                          setSelectedCase("");
                        }}
                      >
                        <option value="all">All cases</option>
                        <option value="unreviewed">Unreviewed</option>
                        <option value="approved">Approved</option>
                        <option value="rejected">Rejected</option>
                      </select>
                    </div>
                    {cases
                      .filter(
                        (c) =>
                          caseFilter === "all" ||
                          c.review_status === caseFilter,
                      )
                      .map((c) => (
                        <button
                          className={`case-item ${currentCase?.id === c.id ? "selected" : ""}`}
                          key={c.id}
                          onClick={() => setSelectedCase(c.id)}
                        >
                          <span>{c.question}</span>
                          <div className="row between">
                            <small>
                              {title(c.category)} · {c.split}
                            </small>
                            <Badge value={c.review_status} />
                          </div>
                        </button>
                      ))}
                  </section>
                  {currentCase && (
                    <CaseEditor
                      key={`${currentCase.id}-${currentCase.revision}`}
                      item={currentCase}
                      sources={sources}
                      actor={actor}
                      events={events}
                      save={(id, body) =>
                        perform(
                          () => api(`/cases/${id}/review`, body),
                          "Case revision saved and decision recorded.",
                        )
                      }
                    />
                  )}
                </div>
              ) : (
                <p className="empty panel">
                  Generate structured candidates or import manually authored
                  JSONL cases.
                </p>
              )}
              <section className="panel">
                <div className="row between">
                  <h2>Frozen dataset versions</h2>
                  <a href={`/api/export/dataset?application_id=${appId}`}>
                    Export snapshots ↗
                  </a>
                </div>
                {datasets.length ? (
                  datasets.map((d) => (
                    <div className="dataset-row" key={d.id}>
                      <div>
                        <strong>
                          Version {d.version} · {d.cases.length} approved cases
                        </strong>
                        <p className="muted small">
                          {date(d.created_at)} · {d.actor}
                          <br />
                          {
                            d.cases.filter((c) => c.split === "held_out").length
                          }{" "}
                          held-out /{" "}
                          {
                            d.cases.filter((c) => c.split === "calibration")
                              .length
                          }{" "}
                          calibration /{" "}
                          {
                            d.cases.filter((c) => c.split === "exploratory")
                              .length
                          }{" "}
                          exploratory
                        </p>
                        <code>SHA-256 {d.checksum}</code>
                      </div>
                      <button
                        className="secondary"
                        onClick={() => {
                          setDatasetId(d.id);
                          setView("runs");
                        }}
                      >
                        Evaluate v{d.version} →
                      </button>
                    </div>
                  ))
                ) : (
                  <p className="empty">No dataset published yet.</p>
                )}
              </section>
            </>
          )}
          {application && view === "runs" && (
            <>
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  void perform(async () => {
                    if (!selectedDataset)
                      throw new Error("Publish a dataset first.");
                    const run = await api<Run>("/runs", {
                      dataset_id: selectedDataset.id,
                      target,
                      split,
                      sample_size: sampleSize,
                      max_requests: maxRequests,
                      sampling_seed: samplingSeed,
                      spending_cap: 0,
                      trace_batch_id:
                        target === "imported" ? traceBatchId : null,
                      metrics: selectedMetrics,
                      input_price_per_million:
                        inputPrice === "" ? null : Number(inputPrice),
                      output_price_per_million:
                        outputPrice === "" ? null : Number(outputPrice),
                    });
                    setActiveRun(run);
                  }, "Evaluation queued for the local worker.");
                }}
              >
                <div className="row between">
                  <h2>New evaluation</h2>
                  <Badge value="local" />
                </div>
                <div className="form-grid">
                  <label>
                    Frozen dataset
                    <select
                      aria-label="Frozen dataset"
                      required
                      value={selectedDataset?.id ?? ""}
                      onChange={(e) => setDatasetId(e.target.value)}
                    >
                      <option value="">Choose a dataset</option>
                      {datasets.map((d) => (
                        <option key={d.id} value={d.id}>
                          Version {d.version} · {d.cases.length} cases
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Target
                    <select
                      aria-label="Target"
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                    >
                      {targets.map((t) => (
                        <option key={t} value={t}>
                          {title(t)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Dataset split
                    <select
                      aria-label="Dataset split"
                      value={split}
                      onChange={(e) => setSplit(e.target.value)}
                    >
                      {["held_out", "calibration", "exploratory", "all"].map(
                        (s) => (
                          <option key={s} value={s}>
                            {title(s)}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                  <label>
                    Sample size
                    <input
                      type="number"
                      min="1"
                      max="2000"
                      value={sampleSize}
                      onChange={(e) => setSampleSize(Number(e.target.value))}
                    />
                  </label>
                  <label>
                    Maximum target requests
                    <input
                      type="number"
                      min="1"
                      max="2000"
                      value={maxRequests}
                      onChange={(e) => setMaxRequests(Number(e.target.value))}
                    />
                  </label>
                  <label>
                    Sampling seed
                    <input
                      type="number"
                      value={samplingSeed}
                      onChange={(e) => setSamplingSeed(Number(e.target.value))}
                    />
                  </label>
                  {target === "imported" && (
                    <label>
                      Trace batch
                      <select
                        aria-label="Trace batch"
                        required
                        value={traceBatchId}
                        onChange={(e) => setTraceBatchId(e.target.value)}
                      >
                        <option value="">Choose an imported batch</option>
                        {batches.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.traces.length} traces · {date(b.created_at)}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
                <details className="run-settings">
                  <summary>Evaluator selection & telemetry prices</summary>
                  <p className="muted small">
                    Unavailable measurements stay explicit non-score results. No
                    semantic provider is available.
                  </p>
                  <div className="checkboxes">
                    {metrics.map((m) => (
                      <label key={m.id}>
                        <input
                          type="checkbox"
                          checked={
                            selectedMetrics === null ||
                            selectedMetrics.includes(m.id)
                          }
                          onChange={(e) => {
                            const selected =
                              selectedMetrics ?? metrics.map((x) => x.id);
                            setSelectedMetrics(
                              e.target.checked
                                ? [...selected, m.id]
                                : selected.filter((id) => id !== m.id),
                            );
                          }}
                        />
                        {title(m.id)} <Badge value={m.state} />
                      </label>
                    ))}
                  </div>
                  <div className="form-grid">
                    <label>
                      Input price / million tokens
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={inputPrice}
                        onChange={(e) => setInputPrice(e.target.value)}
                        placeholder="Unavailable"
                      />
                    </label>
                    <label>
                      Output price / million tokens
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={outputPrice}
                        onChange={(e) => setOutputPrice(e.target.value)}
                        placeholder="Unavailable"
                      />
                    </label>
                  </div>
                </details>
                <p className="muted small">
                  Spending cap: $0 · providers unavailable. The demo uses
                  lexical retrieval and literal answers; timeout is simulated. A
                  separate worker process must be running.
                </p>
                <button disabled={busy || !selectedDataset}>
                  Queue evaluation
                </button>
              </form>
              <RunList runs={runs} activeId={activeRun?.id} load={loadRun} />
              {activeRun && (
                <RunDetail
                  run={activeRun}
                  cancel={() =>
                    void perform(async () => {
                      await api(`/runs/${activeRun.id}/cancel`, {});
                      await loadRun(activeRun.id);
                    }, "Cancellation requested.")
                  }
                  inspect={() => setView("findings")}
                />
              )}
              <section className="panel">
                <h2>Compare runs</h2>
                <p className="muted small">
                  Only matched, unchanged case IDs and compatible evaluator
                  definitions can be compared. Counts and incomplete coverage
                  remain visible.
                </p>
                <div className="row wrap">
                  <label>
                    Baseline run
                    <select
                      aria-label="Baseline run"
                      value={leftRun}
                      onChange={(e) => {
                        setLeftRun(e.target.value);
                        setComparison(null);
                      }}
                    >
                      <option value="">Choose baseline</option>
                      {runs.map((r) => (
                        <option key={r.id} value={r.id}>
                          {title(r.request.target)} · {r.id.slice(0, 8)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Candidate run
                    <select
                      aria-label="Candidate run"
                      value={rightRun}
                      onChange={(e) => {
                        setRightRun(e.target.value);
                        setComparison(null);
                      }}
                    >
                      <option value="">Choose candidate</option>
                      {runs.map((r) => (
                        <option key={r.id} value={r.id}>
                          {title(r.request.target)} · {r.id.slice(0, 8)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    disabled={!leftRun || !rightRun || busy}
                    onClick={() =>
                      void perform(
                        async () =>
                          setComparison(
                            await api<Comparison>(
                              `/compare?left=${leftRun}&right=${rightRun}`,
                            ),
                          ),
                        "Run comparison loaded.",
                      )
                    }
                  >
                    Compare selected runs
                  </button>
                </div>
                {comparison && (
                  <div className="comparison">
                    <Badge
                      value={
                        comparison.compatible ? "compatible" : "incomplete"
                      }
                    />
                    <h3>
                      {comparison.matched_cases} matched cases ·{" "}
                      {comparison.left_cases} baseline /{" "}
                      {comparison.right_cases} candidate
                    </h3>
                    {comparison.reasons.map((r) => (
                      <p key={r}>{r}</p>
                    ))}
                    <p>
                      {comparison.changes.length} measurement changes, including
                      observed latency.
                    </p>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Case</th>
                            <th>Metric</th>
                            <th>Baseline</th>
                            <th>Candidate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {comparison.changes
                            .slice()
                            .sort(
                              (a, b) =>
                                Number(b.left.status !== b.right.status) -
                                Number(a.left.status !== a.right.status),
                            )
                            .map((c, i) => (
                              <tr key={i}>
                                <td>{c.case_id.slice(0, 8)}</td>
                                <td>{title(c.metric)}</td>
                                <td>
                                  <Badge value={c.left.status} />{" "}
                                  {number(c.left.value)}
                                </td>
                                <td>
                                  <Badge value={c.right.status} />{" "}
                                  {number(c.right.value)}
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            </>
          )}
          {application && view === "findings" && (
            <>
              <label className="panel run-picker">
                Evaluation run
                <select
                  aria-label="Evaluation run"
                  value={activeRun?.id ?? ""}
                  onChange={(e) => void loadRun(e.target.value)}
                >
                  <option value="">Choose a run</option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {title(r.request.target)} · {r.status} ·{" "}
                      {r.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </label>
              {!activeRun ? (
                <p className="panel empty">
                  Choose a completed run to inspect results and source evidence.
                </p>
              ) : (
                <>
                  <RunDetail
                    run={activeRun}
                    cancel={() =>
                      void perform(
                        () => api(`/runs/${activeRun.id}/cancel`, {}),
                        "Cancellation requested.",
                      )
                    }
                  />
                  <div className="blindspot">
                    <strong>Known blind spot</strong>
                    <p>
                      Literal answer agreement can pass an answer containing an
                      unsupported extra claim. Citation consistency checks
                      source IDs, not meaning. Semantic grounding is
                      unavailable.
                    </p>
                  </div>
                  <div
                    className="row wrap finding-filters"
                    role="group"
                    aria-label="Finding status"
                  >
                    {[
                      "failed",
                      "insufficient_evidence",
                      "skipped",
                      "evaluator_error",
                      "all",
                    ].map((f) => (
                      <button
                        className={findingFilter === f ? "" : "secondary"}
                        key={f}
                        onClick={() => setFindingFilter(f)}
                      >
                        {title(f)}
                      </button>
                    ))}
                  </div>
                  <Findings run={activeRun} filter={findingFilter} />
                </>
              )}
            </>
          )}
          <footer>
            GovernLoom · Local evaluation, separate dimensions, inspectable
            evidence. <span>Times shown in your browser’s local timezone.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function RunList({
  runs,
  activeId,
  load,
}: {
  runs: Run[];
  activeId?: string;
  load: (id: string) => Promise<void>;
}) {
  return (
    <section className="panel">
      <h2>Evaluation history</h2>
      {runs.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Target / run</th>
                <th>State</th>
                <th>Progress</th>
                <th>Findings</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr
                  key={r.id}
                  className={activeId === r.id ? "selected-row" : ""}
                >
                  <td>
                    <button
                      className="text-button"
                      onClick={() => void load(r.id)}
                    >
                      {title(r.request.target)} · {r.id.slice(0, 8)}
                    </button>
                  </td>
                  <td>
                    <Badge value={r.status} />
                  </td>
                  <td>
                    {r.completed} / {r.total}
                  </td>
                  <td>
                    {
                      r.results.filter((c) =>
                        c.metrics.some((m) => m.status === "failed"),
                      ).length
                    }{" "}
                    cases
                  </td>
                  <td>{date(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty">
          Queue your first evaluation after publishing a dataset.
        </p>
      )}
    </section>
  );
}

function RunDetail({
  run,
  cancel,
  inspect,
}: {
  run: Run;
  cancel: () => void;
  inspect?: () => void;
}) {
  return (
    <section className="panel">
      <div className="row between">
        <h2>Run · {title(run.request.target)}</h2>
        <Badge value={run.status} />
      </div>
      <div className="run-progress">
        <progress max={run.total} value={run.completed} />
        <span>
          {run.completed} / {run.total} finalized
        </span>
      </div>
      {run.error && <p role="alert">{run.error}</p>}
      <p className="small muted">
        {run.id} · {date(run.created_at)}
        <br />
        Dataset SHA-256 {run.dataset_checksum}
        <br />
        {run.snapshot &&
          `Application ${run.snapshot.application.application_version} · model ${run.snapshot.application.model_version} · prompt ${run.snapshot.application.prompt_version} · target ${run.snapshot.target_version}`}
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Pass / scored</th>
              <th>Failed</th>
              <th>Skipped</th>
              <th>Insufficient</th>
              <th>Evaluator errors</th>
              <th>Pending / selected</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(run.summary).map(([name, s]) => (
              <tr key={name}>
                <td>{title(name)}</td>
                <td>
                  {s.passed} / {s.scored}
                </td>
                <td className={s.failed ? "failure-number" : ""}>{s.failed}</td>
                <td>{s.skipped}</td>
                <td>{s.insufficient_evidence}</td>
                <td>{s.evaluator_error}</td>
                <td>
                  {s.pending} / {s.selected}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="actions">
        <a href={`/api/runs/${run.id}/traces`}>Export run traces ?</a>

        {["queued", "running"].includes(run.status) && (
          <button className="danger" onClick={cancel}>
            Cancel evaluation
          </button>
        )}
        {inspect && (
          <button className="secondary" onClick={inspect}>
            Inspect findings & evidence →
          </button>
        )}
      </div>
    </section>
  );
}

function Findings({ run, filter }: { run: Run; filter: string }) {
  const results = run.results.filter(
    (r) => filter === "all" || r.metrics.some((m) => m.status === filter),
  );
  if (!results.length)
    return (
      <p className="panel empty">
        No {filter === "all" ? "" : title(filter)} results in this run.
      </p>
    );
  return (
    <div className="findings">
      {results.map((r) => {
        const item = run.snapshot?.cases.find((c) => c.id === r.case_id);
        return (
          <article className="panel" key={r.case_id}>
            <div className="eyebrow">
              {item ? title(item.category) : r.case_id} · {item?.split}
            </div>
            <h2>{item?.question ?? r.case_id}</h2>
            <div className="answer-grid">
              <div>
                <h3>Observed answer</h3>
                <p>{r.trace?.answer ?? "Unavailable"}</p>
                {r.trace?.error && (
                  <p className="failure-number">{r.trace.error}</p>
                )}
                <small>
                  Behavior: {r.trace?.behavior ?? "Unavailable"}
                  <br />
                  Citations: {r.trace?.citations?.join(", ") || "None supplied"}
                </small>
              </div>
              <div>
                <h3>Expected behavior</h3>
                <p>
                  {item?.reference_answer ??
                    title(item?.expected_behavior ?? "Unavailable")}
                </p>
                <small>{item?.provenance}</small>
              </div>
            </div>
            <div className="metric-findings">
              {r.metrics
                .filter((m) => filter === "all" || m.status === filter)
                .map((m) => (
                  <details key={m.metric}>
                    <summary>
                      <span>
                        {title(m.metric)} · {number(m.value)}
                      </span>
                      <Badge value={m.status} />
                    </summary>
                    <p>{m.explanation}</p>
                    <pre>{JSON.stringify(m.evidence, null, 2)}</pre>
                    <small>Evaluator: {m.evaluator_version}</small>
                  </details>
                ))}
            </div>
            <h3>Frozen source evidence</h3>
            <Evidence
              references={item?.references ?? []}
              sources={run.snapshot?.dataset.sources ?? []}
            />
            <details>
              <summary>Trace record</summary>
              <pre>{JSON.stringify(r.trace, null, 2)}</pre>
            </details>
          </article>
        );
      })}
    </div>
  );
}
