"""Export Qatro's memory and skills to a private local archive. Exclude credentials."""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import re
import sqlite3
import tarfile
import tempfile
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[1]
TREES = ["memories", "sessions", "skills"]
FILES = ["SOUL.md", "shared-state.db", "kanban.db", "state.db"]
EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", ".hub", ".locks", ".venv"}


def safe_file(path):
    name = path.name.lower()
    if path.is_symlink() or any(p.startswith(".") or p in EXCLUDED_DIRS for p in path.parts): return False
    if name.endswith((".lock", ".pem", ".key", ".pfx", ".p12", ".db-wal", ".db-shm", ".pyc")): return False
    return not re.search(r"(^|[._-])(auth|credentials?|secrets?|tokens?|cookies?)([._-]|$)", name)


def selected_files(home):
    for name in FILES:
        p = home / name
        if p.is_file() and not p.is_symlink(): yield p, Path("home") / name
    for tree in TREES:
        root = home / tree
        if not root.is_dir(): continue
        for p in sorted(root.rglob("*")):
            relative = p.relative_to(home)
            if p.is_file() and safe_file(relative) and not p.is_symlink():
                if any(q.is_symlink() for q in p.parents if q != home and home in q.parents): continue
                yield p, Path("home") / relative
    provider = home / "plugins/model-providers/opencode-acp"
    for name in ["__init__.py", "router.py", "routing.json", "plugin.yaml"]:
        p = provider / name
        if p.is_file() and not p.is_symlink(): yield p, Path("home/plugins/model-providers/opencode-acp") / name


def export(home, destination):
    home, destination = home.resolve(), destination.resolve()
    if not home.is_dir(): raise ValueError("The selected Hermes home does not exist.")
    if destination.is_relative_to(PUBLIC_ROOT): raise ValueError("Keep private state outside the public project directory.")
    if destination.exists(): raise ValueError("The destination already exists. Choose a new archive path.")
    pairs = list(selected_files(home))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qatro-export-", dir=destination.parent) as temp:
        temp = Path(temp)
        try:
            with tarfile.open(destination, "x:gz") as archive:
                for source, relative in pairs:
                    if source.suffix == ".db":
                        target = temp / source.name
                        uri = source.as_uri() + "?mode=ro"
                        with closing(sqlite3.connect(uri, uri=True)) as reader, closing(sqlite3.connect(target)) as writer:
                            with writer:
                                reader.backup(writer)
                        archive.add(target, arcname=relative.as_posix(), recursive=False)
                    else: archive.add(source, arcname=relative.as_posix(), recursive=False)
            destination.chmod(0o600)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return len(pairs)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--destination", type=Path)
    a = p.parse_args()
    if a.destination:
        print(json.dumps({"exported_files": export(a.home, a.destination), "credentials_included": False}))
    else:
        pairs = list(selected_files(a.home))
        print(json.dumps({"selected_files": len(pairs), "exported": False, "credentials_included": False}))
