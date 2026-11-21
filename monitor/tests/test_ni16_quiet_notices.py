# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`github_status.quiet_notices`: during an incident of GitHub Actions the notices of the reds marked "possible cause: an incident of GitHub" wait, and are told once when the incident is over, with how
many are still red. Off by default; the reds themselves are never hidden. Fake reads only: no network."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import githubstatus  # noqa: E402
from github_actions_monitor.integrations import notifiers  # noqa: E402
import test_famf_realtime as base  # noqa: E402

NOW = 1_800_000_000.0
QUIET = {"github_status": {"enabled": True, "quiet_notices": True}}


def red(repo="R", workflow="CI", marked=True):
    event = {"kind": "red_new", "owner": "main", "repo": repo, "text": f"{repo}: {workflow} is red", "url": "u", "args": {"repo": repo, "workflow": workflow}}
    if marked:
        event["possible_cause"] = "github_incident"
    return event


class QuietNotices(unittest.TestCase):
    def incident(self):
        status = githubstatus.Status()
        status.update(githubstatus.parse(base.SUMMARY), NOW)
        return status

    def test_it_is_off_by_default_and_a_setting_of_the_page(self):
        self.assertFalse(githubstatus.settings({})["quiet_notices"])
        self.assertFalse(githubstatus.settings({"github_status": {"enabled": True}})["quiet_notices"])
        self.assertFalse(githubstatus.settings({"github_status": {"quiet_notices": "yes"}})["quiet_notices"])
        self.assertIs(am.DEFAULTS["github_status"]["quiet_notices"], False)
        self.assertIn("github_status.quiet_notices", settings_api.FIELDS)

    def test_without_the_setting_nothing_is_held(self):
        status = self.incident()
        self.assertFalse(status.hold(red(), {"github_status": {"enabled": True}}, NOW + 5))
        self.assertEqual(status.take_held()["held"], 0)

    def test_a_marked_red_waits_during_the_incident_and_only_that(self):
        status = self.incident()
        self.assertTrue(status.hold(red("A"), QUIET, NOW + 5))
        self.assertTrue(status.hold(red("B"), QUIET, NOW + 6))
        self.assertFalse(status.hold(red("C", marked=False), QUIET, NOW + 7))      # a red without the mark is told as always
        self.assertFalse(status.hold({"kind": "stuck_new", "possible_cause": "github_incident"}, QUIET, NOW + 7))
        self.assertFalse(status.hold(red("D"), {"github_status": {"enabled": False, "quiet_notices": True}}, NOW + 7))

    def test_nothing_is_held_without_an_incident_or_with_an_old_read_or_too_long(self):
        calm = githubstatus.Status()
        self.assertFalse(calm.hold(red(), QUIET, NOW))
        status = self.incident()
        self.assertFalse(status.hold(red(), QUIET, NOW + 5000))      # the last good read is too old: GitHub may have recovered unseen
        status.update(githubstatus.parse(base.SUMMARY), NOW + githubstatus.HOLD_MAX_SECONDS + 10)
        self.assertFalse(status.hold(red(), QUIET, NOW + githubstatus.HOLD_MAX_SECONDS + 20))      # never longer than the limit

    def test_the_end_gives_back_how_many_were_held_and_how_many_are_still_red(self):
        status = self.incident()
        for name in ("A", "B", "C"):
            status.hold(red(name), QUIET, NOW + 5)
        self.assertEqual(status.snapshot(QUIET["github_status"] and QUIET, NOW + 6)["held_notices"], 3)
        told = status.take_held(lambda repo, workflow: repo in ("A", "C"))
        self.assertEqual((told["held"], told["still_red"], len(told["items"])), (3, 2, 3))
        again = status.take_held()
        self.assertEqual((again["held"], again["still_red"]), (0, None))      # told once

    def test_the_held_list_is_bounded_but_counted(self):
        status = self.incident()
        for number in range(githubstatus.HELD_MAX + 5):
            status.hold(red("R%d" % number), QUIET, NOW + 5)
        told = status.take_held()
        self.assertEqual(told["held"], githubstatus.HELD_MAX + 5)
        self.assertEqual(len(told["items"]), githubstatus.HELD_MAX)

    def test_the_notification_does_not_leave_while_held_and_leaves_after(self):
        sent = []
        with mock.patch.object(githubstatus, "STATUS", self.incident()), mock.patch("time.time", return_value=NOW + 5), \
                mock.patch.object(notifiers, "settings", return_value={"enabled": False, "events": [], "channels": {}}), mock.patch("github_actions_monitor.integrations.dispatcher.dispatch", side_effect=lambda c, e: sent.append(e)):
            before = notifiers.STATS.get("held", 0)
            self.assertEqual(notifiers.notify(QUIET, red("A")), [])
            self.assertEqual(sent, [])      # not even the users of the team mode are told
            self.assertEqual(notifiers.STATS["held"], before + 1)
            notifiers.notify(QUIET, red("B", marked=False))
            self.assertEqual(len(sent), 1)

    def test_the_end_of_the_incident_is_told_once_with_the_count(self):
        status = self.incident()
        status.hold(red("A"), QUIET, NOW + 5)
        status.hold(red("B"), QUIET, NOW + 5)
        told = []

        class Feed:
            state = {"reds": {"A|CI": {}}}

            def _append(self, events):
                told.extend(events)
        with mock.patch.object(githubstatus, "STATUS", status), mock.patch.dict(am.SENTINEL, {"obj": mock.Mock(feed=Feed())}), mock.patch.object(notifiers, "notify") as notify:
            am.announce_github_status("over", QUIET)
        self.assertEqual(len(told), 1)
        self.assertEqual(told[0]["args"]["held"], 2)
        self.assertEqual(told[0]["args"]["still_red"], 1)
        self.assertIn("2", told[0]["text"])
        notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
