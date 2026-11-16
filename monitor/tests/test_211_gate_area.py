# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The gate of the network mode behind a proxy and the login: three visitors with wrong tokens cannot lock out the others, a lock that is common to the proxy never stops the right token, and the time a
login takes does not tell which names are users."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_170 as t170  # noqa: E402
import test_auth  # noqa: E402
from github_actions_monitor.security import auth, localguard  # noqa: E402

ACCESS = "T" * 24
PROXY = ("172.29.77.5", 40000)


class Headers(dict):
    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


def visitor(ip):
    return Headers({"X-Forwarded-For": ip})


class BehindTheProxy(unittest.TestCase):
    def setUp(self):
        localguard.configure(True, "0.0.0.0", ACCESS, trusted_proxy=True, trusted_proxies=["172.29.77.0/24"])
        localguard.reset_limits()
        self.addCleanup(lambda: (localguard.configure(False), localguard.reset_limits()))

    @staticmethod
    def fail(headers, times=10):
        for _ in range(times):
            localguard.note_failure(localguard.client_key(PROXY, headers), 10)
            localguard.note_proxy_failure(PROXY, headers, 10)

    def test_three_visitors_with_wrong_tokens_do_not_lock_out_everybody_else(self):
        for ip in ("203.0.113.1", "203.0.113.2", "203.0.113.3"):
            self.fail(visitor(ip))
            self.assertTrue(localguard.is_locked_out(PROXY, visitor(ip)), "the visitor who failed is locked")
        self.assertFalse(localguard.is_locked(localguard.PROXY_KEY), "the common key was not even counted")
        for ip in ("198.51.100.7", "192.0.2.200"):
            self.assertFalse(localguard.is_locked_out(PROXY, visitor(ip)), ip)
            self.assertFalse(localguard.is_locked_out(PROXY, visitor(ip), token_ok=True), ip)

    def test_many_visitors_never_add_up_to_a_lock_of_the_proxy(self):
        for n in range(1, 60):
            self.fail(visitor("203.0.113.%d" % n), times=3)
        self.assertFalse(localguard.is_locked(localguard.PROXY_KEY))
        self.assertFalse(localguard.is_locked_out(PROXY, visitor("198.51.100.7")))

    def test_requests_that_carry_no_address_still_share_the_common_limit_and_the_right_token_passes(self):
        bare = Headers({})
        self.assertTrue(localguard.shares_proxy_key(PROXY, bare))
        self.fail(bare, times=30)
        self.assertTrue(localguard.is_locked(localguard.PROXY_KEY))
        self.assertTrue(localguard.is_locked_out(PROXY, bare), "a guesser without an address is stopped")
        self.assertFalse(localguard.is_locked_out(PROXY, bare, token_ok=True), "the right token is not punished for the guesses of others")
        self.assertFalse(localguard.is_locked_out(PROXY, visitor("198.51.100.7")), "a visitor who carries an address is not touched by it")

    def test_the_common_lock_ends(self):
        self.fail(Headers({}), times=30)
        later = time.time() + localguard.LOCKOUT_SECONDS + 1
        self.assertFalse(localguard.is_locked(localguard.PROXY_KEY, later))

    def test_an_address_that_failed_stays_locked_even_with_the_right_token(self):
        self.fail(visitor("203.0.113.9"))
        self.assertTrue(localguard.is_locked_out(PROXY, visitor("203.0.113.9"), token_ok=True))


class LoginTime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = test_auth.new_storage(self.tmp.name)
        self.addCleanup(self.storage.close)
        auth.GHOSTS.clear()
        self.addCleanup(auth.GHOSTS.clear)
        auth.create_user(self.storage, "root", test_auth.PASSWORD, "admin")
        self.cfg = auth.settings({"auth": {"enabled": True, "max_failed_logins": 5}})

    def hashes_in_the_sixth_attempt(self, name):
        for i in range(5):
            auth.login(self.storage, name, "wrong password %d" % i, self.cfg)
        with mock.patch.object(auth, "verify_password", return_value=False) as spy:
            code = auth.login(self.storage, name, "wrong password 6", self.cfg)[1]
        self.assertEqual(code, "locked")
        return spy.call_count

    def test_a_locked_user_and_a_locked_name_that_does_not_exist_do_the_same_work(self):
        real, ghost = self.hashes_in_the_sixth_attempt("root"), self.hashes_in_the_sixth_attempt("nobody")
        self.assertEqual(real, ghost)
        self.assertGreaterEqual(real, 1)


def only_mine(cls):
    for name in dir(cls):
        if name.startswith("test") and name not in cls.__dict__:
            setattr(cls, name, None)
    return cls


@only_mine
class OnlyTheListingRoutesAreFiltered(test_auth.TeamSupervisor):
    def test_a_path_under_accounts_that_the_supervisor_does_not_filter_is_judged_like_any_other(self):
        ana = self.sign("ana")
        for path in ("/api/accounts/x?account=beta", "/api/accounts/x/y?account=beta"):
            status, body, _ = t170.get(self.url + path, ana)
            self.assertEqual((status, body.get("code")), (403, "account_scope"), path)

    def test_the_three_listing_routes_are_still_filtered_by_the_supervisor(self):
        ana = self.sign("ana")
        self.assertEqual(t170.get(self.url + "/api/accounts", ana)[0], 200)
        self.assertEqual(t170.get(self.url + "/api/accounts/alpha/status", ana)[0], 200)
        self.assertEqual(t170.get(self.url + "/api/accounts/beta/status", ana)[1]["code"], "account_scope")

    def test_the_credential_of_an_account_is_not_for_a_user_who_cannot_see_it(self):
        root_only = {**self.sign("ana"), "Content-Type": "application/json"}
        status, body, _ = t170.get(self.url + "/api/accounts/beta/credential", root_only, data=b'{"action": "reload"}')
        self.assertIn(status, (403,), body)


if __name__ == "__main__":
    unittest.main()
