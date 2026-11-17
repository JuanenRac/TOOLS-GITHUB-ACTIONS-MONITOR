# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A failure nobody fixes weighs on the score for as long as it is red: it does not go back to 100 when the failing run leaves the window of days. A failure that crosses the edge of the window is measured
only for the stretch that falls inside the window (the window before counted its own, so no day is counted twice). A collaboration item still open at the end of the window counts with its age so far.
The numbers are the worked examples of the decisions about the score (default weights and limits)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.scoring import collector, engine, ledger  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400.0
CFG = engine.settings({"score": {"min_runs": 5, "min_coverage": 0, "calibrating_hours": 0}})
SECURITY = {"penalty": 0, "repos": 3}
FAST_ITEM = [{"opened": NOW - 3 * 3600, "closed": NOW - 2 * 3600}]      # a collaboration item solved in one hour: that part is 100


def run(n, repo, name, days_ago, conclusion):
    return {"id": n, "repo": repo, "name": name, "status": "completed", "conclusion": conclusion, "seconds": 120, "started": NOW - days_ago * DAY}


def history(fail_days, fixed_days=None):
    """A CI that is green every day for 25 days and a `deploy` that failed `fail_days` ago and was fixed `fixed_days` ago (never, if None)."""
    runs = [run(1000 + d, "r", "ci", d + 0.1, "success") for d in range(25)]
    if fail_days:
        runs += [run(1, "r", "deploy", fail_days + 1, "success"), run(2, "r", "deploy", fail_days, "failure")]
        if fixed_days is not None:
            runs.append(run(3, "r", "deploy", fixed_days, "success"))
    return runs


def answer(runs, collab):
    return engine.score_window(runs, collab, NOW, CFG, watched_hours=24 * 60, security=SECURITY)


def part(result, name):
    return next(p for p in result["parts"] if p["part"] == name)


class TheOpenRedKeepsWeighing(unittest.TestCase):
    def test_the_recovery_stays_at_zero_after_the_failure_leaves_the_window(self):
        values = [part(answer(history(d), FAST_ITEM), "recovery")["score"] for d in (2, 6, 8, 10, 14, 20)]
        self.assertEqual(values, [0.0] * 6)

    def test_the_open_stretch_is_the_one_inside_the_window_and_is_the_same_from_the_edge_on(self):
        for d in (8, 14, 20):
            metrics = collector.collect(history(d), [], NOW - 7 * DAY, NOW)
            self.assertEqual(metrics["samples"]["recoveries_open"], 1)
            self.assertAlmostEqual(metrics["mttr"], 7 * DAY, delta=1)

    def test_the_score_is_lower_than_with_no_red_at_all(self):
        self.assertLess(answer(history(8), FAST_ITEM)["score"], answer(history(0), FAST_ITEM)["score"] - 1)
        self.assertLess(answer(history(20), FAST_ITEM)["score"], answer(history(0), FAST_ITEM)["score"] - 1)

    def test_the_score_never_rises_because_one_more_day_passed_in_red(self):
        scores = [answer(history(d), FAST_ITEM)["score"] for d in (1, 3, 6, 7, 8, 10, 14, 20)]
        self.assertTrue(all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)), scores)

    def test_the_success_rate_counts_the_unfixed_failure_that_entered_the_window(self):
        metrics = collector.collect(history(8), [], NOW - 7 * DAY, NOW)
        self.assertLess(metrics["success_rate"], 1.0)
        self.assertEqual(collector.collect(history(8, 1), [], NOW - 7 * DAY, NOW)["success_rate"], 1.0)      # fixed inside the window: nothing to count

    def test_a_workflow_that_recovered_before_the_window_is_not_carried(self):
        runs = [run(1, "r", "deploy", 9, "failure"), run(2, "r", "deploy", 8, "success"), run(3, "r", "ci", 1, "success")]
        self.assertEqual(collector.carried_red(runs, NOW - 7 * DAY), {})
        self.assertEqual(collector.collect(runs, [], NOW - 7 * DAY, NOW)["samples"]["recoveries_open"], 0)

    def test_a_cancelled_run_does_not_break_the_series(self):
        runs = [run(1, "r", "deploy", 12, "failure"), run(2, "r", "deploy", 10, "failure"), run(3, "r", "deploy", 9, "cancelled")]
        self.assertEqual(collector.carried_red(runs, NOW - 7 * DAY), {("r", "deploy"): NOW - 7 * DAY})

    def test_the_window_before_counts_its_own_stretch_so_no_day_is_counted_twice(self):
        runs = history(8, 1)
        before = collector.collect(runs, [], NOW - 14 * DAY, NOW - 7 * DAY)
        now = collector.collect(runs, [], NOW - 7 * DAY, NOW)
        self.assertAlmostEqual(before["mttr"], 1 * DAY, delta=1)      # failed 8 days ago, the window ends 7 days ago: 1 day open there
        self.assertAlmostEqual(now["mttr"], 6 * DAY, delta=1)      # from the edge of the window to the fix, yesterday

    def test_the_failure_that_crosses_the_edge_weighs_85_not_100(self):
        """Worked example: 'deploy' red for 7 days (failed 8 days ago, fixed yesterday), window of 7 days."""
        result = answer(history(8, 1), FAST_ITEM)
        self.assertEqual(part(result, "recovery")["score"], 0.0)
        self.assertEqual((result["score"], result["letter"]), (85.0, "B"))
        self.assertEqual(part(result, "recovery")["samples"], 1)      # the number carries its data

    def test_the_ledger_keeps_the_last_failure_of_a_workflow_nobody_fixed(self):
        data = ledger.empty_ledger(NOW - 40 * DAY)
        ledger.update_ledger(data, history(20), [], NOW, 15, pin_days=30)
        self.assertEqual(sorted(row[1] for row in data["runs"].values() if row[4] == "deploy"), ["failure"])      # only the failure is pinned, the older green run goes

    def test_a_failure_older_than_the_pin_goes_and_a_fixed_one_does_not_stay(self):
        data = ledger.empty_ledger(NOW - 90 * DAY)
        old = [run(1, "r", "deploy", 40, "failure"), run(2, "r", "api", 20, "failure"), run(3, "r", "api", 19, "success")]
        ledger.update_ledger(data, old, [], NOW, 15, pin_days=30)
        self.assertEqual(data["runs"], {})

    def test_without_a_pin_the_behaviour_is_the_old_one(self):
        data = ledger.empty_ledger(NOW - 40 * DAY)
        ledger.update_ledger(data, history(20), [], NOW, 15, pin_days=0)
        self.assertNotIn("deploy", {row[4] for row in data["runs"].values()})


class TheOpenCollaborationItemsCount(unittest.TestCase):
    def items(self, count, days, closed_days_ago=None):
        return [{"opened": NOW - days * DAY, "closed": None if closed_days_ago is None else NOW - closed_days_ago * DAY} for _ in range(count)]

    def test_twelve_alerts_open_for_30_days_give_85_not_100(self):
        result = answer(history(0), self.items(12, 30))
        self.assertEqual(part(result, "collaboration")["score"], 0.0)
        self.assertEqual((result["score"], result["letter"]), (85.0, "B"))
        self.assertEqual(part(result, "collaboration")["samples"], 12)

    def test_the_same_twelve_solved_in_three_days_keep_a_high_mark(self):
        self.assertGreater(part(answer(history(0), self.items(12, 3, 0.01)), "collaboration")["score"], 90.0)
        self.assertGreater(answer(history(0), self.items(12, 3, 0.01))["score"], 97.0)

    def test_solving_them_never_scores_lower_than_leaving_them_open(self):
        self.assertGreaterEqual(answer(history(0), self.items(12, 30, 1))["score"], answer(history(0), self.items(12, 30))["score"])

    def test_an_item_that_just_opened_does_not_weigh_down(self):
        metrics = collector.collect_collab([{"opened": NOW - 60, "closed": None}], NOW - 7 * DAY, NOW)
        self.assertEqual((metrics["collab_resolution_time"], metrics["collab_open"]), (60.0, 1))

    def test_the_median_mixes_closed_and_open_items(self):
        items = [{"opened": NOW - 5 * DAY, "closed": NOW - 4 * DAY}, {"opened": NOW - 30 * DAY, "closed": None}, {"opened": NOW - 20 * DAY, "closed": None}]
        self.assertAlmostEqual(collector.collect_collab(items, NOW - 7 * DAY, NOW)["collab_resolution_time"], 20 * DAY, delta=1)


if __name__ == "__main__":
    unittest.main()
