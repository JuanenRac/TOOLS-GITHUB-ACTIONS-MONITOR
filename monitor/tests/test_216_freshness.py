# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Fresh, stale and expired answers of the heavy queries and their time ceiling (`cache.heavy_fresh_s`, `cache.stale_serve_h`, `analytics.query_timeout_s`)."""
import sys
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import freshness  # noqa: E402

CFG = {"fresh_s": 10, "stale_serve_h": 1, "query_timeout_s": 5}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def wait_until(check, seconds=5.0):
    end = time.time() + seconds
    while time.time() < end:
        if check():
            return True
        time.sleep(0.01)
    return False


class Base(unittest.TestCase):
    def setUp(self):
        freshness.clear()
        self.addCleanup(freshness.clear)
        self.clock = Clock()
        self.calls = []

    def build(self, value="v", delay=0.0, boom=None):
        def run():
            self.calls.append(self.clock())
            if delay:
                time.sleep(delay)
            if boom:
                raise boom
            return {"value": value, "n": len(self.calls)}
        return run


class TheSettings(unittest.TestCase):
    def test_defaults_and_nonsense(self):
        self.assertEqual(freshness.settings({}), {"fresh_s": 5, "stale_serve_h": 1, "query_timeout_s": 120})
        got = freshness.settings({"cache": {"heavy_fresh_s": 30, "stale_serve_h": 4}, "analytics": {"query_timeout_s": 60}})
        self.assertEqual(got, {"fresh_s": 30, "stale_serve_h": 4, "query_timeout_s": 60})
        for bad in (-1, 3601, "9", True, None, 2.5):
            self.assertEqual(freshness.settings({"cache": {"heavy_fresh_s": bad, "stale_serve_h": bad}, "analytics": {"query_timeout_s": bad}}), freshness.DEFAULTS, bad)
        self.assertEqual(freshness.settings({"analytics": {"query_timeout_s": 4}})["query_timeout_s"], 120)
        self.assertEqual(freshness.settings({"cache": {"stale_serve_h": 0}})["stale_serve_h"], 0)

    def test_the_three_states_by_age(self):
        self.assertEqual([freshness.state_of(a, CFG) for a in (0, 10, 11, 3610, 3611, 99999)], ["fresh", "fresh", "stale", "stale", "expired", "expired"])
        self.assertEqual(freshness.state_of(1, {"fresh_s": 0, "stale_serve_h": 0, "query_timeout_s": 5}), "expired")


class TheStates(Base):
    def test_the_first_request_computes_and_the_next_one_is_served_without_computing(self):
        state, value, age = freshness.serve("k", self.build(), CFG, self.clock)
        self.assertEqual((state, value["n"], age), ("fresh", 1, 0.0))
        self.clock.now += 5
        state, value, age = freshness.serve("k", self.build(), CFG, self.clock)
        self.assertEqual((state, value["n"], age), ("fresh", 1, 5.0))
        self.assertEqual(len(self.calls), 1)

    def test_a_stale_copy_is_served_at_once_and_refreshed_in_the_background(self):
        freshness.serve("k", self.build(), CFG, self.clock)
        self.clock.now += 60
        gate = threading.Event()

        def slow():
            self.calls.append(self.clock())
            gate.wait(5)
            return {"value": "new", "n": len(self.calls)}
        started = time.time()
        state, value, age = freshness.serve("k", slow, CFG, self.clock)
        self.assertEqual((state, value["n"], age), ("stale", 1, 60.0))
        self.assertLess(time.time() - started, 1.0, "nobody waits for the refresh")
        self.assertEqual(freshness.mark(value, state, age)["freshness"], {"state": "stale", "age_s": 60})
        again = freshness.serve("k", slow, CFG, self.clock)
        self.assertEqual(again[0], "stale")
        self.assertTrue(wait_until(lambda: len(self.calls) == 2))
        self.assertEqual(len(self.calls), 2, "only one refresh runs at a time")
        gate.set()
        self.assertTrue(wait_until(lambda: freshness.serve("k", self.build(), CFG, self.clock)[0] == "fresh"))
        state, value, _ = freshness.serve("k", self.build(), CFG, self.clock)
        self.assertEqual(value["value"], "new")

    def test_an_expired_copy_is_never_served_it_is_computed_now(self):
        freshness.serve("k", self.build("old"), CFG, self.clock)
        self.clock.now += 3 * 3600
        state, value, age = freshness.serve("k", self.build("new"), CFG, self.clock)
        self.assertEqual((state, value["value"], age), ("fresh", "new", 0.0))

    def test_no_stale_window_means_no_stale_copy(self):
        cfg = {**CFG, "stale_serve_h": 0}
        freshness.serve("k", self.build("old"), cfg, self.clock)
        self.clock.now += 11
        state, value, _ = freshness.serve("k", self.build("new"), cfg, self.clock)
        self.assertEqual((state, value["value"]), ("fresh", "new"))

    def test_a_fresh_answer_is_left_exactly_as_it_is(self):
        answer = {"a": 1}
        self.assertIs(freshness.mark(answer, "fresh", 3), answer)
        self.assertEqual(freshness.mark(answer, "stale", 3)["a"], 1)
        self.assertNotIn("freshness", answer)
        self.assertEqual(freshness.mark([1], "stale", 3), [1])


class TheCeiling(Base):
    def test_a_query_that_takes_longer_than_the_ceiling_is_a_timeout_and_its_answer_is_kept(self):
        cfg = {**CFG, "query_timeout_s": 0.2}
        started = time.time()
        state, value, _ = freshness.serve("k", self.build(delay=0.6), cfg, self.clock)
        self.assertEqual((state, value), ("timeout", None))
        self.assertLess(time.time() - started, 0.5)
        self.assertTrue(wait_until(lambda: freshness.serve("k", self.build(), cfg, self.clock)[0] == "fresh"), "the late answer is there for the next request")
        self.assertEqual(len(self.calls), 1, "and the query was not started a second time")

    def test_while_a_query_runs_no_second_one_is_started_for_the_same_key(self):
        cfg = {**CFG, "query_timeout_s": 0.1}
        gate = threading.Event()

        def hang():
            self.calls.append(1)
            gate.wait(5)
            return {"n": 1}
        results = [freshness.serve("k", hang, cfg, self.clock)[0] for _ in range(4)]
        self.assertEqual(results, ["timeout"] * 4)
        self.assertEqual(len(self.calls), 1, "a slow query does not pile up")
        gate.set()
        self.assertTrue(wait_until(lambda: freshness.serve("k", hang, cfg, self.clock)[0] == "fresh"))

    def test_a_failure_is_given_back_and_never_kept_as_an_answer(self):
        state, value, _ = freshness.serve("k", self.build(boom=ValueError("bad window")), CFG, self.clock)
        self.assertEqual(state, "error")
        self.assertIsInstance(value, ValueError)
        state, value, _ = freshness.serve("k", self.build("ok"), CFG, self.clock)
        self.assertEqual((state, value["value"]), ("fresh", "ok"))
        self.assertEqual(len(self.calls), 2)

    def test_different_keys_do_not_share_an_answer(self):
        freshness.serve(("c", "a"), self.build("A"), CFG, self.clock)
        state, value, _ = freshness.serve(("c", "b"), self.build("B"), CFG, self.clock)
        self.assertEqual(value["value"], "B")


class TheRoute(unittest.TestCase):
    def test_the_compare_and_reports_routes_go_through_the_cache_and_the_ceiling(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertEqual(text.count("freshness.serve("), 2)
        self.assertIn('"code": "query_timeout"', text)
        self.assertEqual(text.count('"code": "query_timeout"'), 2)


if __name__ == "__main__":
    unittest.main()
