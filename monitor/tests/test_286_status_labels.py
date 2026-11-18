# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The status label of a detail panel (the lamp pill in the heading of "Detail by layer") stays on one line. The heading is a flex row whose text may break anywhere, so the label was squeezed to
one letter per line; it is now measured in a headless browser in the eight languages, wide and narrow (tools/check_pills.py). The source of the page is also read as text (this part runs everywhere).

Skipped when there is no Edge, Chrome or Chromium on this computer, or no tools folder."""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))
try:
    import check_overflow  # noqa: E402
    import check_pills  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_pills = check_overflow = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
BROWSER_ONLY = unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")


class TheSource(unittest.TestCase):
    def test_the_label_in_a_heading_does_not_shrink_and_does_not_break_inside_a_word(self):
        rule = re.search(r"summary>\.sem\{[^}]*\}", PAGE)
        self.assertIsNotNone(rule, "the label in a heading has no rule of its own")
        for part in ("flex:0 0 auto", "white-space:nowrap", "overflow-wrap:normal"):
            self.assertIn(part, rule.group(0))

    def test_every_panel_heading_puts_its_label_first_in_the_heading(self):
        self.assertRegex(PAGE, r"<summary><span class=\"sem \$\{level\}\"")


@unittest.skipUnless(check_pills is not None and check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
class TheGeometry(unittest.TestCase):
    @BROWSER_ONLY
    def test_no_status_label_is_taller_than_wide_in_the_eight_languages_wide_and_narrow(self):
        results = check_pills.run(quiet=True)
        self.assertIsNotNone(results)
        self.assertEqual(len(results), len(check_pills.LANGS) * 2)
        lines = [f"[{lang}/{size}] {item['kind']} {item['at']}: {item['detail']}" for (lang, size), items in sorted(results.items()) for item in items]
        self.assertEqual(lines, [], "a status label is squeezed:\n" + "\n".join(lines[:40]))

    @BROWSER_ONLY
    def test_the_probe_catches_a_label_split_one_letter_per_line(self):
        """The measuring script itself: a silent probe could never fail."""
        page = ("<!doctype html><meta charset=utf-8><style>summary{display:flex;width:90px;overflow-wrap:anywhere}.sem{display:inline-flex;font-size:12px}</style><body>"
                "<details open data-k=a2><summary><span class='sem bad'><i></i>attention to take</span> title</summary></details>" + check_pills.PROBE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.html"
            path.write_text("<script>function showTab(){}function renderSent(){}var OPEN=new Set()</script>" + page, encoding="utf-8")
            doc = check_overflow.measure_once(check_overflow.edge(), path.as_uri(), (800, 600), report="pills-report")
        kinds = {f["kind"] for f in doc["found"]}
        self.assertTrue(kinds & {"taller_than_wide", "several_lines"}, kinds)


if __name__ == "__main__":
    unittest.main()
