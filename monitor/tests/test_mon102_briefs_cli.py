# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The briefs for the AI tools also reach the command line (`briefs index | show TAB | all`) and the MCP server (`briefs_index`, `brief_tab`). Parity: the three ways (HTTP, command, MCP) list the same tabs, every
tab of the page can be read through each of them, the tools only read, a tab that does not exist is refused, and no secret travels. Nothing here reaches GitHub."""
import contextlib
import io
import json
import re
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import monitor_cli as cli  # noqa: E402
from github_actions_monitor.data_pipeline import briefs, signals  # noqa: E402
from github_actions_monitor.integrations import mcp_server  # noqa: E402
from github_actions_monitor.security import redactor  # noqa: E402

SEEN = []


def a_state():
    data = {"updated": None, "figures": {"active": 1, "queued": 0, "fail24": 2, "ok24": 5}, "repos": []}
    return signals.state(data, [{"id": "a3", "title": "Trend", "summary": "up", "level": "warn", "rows": []}], "complete", {"age_seconds": 3}, version="9.9.9")


def route(path, query):
    """What the monitor answers on its two routes, built from the same module the server uses."""
    from urllib.parse import parse_qs
    args = {k: v[0] for k, v in parse_qs(query).items() if v}
    state = a_state()
    if path == "/api/ai/index":
        return redactor.redact_data(briefs.index(state, "en", i18n.tl)), 200
    if not args.get("tab") or args.get("tab") == "all":
        every = [briefs.brief(t, state, "en", i18n.tl) for t in briefs.tabs()]
        return redactor.redact_data({"schema": briefs.SCHEMA, "kind": "ai-briefs", "edition": "complete", "version": "9.9.9", "count": len(every), "briefs": every}), 200
    document = briefs.brief(args["tab"], state, "en", i18n.tl)
    return (redactor.redact_data(document), 200) if document else ({"ok": False, "error": "tab"}, 404)


class Fake(BaseHTTPRequestHandler):
    def do_GET(self):    # noqa: N802
        SEEN.append(self.path)
        path, _, query = self.path.partition("?")
        document, status = route(path, query) if path in ("/api/ai/index", "/api/ai/briefs") else ({}, 404)
        body = json.dumps(document).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TheCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(5)

    def test_it_is_a_command_and_works_in_the_lite_edition_too(self):
        self.assertIn("briefs", cli.COMMANDS)
        self.assertIn("briefs", cli.LITE_COMMANDS)      # both routes are in LITE_SHARED
        self.assertEqual(cli.BRIEFS_ACTIONS, ("index", "show", "all"))

    def test_the_index_lists_every_tab_of_the_page(self):
        code, out, _err = run("briefs", "--url", self.url, "--json", "--lang", "en")
        self.assertEqual(code, 0)
        data = json.loads(out)["data"]
        self.assertEqual([e["tab"] for e in data["briefs"]], list(briefs.tabs()))
        code, text, _err = run("briefs", "index", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 0)
        for tab in briefs.tabs():
            self.assertRegex(text, rf"(?m)^\s+{re.escape(tab)}\s")

    def test_every_tab_can_be_read_one_by_one_and_all_at_once(self):
        for tab in briefs.tabs():
            code, out, _err = run("briefs", "show", tab, "--url", self.url, "--json")
            self.assertEqual(code, 0, tab)
            self.assertEqual(json.loads(out)["data"]["tab"], tab)
        code, out, _err = run("briefs", "all", "--url", self.url, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["data"]["count"], len(briefs.tabs()))

    def test_a_tab_that_does_not_exist_or_is_missing_is_a_usage_error(self):
        code, _out, err = run("briefs", "show", "nope", "--url", self.url)
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("nope", err)
        code, _out, _err = run("briefs", "show", "--url", self.url)
        self.assertEqual(code, cli.EXIT_USAGE)
        code, _out, _err = run("briefs", "show", "../../etc/passwd", "--url", self.url)
        self.assertEqual(code, cli.EXIT_USAGE)

    def test_it_only_reads(self):
        SEEN.clear()
        run("briefs", "all", "--url", self.url, "--json")
        self.assertTrue(SEEN)
        self.assertTrue(all(p.startswith("/api/ai/") for p in SEEN), SEEN)

    def test_the_texts_of_the_command_exist_in_the_eight_languages(self):
        keys = ("briefs_action", "briefs_head", "briefs_tab_needed", "briefs_unknown_tab", "briefs_signals", "briefs_none")
        for lang in i18n.LANGS:
            for key in keys:
                self.assertNotEqual(i18n.tl(lang, "cli." + key, n=1, edition="x", tab="t"), "cli." + key, (lang, key))


class TheTools(unittest.TestCase):
    config = {}

    @staticmethod
    def getter(path, port=None):
        base, _, query = path.partition("?")
        document, status = route(base, query)
        if status != 200:
            raise OSError("404")
        return document

    def call(self, name, arguments):
        return mcp_server.call(name, arguments, self.config, getter=self.getter)

    def test_the_two_tools_exist_and_only_read(self):
        tools = {t["name"]: t for t in mcp_server.TOOLS}
        self.assertIn("briefs_index", tools)
        self.assertIn("brief_tab", tools)
        listed = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.config)["result"]["tools"]
        self.assertTrue({"briefs_index", "brief_tab"} <= {t["name"] for t in listed})      # no --allow-ack needed
        self.assertEqual(tools["brief_tab"]["inputSchema"]["required"], ["tab"])

    def test_the_index_and_every_tab_are_the_same_as_over_http(self):
        index = json.loads(self.call("briefs_index", {}))
        self.assertEqual([e["tab"] for e in index["briefs"]], list(briefs.tabs()))
        for tab in briefs.tabs():
            self.assertEqual(json.loads(self.call("brief_tab", {"tab": tab}))["tab"], tab)
        self.assertEqual(json.loads(self.call("brief_tab", {"tab": "all"}))["count"], len(briefs.tabs()))

    def test_a_wrong_tab_is_refused(self):
        for bad in ("", "../x", "A B", "x" * 40, None):
            with self.assertRaises(ValueError, msg=bad):
                self.call("brief_tab", {"tab": bad})
        reply = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "brief_tab", "arguments": {"tab": "nope"}}}, self.config, getter=self.getter)
        self.assertTrue(reply["result"]["isError"])      # a tab the monitor does not know: an error reply, the loop of the server goes on

    def test_a_secret_in_an_answer_never_reaches_the_tool(self):
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        text = mcp_server.call("briefs_index", {}, self.config, getter=lambda path, port=None: {"briefs": [{"tab": "x", "note": "token " + token}]})
        self.assertNotIn(token, text)

    def test_the_tools_and_the_command_are_named_in_the_docs_and_the_skills(self):
        connection = (HERE / "docs" / "AI_CONNECTION.md").read_text(encoding="utf-8")
        self.assertIn("`briefs_index`", connection)
        self.assertIn("`brief_tab`", connection)
        self.assertIn("briefs show", connection)
        cli_md = (HERE / "skills" / "external" / "references" / "cli.md").read_text(encoding="utf-8")
        self.assertIn("`briefs`", cli_md)


if __name__ == "__main__":
    unittest.main()
