set -euo pipefail
sudo -u qatro python3 - <<'PY'
from pathlib import Path
import base64, os, secrets
p = Path('/home/qatro/.config/quatro-dashboard')
p.mkdir(mode=0o700, parents=True, exist_ok=True)
f = p / 'environment'
if not f.exists():
    client_secret = (p / 'github-client-secret').read_text().strip()
    values = {
      'OAUTH2_PROXY_CLIENT_SECRET': client_secret,
      'OAUTH2_PROXY_COOKIE_SECRET': base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
      'QUATRO_ORIGIN_KEY': secrets.token_urlsafe(40),
      'QUATRO_REGISTRATION_KEY': secrets.token_urlsafe(40),
      'QUATRO_PUBLIC_ORIGIN': 'https://quatro-dashboard.lashtabeha-dmytro.workers.dev',
      'QUATRO_REGISTRATION_URL': 'https://quatro-dashboard-register.lashtabeha-dmytro.workers.dev/register',
    }
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as out:
        for k,v in values.items(): out.write(k + '=' + v + '\n')
PY
PYTHON=$(sudo -H -u qatro bash -c "cd /home/qatro; find /home/qatro/.hermes/installs \\( -type f -o -type l \\) -path '*/venv/bin/python3' -print -quit")
sudo -u qatro test -x "$PYTHON"
sudo tee /etc/systemd/system/quatro-dashboard.service >/dev/null <<'EOF'
[Unit]
Description=Quatro private dashboard
After=network.target
[Service]
User=qatro
Group=qatro
Environment=HOME=/home/qatro
Environment=HERMES_HOME=/home/qatro/.hermes
WorkingDirectory=/home/qatro/workspace
ExecStart=/home/qatro/.local/bin/hermes dashboard --no-open --host 127.0.0.1 --port 9119 --skip-build
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/quatro-dashboard-auth.service >/dev/null <<'EOF'
[Unit]
Description=Quatro dashboard GitHub sign-in
After=quatro-dashboard.service
Requires=quatro-dashboard.service
[Service]
User=qatro
Group=qatro
EnvironmentFile=/home/qatro/.config/quatro-dashboard/environment
ExecStart=/home/qatro/.local/bin/oauth2-proxy --http-address=127.0.0.1:4180 --upstream=http://127.0.0.1:9119/ --provider=github --github-user=limidotu --email-domain=* --client-id=Ov23liJWcPRbcguy6KD3 --redirect-url=https://quatro-dashboard.lashtabeha-dmytro.workers.dev/oauth2/callback --reverse-proxy=true --trusted-proxy-ip=127.0.0.1/32 --cookie-secure=true --cookie-samesite=lax --cookie-expire=7h
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/quatro-dashboard-guard.service >/dev/null <<EOF
[Unit]
Description=Quatro dashboard origin guard
After=quatro-dashboard-auth.service
Requires=quatro-dashboard-auth.service
[Service]
User=qatro
Group=qatro
EnvironmentFile=/home/qatro/.config/quatro-dashboard/environment
ExecStart=$PYTHON /home/qatro/dashboard-staging/local_proxy.py
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/quatro-dashboard-tunnel.service >/dev/null <<EOF
[Unit]
Description=Quatro dashboard outbound tunnel
After=network-online.target quatro-dashboard-guard.service
Requires=quatro-dashboard-guard.service
[Service]
User=qatro
Group=qatro
EnvironmentFile=/home/qatro/.config/quatro-dashboard/environment
ExecStart=$PYTHON /home/qatro/dashboard-staging/tunnel_bridge.py
Restart=always
RestartSec=15
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl stop quatro-oauth-preview.service quatro-dashboard-preview.service
sudo systemctl enable --now quatro-dashboard.service quatro-dashboard-auth.service quatro-dashboard-guard.service
systemctl is-active quatro-dashboard.service quatro-dashboard-auth.service quatro-dashboard-guard.service
