# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What /api/score and /api/score/history answer: coverage and quality always present, a state instead of a number when there is none, old snapshots said to be old, and Lite without the routes."""
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.scoring import api  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402
from github_actions_monitor.storage import file_storage, sqlite_storage  # noqa: E402

NOW = 1_800_000_000.0


def snapshot(at, score=82.5, state="scored"):
    return {"schema": 1, "at": at, "account": "alpha", "window_days": 7, "state": state, "score": score, "letter": "B", "trend": {"direction": "up", "delta": 3.0}, "coverage": 0.8,
            "complete": False, "missing_parts": ["security"], "parts": [], "repos": [{"repo": "a/x", "state": "scored", "score": 90, "letter": "A", "runs": 30, "success_rate": 0.99}],
            "data_quality": {"runs": 80, "min_runs": 20, "coverage": 0.8, "min_coverage": 0.5, "watched_hours": 200.0, "reasons": []}}


def hour(at):
    import time
    return time.strftime("%Y-%m-%dT%H", time.gmtime(at))


class Latest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = file_storage.FileStorage(Path(self.tmp.name))

    def test_nothing_written_yet_is_calibrating_and_says_why(self):
        r = api.latest(self.s, "alpha", {}, now=NOW)
        self.assertEqual((r["state"], r["score"], r["letter"], r["coverage"]), ("calibrating", None, None, 0.0))
        self.assertEqual(r["data_quality"]["reasons"], ["no_snapshot_yet"])
        self.assertFalse(r["complete"])
        self.assertEqual(r["missing_parts"], ["security"])

    def test_the_score_off_says_off(self):
        r = api.latest(self.s, "alpha", {"score": {"enabled": False}}, now=NOW)
        self.assertEqual((r["enabled"], r["state"], r["score"]), (False, "off", None))

    def test_the_newest_snapshot_is_served_with_its_age(self):
        self.s.save_score_snapshot("alpha", hour(NOW - 7200), snapshot(NOW - 7200, 70))
        self.s.save_score_snapshot("alpha", hour(NOW - 60), snapshot(NOW - 60, 82.5))
        r = api.latest(self.s, "alpha", {}, now=NOW)
        self.assertEqual((r["score"], r["letter"], r["age_seconds"], r["stale"], r["account"], r["schema"]), (82.5, "B", 60, False, "alpha", 1))
        self.assertEqual(r["repos"][0]["repo"], "a/x")
        self.assertNotIn("hour", r)

    def test_an_old_snapshot_is_said_to_be_old(self):
        self.s.save_score_snapshot("alpha", hour(NOW - 5 * 3600), snapshot(NOW - 5 * 3600))
        self.assertTrue(api.latest(self.s, "alpha", {}, now=NOW)["stale"])

    def test_every_answer_has_the_fields_a_client_relies_on(self):
        self.s.save_score_snapshot("alpha", hour(NOW), snapshot(NOW))
        for r in (api.latest(self.s, "alpha", {}, now=NOW), api.latest(file_storage.FileStorage(Path(self.tmp.name) / "empty"), "alpha", {}, now=NOW)):
            for key in ("schema", "account", "state", "score", "letter", "trend", "coverage", "complete", "missing_parts", "data_quality", "parts", "repos", "window_days"):
                self.assertIn(key, r)

    def test_another_account_is_not_served(self):
        self.s.save_score_snapshot("alpha", hour(NOW), snapshot(NOW))
        self.assertEqual(api.latest(self.s, "beta", {}, now=NOW)["state"], "calibrating")


class History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = file_storage.FileStorage(Path(self.tmp.name))
        for h in range(0, 30):
            at = NOW - h * 3600
            self.s.save_score_snapshot("alpha", hour(at), snapshot(at, 50 + h))

    def test_oldest_first_and_only_the_fields_of_a_point(self):
        r = api.history(self.s, "alpha", {}, {"hours": "5"}, now=NOW)
        self.assertEqual(len(r["points"]), 6)
        ats = [p["at"] for p in r["points"]]
        self.assertEqual(ats, sorted(ats))
        self.assertEqual(set(r["points"][0]), set(api.HISTORY_FIELDS))

    def test_the_default_is_the_window_of_the_account(self):
        self.assertEqual(api.history(self.s, "alpha", {}, now=NOW)["hours"], 7 * 24)
        self.assertEqual(api.history(self.s, "alpha", {"score": {"window_days": 3}}, now=NOW)["hours"], 72)

    def test_limits_are_clamped_and_bad_values_ignored(self):
        self.assertEqual(api.history(self.s, "alpha", {}, {"hours": "999999"}, now=NOW)["hours"], 24 * 90)
        self.assertEqual(api.history(self.s, "alpha", {}, {"hours": "0"}, now=NOW)["hours"], 1)
        self.assertEqual(api.history(self.s, "alpha", {}, {"hours": "x"}, now=NOW)["hours"], 168)
        self.assertEqual(len(api.history(self.s, "alpha", {}, {"hours": "100", "limit": "3"}, now=NOW)["points"]), 3)

    def test_off_gives_no_points(self):
        self.assertEqual(api.history(self.s, "alpha", {"score": {"enabled": False}}, now=NOW)["points"], [])

    def test_the_sqlite_storage_answers_the_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite_storage.SqliteStorage(Path(tmp) / "monitor.db")
            try:
                for h in range(0, 5):
                    db.save_score_snapshot("alpha", hour(NOW - h * 3600), snapshot(NOW - h * 3600, 60 + h))
                self.assertEqual(len(api.history(db, "alpha", {}, {"hours": "10"}, now=NOW)["points"]), 5)
                self.assertEqual(api.latest(db, "alpha", {}, now=NOW)["score"], 60)
            finally:
                db.close()


class Routes(unittest.TestCase):
    def test_the_handler_serves_both_routes_and_lite_does_not_have_them(self):
        source = inspect.getsource(actions_monitor)
        self.assertIn('path in ("/api/score", "/api/score/history")', source)
        self.assertTrue(any("/api/score".startswith(p) or p.startswith("/api/score") for p in actions_monitor.LITE_PATHS))

    def test_a_viewer_may_read_the_score_and_only_an_admin_changes_the_settings_behind_it(self):
        self.assertEqual(auth.required_role("GET", "/api/score"), "viewer")
        self.assertEqual(auth.required_role("GET", "/api/score/history?hours=5"), "viewer")
        self.assertEqual(auth.required_role("POST", "/api/settings"), "admin")


if __name__ == "__main__":
    unittest.main()
