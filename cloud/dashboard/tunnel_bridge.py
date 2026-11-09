"""Keep a temporary tunnel connected and register its origin privately."""
import asyncio
import os
import re
import signal
from urllib.parse import urlsplit

from aiohttp import ClientSession, ClientTimeout

ORIGIN = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')


def validate_registration_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.workers.dev')
            or parsed.username or parsed.password or parsed.port or parsed.path != '/register'
            or parsed.query or parsed.fragment):
        raise ValueError('The registration address must be a Workers HTTPS endpoint.')
    return value


async def main():
    endpoint = validate_registration_url(os.environ['QUATRO_REGISTRATION_URL'])
    token = os.environ['QUATRO_REGISTRATION_KEY']
    if len(token) < 32:
        raise ValueError('A private registration key is required.')
    proc = await asyncio.create_subprocess_exec(
        '/home/qatro/.local/bin/cloudflared', 'tunnel', '--no-autoupdate',
        '--url', 'http://127.0.0.1:9120',
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: proc.terminate() if proc.returncode is None else None)
    registered = None
    async with ClientSession(timeout=ClientTimeout(total=15)) as session:
        while line := await proc.stdout.readline():
            match = ORIGIN.search(line.decode('utf-8', errors='replace'))
            if not match or match.group() == registered:
                continue
            origin = match.group()
            for attempt in range(10):
                try:
                    async with session.post(endpoint, json={'origin': origin},
                                            headers={'Authorization': 'Bearer ' + token}) as response:
                        if response.status == 204:
                            registered = origin
                            print('Private dashboard tunnel registered.', flush=True)
                            break
                except Exception:
                    pass
                await asyncio.sleep(min(30, 2 ** attempt))
            if registered != origin:
                print('Could not register the private tunnel.', flush=True)
                proc.terminate()
                break
    status = await proc.wait()
    return status or (0 if registered else 1)


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
