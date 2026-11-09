// Cloudflare Access must authenticate every request before it reaches Quatro.
export default {
  async fetch(request, env, ctx) {
    if (!ctx.access) return new Response('Sign-in required.', { status: 403 });
    const identity = await ctx.access.getIdentity();
    if (!identity?.email || identity.email.toLowerCase() !== env.OWNER_EMAIL?.toLowerCase()) {
      return new Response('Access denied.', { status: 403 });
    }
    const url = new URL(request.url);
    const upgrade = request.headers.get('Upgrade')?.toLowerCase() === 'websocket';
    if ((!['GET', 'HEAD'].includes(request.method) || upgrade) && request.headers.get('Origin') !== url.origin) {
      return new Response('Invalid request origin.', { status: 403 });
    }
    const origin = await env.QUATRO_ORIGIN.get('origin', { cacheTtl: 30 });
    if (!origin || !/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(origin) || !env.ORIGIN_KEY) {
      return new Response('Quatro is offline or the dashboard is starting.', { status: 503 });
    }
    const target = new URL(url.pathname + url.search, origin);
    const headers = new Headers(request.headers);
    headers.delete('Cookie');
    headers.delete('Cf-Access-Jwt-Assertion');
    headers.delete('X-Quatro-Origin');
    headers.set('X-Quatro-Origin', env.ORIGIN_KEY);
    try {
      const proxied = new Request(target, request);
      const response = await fetch(proxied, { headers, redirect: 'manual' });
      if (response.status === 101) return response;
      const out = new Headers(response.headers);
      out.delete('Set-Cookie');
      out.set('Cache-Control', 'no-store');
      return new Response(response.body, { status: response.status, headers: out });
    } catch {
      return new Response('Quatro is offline or the dashboard is starting.', { status: 503 });
    }
  },
};
