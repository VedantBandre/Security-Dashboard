export function filterEvents(events, { query, result, detection, period }, now = Date.now()) {
  const needle = query.trim().toLowerCase();
  const window = period === '24h' ? 86400000 : period === '7d' ? 604800000 : null;
  return events.filter(event => {
    const matchesQuery = !needle || [event.ip_address, event.username || '', String(event.id)].some(value => value.toLowerCase().includes(needle));
    const matchesResult = result === 'all' || event.success === (result === 'success');
    const matchesDetection = detection === 'all' || event.is_suspicious === (detection === 'flagged');
    const timestamp = new Date(event.timestamp).getTime();
    return matchesQuery && matchesResult && matchesDetection && (!window || (event.timestamp && timestamp >= now - window && timestamp <= now));
  });
}

export function eventsCsv(events) {
  const cell = value => {
    let text = String(value ?? '');
    // Prevent spreadsheet formulas in untrusted event fields.
    if (/^[\s]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  return ['id,timestamp,ip_address,username,success,is_suspicious', ...events.map(event => [event.id, event.timestamp, event.ip_address, event.username, event.success, event.is_suspicious].map(cell).join(','))].join('\r\n');
}
