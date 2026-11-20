# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What fits on the wall screens and the kiosk. Without a browser: the safe margin (a setting and an address parameter, kept inside 0 to 10 and 0 by default), the rules of the page that make a list say
what it leaves out and a hidden row really disappear, and the guides naming every size that the tool measures. With a browser (Edge, Chrome or Chromium in headless mode, against the demo monitor with invented
data): every screen in the eight languages and in the sizes of a television, a monitor, an ultra-wide monitor and a turned screen shows no page that scrolls, no text or box beyond the edge, no box whose content
does not fit, no heading that ends in dots, no two texts that cover each other, no type smaller than the floor and no row hidden without the line "+N more". The browser part measures a few representative
combinations in the normal suite; the whole matrix (every language, every size, every kind of data, and the kiosk) runs when MONITOR_SCREENS_MATRIX is set (the CI sets it). Skipped when there is no
browser (and on a CI runner unless MONITOR_BROWSER_TESTS=1)."""
import os
import re
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor, screens
from github_actions_monitor.surfaces import kiosk

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
HTML = HERE / "assets" / "static" / "screens.html"
DOCS = HERE / "docs"
sys.path.insert(0, str(TOOLS))
try:
    import check_overflow  # noqa: E402
    import check_screens  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = check_screens = None


class TheSafeMargin(unittest.TestCase):
    def test_it_is_off_by_default_and_kept_between_zero_and_ten(self):
        self.assertEqual(screens.settings({})["safe_margin_percent"], 0)
        self.assertEqual(actions_monitor.DEFAULTS["screens"]["safe_margin_percent"], 0)
        for value, expected in ((4, 4), ("5", 5), (99, 10), (-3, 0), ("x", 0), (True, 0), (None, 0)):
            self.assertEqual(screens.settings({"screens": {"safe_margin_percent": value}})["safe_margin_percent"], expected, value)
        self.assertEqual(kiosk.settings({})["safe_margin_percent"], 0)
        self.assertEqual(actions_monitor.DEFAULTS["kiosk"], kiosk.DEFAULTS)
        for value, expected in ((4, 4), (10, 10), (11, 0), (-1, 0), ("5", 0), (True, 0)):
            self.assertEqual(kiosk.settings({"kiosk": {"safe_margin_percent": value}})["safe_margin_percent"], expected, value)

    def test_an_address_may_ask_for_it_inside_the_same_limits(self):
        cfg = screens.settings({"screens": {"safe_margin_percent": 3}})
        self.assertEqual(screens.params({}, cfg)["safe"], 3)
        self.assertEqual(screens.params({"safe": "6"}, cfg)["safe"], 6)
        self.assertEqual(screens.params({"safe": "60"}, cfg)["safe"], 10)
        self.assertEqual(screens.params({"safe": "junk"}, cfg)["safe"], 3)

    def test_the_page_reads_it_and_draws_everything_smaller_inside_it(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("P.safe", html)
        self.assertIn("--safe", html)
        self.assertRegex(html, r"font-size:max\(calc\(var\(--minpx\)\*1px/\.8\),calc\(var\(--k\)\*var\(--d\)\*\(1 - var\(--safe\)/50\)")      # the type shrinks with the margin, so the design fits in what is left
        self.assertRegex(html, r"padding:calc\(1rem \+ var\(--safe\)\*1vh\)")
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("kiosk-safe", page)


class TheTypeOfTheKioskThatGrowsWithTheWindow(unittest.TestCase):
    def test_it_is_off_by_default_and_only_a_true_turns_it_on(self):
        self.assertIs(kiosk.settings({})["scale_with_window"], False)
        self.assertIs(actions_monitor.DEFAULTS["kiosk"]["scale_with_window"], False)
        for value, expected in ((True, True), (False, False), ("yes", False), (1, False), (None, False)):
            self.assertIs(kiosk.settings({"kiosk": {"scale_with_window": value}})["scale_with_window"], expected, value)

    def test_the_page_scales_from_a_window_of_1080_px_on_its_short_side(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("scale_with_window", page)
        self.assertRegex(page, r"Math\.min\(window\.innerWidth,window\.innerHeight\)/1080")
        self.assertIn('QS.get("fit")', page)


class TheRulesOfThePage(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")

    def test_a_hidden_row_disappears_whatever_its_own_display_says(self):
        self.assertIn("[hidden]{display:none!important}", self.html)

    def test_a_list_that_leaves_rows_out_says_how_many(self):
        self.assertIn('T("ui.scr_more"', self.html)
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                text = i18n.t("ui.scr_more", n=3)
                self.assertIn("3", text, lang)
                self.assertNotEqual(text, "ui.scr_more", lang)
        with i18n.use_language("en"):
            self.assertEqual(i18n.t("ui.scr_more", n=3), "+3 more")

    def test_a_heading_never_ends_in_dots(self):
        css = re.search(r"\.card h2\{[^}]*\}", self.html).group(0)
        self.assertNotIn("text-overflow", css)
        self.assertNotIn("nowrap", css)

    def test_no_type_of_the_page_is_below_the_floor(self):
        """The smallest size in rem of the page (the type is a part of the short side of the window): 0.8 rem is 12.8 px in a window of 1080 px, over the 12 px floor of the tool."""
        sizes = [float(m) for m in re.findall(r"font-size:\s*(\d*\.?\d+)rem", self.html)]
        self.assertGreaterEqual(min(sizes), 0.8)


class TheGuidesNameWhatIsMeasured(unittest.TestCase):
    @unittest.skipIf(check_screens is None, "the tools folder does not travel in the zip of a release")
    def test_every_size_of_the_tool_is_in_the_guide_of_the_screens_in_the_eight_languages(self):
        suffixes = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
        for suffix in suffixes:
            text = (DOCS / f"SCREENS{suffix}.md").read_text(encoding="utf-8")
            for name, (width, height) in check_screens.SIZES.items():
                self.assertIn(f"{width}x{height}", text, (suffix, name))
            self.assertIn("safe_margin_percent", text, suffix)
            self.assertIn("?safe=", text, suffix)
            self.assertIn("check_screens.py", text, suffix)
            kiosk_text = (DOCS / f"KIOSK{suffix}.md").read_text(encoding="utf-8")
            self.assertIn("kiosk.safe_margin_percent", kiosk_text, suffix)
            self.assertIn("safe=", kiosk_text, suffix)

    @unittest.skipIf(check_screens is None, "the tools folder does not travel in the zip of a release")
    def test_the_floor_of_the_tool_matches_the_guide(self):
        self.assertAlmostEqual(check_screens.MIN_FONT * 1080, 11.34, places=1)      # the guide says 12 px in a window of 1080 px, a hundredth of the short side rounded up


def _ready():
    return check_screens is not None and check_overflow is not None and bool(check_overflow.edge())


@unittest.skipUnless(_ready() or os.environ.get("MONITOR_REQUIRE_BROWSER"), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class TheScreensFitInABrowser(unittest.TestCase):
    MATRIX = os.environ.get("MONITOR_SCREENS_MATRIX", "")      # "1": everything; or a list of sizes ("4K,portrait") to measure all the languages in those

    @classmethod
    def setUpClass(cls):
        if not _ready():      # a job that asks for the browser (MONITOR_REQUIRE_BROWSER) must not pass by skipping
            raise RuntimeError("MONITOR_REQUIRE_BROWSER is set and there is no browser (or no tools folder) on this computer")
        cls.demo, port = check_screens.start_demo()
        cls.relay = check_overflow.relay(port, probe=check_screens.PROBE, head=check_screens.HEAD.encode("utf-8"))
        cls.kiosk_relay = check_overflow.relay(port, probe=check_screens.KIOSK_PROBE, head=check_screens.HEAD.encode("utf-8"))
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}"
        cls.kiosk_base = f"http://127.0.0.1:{cls.kiosk_relay.server_address[1]}"
        cls.browser = check_overflow.edge()

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.kiosk_relay.shutdown()
        cls.demo.terminate()

    def clean(self, report, label, ignore=()):
        self.assertEqual(report.get("errors", []), [], label)
        found = [f for f in report.get("found", []) if f["kind"] not in ignore]
        shown = ["%s %s/%s %s %s" % (f["kind"], f["screen"], f["data"], f["at"], f["detail"]) for f in found[:10]]
        self.assertEqual(found, [], (label, len(found), shown))

    def wall(self, lang, size, data=check_screens.DATA if check_screens else (), safe=0, inset=None):
        return check_screens.measure_one(self.browser, self.base, lang, size, data, check_screens.KINDS, safe, inset)

    def test_a_few_representative_cells_fit(self):
        """The normal suite: English, German (the longest words) and Japanese (no spaces) in a monitor, a turned screen and a super ultra-wide one, with the invented data, the worst data and no data."""
        for lang in ("en", "de", "ja"):
            for size in ("1080p", "portrait", "superwide"):
                with self.subTest(lang=lang, size=size):
                    self.clean(self.wall(lang, size, check_screens.QUICK_DATA), (lang, size))

    def kiosk(self, lang, size, preset, safe=0):
        return check_screens.measure_kiosk(self.browser, self.kiosk_base, lang, size, preset, 150, safe, None, True)

    def test_the_kiosk_fits_in_a_monitor_and_in_a_4k_television(self):
        """The page of the monitor with the kiosk profile and the type that grows with the window: no text smaller than the floor, none beyond the edge, none over another. The panels that scroll inside (kind
        scroll) are the known gap of the kiosk, which has no one to scroll them, and are not part of this test."""
        for lang in ("en", "de"):
            for size in ("1080p", "4K"):
                with self.subTest(lang=lang, size=size):
                    self.clean(self.kiosk(lang, size, "ops"), (lang, size), ignore=("scroll",))

    def test_the_kiosk_keeps_the_safe_margin(self):
        for lang in ("en", "ja"):
            with self.subTest(lang=lang):
                self.clean(self.kiosk(lang, "1080p", "quiet", safe=5), (lang, "kiosk safe 5"), ignore=("scroll",))

    def test_the_kiosk_in_the_whole_matrix(self):
        if not self.MATRIX:
            self.skipTest("MONITOR_SCREENS_MATRIX is not set: the whole matrix runs in the CI")
        sizes = tuple(check_screens.SIZES) if self.MATRIX == "1" else tuple(s for s in self.MATRIX.split(",") if s in check_screens.SIZES)
        for size in sizes:
            for lang in check_screens.LANGS:
                with self.subTest(lang=lang, size=size):
                    self.clean(self.kiosk(lang, size, "ops"), (lang, size), ignore=("scroll",))

    def test_a_television_that_cuts_the_edge_loses_nothing_with_the_safe_margin(self):
        """Overscan: with a margin of 5 % every text and box is at least 5 % inside each edge."""
        for lang in ("en", "de"):
            with self.subTest(lang=lang):
                self.clean(self.wall(lang, "1080p", check_screens.QUICK_DATA, safe=5), (lang, "safe 5"))

    def test_the_whole_matrix(self):
        if not self.MATRIX:
            self.skipTest("MONITOR_SCREENS_MATRIX is not set: the whole matrix runs in the CI")
        sizes = tuple(check_screens.SIZES) if self.MATRIX == "1" else tuple(s for s in self.MATRIX.split(",") if s in check_screens.SIZES)
        self.assertTrue(sizes, self.MATRIX)
        for size in sizes:
            for lang in check_screens.LANGS:
                with self.subTest(lang=lang, size=size):
                    self.clean(self.wall(lang, size), (lang, size))

    def test_the_whole_matrix_with_a_safe_margin(self):
        if not self.MATRIX:
            self.skipTest("MONITOR_SCREENS_MATRIX is not set: the whole matrix runs in the CI")
        if self.MATRIX != "1" and "1080p" not in self.MATRIX.split(","):
            self.skipTest("measured with the size 1080p")
        for lang in check_screens.LANGS:
            with self.subTest(lang=lang):
                self.clean(self.wall(lang, "1080p", check_screens.QUICK_DATA, safe=5), (lang, "safe 5"))


if __name__ == "__main__":
    unittest.main()
