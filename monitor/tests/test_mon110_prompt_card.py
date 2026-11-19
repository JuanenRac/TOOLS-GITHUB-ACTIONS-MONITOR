# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The card of the record of prompts and the column of origin of the table of models: they are in the page, every text they use exists in the eight languages, and the text of a prompt is
written with textContent (a prompt is text of the person who asked, never markup)."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
KEYS = ["ui.ai_col_origin", "ui.ai_src_manual", "ui.ai_src_file", "ui.ai_src_provider"] + [f"ui.pl_{n}" for n in ("h", "help", "show", "clear", "off", "empty", "cleared", "confirm", "count", "denied", "failed")]
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


class Card(unittest.TestCase):
    def test_every_text_exists_in_the_eight_languages(self):
        for lang in LANGS:
            data = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            missing = [k for k in KEYS if not str(data.get(k, "")).strip()]
            self.assertEqual(missing, [], lang)

    def test_the_card_reads_and_clears_through_the_two_routes(self):
        self.assertIn('fetch("/api/ai/prompts"', PAGE)
        self.assertIn('fetch("/api/ai/prompts/clear"', PAGE)
        self.assertIn('querySelector(".pl-extra")', PAGE)

    def test_a_prompt_is_never_written_as_markup(self):
        start = PAGE.index('className="cfg-group pl-extra"')
        block = PAGE[start:PAGE.index('querySelector(".sk-extra")', start)]
        shown = re.findall(r"\.innerHTML\s*=\s*([^;]+);", block)
        self.assertTrue(all(s.strip() in ('""', "`<h3 id=\"pl-h\"></h3>") or s.startswith("`<h3") for s in shown), shown)
        self.assertIn("p.textContent=(x.prompt", block)

    def test_the_origin_column_is_in_the_table_of_models(self):
        self.assertIn('"ui.ai_col_origin"', PAGE)
        self.assertIn('T("ui.ai_src_"+s)', PAGE)


if __name__ == "__main__":
    unittest.main()
