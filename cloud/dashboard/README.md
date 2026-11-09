# Quatro dashboard

The dashboard uses the Hermes web interface on the Oracle server. GitHub sign-in
passes through OAuth2 Proxy and only permits the configured GitHub user. The
dashboard, sign-in proxy, and origin guard listen on localhost. Cloudflared
opens an outbound quick tunnel. Two Cloudflare Workers relay dashboard requests
and register the current tunnel address. A Workers KV namespace stores that
address. The server and Workers store the shared keys outside this repository.

`setup_server.sh` records the current systemd configuration. It expects Hermes,
OAuth2 Proxy, Cloudflared, the guard scripts, and the private environment file
to already exist on the server. It is not a complete installation script.

Cloudflare describes quick tunnels as testing tools with no uptime guarantee.
A server restart gives the tunnel a new address, and caches can delay recovery.
The dashboard needs the server to be running. GitHub Pages remains available to
start it when the server is stopped.

The dashboard's web chat and the Discord conversation are separate routes.
Selecting a conversation in the web chat does not change Discord's active chat.
Use Discord's `/new`, `/title`, and `/resume` commands to manage that route.

The model uses the free Workers AI allowance. If that daily allowance is used,
new AI replies stop until the next reset, even when the dashboard stays online.

Run `node --test cloud/dashboard/test-workers.mjs` to check the Worker guards.
The Python proxy tests require `aiohttp` and run with
`python -m unittest discover -s cloud/dashboard -p test_local_proxy.py`.
