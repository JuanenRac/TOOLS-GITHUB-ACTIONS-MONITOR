# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""MetricCollector of the score: synthetic series with a fixed seed, and the cases where a number must be None instead of 0."""
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.scoring import collector  # noqa: E402

T0 = 1_700_000_000.0
DAY = 86400.0


def run(offset, conclusion="success", seconds=60, repo="a/x", name="ci", status="completed"):
    return {"repo": repo, "name": name, "status": status, "conclusion": conclusion, "seconds": seconds, "started": T0 + offset}


class Runs(unittest.TestCase):
    def test_nothing_gives_none_and_never_zero(self):
        m = collector.collect_runs([], T0, T0 + DAY)
        self.assertIsNone(m["success_rate"])
        self.assertIsNone(m["duration_p50"])
        self.assertIsNone(m["mttr"])
        self.assertIsNone(m["throughput"])
        self.assertEqual(m["samples"]["runs"], 0)

    def test_cancelled_skipped_and_unfinished_do_not_count(self):
        runs = [run(10), run(20, "failure"), run(30, "cancelled"), run(40, "skipped"), run(50, None, status="in_progress")]
        m = collector.collect_runs(runs, T0, T0 + DAY)
        self.assertEqual(m["samples"]["runs"], 2)
        self.assertEqual(m["success_rate"], 0.5)

    def test_only_runs_inside_the_window(self):
        runs = [run(-1), run(0), run(DAY - 1), run(DAY)]
        m = collector.collect_runs(runs, T0, T0 + DAY)
        self.assertEqual(m["samples"]["runs"], 2)

    def test_percentiles_use_successful_runs_only(self):
        runs = [run(i, seconds=s) for i, s in enumerate([10, 20, 30, 40, 100])] + [run(99, "failure", seconds=9999)]
        m = collector.collect_runs(runs, T0, T0 + DAY)
        self.assertEqual(m["duration_p50"], 30)
        self.assertEqual(m["duration_p95"], 100)

    def test_mttr_is_failure_to_next_success_per_workflow(self):
        runs = [run(0, "failure"), run(100, "failure"), run(600, "success"),
                run(0, "failure", name="other"), run(1200, "success", name="other"), run(5000, "failure", name="third")]
        m = collector.collect_runs(runs, T0, T0 + DAY)
        self.assertEqual(m["samples"]["recoveries"], 2)
        self.assertEqual(m["mttr"], 600)          # nearest-rank median of 600 and 1200

    def test_a_still_red_workflow_has_no_recovery(self):
        m = collector.collect_runs([run(0, "failure"), run(50, "failure")], T0, T0 + DAY)
        self.assertIsNone(m["mttr"])

    def test_throughput_is_runs_per_day(self):
        runs = [run(i * 100) for i in range(14)]
        self.assertAlmostEqual(collector.collect_runs(runs, T0, T0 + 2 * DAY)["throughput"], 7.0)

    def test_unreadable_entries_are_ignored(self):
        runs = [None, "x", {"status": "completed", "conclusion": "success", "started": "nonsense"}, run(5)]
        self.assertEqual(collector.collect_runs(runs, T0, T0 + DAY)["samples"]["runs"], 1)

    def test_seeded_series_is_stable_and_order_free(self):
        rnd = random.Random(190)
        runs = [run(rnd.randint(0, int(DAY) - 1), rnd.choice(["success"] * 4 + ["failure"]), rnd.randint(30, 300)) for _ in range(200)]
        a = collector.collect_runs(runs, T0, T0 + DAY)
        b = collector.collect_runs(list(reversed(runs)), T0, T0 + DAY)
        self.assertEqual(a, b)
        self.assertTrue(0.6 < a["success_rate"] < 0.95)


class Collab(unittest.TestCase):
    def test_resolution_time_counts_only_items_closed_in_the_window(self):
        items = [{"opened": T0 - 100, "closed": T0 + 400}, {"opened": T0, "closed": T0 + 1000}, {"opened": T0 - 5000, "closed": T0 - 10}]
        m = collector.collect_collab(items, T0, T0 + DAY)
        self.assertEqual(m["samples"]["collab_closed"], 2)
        self.assertEqual(m["collab_resolution_time"], 500)

    def test_open_items_at_the_end_of_the_window(self):
        items = [{"opened": T0, "closed": None}, {"opened": T0 + 2 * DAY, "closed": None}, {"opened": T0, "closed": T0 + 2 * DAY}]
        m = collector.collect_collab(items, T0, T0 + DAY)
        self.assertEqual(m["collab_open"], 2)
        self.assertIsNone(m["collab_resolution_time"])

    def test_iso_times_are_read(self):
        items = [{"opened": "2023-11-14T22:13:20Z", "closed": "2023-11-14T23:13:20Z"}]
        m = collector.collect_collab(items, T0, T0 + DAY)
        self.assertEqual(m["collab_resolution_time"], 3600)


class Merge(unittest.TestCase):
    def test_collect_merges_samples_and_window(self):
        m = collector.collect([run(1)], [{"opened": T0, "closed": T0 + 10}], T0, T0 + DAY)
        self.assertEqual(m["samples"], {"runs": 1, "durations": 1, "recoveries": 0, "collab_closed": 1, "collab_open": 0})
        self.assertEqual(m["window"], {"start": T0, "end": T0 + DAY})

    def test_by_repo_breaks_down(self):
        out = collector.by_repo([run(1, repo="a/x"), run(2, "failure", repo="a/y")], T0, T0 + DAY)
        self.assertEqual(sorted(out), ["a/x", "a/y"])
        self.assertEqual(out["a/y"]["success_rate"], 0.0)


class Quiet(unittest.TestCase):
    def test_runs_and_no_failure_means_nothing_to_recover(self):
        m = collector.collect_runs([run(1), run(2)], T0, T0 + DAY)
        self.assertEqual((m["mttr"], m["samples"]["recoveries"]), (0.0, 0))

    def test_a_failure_that_has_not_recovered_is_still_unknown_not_zero(self):
        self.assertIsNone(collector.collect_runs([run(1), run(2, "failure")], T0, T0 + DAY)["mttr"])

    def test_no_runs_at_all_is_unknown(self):
        self.assertIsNone(collector.collect_runs([], T0, T0 + DAY)["mttr"])


if __name__ == "__main__":
    unittest.main()
