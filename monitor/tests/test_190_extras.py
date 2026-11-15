# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Two optional extras, both off by default: the log of the failed step in the page (one press of a button, cleaned, only for watched repositories) and a read-only token of the GitHub App for the
tools of the person (`monitor_cli.py gh-token --read-only`, only with github_app.share_reads, only to the standard output)."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.integrations import github_app, steplog  # noqa: E402

TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0"
ON = {"logs": {"failed_step": {"enabled": True}}}


def runner(args, timeout=60):
    if args[0] == "api":
        return 0, json.dumps({"jobs": [{"name": "Tests", "steps": [{"name": "Run ruff", "conclusion": "failure"}]}]}), ""
    return 0, f"Tests\tRun ruff\t2026-11-14T10:00:00Z Error: F401 unused import token={TOKEN}\n", ""


class TheLogOfTheFailedStep(unittest.TestCase):
    def setUp(self):
        steplog._CACHE.clear()

    def test_it_is_off_by_default_and_reads_nothing(self):
        calls = []
        self.assertEqual(steplog.read({}, "o", "r", "5", ["r"], lambda a, t=60: calls.append(a))["error"], "off")
        self.assertEqual(calls, [])
        self.assertFalse(steplog.settings({})["enabled"])
        self.assertFalse(steplog.settings({"logs": {"failed_step": {"enabled": "yes"}}})["enabled"])

    def test_it_answers_with_the_failing_step_and_cleaned_lines(self):
        answer = steplog.read(ON, "o", "r", "123", ["r"], runner)
        self.assertTrue(answer["ok"])
        self.assertEqual(answer["step"], "Tests: Run ruff")
        text = json.dumps(answer)
        self.assertNotIn(TOKEN, text)
        self.assertIn("F401", text)

    def test_only_watched_repositories_and_plain_numbers(self):
        for repo, run in (("other", "5"), ("r", "abc"), ("r", "0"), ("../x", "5"), ("r", "9" * 20)):
            self.assertEqual(steplog.read(ON, "o", repo, run, ["r"], runner)["error"], "request", (repo, run))

    def test_a_second_press_costs_nothing(self):
        calls = []

        def counting(args, timeout=60):
            calls.append(args)
            return runner(args, timeout)
        steplog.read(ON, "o", "r", "7", ["r"], counting)
        first = len(calls)
        steplog.read(ON, "o", "r", "7", ["r"], counting)
        self.assertEqual(len(calls), first)

    def test_an_unreadable_run_is_said_and_not_cached(self):
        self.assertEqual(steplog.read(ON, "o", "r", "8", ["r"], lambda a, t=60: (1, "", "boom"))["error"], "unavailable")
        self.assertEqual(steplog.settings({"logs": {"failed_step": {"lines": 1, "max_bytes": 5}}})["lines"], 12)

    def test_the_endpoint_refuses_when_off_and_the_page_has_the_button(self):
        from test_164 import LiveServer
        with LiveServer({"session_guard": True}) as server:
            self.assertEqual(server.call("/api/run-log?repo=r&run=5")[0], 403)
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ("data-fs=", "function fsOpen", "/api/run-log?repo="):
            self.assertIn(needle, page)

    def test_only_an_administrator_may_read_it_in_the_team_mode(self):
        from github_actions_monitor.security import auth
        self.assertEqual(auth.required_role("GET", "/api/run-log"), "admin")


class TheReadOnlyToken(unittest.TestCase):
    def ctx(self, **extra):
        return {"action": "", "read_only": True, **extra}

    def test_it_needs_the_flag_the_switch_and_a_token(self):
        with mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={"github_app": {"enabled": True, "app_id": "1", "key_path": "k"}}):
            with self.assertRaises(monitor_cli.CliError) as flag:
                monitor_cli.cmd_gh_token({"action": "", "read_only": False})
            self.assertEqual(flag.exception.code, monitor_cli.EXIT_USAGE)
            with self.assertRaises(monitor_cli.CliError) as off:
                monitor_cli.cmd_gh_token(self.ctx())
            self.assertEqual(off.exception.code, monitor_cli.EXIT_AUTH)
        on = {"github_app": {"enabled": True, "app_id": "1", "key_path": "k", "share_reads": True}}
        with mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value=on), mock.patch.object(github_app, "shared_token", return_value=("", "failed")):
            with self.assertRaises(monitor_cli.CliError) as none:
                monitor_cli.cmd_gh_token(self.ctx())
            self.assertEqual(none.exception.code, monitor_cli.EXIT_DEGRADED)

    def test_the_token_goes_only_to_the_standard_output_line_and_not_into_the_payload(self):
        on = {"github_app": {"enabled": True, "app_id": "1", "key_path": "k", "share_reads": True}}
        with mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value=on), mock.patch.object(github_app, "shared_token", return_value=(TOKEN, "")):
            payload, lines, code = monitor_cli.cmd_gh_token(self.ctx())
        self.assertEqual((lines, code), ([TOKEN], 0))
        self.assertNotIn(TOKEN, json.dumps(payload))
        text = (HERE / "src" / "github_actions_monitor" / "cli" / "monitor_cli.py").read_text(encoding="utf-8")
        self.assertNotIn("write_text", text.split("def cmd_gh_token")[1].split("def cmd_live")[0])

    def test_the_settings_are_off_and_have_their_text_in_eight_languages(self):
        from github_actions_monitor.app import actions_monitor as am
        self.assertFalse(am.DEFAULTS["github_app"]["share_reads"])
        self.assertFalse(am.DEFAULTS["logs"]["failed_step"]["enabled"])
        self.assertFalse(github_app.settings({})["share_reads"])
        for key in ("github_app.share_reads", "logs.failed_step.enabled", "logs.failed_step.lines", "logs.failed_step.max_bytes"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key, (lang, key))
                self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key, (lang, key))
        self.assertTrue(settings_api.META["github_app.share_reads"]["secure"] and settings_api.META["logs.failed_step.enabled"]["secure"])
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.fs_button", "ui.fs_off", "ui.fs_none", "ui.cfg_b_failed_step", "cli.gh_token_flag", "cli.gh_token_off", "cli.gh_token_none", "cli.help_read_only"):
                self.assertTrue(catalogue.get(key), (lang, key))


if __name__ == "__main__":
    unittest.main()
