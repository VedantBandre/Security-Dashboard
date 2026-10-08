export default function EventTable({ events, loading }) {
    if (loading) return <div className="loading">Loading events...</div>;
    if (!events.length) return <div className="empty">No events recorded yet</div>;
    
    return (
        <div className="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>IP Address</th>
                        <th>Username</th>
                        <th>Time</th>
                        <th>Result</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                   {events.map((e) => (
                    <tr key={e.id} className={e.is_suspicious ? 'row-suspicious' : ''}>
                    <td className="id-col">{e.id}</td>
                    <td className="ip-col">{e.ip_address}</td>
                    <td>{e.username || <span className="muted">-</span>}</td>
                    <td className="time-col">{new Date(e.timestamp).toLocaleTimeString()}</td>
                    <td>
                        <span className={`badge ${e.success ? 'badge-ok' : 'badge-fail'}`}>
                            {e.success ? 'SUCCESS' : 'FAILED'}
                        </span>
                    </td>
                    <td>
                        {e.is_suspicious ? (
                            <span className="badge badge-alert">! SUSPICIOUS !</span>
                        ) : (
                            <span className="badge badge-clean">CLEAN</span>
                        )}
                    </td>
                    </tr>
                   ))} 
                </tbody>
            </table>
        </div>
    );
}