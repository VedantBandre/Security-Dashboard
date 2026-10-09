import { useState } from 'react';

function initialHidden() {
  try { return localStorage.getItem('security-dashboard-guide-hidden') === 'true'; }
  catch { return false; }
}

export default function PortfolioGuide({ demo, role, onNavigate }) {
  const [hidden, setHidden] = useState(initialHidden);
  function toggle() {
    setHidden(!hidden);
    try { localStorage.setItem('security-dashboard-guide-hidden', String(!hidden)); }
    catch { /* The guide remains usable without browser storage. */ }
  }
  return <section className="panel portfolio-guide" aria-label="Portfolio walkthrough">
    <div className="guide-heading"><div><span className="eyebrow">Synthetic demonstration{role === 'viewer' ? ' · Read-only access' : ''}</span><h2>{hidden ? 'Portfolio demo' : 'Explore the demo in three steps'}</h2></div><button className="text-btn" onClick={toggle} aria-expanded={!hidden}>{hidden ? 'Show guide' : 'Hide guide'}</button></div>
    {!hidden && <><p className="guide-description">A saved example of an authentication incident, with evidence and investigation decisions. Sample created {new Date(demo.initialized_at).toLocaleDateString()}; the recent-activity chart may be empty as the sample ages.</p><ol className="guide-steps">
      <li><h3>Explore activity</h3><p>Filter the Events table, open event details, and compare failed attempts with successful sign-ins.</p><button className="text-btn" onClick={() => onNavigate('dashboard')}>Explore events</button></li>
      <li><h3>Understand a detection</h3><p>In Investigations, open a finding to see its detection rule and the captured evidence behind it.</p><button className="text-btn" onClick={() => onNavigate('investigations')}>Review findings</button></li>
      <li><h3>Follow a case</h3><p>Choose the Cases tab in Investigations. Open the resolved sample to read its notes, decision, and audit history.</p></li>
    </ol></>}
  </section>;
}
