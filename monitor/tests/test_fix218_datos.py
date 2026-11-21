# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Regression tests of the data fixes: a run list as long as the limit in force is never green in A2, finops over the whole sample, linear grouping, webhook state kept, OTLP re-runs, CSV cells."""
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.app import modes
from github_actions_monitor.sentinels import sentinel_local as sl

CFG = {"runs_per_repo": 20, "cold_runs_per_repo": 5}
SCANS = {"big": {"workflows": [{"file": "ci.yml", "main_triggered": True}, {"file": "release.yml", "main_triggered": True}]}}      # release.yml exists but is not in the sample


def _runs(n, repo="big"):
    return [{"repo": repo, "id": i, "name": "CI", "path": "ci.yml", "branch": "main", "event": "push", "status": "completed", "conclusion": "success", "started": f"2026-11-21T10:{i % 60:02d}:00Z"} for i in range(n)]


def _level(runs_by_repo, caps):
    inconclusive = sl.a2_inconclusive(runs_by_repo, caps, SCANS)
    return "unknown" if (sl.a2_unchecked(runs_by_repo) or inconclusive) else "ok", inconclusive


class A2FullSampleByMode(unittest.TestCase):
    def _caps(self, mode):
        return {**CFG, "asked": {"big": modes.effective(CFG, "runs_per_repo", mode)}}

    def test_each_mode_full_list_is_unknown(self):
        for mode, size in (("normal", 20), ("low", 10), ("fast", 30), ("turbo", 50)):
            with self.subTest(mode=mode):
                caps = self._caps(mode)
                self.assertEqual(caps["asked"]["big"], size)
                level, inconclusive = _level({"big": _runs(size)}, caps)
                self.assertEqual(sl.a2_full_sample({"big": _runs(size)}, caps), ["big"])
                self.assertEqual((level, inconclusive), ("unknown", ["big"]))

    def test_short_list_is_not_full(self):
        level, _ = _level({"big": _runs(9)}, self._caps("low"))
        self.assertEqual(level, "ok")

    def test_cold_list_plus_webhook_run_is_unknown(self):
        caps = {**CFG, "asked": {"big": 5}}
        self.assertEqual(_level({"big": _runs(6)}, caps)[0], "unknown")

    def test_unknown_limit_is_never_taken_as_complete(self):
        self.assertEqual(sl.a2_full_sample({"big": _runs(5)}, dict(CFG)), ["big"])
        self.assertEqual(sl.a2_full_sample({"big": _runs(25)}, dict(CFG)), ["big"])
        self.assertEqual(sl.a2_full_sample({"big": _runs(12)}, dict(CFG)), [])

    def test_minutes_partial_follows_the_limit_in_force(self):
        from datetime import datetime, timezone
        runs = [dict(r, seconds=60, started="2026-11-21T10:00:00Z") for r in _runs(10)]
        now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
        rows = sl.minutes({"big": runs}, now, {**CFG, "asked": {"big": 10}})
        self.assertTrue(rows["big"]["partial24"])


class FinopsOverTheWholeRead(unittest.TestCase):
    def setUp(self):
        from datetime import datetime, timedelta, timezone
        from github_actions_monitor.app import actions_monitor as am
        self.am = am
        now = datetime.now(timezone.utc)
        self.runs = [{"repo": f"r{i % 300}", "id": i, "name": "CI", "path": "ci.yml", "event": "push", "status": "completed", "conclusion": "success", "seconds": 600, "title": "feat: x",
                      "started": (now - timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ")} for i in range(1200)]
        self.saved = (am.STATE.get("data"), list(am.ALL_RUNS["runs"]), set(am.PRIVATE), set(am.VISIBILITY["known"]))
        am.STATE["data"] = {"runs": self.runs[:600], "runs_total": 1200}
        am.ALL_RUNS["runs"] = self.runs
        am.PRIVATE.clear()
        am.PRIVATE.update(f"r{i}" for i in range(300))
        am.VISIBILITY["known"] = {f"r{i}" for i in range(300)}
        self.addCleanup(self.restore)

    def restore(self):
        am = self.am
        am.STATE["data"], am.ALL_RUNS["runs"] = self.saved[0], self.saved[1]
        am.PRIVATE.clear()
        am.PRIVATE.update(self.saved[2])
        am.VISIBILITY["known"] = self.saved[3]

    def test_counts_every_run_the_cycle_read(self):
        report = self.am.change_cost_report({"finops": {"by_change": True, "co2": True}})
        self.assertEqual(report["total_minutes"], 12000)
        self.assertEqual(sum(r["runs"] for r in report["rows"]), 1200)
        self.assertFalse(report["partial"])

    def test_marks_partial_when_only_the_cut_is_held(self):
        self.am.ALL_RUNS["runs"] = []
        report = self.am.change_cost_report({"finops": {"by_change": True}})
        self.assertEqual(report["total_minutes"], 6000)
        self.assertTrue(report["partial"])
        self.assertEqual(report["runs_read"], 600)

    def test_unknown_visibility_is_private_not_free(self):
        self.am.PRIVATE.clear()
        self.am.VISIBILITY["known"] = set()
        report = self.am.change_cost_report({"finops": {"by_change": True}})
        self.assertGreater(sum(r["estimated_usd"] for r in report["rows"]), 0)

    def test_public_repositories_read_from_github_stay_free(self):
        self.am.PRIVATE.clear()
        report = self.am.change_cost_report({"finops": {"by_change": True}})
        self.assertEqual(sum(r["estimated_usd"] for r in report["rows"]), 0)


class LinearGrouping(unittest.TestCase):
    def test_same_answer_as_filtering_once_per_repository(self):
        from github_actions_monitor.app import actions_monitor as am
        repos = [f"r{i}" for i in range(40)] + ["empty"]
        runs = [{"repo": f"r{(i * 7) % 45}", "id": i} for i in range(900)]      # r40..r44 are not watched: they must not appear
        self.assertEqual(am.group_runs_by_repo(runs, repos), {r: [x for x in runs if x["repo"] == r] for r in repos})
        self.assertEqual(am.group_runs_by_repo(runs, repos)["empty"], [])

    def test_big_account_does_not_take_seconds(self):
        import time
        from github_actions_monitor.app import actions_monitor as am
        repos = [f"r{i}" for i in range(727)]
        runs = [{"repo": repos[i % 727], "id": i} for i in range(14540)]
        started = time.perf_counter()
        for _ in range(4):
            am.group_runs_by_repo(runs, repos)
        self.assertLess(time.perf_counter() - started, 0.5)      # four passes; the quadratic form took about 2.3 s for three


if __name__ == "__main__":
    unittest.main()
