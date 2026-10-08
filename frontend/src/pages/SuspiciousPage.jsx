import { fetchSuspicious } from '../api';
import EventTable from '../components/EventTable';
import usePolling from '../hooks/usePolling';

const INITIAL_EVENTS = [];

export default function SuspiciousPage() {
    const { data: events, loading, error, refresh } = usePolling(fetchSuspicious, INITIAL_EVENTS);

    return (
        <section className="page">
            <div className="page-header">
                <h1>! Suspicious Activity !</h1>
                <button className="btn" onClick={refresh}>Refresh</button>
            </div>

            {error && <div className="error-banner" role="alert">! {error} !</div>}

            {!loading && !error && events.length === 0 && (
                <div className="empty all-clear">No suspicious activity detected</div>
            )}

            {(loading || events.length > 0) && <EventTable events={events} loading={loading} />}
        </section>
    );
}
