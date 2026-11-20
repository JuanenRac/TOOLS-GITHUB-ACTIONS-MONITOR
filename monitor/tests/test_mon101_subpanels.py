# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The panels of Collaboration, Security, Delivery and Supply chain show one card per signal of the code, like the CI sentinel. The list of cards of the page is checked against the codes the
sentinels really raise, and every card has its name and its help in the eight languages."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.delivery import rules, supply
from github_actions_monitor.sentinels import sentinel_collab, sentinel_security

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PAGE = (ASSETS / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


def page_list(scope):
    m = re.search(r"\b" + scope + r":\[([^\]]*)\]", PAGE[PAGE.index("const SPDEF="):])
    return re.findall(r'"([^"]+)"', m.group(1))


class Cards(unittest.TestCase):
    def test_each_panel_lists_exactly_the_signals_its_sentinel_raises(self):
        self.assertEqual(sorted(page_list("scol")), sorted(sentinel_collab.TITLE_KEYS))
        self.assertEqual(sorted(page_list("ssec")), sorted(sentinel_security.SIGNAL_OF))
        self.assertEqual(sorted(page_list("sdel")), sorted(rules.CODES.values()))
        self.assertEqual(sorted(page_list("ssup")), sorted(supply.CODES.values()))

    def test_the_unavailable_keys_of_security_are_its_signal_names(self):
        keys = dict(re.findall(r'"(security\.[a-z_]+)":"([a-z_]+)"', PAGE[PAGE.index("const SPKEY="):PAGE.index("const SPF=")]))
        self.assertEqual(keys, sentinel_security.SIGNAL_OF)

    def test_every_card_has_a_name_and_a_help_in_the_eight_languages(self):
        codes = [c for scope in ("scol", "ssec", "sdel", "ssup") for c in page_list(scope)]
        self.assertEqual(len(codes), 24)
        for lang in LANGS:
            cat = json.loads((ASSETS / "locales" / (lang + ".json")).read_text(encoding="utf-8"))
            for code in codes:
                for prefix in ("ui.sp.", "ui.sph."):
                    self.assertTrue(cat.get(prefix + code), (lang, prefix + code))
            for key in ("ui.sp_count", "ui.sp_none", "ui.sp_nomatch", "ui.sp_unavailable", "ui.sp_f_repo", "ui.sp_f_level", "ui.sp_all", "ui.sp_th_signal", "ui.sp_th_n", "ui.sp_th_repos"):
                self.assertTrue(cat.get(key), (lang, key))

    def test_delivery_and_supply_have_a_table_by_code_and_filters_of_their_own(self):
        block = PAGE[PAGE.index("function spPanel"):PAGE.index('document.addEventListener("change",e=>{const t=e.target;if(!t||!t.dataset)return;')]
        for needle in ('class="sptable"', 'data-spscope="${scope}"', 'data-spk="level"', 'data-spk="repo"', "data-sprepo", "ui.sph."):
            self.assertIn(needle, block, needle)

    def test_the_page_never_asks_github_for_the_cards(self):
        block = PAGE[PAGE.index("const SPDEF="):PAGE.index('document.addEventListener("change",e=>{const t=e.target;if(!t||!t.dataset)return;')]
        self.assertNotIn("fetch(", block)



if __name__ == "__main__":
    unittest.main()
