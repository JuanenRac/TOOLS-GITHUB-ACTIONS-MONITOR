# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The `compare` command: it reads /api/compare, prints the figures with their change and direction, says why a figure is missing, keeps its exit codes (0 compared, 4 too little data or off, 5 with
--fail-on when something got worse), asks only for what the flags say, and is not in Lite."""
import contextlib
import io
import json
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

ANSWERS, SEEN = {}, []


class Fake(BaseHTTPRequestHandler):
    def do_GET(self):    # noqa: N802
        SEEN.append(self.path)
        answer = ANSWERS.get(self.path.partition("?")[0])
        if answer is None:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(answer).encode("utf-8")
        self.send_response(200)
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


def entry(now, base, direction, state="ok", better="lower"):
    return {"now": now, "base": base, "delta": None if now is None or base is None else round(now - base, 4), "direction": direction, "better": better, "state": state}


def answer(**over):
    data = {"schema": 1, "account": "alpha", "enabled": True, "state": "compared", "baseline": "previous", "days": "all", "coverage": 1.0,
            "windows": {"now": {"from": 1_799_395_200.0, "to": 1_800_000_000.0}, "base": {"from": 1_798_790_400.0, "to": 1_799_395_200.0}, "days": 7.0},
            "metrics": {"red_rate": entry(0.25, 0.1, "worse"), "duration_p50": entry(60.0, 120.0, "better"), "resolution": entry(None, 3600.0, "unknown", "insufficient_data"),
                        "score_mean": entry(80.0, 70.0, "better", better="higher"), "score_coverage": entry(0.8, 0.8, "same", better="higher")},
            "changes": {"worse": [{"repo": "a/x", "red_rate_now": 0.5, "red_rate_base": 0.25, "delta": 0.25, "runs_now": 4, "runs_base": 4}], "better": [],
                        "new_failures": [{"repo": "a/y", "workflow": "Deploy", "failures": 3}], "resolved_failures": [], "reason": None},
            "data_quality": {"runs_now": 40, "runs_base": 40, "min_runs": 20, "truncated": False, "reasons": []}}
    data.update(over)
    return data


class Compare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        ANSWERS.clear()
        SEEN.clear()
        ANSWERS["/api/compare"] = answer()

    def ask(self, *argv):
        return run("compare", "--url", self.url, *argv)

    def test_the_figures_the_change_and_the_lists(self):
        code, out, _ = self.ask()
        self.assertEqual(code, 4)      # one figure has too little data
        self.assertIn("Comparison of alpha: 7.0 days ending", out)
        self.assertIn("Share of failed runs: 25.0% (before 10.0%, change +15 pts, worse)", out)
        self.assertIn("Median duration: 1 min (before 2 min, change -60 s, better)", out)
        self.assertIn("Time to resolve alerts: not enough data", out)
        self.assertIn("a/x: 25% -> 50%", out)
        self.assertIn("a/y / Deploy: 3", out)

    def test_exit_zero_when_everything_could_be_compared(self):
        ANSWERS["/api/compare"] = answer(metrics={"red_rate": entry(0.1, 0.1, "same")})
        self.assertEqual(self.ask()[0], 0)

    def test_fail_on_turns_a_worse_figure_into_exit_five(self):
        self.assertEqual(self.ask("--fail-on", "warning")[0], 5)
        ANSWERS["/api/compare"] = answer(metrics={"red_rate": entry(0.05, 0.1, "better")})
        self.assertEqual(self.ask("--fail-on", "warning")[0], 0)

    def test_the_flags_are_what_is_asked(self):
        self.ask("--window", "30d", "--days", "workdays", "--baseline", "year_ago", "--account", "alpha")
        query = SEEN[-1]
        for part in ("window=30d", "days=workdays", "baseline=year_ago", "account=alpha"):
            self.assertIn(part, query)
        self.ask()
        self.assertNotIn("window=", SEEN[-1])

    def test_json_ndjson_and_csv(self):
        code, out, _ = self.ask("--json")
        self.assertEqual(json.loads(out)["data"]["metrics"]["red_rate"]["now"], 0.25)
        code, out, _ = self.ask("--format", "json")
        self.assertEqual(json.loads(out)["data"]["schema"], 1)
        code, out, _ = self.ask("--format", "ndjson")
        self.assertEqual(json.loads(out.splitlines()[0])["metric"], "red_rate")
        code, out, _ = self.ask("--format", "csv")
        self.assertEqual(out.splitlines()[0], "metric,now,base,delta,direction,state")

    def test_off_calibrating_and_no_baseline_say_why(self):
        ANSWERS["/api/compare"] = {"schema": 1, "account": "alpha", "enabled": False, "state": "off", "metrics": {}}
        code, out, _ = self.ask()
        self.assertEqual((code, out.strip()), (4, "The comparison is off (compare.enabled)."))
        ANSWERS["/api/compare"] = answer(state="baseline_unavailable", data_quality={"reasons": ["history_too_short"]}, metrics={"red_rate": entry(0.2, None, "unknown", "baseline_unavailable")})
        code, out, _ = self.ask()
        self.assertEqual(code, 4)
        self.assertIn("compare.min_days_of_history", out)
        self.assertIn("no baseline", out)

    def test_it_is_in_the_other_languages_too(self):
        with i18n.use_language("es"):
            self.assertIn("Comparación de alpha", self.ask()[1])

    def test_a_wrong_window_is_dropped_and_lite_has_no_compare(self):
        self.ask("--window", "abc")
        self.assertNotIn("window=", SEEN[-1])
        self.assertIn("compare", cli.COMMANDS)
        self.assertNotIn("compare", cli.LITE_COMMANDS)
        code, _, err = run("compare", "--lite")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
