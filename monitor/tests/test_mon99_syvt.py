# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Yesterday vs today has a menu entry of its own: the comparison lives in its own tab, the summary of the Sentinel keeps only its report, the tab is hidden in the lite edition, follows the CI sentinel, has an address,
an icon, a help topic and its name in the eight languages."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


def panel(tab):
    start = PAGE.index(f'<div class="tab" id="t-{tab}"')
    end = PAGE.index('<div class="tab" id="t-', start + 10)
    return PAGE[start:end]


class OwnTab(unittest.TestCase):
    def test_the_comparison_is_in_its_own_tab_and_not_in_the_summary(self):
        self.assertIn('id="s-diff"', panel("syvt"))
        self.assertIn('id="lnk-md"', panel("syvt"))
        self.assertNotIn('id="s-diff"', panel("sent"))
        self.assertEqual(PAGE.count('id="s-diff"'), 1)

    def test_the_tab_has_its_button_icon_address_and_place_in_the_list_of_tabs(self):
        self.assertRegex(PAGE, r'<button role="tab" id="n-syvt" data-tab="syvt"[^>]*hidden>')
        self.assertIn('syvt:"i-history"', PAGE)
        self.assertIn('syvt:"sentinel-yesterday"', PAGE)
        self.assertIn('"sentinel-yesterday":"syvt"', PAGE)
        self.assertEqual(PAGE.count('"sentinel-yesterday":"syvt"'), 2)      # the aliases of the address and the views
        self.assertIn('"strend","syvt","team"', PAGE)
        self.assertIn("on.syvt=on.sci;", PAGE)
        self.assertIn('"ssup","strend","syvt"].forEach', PAGE)

    def test_it_is_not_in_the_lite_edition_and_shares_the_layout_of_the_other_sentinel_tabs(self):
        self.assertIn(".lite #n-syvt,.lite #t-syvt", PAGE)
        self.assertRegex(PAGE, r"#t-strend,#t-syvt\{grid-template-columns:minmax\(0,1fr\)")

    def test_its_name_exists_in_the_eight_languages_and_differs_from_the_trend(self):
        for lang in LANGS:
            table = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(table.get("ui.tab_syvt"), lang)
            self.assertNotEqual(table["ui.tab_syvt"], table["ui.tab_strend"], lang)

    def test_the_help_topic_the_signal_table_and_the_guide_know_it(self):
        from github_actions_monitor.data_pipeline import signals
        from github_actions_monitor.ui import helpdocs
        self.assertIn('"syvt": "sentinel"', Path(helpdocs.__file__).read_text(encoding="utf-8"))
        self.assertIn('"tab:syvt"', Path(signals.__file__).read_text(encoding="utf-8"))
        text = (HERE / "docs" / "SENTINEL.md").read_text(encoding="utf-8")
        self.assertIn("#sentinel-yesterday", text)


if __name__ == "__main__":
    unittest.main()
