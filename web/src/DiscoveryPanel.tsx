import {useContext, useEffect, useState} from "react";
import {AuthContext} from "./AuthContext";
import {api, downloadEvidence, readUtf8, title} from "./api";

type Draft = {id: string; checksum: string; created_at: string; analysis: {
  task_type: string; summary: string; mappings: Record<string,string>; ambiguous_mappings: Record<string,string[]>;
  available_paths: string[]; unknowns: string[]; findings: {message: string; path: string; line: number; excerpt: string}[];
}; semantic: null | {summary: string; model: string; hypotheses: {description: string; path: string; quote: string}[]; scenarios: {description: string; path: string; quote: string}[]}; exclusions: string[]};
type Confirmation = {id: string; discovery_id: string; purpose: string; task_type: string; mappings:Record<string,string>; outcome_meaning_confirmed:boolean; created_at: string; corrections: Record<string,unknown>};
type Plan = {id: string; discovery_id: string; confirmation_id: string; status: string; created_at: string;
  metrics: {name: string; status: string; reason?: string; threshold?: number; meaning?: string; calibration?: unknown; held_out?: unknown}[];
  gaps: string[]; warnings: string[]; limitations: string[]; unresolved_business_decisions: string[];
  instrumentation: {fields: Record<string,string>; scope: Record<string,string>; recipe: string};
  dataset: {sha256: string; calibration_cases: number; held_out_cases: number; duplicates_removed: number; split_method: string; synthetic_scenarios: unknown[]}};
const roles = ["prediction", "actual", "confidence", "predicted_label", "actual_label", "timestamp", "group", "split", "citations", "source_ids", "model_version", "application_version", "environment"];
const tasks = ["forecasting", "vision", "classification", "rag", "custom"];
const newest = <T extends {created_at:string}>(rows:T[]) => [...rows].sort((a,b) => b.created_at.localeCompare(a.created_at));

function Measurements({calibration,heldOut}:{calibration:unknown;heldOut:unknown}) {
  const left=(calibration && typeof calibration==="object" ? calibration : {}) as Record<string,unknown>;
  const right=(heldOut && typeof heldOut==="object" ? heldOut : {}) as Record<string,unknown>;
  const labels:Record<string,string>={cases:"Cases",mae:"Mean absolute error",rmse:"Root mean squared error",
    bias_prediction_minus_actual:"Average signed error",exceedances:"Residuals above threshold",true_positives:"Errors flagged",
    false_positives:"Correct predictions flagged",false_negatives:"Errors missed",true_negatives:"Correct predictions clear",
    false_positive_rate:"False-positive rate",risk_capture_rate:"Error capture rate",available:"Cases with required evidence",
    unavailable:"Cases missing evidence",flagged:"Citation identity flags"};
  const keys=[...new Set([...Object.keys(left),...Object.keys(right)])].filter(key=>labels[key]);
  const format=(key:string,value:unknown)=> typeof value==="number" ? key.endsWith("_rate") ? `${(value*100).toFixed(2)}%` :
    Number.isInteger(value) ? String(value) : value.toPrecision(5) : "Unavailable";
  return <table className="measurement-table"><thead><tr><th>Measurement</th><th>Calibration</th><th>Held out</th></tr></thead>
    <tbody>{keys.map(key=><tr key={key}><th>{labels[key]}</th><td>{format(key,left[key])}</td><td>{format(key,right[key])}</td></tr>)}</tbody></table>;
}

export function DiscoveryStart({created}: {created: (identifier:string) => Promise<void>}) {
  const identity = useContext(AuthContext);
  const [name,setName] = useState(""); const [file,setFile] = useState<File|null>(null);
  const [busy,setBusy] = useState(false); const [error,setError] = useState("");
  return <section className="panel discovery-start"><h2>Explore your application</h2>
    <p>Let GovernLoom inspect selected application evidence, suggest measurements and prepare a policy for review.</p>
    <p>Collect a local bundle with <code>governloom explore ./your-app --traces samples.jsonl --output discovery.json</code>. Source code is read without executing it. Review the private bundle before importing it.</p>
    <form onSubmit={async event => {event.preventDefault(); if(!file) return; setBusy(true); setError("");
      try {const bundle = JSON.parse(await readUtf8(file)); await api("/discovery-preview",bundle); const app = await api<{id:string}>("/applications", {
        name, purpose:"Awaiting application discovery confirmation", owner:identity?.username ?? "Local operator",
        expected_behavior:"Confirm discovered behavior and evaluate an observation baseline", model_version:"unconfirmed", application_version:"unconfirmed"});
        await api(`/applications/${app.id}/discoveries`, {...bundle, actor:identity?.username ?? "local-explorer"}); await created(app.id);
      } catch(error) {setError((error as Error).message);} finally {setBusy(false);}}}>
      <label>Application name<input required value={name} onChange={event=>setName(event.target.value)} maxLength={120}/></label>
      <label>Application evidence bundle<input required type="file" accept=".json" onChange={event=>setFile(event.target.files?.[0] ?? null)}/></label>
      <button disabled={busy || (!!identity && identity.role!=="admin")}>Explore application evidence</button>
    </form>{error && <div role="alert" className="alert error">{error}</div>}
  </section>;
}

export default function DiscoveryPanel({applicationId,actor,onActivated}: {applicationId:string;actor:string;onActivated:()=>Promise<void>}) {
  const identity = useContext(AuthContext); const canConfigure = !identity || ["admin","operator"].includes(identity.role);
  const [drafts,setDrafts] = useState<Draft[]>([]); const [confirmations,setConfirmations] = useState<Confirmation[]>([]); const [plans,setPlans] = useState<Plan[]>([]);
  const [selected,setSelected] = useState(""); const [task,setTask] = useState("custom"); const [purpose,setPurpose] = useState(""); const [mappings,setMappings] = useState<Record<string,string>>({});
  const [confirmedOutcomes,setConfirmedOutcomes] = useState(false); const [fraction,setFraction] = useState(10); const [ack,setAck] = useState(false);
  const [replace,setReplace] = useState(false); const [active,setActive] = useState<string|null>(null); const [busy,setBusy] = useState(false); const [error,setError] = useState(""); const [notice,setNotice] = useState("");
  const prefix = `/applications/${applicationId}`;
  async function refresh() {const [d,c,p,policy] = await Promise.all([api<Draft[]>(prefix+"/discoveries"),api<Confirmation[]>(prefix+"/discovery-confirmations"),api<Plan[]>(prefix+"/discovery-plans"),api<{id:string}|null>(prefix+"/monitor-policy")]);
    setDrafts(newest(d)); setConfirmations(newest(c)); setPlans(newest(p)); setActive(policy?.id ?? null);
    setSelected(previous => d.some(item=>item.id===previous) ? previous : newest(d)[0]?.id ?? "");}
  useEffect(()=>{void refresh().catch(error=>setError(error.message));},[applicationId]);
  const draft = drafts.find(item=>item.id===selected);
  const confirmation = confirmations.find(item=>item.discovery_id===selected);
  useEffect(()=>{if(draft) {setTask(confirmation?.task_type ?? draft.analysis.task_type);setPurpose(confirmation?.purpose ?? (draft.semantic?.summary ?? draft.analysis.summary).slice(0,2000));setMappings(confirmation?.mappings ?? draft.analysis.mappings);setConfirmedOutcomes(confirmation?.outcome_meaning_confirmed ?? false);setAck(false);setReplace(false);}},[draft?.id,confirmation?.id]);
  const plan = plans.find(item=>item.confirmation_id===confirmation?.id);
  async function action(run:()=>Promise<void>) {setBusy(true);setError("");setNotice("");try {await run();await refresh();}catch(error){setError((error as Error).message);}finally{setBusy(false);}}
  return <section className="panel discovery-panel"><div className="row between"><h2>Application discovery</h2><span className="small muted">Explore · confirm · calibrate · observe</span></div>
    <p>Review what the application appears to do. Correct the draft, then evaluate a monitoring baseline before activation.</p>
    {error && <div role="alert" className="alert error">{error}</div>}{notice && <div role="status" className="alert success">{notice}</div>}
    <details><summary>Import application evidence</summary><p>Use the local <code>governloom explore</code> command. Source excerpts are retained for review; sample prompts and answer bodies are discarded. Review source files for sensitive information before import.</p>
      <label>Import discovery bundle<input type="file" accept=".json" disabled={busy || !canConfigure} onChange={event=>{const file=event.target.files?.[0];if(file) void action(async()=>{const result=await api<Draft>(prefix+"/discoveries",{...JSON.parse(await readUtf8(file)),actor});setSelected(result.id);setNotice("Evidence imported. Review the inferred application.");});event.target.value="";}}/></label>
    </details>
    {!draft && <p className="muted">No application evidence imported yet. A task-specific monitoring draft will appear here.</p>}
    {draft && <>
      <label>Evidence snapshot<select value={selected} onChange={event=>setSelected(event.target.value)}>{drafts.map(item=><option key={item.id} value={item.id}>{new Date(item.created_at).toLocaleString()} · {item.analysis.task_type}</option>)}</select></label>
      <p><strong>Inferred application:</strong> {draft.analysis.summary}</p>
      {draft.semantic && <div className="discovery-summary"><p>{draft.semantic.summary}</p><p className="small muted">Model-assisted draft · {draft.semantic.model} · exact source references verified; interpretations require review.</p>
        {draft.semantic.hypotheses.map((item,index)=><details key={index}><summary>{item.description}</summary><p>{item.path}</p><blockquote>{item.quote}</blockquote></details>)}
      </div>}
      <details><summary>Inspect source evidence and unknowns</summary>
        {draft.analysis.findings.map((item,index)=><div key={index}><p>{item.message} · {item.path}:{item.line}</p><pre>{item.excerpt}</pre></div>)}
        <ul>{draft.analysis.unknowns.map(item=><li key={item}>{item}</li>)}{draft.exclusions.map(item=><li key={item}>{item}</li>)}</ul>
        <button type="button" className="secondary" onClick={()=>void downloadEvidence(`/api${prefix}/discoveries/${draft.id}`).catch(error=>setError(error.message))}>Download private discovery evidence</button>
      </details>
      <form onSubmit={event=>{event.preventDefault();void action(async()=>{await api(prefix+`/discoveries/${draft.id}/confirm`,{actor,expected_checksum:draft.checksum,task_type:task,purpose,mappings,
        outcome_meaning_confirmed:confirmedOutcomes,rationale:"Owner reviewed the application draft and selected field meanings"});setNotice("Application understanding confirmed. Original inference and corrections remain in history.");});}}>
        <label>Confirmed application type<select value={task} onChange={event=>setTask(event.target.value)}>{tasks.map(item=><option key={item}>{item}</option>)}</select></label>
        <label>Confirm or correct the application description<textarea required maxLength={2000} value={purpose} onChange={event=>setPurpose(event.target.value)}/></label>
        <details><summary>Review suggested telemetry mappings</summary><p>Resolve ambiguous fields here. An empty field remains unavailable.</p><div className="form-grid">{roles.map(role=><label key={role}>{title(role)}<select aria-label={`Map ${role}`} value={mappings[role] ?? ""} onChange={event=>setMappings(current=>{const updated={...current};if(event.target.value) updated[role]=event.target.value;else delete updated[role];return updated;})}>
          <option value="">Unavailable / not selected</option>{draft.analysis.available_paths.map(path=><option key={path}>{path}</option>)}</select></label>)}</div></details>
        <label className="row"><input type="checkbox" checked={confirmedOutcomes} onChange={event=>setConfirmedOutcomes(event.target.checked)}/>The actuals/reference labels represent observed outcomes; I reviewed their meaning.</label>
        <button disabled={busy || !canConfigure || !actor.trim()}>Confirm application understanding</button>
      </form>
      {confirmation && <div className="discovery-calibration"><p>Confirmed as {confirmation.task_type}. {Object.keys(confirmation.corrections).length} corrected fields; history retained.</p>
        <details><summary>Confirmed understanding history</summary>{confirmations.filter(item=>item.discovery_id===selected).map(item=><div key={item.id}><p>{new Date(item.created_at).toLocaleString()} · {item.task_type}</p><p>{item.purpose}</p><p className="small muted">Corrected fields: {Object.keys(item.corrections).map(title).join(", ") || "No task/mapping corrections"}</p></div>)}</details>
        <label>Exploratory alert budget (%)<input type="number" min={1} max={50} value={fraction} onChange={event=>setFraction(Number(event.target.value))}/></label>
        <p className="small muted">For forecasts this selects a historical residual quantile. For labeled classification it is a calibration false-positive budget. It does not define acceptable harm.</p>
        <button disabled={busy || !canConfigure || fraction<1 || fraction>50} onClick={()=>void action(async()=>{await api(prefix+"/discovery-plans",{actor,confirmation_id:confirmation.id,alert_fraction:fraction/100});setAck(false);setNotice("Evaluation dataset and observation proposal prepared.");})}>Evaluate monitoring proposal</button>
      </div>}
      {plan && <div className="discovery-plan"><h3>{plan.status==="ready" ? "Observation proposal ready for review" : "More evidence needed"}</h3>
        <p>{plan.dataset.calibration_cases} calibration · {plan.dataset.held_out_cases} held-out · {plan.dataset.duplicates_removed} duplicates removed</p><p className="small muted">{plan.dataset.split_method}</p>
        {plan.metrics.map(metric=><details key={metric.name}><summary>{metric.name} · {title(metric.status)}{metric.threshold!==undefined ? ` · threshold ${metric.threshold.toPrecision(5)}` : ""}</summary>
          <p>{metric.reason ?? metric.meaning}</p>{(metric.calibration!==undefined || metric.held_out!==undefined) && <Measurements calibration={metric.calibration} heldOut={metric.held_out}/>}
        </details>)}
        <ul>{[...plan.gaps,...plan.warnings].map(item=><li key={item}>{item}</li>)}</ul>
        <details><summary>Proposed instrumentation and limitations</summary><p>{plan.instrumentation.recipe}</p><pre>{JSON.stringify(plan.instrumentation,null,2)}</pre><ul>{[...plan.limitations,...plan.unresolved_business_decisions].map(item=><li key={item}>{item}</li>)}</ul><p>{plan.dataset.synthetic_scenarios.length} model-proposed scenarios remain unreviewed and are excluded from accuracy counts.</p></details>
        <button className="secondary" onClick={()=>void downloadEvidence(`/api${prefix}/discovery-plans/${plan.id}`).catch(error=>setError(error.message))}>Download frozen monitoring plan</button>
        <label className="row"><input type="checkbox" checked={ack} onChange={event=>setAck(event.target.checked)}/>I reviewed the measurements and limitations; activate flags only.</label>
        {active && <label className="row"><input type="checkbox" checked={replace} onChange={event=>setReplace(event.target.checked)}/>Replace the application's existing active policy with this observation baseline.</label>}
        <button disabled={busy || !canConfigure || !ack || (!!active && !replace) || plan.status!=="ready"} onClick={()=>void action(async()=>{await api(prefix+`/discovery-plans/${plan.id}/activate`,{actor,expected_policy_id:active,acknowledge_limitations:ack,rationale:"Reviewed frozen evaluation and approved observation flags only"});await onActivated();setNotice("Observation policy activated. No blocking or automatic mitigation enabled.");})}>Activate observation policy</button>
      </div>}
    </>}
  </section>;
}
