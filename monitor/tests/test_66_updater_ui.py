# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The three faces of the updater (page in the browser, text menu, window) and its command line, on top of the same engine. The page is tested against a real server on 127.0.0.1."""
import http.client
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import monitor_updater as mu  # noqa: E402
from test_66_updater_engine import NO_MONITOR, FakeSource, build_zip, config_from_defaults, make_install, tree_hash  # noqa: E402


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="upd_ui_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        mu.set_language("en")
        self.zip = build_zip(self.tmp / "z.zip", "2.0.8")
        self.root = make_install(self.tmp / "i", "2.0.4", config_from_defaults("2.0.4"))

    def make_updater(self, local=None):
        return mu.Updater(self.root, local or FakeSource({"2.0.8": self.zip, "2.0.4": build_zip(self.tmp / "z4.zip", "2.0.4")}), backups=self.tmp / "copies", env={}, probe=NO_MONITOR)


class Page(Fixture):
    def setUp(self):
        super().setUp()
        from http.server import ThreadingHTTPServer
        self.app = mu.WebApp(self.make_updater)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), mu.make_handler(self.app))
        self.server.daemon_threads = True
        self.app.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.host = f"127.0.0.1:{self.app.port}"

    def call(self, method, path, body=None, headers=None, host=None, token=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.app.port, timeout=30)
        hdr = {"Host": host or self.host}
        if token:
            hdr["X-Updater-Token"] = self.app.token
        hdr.update(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body)
            hdr.setdefault("Content-Type", "application/json")
        conn.request(method, path, data, hdr)
        reply = conn.getresponse()
        raw = reply.read()
        conn.close()
        return reply.status, dict(reply.getheaders()), raw

    def test_the_page_needs_the_token_in_the_address(self):
        self.assertEqual(self.call("GET", "/", token=False)[0], 403)
        self.assertEqual(self.call("GET", "/?t=wrong", token=False)[0], 403)
        status, headers, raw = self.call("GET", "/?t=" + self.app.token, token=False)
        self.assertEqual(status, 200)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn(self.app.token.encode(), raw)                                    # for its own script; removed from the address bar at once
        self.assertIn(b"history.replaceState", raw)
        self.assertNotIn(b"@@", raw)

    def test_the_api_needs_the_token_in_a_header(self):
        self.assertEqual(self.call("GET", "/api/state", token=False)[0], 403)
        self.assertEqual(self.call("GET", "/api/state?t=" + self.app.token, token=False)[0], 403)      # the address is not enough
        status, _h, raw = self.call("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["version"], "2.0.4")

    def test_another_host_name_is_refused_against_rebinding(self):
        self.assertEqual(self.call("GET", "/api/state", host="evil.example:" + str(self.app.port))[0], 403)
        self.assertEqual(self.call("GET", "/api/state", host="127.0.0.1:1")[0], 403)

    def test_a_post_from_another_origin_or_without_json_is_refused(self):
        self.assertEqual(self.call("POST", "/api/plan", {"target": "2.0.8"}, {"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.call("POST", "/api/plan", {"target": "2.0.8"}, {"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.call("POST", "/api/plan", {"target": "2.0.8"}, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.call("POST", "/api/plan", {"target": "2.0.8"}, token=False)[0], 403)
        self.assertEqual(self.call("POST", "/api/nope", {})[0], 404)

    def test_the_listing_the_plan_and_the_whole_update_run_through_the_page(self):
        status, _h, raw = self.call("GET", "/api/releases")
        self.assertEqual([r["version"] for r in json.loads(raw)["releases"]], ["2.0.8", "2.0.4"])
        status, _h, raw = self.call("POST", "/api/plan", {"target": "2.0.8", "policy": "keep_old"}, {"Origin": "http://" + self.host})
        plan = json.loads(raw)
        self.assertEqual((status, plan["direction"], plan["blocked"]), (200, "upgrade", False))
        self.assertTrue(any(c.get("text") for e in plan["config"] for c in e["changes"]))
        self.assertEqual(self.call("POST", "/api/apply", {"target": "2.0.8", "policy": "keep_old"})[0], 200)
        for _ in range(200):
            _s, _h, raw = self.call("GET", "/api/progress")
            job = json.loads(raw)
            if not job["running"]:
                break
            threading.Event().wait(0.1)
        self.assertFalse(job["running"])
        self.assertTrue(job["report"]["ok"], job)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        self.assertEqual([e["step"] for e in job["events"] if e["status"] == "done"][:3], ["lock", "extract", "backup"])
        status, _h, raw = self.call("GET", "/api/history")
        self.assertIn("2.0.4 -> 2.0.8", json.loads(raw)["text"])
        status, _h, raw = self.call("POST", "/api/rollback", {})
        self.assertEqual(mu.read_tool_version(self.root), "2.0.4")

    def test_a_blocked_plan_shows_why_and_an_apply_does_not_change_anything(self):
        before = tree_hash(self.root)
        self.app.updater.probe = lambda port: {"port": port, "open": True, "ours": True, "version": "2.0.4"}
        _s, _h, raw = self.call("POST", "/api/plan", {"target": "2.0.8"})
        self.assertTrue(json.loads(raw)["blocked"])
        self.call("POST", "/api/apply", {"target": "2.0.8"})
        for _ in range(100):
            if not json.loads(self.call("GET", "/api/progress")[2])["running"]:
                break
            threading.Event().wait(0.05)
        self.assertEqual(tree_hash(self.root), before)

    def test_the_catalogue_is_served_in_every_language_and_the_page_never_uses_innerhtml(self):
        for lang in mu.LANGS:
            _s, _h, raw = self.call("GET", "/api/catalog?lang=" + lang)
            self.assertEqual(json.loads(raw)["lang"], lang)
            self.assertIn("btn.apply", json.loads(raw)["catalog"])
        self.assertNotIn("innerHTML", mu.PAGE)                       # what GitHub sends (names, notes) is only ever text
        self.assertNotIn("eval(", mu.PAGE)

    def test_a_zip_chosen_in_the_page_must_be_a_zip_that_exists(self):
        self.assertIn("error", json.loads(self.call("POST", "/api/zip", {"path": str(self.tmp / "no.zip")})[2]))
        self.assertIn("error", json.loads(self.call("POST", "/api/zip", {"path": str(self.tmp / "i" / "LICENSE")})[2]))
        self.assertTrue(json.loads(self.call("POST", "/api/zip", {"path": str(self.zip)})[2])["ok"])

    def test_the_page_listens_only_on_the_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


class TextMenu(Fixture):
    def test_the_menu_shows_the_installation_lists_plans_and_applies(self):
        answers = iter(["1", "2", "3", "2.0.8", "4", "2.0.8", "yes", "6", "0"])
        out = io.StringIO()
        code = mu.console_menu(self.make_updater(), lambda prompt="": next(answers), out)
        text = out.getvalue()
        self.assertEqual(code, mu.OK)
        self.assertIn("2.0.4", text)
        self.assertIn("2.0.8", text)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        self.assertIn("ok", text)

    def test_without_confirmation_nothing_changes(self):
        answers = iter(["4", "2.0.8", "no", "0"])
        before = tree_hash(self.root)
        mu.console_menu(self.make_updater(), lambda prompt="": next(answers), io.StringIO())
        self.assertEqual(tree_hash(self.root), before)

    def test_end_of_input_leaves_the_menu(self):
        def eof(prompt=""):
            raise EOFError
        self.assertEqual(mu.console_menu(self.make_updater(), eof, io.StringIO()), mu.OK)

    def test_the_window_says_so_when_tkinter_or_a_screen_is_missing(self):
        import builtins
        real = builtins.__import__

        def no_tk(name, *a, **k):
            if name.startswith("tkinter"):
                raise ImportError(name)
            return real(name, *a, **k)
        builtins.__import__ = no_tk
        try:
            err = io.StringIO()
            old = sys.stderr
            sys.stderr = err
            try:
                self.assertEqual(mu.run_tk(self.make_updater()), mu.USAGE)
            finally:
                sys.stderr = old
        finally:
            builtins.__import__ = real
        self.assertIn("Tkinter", err.getvalue())


class CommandLine(Fixture):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(mu, "probe_port", NO_MONITOR)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, *argv, answers=()):
        out = io.StringIO()
        it = iter(answers)
        code = mu.main(["--dir", str(self.root), "--backups", str(self.tmp / "copies"), "--zip", str(self.zip), *argv], out, lambda prompt="": next(it))
        return code, out.getvalue()

    def test_status_plan_apply_history_rollback_and_their_exit_codes(self):
        code, text = self.run_cli("status", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["version"], "2.0.4")
        code, text = self.run_cli("plan", "--json")
        self.assertEqual((code, json.loads(text)["target"]), (0, "2.0.8"))
        before = tree_hash(self.root)
        code, text = self.run_cli("apply", "--dry-run", "--yes")
        self.assertEqual(code, 0)
        self.assertEqual(tree_hash(self.root), before)
        code, text = self.run_cli("apply", answers=["no"])
        self.assertEqual(code, mu.NOT_CONFIRMED)
        code, text = self.run_cli("apply", "--yes", "--keep-old-defaults")
        self.assertEqual(code, 0, text)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        code, text = self.run_cli("history")
        self.assertIn("2.0.4 -> 2.0.8", text)
        code, text = self.run_cli("rollback", "--yes")
        self.assertEqual((code, mu.read_tool_version(self.root)), (0, "2.0.4"))
        code, text = self.run_cli("rollback", "--yes")
        self.assertEqual(code, mu.USAGE)

    def test_a_bad_sha_is_exit_code_blocked_and_wrong_use_is_two(self):
        out = io.StringIO()
        code = mu.main(["plan", "--dir", str(self.root), "--zip", str(self.zip), "--sha256", "0" * 64, "--backups", str(self.tmp / "copies")], out)
        self.assertEqual(code, mu.BLOCKED)
        self.assertEqual(mu.main(["plan", "--keep-old-defaults", "--adopt-new-defaults", "--dir", str(self.root)], io.StringIO()), mu.USAGE)
        self.assertEqual(mu.main(["nonsense"], io.StringIO()), mu.USAGE)

    def test_migrate_shows_the_changes_and_writes_only_with_apply(self):
        cfg = self.root / "config" / "actions_monitor.json"
        before = cfg.read_text(encoding="utf-8")
        code, text = self.run_cli("migrate", "--from", "2.0.4", "--to", "2.0.8", "--keep-old-defaults")
        self.assertEqual(code, 0)
        self.assertIn("ci.red_ages", text)
        self.assertEqual(cfg.read_text(encoding="utf-8"), before)
        self.run_cli("migrate", "--from", "2.0.4", "--to", "2.0.8", "--keep-old-defaults", "--apply")
        self.assertNotEqual(cfg.read_text(encoding="utf-8"), before)

    def test_every_language_renders_the_plan(self):
        for lang in mu.LANGS:
            code, text = self.run_cli("plan", "--lang", lang)
            self.assertEqual(code, 0, lang)
            self.assertIn("2.0.4 -> 2.0.8", text)


class OnlyWhenAsked(unittest.TestCase):
    def test_the_updater_has_no_timer_no_schedule_and_never_updates_by_itself(self):
        text = (HERE / "tools" / "monitor_updater.py").read_text(encoding="utf-8")
        for word in ("sched.", "Timer(", "crontab", "schtasks", "while True"):
            self.assertNotIn(word, text, word)

    def test_nothing_in_the_file_runs_a_shell_or_code_from_the_package(self):
        text = (HERE / "tools" / "monitor_updater.py").read_text(encoding="utf-8")
        for word in ("shell=True", "os.system", "eval(", "exec(", "__import__("):
            self.assertNotIn(word, text, word)

    def test_it_uses_only_the_standard_library(self):
        import ast
        tree = ast.parse((HERE / "tools" / "monitor_updater.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.add(node.module.split(".")[0])
        self.assertTrue(names <= set(sys.stdlib_module_names), names - set(sys.stdlib_module_names))


if __name__ == "__main__":
    unittest.main()
