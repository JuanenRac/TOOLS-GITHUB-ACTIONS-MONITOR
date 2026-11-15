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


def metrics(rate=0.98, p95=600, mttr=1800, collab=172800, runs=100, recoveries=5, closed=5, penalty=0, repos=5):
    out = {"success_rate": rate, "duration_p95": p95, "mttr": mttr, "collab_resolution_time": collab,
           "samples": {"runs": runs, "durations": runs, "recoveries": recoveries, "collab_closed": closed}}
    if penalty is not None:
        out["security_penalty"] = penalty
        out["samples"]["security_repos"] = repos
    return out


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
        self.assertEqual(r["score"], 55.0)         # reliability 100 (30) and security 100 (25) of 100
        self.assertEqual(r["letter"], "D")

    def test_letters_follow_the_cuts(self):
        g = CFG["grades"]
        self.assertEqual([engine.letter(s, g) for s in (95, 90, 89.9, 80, 70, 55, 54.9, 0)], ["A", "A", "B", "B", "C", "D", "E", "E"])

    def test_the_answer_always_carries_coverage_quality_and_the_missing_security(self):
        r = engine.compute(metrics(penalty=None), CFG)
        self.assertEqual(r["coverage"], 0.75)
        self.assertEqual(r["missing_parts"], ["security"])
        self.assertFalse(r["complete"])
        self.assertEqual(r["data_quality"]["runs"], 100)
        self.assertEqual({p["part"] for p in r["parts"]}, set(engine.PARTS))

    def test_a_part_without_data_is_left_out_and_lowers_coverage(self):
        r = engine.compute(metrics(collab=None, closed=0), CFG)
        self.assertEqual(r["state"], "scored")
        self.assertEqual(r["coverage"], 0.85)
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
        r = engine.compute(metrics(p95=None, mttr=None, collab=None, penalty=None), CFG)
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
        self.assertEqual(CFG["weights"], {"reliability": 30, "speed": 15, "recovery": 15, "collaboration": 15, "security": 25})
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
        cfg = engine.settings({"score": {"weights": {"reliability": 0, "speed": 0, "recovery": 0, "collaboration": 0, "security": 0}}})
        self.assertEqual(cfg["weights"], CFG["weights"])


class Security(unittest.TestCase):
    def test_no_findings_is_a_full_part_and_the_answer_is_complete(self):
        r = engine.compute(metrics(penalty=0), CFG)
        part = [p for p in r["parts"] if p["part"] == "security"][0]
        self.assertEqual((part["score"], part["available"], part["weight"]), (100.0, True, 25))
        self.assertEqual((r["missing_parts"], r["complete"], r["coverage"]), ([], True, 1.0))

    def test_the_penalty_takes_points_off_one_to_one_and_stops_at_zero(self):
        for penalty, expected in ((0, 100.0), (30, 70.0), (100, 0.0), (400, 0.0)):
            part = [p for p in engine.compute(metrics(penalty=penalty), CFG)["parts"] if p["part"] == "security"][0]
            self.assertEqual(part["score"], expected, penalty)

    def test_open_findings_lower_the_number_by_the_weight_of_the_part(self):
        clean = engine.compute(metrics(penalty=0), CFG)["score"]
        dirty = engine.compute(metrics(penalty=100), CFG)["score"]
        self.assertEqual((clean, dirty), (100.0, 75.0))

    def test_without_the_sentinel_the_part_is_left_out_and_said(self):
        r = engine.compute(metrics(penalty=None), CFG)
        part = [p for p in r["parts"] if p["part"] == "security"][0]
        self.assertEqual((part["score"], part["available"]), (None, False))
        self.assertEqual(r["score"], 100.0)           # rescaled over the four parts that have data

    def test_the_weight_is_a_setting_and_zero_takes_the_part_out_of_the_sum(self):
        cfg = engine.settings({"score": {"weights": {"security": 0}}})
        self.assertEqual(engine.compute(metrics(penalty=100), cfg)["score"], 100.0)

    def test_the_security_figures_are_the_same_in_both_windows(self):
        cfg = engine.settings({"score": {"min_runs": 5}})
        day = 86400.0
        end = 1_700_000_000.0 + 14 * day
        runs = [{"repo": "a/x", "name": f"w{i % 3}", "status": "completed", "conclusion": "success", "seconds": 100, "started": end - 12 * day + i * 600} for i in range(40)]
        runs += [{"repo": "a/x", "name": f"w{i % 3}", "status": "completed", "conclusion": "success", "seconds": 100, "started": end - 5 * day + i * 600} for i in range(40)]
        r = engine.score_window(runs, [], end, cfg, security={"penalty": 40, "repos": 3})
        self.assertEqual(r["trend"]["direction"], "flat")
        self.assertEqual([p["value"] for p in r["parts"] if p["part"] == "security"], [40.0])
        self.assertEqual(engine.with_security({"samples": {}}, {"penalty": "x", "repos": 2}), {"samples": {}})
        self.assertEqual(engine.with_security({"samples": {}}, {"penalty": 3, "repos": 0}), {"samples": {}})

    def test_a_window_with_runs_and_no_failure_has_nothing_to_recover_and_that_is_data(self):
        cfg = engine.settings({"score": {"min_runs": 5}})
        end = 1_700_000_000.0 + 14 * 86400.0
        runs = [{"repo": "a/x", "name": "ci", "status": "completed", "conclusion": "success", "seconds": 100, "started": end - 3 * 86400.0 + i * 60} for i in range(30)]
        r = engine.score_window(runs, [], end, cfg)
        parts = {p["part"]: p for p in r["parts"]}
        self.assertEqual((parts["recovery"]["value"], parts["recovery"]["score"]), (0.0, 100.0))
        self.assertEqual(r["state"], "scored")
        self.assertEqual(r["coverage"], 0.6)


if __name__ == "__main__":
    unittest.main()
