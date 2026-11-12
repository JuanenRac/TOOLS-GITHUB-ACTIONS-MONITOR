# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The lite edition: no sentinel, its own files and port, a short settings page, its own launchers; and the act command of the repository panel."""
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import i18n  # noqa: E402
import settings_api as sa  # noqa: E402


class LiteSwitch(unittest.TestCase):
    def test_how_lite_is_asked_for(self):
        self.assertTrue(am.lite_requested(["--lite"]))
        self.assertTrue(am.lite_requested(["--port", "9000", "--lite"]))
        self.assertFalse(am.lite_requested([]))
        with mock.patch.dict(os.environ, {"MONITOR_MODE": "LITE"}):
            self.assertTrue(am.lite_requested([]))
        with mock.patch.dict(os.environ, {"MONITOR_MODE": "full"}):
            self.assertFalse(am.lite_requested([]))

    def test_lite_has_its_own_files_and_port(self):
        saved = (am.LITE["on"], am.CONFIG_FILE, am.LOG_FILE, sa.CONFIG_FILE, sa.BACKUP_DIR)
        import etagcache
        import toolconfig
        saved_etag, saved_tool = etagcache.CACHE_FILE, toolconfig.CONFIG_FILE
        try:
            am.enable_lite()
            self.assertEqual(am.CONFIG_FILE.name, "actions_monitor_lite.json")
            self.assertEqual(am.LOG_FILE.name, "actions_monitor_log_lite.txt")
            self.assertEqual(etagcache.CACHE_FILE.name, "etag_cache_lite.json")
            self.assertEqual(sa.BACKUP_DIR.name, "config_backups_lite")
            self.assertEqual(toolconfig.CONFIG_FILE.name, "actions_monitor_lite.json")
            self.assertEqual(am.LITE_PORT, 8766)
        finally:
            am.LITE["on"], am.CONFIG_FILE, am.LOG_FILE, sa.CONFIG_FILE, sa.BACKUP_DIR = saved
            etagcache.CACHE_FILE, toolconfig.CONFIG_FILE = saved_etag, saved_tool

    def test_the_first_start_writes_a_lite_template_with_the_sentinel_off(self):
        saved = (am.LITE["on"], am.CONFIG_FILE)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                am.LITE["on"], am.CONFIG_FILE = True, Path(tmp) / "actions_monitor_lite.json"
                config = am.load_config()
                written = json.loads(am.CONFIG_FILE.read_text(encoding="utf-8"))
                self.assertEqual(written["mode"], "lite")
                self.assertEqual(written["sentinel"], {"enabled": False})
                self.assertEqual(config["mode"], "lite")
        finally:
            am.LITE["on"], am.CONFIG_FILE = saved

    def test_the_lite_core_never_starts_the_sentinel(self):
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertRegex(text, r"if not LITE\[\"on\"\]:\n\s+start_sentinel\(config\)")
        self.assertRegex(text, r"if not LITE\[\"on\"\]:\n\s+import report_history")


class LiteSettings(unittest.TestCase):
    def test_the_short_page(self):
        groups = sa.describe(HERE / "nonexistent.json", lite=True)["groups"]
        keys = {f["key"] for g in groups for f in g["fields"]}
        self.assertEqual(keys, set(sa.LITE_KEYS))
        self.assertLessEqual(len(groups), 4)        # Basic, General, Refresh and the connection with an AI tool (the same in both editions)
        self.assertNotIn("sentinel.enabled", keys)
        self.assertTrue(len(sa.describe(HERE / "nonexistent.json")["groups"]) > 5)

    def test_lite_refuses_everything_else_even_if_it_is_a_valid_setting(self):
        clean, errors = sa.validate({"refresh_seconds": 60, "sentinel.enabled": True, "notify.enabled": True}, lite=True)
        self.assertEqual(clean, {"refresh_seconds": 60})
        self.assertEqual(set(errors), {"sentinel.enabled", "notify.enabled"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text("{}", encoding="utf-8")
            old = sa.BACKUP_DIR
            sa.BACKUP_DIR = Path(tmp) / "b"
            try:
                self.assertFalse(sa.apply({"sentinel.enabled": True}, path, lite=True)["ok"])
                self.assertTrue(sa.apply({"refresh_seconds": 90}, path, lite=True)["ok"])
            finally:
                sa.BACKUP_DIR = old
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"refresh_seconds": 90})


class LiteServer(unittest.TestCase):
    def setUp(self):
        am.LITE["on"] = True
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        am.LITE["on"] = False
        self.server.shutdown()
        self.server.server_close()

    def code(self, path, method="GET"):
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=b"{}" if method == "POST" else None, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=5) as answer:
                return answer.status, answer.read()
        except urllib.error.HTTPError as error:
            return error.code, b""

    def test_the_sentinel_and_its_neighbours_do_not_exist_in_lite(self):
        for path in ("/api/sentinel", "/api/sentinel/parte.txt", "/api/analytics", "/api/live-events", "/metrics", "/api/outputs/grafana.json", "/api/ai/actions"):
            self.assertEqual(self.code(path)[0], 404, path)
        for path in ("/api/sentinel/ai", "/api/ai/test", "/api/notify/test", "/api/webhook", "/api/refresh-repos"):
            self.assertEqual(self.code(path, "POST")[0], 404, path)

    def test_the_page_the_health_and_the_data_work_and_say_they_are_lite(self):
        code, body = self.code("/api/health")
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["lite"])
        code, body = self.code("/")
        self.assertEqual(code, 200)
        self.assertIn('"lite": true', body.decode("utf-8"))
        self.assertEqual(self.code("/api/data")[0], 200)
        code, body = self.code("/api/settings")
        keys = {f["key"] for g in json.loads(body)["groups"] for f in g["fields"]}
        self.assertEqual(keys, set(sa.LITE_KEYS))


class LitePage(unittest.TestCase):
    page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")

    def test_the_page_hides_what_lite_does_not_have(self):
        for needle in ("const LITE=!!I18N.lite", ".lite #n-sent", ".lite #t-sent", ".lite #kp-sign", "if(LITE)return;", 'LITE?["now","charts","repos","hist","cfg"]'):
            self.assertIn(needle, self.page, needle)

    def test_the_lite_texts_exist_in_the_eight_languages(self):
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in ("mon.help_lite", "ui.lite_badge", "ui.act_h", "ui.act_hint"):
                self.assertIn(key, cat, f"{lang} {key}")

    def test_the_launchers(self):
        bat = (HERE / "MONITOR_LITE_GITHUB_ACTIONS.bat").read_bytes()
        self.assertIn(b"actions_monitor.py --lite", bat)
        self.assertIn(b"\r\n", bat)
        for name in ("MONITOR_LITE_GITHUB_ACTIONS.sh", "MONITOR_LITE_GITHUB_ACTIONS.command"):
            text = (HERE / name).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
        self.assertIn("--lite", (HERE / "MONITOR_LITE_GITHUB_ACTIONS.sh").read_text(encoding="utf-8"))
        import make_release
        names = {p.name for p in make_release.members()}
        self.assertTrue({"MONITOR_LITE_GITHUB_ACTIONS.bat", "MONITOR_LITE_GITHUB_ACTIONS.sh", "MONITOR_LITE_GITHUB_ACTIONS.command"} <= names)


class ActCommand(unittest.TestCase):
    page = LitePage.page

    def test_the_panel_suggests_act_and_never_runs_it(self):
        self.assertIn("act -W .github/workflows/", self.page)
        self.assertIn('data-copy="${esc(c)}"', self.page)
        self.assertRegex(self.page, r"\[A-Za-z0-9\._-\]\+\\\.ya\?ml")          # only a plain workflow file name
        self.assertNotIn("/api/act/status?since=0", self.page)
        self.assertIn("/api/act", __import__("actions_monitor").LITE_PATHS, "the lite edition has no /api/act endpoint (it answers 404)")

    def test_running_act_exists_only_as_a_confirmed_action_of_the_ai(self):
        import ai_actions
        self.assertIn("act_local", ai_actions.CLOSED_LIST)
        self.assertNotIn("act_local", ai_actions.RUNNABLE)


if __name__ == "__main__":
    unittest.main()
