# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Going back to the previous version takes the lock of the updater and respects an update in progress (the journal that says `applying`), so it never restores under a running update."""
import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))

import _testenv  # noqa: F401,E402
import monitor_updater as mu  # noqa: E402
from test_66_updater_engine import Base, config_from_defaults, make_install, tree_hash  # noqa: E402


class GoBackAndTheLock(Base):
    def setUp(self):
        super().setUp()
        self.root = make_install(self.tmp / "i", "2.0.1", config_from_defaults("2.0.1"))
        self.up = self.updater(self.root)
        self.assertTrue(self.up.apply("2.0.8", {})["ok"])
        self.lock = self.up.backups / ".lock"

    def busy(self):
        self.lock.write_text(json.dumps({"pid": 1234, "time": time.time()}), encoding="utf-8")
        folder = self.up.backups / "20991231-000000_2.0.8_to_2.0.9"
        folder.mkdir()
        (folder / "journal.json").write_text(json.dumps({"status": "applying", "from": "2.0.8", "to": "2.0.9"}), encoding="utf-8")
        return folder

    def test_with_an_update_in_progress_it_does_not_restore(self):
        self.busy()
        before = tree_hash(self.root)
        report = self.up.go_back(confirm=lambda entry: True)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], mu.BLOCKED)
        self.assertIn("20991231-000000_2.0.8_to_2.0.9", report["error"])
        self.assertEqual(tree_hash(self.root), before, "nothing was restored")
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        self.assertTrue(self.lock.is_file(), "the lock of the other update is not touched")

    def test_a_live_lock_alone_also_blocks(self):
        self.lock.write_text(json.dumps({"pid": 1234, "time": time.time()}), encoding="utf-8")
        report = self.up.go_back(confirm=lambda entry: True)
        self.assertEqual(report["code"], mu.BLOCKED)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")

    def test_the_lock_is_held_during_the_return_and_released_after(self):
        seen = {}
        original = self.up.restore

        def spy(*args, **kwargs):
            seen["locked"] = self.up.lock_state() is not None
            seen["second"] = self.up.go_back(confirm=lambda entry: True)["code"]
            return original(*args, **kwargs)
        self.up.restore = spy
        report = self.up.go_back(confirm=lambda entry: True)
        self.assertTrue(report["ok"], report)
        self.assertTrue(seen["locked"])
        self.assertEqual(seen["second"], mu.BLOCKED, "a second return or update during the first is told the folder is locked")
        self.assertFalse(self.lock.exists())
        self.assertEqual(mu.read_tool_version(self.root), "2.0.1")


if __name__ == "__main__":
    unittest.main()
