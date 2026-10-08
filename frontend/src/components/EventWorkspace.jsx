import { useState } from 'react';
import EventTable from './EventTable';
import EventDetails from './EventDetails';
import Icon from './Icon';
import { filterEvents, eventsCsv } from '../utils/events';

const PAGE_SIZE = 25;
export default function EventWorkspace({ events, loading, suspiciousOnly = false }) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('all');
  const [detection, setDetection] = useState('all');
  const [period, setPeriod] = useState('all');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [sourceIp, setSourceIp] = useState(null);
  const filtered = filterEvents(sourceIp ? events.filter(event => event.ip_address === sourceIp) : events, { query, result, detection, period });
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages);
  const start = (currentPage - 1) * PAGE_SIZE;
  function change(setter, value) { setter(value); setPage(1); }
  function exportCsv() {
    const url = URL.createObjectURL(new Blob([eventsCsv(filtered)], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `security-events-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section className="panel event-panel" aria-label="Event explorer">
      <div className="panel-header"><div><h2>{suspiciousOnly ? 'Flagged login events' : 'Event explorer'}</h2><p>{suspiciousOnly ? 'Inspect the evidence behind suspicious source activity.' : 'Search, inspect, and export authentication activity.'}</p></div><button className="btn" disabled={loading || !filtered.length} onClick={exportCsv}><Icon name="download" size={16} />Export CSV</button></div>
      <div className="filter-bar">
        <label className="search-field"><Icon name="search" size={17} /><span className="sr-only">Search events</span><input type="search" placeholder="Search IP, user, or event ID" value={query} onChange={e => change(setQuery, e.target.value)} /></label>
        <label className="select-field"><span className="sr-only">Result filter</span><select value={result} onChange={e => change(setResult, e.target.value)}><option value="all">All results</option><option value="failed">Failed logins</option><option value="success">Successful logins</option></select></label>
        {!suspiciousOnly && <label className="select-field"><span className="sr-only">Detection filter</span><select value={detection} onChange={e => change(setDetection, e.target.value)}><option value="all">All detections</option><option value="flagged">Flagged</option><option value="unflagged">Not flagged</option></select></label>}
        <label className="select-field"><span className="sr-only">Time range</span><select value={period} onChange={e => change(setPeriod, e.target.value)}><option value="all">All time</option><option value="24h">Last 24 hours</option><option value="7d">Last 7 days</option></select></label>
        {sourceIp && <span className="badge badge-clean">Source: {sourceIp}</span>}
        {(query || sourceIp || result !== 'all' || detection !== 'all' || period !== 'all') && <button className="text-btn" onClick={() => { setQuery(''); setSourceIp(null); setResult('all'); setDetection('all'); setPeriod('all'); setPage(1); }}>Clear filters</button>}
      </div>
      {suspiciousOnly && !loading && !events.length ? <div className="empty all-clear"><Icon name="shield" size={28} /><strong>No suspicious activity detected</strong><span>Flagged events will appear here when a detection rule triggers.</span></div> : <EventTable events={filtered.slice(start, start + PAGE_SIZE)} loading={loading} onInspect={setSelected} />}
      <div className="table-footer"><span>{loading ? 'Loading events' : `${filtered.length ? start + 1 : 0}–${Math.min(start + PAGE_SIZE, filtered.length)} of ${filtered.length} events`}</span><div className="pagination"><button className="btn" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Previous</button><span>{currentPage} / {pages}</span><button className="btn" disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}>Next</button></div></div>
      {selected && <EventDetails event={selected} onClose={() => setSelected(null)} onFilter={ip => { setSourceIp(ip); setQuery(''); setResult('all'); setDetection('all'); setPeriod('all'); setPage(1); }} />}
    </section>
  );
}
