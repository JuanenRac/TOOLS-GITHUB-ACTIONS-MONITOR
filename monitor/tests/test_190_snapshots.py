# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Score snapshots in the Storage: one per account and hour, the same behaviour in both backends, kept by the export, the migration between backends and the retention,
and a database of the previous schema that gets its table without losing anything."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.storage import base, file_storage, migrate, retention, sqlite_storage  # noqa: E402


def snap(score, at=0):
    return {"score": score, "letter": "A", "state": "scored", "at": at}


class Both:
    """The behaviour every backend must have; the subclasses only build the storage."""

    def make(self, folder):
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = self.make(Path(self.tmp.name))
        self.addCleanup(self.s.close)

    def test_nothing_saved_gives_an_empty_list(self):
        self.assertEqual(self.s.load_score_snapshots("alpha"), [])

    def test_one_snapshot_per_hour_the_last_one_wins(self):
        self.s.save_score_snapshot("alpha", "2026-01-01T10", snap(80))
        self.s.save_score_snapshot("alpha", "2026-01-01T10", snap(85))
        self.s.save_score_snapshot("alpha", "2026-01-01T11", snap(70))
        got = self.s.load_score_snapshots("alpha")
        self.assertEqual([(g["hour"], g["score"]) for g in got], [("2026-01-01T10", 85), ("2026-01-01T11", 70)])

    def test_order_since_and_limit(self):
        for h in (12, 10, 11, 13):
            self.s.save_score_snapshot("alpha", f"2026-01-01T{h}", snap(h))
        self.assertEqual([g["hour"][-2:] for g in self.s.load_score_snapshots("alpha")], ["10", "11", "12", "13"])
        self.assertEqual([g["hour"][-2:] for g in self.s.load_score_snapshots("alpha", since="2026-01-01T12")], ["12", "13"])
        self.assertEqual([g["hour"][-2:] for g in self.s.load_score_snapshots("alpha", limit=2)], ["12", "13"])
        self.assertEqual(self.s.load_score_snapshots("alpha", limit=0), [])

    def test_accounts_do_not_see_each_other(self):
        self.s.save_score_snapshot("alpha", "2026-01-01T10", snap(1))
        self.s.save_score_snapshot("beta", "2026-01-01T10", snap(2))
        self.assertEqual([g["score"] for g in self.s.load_score_snapshots("alpha")], [1])
        self.assertEqual([g["score"] for g in self.s.load_score_snapshots("beta")], [2])

    def test_a_bad_hour_or_account_is_refused(self):
        for hour in ("2026-01-01", "2026-01-01T1", "x", "", None, "2026-01-01T10:00"):
            with self.assertRaises(base.StorageError):
                self.s.save_score_snapshot("alpha", hour, snap(1))
        with self.assertRaises(base.StorageError):
            self.s.save_score_snapshot("../x", "2026-01-01T10", snap(1))

    def test_purge_removes_only_older_hours(self):
        for h in (9, 10, 11):
            self.s.save_score_snapshot("alpha", f"2026-01-01T{h:02d}", snap(h))
        self.assertEqual(self.s.purge_score_snapshots("alpha", "2026-01-01T10"), {"removed": 1})
        self.assertEqual([g["hour"][-2:] for g in self.s.load_score_snapshots("alpha")], ["10", "11"])
        self.assertEqual(self.s.purge_score_snapshots("alpha", "2026-01-01T10"), {"removed": 0})
        self.assertEqual(self.s.purge_score_snapshots("nobody", "2030-01-01T00"), {"removed": 0})

    def test_export_and_import_carry_the_snapshots_and_replace_the_old_ones(self):
        self.s.save_score_snapshot("alpha", "2026-01-01T10", snap(80))
        payload = self.s.export_account("alpha")
        self.assertEqual([x["hour"] for x in payload["scores"]], ["2026-01-01T10"])
        self.s.save_score_snapshot("alpha", "2026-01-01T11", snap(70))
        self.s.import_account("alpha", payload)
        self.assertEqual([g["hour"] for g in self.s.load_score_snapshots("alpha")], ["2026-01-01T10"])

    def test_the_retention_pass_removes_the_old_snapshots_and_says_so(self):
        now = 1_800_000_000.0
        cfg = retention.settings({"retention": {"analytics_days": 30}})
        old = "2026-01-01T10"
        recent = retention.cutoffs(cfg, now)[1] + "T05"
        recent = "2027-01-15T05"      # newer than now - 30 days (now is 2027-01-15)
        self.s.save_score_snapshot("alpha", old, snap(1))
        self.s.save_score_snapshot("alpha", recent, snap(2))
        line = retention.run(self.s, "alpha", cfg, now)
        self.assertEqual(line["scores_removed"], 1)
        self.assertEqual([g["hour"] for g in self.s.load_score_snapshots("alpha")], [recent])

    def test_verify_stays_sound(self):
        self.s.save_score_snapshot("alpha", "2026-01-01T10", snap(80))
        self.assertEqual(self.s.verify(), [])


class FileBackend(Both, unittest.TestCase):
    def make(self, folder):
        return file_storage.FileStorage(folder)


class SqliteBackend(Both, unittest.TestCase):
    def make(self, folder):
        return sqlite_storage.SqliteStorage(folder / "monitor.db")


class BetweenBackends(unittest.TestCase):
    def test_the_migration_copies_the_snapshots_and_the_comparison_sees_a_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = file_storage.FileStorage(Path(tmp) / "files")
            target = sqlite_storage.SqliteStorage(Path(tmp) / "monitor.db")
            source.save_config("alpha", {"a": 1})
            source.save_score_snapshot("alpha", "2026-01-01T10", snap(80))
            self.assertEqual(migrate.plan(source, target)[0]["scores"], 1)
            migrate.migrate(source, target, apply=True)
            self.assertEqual([g["score"] for g in target.load_score_snapshots("alpha")], [80])
            self.assertEqual(migrate.verify(source, target), [])
            target.save_score_snapshot("alpha", "2026-01-01T11", snap(1))
            self.assertTrue(migrate.verify(source, target))
            target.close()


class UpgradeFromSchemaOne(unittest.TestCase):
    def test_a_database_of_the_previous_schema_gets_the_table_and_keeps_its_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "monitor.db"
            old = {1: sqlite_storage.MIGRATIONS[1]}
            s = sqlite_storage.SqliteStorage(db, migrations=old)
            s.save_config("alpha", {"a": 1})
            self.assertEqual(s.schema_version(), 1)
            s.close()
            con = sqlite3.connect(str(db))
            try:
                self.assertNotIn("score_snapshots", {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")})
            finally:
                con.close()
            s = sqlite_storage.SqliteStorage(db)
            self.assertEqual((s.schema_version(), s.load_config("alpha")), (2, {"a": 1}))
            s.save_score_snapshot("alpha", "2026-01-01T10", snap(5))
            self.assertEqual(len(s.load_score_snapshots("alpha")), 1)
            self.assertEqual(s.verify(), [])
            s.close()


if __name__ == "__main__":
    unittest.main()
