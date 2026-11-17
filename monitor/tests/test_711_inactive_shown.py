# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A red that ages out and a workflow that is inactive leave the list of reds, so the page must say so: the figures the server counts for them have to be read by the page and have text in the eight
languages (the help of `ci.inactive_days` and `ci.red_age_days` promises that they are shown as inactive)."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
SERVER = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
SHOWN = {"inactive": "ui.n_inactive", "dormant": "ui.n_dormant", "inactive_repos": "ui.n_dormant", "awaiting": "ui.n_awaiting", "ghost": "ui.n_ghost"}


class InactiveIsShown(unittest.TestCase):
    def test_the_server_counts_what_the_page_has_to_show(self):
        for figure in SHOWN:
            self.assertRegex(SERVER, r'figures\["%s"\]' % figure)

    def test_the_page_reads_each_of_those_figures(self):
        for figure, key in SHOWN.items():
            with self.subTest(figure=figure):
                self.assertRegex(PAGE, r"\bF\.%s\b" % re.escape(figure))
                self.assertIn('T("%s"' % key, PAGE)

    def test_the_lines_are_in_the_now_tab_and_in_the_eight_catalogues(self):
        for line in ("now-inactive", "now-dormant", "now-awaiting", "now-ghost"):
            self.assertIn('id="%s"' % line, PAGE)
        for lang in LANGS:
            texts = json.loads((HERE / "assets" / "locales" / (lang + ".json")).read_text(encoding="utf-8"))
            for key in ("ui.n_inactive", "ui.n_dormant"):
                self.assertTrue(texts.get(key), (lang, key))
            self.assertIn("{n}", texts["ui.n_inactive"])
            self.assertTrue("{n}" in texts["ui.n_dormant"] and "{m}" in texts["ui.n_dormant"], lang)


if __name__ == "__main__":
    unittest.main()
