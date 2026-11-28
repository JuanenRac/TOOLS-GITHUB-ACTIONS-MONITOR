# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Restore, then one tick of one account: a backup is restored into an empty installation and the monitor of the account, with its files redirected as when the supervisor starts it, makes one
refresh cycle in a process of its own with a double of `gh`. Nothing reaches GitHub."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _testenv
from github_actions_monitor.ops import bundle, restore
from github_actions_monitor.storage import installation
from github_actions_monitor.storage.file_storage import FileStorage

HELPER = Path(__file__).resolve().parent / "_restore_tick_double.py"


class RestoreThenTick(unittest.TestCase):
    def test_the_restored_account_reads_its_repositories_and_finds_the_red_workflow(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            base = Path(tmp)
            old = base / "old" / "accounts"
            files = FileStorage(old, "accounts")
            files.save_config("alpha", {"github_owner": "double-owner", "repos": ["demo-a"], "runs_per_repo": 10})
            files.append_events("alpha", [{"at": "2026-01-01T00:00:00Z", "kind": "red_new"}])
            source = installation.open_installation("file", old)
            package = bundle.create(source, base / "copy.zip", config={}, folder=base / "old")["path"]
            source.close()

            env = _testenv.isolated_env(self)
            target = installation.open_installation("file", Path(env["MONITOR_DATA_DIR"]) / "accounts")
            report = restore.restore(package, config={}, inst=target, alive=lambda: False, folder=base / "new", account="alpha")
            target.close()
            self.assertEqual((report["accounts"], report["events"]), (1, 1))

            done = subprocess.run([sys.executable, str(HELPER), "tick", "alpha", str(base / "calls.txt")], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            self.assertEqual(done.returncode, 0, done.stdout[-2000:] + done.stderr[-2000:])
            result = json.loads(done.stdout.strip().splitlines()[-1])
            calls = (base / "calls.txt").read_text(encoding="utf-8")
        self.assertEqual(result["owner"], "double-owner")
        self.assertEqual(result["repos"], ["demo-a"])
        self.assertEqual(result["runs"], 1)
        self.assertEqual(result["failing"], 1)
        self.assertEqual(result["errors"], {})
        self.assertTrue(result["complete"])
        self.assertIn("repos/double-owner/demo-a/actions/runs", calls)


if __name__ == "__main__":
    unittest.main()
