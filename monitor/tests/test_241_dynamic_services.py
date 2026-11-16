# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The workflows GitHub makes for itself (`dynamic/...`: Dependabot updates, the dependency graph, the default CodeQL, the review and the agent of Copilot), in the shapes measured on public repositories.
They have no file, so they are not red CI, not an abandoned workflow and not a workflow the owner could enable: a failing Dependabot update is a signal of its own, the rest is information."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = 1_800_000_000.0

# (repository, path of the workflow as the API gives it, name, event) of the failing services found on real repositories
MEASURED = [
    ("sumatrapdfreader/sumatrapdf", "dynamic/dependabot/dependabot-updates", "Dependabot Updates", "dynamic"),
    ("hashcat/hashcat", "dynamic/dependabot/dependabot-updates", "Dependabot Updates", "dynamic"),
    ("alacritty/alacritty", "dynamic/copilot-pull-request-reviewer/copilot-pull-request-reviewer", "Copilot code review", "dynamic"),
    ("firecracker-microvm/firecracker", "dynamic/copilot-pull-request-reviewer/copilot-pull-request-reviewer", "Copilot code review", "dynamic"),
    ("sharkdp/bat", "dynamic/copilot-swe-agent/copilot", "Copilot coding agent", "dynamic"),
    ("curl/curl", "dynamic/github-code-scanning/codeql", "CodeQL", "dynamic"),
    ("nushell/nushell", "dynamic/dependabot/update-graph", "Dependency Graph", "dynamic"),
]


def stamp(days_ago):
    import datetime
    return datetime.datetime.fromtimestamp(NOW - days_ago * 86400, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_run(repo, path, name, event, rid=1, conclusion="failure", days=1):
    return {"id": rid, "name": name, "path": path, "event": event, "head_branch": "main", "conclusion": conclusion, "status": "completed", "created_at": stamp(days), "run_started_at": stamp(days),
            "html_url": f"https://github.com/{repo}/actions/runs/{rid}", "head_sha": "abcdef1234567", "run_number": rid, "actor": {"login": "github", "type": "Bot"},
            "head_repository": {"full_name": repo}, "repository": {"full_name": repo}}


class ServicesOfGitHub(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def parsed(self, case, **extra):
        repo, path, name, event = case
        return actions_monitor.parse_runs(repo.split("/")[1], {"workflow_runs": [api_run(repo, path, name, event, **extra)]})

    def test_the_whole_path_is_remembered_even_though_only_the_file_name_is_kept(self):
        for case in MEASURED:
            run = self.parsed(case)[0]
            self.assertTrue(run["dynamic"], case)
            self.assertTrue(redrule.is_dynamic(run), case)

    def test_a_run_of_a_real_workflow_is_not_marked(self):
        run = actions_monitor.parse_runs("demo", {"workflow_runs": [api_run("o/demo", ".github/workflows/ci.yml", "CI", "push")]})[0]
        self.assertNotIn("dynamic", run)
        self.assertFalse(redrule.is_dynamic(run))

    def test_the_service_is_named_from_the_path(self):
        names = [redrule.service_name(path, name) for _repo, path, name, _event in MEASURED]
        self.assertEqual(names, ["dependabot", "dependabot", "copilot", "copilot", "copilot", "codeql", "graph"])
        self.assertEqual(redrule.service_name("dynamic/other/x"), "other")

    def test_a_failing_service_is_never_a_red_of_the_branch_even_when_the_event_is_one_that_decides(self):
        for case in MEASURED:
            for event in ("dynamic", "push", "schedule"):
                run = self.parsed((case[0], case[1], case[2], event))[0]
                self.assertEqual(redrule.red_workflows({"demo": [run]}, {"demo": "main"}, now=NOW)[0], [], (case, event))

    def test_a_failing_dependabot_update_is_a_warning_and_the_others_are_information(self):
        runs = [self.parsed(case, rid=n)[0] for n, case in enumerate(MEASURED, 1)]
        rows = redrule.service_rows(runs, NOW)
        self.assertEqual(len(rows), 7)
        self.assertEqual({r["level"] for r in rows if r["service"] == "dependabot"}, {"warning"})
        self.assertEqual({r["level"] for r in rows if r["service"] != "dependabot"}, {"info"})
        self.assertEqual([r["level"] for r in rows][:2], ["warning", "warning"])      # the warnings come first

    def test_a_service_that_recovered_or_went_quiet_is_not_listed(self):
        case = MEASURED[0]
        fail, ok = self.parsed(case, rid=1, days=3)[0], self.parsed(case, rid=2, conclusion="success", days=1)[0]
        self.assertEqual(redrule.service_rows([fail, ok], NOW), [])
        redrule.configure({"ci": {"inactive_days": 30}})
        self.assertEqual(redrule.service_rows([self.parsed(case, days=45)[0]], NOW), [])
        self.assertEqual(len(redrule.service_rows([self.parsed(case, days=5)[0]], NOW)), 1)

    def test_cancelled_and_waiting_runs_of_a_service_say_nothing(self):
        case = MEASURED[0]
        self.assertEqual(redrule.service_rows([self.parsed(case, conclusion="cancelled")[0], self.parsed(case, rid=2, conclusion="action_required")[0]], NOW), [])

    def test_the_states_carry_the_services_and_a_service_is_not_inactive(self):
        runs = [self.parsed(MEASURED[0], days=200)[0], self.parsed(MEASURED[2], days=1)[0]]
        held = redrule.states({"demo": runs}, {"demo": "main"}, now=NOW)
        self.assertEqual(held["inactive"], [])
        self.assertEqual([r["service"] for r in held["services"]], ["copilot"] if redrule.POLICY["inactive_days"] else ["dependabot", "copilot"])

    def test_the_header_counts_a_run_of_a_service_neither_as_queued_nor_as_running(self):
        queued = self.parsed(MEASURED[0], conclusion=None)[0]
        queued["status"] = "queued"
        figures = actions_monitor.header_figures([queued], [], [], now=NOW)
        self.assertEqual(figures["queued"], 0)


class WorkflowsOfTheRepository(unittest.TestCase):
    """The list of workflows of a repository holds the ones GitHub makes for itself with a path `dynamic/...`: they are not disabled by anybody and are not a schedule that stopped."""

    def sentinel(self, workflows):
        s = sl.Sentinel.__new__(sl.Sentinel)
        s.config, s.perms = {}, {}
        s.cfg = {"hygiene": {"ruleset_mode": "off", "community_fallback": False}}
        s.repo_info = {"R": {"branch": "main"}}

        def gh(*args, **kw):
            path = args[1]
            if path.endswith("/actions/permissions"):
                return {"allowed_actions": "selected", "sha_pinning_required": True}
            if "/actions/workflows" in path:
                return {"total_count": len(workflows), "workflows": workflows}
            return {}
        s._gh = gh
        return s

    def test_workflows_made_by_github_are_not_counted_as_disabled(self):
        workflows = [{"name": "CI", "path": ".github/workflows/ci.yml", "state": "disabled_manually"}, {"name": "Nightly", "path": ".github/workflows/nightly.yml", "state": "disabled_inactivity"},
                     {"name": "Dependabot Updates", "path": "dynamic/dependabot/dependabot-updates", "state": "disabled_manually"},
                     {"name": "Copilot code review", "path": "dynamic/copilot-pull-request-reviewer/copilot-pull-request-reviewer", "state": "disabled_inactivity"}]
        _repo, res = self.sentinel(workflows)._fetch_perms("R")
        self.assertEqual(res["wf_manual"], ["CI"])
        self.assertEqual(res["wf_disabled"], ["Nightly"])


if __name__ == "__main__":
    unittest.main()
