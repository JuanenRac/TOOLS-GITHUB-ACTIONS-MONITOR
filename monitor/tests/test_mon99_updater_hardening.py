# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Updates menu under attack: the foreign Host and Origin are refused before anything is read, a run of failed attempts starts a cooldown, the progress file of the updater is read only when it is a plain,
small, well formed file (never a link, never a truncated or hostile one), the status says WHY an update is blocked, the notes of a release are shown as text, and the log handle of the updater is closed.
Nothing here reaches GitHub."""
import json
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import monitor_updater as mu  # noqa: E402
from github_actions_monitor.ops import updates  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class Cooldown(unittest.TestCase):
    def setUp(self):
        updates.note_success()
        self.addCleanup(updates.note_success)

    def test_a_run_of_failed_attempts_starts_the_cooldown_and_a_good_one_clears_the_count(self):
        for i in range(updates.MAX_FAILURES - 1):
            updates.note_failure(now=100.0 + i)
        self.assertEqual(updates.cooldown_left(now=110.0), 0)
        updates.note_success()
        updates.note_failure(now=120.0)
        self.assertEqual(updates.cooldown_left(now=121.0), 0, "the good attempt cleared the count")
        for i in range(updates.MAX_FAILURES):
            updates.note_failure(now=200.0 + i)
        self.assertGreater(updates.cooldown_left(now=205.0), 0)
        self.assertEqual(updates.cooldown_left(now=205.0 + updates.COOLDOWN + 1), 0)

    def test_failures_older_than_the_window_do_not_count(self):
        for i in range(updates.MAX_FAILURES - 1):
            updates.note_failure(now=10.0 + i)
        updates.note_failure(now=10.0 + updates.WINDOW + 50)
        self.assertEqual(updates.cooldown_left(now=10.0 + updates.WINDOW + 51), 0)

    def test_during_the_cooldown_apply_and_rollback_are_refused_before_any_work(self):
        updates._cooldown["until"] = __import__("time").monotonic() + 100
        with mock.patch.object(updates, "reason_blocked", return_value=""), mock.patch.object(updates, "updater", side_effect=AssertionError("worked")):
            for call in (lambda: updates.apply("latest", "conservative", True, "complete", "en"), lambda: updates.rollback(True, "complete", "en")):
                with self.assertRaises(updates.UpdatesError) as caught:
                    call()
                self.assertEqual(caught.exception.code, "cooldown")

    def test_a_refused_apply_counts_as_a_failure(self):
        with mock.patch.object(updates, "reason_blocked", return_value=""), mock.patch.object(updates, "updater", side_effect=updates.UpdatesError("tool_missing")):
            for _ in range(updates.MAX_FAILURES):
                with self.assertRaises(updates.UpdatesError):
                    updates.apply("latest", "conservative", True, "complete", "en")
            with self.assertRaises(updates.UpdatesError) as caught:
                updates.apply("latest", "conservative", True, "complete", "en")
        self.assertEqual(caught.exception.code, "cooldown")

    def test_the_status_says_why_and_the_cooldown_has_its_text_in_the_eight_languages(self):
        found = updates.status({}, "2.1.2", {}, env={"MONITOR_IN_CONTAINER": "1"})
        self.assertIn("blocked_reason", found)
        self.assertEqual(found["blocked_reason"], found["blocked_by"])
        updates._cooldown["until"] = __import__("time").monotonic() + 100
        found = updates.status({}, "2.1.2", {}, env={})
        self.assertGreater(found["cooldown_seconds"], 0)
        for lang in LANGS:
            table = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(table.get("ui.upd_err_cooldown"), lang)


class ProgressFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(updates, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)
        self.path = self.root / mu.BACKUPS_NAME / updates.STATUS_NAME
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def test_a_corrupt_truncated_or_foreign_file_is_not_running(self):
        for text in ("", "{", '{"kind": "apply", "running": tr', "[]", "null", "\x00\x00\x00", '"running"'):
            self.path.write_text(text, encoding="utf-8")
            self.assertEqual(updates.progress(), {"running": False}, repr(text))

    def test_a_huge_file_is_not_read(self):
        self.path.write_text(json.dumps({"running": True, "pid": os.getpid(), "events": ["x" * 100] * 5000}), encoding="utf-8")
        self.assertGreater(self.path.stat().st_size, updates.MAX_STATUS_BYTES)
        self.assertEqual(updates.progress(), {"running": False})

    def test_a_link_in_place_of_the_file_is_not_followed(self):
        target = self.root / "elsewhere.json"
        target.write_text(json.dumps({"running": True, "pid": os.getpid(), "events": []}), encoding="utf-8")
        try:
            self.path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available here")
        self.assertEqual(updates.progress(), {"running": False})

    def test_a_good_file_is_read_and_never_shows_the_pid(self):
        self.path.write_text(json.dumps({"kind": "apply", "running": True, "pid": os.getpid(), "events": []}), encoding="utf-8")
        found = updates.progress()
        self.assertTrue(found["running"])
        self.assertNotIn("pid", found)


class Handles(unittest.TestCase):
    def test_the_log_of_the_updater_is_closed_after_the_start(self):
        seen = []

        class Fake:
            pid = 1

        def popen(*a, **k):
            seen.append(k["stdout"])
            return Fake()

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(updates, "ROOT", Path(tmp.name)):
            mod, up = updates.updater()
            with warnings.catch_warnings():
                warnings.simplefilter("error", ResourceWarning)
                with mock.patch.object(updates.subprocess, "Popen", side_effect=popen):
                    updates._spawn(["status"], up)
        self.assertTrue(seen[0].closed)


class Routes(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)

    def serve(self):
        from test_164 import LiveServer
        server = LiveServer({})
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        return server

    def test_a_foreign_host_or_origin_is_refused_on_every_route_of_the_menu(self):
        server = self.serve()
        token = server.token()
        for path in ("/api/updates/check", "/api/updates/plan", "/api/updates/apply", "/api/updates/rollback"):
            for headers in ({"Origin": "http://evil.example"}, {"Origin": "null"}, {"Host": "evil.example"}):
                code, _ = server.call(path, {"confirm": True}, {"X-Monitor-Token": token, **headers})
                self.assertEqual(code, 403, (path, headers))
        for path in ("/api/updates/status", "/api/updates/progress", "/api/updates/history"):
            code, _ = server.call(path, None, {"Host": "evil.example"})
            self.assertEqual(code, 403, path)

    def test_without_the_one_use_token_nothing_is_done(self):
        server = self.serve()
        code, answer = server.call("/api/updates/apply", {"confirm": True})
        self.assertIn(code, (401, 403))
        self.assertNotEqual((answer or {}).get("started") if isinstance(answer, dict) else None, True)

    def test_the_routes_that_write_are_still_the_routes_of_this_computer_only(self):
        from github_actions_monitor.app import actions_monitor as am
        for path in ("/api/updates/apply", "/api/updates/rollback", "/api/updates/check", "/api/updates/plan"):
            self.assertIn(path, am.THIS_COMPUTER_POST, path)


class Notes(unittest.TestCase):
    def test_the_notes_of_a_release_reach_the_page_only_through_the_escaper(self):
        line = next(l for l in PAGE.splitlines() if "r.notes" in l)
        self.assertIn("esc(r.notes||\"\")", line)
        self.assertNotIn("innerHTML=r.notes", PAGE.replace(" ", ""))
        for key in ("r.version",):
            for l in PAGE.splitlines():
                if key in l and "upd-" in l:
                    self.assertIn("esc(" + key + ")", l)


if __name__ == "__main__":
    unittest.main()
