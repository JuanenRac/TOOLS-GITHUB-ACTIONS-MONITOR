# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Two holes of the team mode that an outside review found, closed and kept closed.

1. `auth.enabled` with no user yet: the person at this computer works as before (and creates the first administrator) but nobody else is let through to the data of the monitor
   (403 `bootstrap_required`), also with a proxy header in front.
2. The process of one account answers only to its supervisor: without the key the supervisor gave it, every route answers 403, whatever the team mode says.
"""
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_auth as ta  # noqa: E402
from github_actions_monitor.accounts import accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.security import auth_http  # noqa: E402

REMOTE = {"X-Forwarded-For": "203.0.113.9"}      # a forwarding header: the request does not come from a person at this computer


class FirstAdministratorWindow(unittest.TestCase):
    start = ta.LiveTeam.start
    call = ta.LiveTeam.call
    make_admin = ta.LiveTeam.make_admin

    def test_somebody_else_gets_nothing_until_the_first_administrator_exists(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        for path in ("/api/alerts", "/api/data", "/api/accounts", "/api/settings"):
            status, body, _ = self.call(path, headers=REMOTE)
            self.assertEqual((status, body.get("code") if isinstance(body, dict) else None), (403, "bootstrap_required"), path)
        status, body, _ = self.call("/api/alerts", {"x": 1}, headers=REMOTE)
        self.assertEqual((status, body["code"]), (403, "bootstrap_required"), "also a write")

    def test_the_public_routes_and_the_person_at_this_computer_still_work(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.assertEqual(self.call("/api/health", headers=REMOTE)[0], 200)
        self.assertEqual(self.call("/api/auth/me", headers=REMOTE)[0], 200)
        self.assertEqual(self.call("/api/alerts")[0], 200)
        self.assertEqual(self.call("/api/auth/bootstrap", {"username": "root", "password": "x" * 12}, headers=REMOTE)[1]["code"], "bootstrap_local_only")

    def test_after_the_bootstrap_the_normal_gate_takes_over(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        status, body, _ = self.call("/api/alerts", headers=REMOTE)
        self.assertEqual((status, body["code"]), (401, "auth_required"))

    def test_auth_off_changes_nothing(self):
        self.start({})
        self.assertEqual(self.call("/api/alerts", headers=REMOTE)[0], 200)


class ChildAnswersOnlyToItsSupervisor(unittest.TestCase):
    KEY = "key-of-the-supervisor"

    def handler(self, header=None):
        return mock.Mock(path="/api/data", command="GET", headers={auth_http.SUPERVISOR_KEY_HEADER: header} if header is not None else {})

    def test_no_key_a_wrong_key_and_no_key_in_the_environment_are_refused(self):
        sent = []
        with mock.patch.dict(os.environ, {auth_http.CHILD_ENV: "1", auth_http.SUPERVISOR_KEY_ENV: self.KEY}), mock.patch.object(auth_http, "fail", lambda h, code, status, headers=None: sent.append((code, status)) or False):
            self.assertFalse(auth_http.gate(self.handler(), {}))
            self.assertFalse(auth_http.gate(self.handler("guess"), {}))
            self.assertTrue(auth_http.gate(self.handler(self.KEY), {}))
        with mock.patch.dict(os.environ, {auth_http.CHILD_ENV: "1", auth_http.SUPERVISOR_KEY_ENV: ""}), mock.patch.object(auth_http, "fail", lambda h, code, status, headers=None: sent.append((code, status)) or False):
            self.assertFalse(auth_http.gate(self.handler(""), {}), "an empty key proves nothing")
        self.assertEqual(sent, [("supervisor_only", 403)] * 3)

    def test_the_supervisor_puts_the_key_on_every_request_to_its_children(self):
        seen = {}

        class Opened:
            status = 200
            headers = {}

            def read(self, n=-1):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def local_open(request, timeout=0):
            seen["headers"] = {k.lower(): v for k, v in request.header_items()}
            return Opened()
        sup.Child("alpha", 18998, [sys.executable, "-c", "pass"], key=self.KEY)
        with mock.patch.object(sup.netguard, "local_open", local_open):
            sup.fetch("http://127.0.0.1:18998/api/data")
            self.assertEqual(seen["headers"].get(auth_http.SUPERVISOR_KEY_HEADER.lower()), self.KEY)
            sup.fetch("http://127.0.0.1:18997/api/data")      # not a port of a child: no key leaves the supervisor
            self.assertNotIn(auth_http.SUPERVISOR_KEY_HEADER.lower(), seen["headers"])

    def test_the_names_of_the_key_are_the_same_everywhere(self):
        self.assertEqual((auth_http.SUPERVISOR_KEY_ENV, auth_http.SUPERVISOR_KEY_HEADER), (am.SUPERVISOR_KEY_ENV, am.SUPERVISOR_KEY_HEADER))
        self.assertEqual((auth_http.SUPERVISOR_KEY_ENV, auth_http.SUPERVISOR_KEY_HEADER), (sup.SUPERVISOR_KEY_ENV, sup.SUPERVISOR_KEY_HEADER))


if __name__ == "__main__":
    unittest.main()
