# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The active notice to an external AI (ai_notify.py): off by default, a first confirmation per provider, only the redacted fields of a closed list, a cap of calls and of cost an hour,
the key by the name of an environment variable, and the AI never runs an action. The provider is simulated: nothing leaves the computer."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import ai_notify  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NOW = 1_800_000_000
ALERT = {"id": "abc", "class": "real", "state": "open", "severity": "bad", "repo": "repo-a", "workflow": "CI", "conclusion": "failure", "streak": 2,
         "cause": "step Run tests failed", "action": "re-run once", "url": "https://github.com/o/repo-a/actions/runs/9", "since": "x", "diagnosis": {"lines": ["secret line"]}, "origin": None}


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sent = []
        self.config = {"ai": {"provider": "ollama", "model": "m"}, "ai_alerts": {"enabled": True, "folder": self.tmp.name},
                       "ai_notify": {"enabled": True, "confirmed_provider": "ollama", "max_calls_per_hour": 2, "cost_per_call_cents": 5, "max_cost_per_hour_cents": 50}}

    def transport(self, cfg, system, user):
        self.sent.append((system, user))
        return "Probable cause: a test failed. Look at the step Run tests. https://evil.example/x run `rm -rf /`"

    def notify(self, config=None, alert=None, now=NOW):
        return ai_notify.notify(config or self.config, alert or ALERT, now=now, transport=self.transport)

    def test_it_is_off_by_default_and_a_broken_file_never_turns_it_on(self):
        self.assertFalse(ai_notify.settings({})["enabled"])
        self.assertFalse(ai_notify.settings({"ai_notify": {"enabled": "true"}})["enabled"])
        self.assertFalse(am.DEFAULTS["ai_notify"]["enabled"])
        self.assertEqual(self.notify({**self.config, "ai_notify": {}})["reason"], "off")
        self.assertEqual(self.sent, [])

    def test_nothing_goes_until_the_provider_is_confirmed_and_a_change_of_provider_needs_a_new_confirmation(self):
        self.config["ai_notify"]["confirmed_provider"] = ""
        self.assertEqual(self.notify()["reason"], "not_confirmed")
        self.config["ai_notify"]["confirmed_provider"] = "anthropic"      # confirmed another provider, not the one in the AI block
        self.assertEqual(self.notify()["reason"], "not_confirmed")
        self.assertEqual(self.sent, [])
        self.config["ai_notify"]["confirmed_provider"] = "ollama"
        self.assertTrue(self.notify()["sent"])

    def test_no_provider_and_a_key_that_is_not_in_the_environment(self):
        self.assertEqual(self.notify({**self.config, "ai": {"provider": "none"}})["reason"], "no_provider")
        remote = {**self.config, "ai": {"provider": "anthropic", "model": "m", "api_key_env": "MON11_NO_SUCH_KEY"}, "ai_notify": {**self.config["ai_notify"], "confirmed_provider": "anthropic"}}
        os.environ.pop("MON11_NO_SUCH_KEY", None)
        self.assertEqual(self.notify(remote)["reason"], "no_key")
        self.assertEqual(self.sent, [])

    def test_only_a_new_real_alert_is_told(self):
        self.assertEqual(self.notify(alert={**ALERT, "class": "transient"})["reason"], "not_real")
        self.assertEqual(self.notify(alert={**ALERT, "state": "resolved"})["reason"], "not_real")
        self.assertEqual(self.sent, [])

    def test_only_the_closed_list_of_redacted_fields_travels(self):
        loaded = {**ALERT, "cause": "token ghp_" + "a" * 36 + " leaked at C:\\Users\\someone\\x", "diagnosis": {"lines": ["TOP SECRET LOG"]}, "origin": {"id": "z"}, "panel": "A3"}
        self.assertTrue(self.notify(alert=loaded)["sent"])
        user = self.sent[0][1]
        body = json.loads(user.split("\n")[1])
        self.assertEqual(sorted(body), sorted(ai_notify.FIELDS))
        for forbidden in ("TOP SECRET LOG", "ghp_" + "a" * 36, "diagnosis", "origin", "panel"):
            self.assertNotIn(forbidden, user)
        self.assertIn("UNTRUSTED", self.sent[0][0])      # the data is declared untrusted
        self.assertIn("https://github.com/o/repo-a/actions/runs/9", user)

    def test_a_cap_of_calls_and_a_cap_of_cost_an_hour(self):
        self.assertTrue(self.notify(now=NOW)["sent"])
        self.assertTrue(self.notify(now=NOW + 10)["sent"])
        self.assertEqual(self.notify(now=NOW + 20)["reason"], "cap_calls")
        self.assertTrue(self.notify(now=NOW + 3700)["sent"])      # an hour later the window has moved
        self.config["ai_notify"].update(max_calls_per_hour=60, cost_per_call_cents=20, max_cost_per_hour_cents=50)
        self.assertTrue(self.notify(now=NOW + 8000)["sent"])
        self.assertTrue(self.notify(now=NOW + 8001)["sent"])
        self.assertEqual(self.notify(now=NOW + 8002)["reason"], "cap_cost")      # 3 x 20 > 50
        self.assertEqual(len(self.sent), 5)

    def test_a_call_is_counted_before_it_is_made_so_a_failing_provider_spends_the_cap(self):
        def broken(cfg, system, user):
            raise RuntimeError("HTTP 500")
        for step in range(2):
            self.assertEqual(ai_notify.notify(self.config, ALERT, now=NOW + step, transport=broken)["reason"], "error")
        self.assertEqual(ai_notify.notify(self.config, ALERT, now=NOW + 5, transport=broken)["reason"], "cap_calls")

    def test_the_answer_is_only_advice_cut_and_defused_never_an_action(self):
        result = self.notify()
        self.assertTrue(result["sent"])
        self.assertNotIn("evil.example", result["reply"])      # links are defused
        log = (Path(self.tmp.name) / ai_notify.LOG).read_text(encoding="utf-8")
        self.assertIn("Probable cause", log)
        source = Path(ai_notify.__file__).read_text(encoding="utf-8")
        self.assertEqual([line for line in source.splitlines() if line.startswith(("import ", "from ")) and "ai_actions" in line], [])      # nothing of the actions of the assistant is imported here
        with mock.patch("subprocess.run", side_effect=AssertionError("the answer must never be run")):
            self.assertTrue(self.notify(now=NOW + 5000)["sent"])

    def test_the_outgoing_command_is_one_file_without_shell_or_arguments(self):
        config = {**self.config, "ai_notify": {**self.config["ai_notify"], "confirmed_provider": "command", "command": "relative/notify.sh"}}
        self.assertEqual(ai_notify.notify(config, ALERT, now=NOW)["reason"], "bad_command")
        script = Path(self.tmp.name) / "notify.exe"
        script.write_text("x", encoding="utf-8")
        config["ai_notify"]["command"] = str(script)
        calls = []

        def runner(path, text, timeout):
            calls.append((path, json.loads(text)))
            return "noted"
        done = ai_notify.notify(config, ALERT, now=NOW, runner=runner)
        self.assertTrue(done["sent"])
        self.assertEqual(calls[0][0], str(script))
        self.assertEqual(sorted(calls[0][1]), sorted(ai_notify.FIELDS))
        source = Path(ai_notify.__file__).read_text(encoding="utf-8")
        self.assertIn("shell=False", source)
        self.assertNotIn("shell=True", source)
        config["ai_notify"]["confirmed_provider"] = "ollama"      # the provider confirmed does not confirm the command
        self.assertEqual(ai_notify.notify(config, ALERT, now=NOW + 1, runner=runner)["reason"], "not_confirmed")

    def test_the_cycle_starts_the_notice_in_its_own_thread_only_when_it_is_on(self):
        started = []
        with mock.patch("threading.Thread") as thread:
            thread.side_effect = lambda **kw: started.append(kw["name"]) or mock.Mock()
            am.notice_ai({"ai_notify": {"enabled": False}}, ALERT)
            self.assertEqual(started, [])
            am.notice_ai(self.config, ALERT)
            self.assertEqual(started, ["ai-notify"])


class Settings(unittest.TestCase):
    def test_the_outgoing_command_is_only_in_the_file_never_in_the_settings_page(self):
        self.assertNotIn("ai_notify.command", settings_api.META)


    def test_the_switches_are_local_only_and_in_eight_languages(self):
        for key in ("ai_notify.enabled", "ai_notify.confirmed_provider", "ai_notify.max_calls_per_hour", "ai_notify.cost_per_call_cents", "ai_notify.max_cost_per_hour_cents",
                    "ai_notify.timeout_seconds"):
            self.assertIn(key, settings_api.META, key)
            self.assertTrue(settings_api.META[key]["secure"], key)      # only from this computer
            for lang in LANGS:
                texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
                self.assertTrue(texts.get("cfg.f." + key), (lang, key))
                self.assertTrue(texts.get("cfg.h." + key), (lang, key))
        for lang in LANGS:
            self.assertTrue(json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")).get("ui.cfg_b_notice"), lang)


if __name__ == "__main__":
    unittest.main()
