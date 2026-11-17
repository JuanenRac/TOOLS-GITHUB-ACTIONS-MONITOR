# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The health of the team and of the fleet is counted over EVERY run of the cycle, not over the 600 newest runs of the account that the page receives: with 250 active repositories the other 215 would say
'unknown'. The data come out of build(), the way a real cycle produces them (the load test writes the runs straight into the state, a shape build() never gives)."""
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
from github_actions_monitor.health import repo_view  # noqa: E402

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc).timestamp()
CONFIG = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30, "hot_hours": 24}


def stamp(seconds_ago):
    return datetime.fromtimestamp(NOW - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(repo, n, seconds_ago, conclusion="success"):
    return {"repo": repo, "id": n, "name": "ci", "path": "ci.yml", "branch": "main", "event": "push", "fork": False, "status": "completed", "conclusion": conclusion, "started": stamp(seconds_ago)}


class TheHealthSeesEveryRepository(unittest.TestCase):
    def cycle(self, count, per_repo):
        names = [f"repo-{n:04d}" for n in range(count)]
        runs = {r: [run(r, n * 100 + i, 60 * i + n) for i in range(per_repo)] for n, r in enumerate(names)}
        saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE), dict(am.SAMPLE_INFO), am.SENTINEL.get("obj"), am.SENTINEL["registry"], am.STATE.get("data"), dict(getattr(am, "RUN_SUMMARY", {})))

        def restore():
            am.RUN_CACHE.clear()
            am.RUN_CACHE.update(saved[0])
            am.LITE["on"] = saved[1]
            am.ISSUE_CACHE.update(saved[2])
            am.SAMPLE_INFO.clear()
            am.SAMPLE_INFO.update(saved[3])
            am.SENTINEL["obj"], am.SENTINEL["registry"] = saved[4], saved[5]
            am.STATE["data"] = saved[6]
            getattr(am, "RUN_SUMMARY", {}).update(saved[7])
        self.addCleanup(restore)
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update({r: {"runs": v, "at": NOW, "error": None} for r, v in runs.items()})
        am.SAMPLE_INFO.clear()
        am.LITE["on"] = False
        am.SENTINEL["obj"], am.SENTINEL["registry"] = None, None
        am.ISSUE_CACHE.update({"items": [], "at": time.time(), "busy": False})
        with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]), mock.patch("time.time", return_value=NOW):
            data = am.build(CONFIG, names, NOW, 0, False, "")
        am.STATE["data"] = data
        with mock.patch.object(am, "credential_alerts", return_value=[]), mock.patch.object(am, "score_alerts", return_value=[]), mock.patch.object(am, "runner_alerts", return_value=[]):
            views = am.health_views(NOW)
        return data, views

    def test_250_active_repositories_are_all_known(self):
        data, views = self.cycle(250, 20)
        self.assertEqual(data["runs_total"], 5000)
        self.assertEqual(len(data["runs"]), 600)
        team = repo_view.team_view(views)
        self.assertEqual(team["totals"]["unknown"], 0)
        self.assertEqual(team["totals"]["ok"], 250)
        self.assertTrue(all(v["activity"]["last_run_at"] for v in views))
        self.assertTrue(all(v["ci"]["runs_24h"] == 20 for v in views))

    def test_the_counts_do_not_depend_on_the_cut(self):
        _, views = self.cycle(60, 20)
        self.assertEqual({v["ci"]["runs_24h"] for v in views}, {20})
        self.assertEqual({v["activity"]["runs_7d"] for v in views}, {20})

    def test_the_summary_counts_failures_and_the_seven_days(self):
        runs = [run("a", 1, 100, "failure"), run("a", 2, 200), run("a", 3, 3 * 86400), run("a", 4, 9 * 86400), {"repo": "a", "id": 5, "started": stamp(50), "status": "in_progress"}]
        row = repo_view.summarize_runs(runs, NOW)["a"]
        self.assertEqual((row["runs_24h"], row["successes_24h"], row["failures_24h"], row["runs_7d"]), (2, 1, 1, 4))


if __name__ == "__main__":
    unittest.main()
