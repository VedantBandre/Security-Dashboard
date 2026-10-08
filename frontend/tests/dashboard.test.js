import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';
import { JSDOM, VirtualConsole } from 'jsdom';

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

function mount(t, respond) {
    const errors = [];
    const console = new VirtualConsole();
    console.on('jsdomError', (error) => errors.push(error));
    const dom = new JSDOM(html, {
        url: 'http://localhost:5173', runScripts: 'outside-only', virtualConsole: console,
    });
    const calls = [];
    const intervals = new Map();
    let nextId = 0;
    dom.window.setInterval = (callback, milliseconds) => {
        assert.equal(milliseconds, 5000);
        intervals.set(++nextId, callback);
        return nextId;
    };
    dom.window.clearInterval = (id) => intervals.delete(id);
    dom.window.fetch = async (url) => {
        calls.push(url);
        return respond(url);
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
    return { document, calls, intervals, click };
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

test('failed requests do not show an all-clear and manual refresh recovers', async (t) => {
    let failing = true;
    const app = mount(t, (url) => failing ? { ok: false } : success(url));
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
