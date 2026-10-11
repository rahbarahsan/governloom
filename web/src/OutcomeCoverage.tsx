import {useEffect, useState} from "react";
import {api, date} from "./api";

type Coverage = {counts: {pending: number; overdue: number; resolved: number}; unswept_overdue: number;
  expectations: {id: string; event_id: string; status: string; due_at: string; late_seconds: number | null}[]};

export default function OutcomeCoverage({applicationId}: {applicationId: string}) {
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setCoverage(null); setError("");
    async function load() {
      try {const value = await api<Coverage>(`/applications/${applicationId}/outcome-coverage`); if (active) {setCoverage(value); setError("");}}
      catch (e) {if (active) setError(String(e));}
    }
    void load(); const timer = setInterval(() => void load(), 5000);
    return () => {active = false; clearInterval(timer);};
  }, [applicationId]);
  if (!error && (!coverage || !Object.values(coverage.counts).some(Boolean))) return null;
  return <section className="panel outcome-coverage"><h2>Expected outcomes</h2>
    <p>Tracks explicitly declared numeric actuals. Missing outcomes leave prediction correctness unknown; lateness measures receipt by the collector.</p>
    {error && <p role="alert">{error}</p>}
    {coverage && <><p>{coverage.counts.pending} pending · {coverage.counts.overdue} overdue · {coverage.counts.resolved} received</p>
      {coverage.unswept_overdue > 0 && <p className="callout">{coverage.unswept_overdue} overdue outcomes await the monitor worker. Start it to persist alerts and queue incident delivery.</p>}
      <details><summary>Inspect expected outcomes</summary>{coverage.expectations.map(row => <article className="finding" key={row.id}>
        <strong>{row.status}</strong><p>Prediction {row.event_id} · due {date(row.due_at)}</p>
        {row.late_seconds !== null && <p>{row.late_seconds > 0 ? `Received ${row.late_seconds.toFixed(1)} seconds after deadline` : "Received on time"}</p>}
      </article>)}</details>
    </>}
  </section>;
}
