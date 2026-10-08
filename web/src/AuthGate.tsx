import { useEffect, useState } from "react";
import App from "./App";
import { api, setAdminToken } from "./api";
import { AuthContext, type Operator } from "./AuthContext";

export default function AuthGate() {
  const [mode, setMode] = useState<string>("");
  const [user, setUser] = useState<Operator | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [accounts, setAccounts] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  useEffect(() => { void api<{mode: string}>("/auth/config").then(c => setMode(c.mode)).catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (!user) return;
    const timer = window.setInterval(() => {
      void api<Operator>("/auth/me").catch(() => { setAdminToken(""); setUser(null); setError("Session ended. Sign in again."); });
    }, 30_000);
    return () => clearInterval(timer);
  }, [user]);
  if (mode === "local") return <App />;
  if (!user) return <main className="login-shell"><section className="panel">
    <div className="eyebrow">GOVERNLOOM · PRIVATE COLLECTOR</div><h1>Sign in to govern your AI.</h1>
    <p>Your account determines which applications and actions you can access.</p>
    {error && <div role="alert" className="alert error">{error}</div>}
    {mode && <form onSubmit={async e => {
      e.preventDefault(); setBusy(true); setError("");
      try { const result = await api<{token: string; user: Operator}>("/auth/login", {username, password}); setAdminToken(result.token); setUser(result.user); setPassword(""); }
      catch (e) { setError((e as Error).message); }
      finally { setBusy(false); }
    }}><label>Username<input autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} /></label>
      <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
      <button disabled={busy}>Sign in</button></form>}
  </section></main>;
  return <AuthContext.Provider value={user}>
    <div className="identity-bar"><span>Signed in as <strong>{user.username}</strong> · {user.role}</span>
      <details><summary>Change password</summary><form onSubmit={async e => { e.preventDefault(); try { await api("/auth/password", {current_password: currentPassword, new_password: newPassword}); setCurrentPassword(""); setNewPassword(""); setAdminToken(""); setUser(null); setError("Password changed. Sign in again."); } catch(e) { setError((e as Error).message); } }}>
        <label>Current password<input type="password" autoComplete="current-password" required value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} /></label>
        <label>New password<input type="password" autoComplete="new-password" minLength={15} required value={newPassword} onChange={e => setNewPassword(e.target.value)} /></label><button>Change password and sign out</button>
        {error && <p role="alert">{error}</p>}
      </form></details>
      {user.role === "admin" && <button className="secondary" onClick={() => setAccounts(!accounts)}>Operator accounts</button>}
      <button className="secondary" onClick={async () => { try { await api("/auth/logout", {}); } finally { setAdminToken(""); setUser(null); setAccounts(false); } }}>Sign out</button>
    </div>
    {accounts && <Accounts />}
    <App />
  </AuthContext.Provider>;
}

function Accounts() {
  const [users, setUsers] = useState<(Operator & {active: boolean})[]>([]);
  const [apps, setApps] = useState<{id: string; name: string}[]>([]);
  const [username, setUsername] = useState(""); const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer"); const [grants, setGrants] = useState<string[]>([]); const [error, setError] = useState("");
  async function refresh() { setUsers(await api("/auth/users")); setApps(await api("/applications")); }
  useEffect(() => { void refresh().catch(e => setError(e.message)); }, []);
  return <section className="panel account-panel"><h2>Operator accounts</h2>
    {error && <div role="alert" className="alert error">{error}</div>}
    <form onSubmit={async e => { e.preventDefault(); setError(""); try { await api("/auth/users", {username, password, role, application_ids: role === "admin" ? [] : grants}); setPassword(""); setUsername(""); await refresh(); } catch(e) { setError((e as Error).message); } }}>
      <label>New username<input required value={username} onChange={e => setUsername(e.target.value)} /></label>
      <label>Initial password<input type="password" autoComplete="new-password" minLength={15} required value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label>Role<select value={role} onChange={e => setRole(e.target.value)}>{["viewer", "reviewer", "operator", "admin"].map(r => <option key={r}>{r}</option>)}</select></label>
      {role !== "admin" && <fieldset><legend>Application access</legend>{apps.map(app => <label key={app.id}><input type="checkbox" checked={grants.includes(app.id)} onChange={e => setGrants(e.target.checked ? [...grants, app.id] : grants.filter(id => id !== app.id))} />{app.name}</label>)}</fieldset>}
      <p className="muted small">Viewer: read. Reviewer: review and verify. Operator: configure and review assigned applications. Admin: all applications and accounts.</p>
      <button>Create account</button>
    </form>
    {users.map(u => <div className="identity-bar" key={u.id}><span>{u.username} · {u.role} · {u.active ? "active" : "revoked"}</span><button className="secondary" disabled={!u.active} onClick={async () => { try { await api(`/auth/users/${u.id}/revoke`, {}); await refresh(); } catch(e) { setError((e as Error).message); } }}>Revoke account</button></div>)}
  </section>;
}
