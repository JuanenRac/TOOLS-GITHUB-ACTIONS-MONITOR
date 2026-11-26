# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The tooltip of every setting: the page builds it from the same data as the field (help, range, values, default, what a switch does on and off, whether it applies now), a key may add its own lines
(`cfg.t.<key>`), and a guard fails when a setting has no help text in one of the eight languages or when a `cfg.t.` entry points to a setting that does not exist."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n
from github_actions_monitor.app import settings_api  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
TABLES = {lang: i18n.catalogue(lang) for lang in LANGS}      # the catalogue of the monitor and of the parts that plug in (families/)
TIP_KEYS = ("ui.cfg_tip_default_on", "ui.cfg_tip_default_off", "ui.cfg_tip_on", "ui.cfg_tip_off", "ui.cfg_tip_range", "ui.cfg_tip_default", "ui.cfg_tip_values", "ui.cfg_tip_restart", "ui.cfg_tip_live",
            "ui.cfg_tip_secure")


class EverySettingHasItsHelp(unittest.TestCase):
    def test_every_setting_has_a_help_text_in_the_eight_languages(self):
        missing = []
        for key in settings_api.FIELDS:
            help_key = settings_api.help_key(key)
            for lang in LANGS:
                if not TABLES[lang].get(help_key):
                    missing.append((lang, key))
        self.assertEqual(missing, [])

    def test_the_text_of_a_tooltip_exists_in_the_eight_languages_and_keeps_its_placeholders(self):
        for key in TIP_KEYS:
            marks = None
            for lang in LANGS:
                text = TABLES[lang].get(key)
                self.assertTrue(text, (lang, key))
                found = sorted(re.findall(r"\{(\w+)\}", text))
                marks = found if marks is None else marks
                self.assertEqual(found, marks, (lang, key))

    def test_a_specific_entry_points_to_a_setting_that_exists_and_is_in_every_language(self):
        keys = {k for k in TABLES["en"] if k.startswith("cfg.t.")}
        self.assertGreaterEqual(len(keys), 3)
        for key in keys:
            self.assertIn(key[len("cfg.t."):], settings_api.FIELDS, key)
            for lang in LANGS:
                self.assertTrue(TABLES[lang].get(key), (lang, key))
        for lang in LANGS:
            self.assertEqual({k for k in TABLES[lang] if k.startswith("cfg.t.")}, keys, lang)


class ThePage(unittest.TestCase):
    def test_every_field_gets_its_tooltip_with_pointer_keyboard_and_long_press(self):
        self.assertIn("cfgTipBind(wrap,f,input);", PAGE)
        body = PAGE[PAGE.index("function cfgTipBind"):]
        body = body[:body.index("\n}\n") + 3]
        for needle in ("mouseenter", "mouseleave", "focusin", "focusout", "Escape", "touchstart", "touchend", "touchmove"):
            self.assertIn(needle, body, needle)

    def test_the_tooltip_is_text_only_a_tooltip_for_assistive_technology_and_hidden_in_print(self):
        part = PAGE[PAGE.index("function cfgTipShow"):PAGE.index("function cfgTipBind")]
        self.assertNotIn("innerHTML", part)
        self.assertIn('setAttribute("role","tooltip")', part)
        self.assertIn("aria-describedby", part)
        self.assertIn("@media print{.cfg-tip{display:none}}", PAGE)

    def test_it_tells_what_happens_on_and_off_for_a_switch_and_the_range_for_a_number(self):
        text = PAGE[PAGE.index("function cfgTipText"):PAGE.index("function cfgTipShow")]
        for key in TIP_KEYS:
            self.assertIn(key, text, key)


if __name__ == "__main__":
    unittest.main()
