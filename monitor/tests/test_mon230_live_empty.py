# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The duration of a run in progress counts up on the page between two refreshes, and the empty lists say what to do next. The browser check of both lives in tools/check_page.py (run by
test_180_page_smoke.py in the CI job `page`); here the source of the page and the texts are checked. Nothing here reaches GitHub."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))

import _testenv  # noqa: F401,E402

try:
    import check_page  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_page = None

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
EXTRAS = (HERE / "assets" / "static" / "ui_extras.js").read_text(encoding="utf-8")


class LiveDurationAndNextSteps(unittest.TestCase):
    def test_a_run_in_progress_and_its_jobs_carry_the_instant_they_started(self):
        self.assertEqual(PAGE.count("data-live="), 2)
        self.assertIn('data-live-t="took"', PAGE)
        self.assertIn("r.status===\"in_progress\"?`", PAGE.replace("'", '"'))

    def test_the_page_counts_up_every_second_without_a_request_and_not_when_hidden(self):
        block = EXTRAS.split("counts up on the page itself", 1)[1].split("})();", 1)[0]
        self.assertIn("document.hidden", block)
        self.assertIn("},1000)", block)
        self.assertNotIn("fetch(", block)

    def test_every_placeholder_the_page_improves_exists_with_its_hint_in_the_eight_languages(self):
        block = EXTRAS.split("const NEXT=[", 1)[1].split("];", 1)[0]
        pairs = re.findall(r'\["(ui\.[a-z_0-9]+)","(ui\.es_h_[a-z0-9]+)"', block)
        self.assertGreaterEqual(len(pairs), 7)
        for lang in LANGS:
            for placeholder, hint in pairs:
                self.assertTrue(LOCALES[lang].get(placeholder), (lang, placeholder))
                self.assertTrue(LOCALES[lang].get(hint), (lang, hint))
                self.assertNotEqual(LOCALES[lang][hint], LOCALES[lang][placeholder], (lang, hint))
            self.assertTrue(LOCALES[lang].get("ui.es_open_repos"), lang)

    def test_the_judge_of_the_page_check_sees_a_frozen_duration_and_a_bare_placeholder(self):
        if check_page is None:
            self.skipTest("the tools folder does not travel in the zip of a release")
        good = {"ok": True, "tabs": {"now": {"on": True, "text": 500}}, "cfg": {"basic": {"fields": 12, "shown": True}, "interface": {"fields": 5, "shown": True}}, "total_fields": 300,
                "windows": {"about": {"open": True, "text": 100}}, "errors": [], "live": {"n": 3, "changed": 3, "gone": 0}, "next": {"asked": True, "added": True}}
        self.assertEqual(check_page.problems(good), [])
        frozen = check_page.problems({**good, "live": {"n": 3, "changed": 0, "gone": 0}})
        self.assertTrue(any("count up" in line for line in frozen), frozen)
        bare = check_page.problems({**good, "next": {"asked": True, "added": False}})
        self.assertTrue(any("what to do next" in line for line in bare), bare)


if __name__ == "__main__":
    unittest.main()
