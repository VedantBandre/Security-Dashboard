const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
let csrfToken = null;
export function setCsrfToken(token) { csrfToken = token; }

async function request(path, options = {}) {
    const method = options.method || 'GET';
    const headers = { ...options.headers };
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) headers['X-CSRFToken'] = csrfToken;
    const res = await fetch(`${BASE}${path}`, { ...options, credentials: 'include', headers });
    const contentType = res.headers?.get('content-type') || '';
    const data = contentType.includes('text/html') ? { detail: 'The request was rejected. Reload the page and try again.' } : await res.json();
    if (!res.ok) {
        if (data.code === 'not_authenticated') window.dispatchEvent(new Event('session-expired'));
        if (data.code === 'permission_denied') window.dispatchEvent(new Event('session-recheck'));
        const messages = Object.entries(data).filter(([field]) => field !== 'code').map(([field, value]) => `${field === 'detail' ? '' : `${field}: `}${Array.isArray(value) ? value.join(' ') : value}`).join(' ');
        throw new Error(messages || 'The request could not be completed.');
    }
    return data;
}
const jsonOptions = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
export const fetchSession = () => request('/auth/session');
export const signIn = data => request('/auth/login', jsonOptions('POST', data));
export const signOut = () => request('/auth/logout', jsonOptions('POST', {}));
export const fetchEvents = () => request('/events');
export const fetchSuspicious = () => request('/suspicious');
export const fetchStats = () => request('/stats');
export const postLoginAttempt = data => request('/login-attempt', jsonOptions('POST', data));
export const fetchFindings = () => request('/findings');
export const fetchFinding = id => request(`/findings/${id}`);
export const fetchInvestigations = () => request('/investigations');
export const fetchInvestigation = id => request(`/investigations/${id}`);
export const createInvestigation = data => request('/investigations', jsonOptions('POST', data));
export const updateInvestigation = (id, data) => request(`/investigations/${id}`, jsonOptions('PATCH', data));
export const addInvestigationNote = (id, data) => request(`/investigations/${id}/notes`, jsonOptions('POST', data));
export const fetchAssignableUsers = () => request('/users/assignable');
export const fetchUsers = () => request('/users');
export const fetchAccessHistory = () => request('/users/access-history');
export const createUser = data => request('/users', jsonOptions('POST', data));
export const updateUser = (id, data) => request(`/users/${id}`, jsonOptions('PATCH', data));
