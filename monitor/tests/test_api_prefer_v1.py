# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command line as a client of the read API: it asks the routes the contract freezes under /api/v1/ and falls back to /api/ when the monitor answers 404 there (`cli.prefer_v1`), the answer is the
same document by both ways, and everything the command line, the terminal views and the MCP server read is a route the contract freezes (or an exception written down with its reason)."""
import json
import re
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor, api_spec
from github_actions_monitor.cli import monitor_cli as cli
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "src" / "github_actions_monitor"
CONTRACT = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
VOLATILE = {"uptime_seconds", "running_seconds", "seconds_since_ok", "age_seconds", "generated_at", "now", "updated", "ts"}

#: routes the clients read that the contract does not freeze (yet): the command line asks them the old way; each one has its reason.
NOT_FROZEN = {
    "/api/compare": "the comparison of periods is off by default and its keys follow its state",
    "/api/accounts": "the list of accounts of the supervisor, only in the multi-account mode",
    "/api/sentinel/ai": "the findings of the AI sentinel, off by default",
}

#: routes the clients POST to (the prefix is read only, so they keep the old routes): these are not reads.
WRITES = ("/api/auth/login", "/api/ai/ack", "/api/ai/lessons/close", "/api/ai/doctor", "/api/ai/models/refresh", "/api/ai/models/test", "/api/credential")


def served_monitor(case, service=True):
    served = Served(case, lite=False)
    patcher = mock.patch.object(actions_monitor, "service_mode", return_value=service)
    patcher.start()
    case.addCleanup(patcher.stop)
    cli.V1_STATE["closed"].clear()
    case.addCleanup(cli.V1_STATE["closed"].clear)
    return served


def recording(case):
    calls = []
    real = cli.plain_fetch

    def spy(base, path, query=None, timeout=8, token=""):
        calls.append(path)
        return real(base, path, query, timeout, token)
    patcher = mock.patch.object(cli, "plain_fetch", side_effect=spy)
    patcher.start()
    case.addCleanup(patcher.stop)
    return calls


def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(v) for v in value[:1]]
    return type(value).__name__


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in VOLATILE and not k.endswith("_epoch")}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


class ThePreference(unittest.TestCase):
    def test_the_setting_the_variable_and_the_default(self):
        self.assertTrue(cli.prefer_v1(env={}, config={}))
        self.assertTrue(cli.prefer_v1(env={}, config={"cli": {"prefer_v1": True}}))
        self.assertFalse(cli.prefer_v1(env={}, config={"cli": {"prefer_v1": False}}))
        self.assertTrue(cli.prefer_v1(env={}, config={"cli": {"prefer_v1": "no"}}))      # a value of the wrong type keeps the default
        self.assertFalse(cli.prefer_v1(env={"MONITOR_CLI_PREFER_V1": "0"}, config={}))
        self.assertTrue(cli.prefer_v1(env={"MONITOR_CLI_PREFER_V1": "1"}, config={"cli": {"prefer_v1": False}}))      # the variable wins

    def test_only_the_frozen_routes_get_a_versioned_path(self):
        self.assertEqual(cli.v1_path("/api/health"), "/api/v1/health")
        self.assertEqual(cli.v1_path("/api/ai/briefs?tab=sent"), "/api/v1/ai/briefs")
        self.assertIsNone(cli.v1_path("/api/compare"))
        self.assertIsNone(cli.v1_path("/api/v1/health"))
        self.assertIsNone(cli.v1_path("/screen/overview"))
        self.assertIsNone(cli.v1_path("/api/no-such-route"))


class TheFallback(unittest.TestCase):
    def test_an_open_api_is_asked_under_the_prefix_and_gives_the_same_document(self):
        served = served_monitor(self)
        calls = recording(self)
        with mock.patch.object(cli, "prefer_v1", return_value=True):
            versioned = cli.fetch(served.url, "/api/ai/index", {"lang": "en"})
        self.assertEqual(calls, ["/api/v1/ai/index"])
        with mock.patch.object(cli, "prefer_v1", return_value=False):
            plain = cli.fetch(served.url, "/api/ai/index", {"lang": "en"})
        self.assertEqual(calls[-1], "/api/ai/index")
        self.assertEqual(versioned, plain)

    def test_a_closed_api_falls_back_once_and_is_not_asked_again(self):
        served = served_monitor(self, service=False)      # "auto" outside the service mode: the prefix answers 404
        calls = recording(self)
        with mock.patch.object(cli, "prefer_v1", return_value=True):
            first = cli.fetch(served.url, "/api/ai/index", {"lang": "en"})
            second = cli.fetch(served.url, "/api/ai/index", {"lang": "en"})
        self.assertEqual(calls, ["/api/v1/ai/index", "/api/ai/index", "/api/ai/index"])
        self.assertEqual(first, second)
        self.assertIn(served.url, cli.V1_STATE["closed"])

    def test_a_route_that_is_not_frozen_is_asked_the_old_way(self):
        served = served_monitor(self)
        calls = recording(self)
        with mock.patch.object(cli, "prefer_v1", return_value=True):
            try:
                cli.fetch(served.url, "/api/compare")
            except cli.CliError:
                pass      # the answer does not matter here, the path asked does
        self.assertEqual(calls, ["/api/compare"])

    def test_a_refusal_is_not_taken_for_a_closed_prefix(self):
        served = served_monitor(self)
        with mock.patch.object(cli, "prefer_v1", return_value=True), mock.patch.object(cli, "plain_fetch", side_effect=cli.CliError(cli.EXIT_AUTH, "no")):
            with self.assertRaises(cli.CliError) as caught:
                cli.fetch(served.url, "/api/ai/index")
        self.assertEqual(caught.exception.code, cli.EXIT_AUTH)
        self.assertNotIn(served.url, cli.V1_STATE["closed"])

    def test_the_commands_give_the_same_json_by_either_way(self):
        served = served_monitor(self)
        for argv in (["briefs", "index"], ["briefs", "show", "sent"], ["check"], ["lessons", "list"]):
            answers = []
            for prefer in (True, False):
                cli.V1_STATE["closed"].clear()
                with mock.patch.object(cli, "prefer_v1", return_value=prefer):
                    import contextlib
                    import io
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                        code = cli.main([*argv, "--json", "--url", served.url, "--lang", "en"])
                answers.append((code, stable(json.loads(out.getvalue()))))
            self.assertEqual(answers[0], answers[1], argv)


class TheSameDocument(unittest.TestCase):
    def test_every_frozen_route_answers_the_same_shape_under_the_prefix(self):
        served = served_monitor(self)
        problems = []
        for row in CONTRACT["endpoints"]:
            if row.get("local_only") or not isinstance(row["complete"], dict):
                continue
            old = served.raw("GET", row["path"])
            new = served.raw("GET", "/api/v1" + row["path"][len("/api"):])
            if old[0] != new[0]:
                problems.append(f"{row['path']}: status {old[0]} vs {new[0]}")
                continue
            try:
                if shape(stable(json.loads(old[1]))) != shape(stable(json.loads(new[1]))):
                    problems.append(f"{row['path']}: the shape differs")
            except ValueError:
                problems.append(f"{row['path']}: not JSON")
        self.assertEqual(problems, [])

    def test_the_exit_codes_of_the_command_line_are_stable(self):
        self.assertEqual((cli.EXIT_OK, cli.EXIT_USAGE, cli.EXIT_DOWN, cli.EXIT_AUTH, cli.EXIT_DEGRADED, cli.EXIT_ALERTS), (0, 1, 2, 3, 4, 5))
        text = (HERE / "docs" / "CLI.md").read_text(encoding="utf-8")
        for code in ("0", "1", "2", "3", "4", "5"):
            self.assertRegex(text, rf"\b{code}\b")


class TheClientsReadWhatIsFrozen(unittest.TestCase):
    def test_every_route_the_command_line_the_terminal_views_and_the_mcp_server_read_is_frozen_or_written_down(self):
        frozen = {"/api" + p[len("/api/v1"):] for p in api_spec.frozen_paths(CONTRACT)}
        found = {}
        for name in ("cli/monitor_cli.py", "ui/tui.py", "ui/tui_textual.py", "integrations/mcp_server.py"):
            text = (SRC / name).read_text(encoding="utf-8")
            for path in re.findall(r'["\'](/api/[a-z][a-z0-9/_-]*[a-z0-9])["\'?]', text):
                found.setdefault(path, set()).add(name)
        unknown = {}
        for path, files in sorted(found.items()):
            if path in frozen or path in NOT_FROZEN or path.startswith("/api/v1"):
                continue
            if any(path == row["path"] for row in CONTRACT["unfrozen"]) or path in WRITES:
                continue      # a route the contract lists as not frozen, or a write
            unknown[path] = sorted(files)
        self.assertEqual(unknown, {}, "a client reads a route the contract does not freeze: freeze it in docs/schemas/api_contract.json or write it in NOT_FROZEN with its reason")
        for path in NOT_FROZEN:
            self.assertNotIn(path, frozen, path + " is frozen now: take it out of NOT_FROZEN")


if __name__ == "__main__":
    unittest.main()
