# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The page on a phone (no target under 44 px, no sideways scroll, in a window of 375 px) and the contrast of the wall screens, both measured in a real browser. The browser parts need Edge, Chrome or
Chromium; the CI job `page` runs them with MONITOR_REQUIRE_BROWSER (no browser is a failure there). Nothing here reaches GitHub."""
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
    import check_mobile  # noqa: E402
    import check_overflow  # noqa: E402
    import check_screens  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_mobile = check_overflow = check_screens = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
SCREENS = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))
LOCAL_ONLY = unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")


class TheScreensAreMeasuredForContrast(unittest.TestCase):
    def test_the_measure_knows_the_contrast_and_the_glance_marks_do_not_rely_on_a_colour_of_text(self):
        if check_screens is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        self.assertIn('"contrast"', check_screens.LIB)
        self.assertIn("4.5", check_screens.LIB)
        self.assertIn(r"color\(srgb", check_screens.LIB)      # the colours that color-mix() gives are read too
        self.assertIn("could be measured", check_screens.LIB)      # a gate that sees almost nothing fails instead of passing
        self.assertNotIn("span.up{border-color:var(--bad);color:var(--bad)}", SCREENS)
        self.assertIn("--mut:color-mix(in srgb,var(--text) 90%,var(--panel2))", SCREENS)

    @LOCAL_ONLY
    def test_no_text_of_a_wall_screen_is_under_the_contrast_in_any_theme(self):
        if check_screens is None or check_overflow is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        if not check_overflow.edge():
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        everything = os.environ.get("MONITOR_SCREENS_MATRIX")
        themes = ("Armor", "Aqua", "Midnight", "Ember", "Forest", "Violet", "Solar", "Ice", "Crimson", "Mono", "High contrast", "Metallic", "Professional", "Videogame", "Terminal", "Blueprint", "light", "dark", "contrast") \
            if everything else ("Ice", "Solar", "light", "contrast")
        for theme in themes:
            results = check_screens.run(("en",), ("1080p",), ("rich", "worst"), check_screens.KINDS, quiet=True, theme=theme)
            found = [f for f in check_screens.flat(results) if f["kind"] == "contrast"]
            self.assertEqual(found, [], (theme, [(f["screen"], f["at"], f["detail"]) for f in found[:5]]))


class ThePageOnAPhone(unittest.TestCase):
    def test_the_judge_names_the_small_target_the_wide_page_and_the_missing_keyboard_variable(self):
        if check_mobile is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        good = {"ok": True, "compact": True, "menu": {"direction": "row", "scrolls": True}, "vvh": "812px", "wide": [], "small": [], "errors": [], "tabs": {"now": True}}
        self.assertEqual(check_mobile.problems(good), [])
        for change, expected in (({"small": [{"tab": "now", "el": "button#x", "w": 40, "h": 44, "text": "About"}]}, "under 44"), ({"wide": [{"tab": "al", "by": 12}]}, "scrolls sideways"),
                                 ({"vvh": ""}, "--vvh"), ({"compact": False}, "compact view"), ({"menu": {"direction": "column", "scrolls": False}}, "menu")):
            found = check_mobile.problems({**good, **change})
            self.assertTrue(any(expected in line for line in found), (change, found))

    def test_the_icon_buttons_of_the_side_foot_keep_a_finger_wide_in_the_compact_view(self):
        self.assertEqual(PAGE.count(".side-foot button{width:auto;min-width:44px}"), 2)

    @LOCAL_ONLY
    def test_no_target_under_44_px_no_sideways_scroll_in_a_window_of_375_px(self):
        if check_mobile is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        report = check_mobile.audit("en")
        if report is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        self.assertEqual(check_mobile.problems(report), [])


if __name__ == "__main__":
    unittest.main()
