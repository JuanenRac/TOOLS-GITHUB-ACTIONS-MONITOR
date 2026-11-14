# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The book of failures and the library of lessons: every failure that opens is filed under a category with rules that can be edited, the counts and the trend come out of the book, the files an AI
reads are written from it, a lesson is written only with the switch, an administrator and a confirmation, and nothing leaves the computer."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.integrations import ai_alerts, ai_index, lessons, mcp_server  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402
from github_actions_monitor.util import paths  # noqa: E402

NOW = 1_800_000_000
DAY = 86400


def alert(repo="demo", workflow="ci.yml", step="Tests: Run tests", lines=("AssertionError: 1 != 2",), run=100, conclusion="failure"):
    return {"repo": repo, "workflow": workflow, "conclusion": conclusion, "cause": "the workflow failed", "url": f"https://github.com/o/{repo}/actions/runs/{run}",
            "diagnosis": {"run": run, "step": step, "lines": list(lines)}}


class Folders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"MONITOR_DATA_DIR": str(base / "data"), "MONITOR_CONFIG_DIR": str(base / "config"), "MONITOR_AI_DIR": str(base / "ai")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.config = {"ai_alerts": {"enabled": True}}


class TheClassifier(Folders, unittest.TestCase):
    CASES = (("API rate limit exceeded", "quota"), ("connection reset by peer", "flaky_network"), ("Invalid workflow file", "workflow_config"), ("Resource not accessible by integration", "permissions"),
             ("Bad credentials", "secret_config"), ("generated file is out of date", "derived_files"), ("ModuleNotFoundError: No module named x", "dependencies"), ("mypy found 3 errors", "types"),
             ("ruff check failed", "linter"), ("AssertionError: 2 != 3", "test"), ("something nobody has seen", "other"))

    def test_every_built_in_category_is_found(self):
        for text, category in self.CASES:
            self.assertEqual(lessons.classify(text)[0], category, text)

    def test_a_run_that_did_not_start_or_timed_out_is_not_the_code(self):
        self.assertEqual(lessons.classify("", conclusion="startup_failure")[0], "flaky_network")
        self.assertFalse(lessons.classify("", conclusion="timed_out")[1])

    def test_the_rules_can_be_edited_in_a_file_and_a_bad_pattern_is_skipped(self):
        paths.folder("config").mkdir(parents=True, exist_ok=True)
        (paths.folder("config") / lessons.RULES).write_text(json.dumps({"rules": [
            {"category": "mine", "patterns": ["cosmic ray"], "avoidable": False}, {"category": "broken", "patterns": ["("]}, {"category": "Bad Name", "patterns": ["x"]},
            {"category": "long", "patterns": ["a" * 500]}]}), encoding="utf-8")
        rules = lessons.load_rules()
        self.assertEqual([r["category"] for r in rules], ["mine"])
        self.assertEqual(lessons.classify("hit by a cosmic ray", rules), ("mine", False, "mine"))
        self.assertEqual(lessons.classify("AssertionError", rules)[0], "other", "the file replaces the built-in rules")

    def test_a_damaged_rules_file_falls_back_to_the_built_in_rules(self):
        paths.folder("config").mkdir(parents=True, exist_ok=True)
        (paths.folder("config") / lessons.RULES).write_text("{not json", encoding="utf-8")
        self.assertEqual(lessons.classify("ruff check failed")[0], "linter")

    def test_a_huge_log_is_cut_before_the_patterns_read_it(self):
        self.assertEqual(lessons.classify("x" * 100000 + " AssertionError")[0], "other")


class TheBook(Folders, unittest.TestCase):
    def test_a_failure_becomes_one_line_of_the_closed_schema(self):
        written = lessons.record(self.config, [alert()], {("demo", "ci.yml"): "abcdef0123456789"}, now=NOW)
        self.assertEqual(len(written), 1)
        line = json.loads(lessons.book_path().read_text(encoding="utf-8"))
        self.assertEqual(set(line), set(lessons.FIELDS))
        self.assertEqual((line["schema"], line["repo"], line["job"], line["step"], line["category"], line["run_id"], line["sha"], line["source"]),
                         (1, "demo", "Tests", "Run tests", "test", 100, "abcdef0123456789", "feed"))
        self.assertEqual((line["actor_kind"], line["event"], line["branch"]), ("unknown", "unknown", "default"))

    def test_secrets_never_reach_the_book(self):
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0"
        lessons.record(self.config, [alert(lines=(f"Error: failed with token={token}", "mail me at someone@example.com from 10.1.2.3"))], now=NOW)
        text = lessons.book_path().read_text(encoding="utf-8")
        for secret in (token, "someone@example.com", "10.1.2.3"):
            self.assertNotIn(secret, text)

    def test_the_same_run_is_written_once_and_a_panel_is_not_a_failure(self):
        lessons.record(self.config, [alert(), alert()], now=NOW)
        lessons.record(self.config, [alert(), dict(alert(workflow="p"), conclusion="panel")], now=NOW + 5)
        self.assertEqual(len(lessons.read_book()), 1)

    def test_it_is_off_when_the_switch_is_off(self):
        self.assertEqual(lessons.record({"lessons": {"enabled": False}}, [alert()], now=NOW), [])
        self.assertFalse(lessons.book_path().exists())

    def test_old_lines_and_too_many_lines_are_dropped(self):
        for index in range(30):
            lessons.record(self.config, [alert(workflow=f"w{index}.yml", run=index + 1)], now=NOW - index * 20 * DAY)
        cfg = lessons.settings({"lessons": {"retention_days": 100, "max_entries": 100}})
        lessons._prune(lessons.book_path(), cfg, NOW)
        kept = lessons.read_book()
        self.assertTrue(kept and all(e["ts"] >= NOW - 100 * DAY for e in kept))
        lessons._prune(lessons.book_path(), dict(cfg, max_entries=100, retention_days=3650), NOW)
        self.assertLessEqual(len(lessons.read_book()), 100)

    def test_a_damaged_line_is_skipped_and_a_foreign_field_is_cut(self):
        lessons.book_path().parent.mkdir(parents=True, exist_ok=True)
        good = {"ts": NOW, "repo": "demo", "workflow": "ci", "category": "test", "extra": "x", "avoidable": True, "actor_kind": "robot", "source": "elsewhere"}
        lessons.book_path().write_text("nonsense\n" + json.dumps(good) + "\n" + json.dumps({"repo": "../bad", "ts": 1}) + "\n", encoding="utf-8")
        rows = lessons.read_book()
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]), set(lessons.FIELDS))
        self.assertEqual((rows[0]["actor_kind"], rows[0]["source"]), ("unknown", "import"))

    def test_a_book_of_the_same_schema_can_be_imported_once(self):
        line = json.dumps({"schema": 1, "ts": NOW - 5, "repo": "other", "workflow": "ci", "category": "linter", "root_cause": "ruff", "avoidable": True, "actor_kind": "ai"})
        self.assertEqual(lessons.import_book(self.config, line + "\nbroken\n", now=NOW), 1)
        self.assertEqual(lessons.import_book(self.config, line, now=NOW), 0)
        self.assertEqual(lessons.read_book()[0]["source"], "import")
        self.assertEqual(lessons.read_book()[0]["actor_kind"], "ai")

    def test_the_failures_can_be_filtered(self):
        lessons.record(self.config, [alert(repo="a", run=1), alert(repo="b", run=2, step="Lint: ruff", lines=("ruff failed",))], now=NOW)
        self.assertEqual({e["repo"] for e in lessons.failures(self.config)}, {"a", "b"})
        self.assertEqual([e["repo"] for e in lessons.failures(self.config, repo="b")], ["b"])
        self.assertEqual([e["category"] for e in lessons.failures(self.config, category="linter")], ["linter"])
        self.assertEqual(len(lessons.failures(self.config, limit=1)), 1)


class TheAnalysis(Folders, unittest.TestCase):
    def fill(self):
        for index in range(3):
            lessons.record(self.config, [alert(workflow=f"t{index}", run=10 + index)], now=NOW - index * 3600)
        lessons.record(self.config, [alert(repo="lint", workflow="l", step="Lint: ruff", lines=("ruff failed",), run=50)], now=NOW - 2 * DAY)
        for index in range(2):
            lessons.record(self.config, [alert(repo="old", workflow=f"o{index}", run=60 + index, lines=("ruff failed",), step="Lint: ruff")], now=NOW - 10 * DAY - index)

    def test_counts_trend_and_repetition(self):
        self.fill()
        rows = {r["category"]: r for r in lessons.analyze(self.config, NOW)}
        self.assertEqual((rows["test"]["n24"], rows["test"]["n7"], rows["test"]["trend"], rows["test"]["recurring"]), (3, 3, "new", True))
        self.assertEqual((rows["linter"]["n24"], rows["linter"]["n7"], rows["linter"]["prev7"], rows["linter"]["trend"], rows["linter"]["recurring"]), (0, 1, 2, "down", False))
        self.assertEqual(rows["test"]["repos"], ["demo"])
        self.assertTrue(rows["test"]["propose_guard"] and not rows["linter"]["propose_guard"])
        self.assertEqual(lessons.analyze(self.config, NOW)[0]["category"], "test", "the repeated ones come first")

    def test_rising_and_steady(self):
        for index in range(3):
            lessons.record(self.config, [alert(workflow=f"u{index}", run=1 + index, lines=("ruff failed",), step="Lint")], now=NOW - index)
        lessons.record(self.config, [alert(workflow="v", run=9, lines=("ruff failed",), step="Lint")], now=NOW - 9 * DAY)
        self.assertEqual({r["category"]: r["trend"] for r in lessons.analyze(self.config, NOW)}["linter"], "up")
        lessons.record(self.config, [alert(workflow="w", run=19, lines=("ruff failed",), step="Lint")], now=NOW - 9 * DAY)
        lessons.record(self.config, [alert(workflow="x", run=29, lines=("ruff failed",), step="Lint")], now=NOW - 9 * DAY)
        self.assertEqual({r["category"]: r["trend"] for r in lessons.analyze(self.config, NOW)}["linter"], "flat")

    def test_the_threshold_of_repetition_is_a_setting(self):
        lessons.record(self.config, [alert()], now=NOW)
        self.assertFalse(lessons.analyze(self.config, NOW)[0]["recurring"])
        self.assertTrue(lessons.analyze({"lessons": {"recurring_from": 2}, **self.config}, NOW)[0]["n7"] == 1)
        self.assertEqual(lessons.settings({"lessons": {"recurring_from": 1}})["recurring_from"], 2, "a value out of range gives the default")


class TheLibrary(Folders, unittest.TestCase):
    def test_the_built_in_lessons_come_from_the_catalogue_in_each_language(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                rows = lessons.load_library()
                for category in lessons.CATEGORIES:
                    self.assertTrue(rows[category]["what"] and rows[category]["do"] and rows[category]["guard"], (lang, category))
                    self.assertNotIn("lesson.", rows[category]["do"])
        with i18n.use_language("es"):
            self.assertIn("Ejecute", lessons.load_library()["linter"]["do"])

    def test_a_lesson_of_the_file_replaces_the_built_in_one_and_marks_the_failure(self):
        paths.folder("config").mkdir(parents=True, exist_ok=True)
        (paths.folder("config") / lessons.LIBRARY).write_text(json.dumps({"lessons": [{"id": "mine-1", "category": "test", "what": "Mine", "do": "Do mine", "guard": "G"}, {"id": "bad id", "category": "test"}]}), encoding="utf-8")
        library = lessons.load_library()
        self.assertEqual((library["test"]["id"], library["test"]["do"], library["test"]["source"]), ("mine-1", "Do mine", "library"))
        self.assertEqual(library["linter"]["source"], "built-in")
        written = lessons.record(self.config, [alert()], now=NOW)
        self.assertEqual((written[0]["lesson_ref"], written[0]["had_lesson"]), ("mine-1", True))

    def test_writing_needs_the_switch_an_administrator_and_a_confirmation(self):
        request = {"category": "test", "what": "A test broke", "do": "Run it first", "guard": "pre-push"}
        self.assertEqual(lessons.register(self.config, request, True, True)["status"], "write_off")
        on = {"lessons": {"allow_write": True}}
        self.assertEqual(lessons.register(on, request, True, False)["status"], "admin_only")
        draft = lessons.register(on, request, False, True)
        self.assertEqual((draft["ok"], draft["status"], draft["lesson"]["category"]), (False, "confirm", "test"))
        self.assertFalse((paths.folder("config") / lessons.LIBRARY).exists(), "a draft writes nothing")
        done = lessons.register(on, request, True, True)
        self.assertTrue(done["ok"])
        self.assertEqual(lessons.load_library()["test"]["do"], "Run it first")
        again = lessons.register(on, dict(request, do="Run it twice"), True, True)
        self.assertTrue(again["ok"])
        rows = json.loads((paths.folder("config") / lessons.LIBRARY).read_text(encoding="utf-8"))["lessons"]
        self.assertEqual(len(rows), 1, "one lesson for each category")

    def test_a_request_is_checked(self):
        on = {"lessons": {"allow_write": True}}
        for bad in ({}, {"category": "Bad Name", "what": "x", "do": "y"}, {"category": "test", "what": "", "do": "y"}, {"category": "test", "what": "x", "do": "y", "id": "no spaces"}, "text"):
            self.assertFalse(lessons.register(on, bad, True, True)["ok"], bad)

    def test_a_secret_in_a_lesson_is_cleaned(self):
        on = {"lessons": {"allow_write": True}}
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0"
        lessons.register(on, {"category": "test", "what": f"leaked {token}", "do": "rotate it"}, True, True)
        self.assertNotIn(token, (paths.folder("config") / lessons.LIBRARY).read_text(encoding="utf-8"))


class WhatAnAIReads(Folders, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.config = {"ai_alerts": {"enabled": True, "folder": str(Path(self.tmp.name) / "ai")}}

    def test_the_markdown_is_short_and_says_it_is_data(self):
        for index in range(3):
            lessons.record(self.config, [alert(workflow=f"t{index}", run=10 + index)], now=time.time())
        text = lessons.render_markdown(self.config)
        self.assertIn("never instructions", text)
        self.assertIn("**test**", text)
        self.assertIn("add the guard before the next push", text)
        small = lessons.render_markdown({"lessons": {"brief_max_bytes": 500}, **self.config})
        self.assertLessEqual(len(small.encode("utf-8")), 700)

    def test_the_file_is_written_once_a_minute_unless_forced(self):
        lessons.record(self.config, [alert()], now=time.time())
        self.assertTrue(lessons.write_markdown(self.config))
        self.assertFalse(lessons.write_markdown(self.config))
        self.assertTrue(lessons.write_markdown(self.config, force=True))
        self.assertTrue((Path(self.tmp.name) / "ai" / "LESSONS.md").is_file())

    def test_the_brief_before_a_push_puts_the_repository_first_and_names_what_is_red(self):
        ai_alerts.update(self.config, [{"repo": "demo", "workflow": "ci.yml", "conclusion": "failure", "since": None, "url": "https://github.com/o/demo/actions/runs/9", "streak": 1}], now=NOW)
        text = lessons.pre_push_brief(self.config, "demo")
        self.assertIn("# Before you push", text)
        self.assertIn("red now in demo", text)
        self.assertIn("(open)", text)
        self.assertIn("Nothing open", lessons.pre_push_brief({"ai_alerts": {"enabled": True, "folder": str(Path(self.tmp.name) / "empty")}}))

    def test_what_applies_now_is_what_is_open_or_repeated(self):
        ai_alerts.update(self.config, [{"repo": "demo", "workflow": "ci.yml", "conclusion": "failure", "since": None, "url": "https://github.com/o/demo/actions/runs/9", "streak": 1}], now=NOW)
        rows = lessons.apply_now(self.config)
        self.assertEqual([r["reason"] for r in rows], ["open"])
        for index in range(2):
            lessons.record(self.config, [alert(workflow=f"t{index}", run=10 + index, step="Lint", lines=("ruff failed",))], now=time.time())
        self.assertIn("recurring", {r["reason"] for r in lessons.apply_now(self.config)})

    def test_the_document_has_the_analysis_the_library_and_the_switches(self):
        doc = lessons.document(self.config)
        self.assertEqual((doc["schema"], doc["enabled"], doc["allow_write"]), (1, True, False))
        self.assertEqual({r["category"] for r in doc["library"]}, set(lessons.CATEGORIES))

    def test_the_failures_endpoint_and_the_lessons_endpoint_answer(self):
        from test_164 import LiveServer
        lessons.record(self.config, [alert()], now=time.time())
        with LiveServer({"session_guard": True, **self.config}) as server:
            status, body = server.call("/api/ai/lessons")
            self.assertEqual(status, 200)
            self.assertEqual(body["schema"], 1)
            self.assertIn("test", [c["category"] for c in body["categories"]])
            self.assertIn("demo", [f["repo"] for f in server.call("/api/ai/failures?limit=50")[1]["failures"]])
            self.assertEqual(server.call("/api/ai/failures?repo=nothing")[1]["failures"], [])
            text = server.call("/api/ai/lessons?fmt=brief&repo=demo")[1]
            self.assertIn("Before you push", text if isinstance(text, str) else json.dumps(text))
            self.assertEqual(server.call("/api/ai/lessons?fmt=brief&as=json")[1]["fmt"], "brief")
            self.assertEqual(server.call("/api/ai/lessons", {"lesson": {"category": "test", "what": "x", "do": "y"}, "confirm": True})[0], 403, "writing needs the one-use token")

    def test_the_state_document_carries_the_lessons_that_apply(self):
        from github_actions_monitor.app import actions_monitor as am
        ai_alerts.update(self.config, [{"repo": "demo", "workflow": "ci.yml", "conclusion": "failure", "since": None, "url": "https://github.com/o/demo/actions/runs/9", "streak": 1}], now=NOW)
        with mock.patch.object(am.toolconfig, "raw_config", return_value=self.config):
            doc = am.ai_state(data={"repos": [], "runs": []}, panels=[])
        self.assertIsInstance(doc["lessons"], list)
        self.assertEqual(doc["lessons"][0]["reason"], "open")

    def test_the_places_of_the_new_files(self):
        self.assertEqual(paths.kind_of("failures.jsonl"), "data")
        self.assertEqual(paths.kind_of("LESSONS.md"), "ai")
        self.assertEqual(paths.kind_of("lessons.json"), "config")
        self.assertEqual(paths.kind_of("lessons_rules.json"), "config")
        names = {row[0] for row in ai_index.FILES}
        self.assertIn("LESSONS.md", names)
        self.assertIn("/api/ai/lessons", {row[1] for row in ai_index.ENDPOINTS})


class Providers(Folders, unittest.TestCase):
    def test_the_file_provider_answers_for_a_text_and_for_the_book(self):
        provider = lessons.provider(self.config)
        self.assertEqual(provider.name, "file")
        self.assertEqual(provider.applicable(text="ruff check failed")[0]["category"], "linter")
        self.assertEqual(provider.applicable(text="nobody knows"), [])
        lessons.record(self.config, [alert(workflow="a", run=1), alert(workflow="b", run=2)], now=time.time())
        self.assertEqual([r["category"] for r in provider.recurrences()], ["test"])
        self.assertEqual(provider.propose({"category": "test", "what": "x", "do": "y"})["status"], "draft")
        self.assertFalse(provider.register({"category": "test", "what": "x", "do": "y"}, True, True)["ok"], "the switch is off")

    def test_the_example_provider_and_a_provider_of_your_own(self):
        self.assertEqual(lessons.provider(self.config, "example").applicable()[0]["category"], "test")
        self.assertEqual(lessons.LessonProvider().applicable(), [])
        lessons.register_provider("wiki", lambda config: lessons.ExampleProvider([{"category": "x", "do": "from the wiki"}]))
        self.addCleanup(lessons.PROVIDERS.pop, "wiki", None)
        self.assertEqual(lessons.provider(self.config, "wiki").applicable()[0]["do"], "from the wiki")
        self.assertIsInstance(lessons.provider(self.config, "unknown"), lessons.FileProvider)
        with self.assertRaises(ValueError):
            lessons.register_provider("Bad Name", lambda config: None)

    def test_the_prompt_of_the_ai_of_the_monitor_carries_the_lesson_of_the_failure(self):
        block = lessons.prompt_block("Error: ruff check failed", self.config)
        self.assertIn("Known lesson (linter)", block)
        system, _user = sentinel_ai.build_prompt("build", "log", "n1", "English", block)
        self.assertIn(block, system)
        self.assertEqual(lessons.prompt_block("nobody knows", self.config), "")
        self.assertEqual(lessons.prompt_block("ruff failed", {"lessons": {"enabled": False}}), "")
        system, _user = sentinel_ai.build_prompt("build", "log", "n1", "English")
        self.assertNotIn("Known lesson", system)


class TheTools(Folders, unittest.TestCase):
    def test_the_mcp_tools_read_and_only_write_with_the_flag_and_the_switch(self):
        lessons.record(self.config, [alert(workflow="a", run=1), alert(workflow="b", run=2)], now=time.time())
        names = {t["name"] for t in mcp_server.TOOLS}
        self.assertTrue({"lessons_apply", "lessons_recurring", "lessons_brief", "lesson_propose"} <= names)
        applied = json.loads(mcp_server.call("lessons_apply", {"text": "ruff check failed"}, self.config))
        self.assertEqual(applied[0]["category"], "linter")
        self.assertEqual(json.loads(mcp_server.call("lessons_recurring", {}, self.config))[0]["category"], "test")
        self.assertIn("Before you push", mcp_server.call("lessons_brief", {"repo": "demo"}, self.config))
        draft = json.loads(mcp_server.call("lesson_propose", {"category": "test", "what": "x", "do": "y"}, self.config))
        self.assertEqual(draft["status"], "draft")
        with self.assertRaises(ValueError):
            mcp_server.call("lesson_propose", {"category": "test", "what": "x", "do": "y", "confirm": True}, self.config)
        on = {"lessons": {"allow_write": True}, **self.config}
        self.assertEqual(json.loads(mcp_server.call("lesson_propose", {"category": "test", "what": "x", "do": "y", "confirm": True}, on, allow_lessons=True))["status"], "saved")

    def test_the_command_line_lists_briefs_and_shows_the_failures(self):
        answers = {"/api/ai/lessons": {"categories": [{"category": "test", "n24": 2, "n7": 3, "trend": "up", "lesson": {"do": "Run them"}}], "enabled": True},
                   "/api/ai/failures": {"failures": [{"category": "test", "repo": "demo", "workflow": "ci", "root_cause": "assert"}]}}

        def fake(base, path, query=None, timeout=8, token=""):
            if query and query.get("fmt") == "brief":
                return {"text": "# Before you push\nline"}
            return answers[path]

        ctx = {"base": "http://127.0.0.1:1", "timeout": 1, "token": "", "action": "", "repo": "demo"}
        with mock.patch.object(monitor_cli, "fetch", fake):
            _data, lines, code = monitor_cli.cmd_lessons(ctx)
            self.assertEqual(code, 0)
            self.assertIn("test", lines[1])
            self.assertEqual(monitor_cli.cmd_lessons(dict(ctx, action="brief"))[1][0], "# Before you push")
            self.assertIn("demo", monitor_cli.cmd_lessons(dict(ctx, action="failures"))[1][1])
            with self.assertRaises(monitor_cli.CliError):
                monitor_cli.cmd_lessons(dict(ctx, action="nonsense"))

    def test_the_settings_exist_with_their_defaults_and_their_text_in_eight_languages(self):
        from github_actions_monitor.app import actions_monitor as am, settings_api
        for key in ("lessons.enabled", "lessons.allow_write", "lessons.retention_days", "lessons.max_entries", "lessons.brief_max_bytes", "lessons.recurring_from"):
            self.assertIn(key, settings_api.FIELDS, key)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key, (lang, key))
                self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key, (lang, key))
        self.assertEqual(am.DEFAULTS["lessons"], {"enabled": True, "allow_write": False, "retention_days": 180, "max_entries": 5000, "brief_max_bytes": 3000, "recurring_from": 2})
        self.assertTrue(settings_api.META["lessons.allow_write"]["secure"], "writing lessons is a security option")

    def test_the_texts_of_the_panel_exist_in_the_eight_languages_and_the_page_has_the_panel(self):
        keys = [f"ui.les_c_{c}" for c in lessons.CATEGORIES] + [f"lesson.{c}.{f}" for c in lessons.CATEGORIES for f in ("what", "do", "guard")] + \
               ["ui.les_title", "ui.les_intro", "ui.les_empty", "ui.les_off", "ui.les_h_24", "ui.les_h_7", "ui.les_h_guard", "ui.les_repeats", "ui.les_applies", "ui.cfg_b_lessons"] + \
               [f"ui.les_t_{t}" for t in ("new", "up", "down", "flat")]
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(catalogue.get(key), (lang, key))
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="les-list"', "function renderLessons", "/api/ai/lessons", "data-i18n=\"ui.les_title\""):
            self.assertIn(needle, page, needle)

    def test_nothing_in_the_module_reaches_the_network_or_runs_a_program(self):
        text = (HERE / "src" / "github_actions_monitor" / "integrations" / "lessons.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "subprocess", "os.system", "socket", "http.client", "shell=True"):
            self.assertNotIn(forbidden, text, forbidden)


if __name__ == "__main__":
    unittest.main()
