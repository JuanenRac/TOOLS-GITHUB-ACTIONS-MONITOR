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


if __name__ == "__main__":
    unittest.main()
