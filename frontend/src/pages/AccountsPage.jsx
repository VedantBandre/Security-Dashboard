import { useState } from 'react';
import { fetchUsers, fetchAccessHistory, createUser, updateUser } from '../api';
import { useSession } from '../auth/SessionContext';
import usePolling from '../hooks/usePolling';

const INITIAL = { users: [], history: [] };
async function fetchAccounts() { const [users, history] = await Promise.all([fetchUsers(), fetchAccessHistory()]); return { users, history }; }
const roleNames = { viewer: 'Viewer', analyst: 'Analyst', admin: 'Administrator' };
export default function AccountsPage() {
  const { data: { users, history }, loading, error, refresh } = usePolling(fetchAccounts, INITIAL);
  const { user: me, refreshSession } = useSession();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [notice, setNotice] = useState(null);
  async function change(user, changes) {
    setBusy(true); setActionError(null); setNotice(null);
    try { await updateUser(user.id, changes); refresh(); setNotice('Account access updated.'); if (user.id === me.id) await refreshSession(); }
    catch (error) { setActionError(error.message); }
    finally { setBusy(false); }
  }
  async function add(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true); setActionError(null); setNotice(null);
    try { await createUser(Object.fromEntries(data)); form.reset(); refresh(); setNotice('Account created. Share its credentials securely with the account owner.'); }
    catch (error) { setActionError(error.message); }
    finally { setBusy(false); }
  }
  return <section className="page"><div className="page-header"><div><span className="eyebrow">Workspace administration</span><h1>Accounts & access</h1><p>Provision accounts, manage roles, and review access changes.</p></div><button className="btn" onClick={refresh}>Refresh</button></div>{(error || actionError) && <div className="error-banner" role="alert">{error || actionError}</div>}{notice && <div className="success-banner" role="status">{notice}</div>}<div className="case-layout"><div className="case-main"><section className="panel"><div className="panel-header"><div><h2>Workspace accounts</h2><p>Viewer: read only · Analyst: investigations · Administrator: accounts and ingestion</p></div></div>{loading ? <div className="loading">Loading accounts…</div> : <div className="table-wrapper"><table><thead><tr><th>Account</th><th>Role</th><th>Access</th><th>Action</th></tr></thead><tbody>{users.map(user => <tr key={user.id}><td>{user.username}{user.id === me.id && <span className="record-id">Your account</span>}</td><td><select aria-label={`Role for ${user.username}`} disabled={busy} value={user.role || ''} onChange={event => change(user, { role: event.target.value })}><option value="" disabled>No role</option>{Object.entries(roleNames).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></td><td><span className={`badge ${user.is_active ? 'badge-ok' : 'badge-clean'}`}>{user.is_active ? 'Active' : 'Inactive'}</span></td><td><button className="btn" disabled={busy} onClick={() => change(user, { is_active: !user.is_active })}>{user.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>)}</tbody></table></div>}</section><section className="panel case-section"><h2>Access change history</h2><ol className="case-timeline">{history.map(entry => <li key={entry.id}><div><strong>{entry.actor} · {entry.action.replaceAll('_', ' ')} · {entry.target}</strong><time>{new Date(entry.created_at).toLocaleString()}</time></div><p>Role: {entry.after.role || 'None'} · {entry.after.is_active ? 'Active' : 'Inactive'}</p></li>)}</ol>{!history.length && <p className="section-description">Access changes will be recorded here. Showing the latest 100 entries.</p>}</section></div><section className="panel case-section case-aside"><div><h2>Create an account</h2><p className="section-description">Use an individual account for each analyst.</p><form onSubmit={add}><fieldset disabled={busy}><label className="form-field">Username<input name="username" autoComplete="off" required maxLength={150} /></label><label className="form-field">Initial password<input name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={1024} /></label><label className="form-field">Workspace role<select name="role" defaultValue="analyst">{Object.entries(roleNames).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><button className="btn btn-primary">Create account</button></fieldset></form></div></section></div></section>;
}
