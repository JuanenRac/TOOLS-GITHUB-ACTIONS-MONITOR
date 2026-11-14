# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Three robustness holes that an outside review found, closed and kept closed.

1. The cooldown of the hook of an AI tool is reserved in one step: two events at the same moment cannot both pass, and a moment that cannot be kept is not an "ok".
2. The exporter of a runner may redirect only to a private address with the same scheme, at most three times; nothing else is followed.
3. The calls that gave up waiting but never returned are counted; with too many of them alive nothing new is started and the health check says the monitor is degraded.
"""
import http.server
import json
import os
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
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import cycle_watch  # noqa: E402
from github_actions_monitor.integrations import ai_hook, runners  # noqa: E402

NOW = 1_800_000_000


class HookCooldown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_the_second_call_inside_the_interval_is_refused_and_the_moment_is_kept(self):
        self.assertTrue(ai_hook.cooldown_ok(self.folder, 20, NOW))
        self.assertFalse(ai_hook.cooldown_ok(self.folder, 20, NOW + 60))
        self.assertTrue(ai_hook.cooldown_ok(self.folder, 20, NOW + 21 * 60))
        self.assertEqual(json.loads((self.folder / "ai_hook_state.json").read_text(encoding="utf-8")), {"last_block": NOW + 21 * 60})
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["ai_hook_state.json"], "no lock or temporary file is left")

    def test_events_at_the_same_moment_let_exactly_one_through(self):
        gate, answers = threading.Barrier(10), []

        def one():
            gate.wait(10)
            answers.append(ai_hook.cooldown_ok(self.folder, 20, NOW))
        threads = [threading.Thread(target=one) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        self.assertEqual(answers.count(True), 1)

    def test_two_processes_at_the_same_moment_let_exactly_one_through(self):
        script = ("import sys, time\nsys.path.insert(0, sys.argv[1])\nfrom pathlib import Path\nfrom github_actions_monitor.integrations import ai_hook\n"
                  "while time.time() < float(sys.argv[3]):\n    pass\nprint(ai_hook.cooldown_ok(Path(sys.argv[2]), 20, 1800000000))\n")
        start = str(time.time() + 3)
        procs = [subprocess.Popen([sys.executable, "-I", "-c", script, str(HERE / "src"), str(self.folder), start], stdout=subprocess.PIPE, text=True) for _ in range(4)]
        answers = [p.communicate(timeout=60)[0].strip() for p in procs]
        self.assertEqual(sorted(answers), ["False", "False", "False", "True"])

    def test_a_moment_that_cannot_be_kept_is_not_an_ok(self):
        with mock.patch.object(ai_hook, "private_write", side_effect=PermissionError("denied")):
            self.assertFalse(ai_hook.cooldown_ok(self.folder, 20, NOW))
        self.assertFalse((self.folder / "ai_hook_state.json").exists())
        self.assertEqual(list(self.folder.iterdir()), [], "the lock does not stay behind")
        self.assertTrue(ai_hook.cooldown_ok(self.folder, 20, NOW + 1), "and the next try is not blocked by the failure")

    def test_without_the_lock_nothing_is_blocked_and_a_dead_lock_is_taken_over(self):
        (self.folder / "ai_hook_state.json.lock").write_text("1", encoding="utf-8")
        with mock.patch.object(ai_hook, "LOCK_WAIT", 0.1):
            self.assertFalse(ai_hook.cooldown_ok(self.folder, 20, NOW), "a lock held by somebody else for the whole wait")
        old = time.time() - 60
        os.utime(self.folder / "ai_hook_state.json.lock", (old, old))
        self.assertTrue(ai_hook.cooldown_ok(self.folder, 20, NOW), "a lock left by a process that died is taken over")

    def test_a_corrupt_state_file_counts_as_never_blocked(self):
        (self.folder / "ai_hook_state.json").write_text("{not json", encoding="utf-8")
        self.assertTrue(ai_hook.cooldown_ok(self.folder, 20, NOW))


class Exporter(unittest.TestCase):
    METRICS = 'node_load1 0.5\nnode_filesystem_size_bytes{mountpoint="/"} 1000\nnode_filesystem_avail_bytes{mountpoint="/"} 250\n'

    @classmethod
    def setUpClass(cls):
        cls.hits = []
        test = cls

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                test.hits.append(self.path)
                routes = {"/metrics": (200, None), "/hop1": (302, "/hop2"), "/hop2": (302, "/hop3"), "/hop3": (302, "/metrics"), "/hop4": (302, "/hop1"),
                          "/loop": (302, "/loop"), "/public": (302, "http://93.184.216.34/metrics"), "/other": (302, "ftp://127.0.0.1/metrics"),
                          "/creds": (302, "http://user:pass@127.0.0.1/metrics"), "/https": (302, "https://127.0.0.1/metrics"), "/relative": (302, "metrics")}
                code, where = routes.get(self.path, (404, None))
                self.send_response(code)
                if where:
                    self.send_header("Location", where)
                body = test.METRICS.encode() if code == 200 else b""
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def read(self, path):
        del self.hits[:]
        return runners.read_metrics(self.base + path)

    def test_a_plain_exporter_and_a_few_private_redirects_work(self):
        self.assertEqual(self.read("/metrics"), {"load1": 0.5, "disk_free_percent": 25.0})
        self.assertEqual(self.read("/hop1"), {"load1": 0.5, "disk_free_percent": 25.0}, "three hops are allowed")
        self.assertEqual(self.hits, ["/hop1", "/hop2", "/hop3", "/metrics"])

    def test_more_than_three_redirects_and_a_loop_end_with_no_figures(self):
        self.assertEqual(self.read("/hop4"), {})
        self.assertLessEqual(len(self.hits), 5)
        self.assertEqual(self.read("/loop"), {})
        self.assertLessEqual(len(self.hits), 5)

    def test_a_redirect_to_a_public_host_another_scheme_or_credentials_is_not_followed(self):
        for path in ("/public", "/other", "/creds", "/https"):
            self.assertEqual(self.read(path), {}, path)
            self.assertEqual(self.hits, [path], "nothing else was requested after the first answer")

    def test_a_redirect_judged_by_the_same_rule_as_the_configuration(self):
        handler = runners.PrivateRedirects()
        request = mock.Mock(full_url="http://127.0.0.1:9100/metrics")
        for target in ("http://93.184.216.34/x", "https://127.0.0.1/x", "http://u:p@127.0.0.1/x", "http://169.254.169.254/latest", "http://example.org/x"):
            with self.assertRaises(runners.urllib.error.URLError, msg=target):
                handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_the_answer_is_cut_at_the_limit_and_an_address_outside_the_rule_is_not_opened(self):
        self.assertEqual(runners.read_metrics("http://93.184.216.34/metrics"), {})
        self.assertEqual(runners.MAX_BYTES, 500_000)
        self.assertEqual(runners.read_metrics("http://127.0.0.1:1/metrics"), {}, "nobody listens: no figures, no error")

    def test_a_reader_given_by_the_caller_is_still_used(self):
        self.assertEqual(runners.read_metrics("http://anything", opener=lambda u: self.METRICS), {"load1": 0.5, "disk_free_percent": 25.0})


class AbandonedCalls(unittest.TestCase):
    def setUp(self):
        self.release = threading.Event()
        self.addCleanup(self.release.set)
        self.addCleanup(lambda: cycle_watch.ABANDONED.clear())
        cycle_watch.ABANDONED.clear()

    def hang(self):
        self.release.wait(30)

    def test_every_call_that_never_returns_is_counted_until_it_ends(self):
        for _ in range(3):
            with self.assertRaises(subprocess.TimeoutExpired):
                cycle_watch.bounded(self.hang, 0.05, 8)
        self.assertEqual(cycle_watch.abandoned(), 3)
        self.release.set()
        for _ in range(100):
            if cycle_watch.abandoned() == 0:
                break
            time.sleep(0.02)
        self.assertEqual(cycle_watch.abandoned(), 0, "the ones that ended are forgotten")

    def test_at_the_limit_nothing_new_is_started(self):
        for _ in range(2):
            with self.assertRaises(subprocess.TimeoutExpired):
                cycle_watch.bounded(self.hang, 0.05, 2)
        ran = []
        with self.assertRaises(cycle_watch.TooManyAbandoned):
            cycle_watch.bounded(lambda: ran.append(1), 1, 2)
        self.assertEqual(ran, [], "the call was not even started")
        self.assertTrue(cycle_watch.blocked(2) and not cycle_watch.blocked(3) and not cycle_watch.blocked(0), "0 switches the limit off")
        self.assertEqual(cycle_watch.bounded(lambda: 7, 1, 0), 7)
        self.release.set()
        for _ in range(100):
            if not cycle_watch.blocked(2):
                break
            time.sleep(0.02)
        self.assertEqual(cycle_watch.bounded(lambda: 8, 1, 2), 8, "once they end, calls go again")

    def test_a_too_many_abandoned_is_a_timeout_for_the_callers_that_catch_it(self):
        self.assertTrue(issubclass(cycle_watch.TooManyAbandoned, subprocess.TimeoutExpired))

    def test_the_monitor_degrades_and_says_so_without_restarting_the_loop(self):
        with mock.patch.dict(am.LIVE_CONFIG, {"watchdog_max_abandoned": 2}):
            self.assertEqual(am.abandoned_limit(None), 2)
            for _ in range(2):
                with self.assertRaises(subprocess.TimeoutExpired):
                    cycle_watch.bounded(self.hang, 0.05, 2)
            alive = mock.Mock(is_alive=lambda: True)
            with mock.patch.dict(am.LOOP, {"thread": alive}), mock.patch.object(am, "watchdog_restart") as restart:
                self.assertEqual(am.cycle_verdict(), "blocked")
                self.assertEqual(am.watchdog_once(am.DEFAULTS), "", "restarting the loop would not free those calls")
                restart.assert_not_called()
                payload = am.health_payload(deep=True)
            self.assertEqual((payload["ok"], payload["cycle"]["blocked"], payload["cycle"]["abandoned_calls"]), (False, True, 2))
            self.assertEqual(am.run_gh(["version"], 1)[2], "timeout", "a call to gh answers with a timeout at once")

    def test_the_limit_is_a_setting_with_a_conservative_default(self):
        self.assertEqual(am.DEFAULTS["watchdog_max_abandoned"], 8)
        with mock.patch.dict(am.LIVE_CONFIG, {"watchdog_max_abandoned": "x"}):
            self.assertEqual(am.abandoned_limit(None), cycle_watch.DEFAULT_MAX_ABANDONED)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["watchdog_max_abandoned"], 8)


if __name__ == "__main__":
    unittest.main()
