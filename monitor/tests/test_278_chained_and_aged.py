# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A deployment chained to the CI (`workflow_run`, `repository_dispatch`) that fails on the default branch is red, but only there and never when it comes from a fork; and the reds that aged into inactive
are counted and listed in the view of what is happening now, so they do not vanish without a trace."""
import json
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
from github_actions_monitor.data_pipeline import redrule  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


def stamp(seconds_ago):
    return datetime.fromtimestamp(NOW - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(n, seconds_ago, conclusion="failure", event="push", path="ci.yml", branch="main", fork=False, repo="demo"):
    return {"repo": repo, "id": n, "name": path, "path": path, "branch": branch, "event": event, "fork": fork, "status": "completed", "conclusion": conclusion, "started": stamp(seconds_ago), "url": f"https://x/{n}"}


class AChainedDeploymentThatFails(unittest.TestCase):
    def setUp(self):
        redrule.configure({})
        self.addCleanup(redrule.configure, {})

    def red(self, runs, config=None):
        if config:
            redrule.configure(config)
        return [item["run"]["path"] for item in redrule.classify(runs, "main", NOW)["red"]]

    def test_a_workflow_run_deployment_failing_on_main_is_red(self):
        runs = [run(1, DAY, "success"), run(2, DAY, "failure", "workflow_run", "deploy.yml")]
        self.assertEqual(self.red(runs), ["deploy.yml"])

    def test_a_repository_dispatch_failing_on_main_is_red(self):
        self.assertEqual(self.red([run(1, DAY, "failure", "repository_dispatch", "deploy.yml")]), ["deploy.yml"])

    def test_not_on_a_work_branch_not_from_a_fork_and_not_when_it_succeeded(self):
        self.assertEqual(self.red([run(1, DAY, "failure", "workflow_run", "deploy.yml", branch="feature")]), [])
        self.assertEqual(self.red([run(1, DAY, "failure", "workflow_run", "deploy.yml", fork=True)]), [])
        self.assertEqual(self.red([run(1, DAY, "success", "workflow_run", "deploy.yml")]), [])

    def test_the_setting_still_decides(self):
        runs = [run(2, DAY, "failure", "workflow_run", "deploy.yml")]
        self.assertEqual(self.red(runs, {"ci": {"red_events": ["push"]}}), [])

    def test_the_default_of_the_page_and_of_the_example_say_so(self):
        for events in (am.DEFAULTS["ci"]["red_events"], json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))["ci"]["red_events"], list(redrule.RED_EVENTS)):
            self.assertIn("workflow_run", events)
            self.assertIn("repository_dispatch", events)

    def test_the_help_of_the_setting_says_it_in_eight_languages(self):
        for lang in LANGS:
            text = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))["cfg.h.ci.red_events"]
            self.assertIn("workflow_run", text, lang)
            self.assertIn("repository_dispatch", text, lang)


class TheAgedRedsAreListed(unittest.TestCase):
    def build(self, runs, ci=None):
        saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE), dict(am.SAMPLE_INFO), am.SENTINEL.get("obj"))
        self.addCleanup(redrule.configure, {})
        redrule.configure({"ci": ci or {"red_age_days": 30}})

        def restore():
            am.RUN_CACHE.clear()
            am.RUN_CACHE.update(saved[0])
            am.LITE["on"] = saved[1]
            am.ISSUE_CACHE.update(saved[2])
            am.SAMPLE_INFO.clear()
            am.SAMPLE_INFO.update(saved[3])
            am.SENTINEL["obj"] = saved[4]
        self.addCleanup(restore)
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update({"demo": {"runs": runs, "at": NOW, "error": None}})
        am.SAMPLE_INFO.clear()
        am.LITE["on"] = True
        am.SENTINEL["obj"] = None
        am.ISSUE_CACHE.update({"items": [], "at": time.time(), "busy": False})
        config = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30, "hot_hours": 24}
        with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]), mock.patch("time.time", return_value=NOW):
            return am.build(config, ["demo"], NOW, 0, False, "")

    def test_a_red_of_45_days_is_not_in_failing_but_is_counted_and_listed(self):
        data = self.build([run(1, 45 * DAY, "failure", "workflow_dispatch", "release.yml"), run(2, DAY, "success", "push", "ci.yml")])
        self.assertEqual(data["failing"], [])
        self.assertEqual(data["figures"]["aged"], 1)
        self.assertEqual(data["figures"]["aged_days"], 30)
        self.assertEqual([(r["repo"], r["workflow"]) for r in data["aged_reds"]], [("demo", "release.yml")])

    def test_an_abandoned_workflow_that_failed_is_counted_and_listed_apart(self):
        data = self.build([run(1, 100 * DAY, "failure", "push", "old.yml"), run(2, DAY, "success", "push", "ci.yml")], {"red_ages": False, "inactive_days": 90})
        self.assertEqual(data["failing"], [])
        self.assertEqual((data["figures"]["quiet"], data["figures"]["quiet_days"], data["figures"]["aged"]), (1, 90, 0))
        self.assertEqual([(r["repo"], r["workflow"]) for r in data["quiet_reds"]], [("demo", "old.yml")])

    def test_a_fresh_red_is_not_listed_as_aged(self):
        data = self.build([run(1, 2 * DAY, "failure")])
        self.assertEqual(data["figures"]["aged"], 0)
        self.assertEqual(data["aged_reds"], [])
        self.assertEqual(len(data["failing"]), 1)

    def test_the_page_shows_the_line_and_the_eight_languages_have_the_text(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("ui.n_aged", page)
        self.assertIn("now-aged", page)
        self.assertIn("ui.n_quiet", page)
        for lang in LANGS:
            text = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))["ui.n_aged"]
            self.assertIn("{n}", text, lang)
            self.assertIn("{days}", text, lang)
            self.assertIn("{days}", json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))["ui.n_quiet"], lang)


if __name__ == "__main__":
    unittest.main()
