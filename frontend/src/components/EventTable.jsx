import Icon from './Icon';

export default function EventTable({ events, loading, onInspect }) {
  if (loading) return <div className="loading" role="status">Loading events…</div>;
  if (!events.length) return <div className="empty">No events match these filters.</div>;
  return (
    <div className="table-wrapper">
      <table>
        <thead><tr><th scope="col">Event</th><th scope="col">Source IP</th><th scope="col">User</th><th scope="col">Timestamp</th><th scope="col">Result</th><th scope="col">Detection</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
        <tbody>{events.map(event => (
          <tr key={event.id} className={event.is_suspicious ? 'row-suspicious' : ''}>
            <td className="id-col">#{event.id}</td><td className="ip-col">{event.ip_address}</td>
            <td>{event.username || <span className="muted">Not provided</span>}</td>
            <td className="time-col"><time dateTime={event.timestamp}>{event.timestamp ? new Date(event.timestamp).toLocaleString() : 'Unavailable'}</time></td>
            <td><span className={`badge ${event.success ? 'badge-ok' : 'badge-fail'}`}><span className="badge-dot" />{event.success ? 'Success' : 'Failed'}</span></td>
            <td><span className={`badge ${event.is_suspicious ? 'badge-alert' : 'badge-clean'}`}>{event.is_suspicious ? 'Flagged' : 'Not flagged'}</span></td>
            <td><button className="inspect-btn" aria-label={`Inspect event ${event.id}`} onClick={() => onInspect(event)}>Details<Icon name="arrow" size={14} /></button></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
