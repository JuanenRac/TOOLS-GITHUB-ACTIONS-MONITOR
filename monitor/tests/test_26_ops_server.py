# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The operation through the server: GET /api/ops/status, POST /api/ops/backup and POST /api/ops/purge (the purge does not exist until it is switched on, is a dry run unless asked, and is refused
without a recent good backup), their places in the tables of the log of actions, of the routes of this computer, of the roles and of the lite edition, and the tick of the scheduled copy."""
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: E402
from test_164 import LiveServer  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.ops import bundle, opsconf, purge, schedule  # noqa: E402
from github_actions_monitor.ops.bundle import OpsError  # noqa: E402
from github_actions_monitor.security import audited_posts, auth  # noqa: E402
from github_actions_monitor.storage import installation, runtime  # noqa: E402
from github_actions_monitor.storage.file_storage import FileStorage  # noqa: E402


def stamp(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Place(unittest.TestCase):
    """A temporary installation: its data folder, one account with old and new events, and the patches that make the product use them."""

    def setUp(self):
        _testenv.guard(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "data" / "accounts"
        self.files = FileStorage(self.root, "accounts")
        self.files.save_config("alpha", {"github_owner": "alpha"})
        self.files.append_events("alpha", [{"at": stamp(200), "kind": "old"}, {"at": stamp(150), "kind": "old"}, {"at": stamp(1), "kind": "new"}])
        self.inst = installation.open_installation("file", self.root)
        self.addCleanup(self.inst.close)
        for patch in (mock.patch.object(opsconf.paths, "folder", side_effect=lambda kind, base=None: self.base / kind),
                      mock.patch.object(bundle, "open_installation", side_effect=lambda *a, **k: installation.open_installation("file", self.root)),
                      mock.patch.object(runtime, "process_storage", return_value=(self.files, "alpha"))):
            patch.start()
            self.addCleanup(patch.stop)

    def fresh_backup(self, hours_ago=1.0):
        now = datetime.now(timezone.utc).timestamp()
        schedule._save(None, {"ok": True, "last_ok_epoch": now - hours_ago * 3600, "last_attempt_epoch": now - hours_ago * 3600, "last_ok": "x", "file": "ghamon-backup-x.zip"})


class PurgeOnDemand(Place):
    ON = {"ops": {"purge": {"enabled": True}}}

    def test_it_is_refused_while_it_is_switched_off(self):
        with self.assertRaises(OpsError) as caught:
            purge.run({}, self.files, "alpha")
        self.assertEqual(caught.exception.code, "purge_off")

    def test_a_dry_run_says_what_would_go_and_changes_nothing(self):
        found = purge.run(self.ON, self.files, "alpha")
        self.assertEqual((found["dry_run"], found["would_remove"], found["events"]), (True, 2, 3))
        self.assertFalse(found["backup_ok"], "no copy yet")
        self.assertEqual(self.files.event_stats("alpha")["count"], 3)

    def test_a_real_purge_needs_a_recent_good_copy(self):
        with self.assertRaises(OpsError) as caught:
            purge.run(self.ON, self.files, "alpha", dry_run=False)
        self.assertEqual(caught.exception.code, "purge_no_backup")
        self.fresh_backup(hours_ago=30)
        with self.assertRaises(OpsError):
            purge.run(self.ON, self.files, "alpha", dry_run=False)
        self.assertEqual(self.files.event_stats("alpha")["count"], 3)

    def test_with_a_recent_copy_it_removes_the_old_events_and_leaves_its_line_in_the_audit(self):
        self.fresh_backup()
        done = purge.run(self.ON, self.files, "alpha", dry_run=False)
        self.assertEqual(done["line"]["events_removed"], 2)
        self.assertEqual(self.files.event_stats("alpha")["count"], 1)
        from github_actions_monitor.storage import retention
        self.assertEqual(len(retention.audit(self.files, "alpha")["runs"]), 1)

    def test_a_requirement_of_zero_hours_does_not_ask_for_a_copy(self):
        config = {"ops": {"purge": {"enabled": True, "require_backup_hours": 0}}}
        self.assertEqual(purge.run(config, self.files, "alpha", dry_run=False)["line"]["events_removed"], 2)


class Routes(Place):
    def serve(self, config):
        server = LiveServer(config)
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        return server

    def test_the_purge_route_does_not_exist_until_it_is_switched_on(self):
        server = self.serve({})
        code, _ = server.sensitive("/api/ops/purge", {})
        self.assertEqual(code, 404)

    def test_the_purge_route_plans_first_and_refuses_without_a_copy(self):
        server = self.serve({"ops": {"purge": {"enabled": True}}})
        code, plan = server.sensitive("/api/ops/purge", {})
        self.assertEqual((code, plan["ok"], plan["dry_run"], plan["would_remove"], plan["backup_ok"]), (200, True, True, 2, False))
        code, answer = server.sensitive("/api/ops/purge", {"dry_run": False})
        self.assertEqual((code, answer), (200, {"ok": False, "status": "purge_no_backup"}))
        self.assertEqual(self.files.event_stats("alpha")["count"], 3)
        self.fresh_backup()
        code, answer = server.sensitive("/api/ops/purge", {"dry_run": False})
        self.assertEqual((answer["ok"], answer["line"]["events_removed"]), (True, 2))

    def test_a_backup_made_from_the_route_is_written_recorded_and_listed(self):
        copies = self.base / "copies"
        server = self.serve({"ops": {"backup": {"dir": str(copies)}}})
        code, answer = server.sensitive("/api/ops/backup", {})
        self.assertEqual((code, answer["ok"], answer["status"]), (200, True, "ok"), answer)
        self.assertEqual(len(list(copies.glob("ghamon-backup-*.zip"))), 1)
        code, status = server.call("/api/ops/status")
        self.assertEqual(code, 200)
        self.assertEqual((status["schema"], status["backup"]["ok"], status["backup"]["count"]), (1, True, 1))
        self.assertNotIn(str(self.base), json.dumps(status), "no path of the person")

    def test_a_backup_while_another_is_running_is_refused(self):
        server = self.serve({})
        self.assertTrue(schedule.RUNNING.acquire(blocking=False))
        try:
            code, answer = server.sensitive("/api/ops/backup", {})
        finally:
            schedule.RUNNING.release()
        self.assertEqual((answer["ok"], answer["status"]), (False, "busy"))

    def test_the_routes_are_in_every_table_that_guards_them(self):
        for path in ("/api/ops/backup", "/api/ops/purge"):
            self.assertIn(path, am.THIS_COMPUTER_ADVANCED)
            self.assertIn(path, audited_posts.AUDITED)
            self.assertEqual(auth.required_role("POST", path), "admin", "an administrator only: it is not in the list of a maintainer")
        self.assertEqual(auth.required_role("GET", "/api/ops/status"), "viewer")
        self.assertIn("/api/ops", am.LITE_PATHS, "the lite edition has none of it")


class TheTick(Place):
    def test_the_tick_starts_a_thread_only_when_a_copy_is_due(self):
        started = []
        with mock.patch.object(threading, "Thread") as thread:
            thread.side_effect = lambda **k: started.append(k) or mock.Mock()
            am.backup_tick({})
            self.assertEqual(started, [], "off by default: no thread")
            am.backup_tick({"ops": {"backup": {"enabled": True}}})
            self.assertEqual(len(started), 1)
            self.assertEqual(started[0]["name"], "ops-backup")
            with mock.patch.dict(am.LITE, {"on": True}):
                am.backup_tick({"ops": {"backup": {"enabled": True}}})
            self.assertEqual(len(started), 1, "never in the lite edition")

    def test_the_job_swallows_what_goes_wrong(self):
        with mock.patch.object(schedule, "tick", side_effect=RuntimeError("x")):
            am.backup_job({})      # must not raise


if __name__ == "__main__":
    unittest.main()
