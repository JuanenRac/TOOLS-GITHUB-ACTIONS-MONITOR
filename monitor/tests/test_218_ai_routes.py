# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The review route of the proposals of the AI answers over HTTP, and a reject stops the run."""
import json
import sys
import tempfile
import threading
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
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.integrations import ai_actions  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402


class ReviewRoute(unittest.TestCase):
    CONFIG = {"ai": {"actions": {"enabled": True, "execute": True, "require_approval": True}}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.actions = ai_actions.Actions(log_file=Path(self.tmp.name) / "log.jsonl")
        out = self.actions.propose("run gh run rerun 5 --failed", "r", self.CONFIG, {"r"}, lambda repo, n: True, lambda repo, n: True, "o")
        self.ident, self.command = out[0]["id"], out[0]["command"]
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"
        for patch in (mock.patch.object(ai_actions, "ACTIONS", self.actions), mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=self.CONFIG),
                      mock.patch.object(actions_monitor, "token_required", return_value=False), mock.patch.dict(localguard.STATE, {"network": False})):
            patch.start()
            self.addCleanup(patch.stop)

    def post(self, path, body):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                return answer.status, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            body = json.loads(error.read() or b"{}")
            error.close()
            return error.code, body

    def test_approve_over_http_lets_the_proposal_run(self):
        self.assertEqual(self.post("/api/ai/actions/confirm", {"id": self.ident, "command": self.command})[1]["reason"], "not_approved")
        self.assertEqual(self.post("/api/ai/actions/review", {"id": self.ident, "decision": "approve", "by": "cli"})[1]["reason"], "confirm")      # alone: the code of the proposal is typed
        typed = self.actions.listing(self.CONFIG)[0]["hash"][:8]
        code, answer = self.post("/api/ai/actions/review", {"id": self.ident, "decision": "approve", "by": "cli", "confirm": typed})
        self.assertEqual((code, answer), (200, {"ok": True, "reason": "ok", "status": "approved"}))
        self.assertEqual([r["status"] for r in self.actions.listing(self.CONFIG)], ["approved"])

    def test_reject_over_http_stops_the_run(self):
        code, answer = self.post("/api/ai/actions/review", {"id": self.ident, "decision": "reject"})
        self.assertEqual((code, answer["ok"], answer["status"]), (200, True, "rejected"))
        with mock.patch.object(ai_actions.subprocess, "run", side_effect=AssertionError("it ran")):
            self.assertEqual(self.post("/api/ai/actions/confirm", {"id": self.ident, "command": self.command})[1]["reason"], "rejected")

    def test_a_bad_decision_is_not_a_channel_error(self):
        answer = self.post("/api/ai/actions/review", {"id": self.ident, "decision": "maybe"})[1]
        self.assertEqual(answer["reason"], "bad_decision")

    def test_the_person_with_a_session_is_the_reviewer(self):
        typed = self.actions.listing(self.CONFIG)[0]["hash"][:8]
        done = actions_monitor.handle_action_post("/api/ai/actions/review", {"id": self.ident, "decision": "approve", "by": "bob", "confirm": typed}, "ana")
        self.assertTrue(done["ok"])
        self.assertEqual(self.actions.listing(self.CONFIG)[0]["by"], "ana")

    def test_an_unknown_route_never_falls_into_the_notification_test(self):
        self.assertEqual(actions_monitor.handle_action_post("/api/nothing", {"channel": "slack"})["reason"], "unknown_route")

    def test_no_route_of_this_computer_answers_with_the_channel_error(self):
        for path in actions_monitor.THIS_COMPUTER_ACTIONS:
            if path in ("/api/notify/test", "/api/ai/test") or path.startswith("/api/ai/models") or path == "/api/ai/doctor":
                continue
            self.assertNotEqual(actions_monitor.handle_action_post(path, {}).get("reason"), "bad_value", path)


class ApprovalIsTheDefault(unittest.TestCase):
    def test_the_proposals_need_an_approval_unless_the_person_turns_it_off(self):
        self.assertIs(ai_actions.settings({})["require_approval"], True)
        self.assertIs(ai_actions.settings({"ai": {"actions": {"require_approval": False}}})["require_approval"], False)


if __name__ == "__main__":
    unittest.main()
