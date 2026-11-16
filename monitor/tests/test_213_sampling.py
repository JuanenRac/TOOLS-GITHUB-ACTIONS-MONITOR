# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Sampling and coverage (no network): what a list of runs covers in time, the total that GitHub stops counting, the second look at the default branch, the budget of requests
with its ordered degraded mode, and A2 settled for many workflows with one request."""
import tempfile
import time
import unittest
from unittest import mock

import _testenv  # noqa: F401
import test_a2_resolve as base
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.data_pipeline import redrule, sampling
from github_actions_monitor.sentinels import sentinel_local as sl

NOW = 1_800_000_000.0


def stamp(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - offset))


def runs(count, step=60):
    return [{"repo": "R", "id": i, "started": stamp(i * step), "branch": "main", "path": "ci.yml", "status": "completed", "conclusion": "success"} for i in range(count)]


class Coverage(unittest.TestCase):
    def test_a_full_list_that_reaches_back_a_few_minutes_is_low_coverage(self):
        cov = sampling.coverage(runs(20, 30), 20, 700, 30, now=NOW)
        self.assertEqual((cov["complete"], cov["low"], cov["window_seconds"]), (False, True, 570))

    def test_a_full_list_that_reaches_back_a_long_time_is_not_low(self):
        cov = sampling.coverage(runs(20, 3600), 20, 20, 30, now=NOW)
        self.assertFalse(cov["low"])

    def test_a_short_list_is_the_whole_history_and_is_never_low(self):
        cov = sampling.coverage(runs(7, 30), 20, 7, 30, now=NOW)
        self.assertEqual((cov["complete"], cov["low"], cov["window_seconds"]), (True, False, None))

    def test_the_mark_can_be_turned_off(self):
        self.assertFalse(sampling.coverage(runs(20, 30), 20, None, 0, now=NOW)["low"])

    def test_the_counts_where_github_stops_are_at_least(self):
        self.assertTrue(sampling.coverage(runs(3), 20, 2500)["at_least"])
        self.assertTrue(sampling.coverage(runs(3), 20, 40000)["at_least"])
        self.assertFalse(sampling.coverage(runs(3), 20, 2499)["at_least"])

    def test_the_runs_of_the_second_look_do_not_make_a_list_full_for_the_sentinel(self):
        merged, added = sampling.merge_probe(runs(5), [dict(r, id=100 + r["id"]) for r in runs(3)] + runs(2))
        self.assertEqual((len(merged), added), (8, 3))
        self.assertEqual(sl.a2_full_sample({"R": merged}, {"runs_per_repo": 5}), ["R"])
        self.assertEqual(sl.a2_full_sample({"R": merged}, {"runs_per_repo": 8}), [])

    def test_the_settings_keep_safe_defaults_and_ignore_nonsense(self):
        self.assertEqual(sampling.settings({}), {"default_branch_probe": False, "min_coverage_minutes": 30, "api_budget_per_hour": 0})
        self.assertEqual(sampling.settings({"sampling": {"default_branch_probe": "yes", "min_coverage_minutes": -3, "api_budget_per_hour": True}}),
                         {"default_branch_probe": False, "min_coverage_minutes": 30, "api_budget_per_hour": 0})


class Budget(unittest.TestCase):
    def test_without_a_budget_everything_is_read(self):
        todo = [("a", 5), ("b", 5)]
        self.assertEqual(sampling.plan(todo, {"b"}, 0, 99999), (todo, []))

    def test_a_spent_budget_reads_the_red_first_and_keeps_a_tenth_for_them(self):
        todo = [(f"r{i}", 5) for i in range(30)]
        kept, dropped = sampling.plan(todo, {"r29", "r28"}, 100, 100)
        self.assertEqual([k[0] for k in kept], ["r28", "r29"])
        self.assertEqual(len(dropped), 28)

    def test_what_is_left_of_the_budget_goes_to_red_then_to_the_others_in_order(self):
        todo = [(f"r{i}", 5) for i in range(10)]
        kept, dropped = sampling.plan(todo, {"r9"}, 100, 97)
        self.assertEqual([k[0] for k in kept], ["r9", "r0", "r1"])
        self.assertEqual(len(dropped), 7)

    def test_the_counter_forgets_what_is_older_than_an_hour(self):
        budget = sampling.Budget()
        budget.record(5, now=NOW - 4000)
        budget.record(3, now=NOW - 10)
        self.assertEqual(budget.used(NOW), 3)

    def test_the_estimate_grows_with_the_repositories_and_with_the_second_look(self):
        small = sampling.estimate_per_hour(10, 45, 600)
        big = sampling.estimate_per_hour(250, 45, 600)
        self.assertGreater(big, small * 20)
        self.assertGreater(sampling.estimate_per_hour(250, 45, 600, probe=True), big)

    def test_the_cycle_reads_the_red_repositories_first_when_the_budget_is_short(self):
        am.RUN_CACHE.clear()
        am.BUDGET.stamps.clear()
        reds = [dict(r, conclusion="failure") for r in runs(2)]
        am.RUN_CACHE["bad"] = {"runs": reds, "at": 1, "error": None}
        asked = []

        def fake(repo, per_page, config):
            asked.append(repo)
            return [], None
        config = {"mode": "full", "sampling": {"api_budget_per_hour": 10}, "cold_runs_per_repo": 5, "runs_per_repo": 20, "max_workers": 2, "refresh_seconds": 45, "cold_refresh_seconds": 600}
        am.BUDGET.record(9)
        repos = ["bad"] + [f"new{i}" for i in range(8)]
        try:
            with mock.patch.object(am, "fetch_sampled", fake), mock.patch.object(am, "tuned", lambda c, k, d=None: c[k]):
                am.refresh_runs(repos, config)
            self.assertIn("bad", asked)
            self.assertLessEqual(len(asked), 2)
            self.assertEqual(len(am.SAMPLING_STATE["dropped"]), len(repos) - len(asked))
        finally:
            am.RUN_CACHE.clear()
            am.BUDGET.stamps.clear()
            am.SAMPLING_STATE["dropped"] = []


class SecondLook(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def reader(self, answers):
        def read(path, **kw):
            self.calls.append(path)
            for key, value in answers.items():
                if key in path:
                    return value
            return {"workflow_runs": []}
        return read

    @staticmethod
    def raw(i, branch="main", event="push"):
        return {"id": i, "name": "CI", "path": ".github/workflows/ci.yml", "head_branch": branch, "event": event, "status": "completed", "conclusion": "success",
                "created_at": stamp(i * 10), "run_started_at": stamp(i * 10), "updated_at": stamp(i * 10), "head_sha": "abcdef1234", "html_url": f"https://x/{i}"}

    def test_the_total_that_github_reports_is_kept(self):
        data = {"total_count": 2500, "workflow_runs": [self.raw(i) for i in range(3)]}
        with mock.patch.object(am, "gh_read", self.reader({"actions/runs": data})):
            runs_, error = am.fetch_runs("R", 20)
        self.assertEqual((len(runs_), error, am.SAMPLE_INFO["R"]["total"]), (3, None, 2500))

    def test_a_full_list_asks_for_the_pushes_of_the_default_branch_when_it_is_on(self):
        first = {"total_count": 900, "workflow_runs": [self.raw(i, branch="feature", event="pull_request") for i in range(1, 4)]}
        probe = {"total_count": 40, "workflow_runs": [self.raw(50), self.raw(51)]}
        reader = self.reader({"branch=main": probe, "actions/runs?per_page": first})
        with mock.patch.object(am, "gh_read", reader), mock.patch.object(am, "repo_meta", return_value={"R": {"branch": "main"}}):
            merged, error = am.fetch_sampled("R", 3, {"sampling": {"default_branch_probe": True}})
        self.assertIsNone(error)
        self.assertEqual(len(merged), 5)
        self.assertEqual(sorted(r["id"] for r in merged if r.get("probe")), [50, 51])
        self.assertTrue(any("branch=main&event=push&exclude_pull_requests=true" in c for c in self.calls))
        self.assertEqual(am.SAMPLE_INFO["R"]["probe"], 2)

    def test_it_does_nothing_extra_when_it_is_off_or_the_list_is_not_full(self):
        first = {"workflow_runs": [self.raw(i) for i in range(3)]}
        with mock.patch.object(am, "gh_read", self.reader({"actions/runs": first})):
            am.fetch_sampled("R", 3, {})
            am.fetch_sampled("R", 5, {"sampling": {"default_branch_probe": True}})
        self.assertEqual(len(self.calls), 2)

    def test_a_failed_second_look_keeps_the_first_list(self):
        first = {"workflow_runs": [self.raw(i) for i in range(3)]}
        calls = []

        def read(path, **kw):
            calls.append(path)
            if "branch=" in path:
                raise OSError("boom")
            return first
        with mock.patch.object(am, "gh_read", read), mock.patch.object(am, "repo_meta", return_value={"R": {"branch": "main"}}):
            merged, error = am.fetch_sampled("R", 3, {"sampling": {"default_branch_probe": True}})
        self.assertEqual((len(merged), error), (3, None))

    def test_the_coverage_goes_to_the_repository_table_and_the_summary(self):
        am.RUN_CACHE.clear()
        am.SAMPLE_INFO["R"] = {"asked": 20, "total": 2500, "probe": 0}
        am.RUN_CACHE["R"] = {"runs": [dict(r, started=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - i * 20))) for i, r in enumerate(runs(20))], "at": 1, "error": None}
        try:
            meta = am.repo_meta(["R"], {})
            summary = am.sampling_summary({"refresh_seconds": 45, "cold_refresh_seconds": 600}, ["R"], meta)
        finally:
            am.RUN_CACHE.clear()
        self.assertTrue(meta["R"]["coverage"]["low"])
        self.assertTrue(meta["R"]["coverage"]["at_least"])
        self.assertEqual((summary["low"], summary["low_count"], summary["waiting_count"]), (["R"], 1, 0))


class A2Together(unittest.TestCase):
    FILES = ["ci.yml", "a.yml", "b.yml", "c.yml", "d.yml"]

    def sentinel(self, tmp, listing, **cfg):
        calls = []
        s, _ = base.make(tmp, {}, **cfg)
        s.surface.scans = base.scans(*self.FILES)

        def gh(*args, **kw):
            calls.append(args)
            if args[0] == "api":
                value = listing(args)
                if isinstance(value, Exception):
                    raise value
                return value
            file = args[args.index("-w") + 1]
            return [{"databaseId": 7, "name": file, "conclusion": "success", "status": "completed", "startedAt": "2026-11-05T08:00:00Z", "url": "https://x/7", "headSha": "deadbeefcafe"}]
        s._gh = gh
        return s, calls

    @staticmethod
    def raw(file, conclusion="success", i=1):
        return {"id": i, "name": file, "path": f".github/workflows/{file}@refs/heads/main", "status": "completed", "conclusion": conclusion, "created_at": "2026-11-05T08:00:00Z",
                "run_started_at": "2026-11-05T08:00:00Z", "html_url": f"https://x/{file}", "head_sha": "deadbeefcafe"}

    def test_four_workflows_are_settled_with_one_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = self.sentinel(tmp, lambda args: {"workflow_runs": [self.raw(f, "failure" if f == "b.yml" else "success", i) for i, f in enumerate(self.FILES[1:], 10)]})
            self.assertTrue(s._a2_resolve_tick())
            a2 = base.a2_of(s)
        self.assertEqual(len(calls), 1)
        self.assertIn("exclude_pull_requests=true", calls[0][1])
        self.assertIn("branch=main", calls[0][1])
        self.assertEqual((a2["level"], a2["inconclusive"]), ("bad", []))
        self.assertEqual([r["workflow"] for r in a2["red"]], ["b.yml"])

    def test_what_the_listing_does_not_show_is_asked_one_by_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = self.sentinel(tmp, lambda args: {"workflow_runs": [self.raw("a.yml"), self.raw("b.yml", i=2)]})
            s._a2_resolve_tick()
        self.assertEqual([c[0] for c in calls], ["api", "run", "run"])
        self.assertEqual(len(s.a2_resolved), 4)

    def test_a_failed_listing_falls_back_to_one_by_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = self.sentinel(tmp, lambda args: OSError("down"))
            s._a2_resolve_tick()
        self.assertEqual(calls[0][0], "api")
        self.assertEqual([c[0] for c in calls[1:]], ["run", "run", "run"])

    def test_with_batch_min_zero_it_is_always_one_by_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = self.sentinel(tmp, lambda args: {"workflow_runs": []}, a2_resolve_batch_min=0)
            s._a2_resolve_tick()
        self.assertEqual({c[0] for c in calls}, {"run"})

    def test_more_pages_are_read_only_while_the_workflows_are_not_all_found(self):
        pages = []

        def listing(args):
            pages.append(args[1])
            first = args[1].endswith("&page=1")
            return {"workflow_runs": [self.raw(f, i=n) for n, f in enumerate(self.FILES[1:3] if first else self.FILES[3:], 20)] + ([self.raw("ci.yml", i=99 + n) for n in range(98)] if first else [])}
        with tempfile.TemporaryDirectory() as tmp:
            s, calls = self.sentinel(tmp, listing, a2_resolve_batch_pages=3, a2_resolve_max_calls_per_tick=6)
            s._a2_resolve_tick()
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(s.a2_resolved), 4)

    def test_the_listing_helper_picks_the_last_concluded_run_per_file(self):
        items = [dict(self.raw("a.yml", "cancelled", 3)), self.raw("a.yml", "failure", 2), self.raw("b.yml", i=4), self.raw("other.yml", i=5)]
        found = sl.a2_from_listing(items, {"a.yml", "b.yml", "c.yml"})
        self.assertEqual(sorted(found), ["a.yml", "b.yml"])
        self.assertEqual(found["a.yml"]["conclusion"], "failure")


class RedRuleStillWorks(unittest.TestCase):
    def test_a_run_marked_probe_counts_like_any_other_run_of_the_branch(self):
        merged, _ = sampling.merge_probe([], [dict(r, conclusion="failure") for r in runs(1)])
        rows, _approx = redrule.red_workflows({"R": merged}, {"R": "main"})
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
