import { fetchSuspicious } from '../api';
import EventWorkspace from '../components/EventWorkspace';
import Icon from '../components/Icon';
import usePolling from '../hooks/usePolling';

const INITIAL_EVENTS = [];
export default function SuspiciousPage() {
  const { data: events, loading, error, lastRefresh, refresh } = usePolling(fetchSuspicious, INITIAL_EVENTS);
  return (
    <section className="page">
      <div className="page-header"><div><span className="eyebrow">Detection review</span><h1>Suspicious activity</h1><p>Review flagged login attempts and investigate the surrounding evidence.</p></div><div className="header-actions">{lastRefresh && <span className={`refresh-note ${error ? 'refresh-stale' : ''}`}><span className="status-dot" />{error ? 'Update unavailable' : 'Updates every 5s'}<small>Last sync {lastRefresh.toLocaleTimeString()}</small></span>}<button className="btn" onClick={refresh}><Icon name="refresh" size={16} />Refresh</button></div></div>
      {error && <div className="error-banner" role="alert">{error}. Displayed data may be out of date. Retry with Refresh.</div>}
      {(!error || events.length > 0) && <EventWorkspace events={events} loading={loading} suspiciousOnly />}
    </section>
  );
}
