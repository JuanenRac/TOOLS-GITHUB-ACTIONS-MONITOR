# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The reads that go to GitHub stay inside their budget: the plan of a cycle counts requests (the second look at the default branch costs one more), the duration of a re-run is a request of the hour, and
the answer of /api/runners is kept for a few minutes instead of reading the runners of up to thirty repositories on every request."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_216_load as t216  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import sampling  # noqa: E402
from test_200_contract import Served  # noqa: E402


class ThePlanCountsRequests(unittest.TestCase):
    def test_a_repository_that_costs_two_takes_two_places_of_the_budget(self):
        todo = [("r%02d" % n, 5) for n in range(30)]
        kept, dropped = sampling.plan(todo, set(), 10, 0, lambda item: 2)
        self.assertEqual((len(kept), len(dropped)), (5, 25))
        kept, _ = sampling.plan(todo, set(), 10, 0)
        self.assertEqual(len(kept), 10, "without a price every repository costs one, as before")

    def test_the_reserve_for_the_red_ones_is_counted_in_requests_too(self):
        todo = [("r%02d" % n, 5) for n in range(30)]
        kept, _ = sampling.plan(todo, {"r28", "r29"}, 10, 10, lambda item: 2)
        self.assertEqual(sorted(r for r, _n in kept), ["r28"], "a tenth of the budget (one request) is reserved: one red repository of price 2 fits the first place")


class TheCycleStaysInsideTheBudget(unittest.TestCase):
    def test_with_the_second_look_on_a_budget_of_100_requests_makes_about_100_requests(self):
        fake = t216.FakeGitHub()
        config = {"mode": "full", "cold_runs_per_repo": 5, "runs_per_repo": 20, "max_workers": 8, "refresh_seconds": 45, "cold_refresh_seconds": 600, "hot_hours": 3,
                  "sampling": {"default_branch_probe": True, "api_budget_per_hour": 100}}
        am.RUN_CACHE.clear()
        self.addCleanup(am.RUN_CACHE.clear)
        with mock.patch.object(am, "gh_read", fake.read), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), mock.patch.object(am, "tuned", lambda c, k, d=None: c[k]), \
                mock.patch.object(am, "BUDGET", sampling.Budget()), mock.patch.object(am, "TIMING", {"on": False, "known": {}, "budget": 3}):
            am.refresh_runs(t216.repo_names(), config)
        self.assertLessEqual(len(fake.reads), 110, "the budget of 100 requests an hour is the number of requests, not of repositories")

    def test_the_duration_of_a_rerun_is_a_request_of_the_hour_and_is_not_made_with_the_budget_spent(self):
        reads = []

        def read(path, **kw):
            reads.append(path)
            return {"run_duration_ms": 90000}
        budget = sampling.Budget()
        run = {"id": 7, "run_attempt": 2}
        with mock.patch.object(am, "gh_read", read), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), mock.patch.object(am, "BUDGET", budget), \
                mock.patch.object(am, "TIMING", {"on": True, "known": {}, "budget": 3, "limit": 2}):
            self.assertEqual(am.rerun_seconds("r", run), 90)
            self.assertEqual(budget.used(), 1)
            am.rerun_seconds("r", {"id": 8, "run_attempt": 2})
            self.assertIsNone(am.rerun_seconds("r", {"id": 9, "run_attempt": 2}), "the budget of the hour (2) is spent")
        self.assertEqual(len(reads), 2)


class TheRunnersAreReadOncePerFiveMinutes(unittest.TestCase):
    def test_twenty_requests_cost_one_reading(self):
        served = Served(self, lite=False)
        seen = {"payload": None, "at": 0.0}
        patcher = mock.patch.object(am, "RUNNERS_SEEN", seen)
        patcher.start()
        self.addCleanup(patcher.stop)
        from github_actions_monitor.integrations import runners
        with mock.patch.object(runners, "payload", return_value={"enabled": True, "runners": []}) as read:
            codes = [served.raw("GET", "/api/runners")[0] for _ in range(20)]
            self.assertEqual(set(codes), {200})
            self.assertEqual(read.call_count, 1)
            seen["at"] -= am.RUNNERS_MEMORY_SECONDS + 1
            served.raw("GET", "/api/runners")
            self.assertEqual(read.call_count, 2, "after five minutes it reads again")


if __name__ == "__main__":
    unittest.main()
