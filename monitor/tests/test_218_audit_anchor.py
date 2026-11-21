# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The chain of the log of actions has an anchor: the lines cut off its tail are found, and a log written before the anchor existed still verifies."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.security import audit_log  # noqa: E402

NOW = 1_800_000_000.0


class Anchor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "audit_actions.jsonl"
        audit_log.FILE = self.file
        audit_log._last.update(path=None, hash="")
        self.addCleanup(lambda: (setattr(audit_log, "FILE", None), audit_log._last.update(path=None, hash="")))
        for i in range(5):
            audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", details={"settings": [f"a.b{i}"]}, now=NOW + i)

    def test_a_whole_chain_verifies(self):
        self.assertEqual(audit_log.verify(), {"ok": True, "entries": 5, "broken_at": None, "segments": 1, "complete": True})

    def test_the_last_lines_cut_off_are_found(self):
        lines = self.file.read_text(encoding="utf-8").splitlines()
        self.file.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")      # the chain of the two first lines is still whole
        result = audit_log.verify()
        self.assertFalse(result["ok"])
        self.assertEqual((result["segment"], result["anchor"]), ("anchor", "anchor_mismatch"))

    def test_one_line_cut_off_and_a_deleted_file_are_found_too(self):
        lines = self.file.read_text(encoding="utf-8").splitlines()
        self.file.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        self.assertFalse(audit_log.verify()["ok"])
        self.file.unlink()
        self.assertFalse(audit_log.verify()["ok"])

    def test_a_log_without_an_anchor_still_verifies_and_gets_one_with_its_next_line(self):
        audit_log.anchor_path(self.file).unlink()
        self.assertTrue(audit_log.verify()["ok"])
        audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", now=NOW + 9)
        self.assertTrue(audit_log.anchor_path(self.file).exists())
        self.assertTrue(audit_log.verify()["ok"])

    def test_a_cut_followed_by_a_new_line_is_the_limit_of_the_anchor(self):
        lines = self.file.read_text(encoding="utf-8").splitlines()
        self.file.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")
        audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", now=NOW + 9)      # the anchor follows what is written now
        self.assertTrue(audit_log.verify()["ok"])      # a cut that is followed by a write is accepted: the anchor protects the end, not the lines that came before a later write


if __name__ == "__main__":
    unittest.main()
