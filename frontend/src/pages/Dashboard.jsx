import { fetchEvents, fetchStats } from '../api';
import EventTable from '../components/EventTable';
import StatCard from '../components/StatCard';
import usePolling from '../hooks/usePolling';

const INITIAL_DATA = { events: [], stats: {} };

async function fetchDashboard() {
    const [events, stats] = await Promise.all([fetchEvents(), fetchStats()]);
    return { events, stats };
}

export default function Dashboard() {
    const { data: { events, stats }, loading, error, lastRefresh, refresh } = usePolling(
        fetchDashboard, INITIAL_DATA,
    );

    return (
        <section className="page">
            <div className="page-header">
                <h1>Event Dashboard</h1>
                {lastRefresh && (
                    <span className="refresh-note">
                        Last refresh: {lastRefresh.toLocaleTimeString()}
                    </span>
                )}
                <button className="btn" onClick={refresh}>Refresh</button>
            </div>

            {error && <div className="error-banner" role="alert">! {error} !</div>}

            <div className="stats-row">
                <StatCard label="Total Events" value={stats?.total} variant="default" />
                <StatCard label="Successful Logins" value={stats?.succeeded} variant="ok" />
                <StatCard label="Failed Logins" value={stats?.failed} variant="fail" />
                <StatCard label="Suspicious Events" value={stats?.suspicious} variant="alert" />
            </div>

            {(!error || events.length > 0) && <EventTable events={events} loading={loading} />}
        </section>
    );
}
