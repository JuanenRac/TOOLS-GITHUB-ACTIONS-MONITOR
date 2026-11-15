# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The `score` command: it reads /api/score (and the history with --compare), says why there is no number, never fails because the score is not there yet, and is not in Lite."""
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

ANSWERS = {}
SEEN = []


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


def scored():
    return {"schema": 1, "account": "alpha", "enabled": True, "state": "scored", "score": 82.5, "letter": "B", "trend": {"direction": "up", "delta": 3.0}, "coverage": 0.8,
            "complete": False, "missing_parts": ["security"], "window_days": 7, "stale": True, "age_seconds": 14400,
            "parts": [{"part": "reliability", "weight": 40, "score": 90.0}, {"part": "speed", "weight": 20, "score": 70.0}, {"part": "recovery", "weight": 20, "score": 80.0},
                      {"part": "collaboration", "weight": 20, "score": None}],
            "repos": [{"repo": "a/x", "state": "scored", "score": 61.0, "letter": "D", "runs": 30}, {"repo": "a/y", "state": "insufficient_data", "score": None, "letter": None, "runs": 3}],
            "data_quality": {"runs": 120, "reasons": []}}


class Score(unittest.TestCase):
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
        ANSWERS["/api/score"] = scored()
        ANSWERS["/api/score/history"] = {"points": [{"score": 70.0}, {"score": 60.0}, {"score": 82.5}]}

    def ask(self, *argv, lang="en"):
        return run(*argv, "--url", self.url, "--lang", lang)

    def test_the_number_the_letter_the_trend_the_parts_and_what_is_missing(self):
        code, out, _ = self.ask("score")
        self.assertEqual(code, 0, out)
        for needle in ("alpha", "82.5 (B)", "up 3.0 points", "Coverage 80 %", "120 finished runs in 7 days", "reliability: 90.0 (weight 40)", "collaboration: no data (weight 20)",
                       "Not collected yet: security", "a/x: 61.0 D (30 runs)", "a/y: insufficient_data (3 runs)", "4 h 0 min old"):
            self.assertIn(needle, out)

    def test_json_is_the_answer_of_the_api_inside_the_usual_document(self):
        code, out, _ = self.ask("score", "--json")
        doc = json.loads(out)
        self.assertEqual((code, doc["ok"], doc["exit"]), (0, True, 0))
        self.assertEqual((doc["data"]["score"], doc["data"]["missing_parts"], doc["data"]["complete"]), (82.5, ["security"], False))

    def test_the_account_goes_to_the_monitor(self):
        self.ask("score", "--account", "beta")
        self.assertIn("account=beta", " ".join(SEEN))

    def test_no_number_yet_is_said_with_its_reason_and_is_not_an_error(self):
        for state, word in (("calibrating", "calibrating"), ("insufficient_data", "not enough data"), ("off", "switched off")):
            ANSWERS["/api/score"] = {"account": "alpha", "state": state, "score": None, "letter": None, "coverage": 0.0, "parts": [], "repos": [], "missing_parts": ["security"],
                                     "window_days": 7, "data_quality": {"runs": 0}}
            code, out, _ = self.ask("score")
            self.assertEqual(code, 0)
            self.assertIn("no number yet (" + word + ")", out)

    def test_compare_sets_the_score_against_the_oldest_point_of_the_window(self):
        code, out, _ = self.ask("score", "--compare", "--json")
        doc = json.loads(out)["data"]["compare"]
        self.assertEqual((code, doc["hours"], doc["delta"], doc["lowest"], doc["highest"], doc["points"]), (0, 168, 12.5, 60.0, 82.5, 3))
        self.assertIn("hours=168", " ".join(SEEN))
        _, text, _ = self.ask("score", "--compare")
        self.assertIn("Against 168 h ago: +12.5 points (lowest 60.0, highest 82.5, 3 points)", text)

    def test_compare_without_enough_history_says_so(self):
        ANSWERS["/api/score/history"] = {"points": [{"score": 70.0}]}
        _, out, _ = self.ask("score", "--compare")
        self.assertIn("Not enough history to compare yet.", out)

    def test_a_monitor_without_the_route_is_degraded_not_a_traceback(self):
        del ANSWERS["/api/score"]
        code, _, err = self.ask("score")
        self.assertEqual(code, 4)
        self.assertTrue(err)

    def test_lite_has_no_score(self):
        code, _, err = run("score", "--lite", "--lang", "en")
        self.assertEqual(code, 1)
        self.assertTrue(err)

    def test_every_text_exists_in_the_eight_languages(self):
        keys = [k for k in __import__("json").loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8")) if k.startswith("cli.score_") or k == "cli.help_compare"]
        self.assertGreaterEqual(len(keys), 20)
        for lang in i18n.LANGS:
            for key in keys:
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        self.assertIn("score", cli.COMMANDS)
        self.assertNotIn("score", cli.LITE_COMMANDS)


if __name__ == "__main__":
    unittest.main()
