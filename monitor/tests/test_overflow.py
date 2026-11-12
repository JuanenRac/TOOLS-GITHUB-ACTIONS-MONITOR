# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""No text leaves its box: the page is opened in a headless browser in the eight languages, wide and narrow, and every box is measured (tools/check_overflow.py).

Skipped when there is no Edge, Chrome or Chromium on this computer."""
import os
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
class NoTextLeavesItsBox(unittest.TestCase):
    @unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "fonts and browsers differ on the runners of the CI: the measurement runs on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_every_language_wide_and_narrow(self):
        results = check_overflow.run(quiet=True)
        self.assertIsNotNone(results)
        self.assertEqual(len(results), len(check_overflow.LANGS) * 2)
        lines = [f"[{lang}/{size}] {item['section']}: {item['kind']} {item['at']} ({item['detail']}) {item['text']!r}" for (lang, size), items in results.items() for item in items]
        self.assertEqual(lines, [], "text outside its box:\n" + "\n".join(lines[:40]))

    @unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
    def test_the_probe_catches_a_real_overflow(self):
        """The measuring script itself: a page with a box too small for its word must be reported (so a silent probe cannot pass)."""
        import tempfile
        page = "<!doctype html><meta charset=utf-8><body><div id=box style='width:40px;border:1px solid #000;white-space:nowrap'>an_unbreakable_word_that_is_long</div>" + check_overflow.PROBE.replace("for(const t of TABS)", "for(const t of [])").replace("await openAbout()", "0") + "</body>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.html"
            path.write_text("<script>var TABS=[],CFG={groups:[]};function showTab(){}function cfgTabIds(){return[]}function openAbout(){}function openHelp(){}function openNotes(){}</script>" + page, encoding="utf-8")
            found = check_overflow.measure(check_overflow.edge(), path.as_uri(), (800, 600))
        self.assertTrue([f for f in found if f["kind"] in ("wide", "cut", "text")], found)


if __name__ == "__main__":
    unittest.main()
