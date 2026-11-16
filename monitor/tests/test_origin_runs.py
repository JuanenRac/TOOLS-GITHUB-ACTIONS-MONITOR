# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Which runs may make a branch red: the event, the origin (a fork), the merge queue, the runs that wait for an approval, abandoned workflows and maintenance branches. Synthetic runs only."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import signstate  # noqa: E402

NOW = 1_800_000_000.0      # a fixed "now" (seconds): the tests never read the clock
DAY = 86400


def stamp(days_ago, hour=0):
    import datetime
    return datetime.datetime.fromtimestamp(NOW - days_ago * DAY + hour * 3600, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(n, conclusion="failure", branch="main", event="push", path="ci.yml", days=1, fork=False, status="completed", **extra):
    return {"repo": "demo", "id": n, "name": path, "path": path, "branch": branch, "event": event, "fork": fork, "status": status, "conclusion": conclusion,
            "started": stamp(days, n % 20), "url": f"https://example.invalid/runs/{n}", "sha": "abc1234", **extra}


class OriginRules(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def red(self, runs, branch="main"):
        return redrule.red_workflows({"demo": runs}, {"demo": branch}, now=NOW)[0]

    def test_push_failure_on_main_is_red(self):
        self.assertEqual(len(self.red([run(1)])), 1)

    def test_pull_request_from_a_fork_called_main_is_not_red(self):
        # the head branch of a fork can have any name, also the one of the default branch of this repository
        for name in ("main", "master", "dev"):
            runs = [run(1, "success", branch=name), run(2, "failure", branch=name, event="pull_request", fork=True, days=0, path="ci.yml")]
            self.assertEqual(self.red(runs, name), [], name)

    def test_pull_request_event_never_decides_but_an_unknown_event_does(self):
        self.assertEqual(self.red([run(1, "failure", event="pull_request")]), [])
        self.assertEqual(len(self.red([run(1, "failure", event=None)])), 1)

    def test_fork_runs_can_be_counted_when_asked(self):
        redrule.configure({"ci": {"count_fork_runs": True, "red_events": ["push", "pull_request"]}})
        self.assertEqual(len(self.red([run(1, "failure", event="pull_request", fork=True)])), 1)

    def test_red_events_setting_is_respected(self):
        redrule.configure({"ci": {"red_events": ["push"]}})
        self.assertEqual(self.red([run(1, "failure", event="schedule")]), [])
        redrule.configure({"ci": {"red_events": ["schedule"]}})
        self.assertEqual(len(self.red([run(1, "failure", event="schedule")])), 1)

    def test_action_required_is_not_red_and_is_awaiting(self):
        runs = [run(1, "success", days=3), run(2, "action_required", event="pull_request", fork=True, days=0, branch="main")]
        self.assertEqual(self.red(runs), [])
        waiting = redrule.awaiting_runs(runs, NOW)
        self.assertEqual([w["id"] for w in waiting], [2])
        self.assertTrue(waiting[0]["fork"])
        # not even from the own branch: it needs a person, it did not fail
        self.assertEqual(self.red([run(3, "action_required", event="push")]), [])
        self.assertEqual(len(redrule.awaiting_runs([run(3, "action_required", event="push")], NOW)), 1)

    def test_waiting_status_is_awaiting_not_queued(self):
        job = run(4, None, status="waiting", event="push")
        self.assertTrue(redrule.is_awaiting(job))
        figures = actions_monitor.header_figures([job], [job], [], now=NOW)
        self.assertEqual(figures["queued"], 0)

    def test_old_awaiting_runs_are_dropped(self):
        self.assertEqual(redrule.awaiting_runs([run(5, "action_required", days=60)], NOW), [])

    def test_neutral_does_not_hide_or_make_red(self):
        runs = [run(1, "failure", days=2), run(2, "neutral", days=1)]
        self.assertEqual(len(self.red(runs)), 1)
        self.assertEqual(self.red([run(3, "neutral")]), [])

    def test_merge_group_failure_is_its_own_lane(self):
        queue = "gh-readonly-queue/main/pr-12-0123456789abcdef"
        runs = [run(1, "success", days=3), run(2, "failure", branch=queue, event="merge_group", days=0, path="ci.yml")]
        rows = self.red(runs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["origin"], "merge_queue")
        self.assertIn("merge queue", rows[0]["workflow"])
        # a later green run of the queue clears it
        runs.append(run(3, "success", branch=queue, event="merge_group", days=0, path="ci.yml"))
        runs[-1]["started"] = stamp(0, 23)
        self.assertEqual(self.red(runs), [])
        # the queue of ANOTHER branch is not watched
        self.assertEqual(self.red([run(4, "failure", branch="gh-readonly-queue/dev/pr-1-abc", event="merge_group")]), [])

    def test_merge_queue_failure_does_not_hide_green_main_and_main_red_stays_separate(self):
        queue = "gh-readonly-queue/main/pr-1-abc"
        runs = [run(1, "failure", days=1), run(2, "success", branch=queue, event="merge_group", days=0)]
        rows = self.red(runs)
        self.assertEqual([r["origin"] for r in rows], ["branch"])

    def test_rerun_attempt_fields_are_kept_per_run(self):
        # the series is by start time of the (latest) attempt: an old red is not resurrected by a re-run that succeeded
        runs = [run(1, "failure", days=5), run(2, "success", days=1)]
        self.assertEqual(self.red(runs), [])

    def test_abandoned_workflow_is_inactive_not_red(self):
        old = [run(1, "failure", days=400, path="legacy.yml")]
        redrule.configure({"ci": {"inactive_days": 90}})
        self.assertEqual(self.red(old), [])
        held = redrule.states({"demo": old}, {"demo": "main"}, now=NOW)
        self.assertEqual(len(held["inactive"]), 1)
        redrule.configure({"ci": {"inactive_days": 0}})
        self.assertEqual(len(self.red(old)), 1)
        redrule.configure({"ci": {"inactive_days": 30}})
        self.assertEqual(self.red([run(1, "failure", days=29, path="legacy.yml")]).__len__(), 1)
        self.assertEqual(self.red([run(1, "failure", days=31, path="legacy.yml")]), [])

    def test_triage_workflows_are_automation_and_do_not_count(self):
        redrule.configure({"ci": {"red_events": ["push", "issue_comment"]}})
        triage = [run(1, "failure", event="issue_comment", path="triage.yml")]
        self.assertEqual(self.red(triage), [])
        redrule.configure({"ci": {"red_events": ["push", "issue_comment"], "automation_counts": True}})
        self.assertEqual(self.red(triage)[0]["kind"], "automation")

    def test_workflow_kinds(self):
        self.assertEqual(redrule.workflow_kind({"push", "pull_request"}), "build")
        self.assertEqual(redrule.workflow_kind({"issues", "issue_comment"}), "automation")
        self.assertEqual(redrule.workflow_kind({"release"}), "release")
        self.assertEqual(redrule.workflow_kind({"schedule", "workflow_dispatch"}), "service")
        self.assertEqual(redrule.workflow_kind({"workflow_run"}), "build")

    def test_maintenance_branches_are_watched_only_when_configured(self):
        runs = [run(1, "failure", branch="release-1.2", path="ci.yml")]
        self.assertEqual(self.red(runs), [])
        redrule.configure({"ci": {"extra_branches": ["release-*"]}})
        rows = self.red(runs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["origin"], "maintenance")
        self.assertIn("release-1.2", rows[0]["workflow"])
        # the default branch stays separate: green main does not hide the red maintenance branch
        self.assertEqual(len(self.red(runs + [run(2, "success", days=0)])), 1)

    def test_invalid_configuration_keeps_conservative_defaults(self):
        redrule.configure({"ci": {"red_events": "push", "inactive_days": -3, "extra_branches": "x", "count_fork_runs": "yes"}})
        self.assertEqual(redrule.POLICY["events"], redrule.RED_EVENTS)
        self.assertEqual(redrule.POLICY["inactive_days"], redrule.DEFAULT_INACTIVE_DAYS)
        self.assertEqual(redrule.POLICY["branches"], ())
        self.assertFalse(redrule.POLICY["fork_runs"])

    def test_unresolved_failures_use_the_same_rule(self):
        runs = [run(1, "failure", event="pull_request", fork=True), run(2, "failure", days=0, path="b.yml"), run(3, "action_required", days=0, path="c.yml")]
        self.assertEqual([r["id"] for r in actions_monitor.unresolved_failures(runs, {"demo": "main"})], [2])

    def test_green_main_is_not_made_by_a_fork(self):
        runs = [run(1, "success", event="pull_request", fork=True), run(2, "success", branch="main", event="push", days=2)]
        self.assertEqual([r["id"] for r in signstate.completed_runs(runs, "main")], [2])

    def test_guess_default_branch_ignores_forks(self):
        runs = [run(i, "success", branch="feature", fork=True) for i in range(10, 16)] + [run(1, "success", branch="trunk")]
        self.assertEqual(redrule.guess_default_branch(runs), "trunk")

    def test_fork_detection_from_the_api_record(self):
        self.assertTrue(actions_monitor.is_fork_run({"head_repository": {"full_name": "someone/demo"}, "repository": {"full_name": "owner/demo"}}))
        self.assertFalse(actions_monitor.is_fork_run({"head_repository": {"full_name": "Owner/Demo"}, "repository": {"full_name": "owner/demo"}}))
        self.assertFalse(actions_monitor.is_fork_run({}))

    def test_settings_are_in_the_schema_with_texts_in_eight_languages(self):
        import json
        for key in ("ci.red_events", "ci.count_fork_runs", "ci.automation_counts", "ci.inactive_days", "ci.extra_branches"):
            self.assertIn(key, settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ci.red_events", "ci.count_fork_runs", "ci.automation_counts", "ci.inactive_days", "ci.extra_branches"):
                self.assertTrue(texts.get("cfg.f." + key) and texts.get("cfg.h." + key), (lang, key))
            for key in ("ui.cfg_b_origin", "ui.n_awaiting", "ci.lane_queue", "ci.lane_branch"):
                self.assertTrue(texts.get(key), (lang, key))

if __name__ == "__main__":
    unittest.main()
