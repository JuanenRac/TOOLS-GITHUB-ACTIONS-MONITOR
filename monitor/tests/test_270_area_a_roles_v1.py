# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The prefix /api/v1/ never changes who may read a route: with several accounts and the team mode the door sits in the supervisor, which must judge the route without the prefix."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_170 as t170  # noqa: E402
import test_auth  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402

ROUTES = tuple(sorted(set(auth.ADMIN_GET + auth.MAINTAINER_GET))) + ("/api/data", "/api/alerts", "/api/echo", "/api/score", "/api/settings", "/api/ai/lessons", "/api/live-status", "/api/screens/data")


def only_mine(cls):
    for name in dir(cls):
        if name.startswith("test") and name not in cls.__dict__:
            setattr(cls, name, None)
    return cls


class TheRoleOfARoute(unittest.TestCase):
    def test_a_route_under_the_prefix_needs_the_role_of_the_route_without_it(self):
        for route in ROUTES:
            for method in ("GET", "POST"):
                self.assertEqual(auth.required_role(method, route), auth.required_role(method, "/api/v1/" + route[len("/api/"):]), (method, route))
                self.assertEqual(auth.required_role(method, route), auth.required_role(method, "/api/v1/" + route[len("/api/"):] + "?x=1"), (method, route))
        self.assertEqual(auth.required_role("GET", "/api/v1/advanced"), "admin")
        self.assertEqual(auth.required_role("GET", "/api/v1/audit-log"), "maintainer")


@only_mine
class SeveralAccountsAndTheTeamMode(test_auth.TeamSupervisor):
    def verdict(self, headers, path, account):
        status, body, _ = t170.get(self.url + path + "?account=" + account, headers)
        return status, (body.get("code") if isinstance(body, dict) else None)

    def test_a_viewer_is_refused_the_routes_of_an_administrator_with_and_without_the_prefix(self):
        bob = self.sign("bob")
        for route in auth.ADMIN_GET + auth.MAINTAINER_GET:
            if route.startswith("/api/auth/"):
                continue
            for path in (route, "/api/v1/" + route[len("/api/"):]):
                self.assertEqual(self.verdict(bob, path, "beta"), (403, "forbidden_role"), path)

    def test_the_same_request_gets_the_same_answer_with_and_without_the_prefix_for_every_role(self):
        sessions = {"ana": ("alpha", self.sign("ana")), "bob": ("beta", self.sign("bob")), "root": ("alpha", self.sign("root")), "nobody": ("alpha", {})}
        for who, (account, headers) in sessions.items():
            for route in ROUTES:
                if route.startswith("/api/auth/"):
                    continue
                plain = self.verdict(headers, route, account)
                prefixed = self.verdict(headers, "/api/v1/" + route[len("/api/"):], account)
                if plain[0] in (401, 403):
                    self.assertEqual(plain, prefixed, (who, route))
                else:
                    self.assertNotIn(prefixed[0], (401, 403), (who, route))

    def test_the_prefix_does_not_open_the_door_of_a_session_without_login(self):
        self.assertEqual(self.verdict({}, "/api/v1/advanced", "alpha")[0], 401)


if __name__ == "__main__":
    unittest.main()
