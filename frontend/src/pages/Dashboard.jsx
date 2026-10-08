import { fetchEvents, fetchStats } from '../api';
import EventWorkspace from '../components/EventWorkspace';
import ActivitySummary from '../components/ActivitySummary';
import StatCard from '../components/StatCard';
import Icon from '../components/Icon';
import usePolling from '../hooks/usePolling';

const INITIAL_DATA = { events: [], stats: {} };
async function fetchDashboard() {
  const [events, stats] = await Promise.all([fetchEvents(), fetchStats()]);
  return { events, stats };
}
export default function Dashboard() {
  const { data: { events, stats }, loading, error, lastRefresh, refresh } = usePolling(fetchDashboard, INITIAL_DATA);
  return (
    <section className="page">
      <div className="page-header"><div><span className="eyebrow">Authentication monitoring</span><h1>Security overview</h1><p>Understand login activity and investigate suspicious sources.</p></div><div className="header-actions">{lastRefresh && <span className={`refresh-note ${error ? 'refresh-stale' : ''}`}><span className="status-dot" />{error ? 'Update unavailable' : 'Updates every 5s'}<small>Last sync {lastRefresh.toLocaleTimeString()}</small></span>}<button className="btn" onClick={refresh}><Icon name="refresh" size={16} />Refresh</button></div></div>
      {error && <div className="error-banner" role="alert">{error}. Displayed data may be out of date. Retry with Refresh.</div>}
      <div className="stats-row"><StatCard label="Total Events" value={stats.total} description="All recorded login attempts" /><StatCard label="Successful Logins" value={stats.succeeded} variant="ok" description="Authentication succeeded" /><StatCard label="Failed Logins" value={stats.failed} variant="fail" description="Authentication was unsuccessful" /><StatCard label="Suspicious Events" value={stats.suspicious} variant="alert" description="Events associated with flagged IPs" /></div>
      {!loading && (!error || events.length > 0) && <ActivitySummary events={events} now={lastRefresh.getTime()} />}
      {(!error || events.length > 0) && <EventWorkspace events={events} loading={loading} />}
    </section>
  );
}
