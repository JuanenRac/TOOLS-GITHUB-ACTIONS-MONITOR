# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract suite for outside clients (tools/api_contract_suite.py): it passes against this monitor and fails, naming the check, against a server that breaks the contract on purpose (a key that
disappears, a type that changes, a wrong error code, a header that is missing, a method that is not refused, a cursor that is accepted for another query)."""
import contextlib
import http.client
import io
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import api_contract_suite as suite  # noqa: E402


def view(name, state="ok"):
    return {"repo": name, "ecosystem": "HYDRA", "ecosystem_label": "HYDRA", "state": state, "risk": 3,
            "ci": {"runs_24h": 4, "successes_24h": 3, "failures_24h": 1, "success_rate_24h": 75, "red_workflows": ["a"], "stuck_runs": 0},
            "alerts": {"total": 2, "by_sentinel": {}, "by_level": {}, "items": []}, "readiness": None, "activity": {"last_run_at": None, "runs_7d": 9, "idle_days": 0},
            "sources": {}, "not_fully_seen": []}


VIEWS = [view("repo%03d" % n, "bad" if n % 10 == 0 else "ok") for n in range(40)]


def real_monitor(case):
    served = Served(case, lite=False)
    for patcher in (mock.patch.object(actions_monitor, "service_mode", return_value=True), mock.patch.object(actions_monitor, "health_views", return_value=VIEWS)):
        patcher.start()
        case.addCleanup(patcher.stop)
    return served


class Broken:
    """A server in front of the real one that changes what it answers: `mutate(method, path, status, headers, body)` returns the new (status, headers, body)."""

    def __init__(self, case, origin, mutate):
        port = origin.port

        class Handler(BaseHTTPRequestHandler):
            def handle_any(self):
                length = int(self.headers.get("Content-Length") or 0)
                data = self.rfile.read(length) if length else None
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                try:
                    connection.request(self.command, self.path, data, {"Host": f"127.0.0.1:{port}"})      # identity: the proxy answers without gzip
                    answer = connection.getresponse()
                    status, headers, body = answer.status, {k.lower(): v for k, v in answer.getheaders()}, answer.read()
                finally:
                    connection.close()
                status, headers, body = mutate(self.command, self.path, status, headers, body)
                self.send_response(status)
                for key in ("content-type", "x-api-version", "cache-control"):
                    if key in headers:
                        self.send_header(key, headers[key])
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = handle_any    # noqa: N815

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"


def failed_names(url):
    return [r["check"] for r in suite.run(suite.Client(url)).failed]


def edit_json(body, change):
    document = json.loads(body)
    change(document)
    return json.dumps(document).encode("utf-8")


class AgainstThisMonitor(unittest.TestCase):
    def test_the_suite_passes_and_covers_the_document_the_server_serves(self):
        served = real_monitor(self)
        report = suite.run(suite.Client(served.url))
        self.assertEqual([r for r in report.rows if not r["ok"]], [])
        names = " ".join(r["check"] for r in report.rows)
        for word in ("openapi: served", "GET /api/v1/health", "GET /api/v1/me", "error api.bad_limit", "repos: the second page", "nothing is written: POST", "gzip"):
            self.assertIn(word, names)
        self.assertGreater(len(report.rows), 60)      # one check per frozen route that needs no parameter, plus the rules of the contract

    def test_the_command_prints_pass_and_the_json_form_is_one_document(self):
        served = real_monitor(self)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = suite.main(["--url", served.url])
        self.assertEqual(code, 0)
        self.assertTrue(out.getvalue().strip().endswith("API_CONTRACT=PASS"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            suite.main(["--url", served.url, "--json"])
        self.assertTrue(json.loads(out.getvalue().rsplit("API_CONTRACT=", 1)[0])["ok"])

    def test_nothing_answering_is_exit_2_and_a_closed_api_fails(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(suite.main(["--url", "http://127.0.0.1:9", "--timeout", "2"]), 2)
        self.assertIn("API_CONTRACT=FAIL", out.getvalue())
        served = Served(self, lite=False)      # one person at one computer: the prefix is closed
        self.assertIn("openapi: served", failed_names(served.url))


class AgainstABrokenServer(unittest.TestCase):
    def broken(self, mutate):
        return Broken(self, real_monitor(self), mutate).url

    def test_a_key_that_disappears_is_named(self):
        def mutate(method, path, status, headers, body):
            if method == "GET" and path.startswith("/api/v1/health"):
                return status, headers, edit_json(body, lambda d: d.pop("uptime_seconds"))
            return status, headers, body
        report = suite.run(suite.Client(self.broken(mutate)))
        row = next(r for r in report.failed if r["check"] == "GET /api/v1/health")
        self.assertIn("uptime_seconds", row["detail"])

    def test_a_type_that_changes_is_named(self):
        def mutate(method, path, status, headers, body):
            if method == "GET" and path.startswith("/api/v1/health"):
                return status, headers, edit_json(body, lambda d: d.update(uptime_seconds="soon"))
            return status, headers, body
        row = next(r for r in suite.run(suite.Client(self.broken(mutate))).failed if r["check"] == "GET /api/v1/health")
        self.assertIn("uptime_seconds", row["detail"])

    def test_a_wrong_error_code_is_caught(self):
        def mutate(method, path, status, headers, body):
            if path.startswith("/api/v1/repos?limit=0"):
                return status, headers, edit_json(body, lambda d: d.update(code="api.other"))
            return status, headers, body
        self.assertIn("error api.bad_limit", failed_names(self.broken(mutate)))

    def test_a_missing_version_header_is_caught(self):
        def mutate(method, path, status, headers, body):
            headers.pop("x-api-version", None)
            return status, headers, body
        names = failed_names(self.broken(mutate))
        self.assertIn("openapi: header X-API-Version", names)

    def test_a_write_that_is_accepted_is_caught(self):
        def mutate(method, path, status, headers, body):
            return (200, headers, b"{}") if method in ("POST", "PUT") else (status, headers, body)
        names = failed_names(self.broken(mutate))
        self.assertIn("nothing is written: POST is refused", names)
        self.assertIn("nothing is written: PUT is refused", names)
        self.assertNotIn("nothing is written: DELETE is refused", names)

    def test_a_key_missing_from_the_repository_lines_is_caught(self):
        def mutate(method, path, status, headers, body):
            if method == "GET" and path.split("?")[0] == "/api/v1/repos" and status == 200:
                return status, headers, edit_json(body, lambda d: [i.pop("state") for i in d["items"]])
            return status, headers, body
        row = next(r for r in suite.run(suite.Client(self.broken(mutate))).failed if r["check"] == "GET /api/v1/repos")
        self.assertIn("state", row["detail"])

    def test_a_cursor_that_is_not_bound_to_its_query_is_caught(self):
        def mutate(method, path, status, headers, body):
            if "state=bad&cursor=" in path:      # the real server refuses; this one lets it through
                return 200, headers, json.dumps({"items": [], "next_cursor": None, "limit": 2, "total": 0}).encode("utf-8")
            return status, headers, body
        self.assertIn("repos: a cursor of another query is refused", failed_names(self.broken(mutate)))


class TheShapeRules(unittest.TestCase):
    def test_a_key_the_schema_does_not_name_is_allowed_and_a_missing_one_is_not(self):
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}, "n": {"nullable": True}}}
        self.assertEqual(suite.shape_problems("x", {"a": 1, "extra": 2}, schema), [])
        self.assertEqual(suite.shape_problems("x", {"a": 1, "n": None}, schema), [])
        self.assertTrue(suite.shape_problems("x", {"b": 1}, schema))
        self.assertTrue(suite.shape_problems("x", {"a": True}, schema))      # a boolean is not an integer
        self.assertTrue(suite.shape_problems("x", {"a": "1"}, schema))
        self.assertTrue(suite.shape_problems("x", [], schema))
        listed = {"type": "array", "items": {"type": "object", "required": ["r"]}}
        self.assertTrue(suite.shape_problems("l", [{"r": 1}, {}], listed))

    def test_the_token_is_read_from_a_file_and_never_from_the_command_line(self):
        parser_source = (HERE / "tools" / "api_contract_suite.py").read_text(encoding="utf-8")
        self.assertIn("--token-file", parser_source)
        self.assertNotIn('"--token"', parser_source)


class TheCiRunsIt(unittest.TestCase):
    def test_the_workflow_runs_the_suite_against_the_demo_in_the_service_mode(self):
        workflow = HERE.parent / ".github" / "workflows" / "ci.yml"
        if not workflow.is_file():
            self.skipTest("the workflow does not travel in the zip")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("api_contract_suite.py", text)
        self.assertIn("MONITOR_SERVICE", text)


if __name__ == "__main__":
    unittest.main()
