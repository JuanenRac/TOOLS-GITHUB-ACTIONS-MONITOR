# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract of the read API: the shape of every read endpoint and the codes of its errors are frozen in docs/schemas/api_contract.json and checked here against a real server of each edition,
and the same file is what tools/check_api_contract.py checks against any running monitor."""
import http.client
import json
import threading
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
import check_api_contract as contract_tool
from github_actions_monitor.app import actions_monitor
from github_actions_monitor.security import localguard

HERE = Path(__file__).resolve().parent.parent
CONTRACT = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
TOKEN = "C" * 24


class Served:
    def __init__(self, case, lite):
        _testenv.guard(case)
        self.server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        for patcher in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}), mock.patch.object(actions_monitor, "LITE", {"on": lite})):
            patcher.start()
            case.addCleanup(patcher.stop)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"

    def raw(self, method, path, headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            connection.request(method, path, body, {"Host": f"127.0.0.1:{self.port}", **(headers or {})})
            answer = connection.getresponse()
            return answer.status, answer.read(), answer
        finally:
            connection.close()


class TheContractHolds(unittest.TestCase):
    def test_the_complete_edition_keeps_every_key_and_type_and_every_error_code(self):
        served = Served(self, lite=False)
        self.assertEqual(contract_tool.check(contract_tool.make_caller(served.url), "complete"), [])

    def test_the_lite_edition_keeps_its_answers_and_answers_404_where_the_contract_says(self):
        served = Served(self, lite=True)
        self.assertEqual(contract_tool.check(contract_tool.make_caller(served.url), "lite"), [])

    def test_the_command_line_tool_prints_pass_and_fails_on_a_changed_type(self):
        served = Served(self, lite=False)
        lines = []
        with mock.patch("builtins.print", lambda *a: lines.append(" ".join(map(str, a)))):
            self.assertEqual(contract_tool.main(["--url", served.url]), 0)
        self.assertEqual(lines[-1], "CONTRACT=PASS")
        broken = json.loads(json.dumps(CONTRACT))
        broken["endpoints"][0]["complete"]["ok"] = "str"
        problems = contract_tool.check(contract_tool.make_caller(served.url), "complete", broken)
        self.assertEqual(len(problems), 1)
        self.assertIn("`ok`", problems[0])

    def test_a_missing_key_and_a_wrong_status_are_found(self):
        served = Served(self, lite=False)
        changed = json.loads(json.dumps(CONTRACT))
        changed["endpoints"][0]["complete"]["a_key_that_will_never_exist"] = "str"
        changed["endpoints"][1]["complete"] = 500
        problems = contract_tool.check(contract_tool.make_caller(served.url), "complete", changed)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("missing" in p for p in problems) and any("status 200" in p for p in problems))

    def test_no_server_is_a_failure_with_its_own_exit_code(self):
        lines = []
        with mock.patch("builtins.print", lambda *a: lines.append(" ".join(map(str, a)))):
            self.assertEqual(contract_tool.main(["--url", "http://127.0.0.1:9"]), 2)
        self.assertEqual(lines[-1], "CONTRACT=FAIL")


class TheFileItself(unittest.TestCase):
    def test_every_entry_is_well_formed_and_the_paths_are_unique(self):
        names = set(CONTRACT["types"])
        seen = set()
        for row in CONTRACT["endpoints"]:
            self.assertNotIn(row["path"], seen)
            seen.add(row["path"])
            for edition in ("complete", "lite"):
                value = row[edition]
                if isinstance(value, dict):
                    self.assertTrue(value, row["path"])
                    self.assertLessEqual(set(value.values()), names, row["path"])
                else:
                    self.assertTrue(value == 404 or (edition == "lite" and value == "same"), (row["path"], value))
            self.assertIsInstance(row["complete"], dict, "a complete edition answers every endpoint of the contract")

    def test_what_the_lite_edition_does_not_have_agrees_with_the_list_of_the_handler(self):
        for row in CONTRACT["endpoints"]:
            path = row["path"].split("?")[0]
            missing = any(path.startswith(prefix) for prefix in actions_monitor.LITE_PATHS) and not any(path.startswith(p) for p in actions_monitor.LITE_SHARED)
            self.assertEqual(row["lite"] == 404, missing, row["path"])

    def test_the_errors_are_json_with_a_stable_word_and_the_other_edition_cases_exist(self):
        for row in CONTRACT["errors"]:
            self.assertIn(row["status"], (401, 403, 404, 429))
            self.assertTrue(set(row["editions"]) <= {"complete", "lite"})


class TheRulesOfTheDoor(unittest.TestCase):
    def test_a_foreign_host_is_refused_with_a_json_error_and_unknown_query_words_are_ignored(self):
        served = Served(self, lite=False)
        status, raw, _ = served.raw("GET", "/api/health", {"Host": "other.example"})
        self.assertEqual((status, json.loads(raw)), (403, {"error": "forbidden"}))
        plain = served.raw("GET", "/api/health")
        extra = served.raw("GET", "/api/health?nothing=1&at=all")
        self.assertEqual((plain[0], extra[0]), (200, 200))
        self.assertEqual(set(json.loads(plain[1])), set(json.loads(extra[1])))

    def test_the_network_mode_asks_for_the_token_in_a_header_and_says_401_with_a_stable_word(self):
        served = Served(self, lite=False)
        localguard.configure(True, token=TOKEN)
        self.addCleanup(localguard.configure, False)
        status, raw, _ = served.raw("GET", "/api/health")
        self.assertEqual((status, json.loads(raw)), (401, {"error": "access"}))
        status, raw, _ = served.raw("GET", "/api/health", {"X-Monitor-Access": "x" * 24})
        self.assertEqual((status, json.loads(raw)), (401, {"error": "access"}))
        status, raw, _ = served.raw("GET", "/api/health", {"X-Monitor-Access": TOKEN})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(raw)["ok"])

    def test_every_answer_is_json_with_utf8_except_the_documented_text_ones(self):
        served = Served(self, lite=False)
        for row in CONTRACT["endpoints"]:
            status, _, answer = served.raw("GET", row["path"])
            self.assertEqual(status, 200, row["path"])
            kind = answer.getheader("Content-Type")
            if row["path"].startswith("/api/ai/brief"):
                self.assertIn("json", kind, "fmt=json asks for the structured form")
            self.assertIn("application/json", kind, row["path"])
            self.assertIn("utf-8", kind.lower(), row["path"])


class EveryGuideNamesRealEndpoints(unittest.TestCase):
    def test_no_guide_in_any_language_cites_a_route_the_code_does_not_have(self):
        import re
        source = "".join(p.read_text(encoding="utf-8", errors="replace") for p in (HERE / "src").rglob("*.py"))
        missing = {}
        for path in sorted((HERE / "docs").glob("*.md")):
            if path.name.startswith("CHANGELOG"):
                continue
            for route in re.findall(r"`(?:GET|POST|GET/POST) (/api/[A-Za-z0-9_/.-]+)", path.read_text(encoding="utf-8")):
                if route.rstrip("/") not in source:
                    missing.setdefault(path.name, set()).add(route)
        self.assertEqual(missing, {})


class TheGuidesByUse(unittest.TestCase):
    BASES = ("COMPLETE_INDIVIDUAL", "COMPLETE_SERVICE", "COMPLETE_TEAM", "API")
    SUFFIXES = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por")

    def test_each_guide_exists_in_eight_languages_is_in_the_help_and_links_to_files_that_exist(self):
        import re
        index = json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))
        topics = {t.get("id") for t in index["topics"] if isinstance(t, dict)}
        for base in self.BASES:
            self.assertIn(base.lower(), topics)
            for suffix in self.SUFFIXES:
                path = HERE / "docs" / f"{base}{suffix}.md"
                text = path.read_text(encoding="utf-8")
                self.assertGreater(len(text), 1200, path.name)
                for target in re.findall(r"\]\(([A-Z_]+(?:_[a-z]{3})?\.md)\)", text):
                    self.assertTrue((HERE / "docs" / target).is_file(), f"{path.name} links to {target}")
                self.assertNotRegex(text, r"[A-Za-z]:\\Users|/home/[a-z]+")

    def test_every_setting_and_endpoint_a_guide_cites_exists(self):
        import re
        from github_actions_monitor.app import modes, settings_api
        from test_177_guides import cited, known_keys
        keys = known_keys() | {k for k in settings_api.FIELDS} | set(modes.DEFAULTS)
        source = Path(actions_monitor.__file__).read_text(encoding="utf-8")
        for base in self.BASES:
            for suffix in self.SUFFIXES:
                text = (HERE / "docs" / f"{base}{suffix}.md").read_text(encoding="utf-8")
                for token in cited(text):
                    probe = token[:-2] if token.endswith(".*") else token
                    self.assertTrue(probe in keys or any(k.startswith(probe + ".") for k in keys), f"{base}{suffix}: `{token}`")
                for path in re.findall(r"`GET (/api/[a-z/-]+)", text):
                    self.assertIn(f'"{path}"', source, f"{base}{suffix}: {path}")


if __name__ == "__main__":
    unittest.main()
