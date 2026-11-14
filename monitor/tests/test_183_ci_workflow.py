# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The CI of the repository is cheap and does not pile up: Ubuntu and Windows on every pull request, macOS only where it pays, a pinned Apple Silicon image, the pip cache everywhere, runs superseded by a
new push cancelled, and the image workflow written so that GitHub accepts it. The workflows are not part of the zip of the product: without them the tests skip."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

CI = ROOT / ".github" / "workflows" / "ci.yml"
IMAGE = ROOT / ".github" / "workflows" / "release-image.yml"


def text(path):
    if not path.is_file():
        raise unittest.SkipTest("the workflows are not part of the package")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def job(source, name):
    """The text of one job of the workflow (from `  name:` to the next job)."""
    match = re.search(r"(?m)^  %s:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)" % re.escape(name), source, re.S)
    if not match:
        raise AssertionError("no job " + name)
    return match.group(1)


class TheCiDoesNotPileUp(unittest.TestCase):
    def test_a_new_push_to_a_pull_request_cancels_the_run_it_supersedes_and_main_is_never_cancelled(self):
        source = text(CI)
        self.assertRegex(source, r"(?m)^concurrency:\n  group: ci-\$\{\{ github\.workflow \}\}-\$\{\{ github\.event\.pull_request\.number \|\| github\.ref \}\}\n")
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", source)
        self.assertNotRegex(source, r"cancel-in-progress: true")

    def test_every_pull_request_runs_ubuntu_and_windows_and_macos_is_a_job_of_its_own(self):
        source = text(CI)
        tests = job(source, "tests")
        self.assertIn("os: [ubuntu-latest, windows-latest]", tests)
        self.assertNotIn("macos", tests)
        mac = job(source, "tests-macos")
        self.assertIn("runs-on: macos-15", mac)
        self.assertIn("contains(github.event.pull_request.labels.*.name, 'full-ci')", mac)
        self.assertIn("github.event_name != 'pull_request'", mac)

    def test_macos_runs_on_main_on_tags_every_night_and_by_hand(self):
        head = text(CI).split("permissions:")[0]
        for needle in ("push:", "branches: [main]", 'tags: ["v*"]', "schedule:", "cron:", "workflow_dispatch:", "labeled"):
            self.assertIn(needle, head)

    def test_no_image_that_moves_and_homebrew_never_updates(self):
        source = text(CI)
        self.assertNotIn("macos-latest", source)
        self.assertRegex(source, r'(?m)^env:\n(?:  .*\n)*?  HOMEBREW_NO_AUTO_UPDATE: "1"')

    def test_every_python_job_uses_the_pip_cache_of_the_same_file(self):
        source = text(CI)
        setups = source.count("uses: actions/setup-python@")
        self.assertGreaterEqual(setups, 5)
        self.assertEqual(source.count("cache: pip\n"), setups)
        self.assertEqual(source.count("cache-dependency-path: .github/ci-requirements.txt"), setups)
        requirements = (ROOT / ".github" / "ci-requirements.txt").read_text(encoding="utf-8")
        self.assertTrue({"rich", "textual"} <= {line.strip() for line in requirements.splitlines() if line.strip() and not line.startswith("#")})

    def test_every_job_has_a_time_limit(self):
        source = text(CI)
        for name in re.findall(r"(?m)^  ([A-Za-z0-9_-]+):\n    name:", source):
            self.assertIn("timeout-minutes:", job(source, name), name)


class TheImageWorkflowIsAcceptedByGitHub(unittest.TestCase):
    def test_it_uses_only_actions_of_github_pinned_by_commit_and_has_its_triggers(self):
        source = text(IMAGE)
        for line in source.splitlines():
            match = re.match(r"\s*-?\s*uses:\s*([^\s#]+)", line)
            if match:
                self.assertRegex(match.group(1), r"^actions/[a-z-]+@[0-9a-f]{40}$", line.strip())
        self.assertRegex(source, r"(?m)^on:\n  release:\n    types: \[published\]\n  workflow_dispatch:\n    inputs:\n      push:\n")
        self.assertIn("permissions: {}", source)

    def test_it_has_no_tab_and_every_job_has_a_time_limit_and_its_own_permissions(self):
        source = text(IMAGE)
        self.assertNotIn("\t", source)
        body = job(source, "image")
        self.assertIn("timeout-minutes:", body)
        self.assertIn("permissions:", body)
        self.assertIn("runs-on: ubuntu-24.04", body)

    def test_the_push_is_a_separate_step_that_only_a_release_or_the_flag_takes(self):
        source = text(IMAGE)
        self.assertIn("PUBLISH: ${{ github.event_name == 'release' || inputs.push }}", source)
        self.assertIn("default: false", source)


if __name__ == "__main__":
    unittest.main()
