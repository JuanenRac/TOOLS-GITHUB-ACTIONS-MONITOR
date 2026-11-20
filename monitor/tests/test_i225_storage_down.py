# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A storage that stops answering gives a clean 503 with `Retry-After` (never a dropped connection or a traceback), the server keeps running, the next request after the storage is back is served, and the
live stream goes on and can be resumed with Last-Event-ID. The server is a real one on a real port with the SQLite storage bound; only the connection to the database is cut."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402
from github_actions_monitor.storage import runtime, sqlite_storage, state_io  # noqa: E402

PROBE = "/api/_store_probe"


class StorageDown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {"storage": {"backend": "sqlite", "path": str(Path(self.tmp.name) / "m.db")}, "live": {"sse": {"enabled": True, "max_clients": 5}}}
        self.storage = runtime.bind(self.config, "alpha", Path(self.tmp.name))
        self.addCleanup(state_io.unbind)
        self.addCleanup(self.storage.close)
        real = actions_monitor.Handler.handle_get

        def handle_get(handler):      # one route that needs the storage and does not hide its failure
            if handler.path.split("?")[0] == PROBE:
                state_io.save_text(events.STATE_FILE, "{}")
                handler.json_reply({"ok": True})
                return
            real(handler)
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for p in (mock.patch.object(actions_monitor.Handler, "handle_get", handle_get), mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=self.config),
                  mock.patch.object(actions_monitor, "LITE", {"on": False})):
            p.start()
            self.addCleanup(p.stop)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def get(self, path, headers=None):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, headers=headers or {}), timeout=10) as answer:
                return answer.status, dict(answer.headers), answer.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def cut(self):
        return mock.patch.object(self.storage, "_conn", side_effect=sqlite_storage.sqlite3.OperationalError("disk I/O error"))

    def test_a_cut_storage_is_a_clean_503_and_the_next_request_after_it_is_back_is_served(self):
        self.assertEqual(self.get(PROBE)[0], 200)
        self.storage.close()
        before = actions_monitor.STORE_DOWN[0]
        with self.cut():
            status, headers, body = self.get(PROBE)
            self.assertEqual(status, 503)
            self.assertEqual(headers.get("Retry-After"), str(actions_monitor.STORE_RETRY_SECONDS))
            self.assertEqual(json.loads(body)["error"], "storage_unavailable")
            self.assertNotIn(b"Traceback", body)
            self.assertNotIn(b"sqlite", body.lower())      # the text of the database error is not for the visitor
            self.assertEqual(self.get("/api/health")[0], 200, "the routes that do not need the storage still answer")
            self.assertEqual(self.get(PROBE)[0], 503, "and it stays 503 while it is down, with no crash")
        self.assertGreaterEqual(actions_monitor.STORE_DOWN[0], before + 2)
        status, _, body = self.get(PROBE)      # the database is back
        self.assertEqual((status, json.loads(body)["ok"]), (200, True))

    def test_a_missing_file_is_not_taken_for_a_storage_failure(self):
        handler = actions_monitor.Handler.__new__(actions_monitor.Handler)
        self.assertFalse(handler.storage_failure(FileNotFoundError("x")))
        self.assertFalse(handler.storage_failure(ConnectionResetError()))
        self.assertFalse(handler.storage_failure(ValueError("x")))
        cause = sqlite_storage.sqlite3.OperationalError("locked")
        failure = OSError("locked")
        failure.__cause__ = cause
        handler.reply_status = 200      # an answer already on its way: the connection is closed, nothing else is written
        self.assertTrue(handler.storage_failure(failure))
        self.assertTrue(handler.close_connection)

    def test_the_live_stream_goes_on_while_the_storage_is_down_and_resumes_after_a_reconnection(self):
        before = actions_monitor.LIVE_TOTAL[0]
        self.addCleanup(lambda: (actions_monitor.LIVE_EVENTS.clear(), actions_monitor.LIVE_TOTAL.__setitem__(0, before)))
        stream = urllib.request.urlopen(self.base + "/api/live-events/stream", timeout=10)
        hello = ""
        for _ in range(4):
            line = stream.readline().decode()
            hello += line
            if line.startswith("data:"):
                break
        self.assertIn("retry: %d" % webhook.SSE_RETRY_MS, hello, "the browser is told how long to wait before it reconnects")
        self.storage.close()
        with self.cut():
            self.assertEqual(self.get(PROBE)[0], 503)
            actions_monitor.LIVE_EVENTS.append({"event": "workflow_run", "repo": "o/during", "status": "completed", "conclusion": "failure", "at": "t"})
            actions_monitor.LIVE_TOTAL[0] += 1
            seen = ""
            for _ in range(40):
                line = stream.readline().decode()
                seen += line
                if "o/during" in line:
                    break
            self.assertIn("o/during", seen, "the stream does not depend on the storage")
        stream.close()      # the connection breaks, the browser reconnects with the id of the last frame it got
        actions_monitor.LIVE_EVENTS.append({"event": "workflow_run", "repo": "o/after", "status": "completed", "conclusion": "success", "at": "t"})
        actions_monitor.LIVE_TOTAL[0] += 1
        resumed = urllib.request.urlopen(urllib.request.Request(self.base + "/api/live-events/stream", headers={"Last-Event-ID": str(before + 1)}), timeout=10)
        text = ""
        for _ in range(40):
            line = resumed.readline().decode()
            text += line
            if "o/after" in line:
                break
        resumed.close()
        self.assertIn("o/after", text)
        self.assertNotIn("o/during", text, "what the browser already had is not sent again")


if __name__ == "__main__":
    unittest.main()
