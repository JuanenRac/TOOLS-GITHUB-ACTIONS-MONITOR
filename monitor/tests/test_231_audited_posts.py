# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of actions covers every POST route: each route is either recorded or exempt with a reason, a recorded one writes who/what/result without the body, and the two confirmations that reach GitHub or this computer say what they confirmed."""
import ast
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.integrations import ghactions  # noqa: E402
from github_actions_monitor.security import audit_log, audited_posts  # noqa: E402


def post_routes():
    """Every route the POST handlers of the monitor name: the strings of handle_post and the two lists of routes of this computer."""
    tree = ast.parse(inspect.getsource(actions_monitor))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "handle_post":
            found |= {c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value.startswith("/api/")}
    found |= set(actions_monitor.THIS_COMPUTER_POST)
    return found


class Table(unittest.TestCase):
    def test_every_post_route_is_recorded_or_exempt_with_a_reason(self):
        routes = post_routes()
        decided = set(audited_posts.AUDITED) | set(audited_posts.EXEMPT)
        self.assertEqual(sorted(routes - decided), [], "a POST route that is neither recorded nor exempt")
        self.assertEqual(sorted(decided - routes), [], "a route of the table that no handler names")
        self.assertFalse(set(audited_posts.AUDITED) & set(audited_posts.EXEMPT))
        self.assertTrue(all(len(reason) > 20 for reason in audited_posts.EXEMPT.values()))

    def test_the_names_of_the_actions_are_valid_and_distinct(self):
        names = list(audited_posts.AUDITED.values())
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(audit_log.ACTION_RE.match(n) for n in names))


class Lines(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "audit_actions.jsonl"
        audit_log.FILE = self.file
        audit_log._last.update(path=None, hash="")
        self.addCleanup(lambda: (setattr(audit_log, "FILE", None), audit_log._last.update(path=None, hash="")))

    def handler(self, status, ok):
        class H:
            auth_user = {"user": "ana", "role": "admin"}
            reply_status, reply_ok = status, ok
        return H()

    def rows(self):
        return [json.loads(x) for x in self.file.read_text(encoding="utf-8").splitlines()] if self.file.exists() else []

    def test_a_confirmed_action_is_one_line_with_its_result(self):
        audit_log.take_note()
        audit_log.note("rerun repo-a#5")
        actions_monitor.Handler.audit_post(self.handler(200, True), "/api/gh-action/confirm")
        actions_monitor.Handler.audit_post(self.handler(200, False), "/api/gh-action/confirm")
        actions_monitor.Handler.audit_post(self.handler(403, False), "/api/github-token")
        actions_monitor.Handler.audit_post(self.handler(400, False), "/api/mode")
        rows = self.rows()
        self.assertEqual([(r["action"], r["result"], r["user"]) for r in rows], [("github_action", "ok", "ana"), ("github_action", "error", "ana"), ("github_token", "denied", "ana"), ("mode_change", "error", "ana")])
        self.assertEqual(rows[0]["target"], "rerun repo-a#5")
        self.assertEqual(rows[0]["details"], {"status": 200})
        self.assertEqual(rows[1]["target"], "/api/gh-action/confirm")      # the note is used once

    def test_an_exempt_route_writes_nothing(self):
        for path in audited_posts.EXEMPT:
            actions_monitor.Handler.audit_post(self.handler(200, True), path)
        self.assertEqual(self.rows(), [])

    def test_the_confirmation_of_a_github_action_names_what_it_ran(self):
        config = {"github_actions": {"enabled": True, "allowed": ["rerun"]}}
        item = {"action": "rerun", "method": "POST", "endpoint": "repos/o/r/actions/runs/7/rerun", "scope": "repo", "subject": "run", "repo": "r", "number": "7", "fields": {}}
        plan_id = ghactions.PENDING.add("ghaction", item)
        audit_log.take_note()
        with mock.patch.object(ghactions, "settings", return_value={"enabled": True, "allowed": ["rerun"]}), mock.patch.object(ghactions, "scopes", return_value=None), mock.patch.object(ghactions, "permission", return_value=True), \
                mock.patch.object(ghactions, "log"):
            done = ghactions.execute(config, plan_id, lambda args, timeout: (0, "", ""))
        self.assertTrue(done["ok"])
        self.assertEqual(audit_log.take_note()[0], "rerun r#7")

    def test_the_handlers_record_once_they_are_done(self):
        source = inspect.getsource(actions_monitor.Handler.do_POST)
        self.assertIn("self.audit_post(", source)
        self.assertLess(source.index("self.handle_post()"), source.index("self.audit_post("))


if __name__ == "__main__":
    unittest.main()
