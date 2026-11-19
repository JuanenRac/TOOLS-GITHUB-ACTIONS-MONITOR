# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The summary of the next report: a person asks for a draft (from the figures, or from the AI when `ai.report_summary.enabled` is on), edits it and approves it; the approved text opens the NEXT report,
once, escaped, and says who wrote it. Nothing is written by itself, the text is cleaned, and the route is for an administrator at this computer. No network, no real AI."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.reporting import report_builder as builder, report_render as render, report_service as service, report_summary as summary  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
NOW = 1_800_000_000.0
SNAPSHOT = {"state": "scored", "score": 81.5, "letter": "B", "trend": {"direction": "up", "delta": 2.0}, "parts": [], "missing_parts": []}
ALERTS = [{"id": "a1", "level": "error", "sentinel": "ci", "repo": "alpha", "title": "build is red"}, {"id": "a2", "level": "warning", "sentinel": "ci", "repo": "beta", "title": "slow"}]
TEAM = {"all": 3, "totals": {"bad": 1, "warn": 1, "ok": 1, "unknown": 0}, "ranking": [{"repo": "alpha", "state": "bad", "risk": 9, "alerts": 1, "red_workflows": 1}, {"repo": "beta", "state": "warn", "risk": 4, "alerts": 1, "red_workflows": 0}]}
ON = {"ai": {"provider": "ollama", "report_summary": {"enabled": True}}}


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sum_test_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        patch = mock.patch.object(service, "folder", lambda base=None: self.tmp / "reports")
        patch.start()
        self.addCleanup(patch.stop)

    def doc(self):
        return builder.build("acme", SNAPSHOT, ALERTS, TEAM, NOW)


class TheText(unittest.TestCase):
    def test_it_is_plain_cut_and_cleaned(self):
        dirty = "Hello\x00 <b>world</b> <script>alert(1)</script>\r\n\r\nSecond  paragraph with a token ghp_" + "a" * 36 + " inside"
        text = summary.clean(dirty)
        self.assertNotIn("\x00", text)
        self.assertNotIn("<b>", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("ghp_" + "a" * 36, text)
        self.assertEqual(text.count("\n\n"), 1, "a blank line stays a paragraph")
        self.assertEqual(len(summary.clean("word " * 1000)), summary.MAX_CHARS - 1)      # cut, and the space at the end goes
        self.assertEqual(summary.clean(None), "")
        self.assertEqual(summary.clean("   \n\n  "), "")

    def test_the_template_is_made_of_the_figures_in_every_language(self):
        doc = Folder.doc(type("X", (), {})())
        for lang in i18n.LANGS:
            text = summary.template(doc, lang)
            self.assertTrue(text and "81.5" in text, (lang, text))
            self.assertIn("alpha", text)
        self.assertEqual(summary.template(doc, "en"), summary.template(doc, "en"), "deterministic")


class TheAiDraft(unittest.TestCase):
    def setUp(self):
        self.doc = Folder.doc(type("X", (), {})())

    def test_off_by_default_and_the_ai_is_not_asked(self):
        asked = []
        for config in ({}, {"ai": {"provider": "ollama"}}, {"ai": {"report_summary": {"enabled": "yes"}}}):
            answer = summary.ai_draft(config, self.doc, "en", lambda text: asked.append(text) or {"ok": True, "text": "x"})
            self.assertEqual(answer["status"], "off")
        self.assertEqual(asked, [])
        self.assertFalse(am.DEFAULTS.get("ai", {}).get("report_summary", {}).get("enabled", False))
        self.assertFalse(sentinel_ai.AI_DEFAULTS["report_summary"]["enabled"])

    def test_with_the_switch_the_ai_text_is_cleaned_and_never_trusted(self):
        reply = {"ok": True, "text": "All good <i>mostly</i>. Visit now.", "provider": "ollama", "model": "m"}
        answer = summary.ai_draft(ON, self.doc, "en", lambda text: reply)
        self.assertEqual((answer["status"], answer["provider"], answer["model"]), ("ok", "ollama", "m"))
        self.assertNotIn("<i>", answer["text"])

    def test_a_failure_or_a_refusal_is_an_answer(self):
        def boom(text):
            raise RuntimeError("down")
        self.assertEqual(summary.ai_draft(ON, self.doc, "en", boom)["status"], "failed")
        self.assertEqual(summary.ai_draft(ON, self.doc, "en", lambda t: {"ok": False, "error": "The AI is off"})["status"], "no_ai")
        self.assertEqual(summary.ai_draft(ON, self.doc, "en", lambda t: {"ok": False, "error": "budget"})["status"], "failed")

    def test_the_model_sees_the_figures_and_the_worst_alerts_only(self):
        seen = []
        summary.ai_draft(ON, self.doc, "en", lambda text: seen.append(text) or {"ok": False, "error": ""})
        self.assertIn("alpha: build is red", seen[0])
        self.assertIn("81.5", seen[0])

    def test_the_drafts_ask_the_ai_only_when_told_to(self):
        asked = []
        both = summary.drafts(ON, self.doc, "en", lambda t: asked.append(t) or {"ok": True, "text": "x"}, with_ai=False)
        self.assertEqual((both["ai"]["status"], asked), ("not_asked", []))


class TheApprovedText(Folder):
    def test_it_is_kept_cleaned_and_only_with_a_known_origin(self):
        self.assertIsNone(service.pending_summary("acme"))
        self.assertIsNone(service.save_summary("acme", "   ", "ai"))
        kept = service.save_summary("acme", "Quiet week <b>mostly</b>.", "ai", now=NOW)
        self.assertEqual((kept["origin"], kept["text"]), ("ai", "Quiet week mostly."))
        self.assertEqual(service.save_summary("acme", "x", "weird")["origin"], "edited")
        self.assertEqual(service.pending_summary("acme")["text"], "x")
        self.assertIsNone(service.pending_summary("another"), "it belongs to the account")
        service.clear_summary("acme")
        self.assertIsNone(service.pending_summary("acme"))

    def test_a_value_that_is_not_what_the_service_wrote_is_not_believed(self):
        directory = service.folder()
        directory.mkdir(parents=True)
        (directory / service.STATE_FILE).write_text(json.dumps({"accounts": {"acme": {"summary": {"text": "hi", "origin": "root"}}}}), encoding="utf-8")
        self.assertIsNone(service.pending_summary("acme"))
        (directory / service.STATE_FILE).write_text(json.dumps({"accounts": {"acme": {"summary": "plain string"}}}), encoding="utf-8")
        self.assertIsNone(service.pending_summary("acme"))

    def test_the_next_report_carries_it_once_in_both_formats_escaped(self):
        service.save_summary("acme", "Rollout is <b>safe</b> & calm.\n\nSecond paragraph.", "edited", now=NOW)
        first = service.run({}, "acme", SNAPSHOT, ALERTS, TEAM, now=NOW + 10)
        directory = service.folder()
        html = (directory / next(n for n in first["files"] if n.endswith(".html"))).read_text(encoding="utf-8")
        md = (directory / next(n for n in first["files"] if n.endswith(".md"))).read_text(encoding="utf-8")
        self.assertIn("Rollout is safe &amp; calm.", html)
        self.assertNotIn("<b>safe", html)
        self.assertIn("Second paragraph.", html)
        self.assertIn("Written by a person.", html)
        self.assertIn("## Summary", md)
        self.assertLess(md.index("## Summary"), md.index("## What changed"), "it opens the report")
        self.assertIsNone(service.pending_summary("acme"), "used once")
        second = service.run({}, "acme", SNAPSHOT, ALERTS, TEAM, now=NOW + 7200)
        again = (directory / next(n for n in second["files"] if n.endswith(".md"))).read_text(encoding="utf-8")
        self.assertNotIn("## Summary", again)

    def test_a_report_without_a_summary_is_the_same_as_before(self):
        doc = service.document({}, "acme", SNAPSHOT, ALERTS, TEAM, now=NOW)
        self.assertNotIn("summary", doc)
        self.assertNotIn("Summary", render.markdown(doc, "en"))

    def test_the_headings_exist_in_eight_languages(self):
        for lang in i18n.LANGS:
            for key in ("report.h_summary", "report.summary_template", "report.summary_ai", "report.summary_edited"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))


class TheRoute(Folder):
    def post(self, request, config=None):
        with mock.patch.object(am, "report_gather", return_value=(SNAPSHOT, ALERTS, TEAM, None)), mock.patch.object(am, "report_account", return_value="acme"):
            return am.report_summary_post(config or {}, request)

    def test_draft_save_and_clear(self):
        out = self.post({"action": "draft"})
        self.assertTrue(out["ok"])
        self.assertIn("alpha", out["template"])
        self.assertEqual(out["ai"]["status"], "not_asked")
        saved = self.post({"action": "save", "text": out["template"], "origin": "template"})
        self.assertEqual((saved["ok"], saved["summary"]["origin"]), (True, "template"))
        self.assertEqual(self.post({"action": "draft"})["summary"]["text"], out["template"], "a pending text is shown with the draft")
        self.assertTrue(self.post({"action": "clear"})["ok"])
        self.assertIsNone(self.post({"action": "draft"})["summary"])

    def test_empty_text_and_unknown_actions_are_refused(self):
        self.assertEqual(self.post({"action": "save", "text": "  "})["status"], "empty")
        self.assertEqual(self.post({"action": "publish"})["status"], "action")
        self.assertEqual(self.post({})["status"], "action")

    def test_the_ai_draft_is_asked_only_with_the_switch_and_through_explain(self):
        with mock.patch.object(sentinel_ai, "explain", return_value={"ok": True, "text": "Calm week.", "provider": "ollama", "model": "m"}) as explain:
            off = self.post({"action": "draft_ai"})
            self.assertEqual((off["ai"]["status"], explain.call_count), ("off", 0))
            on = self.post({"action": "draft_ai"}, ON)
            self.assertEqual((on["ai"]["status"], on["ai"]["text"], explain.call_count), ("ok", "Calm week.", 1))
            self.assertEqual(explain.call_args[0][0], "report", "the same way every question takes")


class ThePageAndTheSetting(unittest.TestCase):
    def test_the_route_is_for_this_computer_and_audited(self):
        from github_actions_monitor.security import audited_posts
        self.assertIn("/api/report-files/summary", am.THIS_COMPUTER_POST)
        self.assertIn("/api/report-files/summary", audited_posts.AUDITED)

    def test_the_setting_is_on_the_page_in_eight_languages_with_its_tip(self):
        key = "ai.report_summary.enabled"
        self.assertIn(key, settings_api.FIELDS)
        for lang in i18n.LANGS:
            table = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for name in (settings_api.help_key(key), "cfg.f." + key, "cfg.t." + key):
                self.assertTrue(table.get(name), (lang, name))

    def test_every_word_of_the_card_exists_in_eight_languages(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        keys = set(re.findall(r'data-i18n="(ui\.rs_sum_[a-z_]+)"', page)) | set(re.findall(r'T\("(ui\.rs_sum_[a-z_]+)"', page))
        self.assertGreaterEqual(len(keys), 9)
        for lang in i18n.LANGS:
            table = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(table.get(key), (lang, key))
        for ident in ("rs-sum-text", "rs-sum-tpl", "rs-sum-ai", "rs-sum-save", "rs-sum-clear"):
            self.assertIn(f'id="{ident}"', page)
        self.assertIn('maxlength="1200"', page)


if __name__ == "__main__":
    unittest.main()
