export default function StatCard({ label, value, variant }) {
    return (
        <div className={`stat-card stat-card--${variant || 'default'}`}>
            <div className="stat-value">{value ?? '-'}</div>
            <div className="stat-label">{label}</div>
        </div>
    );
}