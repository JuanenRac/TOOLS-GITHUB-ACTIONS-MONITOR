# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`watch`: the loop with a false clock and a false monitor. It respects the minimum interval, backs off when the monitor cannot be read, ends with 0 on Ctrl-C, makes one read with --once and
answers 6 for a change only when --exit-on-change is given."""
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
from github_actions_monitor.cli import watch  # noqa: E402


class Down(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code, self.text = code, text


def alerts(*codes):
    return {"alerts": [{"sentinel": "ci", "level": "error", "code": c, "repo": "a/x"} for c in codes]}


class Loop(unittest.TestCase):
    def play(self, steps, **kwargs):
        """Runs the loop over scripted reads; each step is a payload or an exception. Returns (code, shown, pauses, errors, reads)."""
        shown, pauses, errors, reads = [], [], [], []
        queue = list(steps)

        def read():
            reads.append(1)
            step = queue.pop(0)
            if isinstance(step, Exception):
                raise step
            return step, ["line"], 0
        code = watch.run(kwargs.pop("command", "alerts"), read, lambda p, l, c: shown.append(p), kwargs.pop("interval", 5), sleep=pauses.append, error=errors.append, max_cycles=len(steps), **kwargs)
        return code, shown, pauses, errors, reads

    def test_once_is_a_single_read_and_no_pause(self):
        code, shown, pauses, _, reads = self.play([alerts("a")], once=True)
        self.assertEqual((code, len(shown), pauses, len(reads)), (0, 1, [], 1))

    def test_one_read_per_interval(self):
        _, shown, pauses, _, reads = self.play([alerts("a")] * 3)
        self.assertEqual((len(reads), pauses), (3, [5, 5]))

    def test_the_interval_never_goes_below_the_floor_of_the_settings(self):
        self.assertEqual(watch.interval_for(0.5, {}), 2)
        self.assertEqual(watch.interval_for(1, {"cli": {"watch": {"min_interval_seconds": 10}}}), 10)
        self.assertEqual(watch.interval_for(None, {}), 5)
        self.assertEqual(watch.interval_for(None, {"cli": {"watch": {"min_interval_seconds": 30, "default_interval_seconds": 5}}}), 30)
        self.assertEqual(watch.interval_for(99999, {}), 3600)
        self.assertEqual(watch.limits({"cli": {"watch": {"min_interval_seconds": 0, "default_interval_seconds": True}}}), (2, 5))

    def test_backoff_grows_and_is_capped(self):
        self.assertEqual([watch.backoff(5, n) for n in (1, 2, 3, 4, 5)], [10, 20, 40, 60, 60])
        self.assertEqual(watch.backoff(90, 1), 90)      # never shorter than the interval asked for

    def test_a_monitor_that_is_down_is_retried_with_a_longer_pause_and_recovers(self):
        code, shown, pauses, errors, _ = self.play([Down(2, "x"), Down(3, "y"), Down(4, "z"), alerts("a")])
        self.assertEqual((pauses, errors, len(shown)), ([10, 20, 40], ["x", "y", "z"], 1))
        self.assertEqual(code, 0)

    def test_ctrl_c_ends_with_zero(self):
        def read():
            raise KeyboardInterrupt
        self.assertEqual(watch.run("alerts", read, lambda *a: None, 5, sleep=lambda s: None), 0)

    def test_a_change_ends_with_six_only_when_the_flag_is_given(self):
        code, shown, _, _, _ = self.play([alerts("a"), alerts("a"), alerts("a", "b"), alerts("a")], exit_on_change=True)
        self.assertEqual((code, len(shown)), (6, 3))
        code, shown, _, _, _ = self.play([alerts("a"), alerts("a", "b"), alerts("c")])
        self.assertEqual((code, len(shown)), (0, 3))

    def test_a_clock_that_ticks_is_not_a_change(self):
        a = {"repos": 3, "active": 1, "queued": 0, "failures_24h": 0, "red_workflows": 0, "uptime_seconds": 10, "updated": "t1"}
        b = dict(a, uptime_seconds=99, updated="t2")
        self.assertEqual(watch.signature("status", a), watch.signature("status", b))
        self.assertNotEqual(watch.signature("status", a), watch.signature("status", dict(a, red_workflows=1)))

    def test_clear_is_called_before_each_result_only_when_given(self):
        cleared = []
        self.play([alerts("a")] * 2, clear=lambda: cleared.append(1))
        self.assertEqual(len(cleared), 2)

    def test_once_returns_the_error_code_of_the_read(self):
        code, _, _, errors, _ = self.play([Down(2, "nobody")], once=True)
        self.assertEqual((code, errors), (2, ["nobody"]))

    def test_an_unexpected_exception_is_not_swallowed(self):
        with self.assertRaises(RuntimeError):
            self.play([RuntimeError("bug")])


class Command(unittest.TestCase):
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
        base.ANSWERS["/api/alerts"] = alerts("ci.red")

    def test_watch_alerts_once_prints_once_and_asks_the_monitor_once(self):
        code, out, _ = base.run("watch", "alerts", "--once", "--format", "ndjson", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertEqual(len([s for s in base.SEEN if s.startswith("/api/alerts")]), 1)

    def test_watch_needs_a_command_to_watch(self):
        code, _, err = base.run("watch", "--once", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 1)
        self.assertTrue(err.strip())

    def test_watch_once_on_a_monitor_that_is_down_is_exit_two(self):
        code, _, err = base.run("watch", "status", "--once", "--url", "http://127.0.0.1:1", "--lang", "en")
        self.assertEqual(code, 2)
        self.assertTrue(err.strip())

    def test_watch_is_not_in_the_lite_edition(self):
        code, _, _ = base.run("watch", "status", "--once", "--lite", "--lang", "en")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
