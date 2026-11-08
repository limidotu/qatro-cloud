#!/usr/bin/env bash
set -euo pipefail
umask 077
if [ "$(id -un)" != "qatro" ]; then
  echo "Run this installer as the qatro service user." >&2
  exit 1
fi
export HERMES_HOME="$HOME/.hermes"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin" "$HOME/workspace" "$HOME/.config/opencode"
installer="$(mktemp)"
trap 'rm -f "$installer"' EXIT
curl --fail --silent --show-error --location \
  'https://raw.githubusercontent.com/NousResearch/hermes-agent/4d04303818b61bf3aa09278af48356315515965b/scripts/install.sh' \
  --output "$installer"
bash "$installer" --branch main --commit 4d04303818b61bf3aa09278af48356315515965b \
  --dir "$HOME/hermes-agent" --hermes-home "$HERMES_HOME" \
  --non-interactive --skip-browser --skip-computer-use
hermes pm env node npm | python3 -c '
import json, os, subprocess, sys
env = dict(os.environ)
env.update(json.load(sys.stdin))
subprocess.run(["npm", "install", "--global", "--prefix", os.path.expanduser("~/.local"), "@opencode/cli@2.2.5"], env=env, check=True)
'
echo "The runtime is installed. Keep the gateway stopped until migration is complete."
