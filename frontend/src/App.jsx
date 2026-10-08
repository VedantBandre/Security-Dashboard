import { useEffect, useState } from 'react';
import Dashboard from './pages/Dashboard';
import SuspiciousPage from './pages/SuspiciousPage';
import Icon from './components/Icon';
import './App.css';

function initialTheme() {
  try {
    const saved = localStorage.getItem('security-dashboard-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* Use the default when storage is unavailable. */ }
  return 'light';
}

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('security-dashboard-theme', theme); } catch { /* Storage is optional. */ }
  }, [theme]);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="nav-brand"><span className="brand-mark"><Icon name="shield" size={23} /></span><div>Security Dashboard<span className="brand-caption">Operations workspace</span></div></div>
        <div className="workspace-label">Workspace</div>
        <nav className="nav-links" aria-label="Main navigation">
          <button className={`nav-btn ${page === 'dashboard' ? 'active' : ''}`} aria-current={page === 'dashboard' ? 'page' : undefined} onClick={() => setPage('dashboard')}><Icon name="grid" />Events</button>
          <button className={`nav-btn ${page === 'suspicious' ? 'active' : ''}`} aria-current={page === 'suspicious' ? 'page' : undefined} onClick={() => setPage('suspicious')}><Icon name="alert" />Suspicious</button>
        </nav>
        <div className="sidebar-footer"><span className="environment-dot" />Local workspace<span className="sidebar-note">Authentication monitoring</span></div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">Security operations <span>/</span> <strong>{page === 'dashboard' ? 'Events' : 'Suspicious activity'}</strong></div>
          <button className="btn theme-toggle" aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}><Icon name={theme === 'light' ? 'moon' : 'sun'} />{theme === 'light' ? 'Dark mode' : 'Light mode'}</button>
        </header>
        <main className="main">{page === 'dashboard' ? <Dashboard /> : <SuspiciousPage />}</main>
      </div>
    </div>
  );
}
