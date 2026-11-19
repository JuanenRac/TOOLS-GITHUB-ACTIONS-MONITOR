# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A double of GitHub with 250 and with 727 repositories (no network, deterministic): the cost of a cycle in requests, what the monitor does when GitHub answers 403 (refused, or the allowance used up),
429 (secondary limit) or 5xx for some repositories, and what a list of workflows that does not fit one page looks like. The point of these tests is that one bad answer never becomes a storm of requests
and never stops the repositories that answer; they run in the CI of the repository (the same file in the job "Evidence") because an outside auditor cannot do it."""
import time
import unittest
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.data_pipeline import paging

NOW = time.time()
CONFIG = {"mode": "full", "cold_runs_per_repo": 5, "runs_per_repo": 20, "max_workers": 8, "refresh_seconds": 45, "cold_refresh_seconds": 600, "hot_hours": 3}


def run_of(index, i):
    when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 30 * i))
    return {"id": index * 1000 + i, "name": "CI", "display_title": "t", "event": "push", "head_branch": "main", "path": ".github/workflows/ci.yml", "head_sha": "abcdef1234", "run_number": i,
            "status": "completed", "conclusion": "success", "created_at": when, "run_started_at": when, "updated_at": when, "html_url": f"https://x/{index}/{i}", "run_attempt": 1, "actor": {"login": "o"}}


class Double:
    """GitHub: every repository has runs; `faults` maps the number of a repository to the error text GitHub would answer with."""

    def __init__(self, faults=None, after=None):
        self.reads, self.faults, self.after = [], dict(faults or {}), after

    def read(self, endpoint, retries=2):
        self.reads.append(endpoint)
        index = int(endpoint.split("/repo-")[1][:3])
        if self.after is not None and len(self.reads) > self.after:      # the allowance runs out after N reads, for everybody
            raise RuntimeError("HTTP 403: API rate limit exceeded for user ID 1.")
        if index in self.faults:
            raise RuntimeError(self.faults[index])
        per = int(endpoint.split("per_page=")[1].split("&")[0])
        return {"total_count": 900, "workflow_runs": [run_of(index, i) for i in range(min(per, 20))]}


def names(count):
    return [f"repo-{i:03d}" for i in range(count)]


class Cycle(unittest.TestCase):
    def setUp(self):
        am.RUN_CACHE.clear()
        self.addCleanup(am.RUN_CACHE.clear)
        saved = dict(am.RATE_BLOCK)
        self.addCleanup(lambda: (am.RATE_BLOCK.clear(), am.RATE_BLOCK.update(saved)))
        am.RATE_BLOCK.update({"until": 0.0, "unread": 0})

    def cycle(self, double, repos):
        with mock.patch.object(am, "gh_read", double.read), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), mock.patch.object(am, "tuned", lambda c, k, d=None: c[k]), \
                mock.patch.object(am, "rate_block_start", lambda now=None: am.RATE_BLOCK.update(until=time.time() + 600) or time.time() + 600), mock.patch.object(am.time, "sleep", lambda s: None):
            return am.refresh_runs(repos, CONFIG)

    def test_the_first_cycle_reads_each_repository_once_for_250_and_for_727(self):
        for count in (250, 727):
            am.RUN_CACHE.clear()
            double = Double()
            self.cycle(double, names(count))
            self.assertEqual(len(double.reads), count, count)
            self.assertEqual(len(am.RUN_CACHE), count)
            self.assertTrue(all(not e.get("error") for e in am.RUN_CACHE.values()))

    def test_a_missing_or_failing_repository_does_not_stop_the_others_and_is_read_once(self):
        faults = {3: "HTTP 404: Not Found", 10: "HTTP 500: server error", 11: "HTTP 502: bad gateway", 20: "HTTP 404: Not Found"}
        double = Double(faults)
        self.cycle(double, names(727))
        read = [r for r in am.RUN_CACHE if am.RUN_CACHE[r].get("runs")]
        self.assertEqual(len(read), 727 - len(faults))
        self.assertEqual(len(double.reads), 727)      # one read each: no retry storm (the retries live in gh_read, which the double replaces)
        self.assertTrue(am.RUN_CACHE["repo-003"].get("error"))      # a 404 is shown at once
        self.assertGreater(am.RUN_CACHE["repo-010"]["fails"], 0)      # a 5xx is a passing failure: the repository waits for its next turn

    def test_a_refusal_of_the_credential_is_not_taken_for_a_rate_limit(self):
        double = Double({5: "HTTP 401: Bad credentials"})

        def read(endpoint, retries=2):
            try:
                return double.read(endpoint, retries)
            except RuntimeError as error:
                raise am.AuthError(str(error)) from None
        double.read_raw, double.read = double.read, read
        with self.assertRaises(am.AuthError):
            self.cycle(double, names(50))
        self.assertEqual(am.RATE_BLOCK["until"], 0.0)

    def test_the_allowance_running_out_stops_the_cycle_after_one_chunk_and_remembers_what_it_did_not_read(self):
        for count in (250, 727):
            am.RUN_CACHE.clear()
            am.RATE_BLOCK.update({"until": 0.0, "unread": 0})
            double = Double(after=60)
            self.cycle(double, names(count))
            self.assertLessEqual(len(double.reads), 60 + 40 + CONFIG["max_workers"], (count, len(double.reads)))      # the chunk in flight ends, the next one never starts
            self.assertGreater(am.RATE_BLOCK["until"], time.time())
            self.assertGreater(am.RATE_BLOCK["unread"], 0, count)
            before = len(double.reads)
            self.cycle(double, names(count))      # still blocked: nothing is asked
            self.assertEqual(len(double.reads), before)

    def test_a_secondary_limit_is_a_rate_limit_too(self):
        double = Double({0: "HTTP 403: You have exceeded a secondary rate limit. Please wait a few minutes before you try again."})
        self.cycle(double, names(250))
        self.assertGreater(am.RATE_BLOCK["until"], time.time())

    def test_a_429_with_a_retry_after_is_waited_for_in_minutes_not_in_seconds(self):
        self.assertGreaterEqual(am.secondary_wait("HTTP 429: retry-after: 60", 0), 60)
        self.assertGreaterEqual(am.secondary_wait("secondary rate limit", 1), 120)
        self.assertLessEqual(am.secondary_wait("secondary rate limit", 9, 1.0), 300 * 1.2)      # never longer than five minutes (plus the jitter)
        self.assertLess(am.secondary_wait("HTTP 500", 0), 10)


class Pages(unittest.TestCase):
    def test_a_list_of_727_items_is_followed_to_the_end_and_a_cut_is_said(self):
        items = list(range(727))

        def read(path):
            page = int(path.split("&page=")[1])
            return {"total_count": 727, "workflows": items[(page - 1) * 100: page * 100]}
        whole = paging.read_pages(read, "repos/o/r/actions/workflows", "workflows", 100, 20)
        self.assertEqual((whole["seen"], whole["total"], whole["cut"], whole["pages"]), (727, 727, False, 8))
        short = paging.read_pages(read, "repos/o/r/actions/workflows", "workflows", 100, 3)
        self.assertEqual((short["seen"], short["cut"], short["pages"]), (300, True, 3))

    def test_a_page_that_fails_in_the_middle_keeps_what_was_read_and_says_it_was_cut(self):
        def read(path):
            page = int(path.split("&page=")[1])
            if page == 4:
                raise RuntimeError("HTTP 429: secondary rate limit")
            return {"total_count": 727, "workflows": list(range(100))}
        out = paging.read_pages(read, "x", "workflows", 100, 20)
        self.assertEqual((out["seen"], out["cut"], out["pages"]), (300, True, 3))
        self.assertIn("429", out["error"])

    def test_a_first_page_that_fails_is_an_error_for_the_caller(self):
        def read(path):
            raise RuntimeError("HTTP 403: rate limit")
        with self.assertRaises(RuntimeError):
            paging.read_pages(read, "x", "workflows", 100, 5)


if __name__ == "__main__":
    unittest.main()
