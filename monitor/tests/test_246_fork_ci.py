# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A fork is judged (hygiene, lint of workflows, score) only when it has a CI of its own in the last 90 days; the others are counted apart. The fixture is the account measured as a collector of forks
(722 forks in 727 repositories, three with runs, all of them almost a year old and made by the schedule they inherited) plus forks that are maintained (a push of their own a few days ago)."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import fork_ci  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc).timestamp()
DAY = 86400


def stamp(days_ago):
    return datetime.fromtimestamp(NOW - days_ago * DAY, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(repo, n, days, event="push", conclusion="success", **extra):
    return {"repo": repo, "id": n, "name": "ci", "path": "ci.yml", "branch": "main", "event": event, "fork": False, "status": "completed", "conclusion": conclusion, "started": stamp(days), **extra}


class Rule(unittest.TestCase):
    cfg = {"enabled": True, "days": 90}

    def idle(self, runs_by_repo, full=(), cfg=None):
        return fork_ci.idle_forks(sorted(runs_by_repo), runs_by_repo, set(full), NOW, cfg or self.cfg)

    def test_the_forks_of_the_collector_have_no_ci_of_their_own(self):
        runs = {"gitbutler": [run("gitbutler", n, 290, "schedule", "failure") for n in range(42)],
                "hyperswitch-control-center": [run("hyperswitch-control-center", n, 291, "schedule", "failure") for n in range(27)],
                "hyperswitch": [run("hyperswitch", 1, 330), run("hyperswitch", 2, 330, conclusion="cancelled")]}
        runs.update({f"fork-{n:03d}": [] for n in range(719)})
        idle = self.idle(runs)
        self.assertEqual(len(idle), 722)

    def test_a_maintained_fork_stays_in(self):
        runs = {"pivy": [run("pivy", 1, 5), run("pivy", 2, 40, "schedule")], "coin": [run("coin", 1, 80, "pull_request")], "old": [run("old", 1, 200)]}
        self.assertEqual(self.idle(runs), ["old"])

    def test_a_copied_schedule_never_counts_but_a_manual_run_does(self):
        self.assertEqual(self.idle({"a": [run("a", 1, 2, "schedule")]}), ["a"])
        self.assertEqual(self.idle({"a": [run("a", 1, 2, "workflow_dispatch")]}), [])
        self.assertEqual(self.idle({"a": [run("a", 1, 2, "merge_group")]}), [])

    def test_the_pull_request_of_another_fork_and_the_services_of_github_are_not_the_work_of_the_owner(self):
        self.assertEqual(self.idle({"a": [run("a", 1, 2, "pull_request", fork=True)]}), ["a"])
        self.assertEqual(self.idle({"a": [run("a", 1, 2, "dynamic", dynamic=True)]}), ["a"])

    def test_a_full_list_that_does_not_reach_back_far_enough_cannot_tell(self):
        runs = {"a": [run("a", n, 3, "schedule") for n in range(20)]}      # twenty runs of a cron of the last days, a run of its own may hide further back
        self.assertEqual(self.idle(runs, full={"a"}), [])
        self.assertEqual(self.idle(runs, full=()), ["a"])
        reaches = {"a": [run("a", 1, 3, "schedule"), run("a", 2, 120, "schedule")]}      # the list reaches back beyond the window: there is no run of its own for sure
        self.assertEqual(self.idle(reaches, full={"a"}), ["a"])

    def test_the_switch_and_the_days_are_settings(self):
        runs = {"a": [run("a", 1, 100)]}
        self.assertEqual(self.idle(runs), ["a"])
        self.assertEqual(self.idle(runs, cfg=fork_ci.settings({"ci": {"fork_own_ci_days": 120}})), [])
        self.assertEqual(self.idle(runs, cfg=fork_ci.settings({"ci": {"forks_need_own_ci": False}})), [])
        for bad in (0, -1, 400, "90", True, None):
            self.assertEqual(fork_ci.settings({"ci": {"fork_own_ci_days": bad}})["days"], 90, bad)
        self.assertTrue(fork_ci.settings({"ci": {"forks_need_own_ci": "no"}})["enabled"])

    def test_the_shared_rule_is_replaced_by_the_configuration(self):
        try:
            fork_ci.configure({"ci": {"forks_need_own_ci": False}})
            self.assertEqual(fork_ci.idle_forks(["a"], {"a": []}, (), NOW), [])
        finally:
            fork_ci.configure({})
        self.assertEqual(fork_ci.idle_forks(["a"], {"a": []}, (), NOW), ["a"])


class TheSentinel(unittest.TestCase):
    def snapshot(self, forks, lint=None):
        repo = {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": False, "files": {}, "license": None}
        info = {name: dict(repo, fork=name.startswith("fork")) for name in ("fork-idle", "fork-active", "own")}
        runs = {"fork-idle": [run("fork-idle", 1, 290, "schedule", "failure")], "fork-active": [run("fork-active", 1, 4)], "own": []}
        inp = {"now": datetime.fromtimestamp(NOW, timezone.utc), "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": sorted(info), "eco": {r: "main" for r in info}, "repo_info": info, "alerts": {},
               "perms": {r: {"sha_pinning_required": False, "allowed_actions": "all", "wf_disabled": [], "at": 1} for r in info}, "runs": runs,
               "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "", "audits": None,
               "lint": lint}
        return sl.compute_snapshot(inp)

    def test_an_idle_fork_is_not_judged_and_is_counted_apart(self):
        s = self.snapshot(None)
        rows = {r["repo"]: r for r in s["a6"]["rows"]}
        self.assertEqual(rows["fork-idle"]["problems"], [])
        self.assertEqual(rows["fork-idle"]["skipped"], "fork")
        self.assertTrue(rows["fork-active"]["problems"], "a fork with a CI of its own is judged like any repository")
        self.assertTrue(rows["own"]["problems"])
        self.assertEqual(s["a6"]["forks_idle"], ["fork-idle"])

    def test_the_lint_leaves_the_idle_fork_out(self):
        finding = {"rule": "unpinned", "severity": "warn", "file": "ci.yml", "line": 1, "text": "x"}
        lint = {"by_repo": {"fork-idle": [dict(finding)], "fork-active": [dict(finding)]}, "summary": {}, "in_report": True, "coverage": None}
        s = self.snapshot(None, lint)
        self.assertEqual(sorted({row["repo"] for row in s["lint"]["rows"]}), ["fork-active"])
        self.assertEqual(s["lint"]["summary"]["repos"], 1)

    def test_a_repository_that_is_not_marked_as_a_fork_is_never_skipped(self):
        s = self.snapshot(None)
        self.assertNotIn("skipped", {r["repo"]: r for r in s["a6"]["rows"]}["own"])

    def test_the_listing_asks_for_the_fork_flag_and_keeps_it(self):
        self.assertIn("isFork", sl.repo_query(["README.md"]))
        self.assertTrue(sl.parse_repo_node({"name": "R", "isFork": True}, [])["fork"])
        self.assertFalse(sl.parse_repo_node({"name": "R"}, [])["fork"])


class TheMonitor(unittest.TestCase):
    def test_the_header_counts_the_idle_forks_and_the_score_does_not_see_their_runs(self):
        import time
        from unittest import mock
        runs = {"fork-idle": [run("fork-idle", 1, 290, "schedule", "failure")], "fork-active": [run("fork-active", 1, 4)], "own": [run("own", 1, 1)]}
        cache = {r: {"runs": v, "at": 0, "error": None} for r, v in runs.items()}
        saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE), dict(am.SAMPLE_INFO), am.SENTINEL.get("obj"))

        class Held:
            repo_info = {"fork-idle": {"fork": True, "branch": "main"}, "fork-active": {"fork": True, "branch": "main"}, "own": {"fork": False, "branch": "main"}}
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(cache)
        am.SAMPLE_INFO.clear()
        am.LITE["on"] = False
        am.SENTINEL["obj"] = Held()
        am.ISSUE_CACHE.update({"items": [], "at": NOW, "busy": False})      # the clock of the build is NOW: with the real time, a NOW ahead of the real clock makes the issues look stale and a background reading of "demo" leaks into later tests
        config = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30, "hot_hours": 24}
        try:
            with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]), mock.patch("time.time", return_value=NOW):
                data = am.build(config, sorted(runs), NOW, 0, False, "")
        finally:
            am.RUN_CACHE.clear()
            am.RUN_CACHE.update(saved[0])
            am.LITE["on"] = saved[1]
            am.ISSUE_CACHE.update(saved[2])
            am.SAMPLE_INFO.clear()
            am.SAMPLE_INFO.update(saved[3])
            am.SENTINEL["obj"] = saved[4]
        self.assertEqual(data["figures"]["forks_idle"], 1)
        self.assertEqual(data["forks_idle"], ["fork-idle"])
        self.assertTrue(data["repo_meta"]["fork-idle"]["fork"])
        self.assertFalse(data["repo_meta"]["own"]["fork"])


class TheSettings(unittest.TestCase):
    def test_they_are_in_the_schema_with_texts_in_eight_languages(self):
        import json
        for key in ("ci.forks_need_own_ci", "ci.fork_own_ci_days"):
            self.assertIn(key, settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ci.forks_need_own_ci", "ci.fork_own_ci_days"):
                self.assertTrue(texts.get("cfg.f." + key) and texts.get("cfg.h." + key), (lang, key))
            self.assertTrue(texts.get("ui.a6_forks_idle"), lang)
        self.assertIn("ui.a6_forks_idle", (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
