# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""listen.trusted_proxy: off by default and then nothing changes; on, behind a proxy of the owner, a failed attempt is counted against the last address of X-Forwarded-For; never "this computer"."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402
import localguard  # noqa: E402
import settings_api  # noqa: E402


class Headers(dict):
    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


LOOP = ("127.0.0.1", 5000)
REMOTE = ("203.0.113.9", 5000)


class TrustedProxy(unittest.TestCase):
    def setUp(self):
        localguard.configure(True, "127.0.0.1", "t" * 20, (), secure=False, proxy_host="", trusted_proxy=False)
        localguard.reset() if hasattr(localguard, "reset") else None
        self.addCleanup(localguard.configure, False)

    def test_off_nothing_changes(self):
        headers = Headers({"X-Forwarded-For": "198.51.100.7"})
        self.assertEqual(localguard.client_key(LOOP, headers), "127.0.0.1")
        self.assertEqual(localguard.client_key(LOOP, None), "127.0.0.1")
        self.assertFalse(localguard.settings_from({})["trusted_proxy"])
        self.assertFalse(localguard.settings_from({"listen": {"trusted_proxy": "yes"}})["trusted_proxy"], "only a real true turns it on")
        self.assertTrue(localguard.settings_from({"listen": {"trusted_proxy": True}})["trusted_proxy"])

    def test_on_the_last_address_of_the_header_is_the_client(self):
        localguard.configure(True, "127.0.0.1", "t" * 20, (), trusted_proxy=True)
        self.assertEqual(localguard.client_key(LOOP, Headers({"X-Forwarded-For": "198.51.100.7"})), "fwd:198.51.100.7")
        self.assertEqual(localguard.client_key(LOOP, Headers({"X-Forwarded-For": "1.2.3.4, 198.51.100.7"})), "fwd:198.51.100.7", "an address written by the client earlier in the chain is ignored")
        self.assertEqual(localguard.client_key(LOOP, Headers({"X-Forwarded-For": "2001:db8::1"})), "fwd:2001:db8::1")

    def test_only_a_peer_on_this_computer_is_a_proxy_and_a_bad_header_is_ignored(self):
        localguard.configure(True, "127.0.0.1", "t" * 20, (), trusted_proxy=True)
        self.assertEqual(localguard.client_key(REMOTE, Headers({"X-Forwarded-For": "198.51.100.7"})), "203.0.113.9", "a client of the network cannot name itself")
        self.assertEqual(localguard.client_key(LOOP, Headers({"X-Forwarded-For": "not-an-address"})), "127.0.0.1")
        self.assertEqual(localguard.client_key(LOOP, Headers({"X-Forwarded-For": ""})), "127.0.0.1")
        localguard.configure(False, trusted_proxy=True)
        self.assertFalse(localguard.STATE["trusted_proxy"], "without the network mode there is nothing to trust")

    def test_it_never_makes_a_request_local(self):
        for flag in (False, True):
            localguard.configure(True, "127.0.0.1", "t" * 20, (), trusted_proxy=flag)
            self.assertFalse(localguard.is_this_computer(LOOP, Headers({"X-Forwarded-For": "127.0.0.1"})), flag)
            self.assertFalse(localguard.is_this_computer(LOOP, Headers({"X-Forwarded-For": "198.51.100.7"})), flag)
            self.assertTrue(localguard.is_this_computer(LOOP, Headers({})), flag)

    def test_the_wrong_tokens_of_one_person_lock_only_that_person_when_it_is_on(self):
        for flag, expect_other_locked in ((False, True), (True, False)):
            localguard.configure(True, "127.0.0.1", "t" * 20, (), trusted_proxy=flag)
            localguard._failures.clear()
            localguard._locked.clear()
            a = localguard.client_key(LOOP, Headers({"X-Forwarded-For": "198.51.100.7"}))
            b = localguard.client_key(LOOP, Headers({"X-Forwarded-For": "198.51.100.8"}))
            for _ in range(20):
                localguard.note_failure(a, 5)
            self.assertTrue(localguard.is_locked(a), flag)
            self.assertEqual(localguard.is_locked(b), expect_other_locked, f"trusted_proxy={flag}")

    def test_the_setting_is_local_only_and_has_its_help_in_the_eight_languages(self):
        self.assertIn("listen.trusted_proxy", settings_api.FIELDS)
        self.assertTrue(localguard.local_only_key("listen.trusted_proxy"))
        self.assertNotIn("listen.trusted_proxy", localguard.REMOTE_WRITABLE)
        for lang in i18n.LANGS:
            for prefix in ("cfg.f.", "cfg.h."):
                self.assertNotEqual(i18n.tl(lang, prefix + "listen.trusted_proxy"), prefix + "listen.trusted_proxy", lang)
            self.assertIn("X-Forwarded-For", i18n.tl(lang, "cfg.h.listen.trusted_proxy"), lang)
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("localguard.client_key(self.client_address, self.headers)"), 2)
        self.assertIn('"trusted_proxy": False', source)


if __name__ == "__main__":
    unittest.main()
