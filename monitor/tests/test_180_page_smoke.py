# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The page of the monitor must not break without a test turning red. Two layers:

  * the source of the page is read as text: a function defined twice, in any of its forms (declaration with an indent, `async`, assignment), is a failure (runs everywhere);
  * the page is opened in a real browser (tools/check_page.py): every tab and every sub-tab of Settings must draw a minimum of fields and raise no error, no unhandled promise and no
    console.error. The CI runs this file in a job of its own that fails for real (MONITOR_REQUIRE_BROWSER=1: no browser is a failure there, not a skip).

The three ways in which the page was broken on purpose (a second definition with one space in front, an assignment to the name of a function, a call to a function that does not exist) must
turn at least one of the two layers red."""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402
import pagecheck  # noqa: E402

try:
    import check_page  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_page = None

PAGE = HERE / "assets" / "static" / "actions_monitor.html"
BROKEN = "async function quotaTabBox(host){const j=await (await fetch('/api/quota')).json();host.textContent=String(j)}"
#: name -> (text of the page that is replaced, what takes its place): the three breakages
BREAKAGES = {
    "a second definition with a space in front": ("</script>", " " + BROKEN + "\n</script>"),
    "an assignment to the name of a function": ("</script>", "window.quotaTabBox=" + BROKEN.replace("function quotaTabBox", "function") + ";\n</script>"),
    "a call to a function that does not exist": ("function cfgBuild(j){", "function cfgBuild(j){funcionQueNoExiste();"),
}
NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))


def broken(name):
    old, new = BREAKAGES[name]
    page = PAGE.read_text(encoding="utf-8")
    assert page.count(old) == 1, (name, page.count(old))
    return page.replace(old, new)


class TheSourceOfThePage(unittest.TestCase):
    def test_the_page_defines_nothing_twice(self):
        self.assertEqual(pagecheck.duplicates(PAGE.read_text(encoding="utf-8")), [])

    def test_the_two_breakages_of_the_source_are_seen_without_a_browser(self):
        self.assertTrue(pagecheck.duplicates(broken("a second definition with a space in front")))
        self.assertTrue(pagecheck.duplicates(broken("an assignment to the name of a function")))
        self.assertEqual(pagecheck.duplicates(broken("a call to a function that does not exist")), [], "this one only fails when the page runs: the browser layer sees it")

    def test_the_forms_of_a_repeated_definition_are_all_seen(self):
        for text, expected in (("function a(){}\nfunction a(){}", ["a (declared 2 times)"]), ("function a(){}\n  async function a(){}", ["a (declared 2 times)"]),
                               ("function a(){}\n\tfunction a(){}", ["a (declared 2 times)"]), ("function a(){}\nwindow.a=function(){}", ["a (assigned again)"]),
                               ("function a(){}\na = async () => 1", ["a (assigned again)"]), ("function a(){}\n;a=function(){}", ["a (assigned again)"]),
                               ("function a(){}\nfunction b(){}", []), ("function renderSent(){}\nrenderSent=function(){}", []), ("function a(){}\nb=function(){}", [])):
            self.assertEqual(pagecheck.duplicates(text), expected, text)

    def test_the_ci_has_a_job_for_the_page_that_can_turn_it_red(self):
        workflow = HERE.parent / ".github" / "workflows" / "ci.yml"
        if not workflow.is_file():
            self.skipTest("the workflows live in the repository")
        text = workflow.read_text(encoding="utf-8")
        job = text.split("\n  page:", 1)
        self.assertEqual(len(job), 2, "a job named `page`")
        block = job[1].split("\n  container:", 1)[0]
        code = "\n".join(line.split("#", 1)[0] for line in block.splitlines())      # a comment may say the words
        self.assertNotIn("continue-on-error", code)
        self.assertIn("test_180_page_smoke.py", block)
        self.assertIn('MONITOR_REQUIRE_BROWSER: "1"', block)


class ThePageInABrowser(unittest.TestCase):
    def results(self, **kwargs):
        if check_page is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        found = check_page.run(("en",), **kwargs)
        if found is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        return found["en"]

    @unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_the_page_opens_draws_every_tab_and_raises_nothing(self):
        self.assertEqual(self.results(), [])

    @unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_a_page_broken_on_purpose_turns_the_check_red(self):
        for name in BREAKAGES:
            old, new = BREAKAGES[name]
            problems = self.results(change=lambda body, old=old, new=new: body.decode("utf-8").replace(old, new, 1).encode("utf-8"))
            if name == "a call to a function that does not exist":
                self.assertTrue(problems, "an error that only happens when the page runs must be seen by the browser")
            else:
                self.assertTrue(problems or pagecheck.duplicates(broken(name)), name)      # the source check or the browser

    def test_the_judge_of_the_report_needs_a_minimum_and_no_error(self):
        if check_page is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        good = {"ok": True, "tabs": {"now": {"on": True, "text": 500}}, "cfg": {"basic": {"fields": 12, "shown": True}, "interface": {"fields": 5, "shown": True}}, "total_fields": 300,
                "windows": {"about": {"open": True, "text": 100}}, "errors": []}
        self.assertEqual(check_page.problems(good), [])
        for change, expected in (({"errors": ["error: x is not defined"]}, "x is not defined"), ({"ok": False, "error": "boom"}, "boom"), ({"total_fields": 12}, "in all"),
                                 ({"tabs": {"now": {"on": False, "text": 0}}}, "did not open"), ({"tabs": {"now": {"on": True, "text": 3}}}, "almost nothing"),
                                 ({"cfg": {"basic": {"fields": 2, "shown": True}}}, "drew 2 fields"), ({"cfg": {"basic": {"fields": 12, "shown": False}}}, "did not open"),
                                 ({"cfg": {}}, "no sub-tab"), ({"windows": {"help": {"open": False, "text": 0}}}, "window help")):
            found = check_page.problems({**good, **change})
            self.assertTrue(any(expected in line for line in found), (change, found))


if __name__ == "__main__":
    unittest.main()
