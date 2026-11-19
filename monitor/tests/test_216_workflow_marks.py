# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The marks of the days a commit touched the workflow files in the daily trend (sentinel.trend_workflow_marks): the day list, the merge into the history, the read by round and its quota gate."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api
from github_actions_monitor.data_pipeline import trend_day
from github_actions_monitor.sentinels import sentinel_local as sl


def commit(sha, date):
    return {"sha": sha, "commit": {"committer": {"date": date}}}


class Days(unittest.TestCase):
    def test_the_days_come_from_the_date_of_the_committer(self):
        found = trend_day.commit_days("tool", [commit("a" * 40, "2026-01-02T10:00:00Z"), commit("b" * 40, "2026-01-02T11:00:00Z"), commit("c" * 40, "2026-01-01T09:00:00Z")], "2026-01-01")
        self.assertEqual(found, {"2026-01-02": ["tool aaaaaaa", "tool bbbbbbb"], "2026-01-01": ["tool ccccccc"]})

    def test_what_is_not_a_commit_is_left_out(self):
        bad = [None, "x", {}, commit("zzzzzzz", "2026-01-02T00:00:00Z"), commit("abc", "2026-01-02T00:00:00Z"), commit("a" * 40, ""), commit("a" * 40, "2025-12-01T00:00:00Z")]
        self.assertEqual(trend_day.commit_days("r", bad, "2026-01-01"), {})
        self.assertEqual(trend_day.commit_days("r", {"message": "Not Found"}), {})

    def test_a_day_keeps_at_most_five_names_and_never_repeats_one(self):
        many = [commit(f"{i:x}" * 7, "2026-01-02T00:00:00Z") for i in range(10)] + [commit("1" * 7, "2026-01-02T00:00:00Z")]
        self.assertEqual(len(trend_day.commit_days("r", many)["2026-01-02"]), trend_day.MAX_RELEASES_PER_DAY)

    def test_the_marks_go_only_to_days_the_history_has_and_are_not_repeated(self):
        days = {"2026-01-02": {"red": 0}, "2026-01-03": {"red": 0}}
        found = {"2026-01-02": ["r a1"], "2025-12-30": ["r b2"]}
        trend_day.merge_marks(days, found, "workflows")
        trend_day.merge_marks(days, found, "workflows")
        self.assertEqual(days["2026-01-02"]["workflows"], ["r a1"])
        self.assertNotIn("2025-12-30", days)
        self.assertEqual(trend_day.workflow_marks({"days": days}), {"2026-01-02": ["r a1"]})
        trend_day.merge_releases(days, {"2026-01-02": ["r v1"]})
        self.assertEqual(days["2026-01-02"]["releases"], ["r v1"])      # the releases keep their own list


class Round(unittest.TestCase):
    def make(self, tmp, answers, rate=4000, repos=("A", "B", "C"), **cfg):
        calls = []

        def gh(*args, **kw):
            calls.append(args)
            value = answers.get(args[1].split("/")[3] if len(args) > 1 else "", [])
            if isinstance(value, Exception):
                raise value
            return value

        ctx = {"gh": gh, "repos_fn": lambda: list(repos), "runs_fn": lambda: {}, "data_fn": lambda: {"rate": {"remaining": rate, "limit": 5000}, "active": [], "issues": []}, "eco_fn": lambda r: "main"}
        with mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s = sl.Sentinel(ctx, {"sentinel": dict(cfg)})
        s.repo_info = {r: {"branch": "main"} for r in repos}
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        s.history = {"days": {today: {"red": 0}}}
        return s, calls, today

    def stamp(self, today):
        return today + "T10:00:00Z"

    def test_it_is_off_by_default_and_the_settings_have_bounds(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s, calls, _ = self.make(tmp, {})
            self.assertFalse(s.cfg["trend_workflow_marks"])
            self.assertFalse(s._workflow_marks_tick())
        self.assertEqual(calls, [])
        self.assertTrue(settings_api.check_value("sentinel.trend_workflow_marks", True)[0])
        self.assertTrue(settings_api.check_value("sentinel.trend_workflow_marks_per_tick", 50)[0])
        self.assertFalse(settings_api.check_value("sentinel.trend_workflow_marks_per_tick", 0)[0])
        self.assertFalse(settings_api.check_value("sentinel.trend_workflow_marks_days", 91)[0])
        self.assertFalse(settings_api.check_value("sentinel.trend_workflow_marks_hours", 0)[0])

    def test_a_round_asks_a_few_repositories_once_each_and_marks_the_day(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s, calls, today = self.make(tmp, {}, trend_workflow_marks=True, trend_workflow_marks_per_tick=2)
            s.ctx["gh"] = lambda *a, **k: (calls.append(a), [commit("a" * 40, self.stamp(today))])[1]
            self.assertTrue(s._workflow_marks_tick())
            self.assertEqual(len(calls), 2)
            self.assertIn("commits?path=.github/workflows&since=", calls[0][1])
            self.assertEqual(calls[0][0], "api")
            self.assertEqual(sorted(s.history["days"][today]["workflows"]), ["A aaaaaaa", "B aaaaaaa"])
            self.assertTrue(s._workflow_marks_tick())      # the third repository
            self.assertEqual(len(calls), 3)
            self.assertFalse(s._workflow_marks_tick())      # all of them asked: nothing before the hours pass
            self.assertEqual(len(calls), 3)

    def test_a_failed_read_waits_its_turn_and_the_others_go_on(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s, calls, today = self.make(tmp, {}, trend_workflow_marks=True, trend_workflow_marks_per_tick=3)

            def gh(*a, **k):
                calls.append(a)
                if "/A/" in a[1]:
                    raise RuntimeError("HTTP 404")
                return [commit("b" * 40, self.stamp(today))]
            s.ctx["gh"] = gh
            self.assertTrue(s._workflow_marks_tick())
        self.assertEqual(len(calls), 3)
        self.assertEqual(sorted(s.history["days"][today]["workflows"]), ["B bbbbbbb", "C bbbbbbb"])
        self.assertIn("workflow_marks", s.errors)

    def test_without_quota_nothing_is_asked(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s, calls, _ = self.make(tmp, {}, rate=100, trend_workflow_marks=True)
            self.assertFalse(s._workflow_marks_tick())
        self.assertEqual(calls, [])

    def test_the_trend_of_the_sentinel_carries_the_marks(self):
        self.assertEqual(trend_day.workflow_marks({"days": {"2026-01-02": {"workflows": ["r a1"]}, "2026-01-03": {}}}), {"2026-01-02": ["r a1"]})
        text = (Path(__file__).resolve().parent.parent / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("tr_ev_workflow", text)


if __name__ == "__main__":
    unittest.main()
