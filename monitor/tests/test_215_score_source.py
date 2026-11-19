# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The score, the reports, the mirror and the analytics on every run (`score.source`): the choice of source, the hourly totals of the ledger, the honest mark when the page's cut hides runs."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.scoring import engine, ledger as service  # noqa: E402
from github_actions_monitor.storage import file_storage  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400.0


def run(i, ago, conclusion="success", repo="a/x", name="ci"):
    return {"id": i, "repo": repo, "name": name, "status": "completed", "conclusion": conclusion, "seconds": 60, "started": NOW - ago}


def account(total):
    """5000 finished runs spread over three days: every fifth one is a failure, the newest 600 are all green, so the cut and the whole disagree."""
    out = []
    for i in range(total):
        out.append(run(i + 1, 60 + i * 50, "success" if (i < 600 or i % 5) else "failure"))
    return out


class Source(unittest.TestCase):
    def test_the_source_is_recent600_until_chosen_and_nonsense_is_ignored(self):
        self.assertEqual(engine.settings({})["source"], "recent600")
        self.assertEqual(engine.settings({"score": {"source": "everything"}})["source"], "recent600")
        self.assertEqual(engine.settings({"score": {"source": True}})["source"], "recent600")
        self.assertEqual(engine.settings({"score": {"source": "ledger"}})["source"], "ledger")
        self.assertTrue(settings_api.check_value("score.source", "ledger")[0])
        self.assertFalse(settings_api.check_value("score.source", "all")[0])

    def test_the_runs_for_the_score_are_all_the_runs_only_when_the_ledger_is_chosen(self):
        full = account(1000)
        data = {"runs": full[:600], "runs_total": 1000}
        old = am.ALL_RUNS["runs"]
        am.ALL_RUNS["runs"] = full
        try:
            self.assertEqual(len(am.source_runs({"score": {"source": "ledger"}}, data)), 1000)
            self.assertEqual(len(am.source_runs({"score": {"source": "recent600"}}, data)), 600)
            self.assertEqual(len(am.source_runs({"score": {}}, data)), 600)
            self.assertEqual(len(am.source_runs({"score": {"source": "ledger"}}, {"runs": full[:600], "runs_total": 999})), 600)      # the full list belongs to another picture
            self.assertEqual(am.source_runs({"score": {"source": "ledger"}}, {}), [])
        finally:
            am.ALL_RUNS["runs"] = old


class Totals(unittest.TestCase):
    def cfg(self, **extra):
        return engine.settings({"score": {"calibrating_hours": 0, **extra}})

    def test_with_5000_runs_the_failure_rate_is_the_one_counted_by_hand(self):
        runs = account(5000)
        by_hand = sum(1 for r in runs if r["conclusion"] == "failure") / 5000
        ledger = service.empty_ledger(NOW - 3 * DAY)
        service.update_ledger(ledger, runs, [], NOW, 15)
        whole = service.make_snapshot(ledger, self.cfg(), NOW, "a", source="ledger", seen=5000)
        self.assertEqual(whole["data_quality"]["runs"], 5000)
        self.assertEqual(whole["data_quality"]["source"], "ledger")
        self.assertNotIn("cut", whole["data_quality"])
        self.assertAlmostEqual(1 - by_hand, sum(1 for r in service.ledger_runs(ledger) if r["conclusion"] == "success") / 5000, places=6)
        cut = service.empty_ledger(NOW - 3 * DAY)
        service.update_ledger(cut, runs[:600], [], NOW, 15)
        seen = service.make_snapshot(cut, self.cfg(), NOW, "a", source="recent600", seen=5000)
        self.assertEqual(seen["data_quality"]["runs"], 600)      # the cut sees a recent part and says so
        self.assertTrue(seen["data_quality"]["cut"])
        self.assertEqual(seen["data_quality"]["runs_read"], 5000)
        self.assertIn("recent_cut", seen["data_quality"]["reasons"])

    def test_a_page_that_lists_everything_is_not_marked_cut(self):
        ledger = service.empty_ledger(NOW - 3 * DAY)
        service.update_ledger(ledger, account(300), [], NOW, 15)
        snap = service.make_snapshot(ledger, self.cfg(), NOW, "a", source="recent600", seen=300)
        self.assertNotIn("cut", snap["data_quality"])
        self.assertEqual(snap["data_quality"]["source"], "recent600")

    def test_the_hourly_totals_count_each_run_once_and_outlive_the_ceiling(self):
        ledger = service.empty_ledger(NOW - 3 * DAY)
        runs = account(400)
        service.update_ledger(ledger, runs, [], NOW, 15)
        service.update_ledger(ledger, runs, [], NOW + 60, 15)      # seen again: not counted twice
        ok, bad = service.hours_between(ledger, NOW - 3 * DAY, NOW + DAY)
        self.assertEqual((ok, bad), (sum(1 for r in runs if r["conclusion"] == "success"), sum(1 for r in runs if r["conclusion"] == "failure")))
        old = service.MAX_RUNS
        service.MAX_RUNS = 50
        try:
            ledger2 = service.empty_ledger(NOW - 3 * DAY)
            service.update_ledger(ledger2, runs, [], NOW, 15)
        finally:
            service.MAX_RUNS = old
        self.assertEqual(len(ledger2["runs"]), 50)
        snap = service.make_snapshot(ledger2, self.cfg(), NOW, "a", source="ledger")
        self.assertTrue(snap["data_quality"]["truncated"])
        self.assertGreater(snap["data_quality"]["aggregate"]["runs"], 50)      # the totals still hold the runs the ceiling dropped
        self.assertLessEqual(snap["data_quality"]["aggregate"]["runs"], 400)

    def test_a_ledger_from_before_the_hourly_totals_builds_them_from_its_runs(self):
        saved = {"first_seen": NOW - DAY, "last_tick": NOW - 1000, "runs": {"1": [NOW - 100, "success", 5, "a/x", "ci"], "2": [NOW - 200, "failure", 5, "a/x", "ci"]}, "collab": {}}
        ledger = service.clean_ledger(saved, NOW)
        self.assertEqual(sum(sum(row) for row in ledger["hours"].values()), 2)
        again = service.clean_ledger({**saved, "hours": {"5": [1, 2], "x": [1, 1], "6": [-1, 0], "7": "no"}}, NOW)
        self.assertEqual(again["hours"], {"5": [1, 2]})

    def test_an_old_snapshot_without_the_new_fields_is_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp))
            old = {"schema": 1, "at": NOW - 7200, "account": "alpha", "window_days": 7, "state": "scored", "score": 80.0, "letter": "B", "data_quality": {"runs": 30, "min_runs": 20, "reasons": []}, "repos": []}
            storage.save_score_snapshot("alpha", service.hour_key(NOW - 7200), old)
            service.tick(storage, "alpha", {"score": {"source": "ledger"}}, [run(1, 10)], [], now=NOW, seen=1)
            saved = storage.load_score_snapshots("alpha")
            self.assertEqual(len(saved), 2)
            self.assertNotIn("source", saved[0]["data_quality"] if "data_quality" in saved[0] else {})
            self.assertEqual(saved[-1]["data_quality"]["source"], "ledger")


if __name__ == "__main__":
    unittest.main()
