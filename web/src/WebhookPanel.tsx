import { useContext, useEffect, useState } from "react";
import { api, date } from "./api";
import { AuthContext } from "./AuthContext";

type Destination = {id: string; name: string; endpoint: string; active: boolean; revision: number};
type Delivery = {id: string; destination_id: string; incident_id: string; status: string; attempts: number; total_attempts: number; replays: number; revision: number; reason: string | null; created_at: string};

export default function WebhookPanel({applicationId, actor}: {applicationId: string; actor: string}) {
  const identity = useContext(AuthContext);
  const canConfigure = !identity || ["operator", "admin"].includes(identity.role);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const prefix = `/applications/${applicationId}`;
  useEffect(() => {
    let active = true;
    setSecret(""); setDestinations([]); setDeliveries([]); setError("");
    async function load() {
      try {
        const [a, b] = await Promise.all([api<Destination[]>(prefix + "/webhook-destinations"), api<Delivery[]>(prefix + "/webhook-deliveries")]);
        if (active) {setDestinations(a); setDeliveries(b);}
      } catch (e) {if (active) setError(String(e));}
    }
    void load(); const timer = setInterval(() => void load(), 5000);
    return () => {active = false; clearInterval(timer);};
  }, [prefix]);
  async function change(path: string, body: unknown) {
    setBusy(true); setError("");
    try {
      const response = await api<{secret?: string}>(path, body);
      if (response.secret) {setSecret(response.secret); setName(""); setEndpoint("");}
      const [a, b] = await Promise.all([api<Destination[]>(prefix + "/webhook-destinations"), api<Delivery[]>(prefix + "/webhook-deliveries")]);
      setDestinations(a); setDeliveries(b);
    } catch (e) {setError(String(e));} finally {setBusy(false);}
  }
  return <section className="panel webhook-panel">
    <h2>Incident delivery</h2>
    <p>Send signed incident notifications to your receiver. Delivery confirms receipt; application action evidence and incident review establish the response.</p>
    {error && <p role="alert" className="error">{error}</p>}
    <details><summary>Connect an incident receiver</summary>
      <p>The collector host must allow this exact URL. Use HTTPS for remote receivers and start the webhook worker after configuring its secret directory.</p>
      <form onSubmit={e => {e.preventDefault(); void change(prefix + "/webhook-destinations", {name, endpoint, actor});}}>
        <label>Receiver name<input required value={name} onChange={e => setName(e.target.value)} /></label>
        <label>Receiver URL<input required type="url" value={endpoint} onChange={e => setEndpoint(e.target.value)} placeholder="https://your-receiver.example/incidents" /></label>
        <button disabled={busy || !canConfigure || !actor.trim()}>Connect receiver</button>
      </form>
    </details>
    {secret && <div className="callout"><p>Save this signing secret in your receiver. It is shown once and stays in page memory. For rotation, update the receiver within the one-hour overlap before the old key stops signing.</p><code>{secret}</code><button onClick={() => setSecret("")}>Dismiss signing secret</button></div>}
    {!destinations.length && <p className="muted">No receivers connected. Incidents remain available in this console.</p>}
    {destinations.map(destination => <article className="finding" key={destination.id}>
      <strong>{destination.name}</strong><p>{destination.endpoint} · {destination.active ? "active" : "disabled"}</p>
      <button disabled={busy || !canConfigure || !destination.active || !actor.trim()} onClick={() => void change(`/webhook-destinations/${destination.id}/disable`, {actor, expected_revision: destination.revision})}>Disable receiver</button>
      <button disabled={busy || !canConfigure || !destination.active || !actor.trim()} onClick={() => void change(`/webhook-destinations/${destination.id}/rotate-secret`, {actor, expected_revision: destination.revision, overlap_seconds: 3600})}>Rotate signing secret</button>
    </article>)}
    {!deliveries.length && <p className="muted">No notifications yet. The active policy controls escalation count and cooldown.</p>}
    {deliveries.map(delivery => <article className="finding webhook-delivery" key={delivery.id}>
      <strong>{delivery.status === "dead_letter" ? "Delivery failed" : delivery.status}</strong>
      <p>{destinations.find(d => d.id === delivery.destination_id)?.name ?? "Receiver"} · {delivery.total_attempts} attempts · {delivery.replays} replays · {date(delivery.created_at)}</p>
      {delivery.reason && <p>{delivery.reason}</p>}
      <p className="small">Incident {delivery.incident_id} · Delivery {delivery.id}</p>
      {delivery.status === "dead_letter" && <button disabled={busy || !canConfigure || !actor.trim() || !destinations.some(d => d.id === delivery.destination_id && d.active)} onClick={() => void change(`/webhook-deliveries/${delivery.id}/replay`, {actor, expected_revision: delivery.revision})}>Replay failed delivery</button>}
    </article>)}
  </section>;
}
