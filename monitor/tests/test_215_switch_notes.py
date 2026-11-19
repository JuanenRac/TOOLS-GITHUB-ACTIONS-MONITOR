# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The switches that cost requests or open a tab say what you will see and what it costs (cfg.t.*), in the eight languages, and only for settings that exist."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from github_actions_monitor.app import settings_api  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
MUST = ("sentinels.security.enabled", "sentinels.supply.enabled", "sentinels.delivery.enabled", "sentinels.collab.enabled", "runners.model.enabled", "ai.assistant.enabled",
        "ai.similar.enabled", "ai.prompt_log.enabled", "live.sse.enabled", "compare.enabled", "screens.enabled", "updates.check")


class Notes(unittest.TestCase):
    def test_every_note_is_for_a_switch_that_exists(self):
        for key in LOCALES["en"]:
            if key.startswith("cfg.t."):
                self.assertIn(key[len("cfg.t."):], settings_api.FIELDS, key)

    def test_the_switches_that_cost_or_open_something_have_a_note(self):
        for setting in MUST:
            self.assertIn("cfg.t." + setting, LOCALES["en"], setting)

    def test_each_note_exists_in_the_eight_languages_and_is_not_a_copy(self):
        for key in [k for k in LOCALES["en"] if k.startswith("cfg.t.")]:
            texts = {lang: LOCALES[lang].get(key) for lang in LANGS}
            self.assertTrue(all(isinstance(t, str) and len(t) > 30 for t in texts.values()), key)
            for lang in LANGS[1:]:
                self.assertNotEqual(texts[lang], texts["en"], f"{key} {lang}")

    def test_the_english_note_says_what_you_will_see_and_what_it_costs(self):
        for key in [k for k in LOCALES["en"] if k.startswith("cfg.t.")]:
            text = LOCALES["en"][key]
            self.assertIn("You will see:", text, key)
            self.assertIn("Cost:", text, key)


if __name__ == "__main__":
    unittest.main()
