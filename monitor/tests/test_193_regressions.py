# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The reproductions of the independent review of 1.8.3, kept as tests of the repository: each one failed on that version and passes now (accounts of a request, the accounts of a user kept when a password
changes, the silences of a remote maintainer, the test message that counts against the hourly limit, a restored copy that does not bring back a revoked session, a lock that does not shut the
administrator out, and the keys of the monitor that a program it starts does not inherit). They use the harnesses of test_auth.py and test_170.py."""
import os
import stat
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_170 as t170  # noqa: E402
import test_auth  # noqa: E402
from github_actions_monitor.accounts import accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.security import auth, auth_http, localguard  # noqa: E402
from github_actions_monitor.storage import backup, factory  # noqa: E402

ACCESS = "T" * 24


def own_tests_only(cls):
    """A harness brings its own tests; a subclass that only borrows the harness must not run them again."""
    for base in cls.__mro__[1:]:
        if base is unittest.TestCase or not issubclass(base, unittest.TestCase):
            continue
        for name in dir(base):
            if name.startswith("test") and name not in cls.__dict__:
                setattr(cls, name, None)
    return cls


@own_tests_only
class Isolation(test_auth.TeamSupervisor):
    """T-01: the gate and the supervisor read the same account of a request."""

    def test_a_plain_request_for_another_account_is_refused(self):
        self.assertEqual(t170.get(self.url + "/api/echo?account=beta", self.sign("ana"))[0], 403)

    def test_two_account_parameters_do_not_reach_the_account_of_somebody_else(self):
        self.assertIn(t170.get(self.url + "/api/echo?account=alpha&account=beta", self.sign("ana"))[0], (400, 403))
        self.assertIn(t170.get(self.url + "/api/echo?account=beta&account=alpha", self.sign("bob"))[0], (400, 403))

    def test_a_write_with_two_account_parameters_does_not_reach_another_account(self):
        headers = {**self.sign("ana"), "Content-Type": "application/json"}
        status = t170.get(self.url + "/api/mode?account=alpha&account=beta", headers, data=b'{"mode": "low"}')[0]
        self.assertIn(status, (400, 403))

    def test_the_gate_and_the_supervisor_read_the_same_account(self):
        class H:
            def __init__(self, path, headers=None):
                self.path, self.headers = path, headers or {}
        for path in ("/api/x?account=alpha&account=beta", "/api/x?account=ALPHA", "/api/x?account=%62eta", "/api/x?account=alpha;account=beta", "/api/x?account=+beta"):
            gate, served = auth_http.requested_account(H(path)), sup.account_of(path, {}, None)
            self.assertTrue(gate == served or served is None, (path, gate, served))

    def test_a_user_without_assigned_accounts_does_not_read_the_main_account(self):
        auth.create_user(self.storage, "dan", test_auth.PASSWORD, "viewer")
        auth_http.forget_cache()
        status, body, _ = t170.get(self.url + "/api/echo", self.sign("dan"))
        self.assertNotEqual((status, (body or {}).get("account")), (200, "alpha"))


@own_tests_only
class Team(test_auth.LiveTeam):
    def network(self):
        self.ip = am.lan_address()
        if self.ip.startswith("127."):
            self.skipTest("no address that is not loopback on this computer")
        localguard.configure(True, "0.0.0.0", ACCESS, allowed=[self.ip])
        self.net = ThreadingHTTPServer(("0.0.0.0", 0), am.Handler)
        threading.Thread(target=self.net.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.net.shutdown(), self.net.server_close()))
        self.remote_base = f"http://{self.ip}:{self.net.server_address[1]}"
        self.base = f"http://127.0.0.1:{self.net.server_address[1]}"

    def remote(self, path, body=None, headers=None, method=None):
        saved, self.base = self.base, self.remote_base
        try:
            return self.call(path, body, {"X-Monitor-Access": ACCESS, **(headers or {})}, method)
        finally:
            self.base = saved

    def team(self, extra=None):
        self.start({"auth": {"enabled": True}, "session_guard": False, **(extra or {})})
        self.make_admin()
        self.admin = self.sign_in("root")


@own_tests_only
class Roles(Team):
    def test_changing_a_password_or_a_role_keeps_the_accounts_of_the_user(self):
        self.team()
        self.add_user(self.admin, "carla", "viewer", ["clientb"])
        self.call("/api/auth/users/update", {"username": "carla", "password": "another good password"}, self.admin)
        self.assertEqual(auth.accounts_of(self.storage, "carla", "viewer"), ["clientb"])
        self.call("/api/auth/users/update", {"username": "carla", "role": "maintainer"}, self.admin)
        self.assertEqual(auth.accounts_of(self.storage, "carla", "maintainer"), ["clientb"])

    def test_a_remote_maintainer_does_not_silence_from_the_network_as_the_guide_says(self):
        self.team()
        self.add_user(self.admin, "main", "maintainer")
        self.network()
        status, body, head = self.remote("/api/auth/login", {"username": "main", "password": test_auth.PASSWORD, "client": "web"})
        self.assertEqual(status, 200, body)
        me = {"Cookie": head["Set-Cookie"].split(";")[0], "X-CSRF-Token": body["csrf"]}
        self.assertEqual(self.remote("/api/alerts/mute", {"scope": "code", "value": "ci.stuck", "hours": 2}, me)[0], 403)      # silences are made from this computer only (decided and documented)

    def test_the_test_message_counts_against_the_hourly_limit(self):
        self.team({"notify": {"users": {"enabled": True, "max_per_hour": 2}, "channels": {"email": {"enabled": True, "sender": "monitor@example.org"}}}})
        self.add_user(self.admin, "vic", "viewer")
        vic = self.sign_in("vic")
        status, body, _ = self.call("/api/auth/me/notify", {"enabled": True, "channels": ["email"], "destinations": {"email": {"address": "someone@other.example"}}}, vic)
        self.assertEqual(status, 200, body)
        sent = []

        class FakeSMTP:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def send_message(self, mail):
                sent.append(mail["To"])
        from github_actions_monitor.integrations import channels
        with mock.patch.object(channels.smtplib, "SMTP", FakeSMTP):
            for _ in range(12):
                self.call("/api/auth/me/notify/test", {}, vic)
        self.assertLessEqual(len(sent), 2)

    def test_the_first_administrator_can_be_created_by_the_local_door_behind_a_proxy(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        localguard.configure(True, "127.0.0.1", ACCESS, secure=True, proxy_host="monitor.example", behind_proxy=True)
        door = ThreadingHTTPServer(("127.0.0.1", 0), type("Door", (am.Handler,), {"local_door": True}))
        threading.Thread(target=door.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (door.shutdown(), door.server_close()))
        self.base = f"http://127.0.0.1:{door.server_address[1]}"
        status, body, _ = self.call("/api/auth/bootstrap", {"username": "root", "password": test_auth.PASSWORD}, {"X-Monitor-Access": ACCESS})
        self.assertEqual(status, 200, body)

    def test_a_lock_made_by_strangers_does_not_shut_the_administrator_out_at_this_computer(self):
        self.team()
        self.network()
        for i in range(6):
            self.remote("/api/auth/login", {"username": "root", "password": "wrong password %d" % i})
        status, body, _ = self.call("/api/auth/login", {"username": "root", "password": test_auth.PASSWORD}, {"X-Monitor-Access": ACCESS})
        self.assertEqual(status, 200, body)


class Restore(unittest.TestCase):
    def test_a_restored_copy_does_not_bring_back_a_revoked_session(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = factory.create_storage({"backend": "file", "path": tmp.name + "/data"})
        self.addCleanup(store.close)
        cfg = auth.settings({"auth": {"enabled": True}})
        auth.bootstrap_admin(store, "root", "a long enough passphrase 1")
        session, _code = auth.login(store, "root", "a long enough passphrase 1", cfg)
        backup.make_backup(store, tmp.name + "/copy.zip")
        self.assertNotIn(session["csrf"], zipfile.ZipFile(tmp.name + "/copy.zip").read("dump.jsonl").decode())
        auth.revoke_sessions(store, "root")
        backup.restore_backup(tmp.name + "/copy.zip", store, force=True)
        self.assertIsNone(auth.find_session(store, session["token"]))


@unittest.skipIf(os.name == "nt", "the program is a shell script")
class Environment(unittest.TestCase):
    def test_a_program_started_by_the_monitor_does_not_get_its_keys(self):
        from github_actions_monitor.integrations import ai_notify
        from github_actions_monitor.security import secretstore
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prog = Path(tmp.name) / "advisor.sh"
        prog.write_text("#!/bin/sh\ncat >/dev/null\nenv | grep -c -E '^(MONITOR_SUPERVISOR_KEY|MONITOR_ACCESS_TOKEN)='\n")
        prog.chmod(prog.stat().st_mode | stat.S_IXUSR)
        os.environ["MONITOR_SUPERVISOR_KEY"], os.environ["MONITOR_ACCESS_TOKEN"] = "test-key", "test-token"
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("MONITOR_SUPERVISOR_KEY", "MONITOR_ACCESS_TOKEN")])
        self.assertIn("0", str(ai_notify._command(str(prog), "{}", 10))[:3])
        secretstore.APPLIED["token"] = "ghp_test"
        self.addCleanup(lambda: secretstore.APPLIED.update(token=""))
        env = secretstore.gh_kwargs()["env"]
        self.assertFalse([k for k in ("MONITOR_SUPERVISOR_KEY", "MONITOR_ACCESS_TOKEN") if k in env])


if __name__ == "__main__":
    unittest.main()
