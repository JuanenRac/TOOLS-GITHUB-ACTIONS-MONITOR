# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The reads of the sentinel that were new in the fourth phase stay inside their share of the allowance: the listing of the batch way of A2 is not asked again and again, a question that failed waits
(5 minutes, 30, 6 hours) while the others go on, and repositories whose permissions cannot be read do not keep the other 225 from being read."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import surface  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

FILES = ["ci.yml", "release.yml", "manual.yml"]


def run_row(repo, i):
    return {"repo": repo, "id": i, "name": "CI", "path": "ci.yml", "branch": "main", "status": "completed", "conclusion": "success", "started": f"2026-11-06T0{i % 9}:00:00Z", "url": "u", "seconds": 5,
            "actor": "o", "sha": "abc1234"}


class Account:
    """A sentinel of `count` active repositories whose release.yml and manual.yml are hidden (no run of them in the sample)."""

    def __init__(self, case, count, answer):
        self.calls, self.names = [], [f"repo-{i:03d}" for i in range(count)]
        runs = {r: [run_row(r, i) for i in range(6)] for r in self.names}

        def gh(*args, **kw):
            self.calls.append(args)
            return answer(*args)
        ctx = {"gh": gh, "repos_fn": lambda: self.names, "runs_fn": lambda: {r: {"runs": runs[r]} for r in self.names},
               "data_fn": lambda: {"rate": {"remaining": 5000, "limit": 5000}, "active": [], "issues": []}, "eco_fn": lambda r: "main"}
        self.tmp = tempfile.TemporaryDirectory()
        case.addCleanup(self.tmp.cleanup)
        for name, value in (("CACHE_FILE", Path(self.tmp.name) / "c.json"), ("HISTORY_FILE", Path(self.tmp.name) / "h.json")):
            patcher = mock.patch.object(sl, name, value)
            patcher.start()
            case.addCleanup(patcher.stop)
        self.sentinel = sl.Sentinel(ctx, {"runs_per_repo": 6, "cold_runs_per_repo": 3, "sentinel": {"budget_per_hour": 600, "max_calls_per_tick": 4}})
        s = self.sentinel
        s.repo_info = {r: {"branch": "main"} for r in self.names}
        s.surface.scans = {r: {"workflows": [surface.scan_workflow("on: push", f) for f in FILES], "stacks": [], "dependabot_yml": True, "codeql_yml": True, "manifest": None, "changelog_top": None}
                           for r in self.names}

    def hidden(self):
        return [f"{r}|{f}" for r in self.names for f in FILES[1:]]


def listing_without_the_hidden(*args):
    """The batch listing brings only ci.yml; the question one by one answers with a run."""
    if args[0] == "api":
        return {"workflow_runs": [{"id": 1, "name": "CI", "path": ".github/workflows/ci.yml@refs/heads/main", "status": "completed", "conclusion": "success", "created_at": "2026-11-05T08:00:00Z",
                                   "run_started_at": "2026-11-05T08:00:00Z", "html_url": "https://x/1", "head_sha": "deadbeefcafe"}]}
    return [{"databaseId": 7, "name": "w", "conclusion": "success", "status": "completed", "startedAt": "2026-11-05T08:00:00Z", "url": "u", "headSha": "deadbeefcafe"}]


class TheBatchWayOfA2(unittest.TestCase):
    def test_workflows_that_the_listing_does_not_bring_are_resolved_without_asking_the_same_listing_again(self):
        account = Account(self, 6, listing_without_the_hidden)
        s = account.sentinel
        ticks = 0
        while ticks < 40 and any(k not in s.a2_resolved for k in account.hidden()):
            s._a2_resolve_tick()
            ticks += 1
        listings = [c for c in account.calls if c[0] == "api"]
        one_by_one = [c for c in account.calls if c[0] == "run"]
        self.assertTrue(all(k in s.a2_resolved for k in account.hidden()), "all twelve were resolved")
        self.assertLess(ticks, 20)
        self.assertLessEqual(len(listings), 6, "one listing per repository, not one per turn")
        self.assertEqual(len({c[1] for c in listings}), len(listings), "the same listing is not asked for twice inside the TTL")
        self.assertLessEqual(len(one_by_one), 12)

    def test_a_listing_that_was_read_is_followed_by_the_question_one_by_one_in_the_next_turn(self):
        account = Account(self, 4, listing_without_the_hidden)
        account.sentinel._a2_resolve_tick()
        account.sentinel._a2_resolve_tick()
        kinds = [c[0] for c in account.calls]
        self.assertEqual(kinds[:4], ["api"] * 4)
        self.assertEqual(kinds[4:8], ["run"] * 4, "the four listings are not asked for again: the room goes to the questions one by one")


class AQuestionThatFailsWaits(unittest.TestCase):
    def test_a_failing_one_by_one_question_is_not_asked_in_every_turn(self):
        def answer(*args):
            if args[0] == "api":
                return listing_without_the_hidden(*args)
            if "-w" in args and args[args.index("-w") + 1] == "release.yml":
                raise RuntimeError("HTTP 404")
            return listing_without_the_hidden(*args)
        account = Account(self, 3, answer)
        s = account.sentinel
        for _ in range(30):
            s._a2_resolve_tick()
        failing = [c for c in account.calls if c[0] == "run" and "release.yml" in c]
        self.assertLessEqual(len(failing), 3, "once per repository, then it waits")
        self.assertTrue(all(f"{r}|manual.yml" in s.a2_resolved for r in account.names), "the others were resolved meanwhile")
        key = f"a2|{account.names[0]}|release.yml"
        self.assertTrue(s._waiting_question(key))
        self.assertFalse(s._waiting_question(key, now=10 ** 12))

    def test_the_wait_grows_five_minutes_thirty_minutes_six_hours(self):
        account = Account(self, 1, listing_without_the_hidden)
        s = account.sentinel
        waits = []
        for _ in range(5):
            s._failed_question("q", now=1000.0)
            waits.append(s.backoff["q"][1] - 1000.0)
        self.assertEqual(waits, [300, 1800, 21600, 21600, 21600])
        s._answered_question("q")
        self.assertFalse(s._waiting_question("q", now=1001.0))

    def test_the_jobs_of_a_red_run_that_fail_to_be_read_wait_too(self):
        from github_actions_monitor.data_pipeline import causes
        account = Account(self, 2, listing_without_the_hidden)
        s = account.sentinel
        s.last_snap = {"a2": {"red": [{"repo": "repo-000", "run_id": 11}, {"repo": "repo-001", "run_id": 12}]}}
        calls = []

        def jobs(*args, **kw):
            calls.append(args)
            if "/11/" in args[1]:
                raise RuntimeError("HTTP 502")
            return {"jobs": []}
        s._gh = jobs
        policy = dict(causes.POLICY["failed_jobs"], enabled=True, max_per_cycle=4)
        with mock.patch.dict(causes.POLICY, {"failed_jobs": policy}):
            for _ in range(10):
                s._failed_jobs_tick()
        self.assertEqual(len([c for c in calls if "/11/" in c[1]]), 1)
        self.assertEqual(len([c for c in calls if "/12/" in c[1]]), 1)


class RepositoriesWhosePermissionsCannotBeRead(unittest.TestCase):
    def test_twenty_five_that_fail_do_not_keep_the_other_two_hundred_and_twenty_five_from_being_read(self):
        failing = {f"repo-{i:03d}" for i in range(25)}
        asked = {}

        def answer(*args):
            path = args[1] if len(args) > 1 else ""
            if path.endswith("/actions/permissions"):
                repo = path.split("/")[2]
                asked[repo] = asked.get(repo, 0) + 1
                if repo in failing:
                    raise RuntimeError("HTTP 500")
                return {"allowed_actions": "all"}
            return {}
        account = Account(self, 250, answer)
        s = account.sentinel
        s.cfg["hygiene_seconds"] = 3600
        s.cfg["budget_per_hour"] = 100000
        s.cfg["max_calls_per_tick"] = 1000
        clock = [1_800_000_000.0]
        with mock.patch.object(sl.time, "time", side_effect=lambda: clock[0]):
            for _ in range(24):      # about three hours of turns of five minutes
                for _inner in range(3):
                    batch = s._perms_due()[:20]
                    for repo, res in map(s._fetch_perms, batch):
                        if res:
                            s.perms[repo] = res
                clock[0] += 300
        healthy_read = [r for r in account.names if r not in failing and (s.perms.get(r) or {}).get("allowed_actions")]
        self.assertEqual(len(healthy_read), 225)
        self.assertTrue(all(asked[r] <= 6 * 3 for r in failing), "each failing repository is asked a few times, not at every turn")


if __name__ == "__main__":
    unittest.main()
