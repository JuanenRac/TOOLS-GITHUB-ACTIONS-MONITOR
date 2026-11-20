# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The workflow linter of the sentinel reads the workflow files of a clone from the default branch of the remote, not from the working tree: a clone on an old branch is judged by what main says. Real git."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_actions_monitor.cli import lint_workflows  # noqa: E402
from github_actions_monitor.delivery import mainsource  # noqa: E402

GIT = shutil.which("git")
MAIN = "name: ci\non: push\npermissions: {}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
CLEAN = "name: ci\non: push\npermissions: {}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@" + "a" * 40 + "\n"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.autocrlf=false", *args], cwd=cwd, check=True, capture_output=True)


@unittest.skipUnless(GIT, "git is needed")
class FromMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="a10_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        root = Path(self.tmp)
        self.origin, self.work, self.clone = root / "origin.git", root / "work", root / "work" / "repo-a"
        self.work.mkdir()
        git(root, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(self.work, "clone", "-q", str(self.origin), str(self.clone))
        git(self.clone, "checkout", "-q", "-b", "main")
        (self.clone / ".github" / "workflows").mkdir(parents=True)
        (self.clone / ".github" / "workflows" / "ci.yml").write_text(MAIN, encoding="utf-8", newline="")
        git(self.clone, "add", ".")
        git(self.clone, "commit", "-q", "-m", "main")
        git(self.clone, "push", "-q", "origin", "main")

    def rules(self):
        return lint_workflows.settings(None)["rules"]

    def test_a_clone_on_an_old_branch_is_judged_by_main_not_by_its_working_tree(self):
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / ".github" / "workflows" / "ci.yml").write_text(CLEAN, encoding="utf-8", newline="")      # the branch fixed it, main did not
        texts, note = mainsource.workflow_texts(self.clone)
        self.assertEqual((sorted(texts), note), (["ci.yml"], ""))
        self.assertIn("checkout@v4", texts["ci.yml"])
        found = lint_workflows.scan_clones(self.work, ["repo-a"], self.rules())
        self.assertEqual([(f["file"], f["rule"]) for f in found["repo-a"]], [(".github/workflows/ci.yml", "unpinned_uses")])

    def test_a_workflow_that_main_has_not_got_is_not_judged_and_one_that_main_has_is_even_if_deleted_in_the_tree(self):
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        (self.clone / ".github" / "workflows" / "new.yml").write_text(MAIN, encoding="utf-8", newline="")      # only in the working tree
        (self.clone / ".github" / "workflows" / "ci.yml").unlink()
        texts, _ = mainsource.workflow_texts(self.clone)
        self.assertEqual(sorted(texts), ["ci.yml"])

    def test_without_a_remote_the_working_tree_is_read_with_a_note(self):
        git(self.clone, "remote", "remove", "origin")
        git(self.clone, "update-ref", "-d", "refs/remotes/origin/main")
        git(self.clone, "checkout", "-q", "-b", "agent-old")
        texts, note = mainsource.workflow_texts(self.clone)
        self.assertEqual(sorted(texts), ["ci.yml"])
        self.assertIn("agent-old", note)
        self.assertIn("working tree", note)
        self.assertTrue(lint_workflows.scan_clones(self.work, ["repo-a"], self.rules()))      # still linted, from the working tree

    def test_a_folder_that_is_not_a_clone_and_has_no_workflows_is_skipped(self):
        (self.work / "plain").mkdir()
        self.assertEqual(lint_workflows.scan_clones(self.work, ["plain", "missing"], self.rules()), {})
        self.assertEqual(mainsource.workflow_texts(self.work / "plain"), ({}, ""))


if __name__ == "__main__":
    unittest.main()
