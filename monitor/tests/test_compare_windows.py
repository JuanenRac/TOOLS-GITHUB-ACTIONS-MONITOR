# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The windows of the comparison and the calendar filter: the last N days against the same length before, a year ago or a custom range; workdays and weekends in the zone of display, daylight
saving time included; a request that makes no sense is refused with a stable code. The clock is injected."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.compare import config, windows  # noqa: E402

DAY = 86400.0
NOW = datetime(2027, 1, 15, 8, tzinfo=timezone.utc).timestamp()      # a Friday
CFG = config.settings({})


def utc(*parts):
    return datetime(*parts, tzinfo=timezone.utc).timestamp()


class Resolve(unittest.TestCase):
    def test_seven_days_against_the_seven_before(self):
        w = windows.resolve({}, CFG, NOW)
        self.assertEqual(w["now"], (NOW - 7 * DAY, NOW))
        self.assertEqual(w["base"], (NOW - 14 * DAY, NOW - 7 * DAY))
        self.assertEqual((w["baseline"], w["days"], w["window_days"]), ("previous", "all", 7.0))

    def test_thirty_days_and_the_default_follow_the_setting(self):
        self.assertEqual(windows.resolve({"window": "30d"}, CFG, NOW)["now"][0], NOW - 30 * DAY)
        cfg = config.settings({"compare": {"default_window_days": 30}})
        self.assertEqual(windows.resolve({}, cfg, NOW)["base"], (NOW - 60 * DAY, NOW - 30 * DAY))

    def test_a_range_across_the_end_of_a_month(self):
        w = windows.resolve({"from": "2027-01-28T00:00:00Z", "to": "2027-02-04T00:00:00Z"}, CFG, utc(2027, 2, 10))
        self.assertEqual(w["now"], (utc(2027, 1, 28), utc(2027, 2, 4)))
        self.assertEqual(w["base"], (utc(2027, 1, 21), utc(2027, 1, 28)))

    def test_a_year_ago_keeps_the_dates(self):
        w = windows.resolve({"baseline": "year_ago"}, CFG, NOW)
        self.assertEqual(w["base"], (NOW - 7 * DAY - 365 * DAY, NOW - 365 * DAY))

    def test_a_custom_baseline_needs_its_own_range(self):
        w = windows.resolve({"baseline": "custom", "base_from": "2026-12-01T00:00:00Z", "base_to": "2026-12-08T00:00:00Z"}, CFG, NOW)
        self.assertEqual(w["base"], (utc(2026, 12, 1), utc(2026, 12, 8)))
        with self.assertRaises(windows.WindowError) as caught:
            windows.resolve({"baseline": "custom"}, CFG, NOW)
        self.assertEqual(caught.exception.code, "bad_baseline")

    def test_requests_that_make_no_sense_are_refused_with_a_code(self):
        cases = [({"from": "2027-01-10T00:00:00Z", "to": "2027-01-05T00:00:00Z"}, "bad_range"),      # from after to
                 ({"from": "2026-01-01T00:00:00Z", "to": "2027-01-01T00:00:00Z"}, "bad_range"),      # longer than 90 days
                 ({"from": "yesterday"}, "bad_range"), ({"from": "2027-01-10T00:00:00Z", "to": "2027-03-01T00:00:00Z"}, "bad_range"),      # the future
                 ({"window": "0"}, "bad_window"), ({"window": "91d"}, "bad_window"), ({"window": "abc"}, "bad_window"),
                 ({"days": "mondays"}, "bad_days"), ({"baseline": "tomorrow"}, "bad_baseline")]
        for ask, code in cases:
            with self.assertRaises(windows.WindowError, msg=str(ask)) as caught:
                windows.resolve(ask, CFG, NOW)
            self.assertEqual(caught.exception.code, code, str(ask))


class Calendar(unittest.TestCase):
    def test_workdays_and_weekend_split_the_week(self):
        friday, saturday, monday = utc(2027, 1, 15, 12), utc(2027, 1, 16, 12), utc(2027, 1, 18, 12)
        wd = CFG["workdays"]
        self.assertEqual([windows.day_matches(m, "workdays", wd, "utc") for m in (friday, saturday, monday)], [True, False, True])
        self.assertEqual([windows.day_matches(m, "weekend", wd, "utc") for m in (friday, saturday, monday)], [False, True, False])
        self.assertTrue(all(windows.day_matches(m, "all", wd, "utc") for m in (friday, saturday)))

    def test_the_workdays_are_configurable(self):
        cfg = config.settings({"compare": {"workdays": ["7", 1, "2", "3", "4"]}})      # a week that starts on Sunday
        self.assertEqual(cfg["workdays"], [1, 2, 3, 4, 7])
        self.assertTrue(windows.day_matches(utc(2027, 1, 17, 12), "workdays", cfg["workdays"], "utc"))      # Sunday
        self.assertFalse(windows.day_matches(utc(2027, 1, 15, 12), "workdays", cfg["workdays"], "utc"))      # Friday

    def test_the_day_is_the_day_in_the_zone_of_display_not_in_utc(self):
        late_friday_utc = utc(2027, 1, 15, 23, 30)      # already Saturday 00:30 in Madrid
        self.assertTrue(windows.day_matches(late_friday_utc, "workdays", CFG["workdays"], "utc"))
        self.assertFalse(windows.day_matches(late_friday_utc, "workdays", CFG["workdays"], "Europe/Madrid"))
        self.assertTrue(windows.day_matches(late_friday_utc, "weekend", CFG["workdays"], "Europe/Madrid"))

    def test_the_change_of_hour_does_not_move_the_day(self):
        # the last Sunday of March 2027 is the 28th: 00:30 UTC is 02:30 in Madrid (summer time), still Sunday
        sunday = utc(2027, 3, 28, 0, 30)
        self.assertTrue(windows.day_matches(sunday, "weekend", CFG["workdays"], "Europe/Madrid"))
        monday_early = utc(2027, 3, 28, 22, 30)      # 00:30 Monday in Madrid after the change
        self.assertTrue(windows.day_matches(monday_early, "workdays", CFG["workdays"], "Europe/Madrid"))

    def test_an_unreadable_moment_is_not_counted_by_a_filter(self):
        self.assertFalse(windows.day_matches("not a time", "workdays", CFG["workdays"], "utc"))
        self.assertTrue(windows.day_matches("not a time", "all", CFG["workdays"], "utc"))


class Settings(unittest.TestCase):
    def test_off_by_default_and_a_bad_value_keeps_the_default(self):
        self.assertFalse(CFG["enabled"])
        self.assertFalse(CFG["include_in_report"])
        cfg = config.settings({"compare": {"enabled": "yes", "default_window_days": 0, "min_runs_per_window": True, "top_changes": 99, "workdays": ["x"], "default_days_filter": "sometimes", "cache_seconds": -1}})
        self.assertEqual(cfg, config.DEFAULTS)
        self.assertEqual(config.settings(None), config.DEFAULTS)
        self.assertEqual(config.settings({"compare": "x"}), config.DEFAULTS)

    def test_good_values_are_taken(self):
        cfg = config.settings({"compare": {"enabled": True, "default_window_days": 30, "default_days_filter": "weekend", "min_runs_per_window": 5, "top_changes": 3, "cache_seconds": 0}})
        self.assertEqual((cfg["enabled"], cfg["default_window_days"], cfg["default_days_filter"], cfg["min_runs_per_window"], cfg["top_changes"], cfg["cache_seconds"]), (True, 30, "weekend", 5, 3, 0))


if __name__ == "__main__":
    unittest.main()
