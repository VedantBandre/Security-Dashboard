import { useState } from 'react';
import Dashboard from './pages/Dashboard';
import SuspiciousPage from './pages/SuspiciousPage';
import './App.css';

export default function App() {
  const [page, setPage] = useState('dashboard');

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">
          <span className="nav-icon">🛡️</span>
          <span>SOC Dashboard</span>
        </div>
        <div className="nav-links">
          <button
            className={`nav-btn ${page === 'dashboard' ? 'active' : ''}`}
            onClick={() => setPage('dashboard')}
          >
            Events
          </button>
          <button
            className={`nav-btn ${page === 'suspicious' ? 'active' : ''}`}
            onClick={() => setPage('suspicious')}
          >
            Suspicious
          </button>
        </div>
      </nav>
      <main className="main">
        {page === 'dashboard' && <Dashboard />}
        {page === 'suspicious' && <SuspiciousPage />}
      </main>
    </div>
  )
}
