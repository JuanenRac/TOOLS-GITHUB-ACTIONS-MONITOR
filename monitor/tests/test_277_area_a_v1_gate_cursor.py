# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The versioned API says nothing to a visitor without the access token (not even that it is off), and a cursor belongs to the person and the account that asked for it."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_180_network as t180  # noqa: E402
import test_251_api_v1 as t251  # noqa: E402
from github_actions_monitor.app import actions_monitor, api_v1  # noqa: E402

SECRET = b"s" * 32


class ACursorBelongsToWhoAskedForIt(unittest.TestCase):
    def test_the_same_cursor_is_refused_to_another_person_or_account(self):
        first = api_v1.repos_payload(t251.VIEWS, {"limit": "10"}, secret=SECRET, now=1000, cfg=t251.CFG, who="vic|alpha")["next_cursor"]
        self.assertTrue(api_v1.repos_payload(t251.VIEWS, {"limit": "10", "cursor": first}, secret=SECRET, now=1000, cfg=t251.CFG, who="vic|alpha")["items"])
        for other in ("ana|alpha", "vic|beta", ""):
            with self.assertRaises(api_v1.ApiError, msg=other) as caught:
                api_v1.repos_payload(t251.VIEWS, {"limit": "10", "cursor": first}, secret=SECRET, now=1000, cfg=t251.CFG, who=other)
            self.assertEqual(caught.exception.code, "api.bad_cursor")

    def test_without_a_team_the_cursor_is_the_same_as_before(self):
        plain = api_v1.repos_payload(t251.VIEWS, {"limit": "10"}, secret=SECRET, now=1000, cfg=t251.CFG)["next_cursor"]
        self.assertEqual(plain, api_v1.repos_payload(t251.VIEWS, {"limit": "10"}, secret=SECRET, now=1000, cfg=t251.CFG, who="|")["next_cursor"])


class TheSwitchIsNotToldToAVisitorWithoutCredentials(t180.NetworkCase):
    def test_an_off_switch_answers_401_not_404_to_a_remote_visitor_without_the_token(self):
        remote = t180.Running(self)
        with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}):
            for path in ("/api/v1/me", "/api/v1/repos", "/api/v1/alerts", "/api/v1/openapi.json"):
                status, _ = remote.call("GET", path, token="")
                self.assertEqual(status, 401, path)
            status, _ = remote.call("GET", "/api/v1/me")
            self.assertEqual(status, 404, "with the token the switch that is off is a plain 404 as before")

    def test_a_foreign_host_is_refused_before_the_switch_is_looked_at(self):
        remote = t180.Running(self)
        with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}):
            status, _ = remote.call("GET", "/api/v1/me", headers={"Host": "attacker.example"})
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
