# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""In the team mode the operator of a plan on GitHub is the person with a session, not the name the request carries."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402

CONFIG = {"github_actions": {"enabled": True, "allowed": ["cancel"], "writer_lock": False, "preflight": False}}
BODY = {"action": "cancel", "repo": "r", "number": 5, "reason": "stuck for hours", "operator": "bob-the-boss"}


class Operator(unittest.TestCase):
    def plan(self, who):
        with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=CONFIG), mock.patch.object(actions_monitor.toolconfig, "github_owner", return_value="o"):
            return actions_monitor.handle_advanced_post("/api/gh-action/plan", dict(BODY), who)

    def test_with_a_session_the_operator_is_that_person(self):
        answer = self.plan("ana")
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(answer["plan"]["operator"], "ana")

    def test_alone_the_request_may_name_the_operator(self):
        self.assertEqual(self.plan("")["plan"]["operator"], "bob-the-boss")


if __name__ == "__main__":
    unittest.main()
