# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Retention by category, the legal hold, the signed checkpoints and purge of the log of actions, and several processes writing one database."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import ai_prompt_log  # noqa: E402
from github_actions_monitor.ops import opsconf, purge, schedule  # noqa: E402
from github_actions_monitor.reporting import report_service  # noqa: E402
from github_actions_monitor.security import audit_log, compliance_checkpoints as marks  # noqa: E402
from github_actions_monitor.storage import compliance_retention as categories, retention  # noqa: E402
from github_actions_monitor.storage.sqlite_storage import SqliteStorage  # noqa: E402

NOW = 1_800_000_000.0
HOLD = {"retention": {"legal_hold": True}}
SIGNED = {"audit_checkpoints": {"enabled": True}}


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / "audit_actions.jsonl"
        audit_log.FILE = self.log
        audit_log._last.update(path=None, hash="")
        self.addCleanup(lambda: (setattr(audit_log, "FILE", None), audit_log._last.update(path=None, hash="")))
        patch = mock.patch.dict(os.environ, {marks.KEY_ENV: str(self.root / "keys" / "audit.key")})
        patch.start()
        self.addCleanup(patch.stop)
        marks._SINCE.clear()

    def write(self, count, config=SIGNED, start=0):
        for i in range(start, start + count):
            audit_log.record(config, "settings_change", "root", "admin", "alpha", "settings", details={"settings": [f"a.b{i}"]}, now=NOW + i)

    def lines(self):
        return self.log.read_text(encoding="utf-8").splitlines()

    def touch(self, path, age_days):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
        os.utime(path, (NOW - age_days * 86400,) * 2)


class Checkpoints(Folder):
    def test_off_nothing_changes_and_no_key_is_made(self):
        self.write(3, config={})
        self.assertFalse(marks.key_path().exists())
        self.assertFalse(marks.marks_path(self.log).exists())
        self.assertTrue(marks.verify()["ok"])

    def test_a_signed_log_verifies_and_one_rewritten_with_new_hashes_does_not(self):
        self.write(4)
        found = marks.verify()
        self.assertTrue(found["ok"], found)
        self.assertEqual((found["checkpoints"], found["key"]), (1, "ok"))
        entries = [json.loads(x) for x in self.lines()]
        previous = ""
        for entry in entries:      # the whole file written again with honest-looking hashes
            entry["user"] = "mallory"
            entry["prev"] = previous
            entry["hash"] = audit_log._digest(previous, {k: v for k, v in entry.items() if k != "hash"})
            previous = entry["hash"]
        self.log.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
        audit_log.anchor_path(self.log).unlink()
        self.assertTrue(audit_log.verify()["ok"])      # the chain alone accepts it
        found = marks.verify()
        self.assertFalse(found["ok"])
        self.assertEqual(found["bad_checkpoints"][0]["why"], "missing_line")

    def test_a_cut_of_the_end_followed_by_a_new_line_stays_written(self):
        self.write(5)
        self.log.write_text("\n".join(self.lines()[:3]) + "\n", encoding="utf-8")
        self.write(1, start=20)
        found = marks.verify()
        self.assertFalse(found["ok"])
        self.assertEqual(found["gaps"], 1)

    def test_a_forged_checkpoint_or_a_missing_key_does_not_pass(self):
        self.write(2)
        path = marks.marks_path(self.log)
        item = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        item["at"] += 1
        path.write_text(json.dumps(item) + "\n", encoding="utf-8")
        self.assertEqual(marks.verify()["bad_checkpoints"][0]["why"], "signature")
        marks.key_path().unlink()
        found = marks.verify()
        self.assertEqual((found["ok"], found["key"]), (False, "missing"))

    def test_a_checkpoint_each_hour_and_verify_from_a_line(self):
        self.write(2)
        self.write(1, start=4000)
        self.assertEqual(len(marks.read_marks(self.log)), 2)
        found = marks.verify(from_entry=2)
        self.assertTrue(found["ok"], found)
        self.assertEqual((found["entries"], found["from"]), (2, 2))

    def rotated(self):
        """Three files: two rotated and the active one."""
        config = {"audit_checkpoints": {"enabled": True}, "audit_log": {"max_mb": 1}}
        self.write(3, config)
        for number in (1, 2):
            audit_log.rotate(self.log, 5)
            self.write(3, config, start=number * 10)
        return config

    def test_the_purge_removes_old_rotated_files_and_what_is_left_still_verifies(self):
        config = self.rotated()
        before = NOW + 15      # the files whose newest line is before this: the first two
        self.assertEqual(marks.purge(config, before, now=NOW + 100, dry_run=True), {"files": 2, "entries": 6, "reason": ""})
        self.assertTrue(audit_log.generation(self.log, 2).exists())
        self.assertEqual(marks.purge(config, before, now=NOW + 100)["files"], 2)
        self.assertFalse(audit_log.generation(self.log, 1).exists() or audit_log.generation(self.log, 2).exists())
        found = marks.verify()
        self.assertTrue(found["ok"] and found["complete"] and found["purged"], found)
        self.assertEqual(json.loads(self.lines()[-1])["action"], "audit_purge")

    def test_a_legal_hold_keeps_every_file_and_stops_the_rotation(self):
        config = self.rotated()
        held = dict(config, retention={"legal_hold": True})
        self.assertEqual(marks.purge(held, NOW + 10**6)["reason"], "legal_hold")
        self.log.write_text(self.log.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(audit_log, "settings", return_value=dict(audit_log.DEFAULTS, max_mb=0)), mock.patch.object(audit_log, "rotate") as rotate:
            audit_log.record(held, "settings_change", now=NOW + 200)
            rotate.assert_not_called()
            audit_log.record(config, "settings_change", now=NOW + 201)
            rotate.assert_called_once()


class Categories(Folder):
    def places(self):
        return {"reports": self.root / "reports", "backups": self.root / "backups", "ai_log": self.root / "ai_prompts.jsonl"}

    def fill(self):
        places = self.places()
        for age, stamp in ((40, "20200101-000000"), (20, "20200102-000000")):
            self.touch(places["reports"] / f"report_alpha_{stamp}.html", age)
        for age, stamp in ((50, "20200101T000000Z"), (30, "20200102T000000Z")):
            self.touch(places["backups"] / f"ghamon-backup-{stamp}.zip", age)
        self.touch(places["backups"] / "notes.txt", 400)
        places["ai_log"].write_text(json.dumps({"at": NOW - 40 * 86400}) + "\n" + json.dumps({"at": NOW}) + "\n" + "{}\n", encoding="utf-8")
        return places

    def test_each_category_has_its_own_days_and_purging_one_never_touches_the_others(self):
        places = self.fill()
        self.assertEqual(categories.run({}, now=NOW, places=places), {})
        removed = categories.run({"retention": {"reports_days": 10}}, now=NOW, places=places)
        self.assertEqual(removed, {"reports": 1})      # the newest report stays, however old
        self.assertEqual(len(list(places["backups"].iterdir())), 3)
        self.assertEqual(len(places["ai_log"].read_text(encoding="utf-8").splitlines()), 3)
        entry = json.loads(self.lines()[-1])
        self.assertEqual((entry["action"], entry["target"], entry["details"]["removed"]), ("retention_purge", "reports", 1))
        removed = categories.run({"retention": {"backups_days": 10, "ai_log_days": 10}}, now=NOW, places=places)
        self.assertEqual(removed, {"ai_log": 1, "backups": 1})
        self.assertEqual(sorted(p.name for p in places["backups"].iterdir()), ["ghamon-backup-20200102T000000Z.zip", "notes.txt"])

    def test_a_category_with_no_policy_is_named_and_kept(self):
        self.assertEqual(categories.without_policy({}), ["reports", "audit", "ai_log", "backups"])
        names = [row["category"] for row in categories.policy({"retention": {"audit_days": 30}})]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(categories.days({"retention": {"audit_days": True, "reports_days": -1}}), dict.fromkeys(categories.NEW_DAYS, 0))

    def test_under_a_legal_hold_nothing_is_removed_anywhere(self):
        places = self.fill()
        held = {"retention": {"legal_hold": True, "reports_days": 1, "backups_days": 1, "ai_log_days": 1}, "ops": {"purge": {"enabled": True, "require_backup_hours": 0}}}
        self.assertEqual(categories.run(held, now=NOW, places=places), {})
        store = SqliteStorage(self.root / "storage.sqlite3")
        store.append_events("default", [{"at": "2000-01-01T00:00:00Z", "kind": "red_new"}])
        line = retention.run(store, "default", retention.settings(held), NOW, config=held)
        self.assertEqual((line["events_removed"], line["error"]), (0, "legal_hold"))
        self.assertEqual(purge.run(held, store, "default", dry_run=True, now=NOW)["would_remove"], 1)
        with self.assertRaises(Exception) as caught:
            purge.run(held, store, "default", dry_run=False, now=NOW)
        self.assertIn("legal_hold", str(caught.exception))
        with mock.patch.object(retention, "held", return_value=True):
            report_service.prune(places["reports"], "alpha", 0)
            ai_prompt_log._trim(places["ai_log"], 0)
            self.assertEqual(len(list(places["reports"].iterdir())), 2)
            self.assertEqual(len(places["ai_log"].read_text(encoding="utf-8").splitlines()), 3)
            with mock.patch.object(opsconf, "backup_dir", return_value=places["backups"]):
                self.assertEqual(schedule.rotate({"ops": {"backup": {"keep": 1}}}), [])
        self.assertEqual(store.event_stats("default")["count"], 1)

    def test_a_scheduled_purge_that_removes_leaves_its_line_in_the_log_of_actions(self):
        store = SqliteStorage(self.root / "storage.sqlite3")
        store.append_events("default", [{"at": "2000-01-01T00:00:00Z", "kind": "red_new"}])
        retention.run(store, "default", retention.settings({"retention": {"mode": "delete"}}), NOW, config={})
        entry = json.loads(self.lines()[-1])
        self.assertEqual((entry["action"], entry["details"]["events"]), ("retention_purge", 1))

    def test_the_tick_runs_once_per_interval(self):
        state = self.root / "state.json"
        self.assertIsNone(categories.tick({}, now=NOW, state_file=state))
        config = {"retention": {"reports_days": 10}}
        with mock.patch.object(categories, "run", return_value={"reports": 0}) as run:
            categories.tick(config, now=NOW, state_file=state)
            categories.tick(config, now=NOW + 60, state_file=state)
            categories.tick(config, now=NOW + 25 * 3600, state_file=state)
        self.assertEqual(run.call_count, 2)


WRITER = """
import sys
sys.path.insert(0, sys.argv[1])
from github_actions_monitor.storage.sqlite_storage import SqliteStorage
store = SqliteStorage(sys.argv[2])
for n in range(40):
    store.append_events("default", [{"at": "2030-01-01T00:00:00Z", "kind": "red_new", "writer": sys.argv[3], "n": n}])
"""


class Contention(unittest.TestCase):
    def test_four_processes_writing_one_database_lose_nothing(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            path = Path(folder) / "storage.sqlite3"
            store = SqliteStorage(path)
            writers = [subprocess.Popen([sys.executable, "-c", WRITER, str(HERE / "src"), str(path), str(i)], stderr=subprocess.PIPE) for i in range(4)]
            for writer in writers:
                _out, err = writer.communicate(timeout=120)
                self.assertEqual(writer.returncode, 0, err.decode("utf-8", "replace")[-800:])
            self.assertEqual(store.event_stats("default")["count"], 160)


if __name__ == "__main__":
    unittest.main()
