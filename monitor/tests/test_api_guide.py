# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The step by step guide of the read API (docs/API_V1*.md): it exists in the eight languages, the commands of the guide are the same in all of them and each one is run against a monitor (the ones that
must work answer 200, the one that shows an error answers 400 with the code the guide names), and `tools/check_api_contract.py --v1` is the contract suite plus the frozen shapes."""
import contextlib
import io
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import check_api_contract as contract_tool  # noqa: E402
from test_api_mcp import view  # noqa: E402

TAILS = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
BLOCK = re.compile(r"```\n((?:curl [^\n]*\n)+)```")
URL = re.compile(r'"?(http://127\.0\.0\.1:8765(/api/v1/[^"\s]*))"?')


def blocks(tail=""):
    text = (HERE / "docs" / f"API_V1{tail}.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    return [b.strip().split("\n") for b in BLOCK.findall(text)]


class TheGuide(unittest.TestCase):
    def test_it_exists_in_the_eight_languages_with_the_same_commands(self):
        english = blocks()
        self.assertEqual([len(b) for b in english], [8, 1])
        for tail in TAILS:
            text = (HERE / "docs" / f"API_V1{tail}.md").read_text(encoding="utf-8")
            self.assertTrue(text.lstrip().startswith("<!--"), tail)
            for other in (x for x in TAILS if x != tail):      # the switcher of languages points at the other seven files of the guide
                self.assertIn(f"(API_V1{other}.md)", text, (tail, other))
            self.assertEqual(blocks(tail), english, tail)

    def test_every_command_of_the_guide_is_run_against_a_monitor(self):
        import http.client
        served = Served(self, lite=False)
        for patcher in (mock.patch.object(actions_monitor, "service_mode", return_value=True), mock.patch.object(actions_monitor, "health_views", return_value=[view("repo%03d" % n) for n in range(120)])):
            patcher.start()
            self.addCleanup(patcher.stop)
        good, bad = blocks()
        for line in good:
            self.assertIn("X-Monitor-Access", line)
            path = URL.search(line).group(2)
            if "THE_NEXT_CURSOR" in path:
                status, raw, _ = served.raw("GET", "/api/v1/repos?limit=50")
                cursor = json.loads(raw)["next_cursor"]
                self.assertTrue(cursor)
                path = path.replace("THE_NEXT_CURSOR", cursor)
            status, raw, _ = served.raw("GET", path)
            self.assertEqual(status, 200, line)
            if "--compressed" not in line and "openapi" not in line:
                json.loads(raw)
        for line in bad:
            status, raw, _ = served.raw("GET", URL.search(line).group(2))
            self.assertEqual(status, 400, line)
            self.assertEqual(json.loads(raw)["code"], "api.bad_limit")
        del http

    def test_the_guide_is_a_topic_of_the_help_and_the_api_guide_points_at_it(self):
        index = json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))
        self.assertEqual({v for k, v in index["files"].items() if k.startswith("API_V1")}, {"api_v1"})
        self.assertIn("api_v1", [t["id"] for t in index["topics"]])
        for tail in TAILS:
            self.assertIn(f"API_V1{tail}.md", (HERE / "docs" / f"API{tail}.md").read_text(encoding="utf-8"), tail)


class TheCheckTool(unittest.TestCase):
    def serve(self):
        served = Served(self, lite=False)
        for patcher in (mock.patch.object(actions_monitor, "service_mode", return_value=True), mock.patch.object(actions_monitor, "health_views", return_value=[view("repo%03d" % n) for n in range(120)])):
            patcher.start()
            self.addCleanup(patcher.stop)
        return served

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = contract_tool.main(list(args))
        return code, out.getvalue()

    def test_v1_runs_the_whole_suite_and_the_frozen_shapes(self):
        served = self.serve()
        self.assertEqual(contract_tool.check_v1_suite(served.url), [])
        code, out = self.run_tool("--v1", "--url", served.url)
        self.assertEqual((code, out.strip().splitlines()[-1]), (0, "CONTRACT=PASS"))

    def test_v1_fails_and_names_the_check_when_the_suite_finds_a_defect(self):
        served = self.serve()
        with mock.patch.object(contract_tool, "check_v1_suite", return_value=["suite: error api.bad_limit: status 200"]):
            code, out = self.run_tool("--v1", "--url", served.url)
        self.assertEqual(code, 1)
        self.assertIn("suite: error api.bad_limit", out)
        self.assertEqual(out.strip().splitlines()[-1], "CONTRACT=FAIL")

    def test_v1_does_not_repeat_the_checks_of_the_suite(self):
        source = (HERE / "tools" / "check_api_contract.py").read_text(encoding="utf-8")
        self.assertIn("api_contract_suite.py", source)
        self.assertNotIn("def check_pages", source)      # the suite owns the pages, the errors, the header and gzip


if __name__ == "__main__":
    unittest.main()
