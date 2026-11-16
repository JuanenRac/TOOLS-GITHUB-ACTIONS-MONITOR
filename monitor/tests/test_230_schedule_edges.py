# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The schedule of the reports at its edges: the hour that happens twice when the clock goes back, and a monthly report that a long stop must not lose."""
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.reporting import report_schedule as schedule  # noqa: E402

SWITCH = 1_792_800_000      # the moment the fake clock goes back one hour
FIRST = SWITCH - 1800       # 02:30 local, first time (UTC+2)
SECOND = SWITCH + 1800      # 02:30 local again (UTC+1)


def fake_local(stamp):
    """A clock that is UTC+2 before SWITCH and UTC+1 after it; the wall clock at SWITCH-1800 and at SWITCH+1800 is the same."""
    return time.gmtime(stamp + (7200 if stamp < SWITCH else 3600))


class FallBack(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(schedule.time, "localtime", fake_local)
        patcher.start()
        self.addCleanup(patcher.stop)
        wall = fake_local(FIRST)
        self.assertEqual((wall.tm_hour, wall.tm_min), (fake_local(SECOND).tm_hour, fake_local(SECOND).tm_min))

    def test_the_minute_that_comes_twice_is_owed_once(self):
        wall = fake_local(FIRST)
        expression = f"{wall.tm_min} {wall.tm_hour} * * *"
        self.assertTrue(schedule.due(expression, FIRST + 20, FIRST - 3600))           # first time: owed
        self.assertFalse(schedule.due(expression, SECOND + 20, FIRST + 20))           # it ran then; the same wall minute an hour later is not a new one

    def test_a_late_run_is_not_repeated_either(self):
        wall = fake_local(FIRST)
        expression = f"{wall.tm_min} {wall.tm_hour} * * *"
        self.assertFalse(schedule.due(expression, SECOND + 20, FIRST + 100))          # the run happened a minute and a half after the scheduled minute

    def test_a_frequent_schedule_is_not_doubled_in_the_repeated_hour(self):
        wall_minutes = set()
        ran = FIRST
        for moment in range(FIRST, SWITCH + 7200, 60):
            if schedule.due("*/30 * * * *", moment, ran):
                ran = moment
                wall = fake_local(moment)
                key = (wall.tm_hour, wall.tm_min)
                self.assertNotIn(key, wall_minutes)
                wall_minutes.add(key)
        self.assertGreaterEqual(len(wall_minutes), 2)


class Monthly(unittest.TestCase):
    def test_a_monthly_report_survives_a_stop_of_more_than_eight_days(self):
        day = time.mktime((2026, 11, 1, 8, 0, 0, 0, 0, -1))
        now = day + 12 * 86400
        self.assertTrue(schedule.due("0 8 1 * *", now, day - 3600))                    # last ran before the 1st, the monitor was off for 12 days
        self.assertFalse(schedule.due("0 8 1 * *", now, day + 60))                     # it did run on the 1st

    def test_a_weekly_report_still_looks_back_eight_days(self):
        parsed = schedule.parse("0 8 * * 1")
        self.assertEqual(schedule.lookback_minutes(parsed), schedule.MAX_LOOKBACK_MINUTES)
        self.assertEqual(schedule.lookback_minutes(schedule.parse("0 8 1 * *")), schedule.MONTHLY_LOOKBACK_MINUTES)
        self.assertEqual(schedule.lookback_minutes(schedule.parse("0 8 1 6 *")), schedule.YEARLY_LOOKBACK_MINUTES)

    def test_a_long_search_is_cheap(self):
        now = time.mktime((2026, 11, 16, 9, 0, 0, 0, 0, -1))
        started = time.perf_counter()
        self.assertIsNone(schedule.last_due(schedule.parse("0 8 1 2 *"), now, now - 100 * 86400))
        self.assertLess(time.perf_counter() - started, 1.0)


class OneReportAllFormats(unittest.TestCase):
    def test_a_failed_second_format_leaves_no_orphan_first_file(self):
        import tempfile
        from github_actions_monitor.reporting import report_service as service
        from github_actions_monitor.security import private_io
        real = private_io.write_private
        snap = {"state": "scored", "score": 80.0, "letter": "B", "trend": {"direction": "flat", "delta": 0.0}, "coverage": 1.0, "missing_parts": [], "parts": []}
        team = {"all": 0, "totals": {"bad": 0, "warn": 0, "ok": 0, "unknown": 0}, "ranking": []}

        def failing(path, text, *args, **kwargs):
            if str(path).endswith(".md"):
                raise OSError(28, "no space")
            return real(path, text, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(private_io, "write_private", failing):
            with self.assertRaises(OSError):
                service.run({"report_schedule": {"formats": "both"}}, "main", snap, [], team, now=1_800_000_000, base=tmp)
            self.assertEqual(service.listing("main", base=tmp), [])


if __name__ == "__main__":
    unittest.main()
