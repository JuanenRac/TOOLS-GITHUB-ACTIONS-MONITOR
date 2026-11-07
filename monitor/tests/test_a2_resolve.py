# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.4.1: A2 resolves a workflow hidden by a full run sample by asking for its last run on the default branch (fake gh, no network):
resolved green, resolved red, no runs, no quota, cache (TTL), the call limit, and the panel naming the workflow."""
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
import i18n  # noqa: E402,F401
import make_release as mr  # noqa: E402
import sentinel_local as sl  # noqa: E402
import surface  # noqa: E402

CAPS = {"runs_per_repo": 6, "cold_runs_per_repo": 3}
HERE = Path(mr.HERE)


def run(rid, path="ci.yml", conclusion="success"):
    return {"repo": "R", "id": rid, "name": "CI", "path": path, "branch": "main", "status": "completed", "conclusion": conclusion,
            "started": f"2026-11-06T0{rid}:00:00Z", "url": f"https://x/{rid}", "seconds": 5, "actor": "o", "sha": "abc1234"}


FULL = [run(i) for i in range(6)]


def scans(*files):
    return {"R": {"workflows": [surface.scan_workflow("on: push", f) for f in files], "stacks": [], "dependabot_yml": True, "codeql_yml": True, "manifest": None, "changelog_top": None}}


def make(tmp, answers, rate=4000, **cfg):
    """A Sentinel over one repository R whose runs are FULL and whose clone has ci.yml and release.yml; `answers` maps a workflow file to the gh answer."""
    calls = []

    def gh(*args, **kw):
        calls.append(args)
        file = args[args.index("-w") + 1]
        value = answers.get(file, [])
        if isinstance(value, Exception):
            raise value
        return value

    ctx = {"gh": gh, "repos_fn": lambda: ["R"], "runs_fn": lambda: {"R": {"runs": FULL}}, "data_fn": lambda: {"rate": {"remaining": rate, "limit": 5000}, "active": [], "issues": []},
           "eco_fn": lambda r: "main"}
    with mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
        s = sl.Sentinel(ctx, dict(CAPS, sentinel=dict(cfg)))
    s.repo_info = {"R": {"branch": "main"}}
    s.surface.scans = scans("ci.yml", "release.yml")
    return s, calls


def a2_of(s):
    now = datetime.now(timezone.utc)
    info = {"R": {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": True, "files": {}}}
    inp = {"now": now, "today": now.strftime("%Y-%m-%d"), "cfg": s.cfg, "repos": ["R"], "eco": {"R": "main"}, "repo_info": info, "alerts": {}, "perms": {}, "runs": {"R": FULL},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "",
           "audits": None, "sample_caps": CAPS, "scans": dict(s.surface.scans), "a2_resolved": dict(s.a2_resolved), "a2_pending_reason": s.a2_reason}
    return sl.compute_snapshot(inp)["a2"]


def answer(conclusion):
    return [{"databaseId": 99, "name": "Release", "conclusion": conclusion, "status": "completed", "startedAt": "2026-11-05T08:00:00Z", "url": "https://x/99", "headSha": "deadbeefcafe"}]


class Resolve(unittest.TestCase):
    def test_without_an_answer_the_workflow_is_named_as_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = make(tmp, {})
            a2 = a2_of(s)
        self.assertEqual((a2["level"], a2["inconclusive"]), ("unknown", ["R"]))
        self.assertEqual(a2["inconclusive_workflows"], ["R/release.yml (not checked yet)"])

    def test_resolved_green_makes_a2_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {"release.yml": answer("success")})
            self.assertTrue(s._a2_resolve_tick())
            a2 = a2_of(s)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ("run", "list"))
        self.assertIn("--branch", calls[0])
        self.assertEqual(calls[0][calls[0].index("-L") + 1], str(sl.A2_RESOLVE_DEPTH))
        self.assertEqual(calls[0][calls[0].index("--status") + 1], "completed")
        self.assertEqual((a2["level"], a2["inconclusive"], a2["inconclusive_workflows"], a2["red"]), ("ok", [], [], []))

    def test_resolved_red_counts_as_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = make(tmp, {"release.yml": answer("failure")})
            s._a2_resolve_tick()
            a2 = a2_of(s)
        self.assertEqual(a2["level"], "bad")
        self.assertEqual([(r["repo"], r["workflow"], r["conclusion"]) for r in a2["red"]], [("R", "Release", "failure")])

    def test_no_run_on_the_branch_stays_inconclusive_for_that_workflow_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = make(tmp, {"release.yml": []})
            s._a2_resolve_tick()
            a2 = a2_of(s)
        self.assertEqual((a2["level"], a2["inconclusive"]), ("unknown", ["R"]))
        self.assertEqual(a2["inconclusive_workflows"], ["R/release.yml (no run on the default branch)"])
        self.assertEqual(a2["inconclusive_details"], [{"repo": "R", "workflow": "release.yml", "reason": "no_runs"}])

    def test_without_quota_nothing_is_asked_and_the_reason_is_said(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {"release.yml": answer("success")}, rate=100)
            self.assertFalse(s._a2_resolve_tick())
            a2 = a2_of(s)
        self.assertEqual(calls, [])
        self.assertEqual(a2["inconclusive_workflows"], ["R/release.yml (no quota left to check it)"])
        self.assertEqual(a2["level"], "unknown")

    def test_the_quota_gate_is_the_one_of_a10(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {"release.yml": answer("success")}, rate=3005, min_rate_remaining=1500)
            s.cfg["surface"]["min_rate_factor"] = 2.0
            self.assertTrue(s._a2_resolve_tick())
            s2, calls2 = make(tmp, {"release.yml": answer("success")}, rate=2995, min_rate_remaining=1500)
            s2.cfg["surface"]["min_rate_factor"] = 2.0
            self.assertFalse(s2._a2_resolve_tick())
        self.assertEqual((len(calls), len(calls2)), (1, 0))

    def test_the_answer_is_cached_for_the_ttl_and_asked_again_after_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {"release.yml": answer("success")}, a2_resolve_ttl_seconds=600)
            s._a2_resolve_tick()
            self.assertFalse(s._a2_resolve_tick())
            self.assertEqual(len(calls), 1)
            s.a2_resolved["R|release.yml"]["at"] = time.time() - 601
            self.assertEqual(a2_of(s)["inconclusive_workflows"], ["R/release.yml (not checked yet)"])   # an expired answer no longer counts
            self.assertTrue(s._a2_resolve_tick())
            self.assertEqual(len(calls), 2)
            self.assertEqual(a2_of(s)["level"], "ok")

    def test_the_answers_are_saved_in_the_cache_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = make(tmp, {"release.yml": answer("failure")})
            s._a2_resolve_tick()
            with mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"), \
                    mock.patch.object(s, "_export_ci_red"):
                s._persist()
            data = json.loads(Path(tmp, "c.json").read_text(encoding="utf-8"))
        self.assertEqual(data["a2_resolved"]["R|release.yml"]["conclusion"], "failure")

    def test_the_call_limit_per_tick_and_the_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {}, a2_resolve_max_calls_per_tick=2)
            s.surface.scans = scans("ci.yml", "a.yml", "b.yml", "c.yml")
            s._a2_resolve_tick()
            self.assertEqual(len(calls), 2)
            s._a2_resolve_tick()
            self.assertEqual(len(calls), 3)   # only 3 workflows (a, b, c) were hidden; the first tick asked two of them
            s3, calls3 = make(tmp, {}, a2_resolve_max_calls_per_tick=0)
            self.assertFalse(s3._a2_resolve_tick())
        self.assertEqual(calls3, [])

    def test_a_failing_question_stays_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = make(tmp, {"release.yml": RuntimeError("boom")})
            self.assertFalse(s._a2_resolve_tick())
            self.assertIn("a2_resolve", s.errors)
            self.assertEqual(a2_of(s)["level"], "unknown")

    def test_a_repository_without_a_clone_cannot_be_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {})
            s.surface.scans = {}
            self.assertFalse(s._a2_resolve_tick())
            a2 = a2_of(s)
        self.assertEqual((calls, a2["inconclusive_workflows"]), ([], ["R (no local clone)"]))

    def test_manual_only_workflows_are_never_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {})
            s.surface.scans = {"R": {"workflows": [surface.scan_workflow("on: push", "ci.yml"), surface.scan_workflow("on: workflow_dispatch", "manual.yml")], "stacks": []}}
            self.assertFalse(s._a2_resolve_tick())
        self.assertEqual(calls, [])


def item(conclusion, status="completed", rid=1):
    return {"databaseId": rid, "name": "Release", "conclusion": conclusion, "status": status, "startedAt": "2026-11-05T08:00:00Z", "url": f"https://x/{rid}", "headSha": "deadbeefcafe"}


class OnlyConcluded(unittest.TestCase):
    """Version 1.4.2: a run in progress or a cancelled one is not "seen"; the last run with a real conclusion decides."""

    def a2(self, items):
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = make(tmp, {"release.yml": items})
            s._a2_resolve_tick()
            return a2_of(s)

    def test_in_progress_over_an_earlier_red_is_red(self):
        a2 = self.a2([item(None, "in_progress", 3), item("failure", rid=2), item("success", rid=1)])
        self.assertEqual(a2["level"], "bad")
        self.assertEqual([r["conclusion"] for r in a2["red"]], ["failure"])

    def test_in_progress_over_an_earlier_green_is_green(self):
        a2 = self.a2([item(None, "queued", 3), item("success", rid=2), item("failure", rid=1)])
        self.assertEqual((a2["level"], a2["inconclusive_workflows"]), ("ok", []))

    def test_cancelled_is_skipped_to_the_previous_verdict(self):
        self.assertEqual(self.a2([item("cancelled", rid=3), item("failure", rid=2)])["level"], "bad")
        self.assertEqual(self.a2([item("cancelled", rid=3), item("skipped", rid=2), item("success", rid=1)])["level"], "ok")

    def test_only_cancelled_or_in_progress_is_inconclusive_for_that_workflow(self):
        a2 = self.a2([item("cancelled", rid=3), item(None, "in_progress", rid=2)])
        self.assertEqual((a2["level"], a2["inconclusive_workflows"]), ("unknown", ["R/release.yml (no run on the default branch)"]))

    def test_pick_and_cache(self):
        self.assertIsNone(sl.a2_pick_concluded([]))
        self.assertIsNone(sl.a2_pick_concluded(None))
        self.assertEqual(sl.a2_pick_concluded([item("cancelled"), item("success", rid=7)])["databaseId"], 7)
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = make(tmp, {"release.yml": [item(None, "in_progress", 3), item("failure", rid=2)]})
            s._a2_resolve_tick()
            self.assertFalse(s._a2_resolve_tick())
            self.assertEqual(len(calls), 1)
            self.assertEqual(s.a2_resolved["R|release.yml"]["id"], 2)


class Settings(unittest.TestCase):
    def test_the_options_are_in_the_defaults_and_in_the_neutral_example(self):
        example = json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))["sentinel"]
        for key in ("a2_resolve_max_calls_per_tick", "a2_resolve_ttl_seconds"):
            self.assertIn(key, sl.DEFAULTS)
            self.assertEqual(example[key], sl.DEFAULTS[key])

    def test_new_texts_exist_in_the_eight_catalogues(self):
        for lang in mr.LANGS:
            cat = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.a2_reason_no_runs", "ui.a2_reason_quota", "ui.a2_reason_pending", "ui.a2_reason_no_clone", "ui.a2_inconclusive"):
                self.assertTrue(cat.get(key, "").strip(), f"{lang}: {key}")

    def test_the_panel_uses_the_workflow_labels(self):
        self.assertIn("inconclusive_workflows", (HERE / "actions_monitor.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
