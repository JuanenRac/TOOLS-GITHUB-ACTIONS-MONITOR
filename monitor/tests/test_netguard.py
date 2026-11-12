# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Outgoing notifications cannot reach the local network unless `notify.allow_private_targets` is on: literals, names that resolve to a private address, mixed answers, redirects and the
metadata address are refused; the switch lets a private server through. Everything runs against a fake server on this computer and a fake resolver."""
import json
import socket
import sys
import threading
import unittest
import unittest.mock
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import netguard  # noqa: E402
import notifiers  # noqa: E402

HITS = []


class Fake(BaseHTTPRequestHandler):
    def do_GET(self):
        HITS.append(self.path)
        if self.path == "/jump":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def resolver_for(table):
    def resolver(host, port, type=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in table[host]]
    return resolver


class Rule(unittest.TestCase):
    def test_which_addresses_are_blocked(self):
        for ip in ("127.0.0.1", "10.1.2.3", "172.16.0.9", "192.168.0.1", "169.254.169.254", "::1", "fc00::1", "fd12::1", "fe80::1", "0.0.0.0", "100.64.0.1", "::ffff:127.0.0.1", "224.0.0.1", "nonsense"):
            self.assertTrue(netguard.blocked_ip(ip), ip)
        for ip in ("93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"):
            self.assertFalse(netguard.blocked_ip(ip), ip)

    def test_a_name_is_judged_by_every_address_it_resolves_to(self):
        resolver = resolver_for({"good.example": ["93.184.216.34"], "bad.example": ["10.0.0.5"], "mixed.example": ["93.184.216.34", "192.168.1.1"]})
        self.assertEqual(netguard.check_host("good.example", 443, False, resolver), "93.184.216.34")
        for name in ("bad.example", "mixed.example"):
            with self.assertRaises(netguard.Refused):
                netguard.check_host(name, 443, False, resolver)
        self.assertEqual(netguard.check_host("bad.example", 443, True, resolver), "10.0.0.5")

    def test_the_channel_check_refuses_a_private_homeserver_by_default(self):
        cfg = {"enabled": True, "homeserver": "https://192.168.1.10", "room": "!abc:example.org", "token_env": "T"}
        with unittest.mock.patch.dict("os.environ", {"T": "x"}):
            self.assertEqual(notifiers.check_channel("matrix", cfg), "private_target")
            self.assertIsNone(notifiers.check_channel("matrix", cfg, allow_private=True))
            for host in ("https://localhost", "https://169.254.169.254", "https://[::1]", "https://[fc00::1]"):
                self.assertEqual(notifiers.check_channel("matrix", {**cfg, "homeserver": host}), "private_target", host)
            self.assertIsNone(notifiers.check_channel("matrix", {**cfg, "homeserver": "https://matrix.example.org"}))

    def test_the_switch_is_off_by_default_and_only_a_boolean_turns_it_on(self):
        self.assertFalse(notifiers.settings({})["allow_private_targets"])
        self.assertFalse(notifiers.settings({"notify": {"allow_private_targets": "yes"}})["allow_private_targets"])
        self.assertTrue(notifiers.settings({"notify": {"allow_private_targets": True}})["allow_private_targets"])


class Connection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Fake)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_a_server_on_this_computer_is_refused_and_never_receives_the_request(self):
        HITS.clear()
        with self.assertRaises(urllib.error.URLError) as caught:
            netguard.open_url(urllib.request.Request(f"http://127.0.0.1:{self.port}/hello"))
        self.assertEqual(netguard.reason_of(caught.exception), "private_target")
        self.assertEqual(HITS, [])

    def test_a_public_looking_name_that_resolves_to_this_computer_is_refused(self):
        HITS.clear()
        resolver = resolver_for({"innocent.example": ["127.0.0.1"]})
        with self.assertRaises(urllib.error.URLError):
            netguard.open_url(urllib.request.Request(f"http://innocent.example:{self.port}/hello"), resolver=resolver)
        self.assertEqual(HITS, [])

    def test_with_the_switch_on_the_request_goes_through(self):
        HITS.clear()
        resolver = resolver_for({"inner.example": ["127.0.0.1"]})
        with netguard.open_url(urllib.request.Request(f"http://inner.example:{self.port}/hello"), allow_private=True, resolver=resolver) as answer:
            self.assertEqual(answer.read(), b"ok")
        self.assertEqual(HITS, ["/hello"])

    def test_a_redirect_to_the_metadata_address_is_refused(self):
        HITS.clear()
        with self.assertRaises(urllib.error.URLError):
            netguard.open_url(urllib.request.Request(f"http://127.0.0.1:{self.port}/jump"), allow_private=False)
        self.assertEqual(HITS, [])      # the first hop is already on this computer
        # with private targets allowed the first hop is served, the redirect to the link-local address is still a hop that is judged by the same rule
        resolver = resolver_for({"inner.example": ["127.0.0.1"]})
        with self.assertRaises(urllib.error.URLError) as caught:
            netguard.open_url(urllib.request.Request(f"http://inner.example:{self.port}/jump"), allow_private=False, resolver=resolver)
        self.assertEqual(netguard.reason_of(caught.exception), "private_target")


class Notifier(unittest.TestCase):
    def test_a_failed_send_to_a_private_server_says_why_and_leaks_no_secret(self):
        cfg = {"enabled": True, "homeserver": "https://matrix.example.org", "room": "!abc:example.org", "token_env": "T"}
        event = notifiers.test_event("hello")
        with unittest.mock.patch.dict("os.environ", {"T": "secret-token"}):
            result = notifiers.send_channel("matrix", {**cfg, "homeserver": "https://10.0.0.7"}, event)
            self.assertEqual(result, {"channel": "matrix", "ok": False, "reason": "private_target"})
            self.assertNotIn("secret-token", json.dumps(result))

    def test_notify_reports_the_private_target_and_books_no_message(self):
        config = {"notify": {"enabled": True, "events": ["red_new"], "channels": {"matrix": {"enabled": True, "homeserver": "https://192.168.0.2", "room": "!abc:example.org", "token_env": "T"}}}}
        with unittest.mock.patch.dict("os.environ", {"T": "x"}):
            out = notifiers.notify(config, notifiers.test_event("x"))
        self.assertEqual(out, [{"channel": "matrix", "ok": False, "reason": "private_target"}])


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main()
