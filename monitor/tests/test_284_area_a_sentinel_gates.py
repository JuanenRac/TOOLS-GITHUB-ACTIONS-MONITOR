# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The reads of the sentinel stop when the hourly budget or the allowance is spent: the jobs of a red run, the pages of the listing of the batch way, the remote linter and the second look at the rules of
a branch (only with the effective mode) never go on in spite of it."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_275_area_a_sentinel_quota as t275  # noqa: E402
from github_actions_monitor.data_pipeline import causes  # noqa: E402


def spent(account):
    account.sentinel.cfg["budget_per_hour"] = 0


class TheJobsOfARedRun(unittest.TestCase):
    def policy(self):
        patcher = mock.patch.dict(causes.POLICY, {"failed_jobs": dict(causes.POLICY["failed_jobs"], enabled=True, max_per_cycle=4)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_they_are_not_read_with_the_budget_of_the_hour_spent_nor_with_the_allowance_low(self):
        self.policy()
        account = t275.Account(self, 2, lambda *a: {"jobs": []})
        s = account.sentinel
        s.last_snap = {"a2": {"red": [{"repo": "repo-000", "run_id": 11}]}}
        spent(account)
        s._failed_jobs_tick()
        self.assertEqual(account.calls, [], "budget spent")
        s.cfg["budget_per_hour"] = 600
        s.ctx["data_fn"] = lambda: {"rate": {"remaining": 5, "limit": 5000}}
        s._failed_jobs_tick()
        self.assertEqual(account.calls, [], "allowance low")
        s.ctx["data_fn"] = lambda: {"rate": {"remaining": 5000, "limit": 5000}}
        s._failed_jobs_tick()
        self.assertEqual(len(account.calls), 1)


class ThePagesOfTheListingOfTheBatchWay(unittest.TestCase):
    def test_they_never_go_beyond_the_room_of_the_turn(self):
        def full_page(*args):
            return {"workflow_runs": [{"id": n, "name": "CI", "path": f".github/workflows/w{n}.yml@refs/heads/main", "status": "completed", "conclusion": "success", "created_at": "2026-11-05T08:00:00Z",
                                       "run_started_at": "2026-11-05T08:00:00Z", "html_url": "u", "head_sha": "deadbeefcafe"} for n in range(100)]}
        account = t275.Account(self, 1, full_page)
        s = account.sentinel
        s.cfg["a2_resolve_batch_pages"] = 3
        spent_calls, found = s._a2_resolve_batch("repo-000", ["release.yml", "manual.yml"], "main", 1, 1000.0)
        self.assertEqual((spent_calls, len([c for c in account.calls if c[0] == "api"])), (1, 1), "one page for a room of one")
        account.calls.clear()
        spent_calls, _ = s._a2_resolve_batch("repo-000", ["release.yml", "manual.yml"], "main", 3, 1000.0)
        self.assertEqual(spent_calls, 3)


class TheRemoteLinter(unittest.TestCase):
    def test_it_waits_when_the_budget_is_spent(self):
        account = t275.Account(self, 3, lambda *a: {})
        s = account.sentinel
        s.config["lint"] = {"enabled": True, "source": "auto"}
        spent(account)
        with mock.patch.object(s, "_clone_repos", return_value=[]):
            self.assertFalse(s._lint_remote_tick())
        self.assertEqual(account.calls, [])


class TheRulesOfABranch(unittest.TestCase):
    def test_the_two_extra_requests_are_made_only_with_the_effective_mode(self):
        for mode, extra in (("effective", True), ("name", False), ("off", False)):
            asked = []

            def answer(*args, asked=asked):
                asked.append(args[1] if len(args) > 1 else "")
                return {"allowed_actions": "all", "workflows": [], "protected": False}
            account = t275.Account(self, 1, answer)
            s = account.sentinel
            s.cfg["hygiene"] = dict(s.cfg["hygiene"], ruleset_mode=mode)
            s._fetch_perms("repo-000")
            self.assertEqual(any("/rules/branches/" in a or "/branches/" in a for a in asked), extra, mode)


if __name__ == "__main__":
    unittest.main()
