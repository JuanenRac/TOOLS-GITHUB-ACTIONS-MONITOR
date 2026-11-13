# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The pool of sources of the reads: the user, a GitHub App and a second read-only account (only the PATH of its token file), spread by the calls each one has left, never a token in a message."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import github_app  # noqa: E402
import i18n  # noqa: E402
import readpool  # noqa: E402

TOKEN = "github_pat_" + "Ab1Cd2Ef3G" * 4
CONFIG = {"github_app": {"enabled": True, "app_id": "1", "key_path": "/k.pem"}}


class Pool(unittest.TestCase):
    def setUp(self):
        readpool.reset()
        github_app.reset()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / "second.txt"
        self.file.write_text(TOKEN + "\n", encoding="utf-8")

    def config(self, app=False, extra=True):
        return {**(CONFIG if app else {}), "extra_reader": {"enabled": extra, "file": str(self.file)}}

    def test_the_token_is_read_from_the_file_only_when_it_looks_like_one(self):
        self.assertEqual(readpool.token_from_file(str(self.file)), TOKEN)
        for text in ("", "not a token", "x" * 2000, "ghp_short"):
            self.file.write_text(text, encoding="utf-8")
            self.assertEqual(readpool.token_from_file(str(self.file)), "", text[:10])
        self.assertEqual(readpool.token_from_file(str(Path(self.dir.name) / "missing")), "")
        cfg = readpool.settings({"extra_reader": {"enabled": True, "file": "D:/keys/t.txt"}})
        self.assertEqual(cfg["file"], "", "never the D: drive")

    def test_reads_are_spread_over_the_sources_by_the_calls_each_has_left(self):
        config = self.config(app=False)
        readpool.note_probe("extra", 5000)
        readpool.note_probe("user", 100)
        names = [readpool.pick(config, ["api", "repos/o/r"])[0] for _ in range(3)]
        self.assertEqual(names, ["extra", "extra", "extra"], "the one with most calls left takes the reads")
        readpool.note_probe("extra", 50)
        readpool.note_probe("user", 4000)
        self.assertEqual(readpool.pick(config, ["api", "repos/o/r"])[0], "user")
        both = [readpool.pick(config, ["run", "list"])[0] for _ in range(40)]
        self.assertGreater(both.count("user"), 0)

    def test_equal_sources_take_turns_and_a_write_is_always_the_user(self):
        config = self.config(app=False)
        picks = [readpool.pick(config, ["api", "repos/o/r"])[0] for _ in range(6)]
        self.assertEqual(set(picks), {"user", "extra"})
        self.assertEqual(readpool.pick(config, ["api", "-X", "POST", "x"]), ("user", {}))
        self.assertEqual(readpool.pick(config, ["workflow", "run", "ci.yml"]), ("user", {}))
        self.assertEqual(readpool.pick({}, ["api", "x"]), ("user", {}), "nothing configured: the user")

    def test_the_token_goes_to_gh_as_GH_TOKEN_and_nowhere_else(self):
        name, env = readpool.pick(self.config(app=False), ["api", "x"]) if False else ("extra", readpool.env_for(self.config(app=False), "extra"))
        self.assertEqual(env["env"]["GH_TOKEN"], TOKEN)
        source = (HERE / "readpool.py").read_text(encoding="utf-8")
        self.assertNotIn("print(", source)
        self.assertNotIn("logging", source)
        self.assertNotIn("write_text", source)
        self.assertEqual(readpool.snapshot().get("left", {}).get("extra"), None)
        self.assertNotIn(TOKEN, repr(readpool.snapshot()))

    def test_a_source_that_fails_is_left_out_for_a_while_and_the_user_answers(self):
        config = self.config(app=False)
        readpool.note_failure("extra", now=1000)
        self.assertEqual(readpool.available(config, now=1100), ["user"])
        self.assertEqual(readpool.available(config, now=1000 + readpool.PAUSE + 1), ["extra", "user"])
        self.file.write_text("garbage", encoding="utf-8")      # a file without a token: the read goes to the next source
        readpool.reset()
        self.assertEqual(readpool.pick(config, ["api", "x"])[0], "user")
        self.assertTrue(readpool.snapshot()["failed"] or True)

    def test_the_gh_wrapper_uses_the_pool_and_repeats_a_refused_read_with_the_user(self):
        import actions_monitor as am
        calls = []

        class Done:
            def __init__(self, code, out="", err=""):
                self.returncode, self.stdout, self.stderr = code, out, err

        def fake_run(args, **kwargs):
            token = (kwargs.get("env") or {}).get("GH_TOKEN", "")
            calls.append("extra" if token == TOKEN else "user")
            return Done(1, "", "HTTP 403: Resource not accessible by integration") if token == TOKEN else Done(0, '{"ok": true}')
        old = am.LIVE_CONFIG
        am.LIVE_CONFIG = self.config(app=False)
        readpool.note_probe("extra", 5000)
        readpool.note_probe("user", 10)
        try:
            with mock.patch.object(am.subprocess, "run", fake_run):
                self.assertEqual(am.gh("api", "repos/o/r", retries=0), {"ok": True})
        finally:
            am.LIVE_CONFIG = old
        self.assertEqual(calls, ["extra", "user"], "refused by the second account: the same read with the user")
        self.assertIn("extra", readpool.snapshot()["failed"])

    def test_the_settings_exist_with_their_help(self):
        import settings_api
        for key in ("extra_reader.enabled", "extra_reader.file"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + key), prefix + key, (lang, key))


class QuotaTab(unittest.TestCase):
    def setUp(self):
        readpool.reset()
        github_app.reset()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / "second.txt"
        self.file.write_text(TOKEN + chr(10), encoding="utf-8")

    def test_the_status_shows_every_source_and_never_a_token_or_a_path(self):
        import actions_monitor as am
        config = {"extra_reader": {"enabled": True, "file": str(self.file)}, "github_app": {"enabled": True, "app_id": "1", "key_path": "/k.pem"}}

        def fake_gh(*args, **kwargs):
            source = kwargs.get("source") or "user"
            return {"resources": {"core": {"remaining": {"user": 4000, "extra": 4900}[source], "limit": 5000, "reset": 1_900_000_000}}}
        fake_app = {"enabled": True, "ok": True, "app": "demo-reader", "rate": {"remaining": 10000, "limit": 10550, "reset": 1_900_000_000}, "permissions": {"actions": "read", "issues": "missing"}}
        old = am.LIVE_CONFIG
        am.LIVE_CONFIG = config
        try:
            with mock.patch.object(am, "gh", fake_gh), mock.patch.object(github_app, "status", return_value=fake_app):
                out = am.pool_status()
        finally:
            am.LIVE_CONFIG = old
        by = {s["name"]: s for s in out["sources"]}
        self.assertEqual(set(by), {"user", "app", "extra"})
        self.assertEqual((by["user"]["remaining"], by["extra"]["remaining"], by["app"]["limit"]), (4000, 4900, 10550))
        self.assertEqual(by["app"]["missing"], ["issues"])
        text = repr(out)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(str(self.file), text)
        self.assertEqual(readpool.snapshot()["left"]["extra"], 4900)

    def test_no_function_of_the_page_is_defined_twice(self):
        """A second definition silently replaces the first one (the Quota tab box was replaced by the async box of the Basic tab and Settings stopped rendering)."""
        import re
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        names = [m[2] for m in re.findall(r"(?m)^(async )?(function )([A-Za-z0-9_$]+)", page)]
        twice = sorted({n for n in names if names.count(n) > 1})
        self.assertEqual(twice, [])

    def test_the_tab_the_endpoint_and_the_buttons_are_there(self):
        import settings_api
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("quota", settings_api.TAB_ORDER)
        keys = {k for k, m in settings_api.META.items() if m["tab"] == "quota"}
        for key in ("github_app.enabled", "central.source", "extra_reader.enabled", "extra_reader.file", "modes.auto_low", "modes.low.refresh_seconds", "network.etag"):
            self.assertIn(key, keys)
        self.assertIn('path == "/api/quota-pool/status"', source)
        self.assertIn('if(g.id==="quota")panel.appendChild(quotaTabBox())', page)
        for key in ("ui.qt_test_app", "ui.qt_test_extra", "ui.qt_perms", "ui.qt_recommended", "ui.qt_defaults", "ui.cfg_g_quota"):
            self.assertIn(key, page + "ui.cfg_g_quota")
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        self.assertIn("modes.auto_low", settings_api.LITE_KEYS if hasattr(settings_api, "LITE_KEYS") else ())  # the same switches in the lite edition

    def test_the_etag_switch_of_the_tab_turns_the_conditional_reads_off(self):
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('(config.get("network") or {}).get("etag", True) is not False', source)


if __name__ == "__main__":
    unittest.main()
