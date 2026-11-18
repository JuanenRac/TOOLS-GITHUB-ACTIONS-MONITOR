# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The common bar at the foot of the page: save and print the tab that is open, and two lamps that say whether the AI built into the monitor is configured and whether an external AI tool is reading it.
The words exist in the eight languages, the save button asks for the brief of the open tab, the print style hides what is not the report, and the status bar says whether the built-in AI is configured
without ever carrying its key. Nothing here reaches GitHub."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
KEYS = ("bar_aria", "bar_save", "bar_print", "bar_save_fail", "bar_on", "bar_off", "bar_ai_int", "bar_ai_ext", "bar_ai_int_t", "bar_ai_ext_t")
SERVER = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")


class Bar(unittest.TestCase):
    def test_the_four_things_are_in_the_page_with_a_name_for_screen_readers(self):
        for ident in ("bar-save", "bar-print", "bar-ai-int", "bar-ai-ext"):
            self.assertIn(f'id="{ident}"', PAGE)
        for ident in ("bar-save", "bar-print"):
            self.assertRegex(PAGE, rf'<button type="button" class="ib" id="{ident}" data-i18n-title="ui\.{ident.replace("-", "_")}" data-i18n-aria="ui\.{ident.replace("-", "_")}">')

    def test_every_word_exists_in_the_eight_languages_and_differs_from_its_key(self):
        for lang in LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in KEYS:
                self.assertTrue(catalogue.get("ui." + key), (lang, key))
        english = json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8"))
        for lang in LANGS[1:]:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertNotEqual(catalogue["ui.bar_save"], english["ui.bar_save"], lang)

    def test_save_asks_for_the_brief_of_the_open_tab_in_the_language_of_the_page(self):
        self.assertIn('fetch("/api/ai/briefs?tab="+encodeURIComponent(CURTAB||"now")+"&lang="+encodeURIComponent(LANG)', PAGE)
        self.assertIn('a.download="monitor-"+(CURTAB||"now")+".json"', PAGE)

    def test_print_hides_the_menu_the_bar_and_the_dialogs(self):
        rule = re.search(r"@media print\{([^}]*)\}", PAGE[PAGE.index("#statusbar .sb-bar"):]).group(1)
        for hidden in ("#statusbar", "nav[role=tablist]", ".dlg"):
            self.assertIn(hidden, rule)

    def test_the_status_bar_says_if_the_built_in_ai_is_configured_and_never_its_key(self):
        block = SERVER[SERVER.index('"ai_internal"'):][:260]
        self.assertIn('"enabled"', block)
        self.assertNotIn("api_key", block)
        self.assertNotIn("base_url", block)


if __name__ == "__main__":
    unittest.main()
