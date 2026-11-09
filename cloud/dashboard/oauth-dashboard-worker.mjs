// Authentication is handled by oauth2-proxy behind the origin guard.
// No dashboard data is served by the Worker when the guarded origin is absent.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const websocket = request.headers.get('Upgrade')?.toLowerCase() === 'websocket';
    if ((!['GET', 'HEAD'].includes(request.method) || websocket) && request.headers.get('Origin') !== url.origin) {
      return new Response('Invalid request origin.', { status: 403 });
    }
    const origin = await env.QUATRO_ORIGIN.get('origin', { cacheTtl: 30 });
    if (!origin || !/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(origin) || !env.ORIGIN_KEY) {
      return new Response('Quatro is offline or starting.', { status: 503 });
    }
    const target = new URL(url.pathname + url.search, origin);
    if (target.origin !== origin) return new Response('Invalid path.', { status: 400 });
    const headers = new Headers(request.headers);
    for (const key of Array.from(headers.keys())) {
      if (key.toLowerCase().startsWith('x-forwarded-') || key.toLowerCase().startsWith('x-auth-request-') ||
          ['forwarded', 'x-quatro-origin'].includes(key.toLowerCase())) headers.delete(key);
    }
    headers.set('X-Forwarded-Host', url.host);
    headers.set('X-Forwarded-Proto', 'https');
    headers.set('X-Quatro-Origin', env.ORIGIN_KEY);
    try {
      return await fetch(new Request(target, request), { headers, redirect: 'manual' });
    } catch {
      return new Response('Quatro is offline or starting.', { status: 503 });
    }
  },
};
