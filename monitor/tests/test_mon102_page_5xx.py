# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The walk through the page tells a monitor that fails: an answer with a 5xx status to a call of the page is a problem of the walk (with its address, without the query), as a script error already was;
the walk can be made at the sizes of a desktop and of a phone; and the job of the CI that does it in the eight languages exists and is wired to the check. The browser part runs where there is a
browser (the CI sets MONITOR_BROWSER_TESTS)."""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))

import _testenv  # noqa: F401,E402

try:
    import check_page  # noqa: E402
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_page = None
    check_overflow = None

NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))
WITH_BROWSER = not (os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"))


@unittest.skipIf(check_page is None, "the tools folder does not travel in the zip of a release")
class TheWalkSeesAFailingMonitor(unittest.TestCase):
    def test_the_script_that_runs_before_the_page_records_the_5xx_answers_only(self):
        head = check_page.HEAD
        self.assertIn("window.fetch", head)
        self.assertIn("reply.status>=500", head)
        self.assertIn("split(\"?\")[0]", head)      # the address without its query: it may hold a name or a filter

    def test_the_walk_can_be_made_at_the_two_sizes(self):
        self.assertEqual(sorted(check_overflow.SIZES), ["desktop", "mobile"])
        import inspect
        self.assertIn("sizes", inspect.signature(check_page.run).parameters)
        self.assertIn("fail", inspect.signature(check_page.run).parameters)
        self.assertIn("fail", inspect.signature(check_overflow.relay).parameters)

    @unittest.skipUnless(WITH_BROWSER, "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_a_503_from_the_monitor_is_a_problem_of_the_walk(self):
        found = check_page.run(("en",), fail=("/api/data",))
        if found is None:
            if NEEDS_BROWSER:
                self.fail("there is no browser and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        self.assertTrue(any("http 503" in item and "/api/data" in item for item in found["en"]), found["en"])
        self.assertFalse(any("?" in item for item in found["en"] if item.startswith("http ")))


class TheJobOfTheCi(unittest.TestCase):
    def test_the_evidence_workflow_walks_the_page_in_the_eight_languages_and_two_sizes(self):
        workflow = HERE.parent / ".github" / "workflows" / "evidence.yml"
        if not workflow.is_file():
            self.skipTest("the workflows live in the repository")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("tools/check_page.py", text)
        self.assertIn("--lang en es de fr it ja zh pt", text)
        self.assertIn("--size desktop mobile", text)


if __name__ == "__main__":
    unittest.main()
