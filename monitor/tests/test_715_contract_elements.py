# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract reaches the ELEMENTS of the lists and the body of `/api/data` (the runs, the repositories and the allowance every client reads), `/api/auth/me` is decided, and the type of every field of an
Alert is frozen, not only its name. Each test breaks one thing and the contract tool (or the frozen list) has to see it."""
import json
import re
import typing
import unittest
from datetime import datetime, timezone
from unittest import mock

import _testenv  # noqa: F401
import check_api_contract as tool
from github_actions_monitor.app import actions_monitor, demo_mode
from github_actions_monitor.sentinels import sentinel_base
from test_200_contract import CONTRACT, Served
from test_201_contract_floor import SOURCE


def broken_copy():
    return json.loads(json.dumps(CONTRACT))


class Elements(unittest.TestCase):
    def test_a_list_with_a_shape_checks_its_elements_and_an_empty_one_passes(self):
        shape = {"items": [{"id": "str", "n": "int"}]}
        self.assertEqual(tool.keys_problems("x", {"items": []}, shape), [])
        self.assertEqual(tool.keys_problems("x", {"items": [{"id": "a", "n": 1}]}, shape), [])
        self.assertEqual(len(tool.keys_problems("x", {"items": [{"id": "a"}]}, shape)), 1)
        self.assertEqual(len(tool.keys_problems("x", {"items": [{"id": "a", "n": "1"}]}, shape)), 1)
        self.assertEqual(len(tool.keys_problems("x", {"items": {"id": "a", "n": 1}}, shape)), 1)
        self.assertEqual(len(tool.keys_problems("x", {"items": ["text"]}, shape)), 1)

    def test_the_elements_of_the_alerts_are_frozen(self):
        served = Served(self, lite=False)
        row = {"id": "system.credential:main", "code": "system.credential_blind", "level": "critical", "sentinel": "system", "account_id": "", "repo": None, "title": "t", "details": {}, "created_at": "2026-01-01T00:00:00Z"}
        with mock.patch.object(actions_monitor, "credential_alerts", return_value=[row]):
            self.assertEqual(tool.check(tool.make_caller(served.url), "complete"), [])
            broken = broken_copy()
            alerts = next(r for r in broken["endpoints"] if r["path"] == "/api/alerts")["complete"]
            self.assertIsInstance(alerts["alerts"], list, "the elements of the alerts have a shape")
            alerts["alerts"][0]["silenced_until"] = alerts["alerts"][0].pop("muted_until")      # what a rename of the key in the answer looks like
            problems = tool.check(tool.make_caller(served.url), "complete", broken)
            self.assertTrue(any("silenced_until" in p for p in problems), problems)


class TheDataRoute(unittest.TestCase):
    def fed(self):
        served = Served(self, lite=False)
        previous = actions_monitor.STATE.get("data")
        with actions_monitor.LOCK:
            actions_monitor.STATE["data"] = demo_mode.data(datetime.now(timezone.utc))
        self.addCleanup(actions_monitor.STATE.__setitem__, "data", previous)
        return served

    def row(self, contract):
        return next(r for r in contract["fed_endpoints"] if r["path"] == "/api/data")["keys"]["data"]

    def test_the_body_of_the_data_route_is_frozen(self):
        served = self.fed()
        self.assertEqual(tool.check_fed(tool.make_caller(served.url), actions_monitor.toolconfig.github_owner()), [])
        data = self.row(CONTRACT)
        for key in ("runs", "repos", "rate", "active", "figures"):
            self.assertIn(key, data)

    def test_renaming_the_list_of_runs_or_dropping_the_allowance_or_the_repositories_is_seen(self):
        served = self.fed()
        for key in ("runs", "rate", "repos"):
            with self.subTest(key=key):
                broken = broken_copy()
                data = self.row(broken)
                data["renamed_" + key] = data.pop(key)
                problems = tool.check_fed(tool.make_caller(served.url), actions_monitor.toolconfig.github_owner(), broken)
                self.assertTrue(any("renamed_" + key in p for p in problems), problems)

    def test_a_removed_key_of_a_run_is_seen(self):
        served = self.fed()
        broken = broken_copy()
        self.row(broken)["runs"][0]["conclusion_text"] = "str"
        self.assertTrue(any("conclusion_text" in p for p in tool.check_fed(tool.make_caller(served.url), actions_monitor.toolconfig.github_owner(), broken)))


class EveryReadRouteIsDecided(unittest.TestCase):
    def test_the_routes_served_outside_the_main_handler_are_decided_too(self):
        """`GET /api/auth/me` is served by the module of the sign-in, not by `handle_get`: it is in the contract."""
        paths = {row["path"] for row in CONTRACT["endpoints"] + CONTRACT["fed_endpoints"]}
        decided = paths | {row["path"] for row in CONTRACT["unfrozen"]}
        self.assertIn("/api/auth/me", paths)
        from github_actions_monitor.security import auth_http
        with open(auth_http.__file__, encoding="utf-8") as handle:
            text = handle.read()
        for route in sorted(set(re.findall(r'path == "(/api/[a-z/_-]+)" and method == "GET"', text))):
            self.assertTrue(route in decided or any(route.startswith(p) for p in decided if p.endswith("/")), route)
        self.assertIn("handle_get", SOURCE)


class TheTypesOfAnAlert(unittest.TestCase):
    EXPECTED = {"id": "str", "code": "str", "level": "Literal['info', 'warning', 'error', 'critical']", "sentinel": "str", "account_id": "str", "repo": "str | None", "title": "str", "details": "dict",
                "created_at": "str"}

    def test_every_field_keeps_its_type(self):
        shown = {name: (hint.__name__ if isinstance(hint, type) else str(hint).replace("typing.", "")) for name, hint in typing.get_type_hints(sentinel_base.Alert).items()}
        self.assertEqual(shown, self.EXPECTED)


if __name__ == "__main__":
    unittest.main()
