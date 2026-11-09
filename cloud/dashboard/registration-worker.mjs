function same(a, b) {
  const encoder = new TextEncoder();
  const x = encoder.encode(a || ''), y = encoder.encode(b || '');
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST' || new URL(request.url).pathname !== '/register') {
      return new Response('Not found.', { status: 404 });
    }
    if (!env.REGISTRATION_KEY || !same(request.headers.get('Authorization'), `Bearer ${env.REGISTRATION_KEY}`)) {
      return new Response('Access denied.', { status: 403 });
    }
    if (Number(request.headers.get('Content-Length') || 0) > 512) return new Response('Invalid request.', { status: 400 });
    const text = await request.text();
    if (text.length > 512) return new Response('Invalid request.', { status: 400 });
    let data;
    try { data = JSON.parse(text); } catch { return new Response('Invalid request.', { status: 400 }); }
    if (!/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(data.origin || '')) {
      return new Response('Invalid origin.', { status: 400 });
    }
    await env.QUATRO_ORIGIN.put('origin', data.origin);
    return new Response(null, { status: 204, headers: { 'Cache-Control': 'no-store' } });
  },
};
