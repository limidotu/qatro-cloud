"""Private localhost proxy for a Cloudflare tunnel. No direct public listener."""
import asyncio
import hmac
import os
from urllib.parse import urlsplit
from aiohttp import ClientSession, ClientTimeout, WSMsgType, web

HOP = {'host', 'connection', 'upgrade', 'keep-alive', 'proxy-authenticate',
       'proxy-authorization', 'te', 'trailer', 'transfer-encoding',
       'x-quatro-origin', 'cf-access-jwt-assertion'}


def make_app(secret, public_origin, upstream='http://127.0.0.1:4180'):
    if not secret or len(secret) < 32:
        raise ValueError('A private origin key is required.')
    if upstream != 'http://127.0.0.1:4180':
        raise ValueError('Only the local sign-in proxy is supported.')
    public = urlsplit(public_origin)
    if (public.scheme != 'https' or not public.hostname or not public.hostname.endswith('.workers.dev')
            or public.username or public.password or public.port or public.path not in ('', '/')
            or public.query or public.fragment):
        raise ValueError('A valid dashboard origin is required.')

    async def on_start(app):
        app['client'] = ClientSession(timeout=ClientTimeout(total=None, sock_connect=10), auto_decompress=False)

    async def on_stop(app):
        await app['client'].close()

    async def handler(request):
        given = request.headers.get('X-Quatro-Origin', '')
        if not hmac.compare_digest(given.encode(), secret.encode()):
            return web.Response(status=403, text='Access denied.')
        target = upstream + request.rel_url.raw_path_qs
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP
                   and not k.lower().startswith('x-forwarded-') and k.lower() != 'forwarded'}
        headers['Host'] = '127.0.0.1:4180'
        headers['X-Forwarded-Host'] = public.hostname
        headers['X-Forwarded-Proto'] = 'https'
        for key in list(headers):
            if key.lower() == 'origin':
                headers[key] = 'http://127.0.0.1:9119'
        client = request.app['client']
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            for key in list(headers):
                if key.lower().startswith('sec-websocket-'):
                    del headers[key]
            async with client.ws_connect(target, headers=headers, max_msg_size=16 * 1024 * 1024) as back:
                front = web.WebSocketResponse(max_msg_size=16 * 1024 * 1024)
                await front.prepare(request)

                async def pump(source, dest):
                    async for msg in source:
                        if msg.type == WSMsgType.TEXT:
                            await dest.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await dest.send_bytes(msg.data)
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                            break

                tasks = [asyncio.create_task(pump(front, back)), asyncio.create_task(pump(back, front))]
                _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await front.close()
                return front
        async with client.request(request.method, target, headers=headers, data=request.content,
                                  allow_redirects=False) as response:
            clean = {k: v for k, v in response.headers.items() if k.lower() not in HOP and k.lower() != 'set-cookie'}
            out = web.StreamResponse(status=response.status, headers=clean)
            for cookie in response.headers.getall('Set-Cookie', []):
                out.headers.add('Set-Cookie', cookie)
            await out.prepare(request)
            async for chunk in response.content.iter_chunked(65536):
                await out.write(chunk)
            await out.write_eof()
            return out

    app = web.Application(client_max_size=25 * 1024 * 1024)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    app.router.add_route('*', '/{tail:.*}', handler)
    return app


if __name__ == '__main__':
    web.run_app(make_app(os.environ.get('QUATRO_ORIGIN_KEY', ''), os.environ.get('QUATRO_PUBLIC_ORIGIN', '')),
                host='127.0.0.1', port=9120, access_log=None)
