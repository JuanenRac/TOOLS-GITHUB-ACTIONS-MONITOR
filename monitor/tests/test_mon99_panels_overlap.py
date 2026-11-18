# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The folding panels of the Sentinel tabs never paint one over another. The panel that is alone unfolded used to be squeezed to a few pixels by the folded ones when they filled the box, and its body was drawn over
the panels below it. It now keeps a minimum height (the box scrolls instead). The browser test unfolds every panel of every Sentinel tab one by one, together and by hand, and compares the rectangles."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE / "src"))

try:
    import check_overflow
    import check_unfolded
except ImportError:      # the zip of the package has no tools folder
    check_unfolded = check_overflow = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


class Css(unittest.TestCase):
    def test_the_one_unfolded_panel_has_a_floor_and_never_shrinks_to_nothing(self):
        rule = next(line for line in PAGE.splitlines() if line.startswith(":is(#t-sci,#t-scol,#t-ssec,#t-sdel,#t-ssup) .body>details[open]:not(details[open]~details)") and "{flex:1 1 auto" in line and "::details-content" not in line and ">.dbody" not in line)
        self.assertRegex(rule, r"min-height:\d+(\.\d+)?rem")
        self.assertNotIn("min-height:0", rule)

    def test_the_folded_panels_keep_their_natural_height(self):
        self.assertIn("#t-sci .body>details,#t-scol .body>details,#t-ssec .body>details,#t-sdel .body>details,#t-ssup .body>details{flex:0 0 auto}", PAGE)

    def test_the_probe_checks_overlap_and_the_end_of_every_body(self):
        text = (HERE.parent / "tools" / "check_unfolded.py").read_text(encoding="utf-8") if check_unfolded else ""
        if not text:
            self.skipTest("no tools folder")
        for needle in ("panels_overlap", "body_outside_panel", "getBoundingClientRect", "all unfolded", "alternate"):
            self.assertIn(needle, text, needle)


@unittest.skipUnless(check_unfolded is not None and check_overflow is not None and check_overflow.edge(), "no tools folder or no browser")
class InTheBrowser(unittest.TestCase):
    def test_no_panel_overlaps_another_in_any_sentinel_tab_wide_and_narrow(self):
        results = check_unfolded.run(["en", "de"], ("desktop", "mobile"), quiet=True)
        self.assertIsNotNone(results)
        bad = [(key, f) for key, found in results.items() for f in found if f["kind"] in ("panels_overlap", "body_outside_panel", "body_without_height")]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
