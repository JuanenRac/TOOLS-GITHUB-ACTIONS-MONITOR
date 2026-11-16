# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The health of the team is built from data grouped once by repository (the cost no longer grows with repositories x runs), and a saved moment that lies in the future (a clock set back) never blocks
the score, the purge or a scheduled report."""
import time
import unittest
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor
from github_actions_monitor.health import repo_view
from github_actions_monitor.reporting import report_schedule
from github_actions_monitor.scoring import ledger
from github_actions_monitor.storage import retention
from github_actions_monitor.util import clock

NOW = 1_800_000_000.0


def run(repo, i, conclusion="success"):
    return {"repo": repo, "id": i, "name": "CI", "status": "completed", "conclusion": conclusion, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 60 * i))}


class CountingList(list):
    """A list that counts how many times it is walked."""
    walks = 0

    def __iter__(self):
        CountingList.walks += 1
        return super().__iter__()


class Grouped(unittest.TestCase):
    def test_group_by_repo_keeps_order_and_leaves_out_what_has_no_repository(self):
        out = repo_view.group_by_repo([{"repo": "a", "n": 1}, {"repo": "b"}, {"repo": "a", "n": 2}, {"n": 3}, "x", None])
        self.assertEqual({k: [i.get("n") for i in v] for k, v in out.items()}, {"a": [1, 2], "b": [None]})

    def test_a_view_from_the_grouped_lists_is_the_same_as_from_all_of_them(self):
        runs = [run("a", i, "failure" if i == 3 else "success") for i in range(6)] + [run("b", i) for i in range(6)]
        failing = [{"repo": "a", "workflow": "CI"}]
        alerts = [{"repo": "b", "level": "warning", "sentinel": "x", "id": "1", "code": "c", "title": "t"}]
        for repo in ("a", "b"):
            full = repo_view.repo_view(repo, runs, failing, [], alerts, None, {"ci": "healthy"}, "", NOW)
            by = lambda items: repo_view.group_by_repo(items).get(repo, [])      # noqa: E731
            part = repo_view.repo_view(repo, by(runs), by(failing), by([]), by(alerts), None, {"ci": "healthy"}, "", NOW)
            self.assertEqual(full, part)

    def test_the_team_view_walks_the_runs_once_however_many_repositories_there_are(self):
        runs = CountingList(run(f"r{n}", i) for n in range(300) for i in range(20))
        data = {"runs": runs, "failing": [], "active": [], "repos": []}
        old = (actions_monitor.STATE.get("data"), actions_monitor.SENTINEL["registry"], actions_monitor.SENTINEL["obj"])
        self.addCleanup(lambda: (actions_monitor.STATE.update(data=old[0]), actions_monitor.SENTINEL.update(registry=old[1], obj=old[2])))
        actions_monitor.STATE["data"] = data
        actions_monitor.SENTINEL.update(registry=None, obj=None)
        CountingList.walks = 0
        with mock.patch.object(actions_monitor, "credential_alerts", return_value=[]), mock.patch.object(actions_monitor, "score_alerts", return_value=[]):
            views = actions_monitor.health_views(NOW)
        self.assertEqual(len(views), 300)
        self.assertLessEqual(CountingList.walks, 3)      # one walk to name the repositories, one to group them (it was one walk per repository: 300)

    def test_one_repository_builds_only_its_own_view(self):
        data = {"runs": [run("a", 1), run("b", 1)], "failing": [], "active": [], "repos": []}
        old = (actions_monitor.STATE.get("data"), actions_monitor.SENTINEL["registry"], actions_monitor.SENTINEL["obj"])
        self.addCleanup(lambda: (actions_monitor.STATE.update(data=old[0]), actions_monitor.SENTINEL.update(registry=old[1], obj=old[2])))
        actions_monitor.STATE["data"] = data
        actions_monitor.SENTINEL.update(registry=None, obj=None)
        with mock.patch.object(actions_monitor, "credential_alerts", return_value=[]), mock.patch.object(actions_monitor, "score_alerts", return_value=[]):
            views = actions_monitor.health_views(NOW, only="b")
            nothing = actions_monitor.health_views(NOW, only="zzz")
        self.assertEqual([v["repo"] for v in views], ["b"])
        self.assertEqual(nothing, [])


class Clock(unittest.TestCase):
    def test_a_moment_in_the_future_counts_as_now_but_a_small_difference_is_kept(self):
        self.assertEqual(clock.settle(NOW + 86400, NOW), NOW)
        self.assertEqual(clock.settle(NOW + 60, NOW), NOW + 60)
        self.assertEqual(clock.settle(NOW - 5, NOW), NOW - 5)
        self.assertFalse(clock.in_future(None, NOW))
        self.assertFalse(clock.in_future(True, NOW))

    def test_the_ledger_of_a_clock_that_was_set_back_is_due_now_not_in_days(self):
        saved = {"first_seen": NOW + 3 * 86400, "last_tick": NOW + 3 * 86400}
        led = ledger.clean_ledger(saved, NOW)
        self.assertEqual((led["first_seen"], led["last_tick"]), (NOW, 0.0))
        self.assertGreaterEqual(NOW - led["last_tick"], ledger.MIN_INTERVAL)      # the pass is due

    def test_the_ledger_of_a_normal_clock_is_untouched(self):
        led = ledger.clean_ledger({"first_seen": NOW - 500, "last_tick": NOW - 100}, NOW)
        self.assertEqual((led["first_seen"], led["last_tick"]), (NOW - 500, NOW - 100))

    def test_the_purge_is_not_blocked_by_a_last_run_in_the_future(self):
        cfg = {"enabled": True, "interval_hours": 24}
        with mock.patch.object(retention, "audit", return_value={"last_run_epoch": NOW + 3 * 86400}):
            self.assertTrue(retention.due(None, "a", cfg, NOW))      # it is not believed: the purge is due now
        with mock.patch.object(retention, "audit", return_value={"last_run_epoch": NOW - 25 * 3600}):
            self.assertTrue(retention.due(None, "a", cfg, NOW))

    def test_a_schedule_fires_at_its_named_minute_when_the_last_run_is_in_the_future(self):
        every_minute = "* * * * *"
        self.assertTrue(report_schedule.due(every_minute, NOW, NOW + 3 * 86400))
        self.assertFalse(report_schedule.due(every_minute, NOW, NOW))      # just ran this minute


if __name__ == "__main__":
    unittest.main()
