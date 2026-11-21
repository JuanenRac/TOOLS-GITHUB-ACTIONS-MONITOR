# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""With network.use_proxy an https destination is reached through the CONNECT tunnel of the proxy (the proxy receives `CONNECT host:443`, not a TLS hello), and the destination is still judged first."""
import os
import socket
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.security import netguard  # noqa: E402


class FakeProxy:
    def __init__(self, answer=b"HTTP/1.1 200 Connection established\r\n\r\n"):
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(1)
        self.server.settimeout(10)
        self.port = self.server.getsockname()[1]
        self.answer = answer
        self.first = b""
        self.after = b""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            conn, _ = self.server.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(5)
            try:
                while b"\r\n\r\n" not in self.first:
                    chunk = conn.recv(1024)
                    if not chunk:
                        return
                    self.first += chunk
                conn.sendall(self.answer)
                self.after = conn.recv(8)      # what the client sends once the tunnel is open: the TLS hello
            except OSError:
                pass

    def close(self):
        self.server.close()
        self.thread.join(5)


def public(host, port=443, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


class ProxyTunnel(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in ("https_proxy", "HTTPS_PROXY", "no_proxy", "NO_PROXY")}
        self.addCleanup(self.restore)

    def restore(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def use(self, proxy):
        os.environ["https_proxy"] = os.environ["HTTPS_PROXY"] = f"http://127.0.0.1:{proxy.port}"
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = ""

    def test_https_through_the_proxy_starts_with_connect_to_the_destination(self):
        proxy = FakeProxy()
        self.addCleanup(proxy.close)
        self.use(proxy)
        request = urllib.request.Request("https://hooks.example.test/x", data=b"{}", method="POST")
        with self.assertRaises(OSError):      # the fake proxy does not speak TLS: the tunnel opens and then the handshake fails
            netguard.open_url(request, timeout=5, use_proxy=True, resolver=public)
        proxy.thread.join(8)
        self.assertTrue(proxy.first.startswith(b"CONNECT hooks.example.test:443 HTTP/1."), proxy.first[:80])
        self.assertTrue(proxy.after.startswith(b"\x16\x03"), "after the CONNECT answer the client speaks TLS over the tunnel")

    def test_a_proxy_that_refuses_the_tunnel_is_an_error_not_a_plain_request(self):
        proxy = FakeProxy(b"HTTP/1.1 403 Forbidden\r\n\r\n")
        self.addCleanup(proxy.close)
        self.use(proxy)
        with self.assertRaises(OSError):
            netguard.open_url(urllib.request.Request("https://hooks.example.test/x"), timeout=5, use_proxy=True, resolver=public)
        proxy.thread.join(8)
        self.assertTrue(proxy.first.startswith(b"CONNECT hooks.example.test:443"))
        self.assertEqual(proxy.after, b"")

    def test_the_final_destination_is_still_judged_before_the_proxy_gets_anything(self):
        proxy = FakeProxy()
        self.addCleanup(proxy.close)
        self.use(proxy)
        with self.assertRaises(netguard.Refused):
            netguard.open_url(urllib.request.Request("https://10.0.0.5/x"), timeout=5, use_proxy=True)
        self.assertEqual(proxy.first, b"")
        proxy.server.close()


if __name__ == "__main__":
    unittest.main()
