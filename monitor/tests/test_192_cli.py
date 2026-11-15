# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The `team` command: the ranking of the repositories and the detail of one, read from the routes of the health views; a repository that was not fully seen is said, a bad name is a usage error, and
the command is not in Lite."""
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

TEAM = {"schema": 1, "all": 3, "shown": 2, "truncated": False, "totals": {"bad": 1, "warn": 1, "ok": 0, "unknown": 0}, "by_ecosystem": {}, "alerts": {"by_sentinel": {}, "by_level": {}},
        "ranking": [{"repo": "a/x", "ecosystem": "alpha", "state": "bad", "risk": 55, "red_workflows": 1, "alerts": 1, "failures_24h": 2, "last_run_at": None, "release_next": None},
                    {"repo": "a/y", "ecosystem": "alpha", "state": "warn", "risk": 3, "red_workflows": 0, "alerts": 1, "failures_24h": 0, "last_run_at": None, "release_next": None}], "filters": {}}
ONE = {"schema": 1, "health": {"repo": "a/x", "state": "bad", "risk": 55, "ci": {"successes_24h": 4, "failures_24h": 2, "red_workflows": ["ci"], "stuck_runs": 0},
                                "alerts": {"total": 1, "items": [{"level": "critical", "sentinel": "security", "code": "security.secret", "title": "A secret"}]}, "not_fully_seen": ["collab"]}}


class Team(unittest.TestCase):
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
        base.ANSWERS["/api/team/health"] = TEAM
        base.ANSWERS["/api/repos/a/x/health"] = ONE

    def ask(self, *argv, lang="en"):
        return base.run(*argv, "--url", self.url, "--lang", lang)

    def test_the_ranking_with_the_totals_and_the_repositories_in_order(self):
        code, out, _ = self.ask("team")
        self.assertEqual(code, 0, out)
        self.assertIn("2 of 3 repositories (bad 1, warning 1, OK 0, not seen 0)", out)
        self.assertLess(out.index("a/x"), out.index("a/y"))
        self.assertIn("risk 55", out)

    def test_the_severity_goes_to_the_monitor(self):
        self.ask("team", "--severity", "warn")
        self.assertIn("severity=warn", " ".join(base.SEEN))

    def test_one_repository_says_what_it_was_not_fully_seen_by(self):
        code, out, _ = self.ask("team", "--repo", "a/x")
        self.assertEqual(code, 0, out)
        for needle in ("a/x: BAD", "4 successful, 2 failed", "red now: ci", "security.secret", "Not fully seen by: collab"):
            self.assertIn(needle, out)

    def test_json_is_the_answer_inside_the_usual_document(self):
        code, out, _ = self.ask("team", "--json")
        doc = json.loads(out)
        self.assertEqual((code, doc["ok"], doc["data"]["shown"]), (0, True, 2))

    def test_a_repository_that_is_not_owner_slash_name_is_a_usage_error(self):
        code, _, err = self.ask("team", "--repo", "x")
        self.assertEqual(code, 1)
        self.assertIn("owner/name", err)

    def test_an_unknown_repository_is_degraded_not_a_traceback(self):
        code, _, _ = self.ask("team", "--repo", "a/nothing")
        self.assertEqual(code, 4)

    def test_it_is_not_in_lite(self):
        code, _, _ = self.ask("team", "--lite")
        self.assertEqual(code, 1)

    def test_the_words_exist_in_the_eight_languages(self):
        for lang in ("es", "de", "fr", "it", "ja", "zh", "pt"):
            code, out, _ = self.ask("team", lang=lang)
            self.assertEqual(code, 0)
            self.assertNotIn("repositories (", out)


if __name__ == "__main__":
    unittest.main()
