# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The export of the log of actions: a destination that is down loses nothing and stops nothing; the file, syslog and HTTP formats against receivers of this computer."""
import json
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import compliance_audit_export as export  # noqa: E402
from github_actions_monitor.security import audit_log  # noqa: E402

NOW = 1_800_000_000.0


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log, self.state = self.root / "audit_actions.jsonl", self.root / "state.json"
        audit_log.FILE = self.log
        self.addCleanup(setattr, audit_log, "FILE", None)
        self.write(5)

    def write(self, count, start=0):
        for i in range(start, start + count):
            audit_log.record({}, "settings_change", "root", "admin", "alpha", f"t{i}", now=NOW + i)

    def run_export(self, block, **options):
        return export.run({"audit_export": dict(block, enabled=True)}, where=self.state, log=self.log, now=NOW, **options)


class Cursor(Base):
    def test_off_or_without_a_destination_nothing_happens(self):
        self.assertEqual(export.run({}, where=self.state, log=self.log)["sent"], 0)
        self.assertFalse(export.active({"audit_export": {"enabled": True}}))
        self.assertFalse(export.active({"airgapped": True, "audit_export": {"enabled": True, "target": "http", "url": "https://x.example"}}))
        self.assertFalse(self.state.exists())

    def test_a_destination_that_is_down_keeps_the_lines_and_takes_them_later_once(self):
        def down(cfg, rows):
            raise OSError("down")
        state = self.run_export({"path": "unused"}, sender=down)
        self.assertEqual((state["sent"], state["cursor"]), (0, ""))
        self.assertIn("down", state["last_error"])
        self.assertGreater(state["backlog_bytes"], 0)
        got = []
        self.write(3, start=5)
        state = self.run_export({"path": "unused", "batch": 3}, sender=lambda cfg, rows: got.extend(rows))
        self.assertEqual([r["target"] for r in got], [f"t{i}" for i in range(8)])
        self.assertEqual((state["sent"], state["backlog_bytes"], state["last_error"]), (8, 0, ""))
        got.clear()
        self.run_export({"path": "unused"}, sender=lambda cfg, rows: got.extend(rows))
        self.assertEqual(got, [])

    def test_lines_rotated_away_before_they_were_sent_are_counted_and_the_lag_is_said(self):
        self.run_export({"path": "x"}, sender=lambda cfg, rows: None)
        self.log.unlink()
        self.write(2, start=50)
        state = self.run_export({"path": "x"}, sender=lambda cfg, rows: None)
        self.assertEqual(state["lost"], 1)
        self.assertTrue(export.lagging({"audit_export": {"enabled": True}}, state))
        self.assertTrue(export.lagging({"audit_export": {"enabled": True, "spool_mb": 1}}, {"backlog_bytes": 2_000_000, "lost": 0}))
        self.assertEqual(export.ALERT_CODE, "system.audit_export_lag")


class Destinations(Base):
    def test_a_file_of_json_lines(self):
        out = self.root / "export.jsonl"
        state = self.run_export({"target": "file", "path": str(out)})
        self.assertEqual(state["sent"], 5)
        self.assertEqual([json.loads(x)["target"] for x in out.read_text(encoding="utf-8").splitlines()], [f"t{i}" for i in range(5)])

    def test_syslog_frames_rfc_5424_over_tcp(self):
        received = bytearray()
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        self.addCleanup(server.close)

        def accept():
            connection, _ = server.accept()
            with connection:
                while chunk := connection.recv(65536):
                    received.extend(chunk)
        thread = threading.Thread(target=accept, daemon=True)
        thread.start()
        block = {"target": "syslog", "host": "127.0.0.1", "port": server.getsockname()[1], "tls": False}
        refused = self.run_export(block)
        self.assertEqual(refused["sent"], 0)      # an address of this computer needs allow_private_targets
        state = self.run_export(dict(block, allow_private_targets=True))
        thread.join(10)
        self.assertEqual(state["sent"], 5, state["last_error"])
        rest, messages = bytes(received), []
        while rest:
            length, _, rest = rest.partition(b" ")
            messages.append(rest[:int(length)].decode("utf-8"))
            rest = rest[int(length):]
        self.assertEqual(len(messages), 5)
        self.assertRegex(messages[0], r"^<110>1 \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ \S+ github-actions-monitor - audit - \{")

    def test_http_batches_with_the_token_of_a_variable_and_never_in_the_error(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.headers.get("Authorization"), self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        block = {"target": "http", "url": f"http://127.0.0.1:{server.server_address[1]}/in", "batch": 2, "allow_private_targets": True, "token_env": "ZZ_EXPORT_TOKEN"}
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"ZZ_EXPORT_TOKEN": "sekret-value"}):
            state = self.run_export(block)
        self.assertEqual((state["sent"], len(seen)), (5, 3), state["last_error"])
        self.assertEqual(seen[0][0], "Bearer sekret-value")
        self.assertNotIn(b"sekret-value", seen[0][1])
        self.assertNotIn("sekret-value", self.state.read_text(encoding="utf-8"))

    def test_the_destination_is_a_row_of_the_table_of_egress(self):
        self.assertEqual(export.hosts({"audit_export": {"enabled": True, "target": "syslog", "host": "Logs.Example.org"}}), ["logs.example.org"])
        self.assertEqual(export.hosts({"audit_export": {"enabled": True, "target": "file", "path": "x"}}), [])


if __name__ == "__main__":
    unittest.main()
