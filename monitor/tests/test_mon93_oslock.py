# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The files that several processes write (the log of actions, the state and the feed of the AI channel, the notification ledger, the dispatcher, the lessons, the schedule, the report state and the
storage of the accounts) are guarded by the lock of the operating system (`os_lock`, on `<file>.oslock`), which the system lets go of when its owner dies, and no longer by a marker file that a dead owner
leaves behind (`process_lock`, which stays for the places that need a rescue by age)."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.storage import locks  # noqa: E402

SRC = HERE / "src" / "github_actions_monitor"


class TheSharedFilesUseTheLockOfTheSystem(unittest.TestCase):
    def test_no_module_but_the_lock_module_takes_the_marker_file_lock(self):
        offenders = []
        for path in SRC.rglob("*.py"):
            if path.name == "locks.py":
                continue
            if re.search(r"\bprocess_lock\b", path.read_text(encoding="utf-8")):
                offenders.append(path.relative_to(SRC).as_posix())
        self.assertEqual(offenders, [])

    def test_the_log_of_actions_leaves_the_file_of_the_os_lock_and_no_marker_file(self):
        from github_actions_monitor.security import audit_log
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "audit_actions.jsonl"
            from unittest import mock
            with mock.patch.object(audit_log, "path", return_value=target):
                line = audit_log.record({"audit_log": {"enabled": True}}, "settings_change", "someone", "admin", "", "x", "ok")
            self.assertIsNotNone(line)
            names = sorted(p.name for p in Path(tmp).iterdir())
            self.assertIn("audit_actions.jsonl.oslock", names)
            self.assertNotIn("audit_actions.jsonl.lock", names)

    def test_a_dead_owner_cannot_leave_the_file_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "state.json"
            Path(str(target) + ".oslock").write_text("0", encoding="ascii")      # what a process that died leaves: the file, not the lock
            with locks.os_lock(target, 1.0):
                pass


if __name__ == "__main__":
    unittest.main()
