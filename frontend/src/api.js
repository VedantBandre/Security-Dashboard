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
async function workflowRequest(path, options) {
    const res = await fetch(`${BASE}${path}`, options);
    const data = await res.json();
    if (!res.ok) {
        const messages = Object.entries(data).map(([field, value]) => `${field === 'detail' ? '' : `${field}: `}${Array.isArray(value) ? value.join(' ') : value}`).join(' ');
        throw new Error(messages || 'The request could not be completed.');
    }
    return data;
}
const jsonOptions = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
export const fetchFindings = () => workflowRequest('/findings');
export const fetchFinding = id => workflowRequest(`/findings/${id}`);
export const fetchInvestigations = () => workflowRequest('/investigations');
export const fetchInvestigation = id => workflowRequest(`/investigations/${id}`);
export const createInvestigation = data => workflowRequest('/investigations', jsonOptions('POST', data));
export const updateInvestigation = (id, data) => workflowRequest(`/investigations/${id}`, jsonOptions('PATCH', data));
export const addInvestigationNote = (id, data) => workflowRequest(`/investigations/${id}/notes`, jsonOptions('POST', data));
