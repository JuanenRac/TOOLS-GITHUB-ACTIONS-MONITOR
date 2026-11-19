# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A retention can never be shorter than the longest window that reads it: the purge raises it and the doctor says so."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from github_actions_monitor.ops import checks, purge  # noqa: E402
from github_actions_monitor.storage import retention  # noqa: E402


class TheFloor(unittest.TestCase):
    def test_the_defaults_are_not_raised(self):
        self.assertEqual(retention.effective({})["raised"], {})
        self.assertEqual(retention.effective({})["events_days"], 90)

    def test_settings_stay_as_written(self):
        self.assertEqual(retention.settings({"retention": {"analytics_days": 1}})["analytics_days"], 1)

    def test_analytics_are_kept_as_long_as_the_analytics_window(self):
        out = retention.effective({"retention": {"analytics_days": 5}, "analytics": {"keep_days": 30}})
        self.assertEqual((out["analytics_days"], out["raised"]), (30, {"analytics_days": {"asked": 5, "now": 30}}))

    def test_events_are_kept_as_long_as_two_windows_of_the_comparison_and_a_day(self):
        out = retention.effective({"retention": {"events_days": 7}, "compare": {"enabled": True, "default_window_days": 14}})
        self.assertEqual((out["events_days"], out["raised"]["events_days"]), (29, {"asked": 7, "now": 29}))

    def test_with_the_comparison_off_it_asks_nothing_of_the_events(self):
        out = retention.effective({"retention": {"events_days": 2}, "compare": {"enabled": False, "default_window_days": 30}})
        self.assertEqual((out["events_days"], out["raised"]), (2, {}))

    def test_a_longer_retention_is_left_alone(self):
        out = retention.effective({"retention": {"events_days": 400, "analytics_days": 400}, "analytics": {"keep_days": 30}, "compare": {"enabled": True, "default_window_days": 14}})
        self.assertEqual((out["events_days"], out["analytics_days"], out["raised"]), (400, 400, {}))

    def test_the_purge_plan_uses_the_raised_value(self):
        class Storage:
            def event_stats(self, account):
                return {"count": 0}

            def load_events(self, account, limit=None):
                return []
        config = {"retention": {"analytics_days": 3}, "analytics": {"keep_days": 60}, "ops": {"purge": {"enabled": True}}}
        plan = purge.plan(config, Storage(), None, now=2_000_000_000)
        self.assertEqual(plan["policy"]["analytics_days"], 60)

    def test_the_doctor_warns_and_says_what_was_raised(self):
        status, text = checks.limits({"retention": {"analytics_days": 3}, "analytics": {"keep_days": 60}})
        self.assertEqual(status, "warn")
        self.assertIn("analytics_days raised from 3 to 60", text)

    def test_the_doctor_is_quiet_without_a_conflict(self):
        status, text = checks.limits({})
        self.assertNotIn("raised", text)


if __name__ == "__main__":
    unittest.main()
