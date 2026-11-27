# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Hardening of what a request, a name or a file can reach: the cookie of the session only ever takes a right token, a file of a secret, of a report or of a workflow stays inside its folder with every
link resolved, the outgoing HTTPS connections refuse old TLS, and the checks of expressions and pictures read their input in one pass."""
import http.client
import os
import ssl
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.accounts import accounts_supervisor  # noqa: E402
from github_actions_monitor.app import orglogo  # noqa: E402
from github_actions_monitor.data_pipeline import meta_columns  # noqa: E402
from github_actions_monitor.integrations import actlocal  # noqa: E402
from github_actions_monitor.reporting import report_service  # noqa: E402
from github_actions_monitor.security import channel_secrets, localguard, netguard, secretstore  # noqa: E402
from test_164 import LiveServer  # noqa: E402

ACCESS = "T" * 24


def link(test, target, name):
    try:
        os.symlink(target, name)
    except (OSError, NotImplementedError):
        test.skipTest("symbolic links are not available here")


class TheCookieOnlyTakesARightToken(unittest.TestCase):
    def ask(self, address, headers):
        with LiveServer({"listen": {"query_access": True}}, network=ACCESS) as live:      # the token in the address counts only with this setting
            connection = http.client.HTTPConnection("127.0.0.1", live.server.server_address[1], timeout=15)
            try:
                connection.request("GET", address, headers={"Accept": "text/html", **headers})
                answer = connection.getresponse()
                answer.read()
                return answer.status, dict(answer.getheaders())
            finally:
                connection.close()

    def test_a_wrong_address_token_never_reaches_a_header_even_with_a_right_cookie(self):
        status, headers = self.ask("/?access=other%0d%0aX-Injected:%20yes", {"Cookie": f"{localguard.COOKIE}={ACCESS}"})
        self.assertNotIn("X-Injected", headers)
        self.assertNotIn("other", headers.get("Set-Cookie", ""))
        self.assertNotEqual(status, 302)

    def test_a_right_address_token_still_opens_the_session(self):
        status, headers = self.ask(f"/?access={ACCESS}", {})
        self.assertEqual(status, 302)
        self.assertIn(f"{localguard.COOKIE}={ACCESS};", headers.get("Set-Cookie", ""))

    def test_an_extra_header_of_the_supervisor_never_carries_a_line_break(self):
        handler = accounts_supervisor.Handler.__new__(accounts_supervisor.Handler)
        sent = []
        handler.send_header = lambda name, value: sent.append((name, value))
        handler.send_response, handler.end_headers, handler.wfile = (lambda code: None), (lambda: None), mock.Mock()
        handler.reply(302, b"", "text/plain", {"Location": "/page\r\nX-Injected: yes"})
        self.assertIn(("Location", "/pageX-Injected: yes"), sent)

    def test_a_value_that_would_add_to_the_answer_is_refused(self):
        for value in ("a\r\nX: y", "a\nb", "a; Domain=example.org", "a\x00"):
            with self.assertRaises(ValueError, msg=repr(value)):
                localguard.cookie_header(value, secure=False)


class FilesStayInTheirFolder(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(os.path.realpath(tmp.name))
        self.outside = self.base / "outside.txt"
        self.outside.write_text("elsewhere", encoding="utf-8")

    def test_the_file_of_a_secret_that_is_a_link_elsewhere_is_neither_read_nor_written(self):
        folder = self.base / "secrets"
        folder.mkdir()
        link(self, self.outside, folder / "notify-user.a.ntfy.600")
        with mock.patch.dict(os.environ, {"MONITOR_SECRET_DIR": str(folder), "MONITOR_SECRET_BACKEND": "file"}):
            self.assertEqual(channel_secrets.get("user.a.ntfy"), "")
            self.assertEqual(channel_secrets.put("user.a.ntfy", "new value"), (False, "write"))
            self.assertFalse(channel_secrets.delete("user.a.ntfy"))
            self.assertEqual(channel_secrets.put("user.b.ntfy", "kept"), (True, "file"))
            self.assertEqual(channel_secrets.get("user.b.ntfy"), "kept")
        self.assertEqual(self.outside.read_text(encoding="utf-8"), "elsewhere")

    def test_a_command_of_the_keychain_that_is_too_long_is_not_sent(self):
        sent = []
        with mock.patch.dict(os.environ, {"MONITOR_SECRET_BACKEND": ""}), mock.patch.object(channel_secrets.shutil, "which", return_value="/usr/bin/security"), \
                mock.patch.object(secretstore, "_run", lambda args, data=None, runner=None: sent.append(data) or (0, "")):
            self.assertEqual(channel_secrets.put("user.a.ntfy", '"' * channel_secrets.MAX_LENGTH, platform="darwin"), (False, "format"))
            self.assertEqual(sent, [])
            self.assertEqual(channel_secrets.put("user.a.ntfy", "short", platform="darwin"), (True, "keychain"))
        self.assertEqual(len(sent), 1)

    def test_a_report_that_is_a_link_elsewhere_is_not_served(self):
        folder = report_service.folder(self.base)
        folder.mkdir(parents=True)
        name = "report_main_20260101-000000.md"
        (folder / name).write_text("a report", encoding="utf-8")
        self.assertEqual(report_service.read_file("main", name, self.base)[0], b"a report")
        other = "report_main_20260102-000000.md"
        link(self, self.outside, folder / other)
        self.assertIsNone(report_service.read_file("main", other, self.base))

    def test_a_workflow_outside_the_clone_is_refused_by_name(self):
        (self.base / "work" / "app" / ".github" / "workflows").mkdir(parents=True)
        (self.base / "work" / "app" / "x.yml").write_text("on: push", encoding="utf-8")
        root = str(self.base / "work")
        self.assertEqual(actlocal.clone_dir(root, "app", "../../x.yml"), (None, "outside"))
        self.assertEqual(actlocal.clone_dir(root, "../work2", "ci.yml"), (None, "outside"))
        self.assertEqual(actlocal.workflow_fingerprint(self.base / "work" / "app", "../../../../outside.txt"), ("", ""))


class OutgoingConnections(unittest.TestCase):
    def test_nothing_older_than_tls_1_2_and_the_certificate_is_checked(self):
        context = netguard.tls_context()
        self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


class OnePassChecks(unittest.TestCase):
    def test_a_repeat_of_a_repeat_is_seen_as_before(self):
        for text in ("(a+)+", "x(a*b){2,}", "(?:\\d+)*", "((a+)", "(a+(b))+", "(ab)(c*)+"):
            expected = bool(__import__("re").search(r"\([^)]*[+*][^)]*\)[+*{]", text))
            self.assertEqual(meta_columns.repeat_of_repeat(text), expected, text)
        for text in ("(a)+", "a+(b)", "(a+)x", "v(\\d+)\\.(\\d+)", "+)+"):
            self.assertFalse(meta_columns.repeat_of_repeat(text), text)

    def test_only_a_link_inside_the_picture_is_accepted(self):
        def problem(body):
            return orglogo.svg_problem(b'<svg xmlns="http://www.w3.org/2000/svg">' + body + b"</svg>")

        self.assertIsNone(problem(b'<use href="#a"/><use xlink:href=\' #b\'/>'))
        for body in (b'<a href="https://example.org/">x</a>', b'<use href=""/>', b"<use href='other.svg#a'/>", b'<use href="unclosed'):
            self.assertEqual(problem(body), "link", body)


if __name__ == "__main__":
    unittest.main()
