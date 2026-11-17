# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The runs that do not come from a push of the repository itself, in the shapes measured on real public repositories: a pull request of a fork with a branch called like the default one
(action_required), an issue, a schedule, a workflow_run and a manual dispatch. They decide nothing in the sample of runs and nothing in the lookups of A2 (`exclude_pull_requests` of GitHub does not remove them)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = 1_800_000_000.0

# (repository, workflow file, event of the last run of the branch, its conclusion, is it a pull request of a fork?)
MEASURED = [
    ("zellij-org/zellij", "ci.yml", "pull_request", "action_required", True),
    ("colibri/colibri", "build.yml", "pull_request", "action_required", True),
    ("ventoy/Ventoy", "ci.yml", "pull_request", "action_required", True),
    ("microsoft/PowerToys", "triage.yml", "issues", "failure", False),
    ("zephyrproject-rtos/zephyr", "twister.yml", "workflow_run", "failure", False),
    ("libsdl-org/SDL", "nightly.yml", "schedule", "failure", False),
    ("astral-sh/uv", "release.yml", "workflow_dispatch", "failure", False),
]


def stamp(days_ago):
    import datetime
    return datetime.datetime.fromtimestamp(NOW - days_ago * 86400, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sample(case, serial=1):
    repo, workflow, event, conclusion, fork = case
    return [{"repo": repo, "id": serial, "name": workflow, "path": workflow, "branch": "main", "event": "push", "fork": False, "status": "completed", "conclusion": "success", "started": stamp(5)},
            {"repo": repo, "id": serial + 1, "name": workflow, "path": workflow, "branch": "main", "event": event, "fork": fork, "status": "completed", "conclusion": conclusion, "started": stamp(1)}]


def api_item(rid, event, conclusion, head="owner/demo", path=".github/workflows/ci.yml", days=1):
    return {"id": rid, "name": "CI", "path": path, "event": event, "conclusion": conclusion, "status": "completed", "created_at": stamp(days), "run_started_at": stamp(days),
            "html_url": f"https://github.com/owner/demo/actions/runs/{rid}", "head_sha": "abcdef1234567", "head_repository": {"full_name": head}, "repository": {"full_name": "owner/demo"}}


class SampleOfRuns(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def red(self, case):
        return redrule.red_workflows({case[0]: sample(case)}, {case[0]: "main"}, now=NOW)[0]

    def test_the_runs_that_are_not_a_push_of_the_repository_do_not_make_red_except_the_ones_that_can(self):
        for case in MEASURED:
            expected = 1 if case[2] in ("schedule", "workflow_dispatch", "workflow_run", "repository_dispatch") and not case[4] else 0      # a failing schedule or manual run is a real red of the repository until the owner narrows ci.red_events
            self.assertEqual(len(self.red(case)), expected, case)

    def test_with_only_push_in_the_events_none_of_them_is_red(self):
        redrule.configure({"ci": {"red_events": ["push"]}})
        for case in MEASURED:
            self.assertEqual(self.red(case), [], case)

    def test_the_older_green_push_is_what_the_branch_shows(self):
        redrule.configure({"ci": {"red_events": ["push"]}})
        runs = sample(MEASURED[0])
        self.assertEqual([r["id"] for r in redrule.completed_runs(runs, "main")], [1])


class LookupsOfA2(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def test_a_pull_request_of_a_fork_in_the_listing_does_not_hide_the_push(self):
        items = [api_item(9, "pull_request", "failure", head="stranger/demo"), api_item(8, "pull_request", "action_required", head="stranger/demo"), api_item(7, "push", "success", days=3)]
        found = sl.a2_from_listing(items, {"ci.yml"})
        self.assertEqual(found["ci.yml"]["databaseId"], 7)
        self.assertEqual(found["ci.yml"]["conclusion"], "success")
        self.assertEqual(found["ci.yml"]["event"], "push")

    def test_an_event_that_does_not_decide_is_skipped_also_when_the_head_is_the_same_repository(self):
        items = [api_item(9, "issue_comment", "failure"), api_item(8, "pull_request_review", "failure"), api_item(7, "push", "failure", days=3)]
        self.assertEqual(sl.a2_from_listing(items, {"ci.yml"})["ci.yml"]["databaseId"], 7)

    def test_a_workflow_with_only_runs_that_do_not_decide_stays_unresolved(self):
        items = [api_item(9, "pull_request", "failure", head="stranger/demo"), api_item(8, "issues", "failure")]
        self.assertEqual(sl.a2_from_listing(items, {"ci.yml"}), {})

    def test_the_runs_of_github_itself_are_not_workflows_of_the_repository(self):
        items = [api_item(9, "push", "failure", path="dynamic/dependabot/dependabot-updates")]
        self.assertEqual(sl.a2_from_listing(items, {"dependabot-updates"}), {})

    def test_the_one_by_one_answer_of_gh_is_filtered_by_event_too(self):
        answer = [{"databaseId": 5, "status": "completed", "conclusion": "failure", "event": "pull_request"}, {"databaseId": 4, "status": "completed", "conclusion": "success", "event": "push"}]
        self.assertEqual(sl.a2_pick_concluded(answer)["databaseId"], 4)
        self.assertEqual(sl.a2_pick_concluded([{"databaseId": 3, "status": "completed", "conclusion": "failure"}])["databaseId"], 3)      # an answer cached without an event counts as before

    def test_the_event_is_kept_and_reaches_the_rule_of_red(self):
        entry = {"at": NOW, "state": "run", "id": 3, "name": "CI", "conclusion": "failure", "status": "completed", "started": stamp(1), "url": "u", "sha": "abc", "branch": "main", "event": "schedule"}
        runs = sl.a2_resolved_runs({"demo|ci.yml": entry}, {"demo": "main"}, NOW, 3600)
        self.assertEqual(runs["demo"][0]["event"], "schedule")
        redrule.configure({"ci": {"red_events": ["push"]}})
        self.assertEqual(redrule.red_workflows(runs, {"demo": "main"}, now=NOW)[0], [])

    def test_the_default_origin_rule_agrees_with_the_function_of_the_lookups(self):
        self.assertTrue(sl.a2_origin_counts("push"))
        self.assertTrue(sl.a2_origin_counts(None))
        self.assertFalse(sl.a2_origin_counts("pull_request"))
        self.assertFalse(sl.a2_origin_counts("push", {"full_name": "a/b"}, {"full_name": "c/b"}))
        self.assertTrue(sl.a2_origin_counts("push", {"full_name": "C/B"}, {"full_name": "c/b"}))


if __name__ == "__main__":
    unittest.main()
