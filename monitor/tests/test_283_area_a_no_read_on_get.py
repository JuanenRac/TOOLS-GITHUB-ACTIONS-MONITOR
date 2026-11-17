# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""No route that answers a GET starts `gh` or reads GitHub (the reading is done by the cycle: a page that refreshes, or somebody who asks in a loop, cannot spend the allowance), the duration of a re-run
has an allowance for each reading of each repository, and the cycle is the one that reads the runners."""
import inspect
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import sampling  # noqa: E402
from github_actions_monitor.integrations import runners  # noqa: E402
from test_200_contract import Served  # noqa: E402

ON = {"api": {"v1_enabled": True}, "runners": {"enabled": True, "scope": "repos"}, "runner_model": {"enabled": True}, "screens": {"enabled": True}, "discovery": {"events": True},
      "orgs": {"discover": True}, "updates": {"check": True}}
#: the one route that reads GitHub on purpose, because a person asked for that very log with a button (admin, off by default, limited per minute)
READS_ON_PURPOSE = ("/api/run-log",)
ROUTE_RE = re.compile(r'path (?:==|in \() ?"(/api/[A-Za-z0-9_/.-]+|/metrics)"')


def get_routes():
    source = inspect.getsource(am.Handler.handle_get) + inspect.getsource(am.Handler.do_GET)
    found = {m.group(1) for m in ROUTE_RE.finditer(source)}
    found |= {"/api/data", "/api/health", "/api/about", "/api/discovery", "/api/runners", "/api/runners/model", "/api/quota-pool/status", "/api/alerts", "/api/team/fleet", "/api/team/health",
              "/api/quota", "/api/screens/data?screen=now", "/api/v1/me", "/api/v1/repos"}
    return sorted(found - set(READS_ON_PURPOSE))


class NoGetReadsGitHub(unittest.TestCase):
    def test_every_get_route_is_answered_without_starting_gh_or_reading_github(self):
        served = Served(self, lite=False)
        for patcher in (mock.patch.object(am.toolconfig, "raw_config", return_value=ON), mock.patch.object(am, "LIVE_CONFIG", dict(am.DEFAULTS, **ON)),
                        mock.patch.dict(am.STATE, {"data": {"repos": ["r1", "r2"], "runs": [], "active": [], "failing": []}})):
            patcher.start()
            self.addCleanup(patcher.stop)
        real_popen, real_run = subprocess.Popen, subprocess.run
        started = []

        def watch(real):
            def inner(args, *more, **kwargs):
                first = args[0] if isinstance(args, (list, tuple)) and args else args
                if isinstance(first, str) and os.path.basename(first).lower() in ("gh", "gh.exe"):
                    started.append(args)
                elif "hermetic test" in str(args):      # the hermetic replacement of gh of the tests
                    started.append(args)
                return real(args, *more, **kwargs)
            return inner
        with mock.patch.object(subprocess, "Popen", watch(real_popen)), mock.patch.object(subprocess, "run", watch(real_run)), \
                mock.patch.object(am, "gh_read", side_effect=AssertionError("a GET read GitHub")) as read, mock.patch.object(am, "gh", side_effect=AssertionError("a GET started gh")) as gh:
            routes = get_routes()
            self.assertGreater(len(routes), 40, "the table of routes was found")
            for path in routes:
                try:
                    served.raw("GET", path)
                except OSError:      # a route that needs more state than this test holds may drop the connection: what counts is that it did not read
                    pass
        self.assertEqual(started, [], "no gh was started")
        self.assertEqual((read.call_count, gh.call_count), (0, 0), "nothing was read: " + str(read.call_args_list[:3] + gh.call_args_list[:3]))

    def test_twenty_requests_to_the_runners_cost_no_reading_at_all(self):
        served = Served(self, lite=False)
        for patcher in (mock.patch.object(am.toolconfig, "raw_config", return_value=ON), mock.patch.object(am, "LIVE_CONFIG", dict(am.DEFAULTS, **ON)),
                        mock.patch.object(am, "RUNNERS_SEEN", {"payload": None, "at": 0.0}), mock.patch.object(am, "POOL_STATUS", {"payload": None, "at": 0.0})):
            patcher.start()
            self.addCleanup(patcher.stop)
        with mock.patch.object(am, "gh_read", side_effect=AssertionError("read")), mock.patch.object(am, "gh", side_effect=AssertionError("gh")):
            for _ in range(20):
                status, raw, _ = served.raw("GET", "/api/runners")
                self.assertEqual(status, 200)
                self.assertIn(b"pending", raw)


class TheCycleReadsTheRunners(unittest.TestCase):
    def setUp(self):
        for target, name, value in ((am, "RUNNERS_SEEN", {"payload": None, "at": 0.0}), (am, "RUNNER_JOBS", {"rows": {}, "list": None, "list_at": 0.0}), (am, "POOL_STATUS", {"payload": None, "at": 0.0})):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_cycle_reads_once_per_five_minutes_and_the_route_and_the_model_use_what_it_read(self):
        config = dict(am.DEFAULTS, **ON)
        reads = []
        listing = {"runners": [{"id": 1, "name": "r", "state": "idle", "labels": ["self-hosted"], "os": "Linux"}], "counts": {"idle": 1, "busy": 0, "offline": 0}, "errors": 0}
        with mock.patch.object(runners, "collect", side_effect=lambda *a, **k: reads.append(1) or listing), mock.patch.object(am.toolconfig, "github_owner", return_value="o"):
            self.assertTrue(am.read_runner_list(config, {"repos": ["r1"]}))
            self.assertFalse(am.read_runner_list(config, {"repos": ["r1"]}), "not again inside five minutes")
            self.assertEqual(len(reads), 1)
            self.assertEqual(am.runner_list(config), listing["runners"])
            self.assertTrue(am.RUNNERS_SEEN["payload"]["enabled"])
            am.RUNNER_JOBS["list_at"] -= am.RUNNERS_MEMORY_SECONDS + 1
            self.assertTrue(am.read_runner_list(config, {"repos": ["r1"]}))
        self.assertEqual(len(reads), 2)

    def test_while_off_or_in_demo_nothing_is_read(self):
        with mock.patch.object(runners, "collect", side_effect=AssertionError("read")):
            self.assertFalse(am.read_runner_list(dict(am.DEFAULTS), {}))
            with mock.patch.dict(am.DEMO, {"on": True}):
                self.assertFalse(am.read_runner_list(dict(am.DEFAULTS, **ON), {}))

    def test_the_cycle_keeps_the_status_of_the_quota_for_five_minutes(self):
        with mock.patch.object(am, "pool_status", return_value={"total": 5, "sources": []}) as read:
            self.assertTrue(am.refresh_pool_status())
            self.assertFalse(am.refresh_pool_status())
            self.assertEqual(am.POOL_STATUS["payload"]["total"], 5)
            am.POOL_STATUS["at"] -= am.RUNNERS_MEMORY_SECONDS + 1
            self.assertTrue(am.refresh_pool_status())
        self.assertEqual(read.call_count, 2)


def api_run(i):
    return {"id": i, "name": "CI", "run_attempt": 2, "status": "completed", "conclusion": "success", "created_at": "2026-11-01T00:00:00Z", "run_started_at": "2026-11-01T00:00:00Z",
            "updated_at": "2026-11-01T00:05:00Z", "head_branch": "main", "path": ".github/workflows/ci.yml", "head_sha": "abcdef1234", "html_url": "u", "actor": {"login": "o"}, "event": "push", "run_number": i}


class TheDurationOfAReRunHasAnAllowanceForEachReading(unittest.TestCase):
    def test_two_readings_do_not_share_their_allowance(self):
        reads = []
        with mock.patch.object(am, "gh_read", side_effect=lambda path, **k: reads.append(path) or {"run_duration_ms": 90000}), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), \
                mock.patch.object(am, "TIMING", {"on": True, "known": {}}), mock.patch.object(am, "BUDGET", sampling.Budget()):
            first = am.parse_runs("a", {"workflow_runs": [api_run(n) for n in range(1, 8)]})
            second = am.parse_runs("b", {"workflow_runs": [api_run(n) for n in range(1, 8)]})
        self.assertEqual(len(reads), 2 * am.TIMING_PER_READ, "three for each repository, not three for both")
        self.assertEqual(len([r for r in first if r["seconds"] == 90]), am.TIMING_PER_READ)
        self.assertEqual(len([r for r in second if r["seconds"] == 90]), am.TIMING_PER_READ)


if __name__ == "__main__":
    unittest.main()
