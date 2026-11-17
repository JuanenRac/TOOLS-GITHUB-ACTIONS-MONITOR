# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What Windows and a damaged file leave behind: the state of the reports is never written back after a read that failed, a document that exists and cannot be understood is set aside before a new one is
written over it, a lock whose owner is alive is not robbed and does not burn a CPU while it waits, and the log of actions and the audit of accesses still record when the rotation is refused."""
import json
import os
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
import _timing  # noqa: E402
from github_actions_monitor.reporting import report_service  # noqa: E402
from github_actions_monitor.security import audit_log, auth  # noqa: E402
from github_actions_monitor.storage import file_storage, locks  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)


class TheStateOfTheReports(Base):
    def test_a_failed_read_writes_nothing_and_the_other_accounts_keep_their_memory(self):
        report_service._save_state(self.dir, {"accounts": {"alpha": {"memory": {"x": 1}, "last_run": 5}, "beta": {"last_run": 6}}})
        before = (self.dir / report_service.STATE_FILE).read_text(encoding="utf-8")
        with mock.patch.object(file_storage, "read_json", side_effect=PermissionError("held by another process")):
            report_service._update_entry(self.dir, "delta", last_run=9)
        self.assertEqual((self.dir / report_service.STATE_FILE).read_text(encoding="utf-8"), before)

    def test_a_good_read_adds_the_account_and_keeps_the_others(self):
        report_service._save_state(self.dir, {"accounts": {"alpha": {"last_run": 5}}})
        report_service._update_entry(self.dir, "delta", last_run=9)
        state = json.loads((self.dir / report_service.STATE_FILE).read_text(encoding="utf-8"))
        self.assertEqual(sorted(state["accounts"]), ["alpha", "delta"])


class ADamagedDocument(Base):
    def test_it_is_set_aside_not_written_over(self):
        path = self.dir / "score_snapshots.json"
        good = json.dumps({"2026-01-01T00": {"score": 90}} | {f"2026-01-02T{h:02d}": {"score": 80} for h in range(24)})
        path.write_text(good[:-1] + "\x00", encoding="utf-8")
        self.assertEqual(file_storage.read_json(path, dict, {}, strict=True), {})
        self.assertFalse(path.exists())
        self.assertEqual((self.dir / "score_snapshots.json.damaged").read_text(encoding="utf-8"), good[:-1] + "\x00")

    def test_a_reader_that_does_not_save_leaves_the_file_where_it_is(self):
        path = self.dir / "x.json"
        path.write_text("{ not json", encoding="utf-8")
        self.assertEqual(file_storage.read_json(path, dict, {}), {})
        self.assertTrue(path.exists())

    def test_an_empty_file_is_not_damage(self):
        path = self.dir / "x.json"
        path.write_text("", encoding="utf-8")
        file_storage.read_json(path, dict, {}, strict=True)
        self.assertFalse((self.dir / "x.json.damaged").exists())

    def test_the_ledger_cut_in_its_last_byte_is_kept_apart_by_the_save(self):
        storage = file_storage.FileStorage(self.dir / "accounts", "accounts")
        storage.save_config("alpha", {"github_owner": "alpha"})
        storage.save_doc("alpha", "score_ledger", {"runs": {str(n): [1.0, "failure", None, "r", "w"] for n in range(500)}})
        path = storage._path("alpha", storage._doc_rel("score_ledger"))
        path.write_bytes(path.read_bytes()[:-1])
        self.assertEqual(storage.load_doc("alpha", "score_ledger", None, strict=True), None)
        self.assertTrue(path.with_name(path.name + ".damaged").exists())


class ALockWhoseOwnerIsAlive(Base):
    def lock(self, content, age):
        target = self.dir / "doc.json"
        lock_file = Path(str(target) + ".lock")
        lock_file.write_text(content, encoding="ascii")
        past = time.time() - age
        os.utime(lock_file, (past, past))
        return target, lock_file

    def test_it_is_not_robbed_when_it_is_only_a_little_old(self):
        target, lock_file = self.lock(str(os.getpid()), 60)
        with self.assertRaises(TimeoutError):
            with locks.process_lock(target, 0.6):
                self.fail("the lock of a live owner was taken")
        self.assertTrue(lock_file.exists())

    def test_it_is_taken_when_it_is_very_old(self):
        target, lock_file = self.lock(str(os.getpid()), locks.stale_seconds() * locks.LIVE_FACTOR + 60)
        with locks.process_lock(target, 2.0):
            pass

    def test_an_old_lock_with_no_pid_is_taken(self):
        target, _ = self.lock("", 60)
        with locks.process_lock(target, 2.0):
            pass

    def test_a_delete_that_is_refused_waits_and_respects_the_deadline(self):
        target, lock_file = self.lock("", 60)
        calls = []
        real = Path.unlink

        def refuse(self_path, *args, **kwargs):
            if self_path.name.endswith(".lock"):
                calls.append(1)
                raise PermissionError("in use")
            return real(self_path, *args, **kwargs)
        started = time.perf_counter()
        with mock.patch.object(Path, "unlink", refuse):
            with self.assertRaises(TimeoutError):
                with locks.process_lock(target, 0.5):
                    pass
        took = time.perf_counter() - started
        self.assertLess(took, _timing.limit(2.0))
        self.assertLess(len(calls), 100, "the contender must sleep between attempts, not spin")


class TheRotationIsRefused(Base):
    def test_the_log_of_actions_still_records(self):
        audit_log.FILE = self.dir / "audit_actions.jsonl"
        audit_log._last.update(path=None, hash="")
        self.addCleanup(lambda: (setattr(audit_log, "FILE", None), audit_log._last.update(path=None, hash="")))
        audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", details={"settings": ["a.b"]}, now=1_800_000_000.0)
        with mock.patch.object(audit_log, "settings", return_value={**audit_log.settings({}), "max_mb": 0}), mock.patch("os.replace", side_effect=PermissionError("a reader has it open")):
            before = audit_log.STATS["rotation_failures"]
            lines = [audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", details={"settings": [f"a.b{i}"]}, now=1_800_000_001.0 + i) for i in range(5)]
        self.assertTrue(all(lines))
        self.assertEqual(len((self.dir / "audit_actions.jsonl").read_text(encoding="utf-8").splitlines()), 6)
        self.assertEqual(audit_log.STATS["rotation_failures"] - before, 5)

    def test_the_audit_of_accesses_still_records(self):
        target = self.dir / "auth_audit.jsonl"
        target.write_text("x" * 2000 + "\n", encoding="utf-8")
        with mock.patch.object(auth, "AUDIT_FILE", target), mock.patch.object(auth, "AUDIT_MAX_BYTES", 1000), mock.patch("os.replace", side_effect=PermissionError("a reader has it open")):
            for _ in range(5):
                auth.audit({"audit": True}, "login", "root", "admin", "127.0.0.1", "/api/login", "denied", "bad_password")
        self.assertEqual(len(target.read_text(encoding="utf-8").splitlines()), 6)


if __name__ == "__main__":
    unittest.main()
