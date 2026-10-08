import { useState } from 'react';
import { useSession } from '../auth/SessionContext';
import Icon from '../components/Icon';

export default function LoginPage() {
  const { login, error: sessionError, refreshSession } = useSession();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError(null);
    try { await login({ username: data.get('username'), password: data.get('password') }); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  return <div className="login-layout"><section className="login-card panel"><span className="brand-mark"><Icon name="shield" size={25} /></span><span className="eyebrow">Security Dashboard</span><h1>Sign in to your workspace</h1><p>Review evidence, investigate activity, and keep a record of decisions.</p>{(error || sessionError) && <div className="error-banner" role="alert">{error || sessionError}</div>}<form onSubmit={submit}><fieldset disabled={busy}><label className="form-field">Username<input name="username" autoComplete="username" required maxLength={150} /></label><label className="form-field">Password<input name="password" type="password" autoComplete="current-password" required maxLength={1024} /></label><button className="btn btn-primary" disabled={Boolean(sessionError)}>{busy ? 'Signing in…' : 'Sign in'}</button></fieldset></form>{sessionError && <button className="text-btn" onClick={refreshSession}>Retry connection</button>}<span className="login-help">Accounts are provisioned by your workspace administrator.</span></section></div>;
}
