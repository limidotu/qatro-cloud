import { test } from 'node:test';
import assert from 'node:assert/strict';
import dashboard from './dashboard-worker.mjs';
import registration from './registration-worker.mjs';
import oauthProxy from './oauth-dashboard-worker.mjs';

const req = (path, options) => new Request('https://quatro.example.workers.dev' + path, options);
const owner = { access: { getIdentity: async () => ({ email: 'owner@example.test' }) } };
const env = { OWNER_EMAIL: 'owner@example.test', ORIGIN_KEY: 'example-origin-key', QUATRO_ORIGIN: { get: async () => null } };

test('dashboard fails closed without the managed sign-in', async () => {
  assert.equal((await dashboard.fetch(req('/'), env, {})).status, 403);
  assert.equal((await dashboard.fetch(req('/'), env, { access: { getIdentity: async () => ({ email: 'other@example.test' }) } })).status, 403);
});

test('dashboard rejects cross-site changes and an unconfigured origin', async () => {
  assert.equal((await dashboard.fetch(req('/api/x', { method: 'POST', headers: { Origin: 'https://other.example' } }), env, owner)).status, 403);
  assert.equal((await dashboard.fetch(req('/'), env, owner)).status, 503);
});

test('registration rejects unauthenticated and invalid origins', async () => {
  const writes = [];
  const registrar = { REGISTRATION_KEY: 'example-key', QUATRO_ORIGIN: { put: async (...args) => writes.push(args) } };
  const post = (body, key) => req('/register', { method: 'POST', headers: { Authorization: `Bearer ${key}` }, body: JSON.stringify(body) });
  assert.equal((await registration.fetch(post({ origin: 'https://ok.trycloudflare.com' }, 'wrong'), registrar)).status, 403);
  assert.equal((await registration.fetch(post({ origin: 'https://localhost' }, 'example-key'), registrar)).status, 400);
  assert.equal(writes.length, 0);
  assert.equal((await registration.fetch(post({ origin: 'https://ok.trycloudflare.com' }, 'example-key'), registrar)).status, 204);
  assert.deepEqual(writes, [['origin', 'https://ok.trycloudflare.com']]);
});

test('the OAuth relay fails closed without a configured origin', async () => {
  assert.equal((await oauthProxy.fetch(req('/'), env)).status, 503);
  const supplied = { ...env, QUATRO_ORIGIN: { get: async () => 'https://allowed.trycloudflare.com' } };
  assert.equal((await oauthProxy.fetch(req('/api/mutate', { method: 'POST', headers: { Origin: 'https://other.example' } }), supplied)).status, 403);
  assert.equal((await oauthProxy.fetch(req('//evil.example/'), supplied)).status, 400);
});

test('the OAuth relay replaces untrusted proxy identity headers', async () => {
  const original = globalThis.fetch;
  const supplied = { ...env, QUATRO_ORIGIN: { get: async () => 'https://allowed.trycloudflare.com' } };
  let observed;
  globalThis.fetch = async (request, options) => {
    observed = { target: request.url, headers: options.headers };
    return new Response('ok');
  };
  try {
    const response = await oauthProxy.fetch(req('/', { headers: { 'X-Forwarded-Host': 'attacker.example', 'X-Quatro-Origin': 'attacker', Cookie: 'test-cookie' } }), supplied);
    assert.equal(response.status, 200);
    assert.equal(observed.headers.get('X-Forwarded-Host'), 'quatro.example.workers.dev');
    assert.equal(observed.headers.get('X-Quatro-Origin'), 'example-origin-key');
    assert.equal(observed.headers.get('Cookie'), 'test-cookie');
  } finally { globalThis.fetch = original; }
});
