# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Updates menu: the updater used from inside the monitor. The engine side (the monitor that asks for the update stops by itself, the update waits for it, a failed start puts the previous version back and
starts it, the progress file) with the fake source of the engine tests; the service side (what the page may see, what it may do, one update at a time); the routes (who can do what, nothing without confirmation);
and the page (the entry in the System group, the dialog, the eight languages). Nothing here reaches GitHub."""
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import monitor_updater as mu  # noqa: E402
from github_actions_monitor.ops import updates  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402
from test_66_updater_engine import NO_MONITOR, Base, FakeSource, config_from_defaults, make_install, tree_hash  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
OPEN = lambda port: {"port": port, "open": True, "ours": True, "version": "2.0.1"}      # noqa: E731


class Handover(Base):
    def setUp(self):
        super().setUp()
        self.root = make_install(self.tmp / "i", "2.0.1", config_from_defaults("2.0.1"))

    def test_the_monitor_that_asks_for_the_update_does_not_block_the_plan(self):
        plan = self.updater(self.root, probe=OPEN).plan("2.0.8", {"handover": True})
        codes = {c["code"]: c["severity"] for c in plan["checks"]}
        self.assertFalse(plan["blocked"])
        self.assertEqual(codes.get("handover"), "info")
        self.assertNotIn("running", codes)

    def test_without_the_handover_a_running_monitor_still_blocks(self):
        plan = self.updater(self.root, probe=OPEN).plan("2.0.8", {})
        self.assertTrue(plan["blocked"])

    def test_the_update_waits_for_the_monitor_to_stop_and_then_applies(self):
        stopped = []
        up = self.updater(self.root, probe=lambda port: NO_MONITOR(port) if stopped else OPEN(port))
        with mock.patch.object(mu.time, "sleep", side_effect=lambda seconds: stopped.append(seconds)):
            report = up.apply("2.0.8", {"handover": True})
        self.assertTrue(report["ok"], report.get("error"))
        self.assertTrue(stopped, "it waited at least once")

    def test_a_monitor_that_never_stops_leaves_everything_as_it_was(self):
        before = tree_hash(self.root)
        up = self.updater(self.root, probe=OPEN)
        report = up.apply("2.0.8", {"handover": True, "handover_timeout": 0})
        self.assertEqual(report["code"], mu.BLOCKED)
        self.assertEqual(tree_hash(self.root), before)

    def test_a_failed_update_puts_the_previous_version_back_and_starts_it(self):
        up = self.updater(self.root)
        started = []
        with mock.patch.object(mu.Updater, "_verify", side_effect=RuntimeError("the new version is broken")), \
                mock.patch.object(mu.Updater, "_start", side_effect=lambda plan, to, journal, holder, opts: started.append(to)):
            report = up.apply("2.0.8", {"handover": True, "start": True})
        self.assertTrue(report["rolled_back"])
        self.assertEqual(started, ["2.0.1"], "the monitor that was stopped for the update comes back in the version it had")

    def test_without_the_handover_nothing_is_started_after_a_failure(self):
        up = self.updater(self.root)
        started = []
        with mock.patch.object(mu.Updater, "_verify", side_effect=RuntimeError("x")), \
                mock.patch.object(mu.Updater, "_start", side_effect=lambda *a, **k: started.append(1)):
            report = up.apply("2.0.8", {"start": False})
        self.assertTrue(report["rolled_back"])
        self.assertEqual(started, [])

    def test_the_way_back_waits_for_the_monitor_and_starts_the_restored_version(self):
        up = self.updater(self.root)
        self.assertTrue(up.apply("2.0.8", {})["ok"])
        stopped, started = [], []
        up.probe = lambda port: NO_MONITOR(port) if stopped else OPEN(port)
        with mock.patch.object(mu.time, "sleep", side_effect=lambda seconds: stopped.append(seconds)), \
                mock.patch.object(mu.Updater, "_start", side_effect=lambda plan, to, journal, holder, opts: started.append(to)):
            report = up.go_back(handover=True)
        self.assertTrue(report["ok"], report.get("error"))
        self.assertEqual(started, ["2.0.1"])

    def test_the_way_back_without_the_handover_still_refuses_while_the_monitor_runs(self):
        up = self.updater(self.root)
        self.assertTrue(up.apply("2.0.8", {})["ok"])
        up.probe = OPEN
        self.assertEqual(up.go_back()["code"], mu.BLOCKED)


class StatusFile(unittest.TestCase):
    def test_the_progress_is_written_event_by_event_and_closed_with_the_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "update_status.json"
            status = mu.StatusFile(path, "apply")
            self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["running"])
            status.event({"step": "backup", "status": "start", "detail": "", "at": "x"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["events"][0]["step"], "backup")
            status.finish("done", {"ok": True})
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((doc["running"], doc["report"], doc["kind"]), (False, {"ok": True}, "apply"))
            self.assertFalse(list(path.parent.glob("*.tmp")), "replaced atomically")

    def test_the_command_line_has_the_two_new_options(self):
        args = mu.build_parser().parse_args(["apply", "--handover", "--status-file", "x.json", "--yes", "--start"])
        self.assertTrue(args.handover)
        self.assertEqual(args.status_file, "x.json")
        self.assertTrue(mu.options_of(args)["handover"])

    def test_the_message_of_the_handover_exists_in_the_eight_languages(self):
        for code in LANGS:
            mu.set_language(code)
            self.assertNotEqual(mu.tr("c.handover", port=8765), "c.handover", code)
        mu.set_language("en")


class Service(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(updates, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def write_status(self, doc):
        path = self.root / mu.BACKUPS_NAME / updates.STATUS_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")

    def test_the_updater_is_the_same_file_the_command_line_uses(self):
        self.assertEqual(updates.TOOL.name, "monitor_updater.py")
        self.assertIs(updates.module(), sys.modules["monitor_updater"])

    def test_it_cannot_be_applied_from_a_container_a_service_the_lite_edition_or_the_demo(self):
        self.assertEqual(updates.reason_blocked(env={"MONITOR_IN_CONTAINER": "1"}), "container")
        self.assertEqual(updates.reason_blocked(env={"INVOCATION_ID": "x"}), "service")
        self.assertEqual(updates.reason_blocked(lite=True, env={}), "lite")
        self.assertEqual(updates.reason_blocked(demo=True, env={}), "demo")
        self.assertEqual(updates.reason_blocked(env={}), "service" if Path("/etc/systemd/system/github-actions-monitor.service").exists() else "")

    def test_nothing_is_applied_without_the_explicit_confirmation(self):
        for value in (None, False, "yes", 1):
            with self.assertRaises(updates.UpdatesError) as caught:
                updates.apply("latest", "conservative", value, "complete", "en", env={})
            self.assertEqual(caught.exception.code, "not_confirmed")
        with self.assertRaises(updates.UpdatesError) as caught:
            updates.rollback(None, "complete", "en", env={})
        self.assertEqual(caught.exception.code, "not_confirmed")

    def test_only_one_update_at_a_time(self):
        import os
        self.write_status({"kind": "apply", "running": True, "pid": os.getpid(), "events": []})
        self.assertTrue(updates.running())
        with mock.patch.object(updates, "reason_blocked", return_value=""):
            with self.assertRaises(updates.UpdatesError) as caught:
                updates.apply("latest", "conservative", True, "complete", "en")
        self.assertEqual(caught.exception.code, "busy")

    def test_a_process_that_died_without_a_result_is_shown_as_stopped_not_running(self):
        self.write_status({"kind": "apply", "running": True, "pid": 2 ** 22 + 12345, "events": []})
        found = updates.progress()
        self.assertEqual((found["running"], found.get("stopped")), (False, True))
        self.assertNotIn("pid", found)

    def test_a_start_that_never_continued_is_given_up_after_a_while(self):
        self.write_status({"kind": "apply", "running": True, "starting": True, "t": time.time(), "pid": 2 ** 22 + 12345, "events": []})
        self.assertTrue(updates.progress()["running"])
        self.write_status({"kind": "apply", "running": True, "starting": True, "t": time.time() - 1000, "pid": 2 ** 22 + 12345, "events": []})
        self.assertFalse(updates.progress()["running"])

    def test_the_check_obeys_the_switch_and_the_connection(self):
        with self.assertRaises(updates.UpdatesError) as caught:
            updates.check({"check": False}, False)
        self.assertEqual(caught.exception.code, "check_off")
        with self.assertRaises(updates.UpdatesError) as caught:
            updates.check({"check": True}, True)
        self.assertEqual(caught.exception.code, "offline")

    def test_the_check_lists_versions_with_their_notes_and_marks_the_installed_one(self):
        class Source(FakeSource):
            def releases(self):
                return [dict(r, body="notes of " + r["version"], assets={mu.ZIP_NAME: {}, "SHA256SUMS": {}}) for r in super().releases()]
        (self.root / "src" / "github_actions_monitor").mkdir(parents=True)
        (self.root / "src" / "github_actions_monitor" / "tool_version.py").write_text('TOOL_VERSION = "2.0.1"\n', encoding="utf-8")
        source = Source({"2.0.1": Path("x"), "2.0.8": Path("y")})
        real = updates.updater
        with mock.patch.object(updates, "updater", side_effect=lambda src=None: real(source)):
            versions = updates.check({"check": True}, False)
        self.assertEqual([v["version"] for v in versions], ["2.0.8", "2.0.1"])
        self.assertEqual([v["relation"] for v in versions], ["newer", "current"])
        self.assertTrue(all(v["has_zip"] and v["has_sums"] for v in versions))
        self.assertIn("notes of 2.0.8", versions[0]["notes"])

    def test_the_status_needs_no_request_to_github(self):
        notice = {"enabled": True, "newer": True, "latest": "9.9.9", "offline": False, "airgapped": False}
        with mock.patch.object(mu.GitHubSource, "releases", side_effect=AssertionError("GitHub was asked")):
            found = updates.status({}, "2.1.1", notice, env={})
        self.assertEqual((found["installed"], found["available"], found["newer"], found["check"]), ("2.1.1", "9.9.9", True, True))
        self.assertIn("can_apply", found)

    def test_the_process_that_applies_the_update_is_started_with_a_hidden_console_never_detached(self):
        calls = []
        class Fake:
            pid = 1
        mod, up = updates.updater()
        with mock.patch.object(updates.subprocess, "Popen", side_effect=lambda *a, **k: calls.append(k) or Fake()):
            updates._spawn(["status"], up)
        if sys.platform == "win32":
            flags = calls[0]["creationflags"]
            self.assertTrue(flags & 0x08000000, "CREATE_NO_WINDOW")
            self.assertFalse(flags & 0x00000008, "DETACHED_PROCESS")
        else:
            self.assertTrue(calls[0]["start_new_session"])
        self.assertEqual(calls[0]["stdin"], updates.subprocess.DEVNULL)


class Routes(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)

    def serve(self, config=None):
        from test_164 import LiveServer
        server = LiveServer(config or {})
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        return server

    def test_the_status_is_read_by_whoever_reads_the_rest_and_holds_no_path(self):
        server = self.serve()
        code, found = server.call("/api/updates/status")
        self.assertEqual(code, 200)
        self.assertEqual(found["installed"], found["installed"] and found["installed"])
        for key in ("available", "newer", "check", "can_apply", "blocked_by", "progress", "last", "can_go_back"):
            self.assertIn(key, found)
        text = json.dumps(found)
        self.assertNotIn(str(HERE), text)
        code, progress = server.call("/api/updates/progress")
        self.assertEqual((code, progress.get("running")), (200, False))
        code, history = server.call("/api/updates/history")
        self.assertEqual((code, isinstance(history["entries"], list)), (200, True))

    def test_applying_without_the_confirmation_does_nothing(self):
        server = self.serve()
        for path in ("/api/updates/apply", "/api/updates/rollback"):
            code, answer = server.sensitive(path, {"target": "latest"})
            self.assertEqual(code, 200)
            self.assertFalse(answer["ok"], path)
            self.assertIn(answer["status"], ("not_confirmed", "service", "container", "demo"), path)

    def test_every_write_is_a_route_of_this_computer_and_of_an_administrator(self):
        from github_actions_monitor.app import actions_monitor as am
        for path in ("/api/updates/check", "/api/updates/plan", "/api/updates/apply", "/api/updates/rollback"):
            self.assertIn(path, am.THIS_COMPUTER_ADVANCED, path)
            self.assertEqual(auth.required_role("POST", path), "admin", path)
        for path in ("/api/updates/status", "/api/updates/progress", "/api/updates/history"):
            self.assertEqual(auth.required_role("GET", path), "viewer", path)
        self.assertIn("/api/updates", am.LITE_PATHS)

    def test_the_lite_edition_has_no_such_routes(self):
        from github_actions_monitor.app import actions_monitor as am
        self.assertTrue(any(p.startswith("/api/updates") or p == "/api/updates" for p in am.LITE_PATHS))


class ThePage(unittest.TestCase):
    def test_the_entry_is_in_the_system_group_before_settings_and_not_in_lite(self):
        system = PAGE[PAGE.index('data-group="system"'):]
        self.assertLess(system.index('id="n-upd"'), system.index('id="n-cfg"'))
        self.assertIn(".lite #n-upd,.lite #t-upd", PAGE)
        self.assertIn('id="t-upd"', PAGE)
        self.assertRegex(PAGE, r'const TABS=LITE\?\[[^\]]*\]:\[[^\]]*"hist","upd","cfg"\]')

    def test_the_page_asks_before_it_applies_and_says_what_will_happen(self):
        self.assertRegex(PAGE, r"askConfirm\(text,\{danger:true\}\)")
        self.assertIn('confirm:true', PAGE)
        self.assertIn('ui.upd_confirm', PAGE)
        self.assertIn("location.reload()", PAGE)      # the new version brings a new page

    def test_every_text_of_the_menu_exists_in_the_eight_languages(self):
        used = {k for k in re.findall(r'"(ui\.upd_[a-z_]+)"', PAGE) if not k.endswith("_")} | {"ui.tab_upd", "ui.upd_title"}
        used |= {"ui.upd_blocked_" + b for b in ("lite", "container", "service", "demo", "tool_missing", "account")}
        used |= {"ui.upd_err_" + e for e in ("check_off", "offline", "fetch_failed", "busy", "blocked", "same", "not_confirmed", "no_previous", "failed", "network", "local_only", "token")}
        used |= {"ui.upd_step_" + s for s in ("lock", "extract", "backup", "copy", "retire", "launchers", "config", "layout", "verify", "start", "rollback")}
        used |= {"ui.upd_r_ok", "ui.upd_r_rolled_back", "ui.upd_r_manual_rollback"}
        for code in LANGS:
            data = json.loads((HERE / "assets" / "locales" / f"{code}.json").read_text(encoding="utf-8"))
            missing = sorted(k for k in used if k not in data or not str(data[k]).strip())
            self.assertEqual(missing, [], code)
            if code != "en":
                for key in ("ui.upd_confirm", "ui.upd_back_confirm"):
                    self.assertNotEqual(data[key], json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8"))[key], (code, key))
            for placeholder in ("{from}", "{to}", "{verified}", "{backups}", "{changes}"):
                self.assertIn(placeholder, data["ui.upd_confirm"], (code, placeholder))

    def test_the_confirmation_names_the_copy_the_checksum_the_restart_and_the_way_back(self):
        en = json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8"))["ui.upd_confirm"]
        for word in ("SHA256SUMS", "copy", "stops by itself", "previous one is put back"):
            self.assertIn(word, en)


if __name__ == "__main__":
    unittest.main()
