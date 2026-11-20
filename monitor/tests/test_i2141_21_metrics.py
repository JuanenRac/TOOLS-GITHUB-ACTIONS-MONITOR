# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`metrics`: the figures as `name=value` lines and nothing else (made for cron and mail), a figure that is not known is left out, and with --if-problem it writes nothing when all is well."""
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402

DATA = {"data": {"repos": [{}, {}, {}], "figures": {"active": 2, "queued": 1, "fail24": 4, "ok24": 40, "red": 0}, "rate": {"remaining": 4000, "limit": 5000}, "updated": "2026-01-01T00:00:00Z"}}


class Metrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), base.Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        base.ANSWERS.clear()
        base.SEEN.clear()
        base.ANSWERS["/api/health"] = {"version": "9.9.9", "account": "alpha", "uptime_seconds": 5}
        base.ANSWERS["/api/data"] = json.loads(json.dumps(DATA))
        base.ANSWERS["/api/alerts"] = {"alerts": [{"level": "warning", "code": "a"}, {"level": "info", "code": "b"}]}

    def ask(self, *argv):
        return base.run("metrics", *argv, "--url", self.url, "--lang", "en")

    def test_one_name_value_line_per_figure_and_nothing_else(self):
        code, out, err = self.ask()
        self.assertEqual(code, 0)
        self.assertNotIn("Traceback", err)
        lines = out.splitlines()
        self.assertTrue(all("=" in line and " " not in line for line in lines), out)
        values = dict(line.split("=", 1) for line in lines)
        self.assertEqual((values["repos"], values["queued"], values["failures_24h"], values["alerts"], values["alerts_warning"], values["allowance_remaining"]), ("3", "1", "4", "2", "1", "4000"))
        self.assertEqual(list(values)[:2], ["repos", "active"])      # a fixed order

    def test_a_figure_that_is_not_known_is_left_out_not_written_as_zero(self):
        base.ANSWERS["/api/data"] = {"data": {"repos": [], "figures": {}, "rate": {}, "updated": "2026-01-01T00:00:00Z"}}
        code, out, _ = self.ask()
        names = [line.split("=")[0] for line in out.splitlines()]
        self.assertNotIn("allowance_remaining", names)
        self.assertNotIn("queued", names)

    def test_if_problem_writes_nothing_and_exits_0_when_all_is_well(self):
        code, out, err = self.ask("--if-problem")
        self.assertEqual((code, out), (0, ""))
        self.assertNotIn("Traceback", err)

    def test_if_problem_writes_the_figures_and_exits_5_for_a_red_workflow_or_an_alert(self):
        base.ANSWERS["/api/data"]["data"]["figures"]["red"] = 2
        code, out, _ = self.ask("--if-problem")
        self.assertEqual(code, 5)
        self.assertIn("red_workflows=2", out)
        base.ANSWERS["/api/data"]["data"]["figures"]["red"] = 0
        base.ANSWERS["/api/alerts"] = {"alerts": [{"level": "error", "code": "x"}]}
        code, out, _ = self.ask("--if-problem")
        self.assertEqual(code, 5)
        self.assertIn("alerts_error=1", out)
        code, out, _ = self.ask("--if-problem", "--fail-on", "critical")      # the level is the one asked for
        self.assertEqual((code, out), (0, ""))

    def test_json_and_plain_give_the_same_figures(self):
        code, out, _ = self.ask("--json")
        self.assertEqual(json.loads(out)["data"]["repos"], 3)
        code, out, _ = self.ask("--format", "ndjson")
        self.assertEqual(json.loads(out)["queued"], 1)

    def test_the_monitor_not_reachable_is_an_error_not_a_silence(self):
        code, out, err = base.run("metrics", "--if-problem", "--url", "http://127.0.0.1:9", "--lang", "en", "--timeout", "1")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err)

    def test_it_is_a_command_of_the_cli_and_not_of_the_lite_edition(self):
        self.assertIn("metrics", monitor_cli.COMMANDS)
        self.assertNotIn("metrics", monitor_cli.LITE_COMMANDS)


if __name__ == "__main__":
    unittest.main()
