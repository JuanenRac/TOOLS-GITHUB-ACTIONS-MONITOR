# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Both skills of the monitor name every card of the sentinel panels and every series of the daily trend, and say how to read them. A card or a series added to the page without a line in the skills fails here."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.integrations import skills

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


class Skills(unittest.TestCase):
    def test_every_card_and_every_series_is_named_in_both_skills_and_the_core_points_to_it(self):
        codes = re.findall(r'"([a-z]+\.[a-z_.]+)"', PAGE[PAGE.index("const SPDEF="):PAGE.index("const SPKEY=")])
        series = re.findall(r'\["([a-z_0-9]+)","ui\.tr_', PAGE[PAGE.index("const TRS="):PAGE.index("let TRR=")])
        self.assertEqual((len(codes), len(series)), (24, 25))
        for name in skills.names():
            text = skills.read(name, "references/cards-and-trend.md")
            for word in codes + series:
                self.assertIn("`" + word + "`", text, (name, word))
            for needle in ("/api/ai/briefs", "/api/ai/index", "/api/sentinel", "null", "unavailable"):
                self.assertIn(needle, text, (name, needle))
            self.assertIn("references/cards-and-trend.md", skills.read(name), name)


if __name__ == "__main__":
    unittest.main()
