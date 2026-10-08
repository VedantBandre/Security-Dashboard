import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';
import { JSDOM, VirtualConsole } from 'jsdom';
import { eventsCsv, filterEvents } from '../src/utils/events.js';

const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
const entry = html.match(/<script[^>]*src="([^"]+)"/);
assert.ok(entry, 'The built HTML must load the application');
const bundle = await readFile(new URL(`../dist${entry[1]}`, import.meta.url), 'utf8');

const event = {
    id: 1, ip_address: '10.0.0.99', username: 'alice',
    timestamp: '2026-10-08T10:00:00Z', success: false, is_suspicious: true,
};

async function waitFor(check) {
    for (let count = 0; count < 100; count += 1) {
        if (check()) return;
        await delay(10);
    }
    assert.fail('Timed out waiting for the dashboard');
}

function mount(t, respond, savedTheme, hash = '', defaultSession = true) {
    const errors = [];
    const console = new VirtualConsole();
    console.on('jsdomError', (error) => errors.push(error));
    const dom = new JSDOM(html, {
        url: `http://localhost:5173/${hash}`, runScripts: 'outside-only', virtualConsole: console,
    });
    const calls = [];
    if (savedTheme) dom.window.localStorage.setItem('security-dashboard-theme', savedTheme);
    // JSDOM does not implement the native dialog lifecycle.
    dom.window.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
    dom.window.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
    const intervals = new Map();
    let nextId = 0;
    dom.window.setInterval = (callback, milliseconds) => {
        assert.equal(milliseconds, 5000);
        intervals.set(++nextId, callback);
        return nextId;
    };
    dom.window.clearInterval = (id) => intervals.delete(id);
    dom.window.fetch = async (url, options) => {
        if (defaultSession && url === '/auth/session') return { ok: true, json: async () => ({ user: { id: 1, username: 'analyst-a', display_name: 'Analyst A', role: 'analyst' }, csrf_token: 'test-csrf' }) };
        if (defaultSession && url === '/users/assignable') return { ok: true, json: async () => [ { id: 1, username: 'analyst-a', display_name: 'Analyst A' }, { id: 2, username: 'analyst-b', display_name: 'Analyst B' } ] };
        calls.push(url);
        return respond(url, options);
    };
    t.after(() => {
        dom.window.close();
        assert.deepEqual(errors, [], 'The application must not raise runtime errors');
    });
    dom.window.eval(bundle);
    const document = dom.window.document;
    const click = (text) => {
        const button = [...document.querySelectorAll('button')].find((item) => item.textContent === text);
        assert.ok(button, `Missing ${text} button`);
        button.click();
    };
    return { document, calls, intervals, click, window: dom.window };
}

function success(url) {
    return {
        ok: true,
        json: async () => url.endsWith('/stats')
            ? { total: 1, failed: 1, succeeded: 0, suspicious: 1 }
            : [event],
    };
}

test('built application renders API data, refreshes, polls, and switches tabs', async (t) => {
    const app = mount(t, success);
    await waitFor(() => app.document.querySelector('tbody tr'));
    assert.match(app.document.body.textContent, /alice/);
    assert.match(app.document.body.textContent, /Suspicious Events/);
    assert.deepEqual(app.calls, ['/events', '/stats']);
    app.click('Refresh');
    await waitFor(() => app.calls.length === 4);
    await delay(20);
    for (const callback of app.intervals.values()) callback();
    await waitFor(() => app.calls.length === 6);
    app.click('Suspicious');
    await waitFor(() => app.calls.includes('/suspicious'));
    await waitFor(() => app.document.querySelector('tbody tr'));
    assert.equal(app.intervals.size, 1, 'Tab changes must clean up the previous poller');
});

test('theme toggles and restores the saved preference', async (t) => {
    const app = mount(t, success);
    await waitFor(() => app.document.querySelector('.theme-toggle') && app.document.documentElement.dataset.theme === 'light');
    app.click('Dark mode');
    await waitFor(() => app.document.documentElement.dataset.theme === 'dark');
    assert.equal(app.window.localStorage.getItem('security-dashboard-theme'), 'dark');
    const restored = mount(t, success, 'dark');
    await waitFor(() => restored.document.querySelector('.theme-toggle') && restored.document.documentElement.dataset.theme === 'dark');
    restored.click('Light mode');
    await waitFor(() => restored.document.documentElement.dataset.theme === 'light');
});

test('search, inspection, exact IP drilldown, and clearing filters work', async (t) => {
    const other = { ...event, id: 2, ip_address: '10.0.0.9', username: 'bob', is_suspicious: false };
    const app = mount(t, url => url.endsWith('/stats') ? success(url) : { ok: true, json: async () => [event, other] });
    await waitFor(() => app.document.querySelectorAll('tbody tr').length === 2);
    const input = app.document.querySelector('input[type="search"]');
    Object.getOwnPropertyDescriptor(app.window.HTMLInputElement.prototype, 'value').set.call(input, 'alice');
    input.dispatchEvent(new app.window.Event('input', { bubbles: true }));
    await waitFor(() => app.document.querySelectorAll('tbody tr').length === 1);
    app.document.querySelector('[aria-label="Inspect event 1"]').click();
    await waitFor(() => app.document.querySelector('dialog[open]'));
    assert.match(app.document.querySelector('dialog').textContent, /10.0.0.99/);
    app.click('View this IP’s events');
    await waitFor(() => !app.document.querySelector('dialog'));
    assert.equal(app.document.querySelectorAll('tbody tr').length, 1);
    assert.match(app.document.body.textContent, /Source: 10.0.0.99/);
    app.click('Clear filters');
    await waitFor(() => app.document.querySelectorAll('tbody tr').length === 2);
});

test('combined filters handle time boundaries and CSV safely escapes event fields', () => {
    const now = Date.parse('2026-10-08T12:00:00Z');
    const recent = { ...event, username: '=HYPERLINK("example")' };
    const old = { ...event, id: 2, timestamp: '2026-10-06T10:00:00Z', success: true };
    const filters = { query: '10.0.0', result: 'failed', detection: 'flagged', period: '24h' };
    assert.deepEqual(filterEvents([recent, old], filters, now), [recent]);
    assert.deepEqual(filterEvents([recent], { ...filters, result: 'success' }, now), []);
    assert.match(eventsCsv([recent]), /"'=HYPERLINK\(""example""\)"/);
    assert.ok(eventsCsv([recent]).startsWith('id,timestamp,ip_address,username,success,is_suspicious\r\n'));
});

test('failed requests do not show an all-clear and manual refresh recovers', async (t) => {
    let failing = true;
    const app = mount(t, (url) => failing ? { ok: false, json: async () => ({ detail: `Failed to fetch ${url}` }) } : success(url));
    await waitFor(() => app.document.querySelector('.error-banner'));
    assert.equal(app.document.querySelector('.empty'), null);
    app.click('Suspicious');
    await waitFor(() => app.document.querySelector('.error-banner')?.textContent.includes('suspicious'));
    assert.equal(app.document.querySelector('.all-clear'), null);
    failing = false;
    app.click('Refresh');
    await waitFor(() => app.document.querySelector('tbody tr'));
    assert.equal(app.document.querySelector('.error-banner'), null);
});

test('an empty successful response shows one styled all-clear message', async (t) => {
    const app = mount(t, (url) => ({
        ok: true, json: async () => url.endsWith('/stats') ? {} : [],
    }));
    await waitFor(() => app.document.querySelector('.empty'));
    app.click('Suspicious');
    await waitFor(() => app.document.querySelector('.all-clear'));
    assert.equal(app.document.querySelectorAll('.empty').length, 1);
});

test('finding review creates a case and persists notes, assignment, resolution, and deep links', async (t) => {
    const finding = { id: 10, ip_address: event.ip_address, rule_id: 'brute_force', rule_version: 1,
        title: 'Repeated failed logins', severity: 'high', threshold: 5, observed_count: 6,
        window_seconds: 300, window_start: event.timestamp, window_end: event.timestamp,
        detected_at: event.timestamp, evidence: [event], investigation_id: null };
    let record = null;
    const actions = [];
    const reply = data => ({ ok: true, json: async () => structuredClone(data) });
    function respond(url, options = {}) {
        const payload = options.body ? JSON.parse(options.body) : null;
        if (url === '/findings') return reply([finding]);
        if (url === '/findings/10') return reply(finding);
        if (url === '/investigations' && options.method === 'POST') {
            assert.equal(payload.finding_id, 10);
            record = { id: 42, title: 'Source investigation', severity: 'high', status: 'new', owner: '',
                disposition: '', closure_reason: '', revision: 1, finding, notes: [], history: [],
                created_at: event.timestamp, updated_at: event.timestamp, resolved_at: null };
            finding.investigation_id = 42;
            return reply(record);
        }
        if (url === '/investigations') return reply(record ? [record] : []);
        if (url === '/investigations/42' && options.method === 'PATCH') {
            assert.equal(payload.revision, record.revision);
            actions.push(payload);
            const { revision, ...changes } = payload;
            assert.equal(payload.actor, undefined);
            if ('owner_user' in changes) changes.owner = changes.owner_user === 2 ? 'analyst-b' : '';
            const actor = 'analyst-a';
            record = { ...record, ...changes, revision: revision + 1 };
            if (changes.status === 'resolved') record.resolved_at = event.timestamp;
            record.history.push({ id: record.revision, actor, action: changes.status === 'resolved' ? 'resolved' : 'updated', before: {}, after: changes, created_at: event.timestamp });
            return reply(record);
        }
        if (url === '/investigations/42/notes') {
            const note = { id: 1, author: 'analyst-a', author_user: 1, text: payload.text, created_at: event.timestamp };
            record.notes.push(note);
            return reply(note);
        }
        if (url === '/investigations/42') return reply(record);
        return success(url);
    }
    const app = mount(t, respond);
    await waitFor(() => app.document.querySelector('.nav-links'));
    app.click('Investigations');
    await waitFor(() => app.document.querySelector('.queue-tabs'));
    await waitFor(() => [...app.document.querySelectorAll('button')].some(button => button.textContent === 'Review finding'));
    app.click('Review finding');
    await waitFor(() => app.document.querySelector('.evidence-summary'));
    app.click('Open investigation');
    await waitFor(() => [...app.document.querySelectorAll('button')].some(button => button.textContent === 'Start investigation'));
    app.click('Start investigation');
    await waitFor(() => record.status === 'investigating' && app.document.querySelector('[name="disposition"]'));
    app.document.querySelector('[name="owner_user"]').value = '2';
    app.click('Save assignment & severity');
    await waitFor(() => app.document.body.textContent.includes('owner: analyst-b') && !app.document.querySelector('[name="owner_user"]').closest('fieldset').disabled);
    app.document.querySelector('[name="text"]').value = 'Reviewed the captured evidence.';
    app.click('Add note');
    await waitFor(() => app.document.body.textContent.includes('Reviewed the captured evidence.'));
    app.document.querySelector('[name="disposition"]').value = 'true_positive';
    app.document.querySelector('[name="closure_reason"]').value = 'Repeated failures confirmed.';
    app.click('Resolve investigation');
    await waitFor(() => app.document.body.textContent.includes('Recorded resolution'));
    assert.equal(record.status, 'resolved');
    assert.equal(record.notes.length, 1);
    assert.equal(actions.at(-1).closure_reason, 'Repeated failures confirmed.');
    const reloaded = mount(t, respond, null, '#investigations/42');
    await waitFor(() => reloaded.document.body.textContent.includes('Recorded resolution'));
    assert.match(reloaded.document.body.textContent, /Reviewed the captured evidence/);
    assert.match(reloaded.document.body.textContent, /Repeated failures confirmed/);
});

test('sign-in gates data, sends CSRF, and sign-out removes the workspace', async t => {
    let signedIn = false;
    const user = { id: 1, username: 'analyst-a', display_name: 'Analyst A', role: 'analyst' };
    const reply = data => ({ ok: true, json: async () => data });
    const app = mount(t, (url, options) => {
        if (url === '/auth/session') return reply({ user: signedIn ? user : null, csrf_token: 'initial-token' });
        if (url === '/auth/login') {
            assert.equal(options.headers['X-CSRFToken'], 'initial-token');
            assert.equal(options.credentials, 'include');
            assert.deepEqual(JSON.parse(options.body), { username: 'analyst-a', password: 'test-password' });
            signedIn = true;
            return reply({ user, csrf_token: 'rotated-token' });
        }
        if (url === '/auth/logout') {
            assert.equal(options.headers['X-CSRFToken'], 'rotated-token');
            signedIn = false;
            return reply({ user: null, csrf_token: 'logout-token' });
        }
        assert.ok(signedIn, 'No workspace requests before authentication');
        return success(url);
    }, null, '', false);
    await waitFor(() => app.document.querySelector('[name="password"]'));
    assert.deepEqual(app.calls, ['/auth/session']);
    app.document.querySelector('[name="username"]').value = 'analyst-a';
    app.document.querySelector('[name="password"]').value = 'test-password';
    app.document.querySelector('form').dispatchEvent(new app.window.Event('submit', { bubbles: true, cancelable: true }));
    await waitFor(() => app.document.querySelector('tbody tr'));
    assert.equal(app.window.localStorage.length, 1, 'Only the theme is persisted');
    app.click('Sign out');
    await waitFor(() => app.document.querySelector('[name="password"]'));
    assert.equal(app.document.querySelector('tbody'), null);
    assert.equal(app.intervals.size, 0);
});

test('session expiry clears event data and returns to sign-in', async t => {
    let expired = false;
    const app = mount(t, url => {
        if (url === '/auth/session') return { ok: true, json: async () => ({ user: expired ? null : { id: 1, username: 'viewer', display_name: 'Viewer', role: 'viewer' }, csrf_token: 'token' }) };
        if (expired) return { ok: false, json: async () => ({ detail: 'Sign in required', code: 'not_authenticated' }) };
        return success(url);
    }, null, '', false);
    await waitFor(() => app.document.querySelector('tbody tr'));
    expired = true;
    app.click('Refresh');
    await waitFor(() => app.document.querySelector('[name="password"]'));
    assert.equal(app.document.querySelector('tbody'), null);
    assert.equal(app.intervals.size, 0);
});

test('viewers can review findings but cannot open new cases or manage accounts', async t => {
    const finding = { id: 10, title: 'Repeated failures', ip_address: event.ip_address, severity: 'high', evidence: [event], window_start: event.timestamp, window_end: event.timestamp, observed_count: 6, threshold: 5, window_seconds: 300, investigation_id: null };
    const app = mount(t, url => ({ ok: true, json: async () => url === '/auth/session' ? { user: { id: 1, username: 'viewer', display_name: 'Viewer', role: 'viewer' }, csrf_token: 'token' } : url === '/findings' ? [finding] : url === '/findings/10' ? finding : [] }), null, '#investigations', false);
    await waitFor(() => app.document.querySelector('.queue-tabs'));
    await waitFor(() => [...app.document.querySelectorAll('button')].some(button => button.textContent.startsWith('Review finding')));
    assert.ok(![...app.document.querySelectorAll('button')].some(button => button.textContent === 'Accounts'));
    assert.match(app.document.body.textContent, /Read-only access/);
    app.click('Review finding');
    await waitFor(() => app.document.querySelector('.evidence-summary'));
    assert.ok([...app.document.querySelectorAll('button')].find(button => button.textContent === 'Open investigation').disabled);
});

test('administrators provision accounts and update access with audited refreshes', async t => {
    const me = { id: 1, username: 'admin', display_name: 'Administrator', role: 'admin', is_active: true };
    const users = [me];
    const history = [];
    const writes = [];
    const app = mount(t, (url, options = {}) => {
        const reply = data => ({ ok: true, json: async () => structuredClone(data) });
        if (url === '/auth/session') return reply({ user: me, csrf_token: 'admin-token' });
        if (url === '/users/access-history') return reply(history);
        if (url === '/users' && options.method === 'POST') {
            assert.equal(options.headers['X-CSRFToken'], 'admin-token');
            const data = JSON.parse(options.body);
            writes.push(data);
            users.push({ id: 2, username: data.username, role: data.role, is_active: true });
            history.push({ id: 1, actor: 'admin', target: data.username, action: 'created', after: users[1], created_at: event.timestamp });
            return reply(users[1]);
        }
        if (url === '/users/2') { users[1].is_active = false; return reply(users[1]); }
        if (url === '/users') return reply(users);
        return success(url);
    }, null, '#accounts', false);
    await waitFor(() => app.document.querySelector('[name="password"]'));
    app.document.querySelector('[name="username"]').value = 'new-analyst';
    app.document.querySelector('[name="password"]').value = 'initial-password';
    app.document.querySelector('form').dispatchEvent(new app.window.Event('submit', { bubbles: true, cancelable: true }));
    await waitFor(() => app.document.querySelector('[aria-label="Role for new-analyst"]'));
    assert.deepEqual(writes, [{ username: 'new-analyst', password: 'initial-password', role: 'analyst' }]);
    assert.equal(app.document.querySelector('[name="password"]').value, '');
    const row = app.document.querySelector('[aria-label="Role for new-analyst"]').closest('tr');
    row.querySelector('button').click();
    await waitFor(() => app.document.querySelector('[aria-label="Role for new-analyst"]').closest('tr').textContent.includes('Inactive'));
    assert.match(app.document.body.textContent, /admin · created · new-analyst/);
});

test('untrusted event fields render as text without injecting markup', async t => {
    const attacker = '<img src=x onerror="window.injected=true">';
    const app = mount(t, url => url.endsWith('/stats') ? success(url) : { ok: true, json: async () => [{ ...event, username: attacker }] });
    await waitFor(() => app.document.querySelector('tbody tr'));
    assert.ok(app.document.querySelector('tbody').textContent.includes(attacker));
    assert.equal(app.document.querySelector('tbody img'), null);
    app.document.querySelector('[aria-label="Inspect event 1"]').click();
    await waitFor(() => app.document.querySelector('dialog[open]'));
    assert.equal(app.document.querySelector('dialog img'), null);
    assert.equal(app.window.injected, undefined);
});
