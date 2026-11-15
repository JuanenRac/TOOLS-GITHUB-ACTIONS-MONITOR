# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The score of the whole installation, for information: the mean of the scored accounts weighted by their repositories with a number, who is in it, no number when nobody is scored, and the
route of the supervisor that asks every account it may see."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.accounts import accounts, accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.scoring import overview  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402


def answer(state="scored", score=80.0, letter="B", coverage=0.8, repos=3):
    return {"state": state, "score": score if state == "scored" else None, "letter": letter if state == "scored" else None, "coverage": coverage,
            "repos": [{"repo": f"r{i}", "score": 70.0} for i in range(repos)], "stale": False}


class Combine(unittest.TestCase):
    def test_the_mean_is_weighted_by_the_repositories_that_have_a_number(self):
        out = overview.combine({"a": answer(score=90.0, repos=1), "b": answer(score=60.0, repos=3)})
        self.assertEqual(out["score"], 67.5)          # (90 * 1 + 60 * 3) / 4
        self.assertEqual((out["state"], out["letter"], out["accounts_scored"], out["accounts_total"], out["informative"]), ("scored", "D", 2, 2, True))

    def test_an_account_without_a_number_is_listed_and_left_out(self):
        out = overview.combine({"a": answer(score=90.0, repos=2), "b": answer(state="calibrating"), "c": answer(state="insufficient_data"), "d": None})
        self.assertEqual((out["score"], out["accounts_scored"], out["accounts_total"]), (90.0, 1, 4))
        self.assertEqual({r["account"]: r["state"] for r in out["accounts"]}, {"a": "scored", "b": "calibrating", "c": "insufficient_data", "d": "unreachable"})
        self.assertTrue(all(r["score"] is None for r in out["accounts"] if r["account"] != "a"))

    def test_nobody_scored_is_no_number_and_never_a_100(self):
        for answers, state in (({"a": answer(state="calibrating")}, "calibrating"), ({"a": answer(state="insufficient_data"), "b": None}, "insufficient_data"),
                               ({"a": answer(state="off")}, "off"), ({}, "calibrating"), ({"a": None}, "calibrating")):
            out = overview.combine(answers)
            self.assertEqual((out["state"], out["score"], out["letter"]), (state, None, None), answers)

    def test_the_answer_says_that_security_is_not_in_it(self):
        out = overview.combine({"a": answer()})
        self.assertEqual((out["complete"], out["missing_parts"]), (False, ["security"]))

    def test_a_scored_account_without_a_breakdown_counts_once(self):
        out = overview.combine({"a": {**answer(score=80.0), "repos": []}, "b": answer(score=60.0, repos=1)})
        self.assertEqual(out["score"], 70.0)

    def test_unreadable_answers_are_unreachable(self):
        for bad in (None, [], "x", {"score": 1}, {"state": 3}):
            self.assertEqual(overview.row("a", bad)["state"], "unreachable")

    def test_the_mean_coverage_is_of_the_accounts_in_the_mean(self):
        out = overview.combine({"a": answer(coverage=0.8), "b": answer(coverage=0.6), "c": answer(state="calibrating", coverage=0.0)})
        self.assertEqual(out["coverage"], 0.7)


STUB = r'''
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
account, port, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            return self.send(200, {"ok": True, "version": "9.9.9", "loaded": True, "offline": False, "account": account, "credential": {"state": "ok", "reason": ""}, "cycle": {"stuck": False}})
        if path == "/api/score":
            if mode == "scored80": return self.send(200, {"state": "scored", "score": 80.0, "letter": "B", "coverage": 0.8, "repos": [{"repo": "r", "score": 80.0}], "stale": False})
            if mode == "scored60": return self.send(200, {"state": "scored", "score": 60.0, "letter": "D", "coverage": 0.6, "repos": [{"repo": "r", "score": 60.0}] * 3, "stale": False})
            if mode == "broken": return self.send(500, {})
            return self.send(200, {"state": "calibrating", "score": None, "letter": None, "coverage": 0.0, "repos": []})
        self.send(404, {})
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"{}")
        finally:
            error.close()


class Supervisor(unittest.TestCase):
    modes = {"alpha": "scored80", "beta": "scored60", "gamma": "calibrating", "delta": "broken"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(base / "accounts")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in self.modes:
            accounts.create_account(name, name + "-owner")
        script = base / "stub190.py"
        script.write_text(STUB, encoding="utf-8")
        from test_182_supervisor import free_stretch
        self.supervisor = sup.Supervisor(command_for=lambda account_id, port: [sys.executable, "-I", str(script), account_id, str(port), self.modes.get(account_id, "calibrating")], port_start=free_stretch())
        self.addCleanup(self.supervisor.stop)
        self.supervisor.sync()
        for _ in range(60):
            self.supervisor.check()
            if all(c.health is not None for c in self.supervisor.children.values()):
                break
            time.sleep(0.25)
        sup.SUPERVISOR["obj"] = self.supervisor
        self.addCleanup(lambda: sup.SUPERVISOR.update(obj=None))
        server = ThreadingHTTPServer(("127.0.0.1", 0), sup.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        self.url = f"http://127.0.0.1:{server.server_address[1]}"
        self.addCleanup(localguard.configure, False)
        self.addCleanup(localguard.reset_limits)

    def test_the_route_asks_every_account_and_combines_the_scored_ones(self):
        status, doc = get(self.url + "/api/score/global")
        self.assertEqual(status, 200, doc)
        self.assertEqual((doc["accounts_total"], doc["accounts_scored"], doc["informative"], doc["state"]), (4, 2, True, "scored"))
        self.assertEqual(doc["score"], 65.0)          # (80 * 1 + 60 * 3) / 4
        rows = {r["account"]: r for r in doc["accounts"]}
        self.assertEqual(rows["gamma"]["state"], "calibrating")
        self.assertEqual(rows["delta"]["state"], "unreachable")
        self.assertIsNone(rows["gamma"]["score"])

    def test_the_route_belongs_to_the_supervisor_and_is_not_forwarded(self):
        self.assertIn("/api/score/global", sup.OWN_PATHS)

    def test_the_accounts_the_asker_may_not_see_are_left_out(self):
        from github_actions_monitor.security import auth_http
        with mock.patch.object(auth_http, "visible_accounts", side_effect=lambda handler, ids: [i for i in ids if i in ("alpha", "gamma")]):
            status, doc = get(self.url + "/api/score/global")
        self.assertEqual((status, doc["accounts_total"], doc["score"]), (200, 2, 80.0))
        self.assertEqual(sorted(r["account"] for r in doc["accounts"]), ["alpha", "gamma"])


if __name__ == "__main__":
    unittest.main()
