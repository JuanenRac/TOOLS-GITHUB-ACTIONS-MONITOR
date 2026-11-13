# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The life of the page: the lamps are animated, every lamp has a shape (the state never depends on the colour alone), a lamp that changes plays one transition, and with the preference of the
user for less motion nothing moves. Two layers:

  * the source of the page is read as text (runs everywhere): every keyframe of the lamps is declared where the user has not asked for less motion, the rule that stops everything is there,
    every level of a lamp has a glyph, the new text is in the eight languages and the page needs no library from the outside;
  * the page is opened in a real browser (tools/check_motion.py): the computed style of every lamp, the transition of a lamp that is changed on purpose, and the same page with the
    preference of less motion. The CI runs this file in the job of the page (MONITOR_REQUIRE_BROWSER=1: no browser is a failure there, not a skip)."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402

try:
    import check_motion  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_motion = None

PAGE = HERE / "assets" / "static" / "actions_monitor.html"
LOCALES = HERE / "assets" / "locales"
NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))
LAMP_KEYFRAMES = ("lamp-breath", "lamp-flip", "tile-flip", "num-tick", "ico-bob", "fx-in")
LEVELS = ("ok", "warn", "bad", "info", "unknown")


def page():
    return PAGE.read_text(encoding="utf-8").replace("\r\n", "\n")


def motion_block(text):
    """The part of the style that is only for users who did not ask for less motion: from its media query to the matching brace."""
    start = text.index("@media (prefers-reduced-motion:no-preference){\n@keyframes lamp-breath")
    depth, i = 0, text.index("{", start)
    while True:
        depth += text[i] == "{"
        depth -= text[i] == "}"
        if depth == 0:
            return text[start:i + 1]
        i += 1


class TheSourceOfTheLife(unittest.TestCase):
    def test_every_keyframe_of_the_life_is_declared_for_users_who_accept_motion(self):
        text, block = page(), motion_block(page())
        for name in LAMP_KEYFRAMES:
            self.assertEqual(text.count(f"@keyframes {name}{{"), 1, name)
            self.assertIn(f"@keyframes {name}{{", block, f"{name} must live inside the media query of no preference")

    def test_every_animation_of_the_lamps_is_inside_that_block(self):
        text, block = page(), motion_block(page())
        outside = text.replace(block, "")
        for name in LAMP_KEYFRAMES:
            self.assertNotRegex(outside, rf"animation:[^;}}]*\b{name}\b", f"{name} is used outside the block of no preference")

    def test_the_rule_that_stops_every_movement_is_there(self):
        self.assertIn("@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}", page())

    def test_the_javascript_asks_before_it_moves_anything(self):
        text = page()
        for fn in ("lampTrack", "fxFilter"):
            body = re.search(r"function %s\(.*?\n" % fn, text).group(0)
            self.assertIn("REDUCED.matches", body, fn)

    def test_every_level_of_a_lamp_has_a_shape_and_not_only_a_colour(self):
        text = page()
        for level in LEVELS:
            self.assertRegex(text, rf"\.sem\.{level} i::after[^{{]*\{{content:\"[^\"]+\"", level)
        glyphs = re.findall(r"\.sem\.\w+ i::after[^{]*\{content:\"([^\"]+)\"", text)
        self.assertEqual(len(glyphs), len(set(glyphs)), "two levels with the same shape")
        for level in ("ok", "warn", "bad"):
            self.assertIn(f".sb-lamp.{level}::after", text, "the lamp of the status bar")

    def test_a_lamp_says_its_state_in_words_too(self):
        text = page()
        self.assertIn('data-tip="${esc(semTip(k,l))}" aria-description="${esc(semTip(k,l))}"', text)
        self.assertIn('id="sb-lamp" aria-hidden="true"', text, "the text next to the lamp of the status bar says the state")

    def test_the_text_of_the_change_is_in_the_eight_languages_and_goes_through_the_catalogue(self):
        self.assertIn('T("ui.lamp_was"', page())
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("{level}", data.get("ui.lamp_was", ""), lang)

    def test_the_life_needs_no_library_from_the_outside(self):
        block = motion_block(page())
        self.assertNotRegex(block, r"https?://|@import|url\(")
        self.assertEqual(re.findall(r"<script[^>]+src=", page()), [])

    def test_the_lite_edition_keeps_its_figures_and_draws_no_sentinel_lamps(self):
        text = page()
        self.assertIn(".lite #n-sent,.lite #t-sent", text)      # the lamps of the sentinels do not exist there: nothing of the new code depends on them
        self.assertIn('lampTrack("sb",lamp,', text)            # the status bar and the tiles are in both editions


class TheLifeInABrowser(unittest.TestCase):
    def results(self, reduced):
        if check_motion is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        found = check_motion.run(reduced)
        if found is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        return found[0]

    @unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_the_lamps_move_have_a_shape_change_with_a_transition_and_raise_nothing(self):
        self.assertEqual(self.results(False), [])

    @unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_with_the_preference_of_less_motion_nothing_moves(self):
        self.assertEqual(self.results(True), [])

    def test_the_judge_of_the_report_sees_each_failure(self):
        if check_motion is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        lamp = {"level": "ok", "animation": "lamp-breath", "glyph": '"x"', "tip": "in order"}
        good = {"ok": True, "reduced": False, "lamps": [dict(lamp) for _ in range(6)], "bar": {"animation": "lamp-breath", "glyph": '"x"', "aria": "true"},
                "flip": {"class": True, "animation": "lamp-flip"}, "errors": []}
        self.assertEqual(check_motion.problems(good), [])
        still = {"ok": True, "reduced": True, "lamps": [{**lamp, "animation": "none"} for _ in range(6)], "bar": {"animation": "none", "glyph": '"x"', "aria": "true"},
                 "flip": {"class": False, "animation": "none"}, "errors": []}
        self.assertEqual(check_motion.problems(still, reduced=True), [])
        cases = (({"lamps": [{**lamp, "glyph": ""}] * 6}, "no shape"), ({"lamps": [{**lamp, "animation": "none"}] * 6}, "not animated"), ({"lamps": [{**lamp, "tip": ""}] * 6}, "no text"),
                 ({"lamps": [dict(lamp)] * 2}, "at least"), ({"bar": {"animation": "none", "glyph": '"x"', "aria": "true"}}, "status bar"),
                 ({"bar": {"animation": "lamp-breath", "glyph": '"x"', "aria": None}}, "screen readers"), ({"flip": {"class": False, "animation": "none"}}, "did not play"),
                 ({"flip": None}, "no lamp to change"), ({"errors": ["console.error: boom"]}, "boom"), ({"ok": False, "error": "boom"}, "driver failed"), ({"reduced": True}, "preference"))
        for change, expected in cases:
            found = check_motion.problems({**good, **change})
            self.assertTrue(any(expected in line for line in found), (change, found))
        moving = check_motion.problems({**still, "lamps": [dict(lamp)] * 6, "bar": {"animation": "lamp-breath", "glyph": '"x"', "aria": "true"}, "flip": {"class": True, "animation": "lamp-flip"}}, reduced=True)
        self.assertEqual(len(moving), 8, moving)      # six lamps, the bar and the transition


if __name__ == "__main__":
    unittest.main()
