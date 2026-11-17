# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A red ages only when the workflow is no longer being run: a failure of 31 days with later runs that were cancelled, are in progress or wait for an approval is still red (the workflow is alive), and a
workflow whose natural period is longer than the age (a monthly schedule that always fails) is not hidden after 30 days. The exact day of the thresholds is tested too."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def stamp(days_ago):
    import datetime
    return datetime.datetime.fromtimestamp(NOW - days_ago * DAY, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(n, days, conclusion="failure", status="completed", event="push", path="ci.yml", branch="main"):
    return {"repo": "demo", "id": n, "name": path, "path": path, "branch": branch, "event": event, "fork": False, "status": status, "conclusion": conclusion, "started": stamp(days), "url": f"https://x/{n}"}


class AgingOnlyWhenTheWorkflowStopped(unittest.TestCase):
    def setUp(self):
        redrule.configure({"ci": {"red_age_days": 30, "inactive_days": 0}})
        self.addCleanup(redrule.configure, {})

    def split(self, runs):
        out = redrule.classify(runs, "main", NOW)
        return len(out["red"]), len(out["inactive"])

    def test_the_control_a_failure_of_31_days_with_nothing_after_it_ages(self):
        self.assertEqual(self.split([run(1, 31)]), (0, 1))

    def test_later_cancelled_pushes_keep_the_red(self):
        runs = [run(1, 31)] + [run(10 + d, d, "cancelled") for d in range(0, 30)]
        self.assertEqual(self.split(runs), (1, 0))

    def test_a_run_in_progress_keeps_the_red(self):
        self.assertEqual(self.split([run(1, 31), run(2, 0, None, "in_progress")]), (1, 0))

    def test_a_run_waiting_for_approval_keeps_the_red(self):
        self.assertEqual(self.split([run(1, 31), run(2, 0, None, "waiting")]), (1, 0))
        self.assertEqual(self.split([run(1, 31), run(2, 0, "action_required")]), (1, 0))

    def test_a_queued_run_keeps_the_red(self):
        self.assertEqual(self.split([run(1, 31), run(2, 0, None, "queued")]), (1, 0))

    def test_runs_of_events_that_do_not_decide_do_not_keep_it_alive(self):
        self.assertEqual(self.split([run(1, 31), run(2, 0, "failure", event="pull_request")]), (0, 1))

    def test_a_manual_workflow_nobody_launched_again_ages(self):
        self.assertEqual(self.split([run(1, 45, event="workflow_dispatch", path="release.yml")]), (0, 1))

    def test_a_monthly_schedule_that_always_fails_is_not_hidden_after_30_days(self):
        runs = [run(n, 31 + 30 * (3 - n), event="schedule", path="monthly.yml") for n in range(4)]      # the last failed 31 days ago, the others every 30 days before
        self.assertEqual(self.split(runs), (1, 0))

    def test_the_same_failure_ages_once_two_intervals_have_passed(self):
        runs = [run(n, 61 + 30 * (3 - n), event="schedule", path="monthly.yml") for n in range(4)]
        self.assertEqual(self.split(runs), (0, 1))

    def test_the_day_of_the_threshold_is_exact(self):
        self.assertEqual(self.split([run(1, 30)]), (1, 0))      # exactly 30 days: still red (the limit is exclusive)
        self.assertEqual(self.split([run(1, 30.04)]), (0, 1))
        self.assertEqual(self.split([run(1, 29.9)]), (1, 0))

    def test_the_day_of_the_inactive_threshold_is_exact(self):
        redrule.configure({"ci": {"red_ages": False, "inactive_days": 90}})
        self.assertEqual(self.split([run(1, 90)]), (1, 0))
        self.assertEqual(self.split([run(1, 90.04)]), (0, 1))


if __name__ == "__main__":
    unittest.main()
