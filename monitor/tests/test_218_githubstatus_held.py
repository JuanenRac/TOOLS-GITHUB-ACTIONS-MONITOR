# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The notices held during an incident of GitHub are told after six hours, when the site cannot be read, when the option is switched off and after a restart."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import githubstatus  # noqa: E402

NOW = 1_800_000_000.0
ON = {"github_status": {"enabled": True, "quiet_notices": True, "interval_seconds": 300}}
INCIDENT = {"indicator": "minor", "description": "x", "components": {}, "incidents": [], "actions": True}
CALM = {"indicator": "none", "description": "x", "components": {}, "incidents": [], "actions": False}


def red(name="ci"):
    return {"kind": "red_new", "possible_cause": "github_incident", "repo": "o/r", "text": "red", "url": None, "args": {"workflow": name}}


class HeldNotices(unittest.TestCase):
    def incident(self):
        status = githubstatus.Status()
        status.update(INCIDENT, NOW)
        self.assertTrue(status.hold(red(), ON, NOW + 60))
        return status

    def test_a_notice_is_released_after_the_limit_although_the_incident_goes_on(self):
        status = self.incident()
        status.update(INCIDENT, NOW + 6 * 3600)      # still the same incident, and the site still answers
        self.assertFalse(status.release_due(ON, NOW + 3600))
        self.assertTrue(status.release_due(ON, NOW + 60 + githubstatus.HOLD_MAX_SECONDS))
        self.assertEqual(status.take_held()["held"], 1)
        self.assertFalse(status.release_due(ON, NOW + 7 * 3600))

    def test_a_site_that_cannot_be_read_releases_what_was_held(self):
        status = self.incident()
        self.assertFalse(status.release_due(ON, NOW + 600))
        self.assertTrue(status.release_due(ON, NOW + 3600))      # the last good read is older than twice the interval

    def test_switching_the_option_off_releases_what_was_held(self):
        status = self.incident()
        self.assertTrue(status.release_due({"github_status": {"enabled": False, "quiet_notices": True}}, NOW + 100))
        self.assertTrue(status.release_due({"github_status": {"enabled": True, "quiet_notices": False}}, NOW + 100))

    def test_nothing_held_nothing_to_release(self):
        self.assertFalse(githubstatus.Status().release_due(ON, NOW))

    def test_what_was_held_survives_a_restart_and_is_released_when_the_incident_is_gone(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "held.json"
            first = githubstatus.Status()
            first.attach(path)
            first.update(INCIDENT, NOW)
            first.hold(red("a"), ON, NOW + 10)
            first.hold(red("b"), ON, NOW + 20)
            second = githubstatus.Status()      # the monitor was restarted
            second.attach(path)
            self.assertEqual(sorted(i["workflow"] for i in second.held), ["a", "b"])
            self.assertFalse(second.release_due(ON, NOW + 100))      # nothing was read yet: it is not known whether the incident is over
            second.update(CALM, NOW + 200)
            self.assertTrue(second.release_due(ON, NOW + 210))
            self.assertEqual(second.take_held()["held"], 2)
            self.assertFalse(path.exists())

    def test_a_restart_with_a_site_that_cannot_be_read_still_lets_go_after_the_limit(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "held.json"
            first = githubstatus.Status()
            first.attach(path)
            first.update(INCIDENT, NOW)
            first.hold(red(), ON, NOW + 10)
            second = githubstatus.Status()
            second.attach(path)
            self.assertTrue(second.release_due(ON, NOW + 10 + githubstatus.HOLD_MAX_SECONDS))

    def test_the_file_is_part_of_the_state_of_an_account(self):
        from github_actions_monitor.accounts import accounts
        self.assertIn(("github_actions_monitor.data_pipeline.githubstatus", "HELD_FILE", "github_status_held.json"), accounts.STATE_FILES)


class TheTurn(unittest.TestCase):
    def test_the_loop_tells_the_held_notices_even_with_github_status_switched_off(self):
        from unittest import mock
        from github_actions_monitor.app import actions_monitor as am
        status = githubstatus.STATUS
        status.reset()
        self.addCleanup(status.reset)
        status.update(INCIDENT, NOW)
        status.hold(red(), ON, NOW + 10)
        told = []
        with mock.patch.object(am, "announce_github_status", side_effect=lambda transition, cfg: told.append(transition)):
            self.assertEqual(am.outside_tick({}, NOW + 100)["status"], "over")
        self.assertEqual(told, ["over"])


if __name__ == "__main__":
    unittest.main()
