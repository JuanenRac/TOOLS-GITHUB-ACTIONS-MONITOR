# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.7: the same-origin guard behind an HTTPS proxy on the default port (`listen.proxy_public_host`): the proxy forwards `Host` and `Origin` without a port, so that one
name is accepted as it is, only under an HTTPS session, and nothing else loses its port."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import localguard  # noqa: E402
import settings_api  # noqa: E402

PUBLIC = "monitor.example.com"


def headers(host, origin=None):
    out = {"Host": host}
    if origin is not None:
        out["Origin"] = origin
    return out


class ProxyOnTheDefaultPort(unittest.TestCase):
    def tearDown(self):
        localguard.configure(False)

    def test_the_named_proxy_host_without_a_port_is_accepted_under_https(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        self.assertTrue(localguard.local_request_ok(headers(PUBLIC), 8765))
        self.assertTrue(localguard.local_request_ok(headers(PUBLIC, f"https://{PUBLIC}"), 8765))
        self.assertTrue(localguard.local_request_ok(headers(PUBLIC.upper(), f"HTTPS://{PUBLIC.upper()}"), 8765))

    def test_the_own_host_and_port_pairs_keep_working(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        self.assertTrue(localguard.local_request_ok(headers("127.0.0.1:8765", "https://127.0.0.1:8765"), 8765))
        self.assertTrue(localguard.local_request_ok(headers("localhost:8765", "https://localhost:8765"), 8765))

    def test_without_the_setting_a_host_without_a_port_is_refused(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True)
        self.assertFalse(localguard.local_request_ok(headers(PUBLIC), 8765))
        self.assertFalse(localguard.local_request_ok(headers(PUBLIC, f"https://{PUBLIC}"), 8765))
        self.assertFalse(localguard.local_request_ok(headers("127.0.0.1", "https://127.0.0.1"), 8765))

    def test_under_plain_http_the_setting_does_nothing(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=False, proxy_host=PUBLIC)
        self.assertEqual(localguard.STATE["proxy_host"], "")
        self.assertFalse(localguard.local_request_ok(headers(PUBLIC), 8765))
        self.assertFalse(localguard.local_request_ok(headers(PUBLIC, f"http://{PUBLIC}"), 8765))

    def test_without_the_network_mode_the_setting_does_nothing(self):
        localguard.configure(False, "127.0.0.1", "", secure=True, proxy_host=PUBLIC)
        self.assertEqual(localguard.STATE["proxy_host"], "")
        self.assertFalse(localguard.local_request_ok(headers(PUBLIC), 8765))

    def test_the_origin_must_be_the_same_name_with_the_same_scheme(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        for origin in (f"http://{PUBLIC}", f"https://{PUBLIC}:8765", f"https://{PUBLIC}:443", "https://other.example.com", f"https://{PUBLIC}/path", f"https://{PUBLIC}@evil.example",
                       f"https://{PUBLIC} ", "null", "", f"https:{PUBLIC}", "https://127.0.0.1"):
            self.assertFalse(localguard.local_request_ok(headers(PUBLIC, origin), 8765), origin)

    def test_another_host_without_a_port_is_refused(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        for host in ("other.example.com", "evil.example", "example.com", "sub." + PUBLIC, PUBLIC + ".evil.example", "", "127.0.0.1", "localhost"):
            self.assertFalse(localguard.local_request_ok(headers(host, f"https://{host}"), 8765), host)
            self.assertFalse(localguard.local_request_ok(headers(host), 8765), host)

    def test_the_proxy_name_with_a_port_is_refused_unless_it_is_listed_too(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        self.assertFalse(localguard.local_request_ok(headers(f"{PUBLIC}:8765", f"https://{PUBLIC}:8765"), 8765))
        localguard.configure(True, "127.0.0.1", "T" * 32, allowed=[PUBLIC], secure=True, proxy_host=PUBLIC)
        self.assertTrue(localguard.local_request_ok(headers(f"{PUBLIC}:8765", f"https://{PUBLIC}:8765"), 8765))
        self.assertTrue(localguard.local_request_ok(headers(PUBLIC, f"https://{PUBLIC}"), 8765))


class ProxyHostValue(unittest.TestCase):
    def test_a_plain_host_name_is_kept_in_lower_case(self):
        self.assertEqual(localguard.proxy_host_clean("  Monitor.Example.COM "), PUBLIC)
        self.assertEqual(localguard.proxy_host_clean("\n" + PUBLIC + "\n"), PUBLIC)
        self.assertEqual(localguard.proxy_host_clean("a"), "a")
        self.assertEqual(localguard.proxy_host_clean("my-proxy.lan"), "my-proxy.lan")

    def test_everything_that_is_not_a_plain_host_name_becomes_empty(self):
        for bad in ("", None, 5, True, [], {}, "host:443", "host:8765", "https://host", "host/path", "user@host", "ho st", "ho\nst", "ho\tst", "host\x00", "-host", "host-", ".host", "host.", "[::1]", "::1",
                    "ho_st", "host?x=1", "host#a", "h" * 101, "ünï.example"):
            self.assertEqual(localguard.proxy_host_clean(bad), "", repr(bad))

    def test_the_settings_take_the_name_from_the_configuration(self):
        self.assertEqual(localguard.settings_from({})["proxy_public_host"], "")
        self.assertEqual(localguard.settings_from({"listen": {"network": True, "proxy_public_host": " Monitor.Example.com "}})["proxy_public_host"], PUBLIC)
        self.assertEqual(localguard.settings_from({"listen": {"proxy_public_host": "host:443"}})["proxy_public_host"], "")
        self.assertEqual(localguard.settings_from({"listen": {"proxy_public_host": 7}})["proxy_public_host"], "")
        self.assertEqual(localguard.settings_from({"listen": "x"})["proxy_public_host"], "")

    def test_it_is_off_by_default(self):
        self.assertEqual(am.DEFAULTS["listen"]["proxy_public_host"], "")
        self.assertEqual(localguard.STATE["proxy_host"], "")


class ProxyHostInTheSettings(unittest.TestCase):
    def test_the_key_is_in_the_advanced_tab_and_only_the_same_computer_can_change_it(self):
        self.assertIn("listen.proxy_public_host", settings_api.META)
        meta = settings_api.META["listen.proxy_public_host"]
        self.assertEqual((meta["tab"], meta["block"], meta["secure"]), ("advanced", "network", True))
        self.assertTrue(localguard.local_only_key("listen.proxy_public_host"))

    def test_a_host_name_or_nothing_is_accepted_and_the_rest_is_refused(self):
        for good in ("", PUBLIC, "my-proxy.lan", "a"):
            self.assertEqual(settings_api.check_value("listen.proxy_public_host", good), (True, good), good)
        self.assertEqual(settings_api.check_value("listen.proxy_public_host", "  " + PUBLIC + " "), (True, PUBLIC))
        for bad in ("host:443", "https://host", "host/path", "user@host", "ho st", "-host", "host.", "h" * 101, "[::1]"):
            self.assertEqual(settings_api.check_value("listen.proxy_public_host", bad), (False, "text"), bad)
        for bad in (5, True, None, [PUBLIC]):
            self.assertEqual(settings_api.check_value("listen.proxy_public_host", bad), (False, "type"), bad)

    def test_the_page_texts_exist_in_the_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "pt", "zh"):
            texts = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("cfg.f.listen.proxy_public_host", "cfg.h.listen.proxy_public_host"):
                self.assertTrue(isinstance(texts.get(key), str) and texts[key].strip(), (lang, key))


if __name__ == "__main__":
    unittest.main()


    def test_a_request_without_origin_still_needs_the_right_host(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        self.assertTrue(localguard.local_request_ok(headers(PUBLIC), 8765))
        self.assertFalse(localguard.local_request_ok({}, 8765))
        self.assertFalse(localguard.local_request_ok({"Origin": f"https://{PUBLIC}"}, 8765))

    def test_leaving_the_network_mode_forgets_the_name(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        self.assertEqual(localguard.STATE["proxy_host"], PUBLIC)
        localguard.configure(False)
        self.assertEqual(localguard.STATE["proxy_host"], "")
        self.assertFalse(localguard.local_request_ok(headers(PUBLIC), 8765))

    def test_the_public_state_never_carries_the_name_or_the_token(self):
        state = localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=PUBLIC)
        self.assertNotIn(PUBLIC, json.dumps(state))
        self.assertNotIn("T" * 32, json.dumps(state))
