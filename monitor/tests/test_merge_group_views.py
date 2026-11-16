# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Merge queue runs (event merge_group, branch gh-readonly-queue/...) in the views that rank, group and count: the health of a repository, the fleet view, the model of the runners and the quota.
The runs come from a synthetic fixture; nothing reads the network or the clock."""
import datetime
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import quota, redrule  # noqa: E402
from github_actions_monitor.health import repo_view  # noqa: E402

NOW = 1_800_000_000.0
FIXTURE = json.loads((HERE / "tests" / "fixtures" / "merge_group_runs.json").read_text(encoding="utf-8"))


def iso(hours):
    return datetime.datetime.fromtimestamp(NOW - hours * 3600, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def runs():
    return [{"repo": r["repo"], "id": r["id"], "name": r["path"], "path": r["path"], "branch": FIXTURE["queue"] if r["branch"] == "QUEUE" else r["branch"], "event": r["event"], "fork": False,
             "status": "completed", "conclusion": r["conclusion"], "started": iso(r["hours"]), "seconds": 120, "url": f"https://example.invalid/{r['id']}", "sha": "abc1234"} for r in FIXTURE["runs"]]


def by_repo():
    out = {}
    for r in runs():
        out.setdefault(r["repo"], []).append(r)
    return out


def health_views():
    redrule.configure({})
    rows, _ = redrule.red_workflows(by_repo(), {r: "main" for r in by_repo()}, now=NOW)
    failing = [{"repo": r["repo"], "workflow": r["workflow"]} for r in rows]
    return [repo_view.repo_view(name, runs(), failing, [], [], None, {"ci": "healthy"}, "alpha", NOW) for name in sorted(by_repo())]


class Health(unittest.TestCase):
    def test_only_the_repository_with_a_red_queue_is_bad_and_it_says_merge_queue(self):
        states = {v["repo"]: v["state"] for v in health_views()}
        self.assertEqual(states, {"no-queue": "ok", "queue-green": "ok", "queue-red": "bad"})
        red = next(v for v in health_views() if v["repo"] == "queue-red")
        self.assertTrue(any("merge queue" in w for w in red["ci"]["red_workflows"]))

    def test_the_team_ranking_puts_the_red_queue_first(self):
        out = repo_view.team_view(health_views())
        self.assertEqual(out["ranking"][0]["repo"], "queue-red")
        self.assertEqual(out["totals"]["bad"], 1)


class Quota(unittest.TestCase):
    def test_queue_runs_count_as_minutes_like_any_other_and_an_unknown_plan_is_not_an_error(self):
        out = quota.summary({}, runs(), [], {"queue-red", "queue-green"})      # plan unknown (the default), two private repositories
        self.assertEqual(out["plan"], "unknown")
        self.assertIsNone(out["included_minutes"])
        self.assertEqual(out["level"], "unknown")
        self.assertIsNone(out["concurrency"]["limit"])
        self.assertEqual(out["concurrency"]["level"], "unknown")
        self.assertGreater(out["billable"]["clock"], 0)      # the four runs of the private repositories were counted, queue ones included

    def test_a_known_plan_still_gives_a_level(self):
        out = quota.summary({"account": {"plan": "free"}}, runs(), [], {"queue-red"})
        self.assertIsNotNone(out["included_minutes"])
        self.assertIn(out["level"], ("ok", "warn", "alert"))


@unittest.skipUnless(importlib.util.find_spec("github_actions_monitor.health.fleet"), "the fleet view is not in this tree yet")
class Fleet(unittest.TestCase):
    def test_a_red_queue_is_in_the_bad_group_and_filters_keep_it(self):
        from github_actions_monitor.health import fleet
        out = fleet.fleet_view(health_views(), {}, group="state")
        self.assertEqual([g["key"] for g in out["groups"]][0], "bad")
        self.assertEqual([r["repo"] for r in out["rows"] if r["group"] == "bad"], ["queue-red"])
        self.assertEqual([r["repo"] for r in fleet.fleet_view(health_views(), {}, severity="bad")["rows"]], ["queue-red"])


@unittest.skipUnless(importlib.util.find_spec("github_actions_monitor.integrations.runner_model"), "the model of the runners is not in this tree yet")
class Runners(unittest.TestCase):
    def test_queue_runs_are_not_a_runaway_when_they_are_few_and_are_one_when_they_are_many(self):
        from github_actions_monitor.integrations import runner_model as rm
        cfg = rm.settings({"runners": {"model": {"enabled": True, "runaway_runs_per_hour": 5}}})
        few = runs()
        self.assertEqual(rm.runaway(few, NOW, cfg)["rows"], [])
        many = [dict(few[1], id=100 + i, started=iso(0.1 + i / 100)) for i in range(8)]      # eight runs of the queue in the last hour
        rows = rm.runaway(many, NOW, cfg)["rows"]
        self.assertEqual([(r["repo"], r["runs_last_hour"]) for r in rows], [("queue-red", 8)])
        self.assertEqual(rows[0]["events"], {"merge_group": 8})


if __name__ == "__main__":
    unittest.main()
