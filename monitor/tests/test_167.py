# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.7: the same-origin guard behind an HTTPS proxy on the default port (`listen.proxy_public_host`): the proxy forwards `Host` and `Origin` without a port, so that one
name is accepted as it is, only under an HTTPS session, and nothing else loses its port."""
import http.client
import http.server
import json
import os
import ssl
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import localguard  # noqa: E402
import settings_api  # noqa: E402
from test_164 import LiveServer  # noqa: E402
from test_166 import make_certificate  # noqa: E402

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


def _openssl_on_path():
    """The `openssl` of the machine, also the one that comes with Git for Windows when it is not on the PATH (the certificate of the test is made with it and stored nowhere)."""
    extra = [p for p in (r"C:\Program Files\Git\usr\bin", r"C:\Program Files\Git\mingw64\bin") if os.path.isdir(p)]
    return mock.patch.dict(os.environ, {"PATH": os.pathsep.join(extra + [os.environ.get("PATH", "")])})


def _forwarder(backend_port, public_name):
    """The request handler of a reverse proxy that ends the TLS and forwards `Host` and `Origin` WITHOUT a port, as a proxy on the default port 443 does."""
    class Forward(http.server.BaseHTTPRequestHandler):
        def forward(self):
            size = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(size) if size else None
            headers = {k: v for k, v in self.headers.items() if k.lower() in ("origin", "content-type", "x-monitor-access", "x-monitor-token", "cookie")}
            headers["Host"] = self.headers.get("Host") or public_name      # like `proxy_set_header Host $host;`: the name the client used, without a port
            connection = http.client.HTTPConnection("127.0.0.1", backend_port, timeout=15)
            try:
                connection.request(self.command, self.path, body, headers)
                answer = connection.getresponse()
                data = answer.read()
                self.send_response(answer.status)
                for name, value in answer.getheaders():
                    if name.lower() in ("content-type", "set-cookie", "cache-control", "location"):
                        self.send_header(name, value)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data)
            finally:
                connection.close()

        do_GET = do_POST = forward

        def log_message(self, *args):
            pass
    return Forward


class HttpsProxyInFront(unittest.TestCase):
    """A real chain: a client over real TLS -> a reverse proxy that ends the TLS and forwards `Host` and `Origin` without a port -> the real monitor over plain HTTP. The proxy is a few
    lines of Python here; the check with nginx or Caddy by hand is `tools/manual_check_live.py proxy`."""

    PROXY_NAME = PUBLIC

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with _openssl_on_path():
            cert, key = make_certificate(self.tmp.name)
        if cert is None:
            self.skipTest("no `openssl` program here: the check by hand is in tools/manual_check_live.py (proxy)")
        self.access = "T" * 24
        live = LiveServer({"session_guard": True}, network=self.access)
        self.live = live.__enter__()
        self.addCleanup(live.__exit__, None, None, None)
        self.proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _forwarder(self.live.server.server_address[1], self.PROXY_NAME))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert, keyfile=key)
        self.proxy.socket = context.wrap_socket(self.proxy.socket, server_side=True)
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.proxy.shutdown(), self.proxy.server_close()))
        self.client_context = ssl.create_default_context()
        self.client_context.check_hostname = False
        self.client_context.verify_mode = ssl.CERT_NONE

    def call(self, method, path, body=None, origin=None, host=None, extra=None):
        """One request through the proxy over TLS: (status, JSON answer or text, headers)."""
        connection = http.client.HTTPSConnection("127.0.0.1", self.proxy.server_address[1], context=self.client_context, timeout=15)
        try:
            headers = {"Host": host or self.PROXY_NAME, "X-Monitor-Access": self.access, "Content-Type": "application/json", **(extra or {})}
            if origin is not None:
                headers["Origin"] = origin
            connection.request(method, path, None if body is None else json.dumps(body), headers)
            answer = connection.getresponse()
            raw = answer.read()
            return answer.status, (json.loads(raw) if raw.startswith((b"{", b"[")) else raw.decode("utf-8", "replace")), dict(answer.getheaders())
        finally:
            connection.close()

    def configure(self, proxy_host):
        localguard.configure(True, "127.0.0.1", self.access, secure=True, proxy_host=proxy_host)

    def save(self, origin, value):
        token = self.call("GET", "/api/session-token", origin=origin)[1]
        token = token["token"] if isinstance(token, dict) else ""
        return self.call("POST", "/api/settings", {"changes": {"refresh_seconds": value}}, origin=origin, extra={"X-Monitor-Token": token})

    def test_a_change_from_the_page_through_the_proxy_reaches_the_settings(self):
        self.configure(self.PROXY_NAME)
        status, answer, _ = self.save(f"https://{self.PROXY_NAME}", 61)
        self.assertEqual(status, 200, answer)

    def test_without_the_setting_the_same_request_is_refused(self):
        self.configure("")
        status, answer, _ = self.call("GET", "/api/session-token", origin=f"https://{self.PROXY_NAME}")
        self.assertEqual(status, 403, answer)
        status, answer, _ = self.call("POST", "/api/settings", {"changes": {"refresh_seconds": 62}}, origin=f"https://{self.PROXY_NAME}")
        self.assertEqual(status, 403, answer)

    def test_a_wrong_scheme_name_or_port_stays_refused_through_the_proxy(self):
        self.configure(self.PROXY_NAME)
        for origin, host in ((f"http://{self.PROXY_NAME}", None), ("https://evil.example", None), (f"https://{self.PROXY_NAME}:8765", None), (f"https://{self.PROXY_NAME}", "evil.example"),
                             ("null", None), (f"https://{self.PROXY_NAME}@evil.example", None)):
            status, answer, _ = self.call("GET", "/api/session-token", origin=origin, host=host)
            self.assertIn(status, (403, 400), (origin, host, answer))

    def test_the_check_by_hand_agrees_with_the_proxy(self):
        """tools/manual_check_live.py proxy, run against this very proxy: it must report that the name is accepted and nothing else is, and never print the token."""
        if not (HERE.parent / "tools" / "manual_check_live.py").is_file():
            self.skipTest("the tools live in the repository, not in the package")
        sys.path.insert(0, str(HERE.parent / "tools"))
        try:
            import manual_check_live
        finally:
            sys.path.pop(0)
        import contextlib
        import io
        port = str(self.proxy.server_address[1])
        env = {"MONITOR_ACCESS_TOKEN": self.access, "MONITOR_CHECK_INSECURE": "1"}
        for proxy_host, expected in ((self.PROXY_NAME, "The proxy name is accepted and nothing else is."), ("", "check(s) failed")):
            self.configure(proxy_host)
            out = io.StringIO()
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
                manual_check_live.proxy_check([self.PROXY_NAME, port, "127.0.0.1"])
            self.assertIn(expected, out.getvalue())
            self.assertNotIn(self.access, out.getvalue())
        self.assertEqual(out.getvalue().count("FAIL"), 1, out.getvalue())      # without the setting only the first check fails: the three that must be refused still are

    def test_the_session_can_be_opened_through_the_proxy_and_the_cookie_is_secure(self):
        self.configure(self.PROXY_NAME)
        status, answer, headers = self.call("POST", "/api/access", {"token": self.access}, origin=f"https://{self.PROXY_NAME}")
        self.assertEqual(status, 200, answer)
        cookie = headers.get("Set-Cookie", "")
        for part in ("HttpOnly", "SameSite=Strict", "Secure"):
            self.assertIn(part, cookie)
        status, answer, _ = self.call("POST", "/api/access", {"token": "wrong" * 5}, origin=f"https://{self.PROXY_NAME}")
        self.assertEqual(status, 401, answer)


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
