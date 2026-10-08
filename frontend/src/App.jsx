import { useEffect, useState } from 'react';
import Dashboard from './pages/Dashboard';
import SuspiciousPage from './pages/SuspiciousPage';
import Icon from './components/Icon';
import InvestigationsPage from './pages/InvestigationsPage';
import './App.css';
import { useSession } from './auth/SessionContext';
import LoginPage from './pages/LoginPage';
import AccountsPage from './pages/AccountsPage';

function initialTheme() {
  try {
    const saved = localStorage.getItem('security-dashboard-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* Use the default when storage is unavailable. */ }
  return 'light';
}

function pageFromHash() {
  if (location.hash === '#accounts') return 'accounts';
  return location.hash.startsWith('#investigations') ? 'investigations' : location.hash.startsWith('#suspicious') ? 'suspicious' : 'dashboard';
}

export default function App() {
  const { user, loading, error: sessionError, logout } = useSession();
  const [logoutError, setLogoutError] = useState(null);
  const [page, setPage] = useState(pageFromHash);
  function navigate(nextPage) { setPage(nextPage); window.history.pushState(null, '', nextPage === 'dashboard' ? '#events' : `#${nextPage}`); window.dispatchEvent(new PopStateEvent('popstate')); }
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    const sync = () => setPage(pageFromHash());
    window.addEventListener('hashchange', sync);
    window.addEventListener('popstate', sync);
    return () => { window.removeEventListener('hashchange', sync); window.removeEventListener('popstate', sync); };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('security-dashboard-theme', theme); } catch { /* Storage is optional. */ }
  }, [theme]);

  const themeButton = <button className="btn theme-toggle" aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}><Icon name={theme === 'light' ? 'moon' : 'sun'} />{theme === 'light' ? 'Dark mode' : 'Light mode'}</button>;
  if (loading) return <div className="loading">Checking your session…</div>;
  if (!user) return <><div className="login-toolbar">{themeButton}</div><LoginPage /></>;
  if (!user.role) return <div className="login-layout"><div className="panel login-card"><h1>Workspace access unavailable</h1><p>Contact an administrator to assign a role.</p><button className="btn" onClick={() => logout().catch(error => setLogoutError(error.message))}>Sign out</button>{logoutError && <p role="alert">{logoutError}</p>}</div></div>;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="nav-brand"><span className="brand-mark"><Icon name="shield" size={23} /></span><div>Security Dashboard<span className="brand-caption">Operations workspace</span></div></div>
        <div className="workspace-label">Workspace</div>
        <nav className="nav-links" aria-label="Main navigation">
          <button className={`nav-btn ${page === 'dashboard' ? 'active' : ''}`} aria-current={page === 'dashboard' ? 'page' : undefined} onClick={() => navigate('dashboard')}><Icon name="grid" />Events</button>
          <button className={`nav-btn ${page === 'suspicious' ? 'active' : ''}`} aria-current={page === 'suspicious' ? 'page' : undefined} onClick={() => navigate('suspicious')}><Icon name="alert" />Suspicious</button>
          <button className={`nav-btn ${page === 'investigations' ? 'active' : ''}`} aria-current={page === 'investigations' ? 'page' : undefined} onClick={() => navigate('investigations')}><Icon name="shield" />Investigations</button>
          {user.role === 'admin' && <button className={`nav-btn ${page === 'accounts' ? 'active' : ''}`} aria-current={page === 'accounts' ? 'page' : undefined} onClick={() => navigate('accounts')}><Icon name="grid" />Accounts</button>}
        </nav>
        <div className="sidebar-footer"><span className="environment-dot" />Local workspace<span className="sidebar-note">Authentication monitoring</span></div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">Security operations <span>/</span> <strong>{page === 'dashboard' ? 'Events' : page === 'investigations' ? 'Investigations' : page === 'accounts' ? 'Accounts & access' : 'Suspicious activity'}</strong></div>
          <div className="session-actions"><span className="session-identity">{user.display_name}<small>{user.role === 'admin' ? 'Administrator' : user.role === 'analyst' ? 'Analyst' : 'Viewer'}</small></span>{themeButton}<button className="btn" onClick={() => { setLogoutError(null); logout().catch(error => setLogoutError(error.message)); }}>Sign out</button></div>
        </header>
        <main className="main">{(sessionError || logoutError) && <div className="error-banner" role="alert">{sessionError || logoutError}</div>}{page === 'dashboard' ? <Dashboard /> : page === 'investigations' ? <InvestigationsPage /> : page === 'accounts' ? user.role === 'admin' ? <AccountsPage /> : <div className="empty">Administrator access is required.</div> : <SuspiciousPage />}</main>
      </div>
    </div>
  );
}
