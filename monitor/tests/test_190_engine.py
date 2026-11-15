# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""ScoreEngine: the weighted sum, the letter, the trend, and every case in which no number may be shown."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.scoring import engine  # noqa: E402

CFG = engine.settings({})


def metrics(rate=0.98, p95=600, mttr=1800, collab=172800, runs=100, recoveries=5, closed=5):
    return {"success_rate": rate, "duration_p95": p95, "mttr": mttr, "collab_resolution_time": collab,
            "samples": {"runs": runs, "durations": runs, "recoveries": recoveries, "collab_closed": closed}}


class Parts(unittest.TestCase):
    def test_linear_between_bad_and_good(self):
        self.assertEqual(engine.part_score(0.98, 0.98, 0.5), 100)
        self.assertEqual(engine.part_score(0.5, 0.98, 0.5), 0)
        self.assertEqual(engine.part_score(0.74, 0.98, 0.5), 50)
        self.assertEqual(engine.part_score(600, 600, 3600), 100)       # lower is better works too
        self.assertEqual(engine.part_score(2100, 600, 3600), 50)
        self.assertEqual(engine.part_score(99999, 600, 3600), 0)
        self.assertEqual(engine.part_score(1, 600, 3600), 100)

    def test_unusable_values_have_no_score(self):
        for bad in (None, True, "x", float("nan"), float("inf")):
            self.assertIsNone(engine.part_score(bad, 1, 0))


class Scored(unittest.TestCase):
    def test_all_good_is_100_and_A(self):
        r = engine.compute(metrics(), CFG)
        self.assertEqual((r["state"], r["score"], r["letter"]), ("scored", 100.0, "A"))

    def test_weights_are_applied(self):
        # reliability 100 (weight 40), the other three 0 (weight 60)
        r = engine.compute(metrics(p95=3600, mttr=86400, collab=1209600), CFG)
        self.assertEqual(r["score"], 40.0)
        self.assertEqual(r["letter"], "E")

    def test_letters_follow_the_cuts(self):
        g = CFG["grades"]
        self.assertEqual([engine.letter(s, g) for s in (95, 90, 89.9, 80, 70, 55, 54.9, 0)], ["A", "A", "B", "B", "C", "D", "E", "E"])

    def test_the_answer_always_carries_coverage_quality_and_the_missing_security(self):
        r = engine.compute(metrics(), CFG)
        self.assertEqual(r["coverage"], 1.0)
        self.assertEqual(r["missing_parts"], ["security"])
        self.assertFalse(r["complete"])
        self.assertEqual(r["data_quality"]["runs"], 100)
        self.assertEqual({p["part"] for p in r["parts"]}, set(engine.PARTS))

    def test_a_part_without_data_is_left_out_and_lowers_coverage(self):
        r = engine.compute(metrics(collab=None, closed=0), CFG)
        self.assertEqual(r["state"], "scored")
        self.assertEqual(r["coverage"], 0.8)
        self.assertEqual(r["score"], 100.0)            # rescaled over the parts that have data, never counted as 0
        self.assertFalse([p for p in r["parts"] if p["part"] == "collaboration"][0]["available"])


class NoNumber(unittest.TestCase):
    def test_few_runs_is_insufficient(self):
        r = engine.compute(metrics(runs=19), CFG)
        self.assertEqual(r["state"], "insufficient_data")
        self.assertIsNone(r["score"])
        self.assertIsNone(r["letter"])
        self.assertEqual(r["data_quality"]["reasons"], ["few_runs"])

    def test_low_coverage_is_insufficient(self):
        r = engine.compute(metrics(p95=None, mttr=None, collab=None), CFG)
        self.assertEqual(r["state"], "insufficient_data")
        self.assertIn("low_coverage", r["data_quality"]["reasons"])

    def test_no_data_at_all_is_never_a_green_100(self):
        r = engine.compute({"samples": {}}, CFG)
        self.assertEqual(r["state"], "insufficient_data")
        self.assertIsNone(r["score"])
        self.assertEqual(r["coverage"], 0.0)

    def test_recently_watched_is_calibrating(self):
        r = engine.compute(metrics(), CFG, watched_hours=23.9)
        self.assertEqual((r["state"], r["score"]), ("calibrating", None))
        self.assertEqual(engine.compute(metrics(), CFG, watched_hours=24)["state"], "scored")

    def test_unknown_watch_time_never_calibrates(self):
        self.assertEqual(engine.compute(metrics(), CFG, watched_hours=None)["state"], "scored")


class Trend(unittest.TestCase):
    def test_direction_and_delta(self):
        self.assertEqual(engine.trend(80, 70, 2), {"direction": "up", "delta": 10.0})
        self.assertEqual(engine.trend(70, 80, 2), {"direction": "down", "delta": -10.0})
        self.assertEqual(engine.trend(70, 71.9, 2)["direction"], "flat")
        self.assertEqual(engine.trend(70, None, 2), {"direction": "unknown", "delta": None})

    def test_compute_uses_the_previous_score(self):
        self.assertEqual(engine.compute(metrics(), CFG, previous=80)["trend"], {"direction": "up", "delta": 20.0})
        self.assertEqual(engine.compute(metrics(), CFG)["trend"]["direction"], "unknown")


class Window(unittest.TestCase):
    def test_previous_window_gives_the_trend_only_when_it_was_scored(self):
        day = 86400.0
        end = 1_700_000_000.0 + 14 * day
        cfg = engine.settings({"score": {"min_runs": 5}})

        def runs(first_day, n, conclusion):
            return [{"repo": "a/x", "name": f"w{i % 3}", "status": "completed", "conclusion": conclusion, "seconds": 100, "started": end - (14 - first_day) * day + i * 60}
                    for i in range(n)]
        data = runs(7, 10, "success") + runs(0, 5, "failure") + runs(1, 5, "success")
        r = engine.score_window(data, [], end, cfg)
        self.assertEqual(r["state"], "scored")
        self.assertEqual(r["trend"]["direction"], "up")
        only_now = engine.score_window(runs(7, 10, "success"), [], end, cfg)
        self.assertEqual(only_now["trend"]["direction"], "unknown")


class Settings(unittest.TestCase):
    def test_defaults_are_the_decided_ones(self):
        self.assertEqual(CFG["weights"], {"reliability": 40, "speed": 20, "recovery": 20, "collaboration": 20})
        self.assertEqual((CFG["window_days"], CFG["calibrating_hours"], CFG["min_runs"], CFG["min_coverage"]), (7, 24, 20, 0.5))
        self.assertEqual(CFG["alert"], {"enabled": True, "drop_points": 10, "notify_external": False})

    def test_bad_values_keep_the_default(self):
        cfg = engine.settings({"score": {"window_days": 0, "min_runs": "x", "min_coverage": 2, "weights": {"reliability": -1, "speed": True},
                                         "grades": {"A": 50, "B": 60, "C": 40, "D": 30}, "limits": {"speed": {"good": 5, "bad": 5}}, "alert": {"drop_points": 0}}})
        self.assertEqual(cfg, CFG)

    def test_good_values_are_taken(self):
        cfg = engine.settings({"score": {"window_days": 30, "weights": {"reliability": 10}, "grades": {"A": 95, "B": 85, "C": 75, "D": 60}, "alert": {"notify_external": True}}})
        self.assertEqual(cfg["window_days"], 30)
        self.assertEqual(cfg["weights"]["reliability"], 10)
        self.assertEqual(cfg["grades"]["A"], 95)
        self.assertTrue(cfg["alert"]["notify_external"])

    def test_all_zero_weights_are_refused(self):
        cfg = engine.settings({"score": {"weights": {"reliability": 0, "speed": 0, "recovery": 0, "collaboration": 0}}})
        self.assertEqual(cfg["weights"], CFG["weights"])


if __name__ == "__main__":
    unittest.main()
