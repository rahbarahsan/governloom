import {useEffect, useState} from "react";
import {api, title} from "./api";

export type Reference = {framework:string; version:string; reference:string; url:string; rationale:string};
export type ControlReference = {catalogue_version:string; control_id:string; references:Reference[]};
type Measurement = {metric_id:string; status:string; value:unknown; denominator:number; excluded_cases:number;
  split:string; label:string|null; unit:string; reason:string|null; evaluator_version:string};
type Recommendation = {id:string; name:string; applicability:string; why:string; status:string; selected:boolean;
  dismissal_rationale:string|null; evidence:{role:string;path:string}[]; metric_ids:string[]; required_inputs:string[];
  missing_prerequisites:string[]; threshold_selection:string; suggested_response:string; limitations:string; references:Reference[]};
export type Guidance = {catalogue?:{version:string;sha256:string;interpretation:string;metrics:{id:string;method:string}[]};
  recommendations?:Recommendation[];metric_results?:Measurement[];live_metric_sources?:Record<string,string>};

export function ControlSources({reference}:{reference?:ControlReference}) {
  if(!reference) return null;
  return <details className="control-sources"><summary>Policy reference: {reference.control_id}</summary>
    <p>Catalogue {reference.catalogue_version}</p>
    {reference.references.map(item=><p key={item.reference}><a href={item.url} target="_blank" rel="noreferrer">{item.framework} {item.version} · {item.reference}</a> — {item.rationale}</p>)}
  </details>;
}

function valueText(item:Measurement) {
  if(item.value===null) return "Unavailable";
  if(typeof item.value==="number") return item.unit==="ratio" ? `${(item.value*100).toFixed(2)}%` : Number.isInteger(item.value) ? String(item.value) : item.value.toPrecision(5);
  return JSON.stringify(item.value);
}

export default function PolicyRecommendations({plan,disabled,onDirty,onPrepare}:{plan:Guidance;disabled:boolean;
  onDirty:()=>void;onPrepare:(selected:string[],dismissed:Record<string,string>)=>void}) {
  const controls=plan.recommendations ?? [];
  const [selected,setSelected]=useState(controls.filter(item=>item.selected).map(item=>item.id));
  const [dismissed,setDismissed]=useState<Record<string,string>>(Object.fromEntries(controls.filter(item=>item.dismissal_rationale!==null).map(item=>[item.id,item.dismissal_rationale ?? ""])));
  const [live,setLive]=useState<{counts:Record<string,number>;checked_at:string;limitation:string}|null>(null);
  const [error,setError]=useState("");
  const livePath=plan.live_metric_sources?.["common.outcomes"];
  useEffect(()=>{if(livePath) void api<{counts:Record<string,number>;checked_at:string;limitation:string}>(livePath.replace(/^\/api/,"")).then(setLive).catch(error=>setError(error.message));},[livePath]);
  if(!plan.catalogue) return null;
  return <section className="policy-recommendations"><h3>Recommended starter policies</h3>
    <p>GovernLoom selected these objectives from the confirmed evidence. Review permissions and proposed thresholds before activation.</p>
    <p className="small muted">{plan.catalogue.interpretation} Catalogue {plan.catalogue.version}.</p>
    {controls.filter(item=>item.applicability==="applicable").map(control=><article className="starter-control" key={control.id} data-control={control.id}>
      <h4>{control.name} · {title(control.status)}</h4><p><strong>Why recommended:</strong> {control.why}</p>
      <details><summary>Evidence, measurements and response</summary>
        <p>Required: {control.required_inputs.join(", ")}</p>
        {control.evidence.map(item=><p className="small" key={item.role}>{title(item.role)} ← {item.path}</p>)}
        <p>{control.threshold_selection}</p>
        <ControlSources reference={{catalogue_version:plan.catalogue!.version,control_id:control.id,references:control.references}}/>
        <table className="measurement-table"><thead><tr><th>Metric / split</th><th>Value</th><th>Denominator</th><th>Excluded</th></tr></thead>
          <tbody>{plan.metric_results?.filter(item=>control.metric_ids.includes(item.metric_id)).map((item,index)=><tr key={index}><th>{title(item.metric_id)}{item.label ? ` · ${item.label}` : ""}<br/><small>{title(item.split)}</small></th>
            <td>{valueText(item)}{item.reason && <p className="small">{item.reason}</p>}</td><td>{item.denominator}</td><td>{item.excluded_cases}</td></tr>)}</tbody></table>
        <p className="small">Counts use the frozen selected observations. Excluded rows are outside the metric denominator; class and gate metrics have different populations.</p>
        <details><summary>Metric definitions</summary>{plan.catalogue?.metrics.filter(item=>control.metric_ids.includes(item.id)).map(item=><p key={item.id}>{title(item.id)}: {item.method}</p>)}</details>
        {control.id==="common.outcomes" && live && <div className="live-outcome-counts"><p>Live tracked outcomes: {Object.entries(live.counts).map(([key,value])=>`${key}: ${value}`).join(" · ")}</p><p className="small">Checked {new Date(live.checked_at).toLocaleString()}. {live.limitation}</p></div>}
        <ul>{control.missing_prerequisites.map(item=><li key={item}>{item}</li>)}</ul>
        <p><strong>Suggested response:</strong> {control.suggested_response}</p><p>{control.limitations}</p>
      </details>
      {control.status==="ready" && <label className="row"><input type="checkbox" aria-label={`Monitor ${control.name}`} disabled={disabled || control.id in dismissed} checked={selected.includes(control.id)} onChange={event=>{setSelected(current=>event.target.checked ? [...current,control.id] : current.filter(id=>id!==control.id));onDirty();}}/>Include in observation policy</label>}
      <details><summary>Record why this recommendation is deferred</summary><label className="row"><input type="checkbox" disabled={disabled} checked={control.id in dismissed} onChange={event=>{setDismissed(current=>{const next={...current};if(event.target.checked) next[control.id]="";else delete next[control.id];return next;});setSelected(current=>current.filter(id=>id!==control.id));onDirty();}}/>Defer {control.name}</label>
        {control.id in dismissed && <label>Reason for deferring {control.name}<input required maxLength={2000} disabled={disabled} value={dismissed[control.id]} onChange={event=>{setDismissed(current=>({...current,[control.id]:event.target.value}));onDirty();}}/></label>}</details>
    </article>)}
    <details><summary>Other catalogue objectives</summary>{controls.filter(item=>item.applicability!=="applicable").map(item=><p key={item.id}>{item.name}: not indicated by the confirmed evidence. Correct discovery if this capability exists.</p>)}</details>
    {error && <p role="alert">Live outcome coverage unavailable: {error}</p>}
    <button type="button" className="secondary" disabled={disabled || Object.values(dismissed).some(reason=>!reason.trim())} onClick={()=>onPrepare(selected,dismissed)}>Save policy selection and reevaluate</button>
  </section>;
}
