# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The read API for clients has three doors that must say the same: HTTP (`/api/v1/me`, `/api/v1/openapi.json`), the command line (`api me`, `api openapi`, `api contract-check`) and the MCP server
(`api_me`, `api_openapi`, `api_contract_check`). The document that each one gives is the same, and a closed prefix is told in one line, not as an empty failure."""
import contextlib
import io
import json
import re
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor
from github_actions_monitor.cli import monitor_cli as cli
from github_actions_monitor.integrations import mcp_server
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
VOLATILE = re.compile(r'"[a-z_]*_epoch": ?[0-9.]+')


def calm(text):
    """Two answers of two instants differ only in the clock: the fields of time are taken out before comparing."""
    return VOLATILE.sub("", text)


def view(name):
    return {"repo": name, "ecosystem": "HYDRA", "ecosystem_label": "HYDRA", "state": "bad" if name.endswith("0") else "ok", "risk": 3,
            "ci": {"runs_24h": 4, "successes_24h": 3, "failures_24h": 1, "success_rate_24h": 75, "red_workflows": ["a"], "stuck_runs": 0},
            "alerts": {"total": 2, "by_sentinel": {}, "by_level": {}, "items": []}, "readiness": None, "activity": {"last_run_at": None, "runs_7d": 9, "idle_days": 0},
            "sources": {}, "not_fully_seen": []}


def run_cli(url, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(["api", *args, "--url", url, "--lang", "en", "--json"])
    return code, json.loads(out.getvalue()) if out.getvalue().strip() else None


class TheThreeDoors(unittest.TestCase):
    def serve(self, service):
        served = Served(self, lite=False)
        for patcher in (mock.patch.object(actions_monitor, "service_mode", return_value=service), mock.patch.object(actions_monitor, "health_views", return_value=[view("repo%03d" % n) for n in range(120)])):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(i18n.set_language, "en")
        self.served = served
        return served

    def getter(self, path, port=None):
        with urllib.request.urlopen(self.served.url + path, timeout=20) as answer:      # an HTTP error is an OSError, as it is for local_get
            return json.load(answer)

    def mcp(self, name, arguments=None, **kwargs):
        return mcp_server.call(name, arguments or {}, {}, getter=self.getter, **kwargs)

    def test_the_tools_exist_only_read_and_need_no_flag(self):
        tools = {t["name"]: t for t in mcp_server.TOOLS}
        listed = {t["name"] for t in mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, {})["result"]["tools"]}
        for name in ("api_me", "api_openapi", "api_contract_check"):
            self.assertIn(name, tools)
            self.assertIn(name, listed)
            self.assertRegex(tools[name]["description"], r"Read only|only reads")

    def test_me_is_the_same_over_http_the_command_line_and_mcp(self):
        served = self.serve(True)
        http_doc = self.getter("/api/v1/me")
        code, cli_doc = run_cli(served.url, "me")
        self.assertEqual(code, cli.EXIT_OK)
        mcp_doc = json.loads(self.mcp("api_me"))
        self.assertEqual(calm(json.dumps(http_doc, sort_keys=True)), calm(json.dumps(cli_doc["data"], sort_keys=True)))
        self.assertEqual(calm(json.dumps(http_doc, sort_keys=True)), calm(json.dumps(mcp_doc, sort_keys=True)))

    def test_openapi_is_the_same_over_http_the_command_line_and_mcp(self):
        served = self.serve(True)
        http_doc = self.getter("/api/v1/openapi.json")
        code, cli_doc = run_cli(served.url, "openapi")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(http_doc, cli_doc["data"])
        self.assertEqual(http_doc, json.loads(self.mcp("api_openapi")))

    def test_one_route_of_the_document_can_be_asked_for_alone(self):
        self.serve(True)
        one = json.loads(self.mcp("api_openapi", {"path": "/api/v1/health"}))
        self.assertEqual(list(one["paths"]), ["/api/v1/health"])
        self.assertEqual(one["paths"]["/api/v1/health"], self.getter("/api/v1/openapi.json")["paths"]["/api/v1/health"])
        with self.assertRaises(ValueError):
            self.mcp("api_openapi", {"path": "/api/v1/nope"})

    def test_the_contract_check_is_the_same_suite_as_the_command_line(self):
        served = self.serve(True)
        port = int(served.url.rsplit(":", 1)[1])
        text = self.mcp("api_contract_check", checker=lambda: mcp_server.run_contract_suite(port))
        found = json.loads(text)
        code, cli_doc = run_cli(served.url, "contract-check")
        self.assertTrue(found["ok"], [r for r in found["rows"] if not r["ok"]])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual((found["checks"], found["failed"]), (cli_doc["data"]["checks"], cli_doc["data"]["failed"]))
        self.assertEqual([r["check"] for r in found["rows"]], [r["check"] for r in cli_doc["data"]["rows"]])

    def test_a_closed_prefix_is_told_in_one_line_in_every_door(self):
        served = self.serve(False)      # "auto" outside the service mode
        for name in ("api_me", "api_openapi"):
            with self.assertRaises(ValueError) as caught:
                self.mcp(name)
            self.assertIn("closed", str(caught.exception))
        reply = mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "api_me", "arguments": {}}}, {}, getter=self.getter)
        self.assertTrue(reply["result"]["isError"])
        code, _ = run_cli(served.url, "me")
        self.assertEqual(code, cli.EXIT_DEGRADED)

    def test_a_secret_in_an_answer_never_reaches_the_tool(self):
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        text = mcp_server.call("api_me", {}, {}, getter=lambda path, port=None: {"user": "x", "note": "token " + token})
        self.assertNotIn(token, text)

    def test_the_tools_are_named_in_the_docs_and_the_skills(self):
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            text = (HERE / "docs" / f"API{tail}.md").read_text(encoding="utf-8")
            self.assertIn("api_contract_check", text, tail)
        for path in ("skills/external/SKILL.md", "skills/external/references/connect.md"):
            self.assertIn("api_me", (HERE / path).read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
