# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two later questions of the assistant (`explain_repo`, `prioritize`): read-only like the first three, the same tools, the same limits, and a page that offers them in eight languages."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_mon104_assistant as base  # noqa: E402
from github_actions_monitor.integrations import assistant  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class TheNewQuestions(unittest.TestCase):
    def ask(self, action, args, *alerts, **assistant_settings):
        seen = []
        out = assistant.ask(action, args, base.config(**assistant_settings), base.reader(*alerts), base.echo(seen))
        return out, seen

    def test_the_list_of_actions_is_closed_and_has_five(self):
        self.assertEqual(assistant.ACTIONS, ("explain_alert", "summarize_week", "why_slow", "explain_repo", "prioritize"))
        self.assertEqual(assistant.describe(base.config())["actions"], list(assistant.ACTIONS))

    def test_a_repository_needs_its_name_and_only_reads_its_own_data(self):
        out, seen = self.ask("explain_repo", {}, base.alert("a/x"))
        self.assertEqual((out["ok"], out["error"]), (False, "argument"))
        self.assertEqual(seen, [])
        out, seen = self.ask("explain_repo", {"repo": "a/x"}, base.alert("a/x", title="the build is red"), base.alert("b/y", title="other repository"))
        self.assertTrue(out["ok"])
        text = seen[0]
        self.assertIn("a/x", text)
        self.assertNotIn("other repository", text)
        self.assertEqual({s["tool"] for s in out["sources"]}, {"runs", "alerts"})

    def test_prioritize_reads_what_is_open_and_the_status_and_the_score(self):
        out, seen = self.ask("prioritize", {}, base.alert("a/x"), base.alert("b/y", level="warn", code="ci.slow"))
        self.assertTrue(out["ok"])
        text = seen[0]
        for needle in ("QUESTION: put what needs attention in order", "OPEN ALERTS:", "STATUS:", "SCORE:", "ci.red:a/x", "ci.slow:b/y"):
            self.assertIn(needle, text)
        self.assertNotIn("do-not-show", text)

    def test_the_tools_and_the_limits_of_the_settings_still_rule(self):
        out, seen = self.ask("prioritize", {}, base.alert("a/x"), tools=["alerts"])
        self.assertTrue(out["ok"])
        self.assertNotIn("STATUS:", seen[0])
        self.assertNotIn("SCORE:", seen[0])
        out, _ = self.ask("prioritize", {}, base.alert("a/x"), max_tool_calls=1)      # one reading is enough for the alerts; the others are left out, not an error
        self.assertTrue(out["ok"])
        self.assertLessEqual(out["tool_calls"], 1)

    def test_nothing_that_writes_exists(self):
        source = (HERE / "src" / "github_actions_monitor" / "integrations" / "assistant.py").read_text(encoding="utf-8")
        for bad in ("subprocess", "urllib", "requests", "write_text", "os.system"):
            self.assertNotIn(bad, source)


class ThePageOffersThem(unittest.TestCase):
    def test_the_options_and_their_words_exist_in_eight_languages(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for action in assistant.ACTIONS:
            self.assertIn(f'<option value="{action}" data-i18n="ui.asst_a_{action}">', page)
            for lang in LANGS:
                locale = (HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")
                self.assertIn(f'"ui.asst_a_{action}"', locale)
        self.assertRegex(page, re.escape('action==="why_slow"||action==="explain_repo"'))

    def test_the_guides_name_every_question(self):
        text = (HERE / "docs" / "AI_CONNECTION.md").read_text(encoding="utf-8")
        for action in assistant.ACTIONS:
            self.assertIn(f"`{action}`", text, action)


if __name__ == "__main__":
    unittest.main()
