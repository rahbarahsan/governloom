import { useContext, useEffect, useState } from "react";
import { api } from "./api";
import { AuthContext } from "./AuthContext";
type Profile = {id: string; name: string; kind: string; checksum: string; model_version: string; environment: string; approval: unknown; calibration: {label_provenance: string; true_positives: number; false_positives: number; true_negatives: number; false_negatives: number; unavailable: number}};

export default function DetectorProfiles({applicationId, actor}: {applicationId: string; actor: string}) {
  const identity = useContext(AuthContext);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [text, setText] = useState(""); const [rationale, setRationale] = useState(""); const [error, setError] = useState("");
  const canConfigure = !identity || ["operator", "admin"].includes(identity.role);
  const canApprove = !identity || identity.role !== "viewer";
  async function refresh() { setProfiles(await api(`/applications/${applicationId}/detector-profiles`)); }
  useEffect(() => { void refresh().catch(e => setError(e.message)); }, [applicationId]);
  return <section className="panel detector-profiles"><h2>Detector evidence</h2>
    <p>Freeze task-specific calibration before enabling a grounding or distribution check. Approval records acceptance of an experimental signal.</p>
    {!profiles.length && <p>No profiles yet. These checks are unavailable until evidence is supplied and approved.</p>}
    {error && <div role="alert" className="alert error">{error}</div>}
    {profiles.map(p => <details key={p.id}><summary>{p.name} · {p.approval ? "approved" : "awaiting review"}</summary>
      <p>{p.kind} · {p.environment} · {p.model_version}</p><p className="small">Profile ID: <code>{p.id}</code></p>
      <p>Labels: {p.calibration.label_provenance}. Captured risks: {p.calibration.true_positives}; missed: {p.calibration.false_negatives}; false positives: {p.calibration.false_positives}; clear controls: {p.calibration.true_negatives}; unavailable: {p.calibration.unavailable}.</p>
      <p className="small muted">Engineering labels are not independent human validation. Drift findings do not establish loss of model quality.</p>
      <a href={`/api/detector-profiles/${p.id}`}>Download immutable profile</a>
      {!p.approval && <form onSubmit={async e => { e.preventDefault(); setError(""); try { await api(`/detector-profiles/${p.id}/approve`, {actor, expected_checksum: p.checksum, rationale}); await refresh(); } catch(e) { setError((e as Error).message); } }}>
        <label>Detector approval rationale<textarea required value={rationale} onChange={e => setRationale(e.target.value)} /></label><button disabled={!canApprove || !actor.trim()}>Approve detector evidence</button>
      </form>}
    </details>)}
    <details><summary>Import a detector profile</summary><form onSubmit={async e => { e.preventDefault(); setError(""); try { const body = JSON.parse(text); await api(`/applications/${applicationId}/detector-profiles`, {...body, actor}); setText(""); await refresh(); } catch(e) { setError((e as Error).message); } }}>
      <label>Profile JSON<textarea required rows={8} value={text} onChange={e => setText(e.target.value)} /></label><p className="small muted">Include scope, source/reference hashes and a grouped calibration/held-out report. See docs/DETECTOR_EVIDENCE.md for the contract.</p><button disabled={!canConfigure || !actor.trim()}>Import immutable profile</button>
    </form></details>
  </section>;
}
