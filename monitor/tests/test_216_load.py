# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A synthetic account of 250 repositories and 1,200 workflows (no network, deterministic): how many requests a cycle makes, how long the cycle and the team health take, how much memory the held
data need, and how many ticks the sentinel needs to look up every workflow that a full sample hides. The bounds are wide on purpose (a loaded computer must pass); they catch a cost that grows
with repositories x runs or a lookup that stops converging, not a few milliseconds."""
import tempfile
import time
import tracemalloc
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.app import surface
from github_actions_monitor.sentinels import sentinel_local as sl

REPOS = 250
WORKFLOWS_PER_REPO = 5      # 250 x 5 = 1,250 (>= 1,200)
RUNS = 20
NOW = time.time()


def repo_names():
    return [f"repo-{i:03d}" for i in range(REPOS)]


def raw_run(repo_index, i):
    when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 30 * i - (6 * 3600 if repo_index % 2 else 0)))      # half of the repositories have been quiet for six hours
    return {"id": repo_index * 1000 + i, "name": "CI", "display_title": "t", "event": "push", "head_branch": "main", "path": f".github/workflows/w{i % 2}.yml", "head_sha": "abcdef1234",
            "run_number": i, "status": "completed", "conclusion": "failure" if (repo_index % 25 == 0 and i == 0) else "success", "created_at": when, "run_started_at": when, "updated_at": when,
            "html_url": f"https://x/{repo_index}/{i}", "run_attempt": 1, "actor": {"login": "o"}}


class FakeGitHub:
    def __init__(self):
        self.reads = []

    def read(self, path, **kw):
        self.reads.append(path)
        index = int(path.split("/repo-")[1][:3])
        per = int(path.split("per_page=")[1].split("&")[0])
        return {"total_count": 900, "workflow_runs": [raw_run(index, i) for i in range(min(per, RUNS))]}


class Load(unittest.TestCase):
    def test_a_cycle_over_250_repositories_costs_one_request_per_repository_and_the_next_one_only_the_hot_ones(self):
        fake = FakeGitHub()
        config = {"mode": "full", "cold_runs_per_repo": 5, "runs_per_repo": 20, "max_workers": 8, "refresh_seconds": 45, "cold_refresh_seconds": 600, "hot_hours": 3}
        am.RUN_CACHE.clear()
        try:
            with mock.patch.object(am, "gh_read", fake.read), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), mock.patch.object(am, "tuned", lambda c, k, d=None: c[k]):
                started = time.perf_counter()
                am.refresh_runs(repo_names(), config)
                first = time.perf_counter() - started
                calls_first = len(fake.reads)
                am.refresh_runs(repo_names(), config)
                calls_second = len(fake.reads) - calls_first
        finally:
            am.RUN_CACHE.clear()
        print(f"\nload: first cycle {calls_first} requests in {first:.2f} s, second cycle {calls_second} requests")
        self.assertEqual(calls_first, REPOS)      # a first look reads each repository once
        self.assertLess(calls_second, REPOS)      # the repositories that were quiet and green wait for their slow turn
        self.assertLess(first, 60)

    def test_the_team_health_over_250_repositories_is_fast_and_light(self):
        runs = [{**{"repo": r, "id": n * 100 + i, "name": "CI", "status": "completed", "conclusion": "success", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 30 * i))}} for n, r in enumerate(repo_names()) for i in range(RUNS)]
        data = {"runs": runs, "failing": [{"repo": "repo-000", "workflow": "CI"}], "active": [], "repos": repo_names()}
        old = (am.STATE.get("data"), am.SENTINEL["registry"], am.SENTINEL["obj"])
        self.addCleanup(lambda: (am.STATE.update(data=old[0]), am.SENTINEL.update(registry=old[1], obj=old[2])))
        am.STATE["data"] = data
        am.SENTINEL.update(registry=None, obj=None)
        tracemalloc.start()
        try:
            started = time.perf_counter()
            with mock.patch.object(am, "credential_alerts", return_value=[]), mock.patch.object(am, "score_alerts", return_value=[]):
                views = am.health_views(NOW)
            took = time.perf_counter() - started
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        print(f"\nload: team health {len(views)} repositories, {took:.2f} s, peak {peak / 1e6:.1f} MB")
        self.assertEqual(len(views), REPOS)
        self.assertLess(took, 30)
        self.assertLess(peak, 200_000_000)

    def test_the_sentinel_looks_up_every_hidden_workflow_in_a_bounded_number_of_requests(self):
        names = repo_names()
        files = ["ci.yml"] + [f"w{k}.yml" for k in range(WORKFLOWS_PER_REPO - 1)]
        full = {r: [{"repo": r, "id": n * 10 + i, "name": "CI", "path": "ci.yml", "branch": "main", "status": "completed", "conclusion": "success", "started": f"2026-11-06T0{i % 9}:00:00Z", "url": "u",
                     "seconds": 5, "actor": "o", "sha": "abc1234"} for i in range(6)] for n, r in enumerate(names)}
        calls = []

        def gh(*args, **kw):
            calls.append(args)
            if args[0] == "api":      # one listing of the default branch: every workflow of the repository has a run in it
                repo = args[1].split("/")[2]
                return {"workflow_runs": [{"id": k + 1, "name": f, "path": f".github/workflows/{f}@refs/heads/main", "status": "completed", "conclusion": "success", "created_at": "2026-11-05T08:00:00Z",
                                           "run_started_at": "2026-11-05T08:00:00Z", "html_url": f"https://x/{repo}/{f}", "head_sha": "deadbeefcafe"} for k, f in enumerate(files)]}
            return [{"databaseId": 7, "name": "w", "conclusion": "success", "status": "completed", "startedAt": "2026-11-05T08:00:00Z", "url": "u", "headSha": "deadbeefcafe"}]
        ctx = {"gh": gh, "repos_fn": lambda: names, "runs_fn": lambda: {r: {"runs": full[r]} for r in names},
               "data_fn": lambda: {"rate": {"remaining": 5000, "limit": 5000}, "active": [], "issues": []}, "eco_fn": lambda r: "main"}
        caps = {"runs_per_repo": 6, "cold_runs_per_repo": 3}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s = sl.Sentinel(ctx, dict(caps, sentinel={"budget_per_hour": 5000, "max_calls_per_tick": 500}))
            s.repo_info = {r: {"branch": "main"} for r in names}
            s.surface.scans = {r: {"workflows": [surface.scan_workflow("on: push", f) for f in files], "stacks": [], "dependabot_yml": True, "codeql_yml": True, "manifest": None, "changelog_top": None} for r in names}
            started = time.perf_counter()
            ticks = 0
            while ticks < 400 and any(files[k] and f"{r}|{f}" not in s.a2_resolved for r in names for k, f in enumerate(files[1:], 1)):
                s._a2_resolve_tick()
                ticks += 1
            took = time.perf_counter() - started
        total = len(names) * (len(files) - 1)
        print(f"\nload: {total} hidden workflows settled in {ticks} ticks and {len(calls)} requests, {took:.2f} s")
        self.assertLess(ticks, 400, "the lookups must converge")
        self.assertLessEqual(len(calls), total)      # never more than one request per hidden workflow
        if hasattr(sl, "a2_from_listing"):
            self.assertLessEqual(len(calls), REPOS)      # with the listing of the branch: one request per repository


if __name__ == "__main__":
    unittest.main()
