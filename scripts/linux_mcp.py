"""Shell and file tools for Qatro's Linux workspace. JSON-RPC over standard input."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("QATRO_WORKSPACE", "/home/qatro/workspace")).resolve()
SERVER = {"name": "pc", "version": "2.0.0"}


def schema(properties, required):
    return {"type": "object", "properties": properties, "required": required}


STRING = {"type": "string"}
TOOLS = [
    {"name": "run_command", "description": "Run a Linux shell command in the workspace.", "inputSchema": schema({"command": STRING, "cwd": STRING, "timeout": {"type": "integer"}}, ["command"])},
    {"name": "read_file", "description": "Read a text file with line numbers.", "inputSchema": schema({"path": STRING, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, ["path"])},
    {"name": "write_file", "description": "Write a text file in the workspace.", "inputSchema": schema({"path": STRING, "content": STRING}, ["path", "content"])},
    {"name": "replace_in_file", "description": "Replace an exact text span in a workspace file.", "inputSchema": schema({"path": STRING, "old": STRING, "new": STRING, "count": {"type": "integer"}}, ["path", "old", "new"])},
    {"name": "list_dir", "description": "List workspace files and directories.", "inputSchema": schema({"path": STRING, "pattern": STRING}, ["path"])},
]


def path_in_workspace(value):
    p = Path(value)
    if not p.is_absolute(): p = ROOT / p
    p = p.resolve()
    if not p.is_relative_to(ROOT): raise ValueError("File tools only access the cloud workspace.")
    return p


def tool(name, args):
    if name == "run_command":
        if os.name == "nt": raise ValueError("This command tool requires Linux.")
        cwd = path_in_workspace(args.get("cwd", str(ROOT)))
        timeout = min(max(int(args.get("timeout", 120)), 1), 600)
        done = subprocess.run(["/bin/bash", "-lc", args["command"]], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return f"[exit {done.returncode}]\n{done.stdout[-32000:]}\n{done.stderr[-8000:]}"
    p = path_in_workspace(args["path"])
    if name == "read_file":
        lines = p.read_text(encoding="utf-8").splitlines()
        start = max(1, int(args.get("offset", 1))) - 1
        count = min(max(1, int(args.get("limit", 2000))), 5000)
        return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines[start:start + count], start))
    if name == "write_file":
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return "The file is written."
    if name == "replace_in_file":
        old, new = args["old"], args["new"]
        if not old: raise ValueError("The old text cannot be empty.")
        text = p.read_text(encoding="utf-8")
        count = int(args.get("count", 1))
        if count != -1 and text.count(old) != count: raise ValueError("The number of matching spans differs from the requested count.")
        p.write_text(text.replace(old, new, count), encoding="utf-8")
        return "The text is replaced."
    if name == "list_dir":
        return "\n".join(("dir " if x.is_dir() else "file ") + x.name for x in sorted(p.glob(args.get("pattern", "*"))))
    raise ValueError("Unknown tool.")


def dispatch(request):
    mid, method = request.get("id"), request.get("method")
    if mid is None: return None
    if method == "initialize":
        value = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": SERVER}
    elif method == "ping": value = {}
    elif method == "tools/list": value = {"tools": TOOLS}
    elif method == "tools/call":
        p = request.get("params", {})
        try: value = {"content": [{"type": "text", "text": tool(p["name"], p.get("arguments", {}))}]}
        except Exception as exc: value = {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
    else: return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "Unknown method."}}
    return {"jsonrpc": "2.0", "id": mid, "result": value}


def main():
    for line in sys.stdin:
        try: response = dispatch(json.loads(line))
        except (ValueError, TypeError, KeyError): response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid request."}}
        if response is not None: print(json.dumps(response), flush=True)


if __name__ == "__main__": main()
