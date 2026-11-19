# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The OpenAPI document of the read API is built from the frozen contract: every frozen route is in it with the keys the contract promises, the routes that are not frozen are experimental (404 under the
prefix unless `api.experimental_routes`), and the document is a valid OpenAPI 3 structure that the server serves."""
import gzip
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor, api_spec, api_v1
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE.parent / "tools"))
try:
    import make_skill_refs
except ImportError:      # the tools folder does not travel in the zip of a release
    make_skill_refs = None
CONTRACT = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
DOC = api_spec.document("9.9.9", CONTRACT)


def refs(node):
    if isinstance(node, dict):
        if "$ref" in node:
            yield node["$ref"]
        for value in node.values():
            yield from refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from refs(value)


class TheDocument(unittest.TestCase):
    def test_it_is_a_valid_openapi_3_structure(self):
        self.assertEqual(DOC["openapi"], "3.0.3")
        self.assertEqual((DOC["info"]["version"], DOC["info"]["x-contract-version"]), ("9.9.9", api_v1.CONTRACT_VERSION))
        ids = []
        for path, item in DOC["paths"].items():
            self.assertTrue(path.startswith("/api/v1/"), path)
            self.assertEqual(list(item), ["get"], path)      # read only: nothing but GET
            operation = item["get"]
            ids.append(operation["operationId"])
            self.assertTrue(operation["responses"], path)
            declared = {p["name"] for p in operation.get("parameters", []) if p["in"] == "path"}
            self.assertEqual(declared, set(re.findall(r"\{(\w+)\}", path)), path)
            for parameter in operation.get("parameters", []):
                self.assertIn(parameter["in"], ("path", "query"))
                self.assertTrue(parameter["name"])
        self.assertEqual(len(ids), len(set(ids)), "operationId must be unique")
        for ref in refs(DOC):
            node = DOC
            for part in ref.lstrip("#/").split("/"):
                node = node[part]      # a reference that does not resolve raises KeyError

    def test_every_frozen_route_is_in_it_and_nothing_else(self):
        frozen = {api_spec.prefixed(re.sub(r"\?.*", "", r["path"])) for r in CONTRACT["endpoints"]}
        fed = {api_spec.prefixed(re.sub(r"\?.*", "", r["path"])) for r in CONTRACT["fed_endpoints"]}
        fed = {"/api/v1/repos/{owner}/{repo}/health" if p.startswith("/api/v1/repos/") else p for p in fed}
        own = set(api_v1.OWN_ROUTES)
        self.assertEqual(set(DOC["paths"]), frozen | fed | own)
        for row in CONTRACT["unfrozen"]:
            self.assertNotIn(api_spec.prefixed(row["path"]), DOC["paths"], row["path"])

    def test_each_key_of_the_contract_is_required_with_its_type(self):
        types = {"bool": "boolean", "int": "integer", "number": "number", "str": "string", "list": "array", "object": "object"}
        for row in CONTRACT["endpoints"]:
            keys = row["complete"]
            if not isinstance(keys, dict):
                continue
            schema = DOC["paths"][api_spec.prefixed(re.sub(r"\?.*", "", row["path"]))]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
            self.assertEqual(sorted(schema["required"]), sorted(keys), row["path"])      # a promised key that disappeared from the document would show here
            for key, kind in keys.items():
                if isinstance(kind, str) and kind in types:
                    self.assertEqual(schema["properties"][key]["type"], types[kind], (row["path"], key))
                if kind == "any":
                    self.assertTrue(schema["properties"][key]["nullable"], (row["path"], key))

    def test_the_nested_shapes_and_the_lists_of_objects_are_described(self):
        health = DOC["paths"]["/api/v1/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(health["properties"]["cycle"]["type"], "object")
        self.assertIn("phase", health["properties"]["cycle"]["required"])
        self.assertEqual(api_spec.schema_of([{"a": "int"}]), {"type": "array", "items": {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}})

    def test_the_lite_edition_and_the_local_routes_are_said(self):
        self.assertEqual(DOC["paths"]["/api/v1/alerts"]["get"]["x-lite"], 404)
        self.assertEqual(DOC["paths"]["/api/v1/health"]["get"]["x-lite"], "same")
        local = [r["path"] for r in CONTRACT["endpoints"] if r.get("local_only")]
        for path in local:
            self.assertTrue(DOC["paths"][api_spec.prefixed(re.sub(r"\?.*", "", path))]["get"]["x-local-only"])

    def test_it_is_small_and_compresses(self):
        raw = json.dumps(DOC).encode("utf-8")
        self.assertLess(len(raw), 200_000)
        self.assertLess(len(gzip.compress(raw)), 20_000)

    def test_the_experimental_routes_appear_only_when_they_are_asked(self):
        with_them = api_spec.document("9.9.9", CONTRACT, experimental_routes=True)
        added = set(with_them["paths"]) - set(DOC["paths"])
        self.assertTrue(added)
        for path in added:
            operation = with_them["paths"][path]["get"]
            self.assertTrue(operation["x-experimental"] and operation["x-reason"], path)

    def test_a_copy_without_the_contract_still_gives_the_three_own_routes(self):
        empty = api_spec.document("1", {"endpoints": [], "fed_endpoints": [], "unfrozen": [], "errors": []})
        self.assertEqual(sorted(empty["paths"]), sorted(api_v1.OWN_ROUTES))


class TheExperimentalRoutes(unittest.TestCase):
    def test_every_route_the_contract_does_not_freeze_is_experimental_and_the_frozen_ones_are_not(self):
        for row in CONTRACT["unfrozen"]:
            self.assertTrue(api_spec.experimental(row["path"], CONTRACT), row["path"])
        for row in CONTRACT["endpoints"]:
            self.assertFalse(api_spec.experimental(row["path"], CONTRACT), row["path"])
        self.assertFalse(api_spec.experimental("/api/repos/o/r/health", CONTRACT))      # `/api/repos/` is not frozen as a prefix, the health of one repository is
        self.assertTrue(api_spec.experimental("/api/outputs/prometheus.json", CONTRACT))
        self.assertFalse(api_spec.experimental("/api/no-such-route", CONTRACT))

    @unittest.skipIf(make_skill_refs is None, "the tools folder does not travel in the zip")
    def test_the_document_never_names_a_route_the_code_does_not_have(self):
        code = set(make_skill_refs.endpoints())
        for path in DOC["paths"]:
            old = "/api/" + path[len("/api/v1/"):]
            if old in ("/api/openapi.json", "/api/me", "/api/repos") or "{" in old:
                continue
            self.assertIn(old, code, path)


class OverHttp(unittest.TestCase):
    def serve(self, config):
        served = Served(self, lite=False)
        for patcher in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), mock.patch.object(actions_monitor, "service_mode", return_value=True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        return served

    def get(self, served, path):
        status, raw, answer = served.raw("GET", path, {"Accept-Encoding": "gzip"})
        if answer.getheader("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, None

    def test_a_route_that_is_not_frozen_answers_404_under_the_prefix_until_the_setting_is_on(self):
        closed = self.serve({})
        self.assertEqual(self.get(closed, "/api/v1/health")[0], 200)
        self.assertEqual(self.get(closed, "/api/health")[0], 200)
        self.assertEqual(self.get(closed, "/api/v1/updates/status")[0], 404)      # not frozen: experimental
        self.assertEqual(self.get(closed, "/api/updates/status")[0], 200)      # the old route does not change
        opened = self.serve({"api": {"experimental_routes": True}})
        self.assertEqual(self.get(opened, "/api/v1/updates/status")[0], 200)

    def test_the_document_served_is_the_one_of_the_contract(self):
        served = self.serve({})
        status, body = self.get(served, "/api/v1/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(sorted(body["paths"]), sorted(api_spec.document(actions_monitor.TOOL_VERSION, CONTRACT)["paths"]))
        status, wide = self.get(self.serve({"api": {"experimental_routes": True}}), "/api/v1/openapi.json")
        self.assertGreater(len(wide["paths"]), len(body["paths"]))


class TheSkills(unittest.TestCase):
    def test_the_skill_for_outside_tools_names_the_typed_client_and_the_commands(self):
        text = (HERE / "skills" / "external" / "SKILL.md").read_text(encoding="utf-8") + (HERE / "skills" / "external" / "references" / "connect.md").read_text(encoding="utf-8")
        for word in ("/api/v1/me", "/api/v1/openapi.json", "api openapi", "api me", "api.v1_enabled"):
            self.assertIn(word, text, word)
        for name in ("external", "internal"):
            refs_text = (HERE / "skills" / name / "references" / "api.md").read_text(encoding="utf-8")
            for route in api_v1.OWN_ROUTES[:2]:
                self.assertIn(f"`{route}`", refs_text, (name, route))
            self.assertIn("api.experimental_routes", refs_text, name)


if __name__ == "__main__":
    unittest.main()
