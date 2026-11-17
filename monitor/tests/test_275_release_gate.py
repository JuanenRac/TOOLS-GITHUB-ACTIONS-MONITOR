# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The gate of the package: the zip must be the commit. A versioned file edited and not committed, names that differ only in capitals and a folder where git does not answer are all found (the last one
fails unless the person says --allow-no-git, instead of skipping the comparison without a word)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import make_release as mr  # noqa: E402


class TheGateComparesWithTheCommit(unittest.TestCase):
    def repo(self):
        if not shutil.which("git"):
            self.skipTest("git is not installed")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=folder, capture_output=True, check=True)
        return folder

    def test_a_versioned_file_edited_and_not_committed_is_found(self):
        folder = self.repo()
        (folder / "a.txt").write_text("one", encoding="utf-8")
        subprocess.run(["git", "add", "a.txt"], cwd=folder, capture_output=True, check=True)
        (folder / "a.txt").write_text("two", encoding="utf-8")
        self.assertEqual(mr.dirty_files(folder), ["a.txt"])

    def test_a_clean_folder_has_no_edited_files(self):
        self.assertEqual(mr.dirty_files(self.repo()), [])

    def test_names_that_differ_only_in_capitals_are_found(self):
        self.assertEqual(mr.case_collisions(["docs/webhook.md", "docs/WEBHOOK.md", "docs/other.md"]), [["docs/WEBHOOK.md", "docs/webhook.md"]])
        self.assertEqual(mr.case_collisions(["a.md", "b.md"]), [])

    def test_git_that_does_not_answer_is_not_a_clean_folder(self):
        with mock.patch.object(mr.subprocess, "run", side_effect=OSError("no git")):
            self.assertIsNone(mr.dirty_files(HERE))
            self.assertIsNone(mr.tracked_files(HERE))

    def test_a_folder_that_is_not_a_checkout_cannot_be_compared(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertIsNone(mr.tracked_files(Path(plain)))

    def test_the_gate_stops_without_git_unless_it_is_allowed(self):
        text = (HERE / "tools" / "make_release.py").read_text(encoding="utf-8")
        self.assertIn("--allow-no-git", text)
        self.assertIn("cannot be compared with the versioned files", text)
        self.assertIn("NOT compared with the versioned files", text)

    def test_content_edits_in_a_tracked_file_are_part_of_the_gate(self):
        text = (HERE / "tools" / "make_release.py").read_text(encoding="utf-8")
        self.assertIn("dirty_files()", text)
        self.assertIn("case_collisions(entries)", text)


if __name__ == "__main__":
    unittest.main()
