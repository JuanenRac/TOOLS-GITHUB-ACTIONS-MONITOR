# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The patterns of the owner for what the AI must never see (security/glob_patterns.py: wildcards, no regular expressions, a loop with a budget) and the one budget of the AI shared by the assistant,
the active notice and the summary of the report. Nothing here reaches a real provider."""
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import _timing  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import ai_notify, assistant  # noqa: E402
from github_actions_monitor.security import glob_patterns  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class ThePatternsAreWildcardsNotRegularExpressions(unittest.TestCase):
    def test_what_a_pattern_may_be(self):
        for good in ("deploy-*", "*.corp-name", "db??.prod", "key#####", "abc"):
            self.assertTrue(glob_patterns.valid(good), good)
        for bad in ("", "*", "**", "a*", "ab", "has space", "(a+)+$", "x" * 81, "a*b*c*d*e*f*ggg", 5, None):
            self.assertFalse(glob_patterns.valid(bad), bad)
        self.assertEqual(glob_patterns.clean_list(["Deploy-*", "deploy-*", "*", "ok-name"]), ["deploy-*", "ok-name"])
        self.assertEqual(glob_patterns.clean_list("deploy-*"), [])
        self.assertEqual(len(glob_patterns.clean_list(["name%d" % i for i in range(200)])), glob_patterns.MAX_PATTERNS)

    def test_it_hides_whole_words_whatever_their_case(self):
        out = glob_patterns.hide("built DEPLOY-prod-7, then (db1.corp-name) and key123 plus keyboard.", ["deploy-*", "*.corp-name", "key###"])
        self.assertEqual(out, "built [hidden], then ([hidden]) and [hidden] plus keyboard.")
        self.assertEqual(glob_patterns.hide("nothing here", ["deploy-*"]), "nothing here")
        self.assertEqual(glob_patterns.hide("x", []), "x")

    def test_a_regular_expression_is_only_text(self):
        for regex in ("(a+)+$", "(a+)+$abc", "^(a|aa)+$", "a{1,99}bc", "[a-z]+x"):
            self.assertFalse(glob_patterns.valid(regex), regex)
            self.assertEqual(glob_patterns.hide("aaaa aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa! abc", [regex]), "aaaa aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa! abc")

    def test_the_text_that_kills_a_regular_expression_is_cheap_here(self):
        evil = ["a*a*a*a*b", "*a*a*a*a*c", "a?a?a?a?a?a?a?a?b", "*aaa*aaa*aaa*aaa*z"]
        for text in ("a" * 100000, " ".join(["a" * 1990] * 300), "a" * 1999 + "!" + "a" * 50000):
            began = time.time()
            out = glob_patterns.hide(text, evil)
            self.assertLess(time.time() - began, _timing.limit(5.0))
            self.assertIsInstance(out, str)

    def test_when_the_budget_runs_out_the_rest_is_hidden_not_left_open(self):
        text = " ".join(["a" * 1900] * 400) + " tail-secret"
        out = glob_patterns.hide(text, ["a*a*a*a*b"])
        self.assertTrue(out.endswith("[hidden]"))
        self.assertNotIn("tail-secret", out)
        with mock.patch.object(glob_patterns, "STEP_BUDGET", 2):
            out = glob_patterns.hide("one two three four", ["zzz*"])
        self.assertTrue(out.startswith("one ") and out.endswith("[hidden] [hidden]"), out)

    def test_the_steps_are_bounded_by_the_two_lengths(self):
        matched, steps = glob_patterns.matches("a*a*a*a*b", "a" * 1990, 10 ** 9)
        self.assertFalse(matched)
        self.assertLess(steps, 9 * 1990 * 2)


class TheAIRemovesThemBeforeAModelSeesAText(unittest.TestCase):
    def test_the_setting_exists_is_secure_and_is_cleaned(self):
        self.assertIn("ai.redact.extra_patterns", settings_api.FIELDS)
        c = sentinel_ai.ai_config({"ai": {"redact": {"extra_patterns": ["Deploy-*", "*", "(a+)+$ x", 7]}}})
        self.assertEqual(c["redact"]["extra_patterns"], ["deploy-*"])
        self.assertEqual(sentinel_ai.ai_config({})["redact"]["extra_patterns"], [])
        self.assertEqual(sentinel_ai.ai_config({"ai": {"redact": "x"}})["redact"]["extra_patterns"], [])

    def test_sanitize_text_and_the_notice_use_them(self):
        c = sentinel_ai.ai_config({"ai": {"redact": {"extra_terms": ["falcon"], "extra_patterns": ["deploy-*"]}}})
        out = sentinel_ai.sanitize_text("Falcon failed at deploy-eu-3 today", 300, keep="head", terms=c["redact"]["extra_terms"], patterns=c["redact"]["extra_patterns"])
        self.assertEqual(out, "[hidden] failed at [hidden] today")
        data = ai_notify.payload({"repo": "deploy-eu-3", "cause": "falcon is down", "workflow": "CI"}, c["redact"])
        self.assertEqual((data["repo"], data["cause"], data["workflow"]), ("[hidden]", "[hidden] is down", "CI"))
        self.assertEqual(ai_notify.payload({"repo": "deploy-eu-3"})["repo"], "deploy-eu-3")


class OneBudgetForEveryWayToAskTheAI(unittest.TestCase):
    """The assistant, the active notice and the summary of the report spend the SAME daily total, also when they run at the same moment."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.cache = str(Path(self.dir.name) / "cache.json")
        patcher = mock.patch.object(sentinel_ai, "CACHE_FILE", self.cache)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sent = []
        self.lock = threading.Lock()

    def transport(self, cfg, system, user):
        with self.lock:
            self.sent.append(user)
        return "the answer"

    def test_the_three_ways_share_the_daily_limit_and_the_reserve_of_the_notice_is_its_own(self):
        config = {"ai": {"provider": "ollama", "model": "m", "daily_limit": 6, "assistant": {"enabled": True}},
                  "ai_alerts": {"enabled": True, "folder": self.dir.name},
                  "ai_notify": {"enabled": True, "confirmed_provider": "ollama", "max_calls_per_hour": 50, "cost_per_call_cents": 0, "max_cost_per_hour_cents": 100}}
        cfg = sentinel_ai.ai_config(config)
        store = sentinel_ai.Store(self.cache)
        results = []

        def ask(n):
            if n % 3 == 0:
                results.append(("ask", assistant.ask("summarize_week", {}, cfg, {"views": lambda: [], "score": lambda: {}}, lambda text: sentinel_ai.explain("assistant", text + str(n), cfg, store, self.transport))["ok"]))
            elif n % 3 == 1:
                results.append(("note", ai_notify.notify(config, {"id": f"i{n}", "class": "real", "state": "open", "repo": f"r{n}"}, now=1_800_000_000 + n, transport=self.transport)["sent"]))
            else:
                results.append(("report", sentinel_ai.explain("report", f"report line {n}", {**cfg, "events": ["build", "codeql", "report"]}, store, self.transport)["ok"]))
        threads = [threading.Thread(target=ask, args=(n,)) for n in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(len(results), 12)
        self.assertEqual((sum(1 for _kind, ok in results if ok), len(self.sent), store.used_today()), (6, 6, 6))
        self.assertGreaterEqual(len({kind for kind, ok in results if ok}), 2)      # the budget is shared, nobody has a lane of its own

    def test_the_notice_keeps_its_own_cap_per_hour_on_top_of_the_daily_total(self):
        config = {"ai": {"provider": "ollama", "model": "m", "daily_limit": 50}, "ai_alerts": {"enabled": True, "folder": self.dir.name},
                  "ai_notify": {"enabled": True, "confirmed_provider": "ollama", "max_calls_per_hour": 2, "cost_per_call_cents": 5, "max_cost_per_hour_cents": 500}}
        out = [ai_notify.notify(config, {"id": f"i{n}", "class": "real", "state": "open", "repo": f"r{n}"}, now=1_800_000_000 + n, transport=self.transport) for n in range(4)]
        self.assertEqual([o["reason"] for o in out], ["ok", "ok", "cap_calls", "cap_calls"])
        self.assertEqual(sentinel_ai.Store(self.cache).used_today(), 2)

    def test_the_documents_say_it(self):
        text = (HERE / "docs" / "AI_CONNECTION.md").read_text(encoding="utf-8")
        self.assertIn("`ai.redact.extra_patterns`", text)
        for lang in LANGS:
            self.assertIn("cfg.f.ai.redact.extra_patterns", (HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
