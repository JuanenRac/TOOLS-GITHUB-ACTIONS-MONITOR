# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The health of a repository and of the team: what makes a repository bad, warn, ok or unknown, how the ranking and the filters work, that a sentinel that did not look is said, and the two routes."""
import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.health import repo_view  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402

NOW = 1_800_000_000.0


def run(repo, ago=3600, conclusion="success", name="ci"):
    return {"repo": repo, "name": name, "status": "completed", "conclusion": conclusion, "started": NOW - ago, "seconds": 60}


def alert(repo, level="warning", sentinel="collab", code="collab.issue.stale", muted=False):
    return {"id": f"{code}:{repo}", "code": code, "level": level, "sentinel": sentinel, "repo": repo, "title": "t", "created_at": "2026-01-01T00:00:00Z", **({"muted_until": NOW + 99} if muted else {})}


def view(repo, runs=(), failing=(), active=(), alerts=(), ready=None, sources=None, eco="alpha"):
    return repo_view.repo_view(repo, list(runs), list(failing), list(active), list(alerts), ready, sources or {"ci": "healthy"}, eco, NOW)


class State(unittest.TestCase):
    def test_a_quiet_repository_with_runs_is_ok(self):
        v = view("a/x", [run("a/x")])
        self.assertEqual((v["state"], v["risk"]), ("ok", 0))
        self.assertEqual((v["ci"]["runs_24h"], v["ci"]["successes_24h"], v["ci"]["success_rate_24h"]), (1, 1, 1.0))

    def test_nothing_to_judge_by_is_unknown_never_ok(self):
        v = view("a/x")
        self.assertEqual((v["state"], v["activity"]["last_run_at"], v["ci"]["success_rate_24h"]), ("unknown", None, None))

    def test_a_red_workflow_is_bad(self):
        v = view("a/x", [run("a/x", conclusion="failure")], failing=[{"repo": "a/x", "workflow": "ci"}, {"repo": "b/y", "workflow": "z"}])
        self.assertEqual((v["state"], v["ci"]["red_workflows"], v["ci"]["failures_24h"], v["risk"]), ("bad", ["ci"], 1, 30))

    def test_an_error_or_a_critical_alert_is_bad_and_a_warning_is_warn(self):
        self.assertEqual(view("a/x", [run("a/x")], alerts=[alert("a/x", "critical", "security", "security.secret")])["state"], "bad")
        self.assertEqual(view("a/x", [run("a/x")], alerts=[alert("a/x", "error")])["state"], "bad")
        self.assertEqual(view("a/x", [run("a/x")], alerts=[alert("a/x", "warning")])["state"], "warn")
        self.assertEqual(view("a/x", [run("a/x")], alerts=[alert("a/x", "info")])["state"], "ok")

    def test_a_stuck_run_is_a_warning(self):
        v = view("a/x", [run("a/x")], active=[{"repo": "a/x", "stuck": True}, {"repo": "a/x", "stuck": False}])
        self.assertEqual((v["state"], v["ci"]["stuck_runs"], v["risk"]), ("warn", 1, 10))

    def test_a_silenced_alert_does_not_count_and_the_others_of_other_repositories_neither(self):
        v = view("a/x", [run("a/x")], alerts=[alert("a/x", "error", muted=True), alert("b/y", "error")])
        self.assertEqual((v["state"], v["alerts"]["total"]), ("ok", 0))

    def test_the_alerts_are_counted_by_sentinel_and_level_and_listed_worst_first(self):
        v = view("a/x", [run("a/x")], alerts=[alert("a/x", "warning"), alert("a/x", "critical", "security", "security.secret"), alert("a/x", "error", "security", "security.dependabot")])
        self.assertEqual(v["alerts"]["by_sentinel"], {"collab": 1, "security": 2})
        self.assertEqual([a["level"] for a in v["alerts"]["items"]], ["critical", "error", "warning"])
        self.assertEqual(v["risk"], 25 + 10 + 3)

    def test_the_runs_older_than_a_day_are_activity_and_not_the_ci_of_today(self):
        v = view("a/x", [run("a/x", ago=3 * 86400, conclusion="failure"), run("a/x", ago=2 * 86400)])
        self.assertEqual((v["ci"]["runs_24h"], v["ci"]["failures_24h"], v["activity"]["runs_7d"], v["activity"]["idle_days"]), (0, 0, 2, 2.0))
        self.assertEqual(v["state"], "ok")

    def test_a_sentinel_that_did_not_look_is_said(self):
        v = view("a/x", [run("a/x")], sources={"ci": "healthy", "collab": "off", "security": "degraded"})
        self.assertEqual(v["not_fully_seen"], ["security"])
        self.assertEqual(v["sources"]["collab"], "off")

    def test_the_readiness_row_travels_with_the_repository(self):
        v = view("a/x", [run("a/x")], ready={"entries": 6, "next": "cut the version"})
        self.assertEqual(v["readiness"]["next"], "cut the version")
        self.assertIsNone(view("a/x", [run("a/x")])["readiness"])

    def test_unreadable_entries_are_ignored(self):
        v = view("a/x", [None, "x", {"repo": "a/x", "started": "nonsense", "status": "completed"}, run("a/x")], alerts=[None, "x"])
        self.assertEqual(v["state"], "ok")


class Team(unittest.TestCase):
    def views(self):
        return [view("a/ok", [run("a/ok")]), view("a/red", [run("a/red", conclusion="failure")], failing=[{"repo": "a/red", "workflow": "ci"}]),
                view("b/warn", [run("b/warn")], alerts=[alert("b/warn", "warning")], eco="beta"), view("b/unknown", eco="beta")]

    def test_the_ranking_puts_what_needs_a_person_first(self):
        out = repo_view.team_view(self.views())
        self.assertEqual([r["repo"] for r in out["ranking"]], ["a/red", "b/warn", "a/ok", "b/unknown"])
        self.assertEqual(out["totals"], {"unknown": 1, "ok": 1, "warn": 1, "bad": 1})
        self.assertEqual((out["all"], out["shown"], out["truncated"]), (4, 4, False))

    def test_the_totals_by_ecosystem_and_by_sentinel(self):
        out = repo_view.team_view(self.views())
        self.assertEqual(out["by_ecosystem"]["beta"], {"repos": 2, "bad": 0, "warn": 1, "ok": 0, "unknown": 1, "risk": 3})
        self.assertEqual(out["alerts"]["by_sentinel"], {"collab": 1})

    def test_the_filters_narrow_the_list_and_the_totals(self):
        v = self.views()
        self.assertEqual([r["repo"] for r in repo_view.team_view(v, ecosystem="beta")["ranking"]], ["b/warn", "b/unknown"])
        self.assertEqual([r["repo"] for r in repo_view.team_view(v, severity="warn")["ranking"]], ["a/red", "b/warn"])
        self.assertEqual([r["repo"] for r in repo_view.team_view(v, severity="bad")["ranking"]], ["a/red"])
        self.assertEqual([r["repo"] for r in repo_view.team_view(v, text="UNK")["ranking"]], ["b/unknown"])
        narrowed = repo_view.team_view(v, ecosystem="beta", severity="warn")
        self.assertEqual((narrowed["all"], narrowed["shown"], narrowed["totals"]["warn"], narrowed["totals"]["bad"]), (4, 1, 1, 0))

    def test_the_label_filter_matches_the_name_shown_for_the_ecosystem(self):
        v = self.views()
        for item in v:
            item["ecosystem_label"] = "Team " + item["ecosystem"].upper()
        self.assertEqual({r["repo"] for r in repo_view.team_view(v, label="team beta")["ranking"]}, {"b/warn", "b/unknown"})

    def test_a_filter_that_matches_nothing_is_an_empty_ranking_not_an_error(self):
        out = repo_view.team_view(self.views(), text="zzz")
        self.assertEqual((out["ranking"], out["shown"], out["totals"]), ([], 0, {"unknown": 0, "ok": 0, "warn": 0, "bad": 0}))

    def test_the_list_is_cut_at_the_limit_and_says_so(self):
        many = [view(f"a/r{i}", [run(f"a/r{i}")]) for i in range(10)]
        out = repo_view.team_view(many, limit=3)
        self.assertEqual((len(out["ranking"]), out["truncated"], out["shown"]), (3, True, 10))


class Routes(unittest.TestCase):
    def test_the_two_routes_are_served_read_only_and_lite_does_not_have_them(self):
        source = inspect.getsource(actions_monitor.Handler)
        self.assertIn('path == "/api/team/health"', source)
        self.assertIn('path.startswith("/api/repos/") and path.endswith("/health")', source)
        self.assertTrue(any(p in actions_monitor.LITE_PATHS for p in ("/api/team", "/api/repos")))
        self.assertEqual(auth.required_role("GET", "/api/team/health"), "viewer")
        self.assertEqual(auth.required_role("GET", "/api/repos/o/r/health"), "viewer")

    def test_the_views_come_from_what_the_monitor_holds_and_never_from_github(self):
        data = {"runs": [run("a/x"), run("a/y", conclusion="failure")], "failing": [{"repo": "a/y", "workflow": "ci"}], "active": [], "repos": ["a/z"]}
        old = (actions_monitor.STATE.get("data"), actions_monitor.SENTINEL["registry"], actions_monitor.SENTINEL["obj"])
        self.addCleanup(lambda: (actions_monitor.STATE.update(data=old[0]), actions_monitor.SENTINEL.update(registry=old[1], obj=old[2])))
        actions_monitor.STATE["data"] = data
        actions_monitor.SENTINEL.update(registry=None, obj=None)
        with mock.patch.object(actions_monitor, "credential_alerts", return_value=[]), mock.patch.object(actions_monitor, "score_alerts", return_value=[]):
            views = actions_monitor.health_views(NOW)
        self.assertEqual([v["repo"] for v in views], ["a/x", "a/y", "a/z"])
        states = {v["repo"]: v["state"] for v in views}
        self.assertEqual(states, {"a/x": "ok", "a/y": "bad", "a/z": "unknown"})
        self.assertTrue(all("ecosystem_label" in v for v in views))


if __name__ == "__main__":
    unittest.main()
