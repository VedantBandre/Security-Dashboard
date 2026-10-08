const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

export async function fetchEvents() {
    const res = await fetch(`${BASE}/events`);
    if (!res.ok) {
        throw new Error('Failed to fetch events');
    }
    return res.json();
}

export async function fetchSuspicious() {
    const res = await fetch(`${BASE}/suspicious`);
    if (!res.ok) throw new Error('Failed to fetch suspicious events');
    return res.json();
}

export async function fetchStats() {
    const res = await fetch(`${BASE}/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

export async function postLoginAttempt(payload) {
    const res = await fetch(`${BASE}/login-attempt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to post login attempt');
    return res.json();
}