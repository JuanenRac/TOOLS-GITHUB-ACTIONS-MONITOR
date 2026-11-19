# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The age of every alert of the feed: `first_failed` (since when it fails), `last_failed` (the last reading that found it red) and `last_checked` (the last time it was looked at, also after it was closed)."""
import json
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.integrations import ai_alerts

NOW = 1_800_000_000
ROW = {"repo": "repo-a", "workflow": "CI", "conclusion": "failure", "streak": 1, "since": "2026-01-01T00:00:00Z", "url": "https://github.com/o/repo-a/actions/runs/9"}


class AlertAge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.config = {"ai_alerts": {"enabled": True, "folder": str(self.folder)}}
        self.addCleanup(ai_alerts.ACCOUNT.update, {"id": ""})
        ai_alerts.ACCOUNT["id"] = ""

    def listed(self, **kw):
        return {a["repo"]: a for a in ai_alerts.alerts(self.config, **kw)}

    def test_a_new_alert_starts_its_age_and_a_later_reading_keeps_the_start(self):
        ai_alerts.update(self.config, [ROW], now=NOW)
        ai_alerts.update(self.config, [ROW], now=NOW + 900)
        a = self.listed()["repo-a"]
        self.assertEqual((a["first_failed"], a["last_failed"], a["last_checked"]), (NOW, NOW + 900, NOW + 900))
        self.assertEqual(a["first_seen"], NOW)

    def test_a_closed_alert_keeps_when_it_last_failed_and_says_when_it_was_last_looked_at(self):
        ai_alerts.update(self.config, [ROW], now=NOW)
        ai_alerts.update(self.config, [], now=NOW + 1800)
        a = self.listed()["repo-a"]
        self.assertEqual((a["state"], a["first_failed"], a["last_failed"], a["last_checked"]), ("resolved", NOW, NOW, NOW + 1800))

    def test_an_alert_kept_by_an_older_version_gets_its_start_from_first_seen_and_no_invented_dates(self):
        legacy = {"id": "old1", "repo": "repo-b", "workflow": "CI", "state": "open", "class": "real", "first_seen": 5}
        (self.folder / ai_alerts.STATE).write_text(json.dumps({"old1": legacy}), encoding="utf-8")
        a = self.listed()["repo-b"]
        self.assertEqual((a["first_failed"], a["last_failed"], a["last_checked"]), (5, None, None))

    def test_each_alert_says_failed_suppressed_or_passed_and_the_brief_counts_the_suppressed_apart(self):
        ai_alerts.update(self.config, [ROW, {**ROW, "repo": "repo-c", "url": "https://github.com/o/repo-c/actions/runs/8"}], now=NOW)
        first = self.listed()
        self.assertEqual({a["status"] for a in first.values()}, {"failed"})
        self.assertTrue(ai_alerts.ack(self.config, first["repo-c"]["id"], now=NOW + 5))
        ai_alerts.update(self.config, [ROW, {**ROW, "repo": "repo-c", "url": "https://github.com/o/repo-c/actions/runs/8"}], now=NOW + 10)
        self.assertEqual(self.listed()["repo-c"]["status"], "suppressed")
        self.assertIn("1 suppressed", ai_alerts.read_brief(self.config))
        ai_alerts.update(self.config, [], now=NOW + 20)
        self.assertEqual({a["status"] for a in self.listed().values()}, {"passed"})

    def test_the_hook_keeps_its_closed_list_of_fields(self):
        for name in ("first_failed", "last_failed", "last_checked"):
            self.assertNotIn(name, ai_alerts.FIELDS + ai_alerts.EXTRA)


if __name__ == "__main__":
    unittest.main()
