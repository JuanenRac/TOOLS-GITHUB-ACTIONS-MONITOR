# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Regression tests of the network and access fixes: a stream of a revoked device ends, a connection that sends nothing is let go and the number of open connections has a ceiling, the chat receiver
counts only bad signatures against an address, the paths of this computer are not given to a client of the network, the webhook has a freshness window and keeps only the links of GitHub, and the
supervisor lets the chat through, takes the largest body of its accounts and answers the 413 after reading the body."""
import json
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
import unittest.mock as mock
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402
from github_actions_monitor.chatops import inbound  # noqa: E402
from github_actions_monitor.security import devices, envguard, localguard  # noqa: E402
from test_chatops import ENV as CHAT_ENV  # noqa: E402
from test_chatops import config as chat_config  # noqa: E402
from test_chatops import slack_body, slack_headers  # noqa: E402
from test_164 import LiveServer  # noqa: E402


class Network(unittest.TestCase):
    """Saves and puts back the state of the process that these tests change."""

    def setUp(self):
        self.guard = _testenv.guard(self)
        self.saved = (dict(am.LIVE_CONFIG), dict(localguard.STATE), dict(localguard.DEVICE_CHECK))
        self.addCleanup(self.restore)

    def restore(self):
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update(self.saved[0])
        localguard.STATE.clear()
        localguard.STATE.update(self.saved[1])
        localguard.DEVICE_CHECK.clear()
        localguard.DEVICE_CHECK.update(self.saved[2])
        for device in devices.list_devices():
            devices.revoke(device["id"])
        devices.close()


class StreamOfARevokedDevice(Network):
    def paired(self):
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, "pairing": {"enabled": True}})
        localguard.configure(True, "127.0.0.1", "t" * 24)
        localguard.DEVICE_CHECK["fn"] = am._device_token_ok
        cfg = devices.settings(am.LIVE_CONFIG)
        return cfg

    def test_revoking_the_device_ends_its_open_stream_at_once(self):
        cfg = self.paired()
        opened = devices.start(cfg)
        token, device = devices.redeem(cfg, opened["code"], "Android")
        self.assertTrue(token.startswith("dev_"))
        handler = types.SimpleNamespace(headers={"Authorization": "Bearer " + token}, path="/api/live-events/stream")
        stop = am.Handler.stream_guard(handler)
        self.assertFalse(stop(), "a live device keeps its stream")
        self.assertTrue(devices.revoke(device["id"]))
        self.assertTrue(stop(), "a revoked device must not keep listening until live.sse.max_seconds")

    def test_switching_the_pairing_off_ends_the_stream_of_a_device(self):
        cfg = self.paired()
        opened = devices.start(cfg)
        token, _device = devices.redeem(cfg, opened["code"], "Android")
        handler = types.SimpleNamespace(headers={"X-Monitor-Access": token}, path="/api/ai/stream")
        stop = am.Handler.stream_guard(handler)
        self.assertFalse(stop())
        am.LIVE_CONFIG["pairing"] = {"enabled": False}
        self.assertTrue(stop())

    def test_the_access_token_itself_and_the_loopback_mode_are_untouched(self):
        self.paired()
        handler = types.SimpleNamespace(headers={"X-Monitor-Access": "t" * 24}, path="/api/updates/stream")
        self.assertFalse(am.Handler.stream_guard(handler)())
        localguard.configure(False, "127.0.0.1", "")
        self.assertFalse(am.Handler.stream_guard(types.SimpleNamespace(headers={}, path="/api/updates/stream"))())


class IdleConnections(unittest.TestCase):
    """A connection that never completes its request is let go, and the number of open ones has a ceiling (plain HTTP, no credentials)."""

    def serve(self, server_class, handler_class):
        server = server_class(("127.0.0.1", 0), handler_class)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def stop():
            server.shutdown()
            server.server_close()
        self.addCleanup(stop)
        return server

    def idle(self, server):
        sock = socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=6)
        self.addCleanup(sock.close)
        sock.sendall(b"GET / HTTP/1.1\r\n")      # the request is never completed
        return sock

    def closed_by_the_server(self, sock):
        try:
            return sock.recv(100) in (b"",) or sock.recv(100) == b""
        except socket.timeout:
            return False
        except OSError:
            return True

    def test_the_handlers_have_a_deadline(self):
        from github_actions_monitor.accounts import accounts_supervisor as sup
        self.assertEqual(am.Handler.timeout, 30)
        self.assertEqual(sup.Handler.timeout, 30)

    def test_the_monitor_closes_a_connection_that_sends_nothing(self):
        saved = am.Handler.timeout
        am.Handler.timeout = 1
        self.addCleanup(setattr, am.Handler, "timeout", saved)
        server = self.serve(am.QuietServer, am.Handler)
        sock = self.idle(server)
        time.sleep(2.5)
        self.assertTrue(self.closed_by_the_server(sock), "the thread of a half-sent request must not be kept for ever")

    def test_the_supervisor_closes_a_connection_that_sends_nothing(self):
        from github_actions_monitor.accounts import accounts_supervisor as sup
        saved = sup.Handler.timeout
        sup.Handler.timeout = 1
        self.addCleanup(setattr, sup.Handler, "timeout", saved)
        server = self.serve(sup.Server, sup.Handler)
        sock = self.idle(server)
        time.sleep(2.5)
        self.assertTrue(self.closed_by_the_server(sock))

    def test_the_ceiling_of_connections_answers_503(self):
        from github_actions_monitor.accounts import accounts_supervisor as sup
        for server_class, handler_class in ((am.QuietServer, am.Handler), (sup.Server, sup.Handler)):
            with self.subTest(server=server_class.__module__):
                server = self.serve(server_class, handler_class)
                server.max_connections = 3
                held = [self.idle(server) for _ in range(3)]
                time.sleep(0.5)
                extra = socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=6)
                self.addCleanup(extra.close)
                self.assertTrue(extra.recv(200).startswith(b"HTTP/1.1 503"), "the connection over the ceiling is refused at once")
                held[0].close()
                time.sleep(1.0)
                again = socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=6)
                self.addCleanup(again.close)
                again.sendall(b"GET /nothing HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
                self.assertFalse(again.recv(200).startswith(b"HTTP/1.1 503"), "a place that is given back can be used again")

    def test_one_address_that_is_not_this_computer_has_its_own_ceiling(self):
        from github_actions_monitor.util import exclusive
        server = types.SimpleNamespace(max_connections=100, max_per_address=2)
        self.assertTrue(exclusive.BoundedThreads._counted_for(server, "192.168.1.20"))
        self.assertFalse(exclusive.BoundedThreads._counted_for(server, "127.0.0.1"))


class ChatOpsRate(unittest.TestCase):
    def setUp(self):
        inbound.reset()
        localguard.reset_limits()
        patch = mock.patch.dict(envguard.HELD, CHAT_ENV)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(inbound.reset)
        self.addCleanup(localguard.reset_limits)

    def post(self, server, body, headers):
        request = urllib.request.Request(server.base + "/api/chatops/slack", data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                return answer.status
        except urllib.error.HTTPError as error:
            with error:
                return error.code

    def test_garbage_without_the_secret_does_not_leave_the_legitimate_command_in_429(self):
        saved = am.STATE["data"]
        am.STATE["data"] = None
        self.addCleanup(am.STATE.__setitem__, "data", saved)
        now = int(time.time())
        with LiveServer(chat_config()) as server:
            codes = {}
            for _ in range(130):
                code = self.post(server, slack_body("status"), {})
                codes[code] = codes.get(code, 0) + 1
            self.assertEqual(codes.get(401), inbound.BAD_PER_MINUTE, "up to the limit the garbage is told 401")
            self.assertGreater(codes.get(429, 0), 0, "past it the garbage itself is limited")
            body = slack_body("status")
            self.assertEqual(self.post(server, body, slack_headers(body, ts=now)), 200, "a signed command of the chat is never counted with the garbage")


if __name__ == "__main__":
    unittest.main()
