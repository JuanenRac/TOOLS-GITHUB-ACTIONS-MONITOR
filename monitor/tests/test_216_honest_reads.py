# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A target that cannot be read is never a clean bill of health and never a defect (rule 13 of the definition of done): the health of an ecosystem does not take a failed read of the alerts for
"no alerts", the candidates of a release are not made from a read that failed, and the combined state of a commit counts the open pull requests."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import surface, toolconfig  # noqa: E402
from github_actions_monitor.cli import release_candidates  # noqa: E402
from github_actions_monitor.sentinels import readiness  # noqa: E402


def snapshot():
    return {"a1": {"stuck": []}, "a2": {"red": []}, "a3": {"rows": []}, "a4": {"stale_days": 14, "dependabot": []}, "a5": {"pending_sign": []}, "a6": {"rows": []}}


class TheHealthOfAnEcosystem(unittest.TestCase):
    def rows(self, alerts):
        key = toolconfig.ecosystem_names()[0]
        repos = ["r1", "r2"]
        runs = {r: [{"id": 1}] for r in repos}
        info = {r: {} for r in repos}
        return readiness.health(snapshot(), {r: key for r in repos}, alerts, runs, info, readiness.settings({}), None)[0]

    def test_alerts_that_were_read_give_a_score(self):
        row = self.rows({"r1": {"at": time.time(), "note": ""}, "r2": {"at": time.time(), "note": "codeql_off"}})
        self.assertEqual(row["score"], 100)
        self.assertEqual((row["missing"], row["unread"]), ([], []))

    def test_a_failed_read_of_the_alerts_is_not_no_alerts(self):
        row = self.rows({"r1": {"at": time.time(), "note": "error: HTTP 502"}, "r2": {"at": time.time(), "note": "error: timeout"}})
        self.assertIsNone(row["score"], "nothing was read: not 100")
        self.assertEqual(row["unread"], ["r1", "r2"])
        self.assertEqual(row["missing"], ["r1", "r2"])

    def test_half_read_is_below_the_coverage_and_says_which_one(self):
        row = self.rows({"r1": {"at": time.time(), "note": ""}, "r2": {"at": time.time(), "note": "error: HTTP 403"}})
        self.assertEqual(row["unread"], ["r2"])
        self.assertEqual(row["covered"], 1)

    def test_the_helper(self):
        self.assertTrue(readiness.alerts_read({"at": 1, "note": ""}))
        self.assertTrue(readiness.alerts_read({"at": 1, "note": "codeql_off"}))
        self.assertFalse(readiness.alerts_read({"at": 1, "note": "error: x"}))
        self.assertFalse(readiness.alerts_read({}))
        self.assertFalse(readiness.alerts_read(None))


class TheLatestReleaseOfACandidate(unittest.TestCase):
    def run_with(self, code, out="", err=""):
        return lambda *a, **k: subprocess.CompletedProcess(a[0], code, out, err)

    def test_a_release_is_read(self):
        body = json.dumps({"published_at": "2026-11-01T10:00:00Z", "tag_name": "v1"})
        self.assertEqual(release_candidates.latest_release("r", self.run_with(0, body))[0], "ok")

    def test_no_release_is_not_a_failed_read(self):
        self.assertEqual(release_candidates.latest_release("r", self.run_with(1, "", "gh: Not Found (HTTP 404)")), ("none", None))

    def test_a_failed_read_is_not_evaluable_and_says_why(self):
        for err in ("gh: HTTP 403: API rate limit exceeded", "dial tcp: lookup api.github.com: no such host", ""):
            state, why = release_candidates.latest_release("r", self.run_with(1, "", err))
            self.assertEqual(state, "unreadable", err)
            self.assertTrue(why)
        self.assertEqual(release_candidates.latest_release("r", self.run_with(0, "<html>"))[0], "unreadable")
        self.assertEqual(release_candidates.latest_release("r", self.run_with(0, "{}"))[0], "unreadable")

        def boom(*a, **k):
            raise subprocess.TimeoutExpired("gh", 60)
        self.assertEqual(release_candidates.latest_release("r", boom)[0], "unreadable")

    def test_the_list_never_makes_a_candidate_of_a_repository_it_could_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("alpha", "beta"):
                (root / name / ".git").mkdir(parents=True)
                (root / name / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n### Added\n\n- one thing\n", encoding="utf-8")
            out = root / "out.txt"
            answers = {"alpha": ("unreadable", "HTTP 502"), "beta": ("none", None)}
            with mock.patch.object(release_candidates, "G", root), mock.patch.object(release_candidates.workspace, "workspace_root", lambda: root), \
                    mock.patch.object(release_candidates.toolconfig, "is_internal", lambda n: True), \
                    mock.patch.object(release_candidates.mainsource, "read_changelog", lambda d: ((d / "CHANGELOG.md").read_text(encoding="utf-8"), "")), \
                    mock.patch.object(release_candidates, "latest_release", lambda n: answers[n]), \
                    mock.patch.object(sys, "argv", ["release_candidates", "--out", str(out)]):
                with self.assertRaises(SystemExit) as stop:
                    release_candidates.main()
            self.assertEqual(stop.exception.code, 2, "a list made with a failed read ends with an error")
            text = out.read_text(encoding="utf-8")
            self.assertIn("beta", text)
            self.assertIn("alpha (HTTP 502)", text)
            self.assertEqual(text.count("alpha"), 1, "it is named once, as not evaluated, not as a candidate")


def check_run(name, conclusion="success", status="completed", cid=1, app="github-actions"):
    return {"name": name, "status": status, "conclusion": conclusion, "id": cid, "started_at": "2026-11-01T10:00:00Z", "app": {"slug": app}}


class TheHeadsOfTheOpenPullRequests(unittest.TestCase):
    def collector(self, answers, **options):
        calls = []

        def gh(*args, **kw):
            calls.append(args[1])
            for fragment, answer in answers.items():
                if fragment in args[1]:
                    if isinstance(answer, Exception):
                        raise answer
                    return answer
            return {}
        cfg = surface.settings({})
        for name in cfg["checks"]:
            cfg["checks"][name]["enabled"] = name == "commit_state"
        cfg["checks"]["commit_state"].update(options)
        return surface.Collector(gh, tempfile.gettempdir(), cfg), calls

    def pulls(self):
        return [{"number": 7, "draft": False, "head": {"sha": "a" * 40}}, {"number": 8, "draft": True, "head": {"sha": "b" * 40}}, {"number": 9, "draft": False, "head": {"sha": "c" * 40}},
                {"number": "x", "draft": False, "head": {"sha": "d" * 40}}, {"number": 10, "draft": False, "head": {"sha": "not a sha"}}]

    def test_off_by_default_and_no_extra_call(self):
        self.assertFalse(surface.DEFAULTS["checks"]["commit_state"]["include_pr_heads"])
        c, calls = self.collector({"check-runs": {"check_runs": []}}, enabled=True)
        c.fetch_repo("A", "main")
        self.assertEqual(len(calls), 1)

    def test_the_heads_are_read_one_call_for_the_list_and_one_each_and_drafts_are_left_out(self):
        answers = {"/pulls?": self.pulls(), "commits/" + "a" * 40: {"check_runs": [check_run("ci", "failure")]}, "commits/" + "c" * 40: {"check_runs": [check_run("ci")]}, "commits/main": {"check_runs": []}}
        c, calls = self.collector(answers, enabled=True, include_pr_heads=True)
        out, used = c.fetch_repo("A", "main")
        self.assertEqual(used, 4, "the branch, the list and two heads (a draft, a bad number and a bad sha are not read)")
        self.assertEqual([h["number"] for h in out["pr_heads"]], [7, 9])

    def test_a_red_pull_request_is_a_row_but_not_a_failure_of_the_branch(self):
        raw = {"A": {"check_runs_full": [check_run("ci")], "pr_heads": [{"number": 7, "check_runs_full": [check_run("ci", "failure"), check_run("lic", app="codecov")]},
                                                                      {"number": 9, "check_runs_full": [check_run("ci")]}]}}
        cfg = surface.settings({"sentinel": {"surface": {"checks": {"commit_state": {"enabled": True, "include_pr_heads": True}}}}})
        rows, bad = surface.commit_state_rows(raw, ["A"], cfg)
        self.assertEqual([r[0] for r in rows], ["A#7"])
        self.assertFalse(bad)
        self.assertIn("ci", rows[0][2])
        off = surface.settings({"checks": {"commit_state": {"enabled": True}}})
        self.assertEqual(surface.commit_state_rows(raw, ["A"], off), ([], False))

    def test_a_head_that_cannot_be_read_is_not_green(self):
        answers = {"/pulls?": self.pulls()[:1], "commits/" + "a" * 40: RuntimeError("HTTP 502"), "commits/main": {"check_runs": []}}
        c, _ = self.collector(answers, enabled=True, include_pr_heads=True)
        out, _used = c.fetch_repo("A", "main")
        self.assertEqual(out["pr_heads"][0]["error"], "HTTP 502")
        cfg = c.cfg
        rows, bad = surface.commit_state_rows({"A": out}, ["A"], cfg)
        self.assertEqual([r[0] for r in rows], ["A#7"])
        self.assertIn("HTTP 502", rows[0][2])
        self.assertFalse(bad)

    def test_a_list_that_cannot_be_read_is_named_too(self):
        c, _ = self.collector({"/pulls?": RuntimeError("HTTP 403"), "commits/main": {"check_runs": []}}, enabled=True, include_pr_heads=True)
        out, _used = c.fetch_repo("A", "main")
        rows, _bad = surface.commit_state_rows({"A": out}, ["A"], c.cfg)
        self.assertEqual([r[0] for r in rows], ["A#"])

    def test_the_number_of_pull_requests_is_clamped(self):
        for bad in (0, 21, -3):
            self.assertEqual(surface.settings({"sentinel": {"surface": {"checks": {"commit_state": {"pr_heads_max": bad}}}}})["checks"]["commit_state"]["pr_heads_max"], 5)
        self.assertEqual(surface.settings({"sentinel": {"surface": {"checks": {"commit_state": {"pr_heads_max": 12}}}}})["checks"]["commit_state"]["pr_heads_max"], 12)


if __name__ == "__main__":
    unittest.main()
