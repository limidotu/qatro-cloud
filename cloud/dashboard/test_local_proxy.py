import importlib.util
import socket
import unittest
from pathlib import Path

from aiohttp import ClientSession, web, WSMsgType

spec = importlib.util.spec_from_file_location('local_proxy', Path(__file__).with_name('local_proxy.py'))
proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy)


class ProxyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app = web.Application()

        async def backend(request):
            if request.headers.get('Upgrade', '').lower() == 'websocket':
                ws = web.WebSocketResponse()
                await ws.prepare(request)
                async for message in ws:
                    if message.type == WSMsgType.TEXT:
                        await ws.send_str(message.data)
                return ws
            response = web.json_response({'cookie': request.headers.get('Cookie'),
                                          'host': request.headers.get('X-Forwarded-Host')})
            response.headers.add('Set-Cookie', 'one=two; HttpOnly; Secure')
            return response

        app.router.add_route('*', '/{tail:.*}', backend)
        self.back = web.AppRunner(app)
        await self.back.setup()
        await web.TCPSite(self.back, '127.0.0.1', 4180).start()
        self.front = web.AppRunner(proxy.make_app('a' * 32, 'https://test.workers.dev'))
        await self.front.setup()
        self.site = web.TCPSite(self.front, '127.0.0.1', 0)
        await self.site.start()
        self.port = self.site._server.sockets[0].getsockname()[1]
        self.client = ClientSession()

    async def asyncTearDown(self):
        await self.client.close()
        await self.front.cleanup()
        await self.back.cleanup()

    async def test_origin_gate_and_cookie_forwarding(self):
        url = f'http://127.0.0.1:{self.port}/'
        async with self.client.get(url) as response:
            self.assertEqual(response.status, 403)
        headers = {'X-Quatro-Origin': 'a' * 32, 'Cookie': 'session=hello', 'X-Forwarded-Host': 'attacker.invalid'}
        async with self.client.get(url, headers=headers) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(await response.json(), {'cookie': 'session=hello', 'host': 'test.workers.dev'})
            self.assertIn('one=two', response.headers.get('Set-Cookie'))

    async def test_websocket_with_origin_gate(self):
        url = f'http://127.0.0.1:{self.port}/ws'
        async with self.client.ws_connect(url, headers={'X-Quatro-Origin': 'a' * 32}) as ws:
            await ws.send_str('hello')
            self.assertEqual((await ws.receive()).data, 'hello')

    def test_refuses_unsafe_origin(self):
        with self.assertRaises(ValueError):
            proxy.make_app('a' * 32, 'http://example.com')


if __name__ == '__main__':
    unittest.main()
