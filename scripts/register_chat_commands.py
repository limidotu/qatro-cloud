"""Register Quatro's existing Discord session commands without changing other commands."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://discord.com/api/v10/"
COMMANDS = (
    {"name": "new", "description": "Start a fresh chat with Quatro.", "type": 1},
    {"name": "title", "description": "Give the current chat a name.", "type": 1,
     "options": [{"name": "name", "description": "Name for this chat", "type": 3, "required": False}]},
    {"name": "sessions", "description": "List your named chats.", "type": 1},
    {"name": "resume", "description": "List chats or switch to a named chat.", "type": 1,
     "options": [{"name": "name", "description": "Chat name or number from the list", "type": 3, "required": False}]},
)


def request(token, path, data=None):
    headers = {"Authorization": "Bot " + token, "User-Agent": "DiscordBot (https://github.com/limidotu/qatro-cloud, 1.0)"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(API + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Discord rejected the request (HTTP {exc.code}).") from None


def reconcile(token, apply=False):
    app = request(token, "applications/@me")
    path = f"applications/{app['id']}/commands"
    existing = {c["name"]: c for c in request(token, path) if c.get("type", 1) == 1}
    names = {c["name"] for c in COMMANDS}
    conflict = names & existing.keys()
    if apply and conflict:
        raise RuntimeError("Some chat commands already exist. Review them before changing anything: " + ", ".join(sorted(conflict)))
    if apply and len(existing) + len(COMMANDS) > 100:
        raise RuntimeError("Discord's command limit leaves no room for these controls.")
    if apply:
        for command in COMMANDS:
            request(token, path, command)
            print("Added /" + command["name"], flush=True)
    return names, existing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        parser.error("DISCORD_BOT_TOKEN must be set privately in the environment.")
    try:
        names, existing = reconcile(token, args.apply)
        if not args.apply:
            print("Commands to add:", ", ".join("/" + n for n in sorted(names - existing.keys())))
            print("Existing commands with these names:", ", ".join(sorted(names & existing.keys())) or "none")
            print("Other existing commands:", len(existing.keys() - names))
    except (RuntimeError, OSError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
