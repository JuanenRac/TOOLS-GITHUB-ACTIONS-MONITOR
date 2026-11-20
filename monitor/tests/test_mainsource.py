# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The CHANGELOG and the version of a clone are read from the default branch of the remote, not from the branch the clone is on (`delivery/mainsource.py`). Real git, in temporary folders."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_actions_monitor.delivery import mainsource, rules  # noqa: E402
from github_actions_monitor.sentinels import readiness  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

GIT = shutil.which("git")
MAIN_LOG = "# Changelog\n\n## [Unreleased]\n\n- one\n- two\n  - nested\n\n## [1.0.0]\n\n- old\n"
BRANCH_LOG = "# Changelog\n\n## [Unreleased]\n\n" + "".join(f"- entry {i}\n" for i in range(20)) + "\n## [0.9.0]\n"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.autocrlf=false", *args], cwd=cwd, check=True, capture_output=True)


@unittest.skipUnless(GIT, "git is needed")
class MainSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mon9x_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        root = Path(self.tmp)
        self.origin, self.clone = root / "origin.git", root / "clone"
        git(root, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(root, "clone", "-q", str(self.origin), str(self.clone))
        git(self.clone, "checkout", "-q", "-b", "main")
        (self.clone / "CHANGELOG.md").write_text(MAIN_LOG, encoding="utf-8", newline="")
        (self.clone / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
        git(self.clone, "add", ".")
        git(self.clone, "commit", "-q", "-m", "main")
        git(self.clone, "push", "-q", "origin", "main")

    def test_a_clone_on_an_old_agent_branch_counts_main(self):
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / "CHANGELOG.md").write_text(BRANCH_LOG, encoding="utf-8", newline="")
        (self.clone / "pyproject.toml").write_text('[project]\nversion = "0.9.0"\n', encoding="utf-8")
        text, note = mainsource.read_changelog(self.clone)
        self.assertEqual((mainsource.unreleased_count(text), note), (3, ""))     # 20 in the branch, 3 in main (the nested one counts)
        self.assertEqual(readiness.local_version(self.clone), "1.0.0")           # the version of main, not the one of the branch

    def test_the_unreleased_count_of_the_working_tree_is_not_what_the_monitor_reports(self):
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / "CHANGELOG.md").write_text(BRANCH_LOG, encoding="utf-8", newline="")
        self.assertEqual(mainsource.unreleased_count((self.clone / "CHANGELOG.md").read_text(encoding="utf-8")), 20)
        self.assertEqual(mainsource.unreleased_count(mainsource.read_changelog(self.clone)[0]), 3)

    def test_without_origin_the_working_tree_is_read_with_a_note_naming_the_branch(self):
        git(self.clone, "remote", "remove", "origin")
        git(self.clone, "update-ref", "-d", "refs/remotes/origin/main")
        text, note = mainsource.read_changelog(self.clone)
        self.assertEqual(mainsource.unreleased_count(text), 3)
        self.assertIn("no remote branch", note)
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / "CHANGELOG.md").write_text(BRANCH_LOG, encoding="utf-8", newline="")
        text, note = mainsource.read_changelog(self.clone)
        self.assertEqual(mainsource.unreleased_count(text), 20)
        self.assertEqual(note, "clone on branch agent-old, not on main; counted from the working tree")

    def test_crlf_in_main_counts_the_same(self):
        (self.clone / "CHANGELOG.md").write_text(MAIN_LOG.replace("\n", "\r\n"), encoding="utf-8", newline="")
        git(self.clone, "commit", "-q", "-am", "crlf")
        git(self.clone, "push", "-q", "origin", "main")
        text, note = mainsource.read_changelog(self.clone)
        self.assertIn("\r\n", text)
        self.assertEqual((mainsource.unreleased_count(text), note), (3, ""))

    def test_main_without_a_changelog_is_not_replaced_by_the_one_of_a_branch(self):
        git(self.clone, "rm", "-q", "CHANGELOG.md")
        git(self.clone, "commit", "-q", "-m", "drop")
        git(self.clone, "push", "-q", "origin", "main")
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / "CHANGELOG.md").write_text(BRANCH_LOG, encoding="utf-8", newline="")
        self.assertEqual(mainsource.read_changelog(self.clone), (None, ""))

    def test_the_default_branch_may_be_master(self):
        git(self.clone, "update-ref", "refs/remotes/origin/master", "HEAD")
        git(self.clone, "update-ref", "-d", "refs/remotes/origin/main")
        self.assertEqual(mainsource.default_ref(self.clone)[0], "origin/master")

    def test_not_a_clone_reads_the_folder_and_a_missing_file_is_none(self):
        plain = Path(self.tmp) / "plain"
        plain.mkdir()
        self.assertEqual(mainsource.read_changelog(plain), (None, ""))
        (plain / "CHANGELOG.md").write_text(MAIN_LOG, encoding="utf-8")
        self.assertIn("no remote branch", mainsource.read_changelog(plain)[1])

    def test_the_roadmap_definitions_are_taken_from_main_not_from_the_branch_of_the_clone(self):
        from github_actions_monitor.sentinels import roadmap_a9
        (self.clone / "tools").mkdir()
        (self.clone / "tools" / "roadmap_defs.py").write_text("VALUE = 'main'\n", encoding="utf-8")
        git(self.clone, "add", ".")
        git(self.clone, "commit", "-q", "-m", "tools")
        git(self.clone, "push", "-q", "origin", "main")
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / "tools" / "roadmap_defs.py").write_text("VALUE = 'branch'\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as scratch:
            folder = roadmap_a9._extract_main_tools(self.clone, scratch)
            self.assertEqual((Path(folder) / "roadmap_defs.py").read_text(encoding="utf-8"), "VALUE = 'main'\n")
        git(self.clone, "remote", "remove", "origin")
        git(self.clone, "update-ref", "-d", "refs/remotes/origin/main")
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(roadmap_a9._extract_main_tools(self.clone, scratch), "")      # no remote branch: the caller reads the working tree

    def test_the_manifest_and_the_top_version_of_the_surface_checks_are_those_of_main(self):
        from github_actions_monitor.app import surface
        (self.clone / "tool.project.json").write_text('{"version": "2.0.0"}', encoding="utf-8")
        (self.clone / "CHANGELOG.md").write_text("## [Unreleased]\n- a\n\n## [2.0.0] - x\n", encoding="utf-8", newline="")
        git(self.clone, "add", ".")
        git(self.clone, "commit", "-q", "-m", "v2")
        git(self.clone, "push", "-q", "origin", "main")
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / "tool.project.json").write_text('{"version": "1.0.0"}', encoding="utf-8")
        (self.clone / "CHANGELOG.md").write_text("## [Unreleased]\n- a\n\n## [1.0.0] - x\n", encoding="utf-8", newline="")
        scan = surface.scan_clone(self.clone)
        self.assertEqual((scan["manifest"]["version"], scan["changelog_top"]), ("2.0.0", "2.0.0"))

    def test_a_clone_that_was_not_fetched_says_so(self):
        head = subprocess.run(["git", "rev-parse", "origin/main"], cwd=self.clone, capture_output=True, text=True).stdout.strip()
        self.assertEqual(mainsource.behind_note(self.clone, head), "")
        self.assertEqual(mainsource.behind_note(self.clone, ""), "")      # GitHub did not say: nothing to compare
        self.assertIn("not fetched", mainsource.behind_note(self.clone, "0" * 40))

    def test_one_function_counts_for_the_whole_monitor(self):
        for text in (MAIN_LOG, BRANCH_LOG, "## [Unreleased]\r\n- a\r\n* b\r\n## [1.0.0]\r\n- c\r\n", ""):
            self.assertEqual(rules.unreleased_count(text), mainsource.unreleased_count(text))

    def test_the_candidate_row_carries_the_note_and_the_panel_line_shows_it(self):
        rows = sl.release_candidates_rule({"A": 3, "B": 5}, {"A": 10.0, "B": 10.0}, 2, 1, (), {"B": "clone on branch x, not on main; counted from the working tree"})
        self.assertNotIn("note", [r for r in rows if r["repo"] == "A"][0])
        self.assertIn("not on main", [r for r in rows if r["repo"] == "B"][0]["note"])


if __name__ == "__main__":
    unittest.main()
