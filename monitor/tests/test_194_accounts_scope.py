# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The team mode with several accounts: one account is resolved once and the same one is judged and served, a repeated `account` is refused, the process of an account refuses a user that
was resolved for another account, and a change of a password or a role keeps the accounts of the user."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_170 as t170  # noqa: E402
import test_auth  # noqa: E402
from github_actions_monitor.accounts import accounts, accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.security import auth, auth_http, auth_cli  # noqa: E402

JSON = {"Content-Type": "application/json"}


def only_mine(cls):
    """A subclass of a harness inherits every test of it: keep just the ones written here."""
    for name in dir(cls):
        if name.startswith("test") and name not in cls.__dict__:
            setattr(cls, name, None)
    return cls


@only_mine
class OneAccountPerRequest(test_auth.TeamSupervisor):
    def test_a_repeated_account_is_refused_before_anything_is_served(self):
        ana, bob = self.sign("ana"), self.sign("bob")
        for path, who in (("/api/echo?account=alpha&account=beta", ana), ("/api/echo?account=beta&account=alpha", bob), ("/api/echo?account=alpha&account=alpha", ana)):
            status, body, _ = t170.get(self.url + path, who)
            self.assertEqual((status, body["code"]), (400, "account_repeated"), path)
        status, body, _ = t170.get(self.url + "/api/mode?account=alpha&account=beta", {**ana, **JSON}, data=b'{"mode": "low"}')
        self.assertEqual((status, body["code"]), (400, "account_repeated"))
        self.assertEqual(t170.get(self.url + "/api/echo?account=beta", ana)[0], 403, "the plain request for another account is still refused")

    def test_the_gate_and_the_supervisor_read_the_account_the_same_way(self):
        class Request:
            def __init__(self, path, headers=None):
                self.path, self.headers = path, headers or {}
        for path, headers, expected in (("/api/x?account=alpha", {}, "alpha"), ("/api/x?account=ALPHA", {}, None), ("/api/x?account=%62eta", {}, "beta"), ("/api/x?account=+beta", {}, "beta"),
                                        ("/api/x", {"X-Account-Id": "beta"}, "beta"), ("/api/x?account=", {"X-Account-Id": "beta"}, "beta"), ("/api/x?account=alpha", {"X-Account-Id": "beta"}, "alpha"),
                                        ("/api/x?account=nobody", {}, None)):
            judged = auth_http.requested_account(Request(path, headers))
            served = sup.account_of(path, headers, self.base)
            self.assertEqual(served, expected, path)
            self.assertEqual(judged, expected if expected is not None else path.partition("account=")[2].partition("&")[0], path)      # what is judged is the very text that is looked up
        self.assertIsNone(auth_http.requested_account(Request("/api/x?account=alpha&account=beta")), "a repeated account is judged for no account")
        self.assertEqual(sup.resolve_account("/api/x?account=alpha&account=beta", {}, self.base)[1], "repeated")

    def test_what_is_judged_is_what_is_served_also_without_the_parameter(self):
        auth.create_user(self.storage, "dan", test_auth.PASSWORD, "viewer")          # no accounts assigned: ["default"], and there is no account called default here
        auth_http.forget_cache()
        dan = self.sign("dan")
        status, body, _ = t170.get(self.url + "/api/echo", dan)
        self.assertEqual(status, 403, body)
        self.assertEqual(body["code"], "account_scope")
        bob = self.sign("bob")                      # only beta: the default account of the installation is alpha, so it is not his
        self.assertEqual(t170.get(self.url + "/api/echo", bob)[0], 403)
        self.assertEqual(t170.get(self.url + "/api/echo?account=beta", bob)[1]["account"], "beta")

    def test_the_account_is_told_to_the_process_of_the_account_and_a_forged_header_is_dropped(self):
        ana = {**self.sign("ana"), "X-Monitor-Account": "beta"}
        status, body, _ = t170.get(self.url + "/api/echo?account=alpha", ana)
        self.assertEqual((status, body["account"]), (200, "alpha"))

    def test_the_process_of_an_account_refuses_a_user_resolved_for_another_account(self):
        class Request:
            def __init__(self, headers):
                self.headers, self.sent = headers, []
        from unittest import mock
        key = "k" * 40
        env = {auth_http.SUPERVISOR_KEY_ENV: key, auth_http.CHILD_ENV: "1"}
        own = {"id": "alpha"}
        with mock.patch.dict("os.environ", env), mock.patch.dict(auth_http.OWN_ACCOUNT, own):
            answers = []
            with mock.patch.object(auth_http, "fail", lambda handler, code, status, headers=None: answers.append((code, status)) or False):
                good = {auth_http.SUPERVISOR_KEY_HEADER: key, auth_http.USER_HEADER: "ana", auth_http.ACCOUNT_HEADER: "alpha"}
                self.assertTrue(auth_http.child_gate(Request(good)))
                self.assertFalse(auth_http.child_gate(Request({**good, auth_http.ACCOUNT_HEADER: "beta"})))
                self.assertFalse(auth_http.child_gate(Request({k: v for k, v in good.items() if k != auth_http.ACCOUNT_HEADER})))
                self.assertTrue(auth_http.child_gate(Request({auth_http.SUPERVISOR_KEY_HEADER: key})), "no user (individual mode) is not asked for an account")
            self.assertEqual(answers, [("account_scope", 403), ("account_scope", 403)])


@only_mine
class AccountsKept(test_auth.LiveTeam):
    def setUp(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()

    def accounts_of(self, name):
        return next(u for u in auth.list_users(self.storage) if u["username"] == name)["accounts"]

    def test_a_new_password_or_role_keeps_the_accounts_of_the_user(self):
        user, code = auth.create_user(self.storage, "carla", test_auth.PASSWORD, "viewer", ["clientb"])
        self.assertEqual(code, "")
        self.assertEqual(self.accounts_of("carla"), ["clientb"])
        updated, code = auth.update_user(self.storage, "carla", password="another long passphrase")
        self.assertEqual(code, "")
        self.assertEqual(self.accounts_of("carla"), ["clientb"], "only the password changed")
        updated, code = auth.update_user(self.storage, "carla", role="maintainer")
        self.assertEqual((code, self.accounts_of("carla")), ("", ["clientb"]), "only the role changed")
        updated, code = auth.update_user(self.storage, "carla", accounts=["a1", "a2"])
        self.assertEqual((code, self.accounts_of("carla")), ("", ["a1", "a2"]), "asked for other accounts: they change")
        updated, code = auth.update_user(self.storage, "carla", role="admin")
        self.assertEqual(self.accounts_of("carla"), [auth.ALL_ACCOUNTS], "an administrator sees all of them")

    def test_the_console_reset_of_a_password_keeps_the_accounts(self):
        import contextlib
        import io
        from unittest import mock
        auth.create_user(self.storage, "carla", test_auth.PASSWORD, "viewer", ["clientb"])
        with mock.patch.dict("os.environ", {"NEW_PASS_FOR_TEST": "yet another long passphrase"}), contextlib.redirect_stdout(io.StringIO()):
            code = auth_cli.main(["reset-password", "carla", "--password-env", "NEW_PASS_FOR_TEST"], storage=self.storage) if "storage" in auth_cli.main.__code__.co_varnames else None
        if code is None:
            self.skipTest("the console takes its storage from the configuration")
        self.assertEqual(self.accounts_of("carla"), ["clientb"])


if __name__ == "__main__":
    unittest.main()
