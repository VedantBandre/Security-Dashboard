export default function StatCard({ label, value, variant, description }) {
  return (
    <div className={`stat-card stat-card--${variant || 'default'}`}>
      <div className="stat-label"><span className="stat-dot" />{label}</div>
      <div className="stat-value">{value ?? '—'}</div>
      <div className="stat-description">{description}</div>
    </div>
  );
}
