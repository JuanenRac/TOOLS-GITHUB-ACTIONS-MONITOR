# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The pictures of the Charts tab fit: the ring of the result of the last 24 hours, the bars and the timeline are opened in a headless browser, wide and narrow, light and dark, in the eight
languages, and the geometry is measured (tools/check_charts.py): no picture cut by its box, no bar or label outside its picture, no legend lying on the ring.

Skipped when there is no Edge, Chrome or Chromium on this computer, or no tools folder. The source of the page is also read as text (this part runs everywhere)."""
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
    import check_charts  # noqa: E402
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_charts = check_overflow = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
BROWSER_ONLY = unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")


class TheSource(unittest.TestCase):
    def test_the_rows_of_the_tab_never_get_shorter_than_a_picture(self):
        rule = re.search(r"#t-charts\{grid-template-columns:[^}]*\}", PAGE).group(0)
        self.assertRegex(rule, r"grid-template-rows:minmax\(\d+px,1fr\) minmax\(\d+px,1\.2fr\)")
        self.assertIn("overflow:auto", rule)

    def test_the_legend_of_the_ring_is_measured_from_its_words_not_guessed(self):
        body = PAGE[PAGE.index("function donut("):PAGE.index("function rates(")]
        self.assertIn("textW(", body)
        self.assertNotIn("size=Math.min(w*0.5", body)

    def test_the_margin_of_the_timeline_holds_half_of_its_last_label(self):
        body = PAGE[PAGE.index("function timeline("):PAGE.index("function durations(")]
        self.assertRegex(body, r"R=Math\.ceil\(textW\(clock\(")

    def test_the_bars_have_the_height_of_their_frame_and_room_for_their_axis_words(self):
        body = PAGE[PAGE.index("function durations("):PAGE.index("function durations(") + 1400]
        self.assertIn("H=Math.max(120,h-42)", body)
        self.assertIn('height="${H+42}"', body)
        self.assertIn("textW(t,12)", body)


@unittest.skipUnless(check_charts is not None and check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
class TheGeometry(unittest.TestCase):
    @BROWSER_ONLY
    def test_every_picture_fits_in_the_eight_languages_wide_and_narrow_light_and_dark(self):
        results = check_charts.run(quiet=True)
        self.assertIsNotNone(results)
        self.assertEqual(len(results), len(check_charts.LANGS) * 2)
        lines = [f"[{lang}/{size}/{item['theme']}] {item['kind']} {item['at']}: {item['detail']}" for (lang, size), items in sorted(results.items()) for item in items]
        self.assertEqual(lines, [], "a picture does not fit:\n" + "\n".join(lines[:40]))

    @BROWSER_ONLY
    def test_the_probe_catches_a_label_outside_its_picture_and_a_picture_cut_by_its_box(self):
        """The measuring script itself: a silent probe could never fail."""
        page = ("<!doctype html><meta charset=utf-8><body><section style='width:200px;height:60px'><div id=donut style='height:50px;overflow:hidden'>"
                "<svg width=180 height=120 viewBox='0 0 180 120'><rect x=2 y=2 width=40 height=40 fill=red /><text x=150 y=30>a label that is too long for the drawing</text></svg></div></section>"
                + check_charts.PROBE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.html"
            path.write_text("<script>function showTab(){}</script>" + page, encoding="utf-8")
            doc = check_overflow.measure_once(check_overflow.edge(), path.as_uri(), (800, 600), report="charts-report")
        kinds = {f["kind"] for f in doc["found"]}
        self.assertIn("label_outside", kinds)
        self.assertTrue(kinds & {"picture_cut", "box_cuts_picture"}, kinds)


if __name__ == "__main__":
    unittest.main()
