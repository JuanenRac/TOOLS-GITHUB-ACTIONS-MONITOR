# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Starting the monitor: one monitor for each port, and the openssl that Git for Windows brings outside the PATH.

1. Two servers of the monitor cannot be bound to the same port (on Windows a shared bind used to let two processes listen on 8765 at once).
2. A start that finds a monitor already answering on its port says so and stops.
3. openssl is found in the places where Git for Windows keeps it, the configured path wins, and a path that is not an openssl is ignored.
"""
import json
import os
import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.integrations import github_app  # noqa: E402
from github_actions_monitor.util import exclusive  # noqa: E402


class Health(BaseHTTPRequestHandler):
    body = b'{"ok": true, "version": "9.9.9"}'

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


class Plain(exclusive.ExclusiveBind, ThreadingHTTPServer):
    pass


def serve(handler=Health):
    server = Plain(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class OnePerPort(unittest.TestCase):
    def test_the_servers_of_the_monitor_bind_for_themselves(self):
        self.assertTrue(issubclass(am.QuietServer, exclusive.ExclusiveBind))
        from github_actions_monitor.accounts import accounts_supervisor
        self.assertTrue(issubclass(accounts_supervisor.Server, exclusive.ExclusiveBind))

    def test_a_second_bind_on_the_same_port_fails(self):
        first = serve()
        self.addCleanup(first.server_close)
        self.addCleanup(first.shutdown)
        with self.assertRaises(OSError):
            Plain(("127.0.0.1", first.server_address[1]), Health).server_close()

    @unittest.skipUnless(os.name == "nt", "the shared bind is a Windows thing")
    def test_on_windows_the_socket_asks_for_the_port_alone(self):
        server = Plain(("127.0.0.1", 0), Health)
        self.addCleanup(server.server_close)
        self.assertFalse(server.allow_reuse_address)
        self.assertTrue(server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE))

    def test_a_port_is_free_again_when_the_server_closes(self):
        first = serve()
        port = first.server_address[1]
        first.shutdown()
        first.server_close()
        again = Plain(("127.0.0.1", port), Health)
        again.server_close()


class IsThereAMonitor(unittest.TestCase):
    def test_a_monitor_is_recognised_by_its_health_route(self):
        server = serve()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.assertTrue(exclusive.monitor_on(server.server_address[1]))

    def test_another_program_or_a_free_port_is_not_a_monitor(self):
        class Other(Health):
            body = b'{"hello": "world"}'
        server = serve(Other)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.assertFalse(exclusive.monitor_on(server.server_address[1]))
        free = socket.socket()
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
        free.close()
        self.assertFalse(exclusive.monitor_on(port))
        self.assertFalse(exclusive.monitor_on(0))
        self.assertFalse(exclusive.monitor_on("8765"))

    def test_the_start_stops_with_a_clear_message_when_a_monitor_is_there(self):
        server = serve()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        printed = []
        with mock.patch.object(sys, "argv", ["actions_monitor.py", "--port", str(port)]), mock.patch.object(am, "accounts_cli", lambda argv: None), \
                mock.patch("builtins.print", lambda *a, **k: printed.append(" ".join(str(x) for x in a))), mock.patch.object(am.paths, "ensure", lambda *a: None), \
                mock.patch.object(am.rootmigrate, "auto", lambda *a: None):
            with mock.patch("github_actions_monitor.integrations.ai_index.write", lambda *a, **k: None):
                code = am.main()
        self.assertEqual(code, 1)
        self.assertTrue(any(str(port) in line and "already" in line for line in printed), printed)

    def test_the_message_is_in_the_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("{port}", data["mon.already_running"], lang)


class WhereIsOpenssl(unittest.TestCase):
    def setUp(self):
        self.addCleanup(github_app.OPENSSL.update, {"configured": ""})
        github_app.OPENSSL["configured"] = ""

    def test_git_for_windows_is_searched_outside_the_path(self):
        env = {"ProgramFiles": "C:\\Program Files", "LOCALAPPDATA": "C:\\Users\\x\\AppData\\Local"}
        wanted = os.path.join("C:\\Program Files", "Git", "usr", "bin", "openssl.exe")
        self.assertEqual(github_app.known_openssl(env, lambda p: p == wanted), [wanted])
        per_user = os.path.join("C:\\Users\\x\\AppData\\Local", "Programs", "Git", "mingw64", "bin", "openssl.exe")
        self.assertIn(per_user, github_app.known_openssl(env, lambda p: p == per_user))
        self.assertEqual(github_app.known_openssl({}, lambda p: False), [])

    def test_the_path_wins_over_the_known_places_and_the_configured_one_wins_over_both(self):
        with mock.patch.object(github_app.shutil, "which", lambda name: "/usr/bin/openssl"):
            self.assertEqual(github_app.find_openssl(lambda p: False, {}), "/usr/bin/openssl")
        github_app.OPENSSL["configured"] = "/opt/ssl/openssl"
        with mock.patch.object(github_app.shutil, "which", lambda name: "/usr/bin/openssl"):
            self.assertEqual(github_app.find_openssl(lambda p: p == "/opt/ssl/openssl", {}), "/opt/ssl/openssl")
            self.assertEqual(github_app.find_openssl(lambda p: False, {}), "/usr/bin/openssl", "a configured file that does not exist is skipped")

    def test_not_in_the_path_it_is_found_where_git_keeps_it(self):
        wanted = os.path.join("C:\\Program Files", "Git", "usr", "bin", "openssl.exe")
        with mock.patch.object(github_app.shutil, "which", lambda name: None):
            self.assertEqual(github_app.find_openssl(lambda p: p == wanted, {"ProgramFiles": "C:\\Program Files"}), wanted)
            self.assertEqual(github_app.find_openssl(lambda p: False, {}), "")

    def test_the_configured_path_must_be_an_openssl(self):
        for good in ("C:\\Git\\usr\\bin\\openssl.exe", "/usr/bin/openssl"):
            self.assertEqual(github_app.settings({"github_app": {"openssl_path": good}})["openssl_path"], good)
        for bad in ("/bin/sh", "C:\\Windows\\cmd.exe", "openssl\n", 7, "x" * 300 + "openssl"):
            self.assertEqual(github_app.settings({"github_app": {"openssl_path": bad}})["openssl_path"], "", bad)

    def test_the_signature_runs_the_program_that_was_found(self):
        seen = []

        class Done:
            returncode, stdout = 0, b"sig"
        with mock.patch.object(github_app, "find_openssl", lambda: "/found/openssl"), mock.patch.object(github_app.subprocess, "run", lambda args, **k: seen.append(args) or Done()):
            self.assertEqual(github_app._sign(b"data", "/key.pem"), b"sig")
        self.assertEqual(seen[0][0], "/found/openssl")

    def test_the_status_and_the_doctor_say_which_one(self):
        with mock.patch.object(github_app, "find_openssl", lambda: "/found/openssl"), mock.patch.object(github_app.shutil, "which", lambda name: None):
            self.assertEqual(github_app.status({})["openssl_path"], "/found/openssl")
            key = Path(__file__)
            status, detail = doctor.github_app_check({"github_app": {"enabled": True, "app_id": "1", "key_path": str(key)}})
            self.assertIn("/found/openssl", detail)
            self.assertEqual(status, "ok", detail)

    def test_the_setting_has_its_texts_in_the_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(data["cfg.f.github_app.openssl_path"] and data["cfg.h.github_app.openssl_path"], lang)
        self.assertIn("github_app.openssl_path", __import__("github_actions_monitor.app.settings_api", fromlist=["FIELDS"]).FIELDS)


if __name__ == "__main__":
    unittest.main()
