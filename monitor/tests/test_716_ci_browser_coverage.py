# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A browser test skips itself in the CI unless `MONITOR_BROWSER_TESTS` is set, so one that no job of the workflow names is never run there (five of them, the wall screens among them, were not). Every file
with that skip has to be named in a step of the workflow that sets the variable, and the demo has to be checked against the contract."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parent.parent / ".github" / "workflows" / "ci.yml"
SKIP = re.compile(r'os\.environ\.get\("CI"\)\s+and\s+not\s+os\.environ\.get\("MONITOR_BROWSER_TESTS"\)')


def steps(text):
    return re.split(r"\n      - ", text)


class EveryBrowserTestRunsInTheCi(unittest.TestCase):
    def setUp(self):
        if not WORKFLOW.is_file():
            self.skipTest("the workflows live in the repository")
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_each_file_that_skips_in_the_ci_is_named_in_a_step_that_turns_the_browser_tests_on(self):
        files = sorted(p.name for p in HERE.glob("test_*.py") if SKIP.search(p.read_text(encoding="utf-8")))
        self.assertGreaterEqual(len(files), 16)
        on = [step for step in steps(self.text) if 'MONITOR_BROWSER_TESTS: "1"' in step]
        missing = [name for name in files if not any(name in step for step in on)]
        self.assertEqual(missing, [], "a browser test no job of the workflow runs")

    def test_the_wall_screens_have_their_job_and_it_can_turn_the_ci_red(self):
        job = self.text.split("\n  page:", 1)[1].split("\n  container:", 1)[0]
        self.assertIn("test_207_wall_screens_browser.py", job)
        code = "\n".join(line.split("#", 1)[0] for line in job.splitlines())
        self.assertNotIn("continue-on-error", code)

    def test_the_demo_is_checked_against_the_contract_in_both_editions(self):
        job = self.text.split("\n  pictures:", 1)[1].split("\n  browser:", 1)[0]
        self.assertIn("tools/demo_monitor.py", job)
        self.assertIn("check_api_contract.py --url", job)
        self.assertIn("check_api_contract.py --lite", job)


if __name__ == "__main__":
    unittest.main()
