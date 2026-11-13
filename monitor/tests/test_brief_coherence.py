# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The brief for the AI tools and the log agree with the monitor that is running: while a cycle is in progress, the connection is down or a cycle failed, the brief says so and carries the
hour of that note (it no longer keeps the hour of the last complete cycle as if nothing happened), and the log says that a cycle began."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.integrations import ai_alerts  # noqa: E402

NOW = 1_800_000_000
RED = {"repo": "repo-a", "workflow": "CI", "conclusion": "failure", "since": "t", "streak": 1, "url": "https://github.com/o/repo-a/actions/runs/1"}


class TheBriefFollowsTheMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {"ai_alerts": {"enabled": True, "folder": self.tmp.name}}
        ai_alerts._BEAT.clear()

    def brief(self):
        return (Path(self.tmp.name) / "ALERTS_BRIEF.md").read_text(encoding="utf-8")

    def test_a_status_note_rewrites_the_hour_and_keeps_the_open_alerts(self):
        ai_alerts.update(self.config, [RED], now=NOW, status="running, cycle complete (3 repositories read)")
        first = self.brief()
        self.assertIn("Monitor: running, cycle complete (3 repositories read)", first)
        self.assertIn("repo-a / CI", first)
        self.assertTrue(ai_alerts.monitor_status(self.config, "running, a cycle has started, the alerts below are from the last complete cycle", now=NOW + 600))
        second = self.brief()
        self.assertIn(f"updated_epoch: {NOW + 600}", second)
        self.assertNotIn(f"updated_epoch: {NOW}\n", second)
        self.assertIn("a cycle has started", second)
        self.assertIn("repo-a / CI", second)      # a partial cycle neither opens nor closes an alert
        self.assertEqual([a["state"] for a in ai_alerts.alerts(self.config)], ["open"])

    def test_nothing_is_written_when_the_feed_is_off(self):
        self.assertFalse(ai_alerts.monitor_status({"ai_alerts": {"enabled": False, "folder": self.tmp.name}}, "running", now=NOW))
        self.assertFalse((Path(self.tmp.name) / "ALERTS_BRIEF.md").exists())

    def test_a_cycle_in_progress_or_without_connection_tells_the_brief(self):
        said = []
        with mock.patch("github_actions_monitor.app.actions_monitor.brief_status", lambda config, text: said.append(text)):
            am.maintain_extras({}, {"loading": "40 / 131", "offline": {"offline": False}})
            am.maintain_extras({}, {"loading": "", "offline": {"offline": True}})
        self.assertIn("reading repositories (40 / 131)", said[0])
        self.assertIn("connection lost", said[1])

    def test_brief_status_is_best_effort(self):
        with mock.patch("github_actions_monitor.integrations.ai_alerts.monitor_status", side_effect=RuntimeError("boom")):
            am.brief_status(self.config, "running")      # must not raise

    def test_the_loop_writes_the_start_of_a_cycle_in_the_log(self):
        source = Path(am.__file__).read_text(encoding="utf-8")
        self.assertIn("cycle=started", source)
        self.assertIn('brief_status(toolconfig.raw_config() if not LITE["on"] else config, "running, a cycle has started', source)


if __name__ == "__main__":
    unittest.main()
