# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The boxes of the optional parts in a real browser (tools/check_parts.py): on a phone and on a computer every box opens, nothing leaves it, no control is under 44 px on the phone and the browser
reports no error; every main tab can be seen (also on a phone held sideways), the figures of the header fold on a phone and the groups of Settings are a list on the left. The CI measures the eight languages and the wall sizes in a job of its own; here two languages stand for all of them."""
import json
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
    import check_parts  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_parts = None

NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))
LOCAL_ONLY = unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")


class TheBoxesOfTheOptionalParts(unittest.TestCase):
    def setUp(self):
        if check_parts is None:
            self.skipTest("the tools folder does not travel in the zip of a release")

    def test_the_judge_names_the_missing_box_the_measure_and_the_error(self):
        self.assertEqual(check_parts.problems({"step": "chat", "found": [], "errors": []}), [])
        self.assertIn("did not appear", check_parts.problems({"step": "chat", "missing": True})[0])
        lines = check_parts.problems({"step": "chat", "found": [{"kind": "under-44px", "at": "button", "detail": "30x20", "text": "Send"}], "errors": ["console.error: no"]})
        self.assertTrue("under-44px" in lines[0] and "console.error" in lines[1], lines)
        self.assertEqual(check_parts.problems({"step": "chat", "found": [], "errors": list(check_parts.EXPECTED)}), [], "the assistant that is off answers 404 on purpose")

    def test_phones_held_sideways_are_measured_in_the_eight_languages(self):
        self.assertEqual([check_parts.SIZES[s] for s in ("land780", "land844", "land915")], [(780, 360), (844, 390), (915, 412)])
        self.assertEqual(len(check_parts.LANGS), 8)
        for step in ("main_tabs", "header_fold", "settings_list"):
            self.assertIn(step, check_parts.STEPS)

    def test_the_text_of_the_folded_figures_is_in_the_eight_languages(self):
        for lang in check_parts.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("{running}", catalogue["ui.tiles_show"], lang)
            self.assertIn("{repos}", catalogue["ui.tiles_show"], lang)
            self.assertTrue(catalogue["ui.tiles_hide"].strip(), lang)

    @LOCAL_ONLY
    def test_every_box_fits_on_a_phone_and_on_a_computer_without_errors(self):
        sizes = ("phone", "land780", "land844", "land915", "desktop")
        results = check_parts.run(("en", "de"), sizes)
        if results is None:
            if NEEDS_BROWSER:
                self.fail("there is no browser or no websockets package here and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no browser, or no websockets package for the browser protocol")
        self.assertGreaterEqual(len(results), 2 * len(sizes) * len(check_parts.STEPS))
        lines = [f"[{lang}/{size}] {line}" for (lang, size, _step), found in results.items() for line in found]
        self.assertEqual(lines, [], "\n".join(lines[:40]))


if __name__ == "__main__":
    unittest.main()
