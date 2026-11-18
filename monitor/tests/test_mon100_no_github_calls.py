# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A counter of requests to GitHub that must stay at zero: while the page, the comparison and the briefs for the AIs answer, nothing leaves the computer (no connection to a host that is not this one, no `gh`
or `git` process). The counter is put in the places every outgoing request goes through; a test that proves the counter works makes sure it cannot stay at zero because it counts nothing."""
import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.compare import compare_service as service  # noqa: E402
from github_actions_monitor.scoring import ledger as score_ledger  # noqa: E402
from github_actions_monitor.storage import file_storage, runtime  # noqa: E402
from test_compare_service import NOW, make_ledger  # noqa: E402

CONFIG = {"compare": {"enabled": True, "min_runs_per_window": 5}}
LOOPBACK = ("127.0.0.1", "::1", "localhost")


class Counter:
    """What tried to leave the computer."""

    def __init__(self):
        self.calls = []
        real_connect = socket.socket.connect
        real_run = subprocess.run
        real_popen = subprocess.Popen.__init__

        def connect(sock, address, *a, **k):
            host = address[0] if isinstance(address, tuple) else str(address)
            if host not in LOOPBACK:
                self.calls.append(("connect", host))
                raise OSError("blocked by the counter")
            return real_connect(sock, address, *a, **k)

        def run(args, *a, **k):
            first = (args if isinstance(args, (list, tuple)) else str(args).split())[0]
            if Path(str(first)).stem.lower() in ("gh", "git"):
                self.calls.append(("process", str(first)))
                raise OSError("blocked by the counter")
            return real_run(args, *a, **k)

        def popen(proc, args, *a, **k):
            first = (args if isinstance(args, (list, tuple)) else str(args).split())[0]
            if Path(str(first)).stem.lower() in ("gh", "git"):
                self.calls.append(("process", str(first)))
                raise OSError("blocked by the counter")
            return real_popen(proc, args, *a, **k)

        self.patches = [mock.patch.object(socket.socket, "connect", connect), mock.patch.object(subprocess, "run", run), mock.patch.object(subprocess.Popen, "__init__", popen)]

    def __enter__(self):
        for patch in self.patches:
            patch.start()
        return self

    def __exit__(self, *exc):
        for patch in reversed(self.patches):
            patch.stop()


class TheCounterWorks(unittest.TestCase):
    def test_a_connection_out_and_a_gh_process_are_counted_and_refused(self):
        with Counter() as counter:
            with self.assertRaises(OSError):
                socket.create_connection(("203.0.113.7", 443), timeout=1)
            with self.assertRaises(OSError):
                subprocess.run(["gh", "api", "rate_limit"])
        self.assertEqual([c[0] for c in counter.calls], ["connect", "process"])

    def test_the_loopback_is_not_counted(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with Counter() as counter:
            socket.create_connection(server.getsockname(), timeout=2).close()
        server.close()
        self.assertEqual(counter.calls, [])


class Answers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = file_storage.FileStorage(Path(self.tmp.name))
        self.storage.save_doc("alpha", score_ledger.LEDGER_DOC, make_ledger())
        service.clear_cache()
        self.addCleanup(service.clear_cache)
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"
        for patch in (mock.patch.object(runtime, "process_storage", return_value=(self.storage, "alpha")), mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=CONFIG),
                      mock.patch("time.time", return_value=NOW), mock.patch.dict(actions_monitor.LITE, {"on": False}), mock.patch.dict(actions_monitor.DEMO, {"on": False})):
            patch.start()
            self.addCleanup(patch.stop)

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=15) as answer:
            return answer.status, answer.read().decode("utf-8")

    def test_the_comparison_in_every_format_makes_zero_requests_to_github(self):
        with Counter() as counter:
            for query in ("window=7&days=all", "days=workdays", "format=csv", "format=ndjson"):
                self.assertEqual(self.get("/api/compare?" + query)[0], 200, query)
        self.assertEqual(counter.calls, [])

    def test_the_index_and_the_briefs_make_zero_requests_to_github(self):
        with Counter() as counter:
            self.assertEqual(json.loads(self.get("/api/ai/index")[1])["kind"], "ai-index")
            self.assertEqual(json.loads(self.get("/api/ai/briefs")[1])["kind"], "ai-briefs")
            self.assertEqual(json.loads(self.get("/api/ai/briefs?tab=sent")[1])["tab"], "sent")
        self.assertEqual(counter.calls, [])


if __name__ == "__main__":
    unittest.main()
