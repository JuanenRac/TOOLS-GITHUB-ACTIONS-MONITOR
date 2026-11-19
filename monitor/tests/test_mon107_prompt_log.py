# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The optional local record of prompts (integrations/ai_prompt_log.py): off by default, only cleaned text, bounded, a file of its own that is neither in the zip nor in the backup, and only an
administrator reads or empties it. The provider is simulated: nothing leaves the computer."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import ai_prompt_log  # noqa: E402
from github_actions_monitor.security import audited_posts, auth  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402
from github_actions_monitor.util import paths  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.log = Path(self.dir.name) / "ai_prompts.jsonl"
        patcher = mock.patch.object(ai_prompt_log, "LOG_FILE", str(self.log))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = sentinel_ai.Store(str(Path(self.dir.name) / "cache.json"))

    def cfg(self, **log):
        return sentinel_ai.ai_config({"ai": {"provider": "ollama", "model": "m", "redact": {"extra_terms": ["falcon"], "extra_patterns": ["deploy-*"]},
                                             "prompt_log": dict({"enabled": True}, **log)}})

    def lines(self):
        return [json.loads(x) for x in self.log.read_text(encoding="utf-8").splitlines()] if self.log.is_file() else []


class WhatIsWritten(Base):
    def test_it_is_off_by_default_and_a_broken_value_never_turns_it_on(self):
        self.assertFalse(sentinel_ai.ai_config({})["prompt_log"]["enabled"])
        self.assertFalse(sentinel_ai.ai_config({"ai": {"prompt_log": {"enabled": "true"}}})["prompt_log"]["enabled"])
        self.assertEqual(sentinel_ai.ai_config({"ai": {"prompt_log": {"keep": 3}}})["prompt_log"]["keep"], 200)
        self.assertEqual(sentinel_ai.ai_config({"ai": {"prompt_log": "x"}})["prompt_log"], {"enabled": False, "keep": 200})
        cfg = sentinel_ai.ai_config({"ai": {"provider": "ollama"}})
        sentinel_ai.explain("ask", "why is it red", cfg, self.store, lambda c, s, u: "because")
        self.assertFalse(self.log.exists())      # off: not even the file

    def test_a_call_writes_the_cleaned_prompt_and_the_cleaned_answer(self):
        cfg = self.cfg()
        out = sentinel_ai.explain("ask", f"why did falcon fail at deploy-eu-3 with {TOKEN}", cfg, self.store,
                                  lambda c, s, u: f"it failed; try again, token {TOKEN} and falcon too")
        self.assertTrue(out["ok"])
        (line,) = self.lines()
        self.assertEqual((line["kind"], line["provider"], line["model"], line["ok"], line["reason"]), ("ask", "ollama", "m", True, ""))
        for text in (line["prompt"], line["reply"]):
            for bad in (TOKEN, "falcon", "deploy-eu-3", "Falcon"):
                self.assertNotIn(bad, text)
        self.assertIn("[hidden]", line["prompt"])
        self.assertGreater(line["system_chars"], 100)
        self.assertNotIn("system", line)
        self.assertEqual(set(line), set(ai_prompt_log.FIELDS))

    def test_a_cached_answer_is_not_a_prompt_and_a_failure_is_written_without_a_reply(self):
        cfg = self.cfg()
        sentinel_ai.explain("ask", "same question", cfg, self.store, lambda c, s, u: "answer")
        sentinel_ai.explain("ask", "same question", cfg, self.store, lambda c, s, u: "answer")
        self.assertEqual(len(self.lines()), 1)

        def boom(c, s, u):
            raise OSError("connection refused")
        sentinel_ai.explain("ask", "another question", cfg, self.store, boom)
        last = self.lines()[-1]
        self.assertFalse(last["ok"])
        self.assertEqual(last["reply"], "")
        self.assertTrue(last["reason"])

    def test_it_keeps_the_newest_lines_and_cuts_the_size(self):
        cfg = self.cfg(keep=10)
        for n in range(40):
            ai_prompt_log.record(cfg, "ask", {"provider": "ollama", "model": "m"}, "system", f"question {n} " + "x " * 5000, "reply " * 1000, now=1000 + n)
        lines = self.lines()
        self.assertLessEqual(len(lines), 10 + 5)
        self.assertEqual(lines[-1]["at"], 1039)
        self.assertLessEqual(len(lines[-1]["prompt"]), ai_prompt_log.PROMPT_CHARS)
        self.assertLessEqual(len(lines[-1]["reply"]), ai_prompt_log.REPLY_CHARS)

    def test_a_line_that_cannot_be_written_never_stops_a_call(self):
        cfg = self.cfg()
        with mock.patch.object(ai_prompt_log.private_io, "open_append", side_effect=OSError("disk full")):
            out = sentinel_ai.explain("ask", "question", cfg, self.store, lambda c, s, u: "answer")
        self.assertTrue(out["ok"])


class WhoReadsIt(Base):
    def test_reading_and_emptying(self):
        cfg = self.cfg()
        for n in range(3):
            ai_prompt_log.record(cfg, "ask", {"provider": "ollama", "model": "m"}, "s", f"q{n}", "r", now=n)
        data = ai_prompt_log.read(cfg, 2)
        self.assertEqual([e["prompt"] for e in data["entries"]], ["q2", "q1"])
        self.assertTrue(data["enabled"])
        self.assertEqual(ai_prompt_log.clear(), 3)
        self.assertFalse(self.log.exists())
        self.assertEqual(ai_prompt_log.read(cfg)["entries"], [])
        self.log.write_text("not json\n[1]\n" + json.dumps({"prompt": "ok"}) + "\n", encoding="utf-8")
        self.assertEqual(len(ai_prompt_log.read(cfg)["entries"]), 1)

    def test_only_an_administrator_reads_or_empties_it_and_the_clearing_is_audited(self):
        self.assertEqual(auth.required_role("GET", "/api/ai/prompts"), "admin")
        self.assertEqual(auth.required_role("POST", "/api/ai/prompts/clear"), "admin")
        self.assertIn("/api/ai/prompts/clear", audited_posts.AUDITED)
        self.assertTrue("/api/ai/prompts".startswith(__import__("github_actions_monitor.app.actions_monitor", fromlist=["x"]).LITE_PATHS))      # not in the lite edition

    def test_the_file_is_a_log_of_its_own_and_never_travels(self):
        self.assertEqual(paths.kind_of("ai_prompts.jsonl"), "logs")
        import make_release
        self.assertIn("ai_prompts.jsonl", make_release.FORBIDDEN_NAMES)
        source = (HERE / "src" / "github_actions_monitor" / "ops" / "bundle.py").read_text(encoding="utf-8")
        self.assertNotIn("ai_prompts", source)      # the backup package lists its files by name and this one is not among them


class TheSettingsAndTheirHelp(unittest.TestCase):
    def test_the_two_settings_exist_with_help_in_eight_languages(self):
        for key in ("ai.prompt_log.enabled", "ai.prompt_log.keep"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in LANGS:
                text = (HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")
                self.assertIn(f'"cfg.h.{key}"', text)
        self.assertIn("`ai.prompt_log.enabled`", (HERE / "docs" / "AI_CONNECTION.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
