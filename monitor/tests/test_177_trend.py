# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who spends the allowance: the trend of the account against the calls of the monitor itself, and the warning when other tools spend most of it."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402
import quotawatch  # noqa: E402
import signals  # noqa: E402


class Trend(unittest.TestCase):
    def setUp(self):
        quotawatch.reset()

    def test_not_enough_samples_say_nothing(self):
        self.assertEqual(quotawatch.trend(), {})
        quotawatch.note(5000, 5000, "r1", 0, 0)
        self.assertEqual(quotawatch.trend(), {})
        quotawatch.note(4990, 5000, "r1", 5, 60)      # one minute: too soon
        self.assertEqual(quotawatch.trend(), {})

    def test_other_tools_are_told_from_the_monitor(self):
        quotawatch.note(5000, 5000, "r1", 0, 0)
        quotawatch.note(4400, 5000, "r1", 40, 1800)      # half an hour: the account spent 600, the monitor 40
        t = quotawatch.trend()
        self.assertEqual((t["minutes"], t["all_per_hour"], t["own_per_hour"], t["others_per_hour"]), (30, 1200, 80, 1120))
        self.assertTrue(t["others_warn"])

    def test_a_monitor_that_spends_most_of_it_does_not_blame_others(self):
        quotawatch.note(5000, 5000, "r1", 0, 0)
        quotawatch.note(4500, 5000, "r1", 480, 1800)
        self.assertFalse(quotawatch.trend()["others_warn"])

    def test_a_renewal_starts_a_new_window(self):
        quotawatch.note(100, 5000, "r1", 900, 0)
        quotawatch.note(5000, 5000, "r2", 905, 3600)      # the allowance renewed: the old samples are not mixed in
        self.assertEqual(quotawatch.trend(), {})
        quotawatch.note(4950, 5000, "r2", 925, 3600 + 900)
        t = quotawatch.trend()
        self.assertEqual(t["all_per_hour"], 200)

    def test_the_state_and_the_tab_say_it(self):
        doc = signals.state({"figures": {}, "quota_trend": {"minutes": 30, "all_per_hour": 1200, "own_per_hour": 80, "others_per_hour": 1120, "others_warn": True}}, [], "complete")
        sig = [s for s in doc["signals"] if s["id"] == "quota.trend"][0]
        self.assertEqual(sig["level"], "watch")
        self.assertIn("other tools are spending most of the allowance", sig["summary"])
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('T("ui.qt_trend"', page)
        for lang in i18n.LANGS:
            self.assertIn("{x}", i18n.tl(lang, "ui.qt_trend"), lang)
            self.assertNotEqual(i18n.tl(lang, "ui.qt_others"), "ui.qt_others", lang)


class EventsForTheStream(unittest.TestCase):
    def test_the_allowance_the_connection_and_the_health_travel_as_events_and_are_resolved(self):
        import tempfile
        import ai_alerts
        down = signals.state({"figures": {}, "offline": {"offline": True, "since": "s"}, "quota_block": {"blocked": True, "until": "2026-01-01T11:00:00Z", "unread": 12}}, [], "complete")
        rows = signals.extra_alert_rows(down)
        self.assertEqual({r["workflow"] for r in rows}, {"quota", "connection"})
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp}}
            first = ai_alerts.update(config, [], extra_rows=rows)
            self.assertEqual({a["workflow"] for a in first["opened"]}, {"quota", "connection"})
            again = ai_alerts.update(config, [], extra_rows=rows)
            self.assertEqual(again["opened"], [], "an event only when it appears")
            up = signals.state({"figures": {}, "offline": {"offline": False}}, [], "complete")
            solved = ai_alerts.update(config, [], extra_rows=signals.extra_alert_rows(up))
            self.assertEqual({a["workflow"] for a in solved["resolved"]}, {"quota", "connection"})
            self.assertTrue(all(a["class"] in ("watch", "real") for a in first["alerts"]))
        self.assertNotIn("alerts.unresolved", {r["workflow"] for r in rows}, "the red workflows already are alerts of their own")


if __name__ == "__main__":
    unittest.main()
