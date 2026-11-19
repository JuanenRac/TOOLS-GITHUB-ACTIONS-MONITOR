# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The routes that only the person at this computer may use, behind a REAL reverse proxy on the same machine (a small proxy of the test that forwards the requests over a socket, adds what proxies add and
sits on loopback, so that every client looks local to the monitor). Three cases: a proxy that adds the usual forwarding headers (the monitor refuses), a naive proxy that adds nothing and a monitor
that was not told about it (the weak point, written down with what protects it), and the same naive proxy once the owner declares it (the main door is closed, the second door still works)."""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.security import localguard  # noqa: E402
from test_164 import LiveServer  # noqa: E402

ACCESS = "a" * 24
ROUTE = "/api/alerts/mute"      # one of the routes that only this computer may use; with an empty body it changes nothing


def make_proxy(target, add):
    class Proxy(BaseHTTPRequestHandler):
        def do_POST(self):    # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            headers = {"Content-Type": "application/json", "X-Monitor-Access": ACCESS, "X-Monitor-Token": self.headers.get("X-Monitor-Token", ""), **add}
            request = urllib.request.Request(target + self.path, data=body, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=10) as answer:
                    code, data = answer.status, answer.read()
            except urllib.error.HTTPError as error:
                code, data = error.code, error.read()
            self.send_response(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def post(base, token=""):
    request = urllib.request.Request(base + ROUTE, data=b"{}", method="POST", headers={"Content-Type": "application/json", "X-Monitor-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            return answer.status, json.loads(answer.read() or b"{}")
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, (json.loads(raw) if raw.startswith(b"{") else {})


class BehindARealProxy(unittest.TestCase):
    def run_case(self, add, declared=False):
        with LiveServer(network=ACCESS) as server:
            if declared:
                localguard.configure(True, "127.0.0.1", ACCESS, (), behind_proxy=True)
            token = server.call("/api/session-token", headers={"X-Monitor-Access": ACCESS})[1]["token"]
            proxy = make_proxy(server.base, add)
            try:
                base = f"http://127.0.0.1:{proxy.server_address[1]}"
                return post(base, token), server.base, token
            finally:
                proxy.shutdown()
                proxy.server_close()

    def test_a_proxy_that_adds_the_usual_headers_is_refused_with_local_only(self):
        for header in ("X-Forwarded-For", "Forwarded", "X-Real-IP", "X-Forwarded-Host", "X-Forwarded-Proto"):
            (code, body), _base, _token = self.run_case({header: "203.0.113.9"})
            self.assertEqual(code, 403, header)
            self.assertEqual((body.get("errors") or {}).get("_"), "local_only", header)

    def test_the_person_at_the_computer_is_not_refused_directly(self):
        with LiveServer(network=ACCESS) as server:
            token = server.call("/api/session-token", headers={"X-Monitor-Access": ACCESS})[1]["token"]
            code, body = server.call(ROUTE, {}, {"X-Monitor-Access": ACCESS, "X-Monitor-Token": token})
            self.assertNotEqual((body.get("errors") or {}).get("_") if isinstance(body, dict) else None, "local_only", (code, body))

    def test_a_naive_proxy_that_adds_nothing_looks_local_until_the_owner_declares_it(self):
        # the written-down weak point: a proxy on loopback that forwards no header cannot be told from the person at the computer. What protects it: the owner declares the proxy
        # (`listen.trusted_proxy`, `listen.proxy_public_host` or `listen.local_port`), which closes the main door; the case below proves that it does.
        (code, body), _base, _token = self.run_case({})
        self.assertNotEqual((body.get("errors") or {}).get("_"), "local_only", (code, body))

    def test_the_same_naive_proxy_is_refused_once_it_is_declared(self):
        (code, body), _base, _token = self.run_case({}, declared=True)
        self.assertEqual(code, 403)
        self.assertEqual((body.get("errors") or {}).get("_"), "local_only")


if __name__ == "__main__":
    unittest.main()
