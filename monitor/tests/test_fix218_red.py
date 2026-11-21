# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Regression tests of the network and access fixes: a stream of a revoked device ends, a connection that sends nothing is let go and the number of open connections has a ceiling, the chat receiver
counts only bad signatures against an address, the paths of this computer are not given to a client of the network, the webhook has a freshness window and keeps only the links of GitHub, and the
supervisor lets the chat through, takes the largest body of its accounts and answers the 413 after reading the body."""
import json
import os
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
import test_182_supervisor as t182  # noqa: E402
from github_actions_monitor.accounts import accounts, accounts_supervisor as sup  # noqa: E402
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


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


class PathsForClients(unittest.TestCase):
    TOKEN = "t" * 24

    def get(self, server, headers):
        request = urllib.request.Request(server.base + "/api/paths", headers={"X-Monitor-Access": self.TOKEN, **headers})
        with urllib.request.urlopen(request, timeout=8) as answer:
            return json.loads(answer.read())

    def test_a_client_of_the_network_gets_no_absolute_path_and_this_computer_does(self):
        with LiveServer({}, network=self.TOKEN) as server:
            remote = self.get(server, {"X-Forwarded-For": "192.168.1.50"})
            self.assertEqual([x for x in strings(remote) if os.path.isabs(x) or "\\" in x or ":/" in x], [], "no folder of this computer for a client of the network")
            self.assertIn("actions_monitor.json", remote["config_file"])
            here = self.get(server, {})
            self.assertTrue(os.path.isabs(here["config_file"]) and os.path.isabs(here["product_folder"]))


STUB = r'''
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
account, port = sys.argv[1], int(sys.argv[2])


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            return self.send(200, {"ok": True, "version": "9.9.9", "loaded": True, "offline": False, "account": account, "credential": {"state": "ok", "reason": ""}, "cycle": {"stuck": False}})
        if path == "/api/live-events/stream":
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-store"); self.end_headers()
            try:
                self.wfile.write(b"event: hello\ndata: {}\n\n"); self.wfile.flush()
                for _ in range(24):
                    time.sleep(0.5)
                    self.wfile.write(b": keepalive\n\n"); self.wfile.flush()
            except OSError:
                pass
            return
        self.send(404, {})

    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0)
        got = 0
        while got < size:
            chunk = self.rfile.read(min(65536, size - got))
            if not chunk:
                break
            got += len(chunk)
        route = self.path.split("?")[0]
        if route in ("/api/webhook", "/api/chatops/slack", "/api/chatops/discord"):
            return self.send(200, {"account": account, "route": route, "bytes": got, "peer": self.headers.get("X-Monitor-Peer"), "slack": self.headers.get("X-Slack-Signature"), "host": self.headers.get("Host")})
        self.send(404, {})


ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
'''


class Supervised(unittest.TestCase):
    """The real supervisor (its handler and its loop) in front of two accounts that are a small stub: the way the requests of a client of the network travel."""
    names = ("alpha", "beta")
    account_config = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(self.base / "accounts")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in self.names:
            accounts.create_account(name, name + "-owner")
            more = self.account_config.get(name)
            if more:
                path = accounts.config_path(name)
                data = json.loads(path.read_text(encoding="utf-8"))
                data.update(more)
                path.write_text(json.dumps(data), encoding="utf-8")
        script = self.base / "stub218.py"
        script.write_text(STUB, encoding="utf-8")
        self.supervisor = sup.Supervisor(command_for=lambda account_id, port: [sys.executable, "-I", str(script), account_id, str(port)], port_start=t182.free_stretch())
        self.addCleanup(self.supervisor.stop)
        self.supervisor.sync()
        for _ in range(60):
            self.supervisor.check()
            if all(c.health is not None for c in self.supervisor.children.values()):
                break
            time.sleep(0.25)
        sup.SUPERVISOR["obj"] = self.supervisor
        self.addCleanup(lambda: sup.SUPERVISOR.update(obj=None))
        self.server = sup.Server(("127.0.0.1", 0), sup.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close()))
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.saved_state = dict(localguard.STATE)
        self.addCleanup(self.put_back)

    def put_back(self):
        localguard.STATE.clear()
        localguard.STATE.update(self.saved_state)
        localguard.reset_limits()

    def network(self, token="t" * 24):
        localguard.configure(True, "127.0.0.1", token)
        return {"X-Monitor-Access": token}

    def request(self, path, headers=None, data=None, method=None):
        return t182.get(self.url + path, headers=headers, data=data, method=method)


class SupervisorPaths(Supervised):
    def test_a_client_of_the_network_gets_no_absolute_path_and_this_computer_does(self):
        key = self.network()
        status, remote, _ = self.request("/api/paths", {**key, "X-Forwarded-For": "192.168.1.50"})
        self.assertEqual(status, 200)
        self.assertEqual([x for x in strings(remote) if os.path.isabs(x)], [])
        status, here, _ = self.request("/api/paths", key)
        self.assertTrue(os.path.isabs(here["config_file"]))


class WebhookWindow(unittest.TestCase):
    """The memory of the deliveries and the freshness window leave no gap, and a link of a delivery only points to GitHub."""
    SECRET = "m" * 40
    CONFIG = {"webhook": {"enabled": True}}

    def setUp(self):
        from github_actions_monitor.security import webhook
        self.webhook = webhook
        webhook.reset()
        localguard.reset_limits()
        self.addCleanup(localguard.reset_limits)
        self.addCleanup(webhook.reset)
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: self.SECRET})
        patch.start()
        self.addCleanup(patch.stop)

    def stamp(self, seconds_ago):
        from datetime import datetime, timezone
        return datetime.fromtimestamp(time.time() - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def raw(self, n, ago=0):
        return json.dumps({"repository": {"name": "R", "full_name": "JuanenRac/R"}, "workflow_run": {"id": n + 1, "updated_at": self.stamp(ago), "status": "completed", "name": "CI"}}).encode()

    def deliver(self, raw, n, config=None):
        headers = {"X-GitHub-Event": "workflow_run", "X-Hub-Signature-256": self.webhook.sign(self.SECRET, raw), "X-GitHub-Delivery": f"{n:08d}-aaaa-bbbb"}
        return self.webhook.handle(config or self.CONFIG, raw, headers, ["R"])

    def at(self, seconds_later):
        return mock.patch.object(self.webhook, "time", types.SimpleNamespace(time=lambda: time.time() + seconds_later))

    def test_a_captured_delivery_is_a_duplicate_until_it_is_stale_and_stale_after_with_the_defaults(self):
        raw = self.raw(1)
        self.assertEqual(self.deliver(raw, 1)[0], 200)
        with self.at(3700):      # past replay_seconds (3600) but inside the skew: the memory still has it
            code, answer, _ = self.deliver(raw, 1)
            self.assertEqual((code, answer.get("duplicate")), (202, True))
        with self.at(4000):      # the memory may have let it go: the event itself is older than the window
            code, answer, _ = self.deliver(raw, 1)
            self.assertEqual((code, answer.get("stale")), (202, True))
        self.assertTrue(self.webhook.guard_settings({})["reject_stale"])
        self.assertFalse(self.webhook.guard_settings({"webhook": {"reject_stale": False}})["reject_stale"], "the owner can still turn it off")

    def test_a_thousand_other_deliveries_do_not_make_the_memory_forget_one(self):
        raw = self.raw(0)
        self.assertEqual(self.deliver(raw, 0)[0], 200)
        for n in range(1, 1100):
            self.deliver(self.raw(n), n)
        code, answer, _ = self.deliver(raw, 0)
        self.assertEqual((code, answer.get("duplicate")), (202, True), "the window is the time, not a count of a thousand")
        self.assertGreaterEqual(self.webhook.MAX_DELIVERIES, 10000)

    def event(self, url):
        body = json.dumps({"repository": {"name": "R", "full_name": "JuanenRac/R"}, "workflow_run": {"id": 5, "html_url": url, "status": "completed", "conclusion": "failure"}}).encode()
        return self.webhook.parse_event("workflow_run", body)

    def test_only_a_link_to_github_is_kept(self):
        self.assertEqual(self.event("https://github.com/JuanenRac/R/actions/runs/5")["url"], "https://github.com/JuanenRac/R/actions/runs/5")
        self.assertIsNone(self.event("https://evil.example/JuanenRac/R/actions/runs/5")["url"])
        self.assertIsNone(self.event("https://github.com.evil.example/JuanenRac/R/actions/runs/5")["url"])
        with mock.patch.dict(os.environ, {"GH_HOST": "ghe.corp.example"}):
            self.assertEqual(self.event("https://ghe.corp.example/JuanenRac/R/actions/runs/5")["url"], "https://ghe.corp.example/JuanenRac/R/actions/runs/5")
            self.assertIsNone(self.event("https://evil.example/JuanenRac/R/actions/runs/5")["url"])
        self.assertIsNone(self.event("https://ghe.corp.example/JuanenRac/R/actions/runs/5")["url"], "without GH_HOST that host is not GitHub")


class SupervisorDeliveries(Supervised):
    account_config = {"alpha": {"webhook": {"max_body_kb": 4096}}}

    def post(self, path, body, headers=None):
        return self.request(path, headers={"Content-Type": "application/json", **(headers or {})}, data=body, method="POST")

    def test_the_chat_gets_through_with_a_host_that_is_not_ours_and_without_the_access_token(self):
        self.network()      # network mode: Slack has no access token and a tunnel changes the Host
        status, answer, _ = self.post("/api/chatops/slack", b"command=%2Fmonitor&text=status", {"Host": "abc.trycloudflare.com", "X-Slack-Signature": "v0=00", "X-Slack-Request-Timestamp": "1"})
        self.assertEqual(status, 200, answer)
        self.assertEqual((answer["route"], answer["account"], answer["slack"]), ("/api/chatops/slack", "alpha", "v0=00"))
        self.assertTrue(answer["peer"], "the account is told who sent it")
        status, answer, _ = self.post("/api/chatops/discord?account=beta", b"{}", {"Host": "abc.trycloudflare.com"})
        self.assertEqual((status, answer["account"], answer["route"]), (200, "beta", "/api/chatops/discord"))

    def test_a_delivery_over_one_mib_reaches_the_account_that_admits_it(self):
        status, answer, _ = self.post("/api/webhook?account=alpha", b"x" * (2 * 1024 * 1024), {"X-GitHub-Event": "push"})
        self.assertEqual((status, answer.get("bytes")), (200, 2 * 1024 * 1024))

    def test_a_body_over_every_limit_gets_its_413_after_being_read(self):
        import http.client
        size = 20 * 1024 * 1024
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/api/webhook?account=alpha")
        connection.putheader("Content-Length", str(size))
        connection.endheaders()
        sent = 0
        try:
            while sent < size:
                connection.sock.sendall(b"y" * 65536)
                sent += 65536
        except OSError:
            pass
        self.assertEqual(connection.getresponse().status, 413, "the sender sees the answer and not a cut connection")
        status, _answer, _ = self.post("/api/webhook?account=alpha", b"x" * (3 * 1024 * 1024), {})
        self.assertEqual(status, 200)

    def test_a_delivery_over_the_limit_of_every_account_is_refused(self):
        status, _answer, _ = self.post("/api/webhook?account=beta", b"x" * (5 * 1024 * 1024), {})
        self.assertEqual(status, 413, "4 MiB is the most any account admits")


class SupervisorStream(Supervised):
    def open_stream(self, headers=None):
        import http.client
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        self.addCleanup(connection.close)
        started = time.time()
        connection.request("GET", "/api/live-events/stream?account=alpha", headers=headers or {})
        answer = connection.getresponse()
        return connection, answer, started

    def test_a_stream_of_an_account_reaches_the_client_as_it_is_written(self):
        _connection, answer, started = self.open_stream()
        self.assertEqual(answer.status, 200)
        self.assertIn("text/event-stream", answer.getheader("Content-Type"))
        first = answer.fp.readline()
        self.assertEqual(first, b"event: hello\n", "the first frame arrives while the account still holds the stream")
        self.assertLess(time.time() - started, 4, "the supervisor did not wait for the account to close the stream")

    def test_closing_the_client_lets_the_supervisor_go_of_the_account(self):
        connection, answer, _started = self.open_stream()
        answer.fp.readline()
        connection.close()
        time.sleep(1.5)
        self.assertEqual(self.request("/api/health")[0], 200, "the supervisor keeps answering")

    def test_revoking_a_device_ends_the_stream_the_supervisor_passes_on(self):
        saved = (dict(am.LIVE_CONFIG), dict(localguard.DEVICE_CHECK))

        def put_back():
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(saved[0])
            localguard.DEVICE_CHECK.clear()
            localguard.DEVICE_CHECK.update(saved[1])
            for device in devices.list_devices():
                devices.revoke(device["id"])
        self.addCleanup(put_back)
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, "pairing": {"enabled": True}})
        localguard.DEVICE_CHECK["fn"] = am._device_token_ok
        self.network()
        cfg = devices.settings(am.LIVE_CONFIG)
        token, device = devices.redeem(cfg, devices.start(cfg)["code"], "Android")
        connection, answer, started = self.open_stream({"Authorization": "Bearer " + token})
        self.assertEqual(answer.status, 200)
        self.assertEqual(answer.fp.readline(), b"event: hello" + bytes([10]))
        self.assertTrue(devices.revoke(device["id"]))
        deadline = time.time() + 8
        ended = False
        while time.time() < deadline:
            if not answer.fp.readline():
                ended = True
                break
        self.assertTrue(ended, "the stream ended at once, not when the account closed it")
        self.assertLess(time.time() - started, 9)


if __name__ == "__main__":
    unittest.main()
