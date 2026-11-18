# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the sentinel knows of a repository (default branch, fork mark, push, pull requests) must reach EVERY repository of the list, not only the first one, once the runs are in memory (the state
of every real cycle). The cache of the tests carries a moment (`at`) different from zero, which is what a real cycle leaves."""
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc).timestamp()
DAY = 86400
CONFIG = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30, "hot_hours": 24}


def stamp(seconds_ago):
    return datetime.fromtimestamp(NOW - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(repo, n, seconds_ago, branch="main", event="push", conclusion="success"):
    return {"repo": repo, "id": n, "name": "ci", "path": "ci.yml", "branch": branch, "event": event, "fork": False, "status": "completed", "conclusion": conclusion, "started": stamp(seconds_ago)}


class Held:
    def __init__(self, info):
        self.repo_info = info


class Cycle:
    """Runs build() with the cache warm (a real `at`) and a sentinel that knows `info`; leaves the module as it was."""

    def __init__(self, runs, info):
        self.runs, self.info = runs, info

    def __enter__(self):
        self.saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE), dict(am.SAMPLE_INFO), am.SENTINEL.get("obj"))
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update({r: {"runs": v, "at": NOW, "error": None} for r, v in self.runs.items()})
        am.SAMPLE_INFO.clear()
        am.LITE["on"] = False
        am.SENTINEL["obj"] = Held(self.info)
        am.ISSUE_CACHE.update({"items": [], "at": NOW, "busy": False})      # the clock of the build is NOW: with the real time, a NOW ahead of the real clock makes the issues look stale and a background reading of "demo" leaks into later tests
        return self

    def __exit__(self, *exc):
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(self.saved[0])
        am.LITE["on"] = self.saved[1]
        am.ISSUE_CACHE.update(self.saved[2])
        am.SAMPLE_INFO.clear()
        am.SAMPLE_INFO.update(self.saved[3])
        am.SENTINEL["obj"] = self.saved[4]

    def build(self):
        with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]), mock.patch("time.time", return_value=NOW):
            return am.build(CONFIG, sorted(self.runs), NOW, 0, False, "")


def score_runs(data):
    """The runs the score pass hands to the ledger."""
    seen = {}

    def fake_tick(storage, account, config, runs, *args, **kwargs):
        seen["runs"] = runs
        return None
    with mock.patch("github_actions_monitor.scoring.ledger.tick", fake_tick), mock.patch("github_actions_monitor.storage.runtime.process_storage", return_value=(None, "acc")):
        am.score_tick(CONFIG, dict(data, loading="", offline={}))
    return seen.get("runs")


class EveryRepositoryKeepsWhatTheSentinelKnows(unittest.TestCase):
    def test_the_branch_the_fork_mark_the_push_and_the_prs_reach_all_the_repositories(self):
        names = ["alpha", "beta", "gamma", "delta"]
        runs = {r: [run(r, 1, 3600)] for r in names}
        info = {r: {"branch": "develop", "fork": True, "pushed": "2026-11-01T00:00:00Z", "prs": [1, 2]} for r in names}
        with Cycle(runs, info) as cycle:
            meta = am.repo_meta(names, CONFIG)
            data = cycle.build()
        for r in names:
            self.assertEqual((meta[r]["branch"], meta[r]["fork"], meta[r]["prs"], meta[r]["pushed"]), ("develop", True, 2, "2026-11-01T00:00:00Z"), r)
            self.assertIn("coverage", meta[r], r)
        self.assertEqual(data["repo_meta"]["delta"]["branch"], "develop")

    def test_the_forks_without_a_ci_of_their_own_are_all_counted_and_none_enters_the_score(self):
        forks = [f"fork-{n:02d}" for n in range(30)]
        runs = {r: [run(r, 1, 290 * DAY, event="schedule", conclusion="failure")] for r in forks}
        runs["own"] = [run("own", 1, 3600)]
        info = {r: {"fork": True, "branch": "main"} for r in forks}
        info["own"] = {"fork": False, "branch": "main"}
        with Cycle(runs, info) as cycle:
            data = cycle.build()
            handed = score_runs(data)
        self.assertEqual(data["figures"]["forks_idle"], 30)
        self.assertEqual({r["repo"] for r in handed}, {"own"})

    def test_the_score_leaves_out_every_idle_fork_even_when_the_page_shows_only_two_hundred(self):
        forks = [f"fork-{n:03d}" for n in range(300)]
        runs = {r: [run(r, 1, 290 * DAY, event="schedule", conclusion="failure")] for r in forks}
        runs["own"] = [run("own", 1, 3600)]
        info = {r: {"fork": True, "branch": "main"} for r in forks}
        with Cycle(runs, info) as cycle:
            data = cycle.build()
            handed = score_runs(data)
        self.assertEqual(len(data["forks_idle"]), 200)
        self.assertEqual(len(data["forks_idle_all"]), 300)
        self.assertEqual({r["repo"] for r in handed}, {"own"})

    def test_a_red_ci_on_a_default_branch_that_is_not_main_is_failing(self):
        names = ["aaa", "svc"]
        runs = {"aaa": [run("aaa", 1, 3600)],
                "svc": [run("svc", 2, 7200, branch="develop", conclusion="failure"), run("svc", 1, 90000, branch="main")]}
        info = {"aaa": {"branch": "main"}, "svc": {"branch": "develop"}}
        with Cycle(runs, info) as cycle:
            data = cycle.build()
        self.assertEqual([(f["repo"], f["branch"]) for f in data["failing"]], [("svc", "develop")])


if __name__ == "__main__":
    unittest.main()
