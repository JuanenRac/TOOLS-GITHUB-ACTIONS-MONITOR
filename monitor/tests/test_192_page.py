# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Team tab in the page: it is in the list of tabs of the Complete edition and not of Lite, the browser checks (smoke test and overflow measurement) go through every tab of that list, the
deep links of the health views are known to the page, and every word of the tab and of the repository window exists in the eight languages."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class TeamTab(unittest.TestCase):
    def test_the_tab_is_in_complete_and_not_in_lite(self):
        found = re.search(r"const TABS=LITE\?(\[[^\]]*\]):(\[[^\]]*\])", PAGE)
        self.assertIsNotNone(found)
        lite, complete = json.loads(found.group(1)), json.loads(found.group(2))
        self.assertIn("team", complete)
        self.assertNotIn("team", lite)
        self.assertIn(".lite #n-team", PAGE)

    def test_the_browser_checks_go_through_every_tab_of_the_list(self):
        for tool in ("check_page.py", "check_overflow.py"):
            if not (ROOT / "tools" / tool).is_file():
                self.skipTest("the tools of the repository are not in the product folder")
            text = (ROOT / "tools" / tool).read_text(encoding="utf-8")
            self.assertIn("for(const t of TABS)", text, tool)

    def test_the_deep_links_are_known_to_the_page(self):
        for view in ("team", "repos", "repo"):
            self.assertRegex(PAGE, rf"\b{view}:\"(team|repos)\"", view)
        self.assertIn("QS.get(\"repo\")", PAGE)

    def test_every_word_of_the_tab_and_of_the_window_exists_in_the_eight_languages(self):
        used = set(re.findall(r'"(ui\.(?:team|rh)_[a-z_]+)"', PAGE)) | set(re.findall(r'T\("(ui\.(?:team|rh)_[a-z_]+)"', PAGE)) | {"ui.tab_team", "ui.view_team", "ui.view_repo"}
        used = {k for k in used if not k.endswith("_")}
        used |= {f"ui.team_sev_{s}" for s in ("all", "bad", "warn", "ok", "unknown")} | {f"ui.rh_life_{s}" for s in ("healthy", "degraded", "paused", "error", "off")}
        for lang in LANGS:
            keys = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(k for k in used if k not in keys), [], lang)
            for key in used:
                self.assertTrue(str(keys[key]).strip(), (lang, key))


if __name__ == "__main__":
    unittest.main()
