from pathlib import Path
from contextlib import closing
from types import SimpleNamespace as NS
import sqlite3
import tarfile
import tempfile
import unittest
from scripts.export_state import export
from scripts.provision import check_allowance, cloud_init
import scripts.linux_mcp as mcp


class MigrationTests(unittest.TestCase):
    def test_private_export_excludes_credential_files_and_keeps_committed_database_state(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp); home = temp / "home"; home.mkdir()
            (home / "memories").mkdir(); (home / "memories/MEMORY.md").write_text("test memory")
            (home / ".env").write_text("fake-credential"); (home / "auth.json").write_text("fake-credential")
            (home / "skills/example").mkdir(parents=True)
            (home / "skills/example/SKILL.md").write_text("test skill")
            (home / "skills/example/.env").write_text("fake-credential")
            (home / "skills/example/tokens.json").write_text("fake-credential")
            with closing(sqlite3.connect(home / "state.db")) as db:
                db.execute("create table history(value text)"); db.execute("insert into history values ('latest committed turn')")
                db.commit()
                out = temp / "private/qatro.tar.gz"; export(home, out)
                with tarfile.open(out) as archive:
                    names = archive.getnames()
                    self.assertIn("home/memories/MEMORY.md", names)
                    self.assertIn("home/skills/example/SKILL.md", names)
                    self.assertFalse(any(".env" in n or "auth.json" in n or "tokens.json" in n for n in names))
                    backup = temp / "backup.db"
                    backup.write_bytes(archive.extractfile("home/state.db").read())
                with closing(sqlite3.connect(backup)) as copied:
                    self.assertEqual(copied.execute("select value from history").fetchone()[0], "latest committed turn")

    def test_refuses_resources_beyond_account_allocation(self):
        self.assertEqual(check_allowance([], 150)["boot_disk_gb"], 50)
        with self.assertRaises(ValueError): check_allowance([], 151)
        existing = NS(shape="VM.Standard.A1.Flex", shape_config=NS(ocpus=1, memory_in_gbs=6), lifecycle_state="STOPPED")
        with self.assertRaises(ValueError): check_allowance([existing], 0)

    def test_bootstrap_does_not_start_gateway_before_private_migration(self):
        import json
        config = json.loads(cloud_init().split("\n", 1)[1])
        commands = str(config["runcmd"])
        self.assertNotIn("enable", commands); self.assertNotIn("start", commands)
        service = next(x["content"] for x in config["write_files"] if x["path"].endswith("qatro.service"))
        self.assertIn("ConditionPathExists=/home/qatro/.hermes/.qatro-ready", service)

    def test_linux_file_tools_reject_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            original = mcp.ROOT
            try:
                mcp.ROOT = Path(temp).resolve()
                self.assertEqual(mcp.tool("write_file", {"path": "note.txt", "content": "hello"}), "The file is written.")
                self.assertEqual(mcp.tool("read_file", {"path": "note.txt"}), "1: hello")
                with self.assertRaises(ValueError): mcp.tool("read_file", {"path": "../outside.txt"})
            finally: mcp.ROOT = original


if __name__ == "__main__": unittest.main()
