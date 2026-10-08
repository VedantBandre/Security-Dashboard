export default function ActivitySummary({ events, now }) {
  const end = Math.floor(now / 3600000) * 3600000 + 3600000;
  const start = end - 24 * 3600000;
  const buckets = Array.from({ length: 24 }, (_, index) => ({ time: start + index * 3600000, success: 0, failed: 0 }));
  const sources = new Map();
  for (const event of events) {
    const time = event.timestamp ? new Date(event.timestamp).getTime() : NaN;
    if (time >= start && time <= now) {
      buckets[Math.floor((time - start) / 3600000)][event.success ? 'success' : 'failed'] += 1;
    }
    const source = sources.get(event.ip_address) || { ip: event.ip_address, total: 0, flagged: 0 };
    source.total += 1;
    source.flagged += Number(event.is_suspicious);
    sources.set(event.ip_address, source);
  }
  const highest = Math.max(1, ...buckets.map(bucket => bucket.success + bucket.failed));
  const topSources = [...sources.values()].sort((a, b) => b.total - a.total).slice(0, 4);
  const recentCount = buckets.reduce((total, bucket) => total + bucket.success + bucket.failed, 0);
  return (
    <div className="insight-grid">
      <section className="panel activity-panel" aria-label="Recent authentication activity">
        <div className="panel-header"><div><h2>Authentication activity</h2><p>Hourly login volume · recent activity</p></div><span className="subtle-count">{recentCount} events</span></div>
        <div className="chart-legend"><span><i className="legend-success" />Successful</span><span><i className="legend-failed" />Failed</span></div>
        <div className="activity-chart" role="img" aria-label={`${recentCount} login events in the last 24 hourly buckets. ${buckets.reduce((total, bucket) => total + bucket.failed, 0)} failed.`}>
          {buckets.map(bucket => <div className="chart-column" key={bucket.time} title={`${new Date(bucket.time).toLocaleString()}: ${bucket.success} successful, ${bucket.failed} failed`}><div className="chart-stack"><div className="bar-success" style={{ height: `${bucket.success / highest * 100}%` }} /><div className="bar-failed" style={{ height: `${bucket.failed / highest * 100}%` }} /></div></div>)}
        </div>
        <div className="chart-axis"><span>{new Date(start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><span>{new Date(start + 12 * 3600000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><span>Now</span></div>
      </section>
      <section className="panel sources-panel" aria-label="Most active source IPs"><div className="panel-header"><div><h2>Top source IPs</h2><p>Ranked by event volume · all time</p></div></div><div className="source-list">{topSources.length ? topSources.map(source => <div className="source-item" key={source.ip}><div><strong className="mono">{source.ip}</strong><span>{source.flagged ? `${source.flagged} flagged events` : 'No flagged events'}</span></div><span className="source-count">{source.total}<small>events</small></span></div>) : <p className="muted">Source activity will appear as events arrive.</p>}</div></section>
    </div>
  );
}
