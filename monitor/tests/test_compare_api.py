# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""GET /api/compare through the real handler: the answer, the 400 codes, the exports, the roles, the demo, the Lite edition, and the account of the process (no data of another account)."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.compare import service  # noqa: E402
from github_actions_monitor.scoring import ledger as score_ledger  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402
from github_actions_monitor.storage import file_storage, runtime  # noqa: E402
from test_compare_service import NOW, make_ledger  # noqa: E402

CONFIG = {"compare": {"enabled": True, "min_runs_per_window": 5}}


class Route(unittest.TestCase):
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
        patches = [mock.patch.object(runtime, "process_storage", return_value=(self.storage, "alpha")), mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=CONFIG),
                   mock.patch("time.time", return_value=NOW), mock.patch.dict(actions_monitor.LITE, {"on": False}), mock.patch.dict(actions_monitor.DEMO, {"on": False})]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as answer:
                return answer.status, answer.headers.get("Content-Type"), answer.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.headers.get("Content-Type"), error.read().decode("utf-8")

    def test_the_answer_has_the_figures_the_windows_and_the_quality(self):
        status, kind, body = self.get("/api/compare?window=7&days=all")
        data = json.loads(body)
        self.assertEqual((status, data["schema"], data["state"], data["account"]), (200, 1, "compared", "alpha"))
        self.assertEqual(data["metrics"]["red_rate"]["now"], 0.25)
        self.assertEqual(data["windows"]["now"]["to"], NOW)
        self.assertEqual({"runs_now", "runs_base", "min_runs", "truncated", "reasons"}, set(data["data_quality"]))
        self.assertIn("coverage", data)

    def test_the_filter_reaches_the_figures(self):
        data = json.loads(self.get("/api/compare?days=workdays")[2])
        self.assertEqual(data["metrics"]["red_rate"]["now"], 0.0)

    def test_a_bad_request_is_a_400_with_a_stable_code(self):
        for query, code in (("window=0", "bad_window"), ("days=sometimes", "bad_days"), ("baseline=x", "bad_baseline"), ("from=2027-01-10T00:00:00Z&to=2027-01-05T00:00:00Z", "bad_range"), ("format=xml", "bad_format")):
            status, _, body = self.get("/api/compare?" + query)
            self.assertEqual((status, json.loads(body)["code"]), (400, code), query)

    def test_ndjson_and_csv(self):
        status, kind, body = self.get("/api/compare?format=ndjson")
        self.assertEqual((status, kind.split(";")[0], json.loads(body.splitlines()[0])["metric"]), (200, "application/x-ndjson", "red_rate"))
        status, kind, body = self.get("/api/compare?format=csv")
        self.assertEqual((status, kind.split(";")[0], body.splitlines()[0]), (200, "text/csv", "metric,now,base,delta,direction,state"))

    def test_off_says_off_and_demo_holds_no_history(self):
        with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}):
            self.assertEqual(json.loads(self.get("/api/compare")[2])["state"], "off")
        with mock.patch.dict(actions_monitor.DEMO, {"on": True}):
            self.assertEqual(json.loads(self.get("/api/compare")[2])["state"], "off")

    def test_the_account_of_the_process_is_the_only_one_read(self):
        self.storage.save_doc("beta", score_ledger.LEDGER_DOC, make_ledger())
        with mock.patch.object(runtime, "process_storage", return_value=(self.storage, "gamma")):
            data = json.loads(self.get("/api/compare")[2])
        self.assertEqual((data["account"], data["state"], data["metrics"]), ("gamma", "calibrating", {}))

    def test_a_viewer_may_read_it_and_it_is_not_in_lite(self):
        self.assertEqual(auth.required_role("GET", "/api/compare?window=30"), "viewer")
        self.assertEqual(auth.required_role("POST", "/api/compare"), auth.required_role("POST", "/api/score"))
        status, _, _ = (lambda: self.get("/api/compare"))()
        self.assertEqual(status, 200)
        with mock.patch.dict(actions_monitor.LITE, {"on": True}):
            self.assertEqual(self.get("/api/compare")[0], 404)


if __name__ == "__main__":
    unittest.main()
