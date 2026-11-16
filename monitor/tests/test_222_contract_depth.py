# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract goes one level deeper (the keys of the nested objects), freezes the value of the `code` of an error, and the answers that need data (the health of a repository, the envelope of the
sentinels) are checked against a server that holds the invented data of the demo."""
import json
import unittest
from datetime import datetime, timezone
from unittest import mock

import _testenv  # noqa: F401
import check_api_contract as tool
from github_actions_monitor.app import actions_monitor, demo_mode
from test_200_contract import CONTRACT, Served


class Depth(unittest.TestCase):
    def fed(self):
        served = Served(self, lite=False)
        previous = actions_monitor.STATE.get("data")
        with actions_monitor.LOCK:
            actions_monitor.STATE["data"] = demo_mode.data(datetime.now(timezone.utc))
        self.addCleanup(actions_monitor.STATE.__setitem__, "data", previous)
        return served, actions_monitor.toolconfig.github_owner()

    def test_nested_objects_are_checked(self):
        served = Served(self, lite=False)
        broken = json.loads(json.dumps(CONTRACT))
        row = next(r for r in broken["endpoints"] if r["path"] == "/api/health")
        self.assertIsInstance(row["complete"]["cycle"], dict)      # the level below is in the contract
        row["complete"]["cycle"]["a_key_that_will_never_exist"] = "str"
        row["complete"]["credential"]["state"] = "int"
        problems = tool.check(tool.make_caller(served.url), "complete", broken)
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(any("cycle" in p and "missing" in p for p in problems))
        self.assertTrue(any("credential" in p for p in problems))

    def test_a_nested_object_that_became_a_text_is_a_failure(self):
        problems = tool.keys_problems("x", {"cycle": "oops"}, {"cycle": {"phase": "str"}})
        self.assertEqual(len(problems), 1)

    def test_the_code_of_an_error_is_frozen(self):
        served = Served(self, lite=False)
        self.assertEqual(tool.check(tool.make_caller(served.url), "complete"), [])
        broken = json.loads(json.dumps(CONTRACT))
        next(r for r in broken["errors"] if r.get("json_values"))["json_values"]["code"] = "another_code"
        problems = tool.check(tool.make_caller(served.url), "complete", broken)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("another_code", problems[0])

    def test_the_answers_that_need_data_hold_with_the_demo(self):
        served, owner = self.fed()
        self.assertEqual(tool.check_fed(tool.make_caller(served.url), owner), [])

    def test_a_removed_key_of_the_health_of_a_repository_is_found(self):
        served, owner = self.fed()
        broken = json.loads(json.dumps(CONTRACT))
        broken["fed_endpoints"][0]["keys"]["health"]["ci"]["a_key_that_will_never_exist"] = "str"
        problems = tool.check_fed(tool.make_caller(served.url), owner, broken)
        self.assertEqual(len(problems), 1, problems)

    def test_without_data_the_health_of_the_repository_is_not_there(self):
        served = Served(self, lite=False)
        problems = tool.check_fed(tool.make_caller(served.url), "nobody")
        self.assertTrue(any("status 404" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
