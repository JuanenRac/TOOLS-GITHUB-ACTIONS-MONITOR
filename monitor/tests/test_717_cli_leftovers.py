# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command line towards a monitor: `credential reload|replace` asks for the one-use token of the monitor before it writes (as the page does), a token piped in with a BOM is read, the warning about plain
http comes before anything is sent, `--ca-file` does not send an address of this computer through the proxy of the environment, and a refused certificate is told apart from a monitor that is down."""
import contextlib
import io
import json
import ssl
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.cli import monitor_admin, monitor_cli


class Fake(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def reply(self, status, document):
        body = json.dumps(document).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Fake.seen.append(("GET", self.path))
        if self.path.startswith("/api/session-token"):
            self.reply(200, {"required": True, "token": "once-123"})
        else:
            self.reply(200, {"version": "x", "lite": False})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        Fake.seen.append(("POST", self.path, self.headers.get("X-Monitor-Token")))
        if self.headers.get("X-Monitor-Token") != "once-123":
            self.reply(403, {"error": "forbidden", "code": "session_token"})
        else:
            self.reply(200, {"ok": True})


def serve(case):
    Fake.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    case.addCleanup(server.server_close)
    case.addCleanup(server.shutdown)
    return f"http://127.0.0.1:{server.server_address[1]}"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = monitor_cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CredentialWithTheSessionGuard(unittest.TestCase):
    def test_reload_sends_the_one_use_token_the_monitor_asks_for(self):
        url = serve(self)
        code, out, err = run("credential", "reload", "--url", url, "--lang", "en")
        self.assertEqual(code, 0, (out, err))
        posts = [row for row in Fake.seen if row[0] == "POST"]
        self.assertEqual(posts, [("POST", "/api/credential", "once-123")])
        self.assertLess(Fake.seen.index(("GET", "/api/session-token")), Fake.seen.index(posts[0]))


class PipedToken(unittest.TestCase):
    def test_a_bom_in_front_of_a_piped_token_is_dropped(self):
        for raw in (b"\xef\xbb\xbfabc123\r\n", b"abc123\n"):
            fake = mock.Mock()
            fake.buffer = io.BytesIO(raw)
            with mock.patch.object(sys, "stdin", fake):
                self.assertEqual(monitor_cli.read_new_token("-"), "abc123")

    def test_a_text_stream_without_a_buffer_still_works(self):
        with mock.patch.object(sys, "stdin", io.StringIO(chr(0xFEFF) + "abc123\n")):
            self.assertEqual(monitor_cli.read_new_token("-"), "abc123")


class OrderOfTheWarning(unittest.TestCase):
    def test_plain_http_to_another_computer_is_said_before_the_password_leaves(self):
        said = {}

        def sign_in(base, user, password, timeout=8, token=""):
            said["before"] = stderr.getvalue()
            raise monitor_cli.CliError(monitor_cli.EXIT_AUTH, "refused")

        stderr = io.StringIO()
        with mock.patch.object(monitor_cli, "sign_in", sign_in), contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.dict("os.environ", {"MONITOR_PASSWORD": "secret-not-printed"}):
            code = monitor_cli.main(["health", "--url", "http://192.0.2.7:8765", "--user", "ann", "--lang", "en"])
        self.assertEqual(code, monitor_cli.EXIT_AUTH)
        self.assertIn("192.0.2.7", said["before"])
        self.assertNotIn("secret-not-printed", stderr.getvalue())


class CertificateAndProxy(unittest.TestCase):
    def test_a_loopback_https_address_with_an_own_authority_skips_the_proxy(self):
        handlers = {}

        def build(*given):
            handlers["all"] = given
            return mock.Mock(open=mock.Mock(return_value="ok"))

        with mock.patch.dict(monitor_admin.CLIENT, {"ca": __file__}), mock.patch.object(ssl, "create_default_context", return_value=ssl.create_default_context()), \
                mock.patch.object(urllib.request, "build_opener", build):
            monitor_admin.open_url(urllib.request.Request("https://127.0.0.1:18898/api/health"), 5)
            proxies = [h for h in handlers["all"] if isinstance(h, urllib.request.ProxyHandler)]
            self.assertEqual([h.proxies for h in proxies], [{}])
            monitor_admin.open_url(urllib.request.Request("https://monitor.example/api/health"), 5)
            self.assertFalse([h for h in handlers["all"] if isinstance(h, urllib.request.ProxyHandler)])

    def test_a_refused_certificate_is_not_reported_as_a_monitor_that_is_down(self):
        refused = urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed"))
        with mock.patch.object(monitor_cli, "open_url", side_effect=refused), self.assertRaises(monitor_cli.CliError) as caught:
            monitor_cli.fetch("https://monitor.example", "/api/health")
        self.assertEqual(caught.exception.code, monitor_cli.EXIT_DOWN)
        self.assertEqual(caught.exception.text, i18n.t("cli.cert_bad", url="https://monitor.example"))
        down = urllib.error.URLError(ConnectionRefusedError())
        with mock.patch.object(monitor_cli, "open_url", side_effect=down), self.assertRaises(monitor_cli.CliError) as caught:
            monitor_cli.fetch("https://monitor.example", "/api/health")
        self.assertEqual(caught.exception.text, i18n.t("cli.unreachable", url="https://monitor.example"))

    def test_the_message_exists_in_the_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            with i18n.use_language(lang):
                self.assertNotEqual(i18n.t("cli.cert_bad", url="U"), "cli.cert_bad")
                self.assertIn("U", i18n.t("cli.cert_bad", url="U"))


if __name__ == "__main__":
    unittest.main()
