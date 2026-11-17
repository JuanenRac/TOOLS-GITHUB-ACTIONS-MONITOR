# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A repository that never ran anything, or has not for months, is neither green nor red: dormant / inactive, counted apart. The fixture is the account measured as a collector of forks: 727 repositories,
722 of them forks, 724 without a single run in their whole history, and three forks whose last run is nearly a year old."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import activity, redrule  # noqa: E402
from github_actions_monitor.scoring import ledger  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def stamp(days_ago):
    import datetime
    return datetime.datetime.fromtimestamp(NOW - days_ago * DAY, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(repo, n, days, path="ci.yml", event="push", conclusion="success", **extra):
    return {"repo": repo, "id": n, "name": path, "path": path, "branch": "main", "event": event, "fork": False, "status": "completed", "conclusion": conclusion, "started": stamp(days), **extra}


def collector_of_forks():
    """727 repositories: 5 own ones and 722 forks; 724 with total_count 0; three with runs whose newest one is ~290 days old."""
    repos = [f"fork-{n:03d}" for n in range(722)] + ["own-1", "own-2", "own-3", "own-4", "own-5"]
    runs = {"gitbutler": [run("gitbutler", n, 290 + n % 3, "publish.yaml", "schedule", "failure") for n in range(42)],
            "hyperswitch-control-center": [run("hyperswitch-control-center", n, 291, "nightly.yaml", "schedule", "failure") for n in range(27)],
            "hyperswitch": [run("hyperswitch", n, 330, "ci.yaml") for n in range(2)]}
    repos = [r for r in repos if r not in runs][:724] + list(runs)
    totals = {r: 0 for r in repos}
    totals.update({"gitbutler": 42, "hyperswitch-control-center": 27, "hyperswitch": 2})
    return repos, runs, totals


class States(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def test_a_repository_that_never_ran_is_dormant_not_green(self):
        self.assertEqual(activity.state_of([], 0, False, NOW, 90), "dormant")

    def test_a_repository_with_a_recent_run_is_active(self):
        self.assertEqual(activity.state_of([run("r", 1, 3)], 1, False, NOW, 90), "active")

    def test_an_old_last_run_is_inactive_and_the_limit_is_the_one_of_the_workflows(self):
        runs = [run("r", 1, 120)]
        self.assertEqual(activity.state_of(runs, 1, False, NOW, 90), "inactive")
        self.assertEqual(activity.state_of(runs, 1, False, NOW, 365), "active")
        self.assertEqual(activity.state_of(runs, 1, False, NOW, 0), "active")      # 0 turns the limit off

    def test_what_cannot_be_told_is_unknown_never_dormant(self):
        self.assertEqual(activity.state_of([], None, False, NOW, 90), "unknown")      # the read gave no total
        self.assertEqual(activity.state_of([], 5, False, NOW, 90), "unknown")      # runs exist but the sample holds none
        self.assertEqual(activity.state_of([], 0, True, NOW, 90), "unknown")      # the read failed

    def test_the_runs_github_makes_for_itself_are_not_runs_of_the_repository(self):
        service = run("r", 1, 2, "dependabot-updates", "dynamic", dynamic=True)
        self.assertEqual(activity.state_of([service], 1, False, NOW, 90), "dormant")      # the list is complete and holds nothing of its own
        self.assertEqual(activity.state_of([service], 400, False, NOW, 90), "unknown")      # the list is cut: it says nothing
        self.assertEqual(activity.state_of([service, run("r", 2, 100)], 2, False, NOW, 90), "inactive")


class TheCollectorOfForks(unittest.TestCase):
    def setUp(self):
        redrule.configure({"ci": {"inactive_days": 90}})

    def tearDown(self):
        redrule.configure({})

    def test_the_account_is_counted_apart_and_nothing_is_green_or_red(self):
        repos, runs, totals = collector_of_forks()
        self.assertEqual(len(repos), 727)
        view = activity.summarize(repos, runs, totals, {}, NOW, activity.settings({}))
        self.assertEqual((view["counts"]["dormant"], view["counts"]["inactive"], view["counts"]["active"], view["counts"]["unknown"]), (724, 3, 0, 0))
        self.assertEqual(sorted(view["inactive"]), ["gitbutler", "hyperswitch", "hyperswitch-control-center"])
        self.assertEqual(len(view["dormant"]), activity.SAMPLE_LIMIT)      # the names are cut, the counts are not
        # nothing of this makes a red: the old failures of the schedule are not red either (the workflow has been quiet for months)
        rows, _approx = redrule.red_workflows(runs, {r: "main" for r in runs}, now=NOW)
        self.assertEqual(rows, [])

    def test_the_switch_turns_the_counting_off(self):
        repos, runs, totals = collector_of_forks()
        cfg = activity.settings({"ci": {"dormant_repos": False}})
        view = activity.summarize(repos, runs, totals, {}, NOW, cfg)
        self.assertEqual((view["enabled"], view["dormant"], view["inactive"]), (False, [], []))
        self.assertIsNone(ledger.activity_counts(view))

    def test_a_repository_that_failed_to_read_is_not_dormant(self):
        view = activity.summarize(["a", "b"], {}, {"a": 0, "b": 0}, {"b": "HTTP 500"}, NOW, activity.settings({}))
        self.assertEqual((view["dormant"], view["unknown"]), (["a"], 1))


class TheMonitorAndTheScore(unittest.TestCase):
    def test_the_figures_of_the_header_carry_the_counts(self):
        import time
        from unittest import mock
        repos, runs, totals = collector_of_forks()
        repos = repos[:10] + ["gitbutler"]
        cache = {r: {"runs": runs.get(r, []), "at": 0, "error": None} for r in repos}
        saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE), dict(am.SAMPLE_INFO))
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(cache)
        am.SAMPLE_INFO.clear()
        am.SAMPLE_INFO.update({r: {"asked": 20, "total": totals[r], "probe": 0} for r in repos})
        am.LITE["on"] = False
        am.ISSUE_CACHE.update({"items": [], "at": NOW, "busy": False})      # the clock of the build is NOW: with the real time, a NOW ahead of the real clock makes the issues look stale and a background reading of "demo" leaks into later tests
        config = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30}
        try:
            with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]), mock.patch("time.time", return_value=NOW):
                redrule.configure({"ci": {"inactive_days": 90}})
                data = am.build(config, repos, NOW, 0, False, "")
        finally:
            redrule.configure({})
            am.RUN_CACHE.clear()
            am.RUN_CACHE.update(saved[0])
            am.LITE["on"] = saved[1]
            am.ISSUE_CACHE.update(saved[2])
            am.SAMPLE_INFO.clear()
            am.SAMPLE_INFO.update(saved[3])
        self.assertEqual((data["figures"]["dormant"], data["figures"]["inactive_repos"]), (10, 1))
        self.assertEqual(data["activity"]["counts"], {"active": 0, "dormant": 10, "inactive": 1, "unknown": 0})

    def test_the_snapshot_of_the_score_carries_the_counts_apart(self):
        view = {"enabled": True, "counts": {"active": 3, "dormant": 724, "inactive": 3, "unknown": 1}}
        self.assertEqual(ledger.activity_counts(view), {"active": 3, "dormant": 724, "inactive": 3, "unknown": 1})
        for bad in (None, {}, {"enabled": True}, {"enabled": False, "counts": {}}, "x"):
            self.assertIsNone(ledger.activity_counts(bad), bad)
        snap = ledger.make_snapshot(ledger.empty_ledger(NOW - 3600), __import__("github_actions_monitor.scoring.engine", fromlist=["x"]).settings({}), NOW, "acc", None, view)
        self.assertEqual(snap["activity"]["dormant"], 724)
        self.assertNotIn("activity", ledger.make_snapshot(ledger.empty_ledger(NOW - 3600), __import__("github_actions_monitor.scoring.engine", fromlist=["x"]).settings({}), NOW, "acc"))


class TheSetting(unittest.TestCase):
    def test_it_is_in_the_schema_with_texts_in_eight_languages(self):
        import json
        self.assertIn("ci.dormant_repos", settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(texts.get("cfg.f.ci.dormant_repos") and texts.get("cfg.h.ci.dormant_repos") and texts.get("ui.score_activity"), lang)
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("ui.score_activity", page)


if __name__ == "__main__":
    unittest.main()
