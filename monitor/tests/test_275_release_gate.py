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

    def commit(self, folder, files):
        for name, content in files.items():
            (folder / name).write_bytes(content)
        subprocess.run(["git", "add", "-A"], cwd=folder, capture_output=True, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x"], cwd=folder, capture_output=True, check=True)

    def test_a_member_whose_content_is_not_the_committed_one_is_found(self):
        folder = self.repo()
        self.commit(folder, {"a.txt": b"one\n", "b.bin": b"\x00\x01", "gone.txt": b"x\n"})
        entries = {"github_actions_monitor/a.txt": b"one\r\n", "github_actions_monitor/b.bin": b"\x00\x02", "github_actions_monitor/new.txt": b"made by the build"}
        self.assertEqual(mr.member_hash_problems(entries, folder), ["b.bin"], "line endings are made alike, a different byte is not, and a member that is not versioned is another check")

    def test_members_equal_to_the_commit_pass_and_git_that_does_not_answer_is_none(self):
        folder = self.repo()
        self.commit(folder, {"a.txt": b"one\n"})
        self.assertEqual(mr.member_hash_problems({"github_actions_monitor/a.txt": b"one\n"}, folder), [])
        with tempfile.TemporaryDirectory() as plain:
            self.assertIsNone(mr.member_hash_problems({}, Path(plain)))

    def test_the_real_members_are_the_committed_ones(self):
        if mr.tracked_files() is None or mr.dirty_files():
            self.skipTest("not a clean checkout")
        entries = {f"github_actions_monitor/{p.relative_to(mr.HERE).as_posix()}": mr.line_endings_for_zip(p.name, mr.lf_for_scripts(p.read_bytes())) for p in mr.members()}
        self.assertEqual(mr.member_hash_problems(entries), [])

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
        self.assertIn("member_hash_problems(entries)", text)


if __name__ == "__main__":
    unittest.main()
