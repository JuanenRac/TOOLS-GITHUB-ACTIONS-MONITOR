# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--help`, `--version` and the other flags that only answer must work while a monitor already listens on the port (the one of the person who runs the tests): the check that stops a second monitor on a
port used to run before the flags were read, so `--help` failed on a computer with a running monitor (and the release gate with it)."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
from github_actions_monitor.app import actions_monitor as am  # noqa: E402


class Health(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"ok": True, "version": "9.9.9"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class InformingFlags(unittest.TestCase):
    def test_the_flags_that_only_answer_are_named(self):
        for flag in ("--help", "-h", "--version", "--about", "--doctor", "--help-topics", "--help-search"):
            self.assertIn(flag, am.INFO_FLAGS)
        old = sys.argv
        try:
            sys.argv = ["actions_monitor.py", "--port", "8765"]
            self.assertFalse(am.only_informs())
            sys.argv = ["actions_monitor.py", "--help"]
            self.assertTrue(am.only_informs())
        finally:
            sys.argv = old

    def test_help_answers_while_a_monitor_is_on_the_port(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Health)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = str(server.server_address[1])
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, **{f"MONITOR_{k}_DIR": str(Path(tmp) / k.lower()) for k in ("CONFIG", "DATA", "LOGS", "AI")}}
            for flag in ("--help",):
                done = subprocess.run([sys.executable, "-I", str(HERE / "bin" / "actions_monitor.py"), "--port", port, flag], capture_output=True, text=True, timeout=60, cwd=tmp, env=env)
                self.assertEqual(done.returncode, 0, (flag, done.stdout[-300:], done.stderr[-300:]))
                self.assertNotIn("already answers", done.stdout)


if __name__ == "__main__":
    unittest.main()
