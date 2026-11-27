# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Apprise channel (off by default): the addresses come from an environment variable and go to a private temporary file that is removed, never into the arguments of the command, the command gets no key of the monitor, a missing command or a failure is a reason and never an exception, and nothing is sent until the channel and notifications are on."""
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
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import notifiers  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
URL_A = "mailto://user:secretpass@mail.example.org"
URL_B = "json://hooks.example.org/path?token=abc123"


class Done:
    def __init__(self, code=0):
        self.returncode = code


class Parsing(unittest.TestCase):
    def test_addresses_are_split_and_only_plain_ones_are_kept(self):
        got = notifiers.apprise_urls(f"{URL_A},  {URL_B}\n--config=/etc/passwd -t x ftp tgram://abc/def")
        self.assertEqual(got, [URL_A, URL_B, "tgram://abc/def"])

    def test_nothing_that_looks_like_an_option_gets_through_and_there_are_at_most_ten(self):
        self.assertEqual(notifiers.apprise_urls("--url=http://x -b -t"), [])
        self.assertEqual(len(notifiers.apprise_urls(" ".join(f"json://h{i}.example.org" for i in range(40)))), 10)
        self.assertEqual(notifiers.apprise_urls(None), [])


class Channel(unittest.TestCase):
    CFG = {"enabled": True, "urls_env": "T193_APPRISE"}

    def test_it_is_off_by_default_and_in_the_list_of_channels(self):
        self.assertIn("apprise", notifiers.CHANNELS)
        self.assertEqual(notifiers.DEFAULTS["channels"]["apprise"], {"enabled": False, "urls_env": ""})
        self.assertEqual(notifiers.check_channel("apprise", {"enabled": False, "urls_env": "X"}), "off")

    def test_the_reasons(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("T193_APPRISE", None)
            self.assertEqual(notifiers.check_channel("apprise", self.CFG), "no_secret")
        with mock.patch.dict(os.environ, {"T193_APPRISE": URL_A}):
            with mock.patch.object(notifiers.shutil, "which", return_value=None):
                self.assertEqual(notifiers.check_channel("apprise", self.CFG), "not_installed")
            with mock.patch.object(notifiers.shutil, "which", return_value="/usr/bin/apprise"):
                self.assertIsNone(notifiers.check_channel("apprise", self.CFG))

    def test_the_addresses_go_in_a_private_file_that_is_removed_and_not_in_the_arguments(self):
        seen = {}

        def fake(args, **kw):
            seen["args"], seen["env"] = list(args), dict(kw.get("env") or {})
            named = os.path.realpath(args[args.index("-c") + 1])
            if not named.startswith(os.path.join(os.path.realpath(tempfile.gettempdir()), "")):
                raise AssertionError("the file of the addresses is not in the temporary folder")
            config = Path(named)
            seen["file"] = config.read_text(encoding="utf-8")
            seen["path"] = config
            if os.name != "nt":
                seen["mode"] = config.stat().st_mode & 0o777
            return Done(0)
        with mock.patch.dict(os.environ, {"T193_APPRISE": f"{URL_A} {URL_B}", "MONITOR_SUPERVISOR_KEY": "k", "MONITOR_ACCESS_TOKEN": "t", "GH_TOKEN": "g", "PATH": os.environ.get("PATH", "")}):
            result = notifiers.apprise_send(self.CFG, "hello", {"kind": "red_new"}, run=fake)
        self.assertEqual(result, {"channel": "apprise", "ok": True, "reason": ""})
        self.assertIn(URL_A, seen["file"])
        self.assertTrue(seen["file"].startswith("urls:"))
        self.assertFalse(any(URL_A in a or "secretpass" in a or "abc123" in a for a in seen["args"]))
        self.assertFalse(seen["path"].exists())
        for name in ("MONITOR_SUPERVISOR_KEY", "MONITOR_ACCESS_TOKEN", "GH_TOKEN", "T193_APPRISE"):
            self.assertNotIn(name, seen["env"])
        if "mode" in seen:
            self.assertEqual(seen["mode"], 0o600)

    def test_a_failure_a_timeout_and_a_missing_command_are_reasons_not_exceptions(self):
        with mock.patch.dict(os.environ, {"T193_APPRISE": URL_A}):
            self.assertEqual(notifiers.apprise_send(self.CFG, "x", {}, run=lambda *a, **k: Done(2))["reason"], "failed")

            def boom(*a, **k):
                raise FileNotFoundError("apprise")
            self.assertFalse(notifiers.apprise_send(self.CFG, "x", {}, run=boom)["ok"])
            import subprocess

            def slow(*a, **k):
                raise subprocess.TimeoutExpired("apprise", 1)
            self.assertEqual(notifiers.apprise_send(self.CFG, "x", {}, run=slow)["reason"], "failed")
        with mock.patch.dict(os.environ, {"T193_APPRISE": "not an address"}):
            self.assertEqual(notifiers.apprise_send(self.CFG, "x", {}, run=lambda *a, **k: Done(0))["reason"], "bad_value")

    def test_nothing_is_sent_until_notifications_and_the_channel_are_on(self):
        calls = []
        config = {"notify": {"enabled": True, "events": ["red_new"], "channels": {"apprise": {"enabled": True, "urls_env": "T193_APPRISE"}}}}
        with mock.patch.dict(os.environ, {"T193_APPRISE": URL_A}), mock.patch.object(notifiers.shutil, "which", return_value="/x/apprise"), mock.patch.object(notifiers.subprocess, "run", side_effect=lambda *a, **k: calls.append(a) or Done(0)):
            self.assertEqual(notifiers.notify({}, {"kind": "red_new", "text": "t"}), [])
            off = json.loads(json.dumps(config))
            off["notify"]["channels"]["apprise"]["enabled"] = False
            self.assertEqual(notifiers.notify(off, {"kind": "red_new", "text": "t"}), [])
            self.assertEqual(calls, [])
            results = notifiers.notify(config, {"kind": "red_new", "text": "t"})
        self.assertEqual([(r["channel"], r["ok"]) for r in results], [("apprise", True)])
        self.assertEqual(len(calls), 1)


class Settings(unittest.TestCase):
    def test_the_page_the_example_and_the_notifier_agree(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["notify"]["channels"]["apprise"], notifiers.DEFAULTS["channels"]["apprise"])
        for key in ("notify.channels.apprise.enabled", "notify.channels.apprise.urls_env"):
            self.assertIn(key, settings_api.FIELDS)
        self.assertTrue(settings_api.META["notify.channels.apprise.enabled"]["secure"])
        self.assertTrue(settings_api.check_value("notify.channels.apprise.urls_env", "MY_APPRISE_URLS")[0])
        self.assertFalse(settings_api.check_value("notify.channels.apprise.urls_env", "https://x.example/token")[0])

    def test_the_texts_are_in_the_eight_languages(self):
        for lang in LANGS:
            keys = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(keys.get("ui.cfg_b_ch_apprise") and keys.get("cfg.h.p.apprise_env"), lang)


if __name__ == "__main__":
    unittest.main()
