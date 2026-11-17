# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""With several accounts the supervisor tells the process of each account who acts, with which role, in a signed context that is good for a few seconds and for one account only: the routes of the account
that decide by role (the log of actions) and /api/v1/me then tell the truth."""
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_251_api_v1 as t251  # noqa: E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.security import auth_http, envguard  # noqa: E402
from test_200_contract import Served  # noqa: E402

KEY = "k" * 40
SESSION = {"user": "ana", "role": "maintainer", "accounts": ["alpha"], "csrf": "x"}


class TheSignedContext(unittest.TestCase):
    def test_a_good_context_is_read_back_without_the_csrf_token_of_the_session(self):
        value = auth_http.sign_context(KEY, SESSION, "alpha", now=1000)
        self.assertEqual(auth_http.read_context(KEY, value, "alpha", now=1005), {"user": "ana", "role": "maintainer", "accounts": ["alpha"], "csrf": ""})
        everyone = auth_http.sign_context(KEY, dict(SESSION, role="admin", accounts=None), "alpha", now=1000)
        self.assertIsNone(auth_http.read_context(KEY, everyone, "alpha", now=1000)["accounts"])

    def test_anything_else_is_nothing(self):
        value = auth_http.sign_context(KEY, SESSION, "alpha", now=1000)
        body, mac = value.split(".")
        forged = auth_http.sign_context(KEY, dict(SESSION, role="admin"), "alpha", now=1000).split(".")[0]
        cases = {"another key": (auth_http.read_context("z" * 40, value, "alpha", now=1000)), "another account": auth_http.read_context(KEY, value, "beta", now=1000),
                 "too old": auth_http.read_context(KEY, value, "alpha", now=1000 + auth_http.CONTEXT_WINDOW + 1), "from the future": auth_http.read_context(KEY, value, "alpha", now=900),
                 "role swapped": auth_http.read_context(KEY, forged + "." + mac, "alpha", now=1000), "no signature": auth_http.read_context(KEY, body, "alpha", now=1000),
                 "empty": auth_http.read_context(KEY, "", "alpha", now=1000), "none": auth_http.read_context(KEY, None, "alpha", now=1000), "no key": auth_http.read_context("", value, "alpha", now=1000),
                 "not ascii": auth_http.read_context(KEY, value + "é", "alpha", now=1000), "huge": auth_http.read_context(KEY, "a" * 5000 + "." + mac, "alpha", now=1000),
                 "garbage": auth_http.read_context(KEY, "%%%.%%%", "alpha", now=1000)}
        for name, result in cases.items():
            self.assertIsNone(result, name)
        unknown_role = auth_http.sign_context(KEY, dict(SESSION, role="root"), "alpha", now=1000)
        self.assertIsNone(auth_http.read_context(KEY, unknown_role, "alpha", now=1000), "a role that does not exist")


class AProcessOfAnAccount(unittest.TestCase):
    def serve(self, config=None):
        patcher = mock.patch.dict(os.environ, {auth_http.CHILD_ENV: "1", envguard.SUPERVISOR_KEY_ENV: KEY})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.dict(auth_http.OWN_ACCOUNT, {"id": "alpha"})
        patcher.start()
        self.addCleanup(patcher.stop)
        served = Served(self, lite=False)
        patcher = mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=dict(t251.ON, **(config or {})))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(actions_monitor, "health_views", return_value=t251.VIEWS)
        patcher.start()
        self.addCleanup(patcher.stop)
        return served

    def ask(self, served, path, session=None, account="alpha", signed=True, now=None):
        headers = {auth_http.SUPERVISOR_KEY_HEADER: KEY}
        if session:
            headers[auth_http.USER_HEADER] = session["user"]
            headers[auth_http.ACCOUNT_HEADER] = account
            if signed:
                headers[auth_http.CONTEXT_HEADER] = auth_http.sign_context(KEY, session, account, now=now)
        status, raw, _ = served.raw("GET", path, headers)
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, None

    def test_me_tells_the_truth_about_the_session_of_the_supervisor(self):
        served = self.serve()
        status, body = self.ask(served, "/api/v1/me", SESSION)
        self.assertEqual((status, body["mode"], body["authenticated"], body["role"], body["user"], body["accounts"]), (200, "team", True, "maintainer", "ana", ["alpha"]))
        status, body = self.ask(served, "/api/v1/me")
        self.assertEqual((body["mode"], body["authenticated"], body["role"]), ("individual", False, None))

    def test_the_log_of_actions_follows_the_role_and_the_setting_of_the_account(self):
        served = self.serve()
        for role, expected in (("admin", 200), ("maintainer", 403), ("viewer", 403)):
            self.assertEqual(self.ask(served, "/api/audit-log", dict(SESSION, role=role))[0], expected, role)
        served = self.serve({"audit_log": {"maintainers_can_read": True}})
        self.assertEqual(self.ask(served, "/api/audit-log", SESSION)[0], 200)
        self.assertEqual(self.ask(served, "/api/audit-log", dict(SESSION, role="viewer"))[0], 403)

    def test_without_a_good_context_no_role_is_believed(self):
        served = self.serve()
        self.assertEqual(self.ask(served, "/api/audit-log", dict(SESSION, role="admin"), signed=False)[0], 403, "the user header alone gives no role")
        self.assertEqual(self.ask(served, "/api/audit-log", dict(SESSION, role="admin"), now=int(time.time()) - 600)[0], 403, "an old context is no context")
        self.assertEqual(self.ask(served, "/api/audit-log", dict(SESSION, role="admin"), account="beta")[0], 403, "the user resolved for another account never gets in")

    def test_a_client_cannot_bring_its_own_context_through_the_supervisor(self):
        from github_actions_monitor.accounts import accounts_supervisor
        self.assertIn("x-monitor-context", accounts_supervisor.NO_FORWARD)


if __name__ == "__main__":
    unittest.main()
