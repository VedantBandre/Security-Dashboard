import { useCallback, useEffect, useState } from 'react';
import { fetchFindings, fetchFinding, fetchInvestigations, fetchInvestigation, createInvestigation, updateInvestigation, addInvestigationNote, fetchAssignableUsers } from '../api';
import usePolling from '../hooks/usePolling';
import Icon from '../components/Icon';
import { useSession } from '../auth/SessionContext';

const INITIAL = { findings: [], cases: [], users: [] };
const labels = { new: 'New', investigating: 'Investigating', resolved: 'Resolved', true_positive: 'True positive', false_positive: 'False positive', benign: 'Benign' };
const time = value => new Date(value).toLocaleString();
async function fetchQueue() {
  const [findings, cases, users] = await Promise.all([fetchFindings(), fetchInvestigations(), fetchAssignableUsers()]);
  return { findings, cases, users };
}
function viewSource(ip) { window.location.assign(`#events?source=${encodeURIComponent(ip)}`); }
function Evidence({ finding }) {
  return <section className="case-section"><h2>Detection evidence</h2><p className="section-description">{finding.title} · rule version {finding.rule_version}</p><div className="evidence-summary"><div><span>Observed</span><strong>{finding.observed_count} attempts</strong></div><div><span>Trigger</span><strong>More than {finding.threshold} in {finding.window_seconds / 60} min</strong></div><div><span>Window</span><strong>{time(finding.window_start)} – {time(finding.window_end)}</strong></div></div><div className="table-wrapper"><table><thead><tr><th>Event</th><th>Recorded at</th><th>Source IP</th><th>User</th><th>Result</th></tr></thead><tbody>{finding.evidence.map(event => <tr key={event.id}><td>#{event.id}</td><td>{time(event.timestamp)}</td><td className="mono">{event.ip_address}</td><td>{event.username || 'Not provided'}</td><td><span className={`badge ${event.success ? 'badge-ok' : 'badge-fail'}`}>{event.success ? 'Success' : 'Failed'}</span></td></tr>)}</tbody></table></div><p className="evidence-caption">Evidence is captured at detection time and retained with this finding.</p></section>;
}
function FindingReview({ id, onBack, onOpen, canWrite }) {
  const fetchData = useCallback(() => fetchFinding(id), [id]);
  const { data: finding, loading, error } = usePolling(fetchData, null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState(null);
  async function open() {
    if (!canWrite || saving) return;
    setSaving(true); setActionError(null);
    try { const caseData = await createInvestigation({ finding_id: id }); onOpen(caseData.id); }
    catch (error) { setActionError(error.message); }
    finally { setSaving(false); }
  }
  return <><button className="text-btn" onClick={onBack}>← Back to findings</button>{(error || actionError) && <div className="error-banner" role="alert">{error || actionError}</div>}{loading ? <div className="loading">Loading finding…</div> : finding && <><div className="page-header"><div><span className="eyebrow">Finding #{finding.id}</span><h1>{finding.title}</h1><p className="mono">{finding.ip_address}</p></div><button className="btn btn-primary" disabled={saving || (!finding.investigation_id && !canWrite)} onClick={() => finding.investigation_id ? onOpen(finding.investigation_id) : open()}>{saving ? 'Opening…' : finding.investigation_id ? 'View investigation' : 'Open investigation'}</button></div><button className="btn source-history-btn" onClick={() => viewSource(finding.ip_address)}>View source login history</button><div className="panel"><Evidence finding={finding} /></div></>}</>;
}
function CaseDetail({ id, canWrite, users, onBack }) {
  const [caseData, setCaseData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  useEffect(() => {
    let active = true;
    fetchInvestigation(id).then(data => { if (active) { setCaseData(data); setError(null); } }).catch(error => { if (active) setError(error.message); });
    return () => { active = false; };
  }, [id, reloadCount]);
  async function patch(changes) {
    if (busy || !canWrite) return;
    setBusy(true); setError(null);
    try { setCaseData(await updateInvestigation(id, { ...changes, revision: caseData.revision })); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  async function addNote(event) {
    event.preventDefault();
    if (busy || !canWrite) return;
    const form = event.currentTarget;
    const text = new FormData(form).get('text');
    setBusy(true); setError(null);
    try { await addInvestigationNote(id, { text }); setCaseData(await fetchInvestigation(id)); form.reset(); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  return <><button className="text-btn" onClick={onBack}>← Back to investigations</button>{error && <div className="error-banner" role="alert">{error} Use Reload case to retrieve the latest record.</div>}{!caseData ? <div className="loading">{error ? <><p>This investigation could not be loaded.</p><button className="btn" onClick={() => setReloadCount(count => count + 1)}>Reload case</button></> : 'Loading investigation…'}</div> : <>
    <div className="page-header"><div><span className="eyebrow">Investigation #{caseData.id}</span><h1>{caseData.title}</h1><p><span className="badge badge-clean">{labels[caseData.status]}</span> <span className="badge badge-alert">{caseData.severity} severity</span> · {caseData.finding.ip_address}</p></div><div className="header-actions"><button className="btn" onClick={() => viewSource(caseData.finding.ip_address)}>Source login history</button><button className="btn" disabled={busy} onClick={() => setReloadCount(count => count + 1)}>Reload case</button>{caseData.status === 'new' && <button className="btn btn-primary" disabled={busy || !canWrite} onClick={() => patch({ status: 'investigating' })}>Start investigation</button>}{caseData.status === 'resolved' && <button className="btn" disabled={busy || !canWrite} onClick={() => patch({ status: 'investigating' })}>Reopen investigation</button>}</div></div>
    <div className="case-layout"><div className="case-main"><div className="panel"><Evidence finding={caseData.finding} /></div>
      <section className="panel case-section"><h2>Analyst notes</h2>{caseData.notes.length ? <ol className="case-timeline">{caseData.notes.map(note => <li key={note.id}><div><strong>{note.author}</strong>{!note.author_user && <span className="legacy-label">Legacy label</span>}<time>{time(note.created_at)}</time></div><p>{note.text}</p></li>)}</ol> : <p className="section-description">No notes yet. Record what you observed and your next step.</p>}<form onSubmit={addNote}><label className="form-field">New note<textarea disabled={!canWrite || busy} name="text" required maxLength={5000} rows={3} placeholder="Evidence reviewed, observations, and next steps" /></label><button className="btn" disabled={busy || !canWrite}>Add note</button></form></section>
      <section className="panel case-section"><h2>Decision history</h2><ol className="case-timeline">{caseData.history.map(entry => <li key={entry.id}><div><strong>{entry.actor} · {entry.action.replaceAll('_', ' ')}</strong>{!entry.actor_user && <span className="legacy-label">Legacy label</span>}<time>{time(entry.created_at)}</time></div>{Object.keys(entry.after).filter(key => key !== 'revision' && entry.before[key] !== entry.after[key]).map(key => <p key={key}>{key.replaceAll('_', ' ')}: {String(entry.after[key] || '—')}</p>)}</li>)}</ol></section>
    </div><div className="case-aside"><section className="panel case-section"><h2>Case management</h2><form key={`${caseData.revision}-${reloadCount}`} onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); patch({ owner_user: data.get('owner_user') ? Number(data.get('owner_user')) : null, severity: data.get('severity') }); }}><fieldset disabled={busy || !canWrite}><label className="form-field">Assigned analyst<select name="owner_user" defaultValue={caseData.owner_user || ''}><option value="">Unassigned</option>{caseData.owner_user && !users.some(user => user.id === caseData.owner_user) && <option value={caseData.owner_user}>{caseData.owner} (no longer eligible)</option>}{users.map(user => <option key={user.id} value={user.id}>{user.display_name}</option>)}</select></label>{caseData.owner && !caseData.owner_user && <p className="section-description">Previous demo assignment: {caseData.owner}. Select an account to replace this legacy label.</p>}<label className="form-field">Severity<select name="severity" defaultValue={caseData.severity}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label><button className="btn" disabled={!canWrite}>Save assignment & severity</button></fieldset></form><div className="case-dates"><span>Created {time(caseData.created_at)}</span><span>Updated {time(caseData.updated_at)}</span></div></section>
      {caseData.status === 'investigating' && canWrite && <section className="panel case-section"><h2>Resolve investigation</h2><p className="section-description">Record a decision and the evidence supporting it.</p><form onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); patch({ status: 'resolved', disposition: data.get('disposition'), closure_reason: data.get('closure_reason') }); }}><fieldset disabled={busy || !canWrite}><label className="form-field">Disposition<select name="disposition" required defaultValue=""><option value="" disabled>Select an outcome</option><option value="true_positive">True positive</option><option value="false_positive">False positive</option><option value="benign">Benign activity</option></select></label><label className="form-field">Closure reason<textarea name="closure_reason" rows={4} required maxLength={2000} /></label><button className="btn btn-primary" disabled={!canWrite}>Resolve investigation</button></fieldset></form></section>}
      {caseData.status === 'resolved' && <section className="panel case-section"><h2>Recorded resolution</h2><span className="badge badge-ok">{labels[caseData.disposition]}</span><p className="resolution-text">{caseData.closure_reason}</p><span className="section-description">Resolved {time(caseData.resolved_at)}</span></section>}
    </div></div></> }</>;
}
export default function InvestigationsPage() {
  const { user } = useSession();
  const canWrite = user.role === 'admin' || user.role === 'analyst';
  const { data: { findings, cases, users }, loading, error, refresh } = usePolling(fetchQueue, INITIAL);
  const [tab, setTab] = useState('findings');
  const [findingId, setFindingId] = useState(null);
  const [caseId, setCaseId] = useState(() => /^#investigations\/\d+$/.test(location.hash) ? Number(location.hash.split('/')[1]) : null);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [severity, setSeverity] = useState('all');
  useEffect(() => {
    const sync = () => { setCaseId(/^#investigations\/\d+$/.test(location.hash) ? Number(location.hash.split('/')[1]) : null); setFindingId(null); };
    window.addEventListener('popstate', sync);
    window.addEventListener('hashchange', sync);
    return () => { window.removeEventListener('popstate', sync); window.removeEventListener('hashchange', sync); };
  }, []);
  function openCase(id) { setCaseId(id); setFindingId(null); window.history.pushState(null, '', `#investigations/${id}`); }
  function back() { setCaseId(null); setFindingId(null); setTab('cases'); window.history.pushState(null, '', '#investigations'); refresh(); }
  const rows = (tab === 'findings' ? findings : cases).filter(row => {
    const source = tab === 'findings' ? row.ip_address : row.finding.ip_address;
    return [row.title, source, row.owner || ''].some(value => value.toLowerCase().includes(query.trim().toLowerCase())) && (severity === 'all' || row.severity === severity) && (tab === 'findings' || statusFilter === 'all' || row.status === statusFilter);
  });
  return <section className="page"><div className="analyst-bar"><span>Signed in as <strong>{user.display_name}</strong> · {canWrite ? 'Notes and decisions are attributed to your account.' : 'Read-only access. An analyst can update investigations.'}</span></div>{caseId ? <CaseDetail key={caseId} id={caseId} canWrite={canWrite} users={users} onBack={back} /> : findingId ? <FindingReview id={findingId} canWrite={canWrite} onOpen={openCase} onBack={() => setFindingId(null)} /> : <>
    <div className="page-header"><div><span className="eyebrow">Analyst workspace</span><h1>Investigations</h1><p>Review detection evidence, track cases, and record decisions.</p></div><button className="btn" onClick={refresh}><Icon name="refresh" size={16} />Refresh</button></div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <div className="stats-row"><div className="stat-card"><div className="stat-label">Detection findings</div><div className="stat-value">{findings.length}</div></div><div className="stat-card"><div className="stat-label">New cases</div><div className="stat-value">{cases.filter(row => row.status === 'new').length}</div></div><div className="stat-card"><div className="stat-label">Investigating</div><div className="stat-value">{cases.filter(row => row.status === 'investigating').length}</div></div><div className="stat-card"><div className="stat-label">Resolved</div><div className="stat-value">{cases.filter(row => row.status === 'resolved').length}</div></div></div>
    <div className="panel"><div className="queue-tabs" role="group" aria-label="Investigation queue"><button className={`nav-btn ${tab === 'findings' ? 'active' : ''}`} aria-pressed={tab === 'findings'} onClick={() => setTab('findings')}>Findings</button><button className={`nav-btn ${tab === 'cases' ? 'active' : ''}`} aria-pressed={tab === 'cases'} onClick={() => setTab('cases')}>Cases</button></div><div className="filter-bar"><label className="search-field"><Icon name="search" /><span className="sr-only">Search findings and cases</span><input type="search" placeholder="Search title, source IP, or owner" value={query} onChange={event => setQuery(event.target.value)} /></label><label><span className="sr-only">Severity filter</span><select value={severity} onChange={event => setSeverity(event.target.value)}><option value="all">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>{tab === 'cases' && <label><span className="sr-only">Case status filter</span><select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}><option value="all">All statuses</option><option value="new">New</option><option value="investigating">Investigating</option><option value="resolved">Resolved</option></select></label>}</div>
    {loading ? <div className="loading">Loading investigation queue…</div> : !rows.length ? <div className="empty">{error ? 'The queue could not be refreshed.' : 'No matching records. New detection findings appear when a login rule triggers.'}</div> : <div className="table-wrapper"><table><thead><tr><th>Record</th><th>Source IP</th><th>Severity</th><th>{tab === 'cases' ? 'Status' : 'Evidence'}</th><th>{tab === 'cases' ? 'Owner' : 'Detected'}</th><th>Action</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.title}</strong><span className="record-id">#{row.id}</span></td><td className="mono">{tab === 'cases' ? row.finding.ip_address : row.ip_address}</td><td><span className="badge badge-alert">{row.severity}</span></td><td>{tab === 'cases' ? labels[row.status] : `${row.observed_count} attempts`}</td><td>{tab === 'cases' ? row.owner || 'Unassigned' : time(row.detected_at)}</td><td><button className="inspect-btn" onClick={() => tab === 'cases' ? openCase(row.id) : setFindingId(row.id)}>{tab === 'cases' ? 'Open case' : 'Review finding'}<Icon name="arrow" size={14} /></button></td></tr>)}</tbody></table></div>}</div>
  </>}</section>;
}
