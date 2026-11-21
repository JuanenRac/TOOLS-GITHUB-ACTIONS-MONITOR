# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Actions on GitHub, guarded by the server: a reason and an operator are mandatory (and written in the log), the state of the target is looked at again right before acting, the credential is asked
without side effects whether it can (doctor of permissions), only one monitor writes and a QA instance is an observer. GitHub is a double here: nothing is sent anywhere."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import ghactions  # noqa: E402

ALLOWED = ["rerun_failed", "cancel", "close_issue", "close_pr", "merge_pr"]


def config(**over):
    block = {"enabled": True, "allowed": ALLOWED, "writer_lock": False, "preflight": False}
    block.update(over)
    return {"github_actions": block}


class Gh:
    """A double of `gh`: answers the reads with `bodies` (endpoint -> json) and records what was written."""

    def __init__(self, bodies=None, fail_reads=False):
        self.bodies, self.sent, self.reads, self.fail_reads = bodies or {}, [], [], fail_reads

    def __call__(self, args, timeout=40):
        if args[:2] == ["api", "-i"]:
            return 0, "HTTP/2 200\nX-OAuth-Scopes: repo, workflow\n\n{}", ""
        if "-X" not in args:
            self.reads.append(args[1])
            if self.fail_reads:
                return 1, "", "HTTP 404"
            for key, body in self.bodies.items():
                if args[1].endswith(key):
                    return 0, json.dumps(body), ""
            return 0, "{}", ""
        self.sent.append(args)
        return 0, "{}", ""


class ReasonAndOperator(unittest.TestCase):
    def test_without_a_reason_or_an_operator_the_server_refuses_to_plan(self):
        cfg = config()
        self.assertEqual(ghactions.plan(cfg, "o", "cancel", "r", 5), (None, "reason_required"))
        self.assertEqual(ghactions.plan(cfg, "o", "cancel", "r", 5, reason="ab", operator="ana"), (None, "reason_required"))
        self.assertEqual(ghactions.plan(cfg, "o", "cancel", "r", 5, reason="stuck for hours"), (None, "operator_required"))
        item, why = ghactions.plan(cfg, "o", "cancel", "r", 5, reason="stuck for hours", operator="ana")
        self.assertEqual((why, item["reason"], item["operator"]), ("ok", "stuck for hours", "ana"))

    def test_the_operator_of_the_configuration_is_used_and_the_texts_are_cleaned(self):
        item, why = ghactions.plan(config(operator="Juan"), "o", "close_pr", "r", 7, reason="duplicate\n\x1b[31mof #3\t")
        self.assertEqual(why, "ok")
        self.assertEqual(item["operator"], "Juan")
        self.assertNotIn("\x1b", item["reason"])
        self.assertNotIn("\n", item["reason"])
        long, _ = ghactions.plan(config(operator="Juan"), "o", "close_pr", "r", 7, reason="x" * 500)
        self.assertEqual(len(long["reason"]), 200)

    def test_the_requirement_can_be_switched_off_and_is_a_setting(self):
        item, why = ghactions.plan(config(require_reason=False), "o", "cancel", "r", 5)
        self.assertEqual(why, "ok")
        for key in ("require_reason", "operator", "comment_on_target", "preflight", "writer_lock"):
            self.assertIn("github_actions." + key, settings_api.FIELDS)
        cfg = ghactions.settings({})
        self.assertEqual((cfg["require_reason"], cfg["comment_on_target"], cfg["preflight"], cfg["writer_lock"]), (True, False, True, True))

    def test_the_log_keeps_who_and_why(self):
        gh, log = Gh(), Path(tempfile.mkdtemp()) / "log.jsonl"
        item, _ = ghactions.plan(config(), "o", "cancel", "r", 5, reason="stuck", operator="ana")
        self.assertTrue(ghactions.execute(config(), item["id"], gh, log)["ok"])
        row = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual((row["operator"], row["reason"], row["action"]), ("ana", "stuck", "cancel"))

    def test_a_comment_on_the_target_only_when_asked_for_and_only_for_issues_and_pull_requests(self):
        for on, action, expected in ((False, "close_pr", 1), (True, "close_pr", 2), (True, "cancel", 1)):
            gh = Gh()
            cfg = config(comment_on_target=on)
            item, _ = ghactions.plan(cfg, "o", action, "r", 7, reason="duplicate", operator="ana")
            ghactions.execute(cfg, item["id"], gh, Path(tempfile.mkdtemp()) / "l.jsonl")
            self.assertEqual(len(gh.sent), expected, (on, action))


class StillFits(unittest.TestCase):
    def run_case(self, action, body, **kw):
        gh = Gh({"/" + ("actions/runs/9" if action in ("cancel", "rerun_failed") else "issues/9" if action == "close_issue" else "pulls/9"): body})
        cfg = config(require_reason=False)
        item, why = ghactions.plan(cfg, "o", action, "r", 9)
        self.assertEqual(why, "ok")
        return ghactions.execute(cfg, item["id"], gh, Path(tempfile.mkdtemp()) / "l.jsonl"), gh

    def test_a_target_that_changed_meanwhile_is_not_acted_on(self):
        for action, body in (("close_issue", {"state": "closed"}), ("close_pr", {"state": "closed"}), ("merge_pr", {"state": "open", "merged": True}), ("cancel", {"status": "completed"}),
                             ("rerun_failed", {"status": "completed", "conclusion": "success"})):
            result, gh = self.run_case(action, body)
            self.assertEqual(result, {"ok": False, "status": "stale"}, action)
            self.assertEqual(gh.sent, [], action)

    def test_a_target_in_the_state_the_screen_showed_is_acted_on_and_what_cannot_be_read_does_not_block(self):
        for action, body in (("close_issue", {"state": "open"}), ("cancel", {"status": "in_progress"}), ("rerun_failed", {"status": "completed", "conclusion": "failure"})):
            result, gh = self.run_case(action, body)
            self.assertTrue(result["ok"], action)
            self.assertEqual(len(gh.sent), 1)
        gh = Gh(fail_reads=True)
        item, _ = ghactions.plan(config(require_reason=False), "o", "cancel", "r", 9)
        self.assertTrue(ghactions.execute(config(require_reason=False), item["id"], gh, Path(tempfile.mkdtemp()) / "l.jsonl")["ok"])


class DoctorOfPermissions(unittest.TestCase):
    def test_write_access_and_the_list_of_who_may_push_decide_what_is_offered(self):
        gh = Gh({"/r": {"permissions": {"push": True}, "default_branch": "main"}, "/branches/main/protection/restrictions": {"users": [{"login": "someone"}], "apps": [], "teams": []}})
        out = ghactions.doctor(gh, "o", "r", login="me")
        self.assertEqual((out["push"], out["restricted"]), (True, True))
        self.assertEqual(out["actions"]["cancel"], "")
        self.assertEqual(out["actions"]["merge_pr"], "restricted_push")
        self.assertEqual(ghactions.doctor(gh, "o", "r", login="someone")["actions"]["merge_pr"], "")
        none = ghactions.doctor(Gh({"/r": {"permissions": {"push": False}}}), "o", "r")
        self.assertTrue(all(why == "no_push" for why in none["actions"].values()))

    def test_planning_is_refused_with_the_reason_when_the_preflight_says_no(self):
        gh = Gh({"/r": {"permissions": {"push": False}}})
        cfg = config(require_reason=False, preflight=True)
        self.assertEqual(ghactions.plan(cfg, "o", "cancel", "r", 5, run_gh=gh), (None, "preflight"))
        self.assertEqual(ghactions.plan(config(require_reason=False, preflight=False), "o", "cancel", "r", 5, run_gh=gh)[1], "ok")
        self.assertEqual(ghactions.plan(cfg, "o", "cancel", "r", 5, run_gh=Gh(fail_reads=True))[1], "ok")      # a question that cannot be asked blocks nothing


class OneWriter(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.lock = Path(self.dir) / "writer.lock"

    def test_the_first_monitor_writes_and_a_live_second_one_is_an_observer_until_the_first_ends(self):
        cfg = config(writer_lock=True)
        self.assertEqual(ghactions.writer_state(cfg, {}, self.lock), ("writer", ""))
        self.assertEqual(self.lock.read_text(encoding="ascii").split()[0], str(os.getpid()))
        self.assertEqual(ghactions.writer_state(cfg, {}, self.lock), ("writer", ""))      # the same monitor again
        self.lock.write_text("999999", encoding="ascii")      # another monitor, alive
        with mock.patch.object(ghactions, "pid_alive", return_value=True):
            self.assertEqual(ghactions.writer_state(cfg, {}, self.lock), ("observer", "lock"))
        with mock.patch.object(ghactions, "pid_alive", return_value=False):      # it ended: the lock is taken over
            self.assertEqual(ghactions.writer_state(cfg, {}, self.lock), ("writer", ""))

    def test_the_lock_can_be_switched_off_and_a_qa_instance_is_always_an_observer(self):
        self.assertEqual(ghactions.writer_state(config(writer_lock=False), {}, self.lock), ("writer", ""))
        self.assertFalse(self.lock.exists())
        self.assertEqual(ghactions.writer_state(config(writer_lock=False), {"MONITOR_PROFILE": "qa"}, self.lock), ("observer", "qa"))

    def test_an_observer_plans_and_executes_nothing(self):
        gh = Gh()
        cfg = config(require_reason=False)
        item, _ = ghactions.plan(cfg, "o", "cancel", "r", 5)
        with mock.patch.dict(os.environ, {"MONITOR_PROFILE": "qa"}):
            self.assertEqual(ghactions.plan(cfg, "o", "cancel", "r", 5), (None, "observer"))
            self.assertEqual(ghactions.execute(cfg, item["id"], gh, Path(self.dir) / "l.jsonl"), {"ok": False, "status": "observer"})
        self.assertEqual(gh.sent, [])

    def test_the_refusals_are_told_in_the_eight_languages(self):
        for key in ("ui.adv_why_reason_required", "ui.adv_why_operator_required", "ui.adv_why_observer", "ui.adv_why_preflight", "ui.adv_why_stale", "ui.adv_gh_reason", "mon.help_profile"):
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, (key, lang))


if __name__ == "__main__":
    unittest.main()
