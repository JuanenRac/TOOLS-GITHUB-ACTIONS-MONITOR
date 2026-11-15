# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The service of the score: the ledger of runs and collaboration alerts, the snapshot of the account and the hourly pass over a real storage."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.scoring import engine, ledger as service  # noqa: E402
from github_actions_monitor.storage import file_storage, sqlite_storage  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400.0


def run(i, ago, conclusion="success", repo="a/x", name="ci", seconds=120):
    return {"id": i, "repo": repo, "name": name, "status": "completed", "conclusion": conclusion, "seconds": seconds, "started": NOW - ago}


class Ledger(unittest.TestCase):
    def test_finished_runs_that_count_are_kept_once(self):
        ledger = service.empty_ledger(NOW)
        runs = [run(1, 100), run(1, 100), run(2, 200, "failure"), run(3, 300, "cancelled"), {"id": 4, "status": "in_progress", "started": NOW}, run(None, 5)]
        service.update_ledger(ledger, runs, [], NOW, 15)
        self.assertEqual(sorted(ledger["runs"]), ["1", "2"])

    def test_old_runs_are_forgotten(self):
        ledger = service.empty_ledger(NOW)
        service.update_ledger(ledger, [run(1, 100), run(2, 20 * DAY)], [], NOW, 15)
        self.assertEqual(sorted(ledger["runs"]), ["1"])

    def test_the_ledger_has_a_ceiling(self):
        ledger = service.empty_ledger(NOW)
        old = service.MAX_RUNS
        service.MAX_RUNS = 5
        try:
            service.update_ledger(ledger, [run(i, i * 10) for i in range(1, 12)], [], NOW, 15)
        finally:
            service.MAX_RUNS = old
        self.assertEqual(sorted(ledger["runs"], key=int), ["1", "2", "3", "4", "5"])      # the newest five

    def test_an_alert_is_open_until_it_is_gone(self):
        ledger = service.empty_ledger(NOW)
        service.update_ledger(ledger, [], [{"id": "k1", "created_at": "2027-01-14T00:00:00Z"}], NOW, 15)
        self.assertIsNone(ledger["collab"]["k1"][1])
        service.update_ledger(ledger, [], [], NOW + 600, 15)
        self.assertEqual(ledger["collab"]["k1"][1], NOW + 600)
        service.update_ledger(ledger, [], [], NOW + 1200, 15)      # a resolved one is not closed again
        self.assertEqual(ledger["collab"]["k1"][1], NOW + 600)

    def test_a_sentinel_that_has_not_looked_yet_resolves_nothing(self):
        ledger = service.empty_ledger(NOW)
        service.update_ledger(ledger, [], [{"id": "k1", "created_at": NOW - 10}], NOW, 15)
        service.update_ledger(ledger, [], [], NOW + 600, 15, collab_known=False)
        self.assertIsNone(ledger["collab"]["k1"][1])

    def test_a_damaged_document_reads_as_a_fresh_ledger(self):
        for bad in (None, [], "x", {"runs": 3, "collab": "x"}, {"runs": {"1": [1, 2]}, "collab": {"k": [1]}}):
            ledger = service.clean_ledger(bad, NOW)
            self.assertEqual((ledger["runs"], ledger["collab"], ledger["first_seen"]), ({}, {}, NOW))


class Snapshot(unittest.TestCase):
    def cfg(self, **over):
        return engine.settings({"score": {"min_runs": 5, **over}})

    def test_a_new_ledger_is_calibrating(self):
        ledger = service.empty_ledger(NOW)
        service.update_ledger(ledger, [run(i, i * 60) for i in range(1, 30)], [], NOW, 15)
        snap = service.make_snapshot(ledger, self.cfg(), NOW, "alpha")
        self.assertEqual((snap["state"], snap["score"], snap["account"], snap["schema"]), ("calibrating", None, "alpha", 1))

    def test_a_watched_ledger_with_runs_is_scored_and_broken_down_by_repository(self):
        ledger = service.empty_ledger(NOW - 3 * DAY)
        runs = [run(i, i * 3000, repo="a/good") for i in range(1, 40)] + [run(100 + i, i * 3000, "failure" if i % 2 else "success", repo="a/bad") for i in range(1, 40)]
        service.update_ledger(ledger, runs, [], NOW, 15)
        snap = service.make_snapshot(ledger, self.cfg(), NOW, "alpha")
        self.assertEqual(snap["state"], "scored")
        self.assertEqual([r["repo"] for r in snap["repos"]], ["a/bad", "a/good"])      # the worst first
        self.assertGreater(snap["repos"][1]["score"], snap["repos"][0]["score"])
        self.assertEqual(snap["missing_parts"], ["security"])

    def test_a_ledger_without_runs_is_not_scored(self):
        snap = service.make_snapshot(service.empty_ledger(NOW - 3 * DAY), self.cfg(), NOW, "alpha")
        self.assertEqual((snap["state"], snap["score"], snap["repos"]), ("insufficient_data", None, []))


class Tick(unittest.TestCase):
    def backends(self, tmp):
        return [file_storage.FileStorage(Path(tmp) / "files"), sqlite_storage.SqliteStorage(Path(tmp) / "monitor.db")]

    def test_a_pass_writes_the_ledger_and_the_snapshot_of_the_hour(self):
        with tempfile.TemporaryDirectory() as tmp:
            for storage in self.backends(tmp):
                try:
                    runs = [run(i, i * 60) for i in range(1, 10)]
                    snap = service.tick(storage, "alpha", {}, runs, [], now=NOW)
                    self.assertIsNotNone(snap)
                    saved = storage.load_score_snapshots("alpha")
                    self.assertEqual([s["hour"] for s in saved], [service.hour_key(NOW)])
                    self.assertEqual(len(storage.load_doc("alpha", service.LEDGER_DOC)["runs"]), 9)
                finally:
                    storage.close()

    def test_a_pass_that_is_not_due_does_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp))
            self.assertIsNotNone(service.tick(storage, "alpha", {}, [run(1, 10)], [], now=NOW))
            self.assertIsNone(service.tick(storage, "alpha", {}, [run(2, 10)], [], now=NOW + 60))
            self.assertEqual(len(storage.load_doc("alpha", service.LEDGER_DOC)["runs"]), 1)
            self.assertIsNotNone(service.tick(storage, "alpha", {}, [run(2, 10)], [], now=NOW + 60, force=True))
            self.assertIsNotNone(service.tick(storage, "alpha", {}, [], [], now=NOW + 60 + service.MIN_INTERVAL + 1))

    def test_the_score_off_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp))
            self.assertIsNone(service.tick(storage, "alpha", {"score": {"enabled": False}}, [run(1, 10)], [], now=NOW))
            self.assertEqual(storage.load_score_snapshots("alpha"), [])
            self.assertEqual(storage.load_doc("alpha", service.LEDGER_DOC), None)

    def test_two_passes_in_the_same_hour_keep_one_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp))
            service.tick(storage, "alpha", {}, [run(1, 10)], [], now=NOW)
            service.tick(storage, "alpha", {}, [run(2, 10)], [], now=NOW + service.MIN_INTERVAL + 1)
            self.assertEqual(len(storage.load_score_snapshots("alpha")), 1)


if __name__ == "__main__":
    unittest.main()
