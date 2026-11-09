"""Apply Linux settings to an explicitly selected cloud home, never the Windows home."""
from __future__ import annotations
import argparse
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(home: Path, workspace: Path, opencode: Path):
    if os.name == "nt" or not str(home).startswith("/home/qatro/"):
        raise ValueError("Run this tool on Quatro's Linux server, with a home below /home/qatro.")
    if not home.is_dir() or not workspace.is_dir() or not opencode.is_file():
        raise ValueError("The migrated home, workspace, and OpenCode executable must exist.")
    ready = home / ".qatro-ready"
    if ready.exists():
        raise ValueError("Stop the cloud gateway and remove its ready marker before changing the configuration.")
    oc_config = Path.home() / ".config/opencode/opencode.json"
    if oc_config.exists():
        raise ValueError("An OpenCode configuration already exists. Review it before applying the cloud settings.")
    config = json.loads((ROOT / "cloud/config.json").read_text(encoding="utf-8"))
    config["terminal"]["cwd"] = str(workspace)
    existing = home / "config.yaml"
    if existing.exists():
        backup = home / "config.before-cloud.yaml"
        if backup.exists():
            raise ValueError("A configuration backup already exists. Preserve it before retrying.")
        shutil.copy2(existing, backup)
    # JSON is valid YAML. No YAML package is needed on the server.
    existing.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    existing.chmod(0o600)
    oc_config.parent.mkdir(parents=True, exist_ok=True)
    oc_config.write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "mcp": {"pc": {"type": "local", "command": ["python3", str(ROOT / "scripts/linux_mcp.py")], "enabled": True}},
    }, indent=2) + "\n", encoding="utf-8")
    print("Linux settings are written. The gateway remains stopped.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, default=Path("/home/qatro/.hermes"))
    p.add_argument("--workspace", type=Path, default=Path("/home/qatro/workspace"))
    p.add_argument("--opencode", type=Path, default=Path("/home/qatro/.local/bin/opencode"))
    a = p.parse_args()
    prepare(a.home.resolve(), a.workspace.resolve(), a.opencode.resolve())
