# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The refresh loop cannot stop in silence: its heartbeat, the watchdog that restarts a cycle that hangs (with the traceback of every thread in the log), the log that fails out loud and the page that says it.
The loop runs here with false collaborators that hang, raise or fail to write."""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import cycle_watch, settings_api  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NODE = shutil.which("node")


def fake_data(stamp="2026-01-01T00:00:00Z"):
    return {"updated": stamp, "repos": ["a"], "hot": 0, "refreshed": 1, "active": [], "issues": [], "rate": {"remaining": 5000, "limit": 5000, "reset": "2026-01-01T01:00:00Z"}, "loading": "", "figures": {}}


def wait_for(condition, seconds=10.0):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.02)
    return False


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Heartbeat(unittest.TestCase):
    def test_the_phases_the_last_good_cycle_and_the_stuck_flag(self):
        clock = Clock()
        watch = cycle_watch.CycleWatch(clock)
        self.assertEqual(watch.snapshot()["phase"], "idle")
        watch.begin()
        watch.phase("maintain")
        clock.now += 30
        snap = watch.snapshot(limit_seconds=600)
        self.assertEqual((snap["phase"], snap["running_seconds"], snap["stuck"]), ("maintain", 30, False))
        clock.now += 700
        self.assertTrue(watch.snapshot(limit_seconds=600)["stuck"])
        self.assertFalse(watch.snapshot(limit_seconds=0)["stuck"], "0 switches it off")
        watch.ok()
        clock.now += 5
        snap = watch.snapshot(limit_seconds=600)
        self.assertEqual((snap["phase"], snap["running_seconds"], snap["seconds_since_ok"], snap["cycles"]), ("idle", 0, 5, 1))
        json.dumps(snap)      # it travels in /api/data

    def test_an_error_keeps_its_phase_and_the_log_problem_is_kept_until_it_writes_again(self):
        watch = cycle_watch.CycleWatch(Clock())
        watch.begin()
        watch.phase("log")
        watch.fail(OSError("disk full"))
        self.assertEqual((watch.snapshot()["last_error_phase"], "disk full" in watch.snapshot()["last_error"]), ("log", True))
        watch.log_failed(PermissionError("no"))
        self.assertIn("PermissionError", watch.snapshot()["log_error"])
        watch.log_ok()
        self.assertEqual(watch.snapshot()["log_error"], "")

    def test_the_watchdog_decides_stuck_dead_or_nothing(self):
        clock = Clock()
        watch = cycle_watch.CycleWatch(clock)
        self.assertEqual(cycle_watch.check(watch, 600, True), "")
        watch.begin()
        clock.now += 601
        self.assertEqual(cycle_watch.check(watch, 600, True), "stuck")
        self.assertEqual(cycle_watch.check(watch, 0, True), "", "limit 0: off")
        self.assertEqual(cycle_watch.check(watch, 600, False), "dead")

    def test_a_replaced_loop_knows_it(self):
        watch = cycle_watch.CycleWatch(Clock())
        first = watch.new_generation()
        self.assertTrue(watch.current(first))
        second = watch.new_generation()
        self.assertFalse(watch.current(first))
        self.assertTrue(watch.current(second))

    def test_a_call_that_never_returns_is_left_behind(self):
        release = threading.Event()
        started = time.time()
        with self.assertRaises(subprocess.TimeoutExpired):
            cycle_watch.bounded(lambda: release.wait(30), 0.2)
        self.assertLess(time.time() - started, 5)
        release.set()
        self.assertEqual(cycle_watch.bounded(lambda: 7, 5), 7)
        with self.assertRaises(ValueError):
            cycle_watch.bounded(lambda: (_ for _ in ()).throw(ValueError("x")), 5)


class LoopWithFalseCollaborators(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "log.txt"
        self.release = threading.Event()
        self.addCleanup(self.release.set)
        patches = [mock.patch.object(am, "LOG_FILE", self.log), mock.patch.object(am, "maintain", lambda config, data: None),
                   mock.patch.dict(am.STATE, {"data": None, "error": None, "hint": None}, clear=False),
                   mock.patch.object(am, "watchdog_limit", lambda config: 0.4),
                   mock.patch.object(am, "SENTINEL", {"obj": None, "registry": None, "error": None})]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        am.STATE.pop("complete", None)
        am.WATCH.reset()
        self.config = dict(am.DEFAULTS)
        self.addCleanup(lambda: am.WATCH.new_generation())      # whatever loop is still alive leaves

    def fast_sleep(self):
        real = am.sleep_for
        return mock.patch.object(am, "sleep_for", lambda seconds, generation=None: real(min(seconds, 0.05), generation))

    def test_a_cycle_that_hangs_is_dumped_to_the_log_and_restarted_and_the_old_one_leaves_quietly(self):
        calls = []

        def collect(config, publish=None):
            calls.append(threading.current_thread().name)
            if len(calls) == 1:
                self.release.wait(30)      # the first cycle hangs
                return fake_data("OLD")
            return fake_data("NEW")

        with mock.patch.object(am, "collect", collect), self.fast_sleep():
            first = am.start_loop(self.config)
            self.assertTrue(wait_for(lambda: len(calls) == 1))
            self.assertEqual(am.WATCH.snapshot()["phase"], "collect")
            self.assertEqual(am.watchdog_once(self.config), "", "not yet over the limit")
            time.sleep(0.5)
            self.assertEqual(am.WATCH.snapshot(limit_seconds=0.4)["stuck"], True)
            self.assertEqual(am.watchdog_once(self.config), "stuck")
            self.assertTrue(wait_for(lambda: (am.STATE["data"] or {}).get("updated") == "NEW"), "the new loop published")
            self.assertEqual(am.WATCH.snapshot()["restarts"], 1)
            text = self.log.read_text(encoding="utf-8")
            self.assertIn("WATCHDOG stuck phase=collect", text)
            self.assertIn("Thread", text, "the traceback of the threads is in the log")
            self.assertIn("collect", text)
            self.release.set()      # the old cycle wakes up late
            first.join(5)
            self.assertFalse(first.is_alive(), "the old loop left")
            self.assertEqual(am.STATE["data"]["updated"], "NEW", "and published nothing")

    def test_a_loop_whose_thread_died_is_started_again(self):
        with mock.patch.object(am, "collect", lambda config, publish=None: fake_data("A")), self.fast_sleep():
            am.LOOP["thread"] = None
            self.assertEqual(am.watchdog_once(self.config), "dead")
            self.assertTrue(wait_for(lambda: (am.STATE["data"] or {}).get("updated") == "A"))

    def test_an_error_in_a_phase_is_kept_and_the_loop_goes_on(self):
        calls = []

        def collect(config, publish=None):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("network gone")
            return fake_data("B")

        with mock.patch.object(am, "collect", collect), mock.patch.object(am.time, "sleep", lambda s: None):
            real = am.sleep_for
            with mock.patch.object(am, "sleep_for", lambda seconds, generation=None: real(0.01, generation)):
                am.start_loop(self.config)
                self.assertTrue(wait_for(lambda: (am.STATE["data"] or {}).get("updated") == "B"))
        self.assertTrue(wait_for(lambda: am.WATCH.snapshot()["cycles"] >= 1))
        snap = am.WATCH.snapshot()
        self.assertIn("network gone", snap["last_error"])
        self.assertEqual(snap["last_error_phase"], "collect")
        self.assertGreaterEqual(snap["cycles"], 1)

    def test_a_log_that_cannot_be_written_is_said_and_the_data_still_come_out(self):
        with mock.patch.object(am, "collect", lambda config, publish=None: fake_data("C")), mock.patch.object(am.private_io, "open_append", side_effect=PermissionError("locked")), self.fast_sleep():
            am.start_loop(self.config)
            self.assertTrue(wait_for(lambda: (am.STATE["data"] or {}).get("updated") == "C"))
            self.assertTrue(wait_for(lambda: am.WATCH.snapshot()["cycles"] >= 1))
        self.assertIn("PermissionError", am.WATCH.snapshot()["log_error"])

    def test_a_phase_that_hangs_after_the_data_came_out_is_found_too(self):
        def maintain(config, data):
            self.release.wait(30)

        with mock.patch.object(am, "collect", lambda config, publish=None: fake_data("D")), mock.patch.object(am, "maintain", maintain), self.fast_sleep():
            am.start_loop(self.config)
            self.assertTrue(wait_for(lambda: am.WATCH.snapshot()["phase"] == "maintain"))
            time.sleep(0.5)
            self.assertEqual(am.watchdog_once(self.config), "stuck")
            self.assertEqual(am.WATCH.snapshot()["last_error_phase"], "maintain")


class Wiring(unittest.TestCase):
    def test_the_answer_of_the_server_carries_the_heartbeat_and_the_gh_calls_are_bounded(self):
        source = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('"loop": WATCH.snapshot(', source)
        self.assertGreaterEqual(source.count("cycle_watch.bounded("), 2)
        self.assertIn("watchdog_loop", source)

    def test_the_setting_exists_with_its_texts_in_the_eight_languages(self):
        self.assertIn("watchdog_minutes", settings_api.FIELDS)
        self.assertEqual(am.DEFAULTS["watchdog_minutes"], 10)
        for lang in i18n.LANGS:
            for key in ("cfg.f.watchdog_minutes", "cfg.h.watchdog_minutes", "ui.loop_stuck", "ui.loop_stuck_t", "ui.loop_logfail", "ui.loop_phase_collect", "ui.loop_phase_idle"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        for key in ("ui.loop_stuck", "ui.loop_logfail"):
            self.assertIn(key, PAGE)

    @unittest.skipUnless(NODE, "no node on this computer")
    def test_the_page_calls_a_stuck_monitor_stuck(self):
        start = PAGE.index("function loopBad(")
        end = PAGE.index("function freshFail(")
        code = PAGE[start:end] + ("console.log(JSON.stringify([loopBad(null,20),loopBad({stuck:true,running_seconds:1},20),loopBad({running_seconds:100},20),"
                                  "loopBad({running_seconds:601},20),loopBad({running_seconds:601},300)]))")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "t.js"
            path.write_text(code, encoding="utf-8")
            out = subprocess.run([NODE, str(path)], capture_output=True, text=True, timeout=60, check=True)
        self.assertEqual(json.loads(out.stdout), [False, True, False, True, False])


if __name__ == "__main__":
    unittest.main()
