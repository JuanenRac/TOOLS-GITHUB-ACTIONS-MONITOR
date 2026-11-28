# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The collaboration views and the actions behind them, against a made-up GitHub: nothing is written without the actions on, allowed and confirmed; the only automatic action is one re-run; what cannot
be read is named, never clean. Invented names, no real calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import redrule, run_dismiss  # noqa: E402
from github_actions_monitor.families import actions as family  # noqa: E402
from github_actions_monitor.families.actions import actions_engine as engine, actions_views as views  # noqa: E402
from github_actions_monitor.families.posture.posture_checks import Unread  # noqa: E402
from github_actions_monitor.integrations import ghactions  # noqa: E402

NOW = 1_800_000_000.0
RECENT = "2027-01-15T07:00:00Z"
ON = {"enabled": True, "queued_hours": 1, "stuck_hours": 1, "dismissed_alerts": True, "inactive_workflows": True, "dismiss_allowed": ["boss"]}


def run(ident, **extra):
    return {"repo": "app", "id": ident, "name": "CI", "path": "ci.yml", "branch": "main", "status": "completed", "conclusion": "success", "started": RECENT, "attempt": 1, "fork": False, "event": "push", "url": "", "actor": "a", **extra}


def get_from(answers):
    def get(endpoint):
        key = endpoint.partition("?")[0]
        state = "dismissed " if "state=dismissed" in endpoint else ""
        if state + key not in answers:
            raise Unread("missing")
        if isinstance(answers[state + key], str):
            raise Unread(answers[state + key])
        return answers[state + key]
    return get


class Views(unittest.TestCase):
    def test_a_person_and_a_machine_are_two_kinds_of_waiting(self):
        out = views.waiting([run(1, status="waiting", conclusion=None), run(2, conclusion="action_required", fork=True), run(3, conclusion="action_required"), run(4, status="queued", conclusion=None), run(5)])
        self.assertEqual([r["kind"] for r in out["person"]], ["environment", "fork", "check"])
        self.assertEqual([r["run"] for r in out["machine"]], [4])

    def test_the_newest_run_of_each_lane_decides(self):
        rows = views.lanes([run(1, conclusion="failure", started="2027-01-01T00:00:00Z"), run(2, started="2027-01-02T00:00:00Z"), run(3, branch="dev", conclusion="failure")])
        self.assertEqual([(r["run"], r["red"]) for r in rows], [(3, True), (2, False)])

    def test_a_pull_request_not_known_is_never_mergeable(self):
        pull = {"number": 1, "head": {"ref": "dependabot/npm/x"}, "user": {"login": "x"}}
        self.assertEqual(views.bot_of(pull, ["dependabot[bot]"], ["dependabot/*"], []), "branch")
        for detail, checks, group in (({"mergeable_state": "clean"}, [], "mergeable"), ({"mergeable_state": "clean"}, None, "unknown"), ({"mergeable_state": "behind"}, [], "pending_rebase"),
                                      ({"mergeable_state": "clean"}, [{"conclusion": "failure"}], "needs_action"), ({}, [], "unknown")):
            self.assertEqual(views.pull_row("app", pull, detail, checks, "branch")["group"], group, detail)

    def test_proposals_cover_the_policy_the_queue_and_the_bots(self):
        runs = [run(1, status="queued", conclusion=None, started="2027-01-14T00:00:00Z"), run(2, status="in_progress", conclusion=None, branch="old/x", started="2027-01-14T00:00:00Z")]
        policy = views.policy_matches(runs, ["app:CI:old/*"])
        pulls = [{"repo": "app", "number": 7, "bot": "author", "failing": 1, "behind": False, "draft": False, "title": "t"}]
        found = {(p["action"], p["number"]) for p in views.proposals(runs, pulls, policy, [{"repo": "app", "id": 9, "name": "n"}], dict(ON), NOW)}
        self.assertEqual(found, {("close_pr", 7), ("cancel", 1), ("force_cancel", 2), ("cancel", 2), ("enable_workflow", 9)})

    def test_the_values_of_a_manual_run_are_checked_against_its_inputs(self):
        inputs = [{"name": "env", "type": "choice", "options": ["a", "b"], "required": True, "default": None}, {"name": "dry", "type": "boolean", "required": False, "default": None}]
        self.assertEqual(views.dispatch_values(inputs, {"env": "a", "dry": "TRUE"}), ({"env": "a", "dry": "true"}, ""))
        self.assertEqual(views.dispatch_values(inputs, {})[1], "env: required")
        self.assertEqual(views.dispatch_values(inputs, {"env": "z"})[1], "env: choice")
        self.assertEqual(views.dispatch_values(inputs, {"env": "a", "other": "1"})[1], "other: unknown")


class Reads(unittest.TestCase):
    def test_what_is_refused_is_named_and_a_dismissal_by_a_stranger_is_flagged(self):
        answers = {"repos/me/app/pulls": [], "repos/me/app/dependabot/alerts": "forbidden",
                   "dismissed repos/me/app/dependabot/alerts": [{"number": 3, "dismissed_at": RECENT, "dismissed_by": {"login": "stranger"}, "dismissed_reason": "no_bandwidth"}],
                   "dismissed repos/me/app/code-scanning/alerts": [], "repos/me/app/actions/workflows": {"workflows": [{"id": 5, "name": "nightly", "state": "disabled_inactivity"}]}}
        out = engine.read_repo(get_from(answers), "me", "app", engine.settings({"teamwork": ON}), NOW)
        self.assertEqual(out["unread"], {"vulnerabilities": "forbidden"})
        self.assertIsNone(out["vulnerable"])
        self.assertEqual([d["authorized"] for d in out["dismissals"]], [False])
        self.assertEqual(out["workflows"][0]["id"], 5)

    def test_nothing_is_read_while_off(self):
        self.assertEqual(engine.refresh({}, "me", ["app"], get=lambda e: self.fail("read")), 0)

    def test_the_oldest_alert_and_its_age(self):
        row = views.vulnerabilities("app", [{"created_at": "2027-01-05T08:00:00Z", "html_url": "u", "security_advisory": {"severity": "high"}}, {"created_at": RECENT, "security_advisory": {"severity": "critical"}}], NOW)
        self.assertEqual((row["critical"], row["high"], row["url"]), (1, 1, "u"))
        self.assertGreaterEqual(row["oldest_days"], 9)


class Writes(unittest.TestCase):
    def config(self, **gh):
        return {"teamwork": {"enabled": True, "auto_rerun": True}, "github_actions": {"enabled": True, "allowed": ["rerun_failed", "dispatch"], "writer_lock": False, "preflight": False, "require_reason": True, **gh}}

    def test_only_the_two_actions_that_need_them_take_fields_from_a_caller(self):
        item, why = ghactions.plan(self.config(), "me", "dispatch", "app", 5, reason="because", operator="me")
        self.assertEqual((item, why), (None, "fields"))
        item, why = ghactions.plan(self.config(), "me", "dispatch", "app", 5, reason="because", operator="me", fields={"ref": "main", "inputs[a]": "1"})
        self.assertEqual((why, item["fields"]["ref"], item["endpoint"]), ("ok", "main", "repos/me/app/actions/workflows/5/dispatches"))
        item, _why = ghactions.plan(self.config(), "me", "rerun_failed", "app", 5, reason="because", operator="me", fields={"evil": "1"})
        self.assertEqual(item["fields"], {})
        self.assertEqual(ghactions.plan(self.config(), "me", "approve_fork", "app", 5, reason="because", operator="me")[1], "not_allowed")

    def test_numbers_of_a_list_are_sent_as_numbers(self):
        sent = []

        def run_gh(args, timeout=0):
            sent.append(args)
            return (0, '{"status": "waiting"}', "")
        config = self.config(allowed=["approve_deployment"])
        item, _why = ghactions.plan(config, "me", "approve_deployment", "app", 5, reason="because", operator="me", fields={"environment_ids[]": [7, 8], "state": "approved"})
        with mock.patch.object(ghactions, "log"):
            self.assertEqual(ghactions.execute(config, item["id"], run_gh)["status"], "done")
        self.assertEqual(sent[-1][-6:], ["-F", "environment_ids[]=7", "-F", "environment_ids[]=8", "-f", "state=approved"])

    def test_one_automatic_rerun_and_never_a_second(self):
        calls = []

        def run_gh(args, timeout=0):
            calls.append(args)
            return (0, '{"status": "completed", "conclusion": "timed_out"}', "")
        runs = [run(11, conclusion="timed_out"), run(12, conclusion="failure"), run(13, conclusion="timed_out", fork=True)]
        with mock.patch.object(engine, "state_file", return_value=Path(tempfile.mkdtemp()) / "s.json"), mock.patch.object(ghactions, "log"):
            self.assertEqual(engine.auto_rerun(self.config(), "me", runs, run_gh, NOW), [11])
            self.assertEqual(engine.auto_rerun(self.config(), "me", runs, run_gh, NOW), [])
            self.assertEqual(engine.auto_rerun(self.config(enabled=False), "me", [run(14, conclusion="timed_out")], run_gh, NOW), [])
            done = engine.load()["rerun"]
        self.assertEqual(sum(1 for a in calls if "-X" in a), 1)
        self.assertEqual(views.failed_again([run(11, conclusion="failure", attempt=2)], done)[0]["run"], 11)

    def test_with_the_switch_off_nothing_runs_by_itself(self):
        config = self.config()
        config["teamwork"]["auto_rerun"] = False
        self.assertEqual(engine.auto_rerun(config, "me", [run(1, conclusion="timed_out")], lambda *a: self.fail("call"), NOW), [])


class Dismissal(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(run_dismiss, "_path", return_value=Path(tempfile.mkdtemp()) / "d.json")
        patch.start()
        self.addCleanup(patch.stop)

    def test_only_that_run_is_set_aside_and_it_can_be_restored(self):
        self.assertEqual(run_dismiss.dismiss("app", 5, "me", "", 30)[1], "no_reason")
        mark, why = run_dismiss.dismiss("app", 5, "me", "known", 30)
        self.assertEqual(why, "")
        self.assertEqual(run_dismiss.lookup(run(5))["until"], mark["until"])
        self.assertIsNone(run_dismiss.lookup(run(6)))
        reds = redrule.classify([run(5, conclusion="failure")], "main", NOW)
        self.assertEqual((len(reds["red"]), len(reds["expected"])), (0, 1))
        self.assertTrue(run_dismiss.restore("app", 5))
        self.assertEqual(len(redrule.classify([run(5, conclusion="failure")], "main", NOW)["red"]), 1)


class RunnerHooks(unittest.TestCase):
    def test_a_hook_is_recorded_only_when_asked(self):
        env = {"GITHUB_REPOSITORY": "me/app", "GITHUB_RUN_ID": "4", "GITHUB_JOB": "build", "RUNNER_NAME": "box"}
        with mock.patch.object(engine, "state_file", return_value=Path(tempfile.mkdtemp()) / "s.json"):
            self.assertFalse(engine.record_hook({"teamwork": {"enabled": True}}, "started", env))
            self.assertTrue(engine.record_hook({"teamwork": {"enabled": True, "runner_hooks": True}}, "started", env, now=NOW))
            self.assertEqual(engine.load()["hooks"][0]["job"], "build")


class Declared(unittest.TestCase):
    def test_everything_is_off_by_default(self):
        defaults = family.FAMILY.defaults["teamwork"]
        for key in ("enabled", "auto_rerun", "forks_help", "inactive_workflows", "runner_hooks", "dismissed_alerts"):
            self.assertIs(defaults[key], False, key)
        self.assertEqual(ghactions.DEFAULT_ALLOWED, ("rerun_failed", "cancel"))
        json.dumps(engine.report({}))


class KeepAlive(unittest.TestCase):
    """A quiet public repository with scheduled runs: the enable of each scheduled workflow is PROPOSED before GitHub switches it off. Off by default."""

    def answers(self, private=False, pushed="2026-11-20T00:00:00Z"):
        return {"repos/me/app": {"private": private, "pushed_at": pushed},
                "repos/me/app/pulls": [], "repos/me/app/dependabot/alerts": [],
                "repos/me/app/actions/runs": {"workflow_runs": [{"workflow_id": 7}]},
                "repos/me/app/actions/workflows": {"workflows": [{"id": 7, "name": "Nightly", "state": "active"}, {"id": 8, "name": "CI", "state": "active"}]}}

    def read(self, days, **kind):
        cfg = engine.settings({"teamwork": {"enabled": True, "keep_alive_days": days}})
        return engine.read_repo(get_from(self.answers(**kind)), "me", "app", cfg, NOW), cfg

    def test_only_the_scheduled_workflow_of_a_quiet_public_repository_is_proposed(self):
        out, cfg = self.read(45)
        quiet = int((NOW - views.epoch("2026-11-20T00:00:00Z")) // 86400)
        self.assertEqual(out["ageing"], [{"repo": "app", "id": 7, "name": "Nightly", "quiet_days": quiet, "days_left": max(0, 60 - quiet)}])
        found = views.proposals([], [], [], [], cfg, NOW, out["ageing"])
        self.assertEqual([(p["action"], p["number"], p["why"]) for p in found], [("enable_workflow", 7, "keep_alive")])

    def test_private_recent_or_off_proposes_nothing(self):
        for days, kind in ((45, {"private": True}), (45, {"pushed": RECENT}), (0, {})):
            self.assertEqual(self.read(days, **kind)[0]["ageing"], [], (days, kind))

    def test_it_is_off_by_default(self):
        self.assertEqual(family.FAMILY.defaults["teamwork"]["keep_alive_days"], 0)


if __name__ == "__main__":
    unittest.main()
