import { useEffect, useRef } from 'react';
import Icon from './Icon';

export default function EventDetails({ event, onClose, onFilter }) {
  const dialog = useRef(null);
  useEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => element.close();
  }, []);
  return (
    <dialog className="event-dialog" ref={dialog} aria-labelledby="event-detail-title" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="detail-header"><div><span className="eyebrow">Event inspection</span><h2 id="event-detail-title">Login attempt #{event.id}</h2></div><button className="icon-btn" aria-label="Close event details" onClick={onClose}><Icon name="close" /></button></div>
      <div className="detail-body">
        <div className={`detail-notice ${event.is_suspicious ? 'flagged-notice' : ''}`}><Icon name={event.is_suspicious ? 'alert' : 'shield'} /><div><strong>{event.is_suspicious ? 'Flagged source IP' : 'No detection flag'}</strong><p>{event.is_suspicious ? 'This event belongs to an IP flagged by detection rules. Review related attempts before drawing a conclusion.' : 'This event has not been flagged. A successful login alone does not establish that activity is legitimate.'}</p></div></div>
        <dl className="detail-fields"><div><dt>Source IP</dt><dd className="mono">{event.ip_address}</dd></div><div><dt>User</dt><dd>{event.username || 'Not provided'}</dd></div><div><dt>Recorded at</dt><dd>{event.timestamp ? new Date(event.timestamp).toLocaleString() : 'Unavailable'}</dd></div><div><dt>Result</dt><dd>{event.success ? 'Successful login' : 'Failed login'}</dd></div></dl>
        <div className="detail-section"><h3>Event record</h3><pre>{JSON.stringify(event, null, 2)}</pre></div>
      </div>
      <div className="detail-footer"><button className="btn" onClick={onClose}>Close</button><button className="btn btn-primary" onClick={() => { onFilter(event.ip_address); onClose(); }}>View this IP’s events<Icon name="arrow" size={16} /></button></div>
    </dialog>
  );
}
