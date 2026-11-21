# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ledger of notifications tells two different notices apart and reads the age of an event in UTC."""
import calendar
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import notify_dedupe  # noqa: E402

ON = {"notify": {"dedupe_ledger": True}}


class Labels(unittest.TestCase):
    def setUp(self):
        notify_dedupe.reset(None)
        self.addCleanup(notify_dedupe.reset, None)

    @staticmethod
    def budget(eco, kind="budget_over"):
        return {"kind": kind, "code": kind, "repo": "", "url": None, "args": {"eco": eco, "used": 90, "limit": 100, "pct": "90", "period": "month"}}

    def test_a_budget_of_another_ecosystem_is_another_notice(self):
        self.assertTrue(notify_dedupe.allow(ON, self.budget("ci-linux"), now=1000))
        self.assertTrue(notify_dedupe.allow(ON, self.budget("macos"), now=1001))
        self.assertFalse(notify_dedupe.allow(ON, self.budget("macos"), now=1002))      # the same one is still told once

    def test_the_counts_do_not_make_a_new_notice(self):
        first, again = self.budget("macos"), self.budget("macos")
        again["args"]["used"] = 95
        self.assertEqual(notify_dedupe.label(first), notify_dedupe.label(again))

    def test_two_reds_of_one_repository_without_a_link_are_two_notices(self):
        one = {"kind": "red_new", "repo": "o/r", "url": None, "args": {"repo": "o/r", "workflow": "ci"}}
        two = {"kind": "red_new", "repo": "o/r", "url": None, "args": {"repo": "o/r", "workflow": "macos"}}
        self.assertNotEqual(notify_dedupe.label(one), notify_dedupe.label(two))


class Age(unittest.TestCase):
    def test_a_new_event_is_zero_hours_old_in_summer_time_too(self):
        stamp = "2026-07-15T10:00:00Z"
        now = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
        with mock.patch.object(time, "timezone", -3600), mock.patch.object(time, "mktime", lambda st: calendar.timegm(st) - 7200):      # a zone that is on summer time
            self.assertEqual(notify_dedupe._event_age_hours({"at": stamp}, now), 0.0)
            self.assertEqual(notify_dedupe._event_age_hours({"at": stamp}, now + 3600), 1.0)

    def test_a_fresh_event_is_not_dropped_as_old(self):
        stamp = "2026-07-15T10:00:00Z"
        now = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
        with mock.patch.object(time, "timezone", -3600), mock.patch.object(time, "mktime", lambda st: calendar.timegm(st) - 7200):
            notify_dedupe.reset(None)
            self.assertTrue(notify_dedupe.allow({"notify": {"max_event_age_hours": 1}}, {"kind": "x", "at": stamp}, now=now + 1800))
        notify_dedupe.reset(None)


if __name__ == "__main__":
    unittest.main()
