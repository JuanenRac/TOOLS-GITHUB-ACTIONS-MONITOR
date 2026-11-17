# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract of the read API cannot be trimmed in the same commit that breaks the API: it must contain the contract of the first 2.x version, and every GET route of the server is either in it or in
its list of routes that are not frozen, each with its reason (a new route forces a decision)."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
CONTRACT = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
FLOOR = json.loads((HERE / "tests" / "fixtures" / "api_contract_floor.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")


def by_path(rows):
    return {row["path"]: row for row in rows}


def contains(current, floor, label):
    """Every key of `floor` is in `current` with the same type."""
    problems = []
    if not isinstance(floor, dict):
        if current != floor:
            problems.append(f"{label}: {current!r} where the first version has {floor!r}")
        return problems
    if not isinstance(current, dict):
        return [f"{label}: the shape {floor!r} became {current!r}"]
    for key, kind in floor.items():
        if key not in current:
            problems.append(f"{label}: the key `{key}` was removed")
        elif (kind == "object" and isinstance(current[key], dict)) or (kind == "list" and isinstance(current[key], list)):      # the same object, now with the list of its own keys
            continue
        elif current[key] != kind:
            problems.append(f"{label}: the key `{key}` changed from {kind} to {current[key]}")
    return problems


class TheContractOnlyGrows(unittest.TestCase):
    def test_the_current_contract_contains_the_first_one(self):
        now = by_path(CONTRACT["endpoints"])
        problems = []
        for path, row in by_path(FLOOR["endpoints"]).items():
            if path not in now:
                problems.append(f"{path}: the route was removed")
                continue
            for edition in ("complete", "lite"):
                problems += contains(now[path][edition], row[edition], f"{path} ({edition})")
        self.assertEqual(problems, [])

    def test_the_error_cases_of_the_first_contract_are_still_there(self):
        now = {(r["method"], r["path"], r.get("host")): r for r in CONTRACT["errors"]}
        for row in FLOOR["errors"]:
            key = (row["method"], row["path"], row.get("host"))
            self.assertIn(key, now, key)
            self.assertEqual(now[key]["status"], row["status"], key)
            self.assertEqual(contains(now[key].get("json_keys", {}), row.get("json_keys", {}), str(key)), [])
            self.assertLessEqual(set(row["editions"]), set(now[key]["editions"]), key)


class EveryGetRouteIsDecided(unittest.TestCase):
    def routes(self):
        start = SOURCE.index("    def handle_get(self):")
        body = SOURCE[start:SOURCE.index("\n    def ", start + 10)]
        return sorted(set(re.findall(r'"(/(?:api|metrics|screen)[^"\s]*)"', body)))

    def test_each_route_is_frozen_or_listed_as_not_frozen_with_its_reason(self):
        frozen = {row["path"].split("?")[0] for row in CONTRACT["endpoints"] + CONTRACT["fed_endpoints"]}
        free = CONTRACT["unfrozen"]
        for row in free:
            self.assertTrue(row["reason"].strip(), row["path"])
            self.assertNotIn(row["path"], frozen, "a route is frozen or not frozen, not both")
        loose = [row["path"] for row in free]
        undecided = []
        for route in self.routes():
            route = route.split("[")[0]
            if route in frozen or route in loose or any(p.endswith("/") and route.startswith(p) for p in loose):
                continue
            undecided.append(route)
        self.assertEqual(undecided, [], "add the route to the contract or to `unfrozen` with a reason")

    def test_the_data_route_that_every_client_reads_is_frozen(self):
        self.assertIn("/api/data", {row["path"] for row in CONTRACT["endpoints"]})


if __name__ == "__main__":
    unittest.main()
