# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Four small rules that said one thing and did another: the reserve of the budget for the reds belongs to the hour (not to every cycle), a page after the first that fails keeps what was read and says the
list is cut, a run that waits for a runner of its own that is off is a breakdown (never a ghost), and a workflow that ran after the permissions were read is not still 'switched off'."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import paging, redrule, sampling, stuckrule  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def stamp(seconds_ago):
    return datetime.fromtimestamp(NOW - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TheReserveOfTheRedsBelongsToTheHour(unittest.TestCase):
    def test_with_the_budget_spent_the_reds_get_the_reserve_once_not_every_cycle(self):
        reds = {f"red-{n:02d}" for n in range(12)}
        todo = [(r,) for r in sorted(reds)] + [(f"ok-{n:02d}",) for n in range(60)]
        spent = 0
        for _cycle in range(80):      # an hour of cycles of 45 seconds
            kept, _ = sampling.plan(todo, reds, 100, 100 + spent)
            spent += len(kept)
        self.assertLessEqual(spent, 10)      # the reserve is a tenth of 100

    def test_the_first_cycle_of_the_hour_still_reads_everything_the_budget_allows(self):
        reds = {"red-1"}
        kept, dropped = sampling.plan([("red-1",), ("a",), ("b",)], reds, 2, 0)
        self.assertEqual([k[0] for k in kept], ["red-1", "a"])
        self.assertEqual([d[0] for d in dropped], ["b"])


class APageThatFailsAfterTheFirst(unittest.TestCase):
    def test_what_was_read_is_kept_and_the_cut_is_said(self):
        calls = []

        def read(path):
            calls.append(path)
            if "page=2" in path:
                raise RuntimeError("502 Bad Gateway")
            return {"total_count": 240, "jobs": [{"id": n} for n in range(100)]}
        page = paging.read_pages(read, "repos/o/r/actions/runs/1/jobs", "jobs", 100, 3)
        self.assertEqual((page["seen"], page["cut"], page["pages"]), (100, True, 1))
        self.assertIn("502", page["error"])

    def test_the_first_page_that_fails_is_still_an_error(self):
        def read(path):
            raise RuntimeError("401")
        with self.assertRaises(RuntimeError):
            paging.read_pages(read, "x", "jobs", 100, 3)

    def test_the_jobs_of_a_run_keep_the_first_page(self):
        calls = []
        saved = am.gh

        def fake(*args, **kwargs):
            calls.append(args)
            if "page=2" in args[1]:
                raise RuntimeError("502")
            return {"total_count": 240, "jobs": [{"id": n, "name": f"j{n}", "status": "completed", "conclusion": "failure" if n == 3 else "success"} for n in range(100)]}
        am.gh = fake
        try:
            jobs, seen, total = am.run_jobs_info("repo", 1)
        finally:
            am.gh = saved
        self.assertEqual(seen, 100)
        self.assertEqual(len(jobs), 100)


class ARunnerThatIsOffIsNotAGhost(unittest.TestCase):
    def test_a_queued_run_for_a_runner_of_its_own_that_is_off_stays_a_breakdown(self):
        cfg = {**stuckrule.DEFAULTS, "ghost_enabled": True, "ghost_days": 7}
        run = {"repo": "r", "name": "build", "path": "b.yml", "status": "queued", "started": stamp(8 * DAY), "attempt": 1}
        _stuck, reason, _ = stuckrule.evaluate(run, 60, cfg, labels=("self-hosted", "lab"), offline_labels=("lab",), now=NOW)
        self.assertEqual(reason, "runner_down")

    def test_the_same_run_with_no_runner_problem_is_a_ghost_after_seven_days(self):
        cfg = {**stuckrule.DEFAULTS, "ghost_enabled": True, "ghost_days": 7}
        run = {"repo": "r", "name": "build", "path": "b.yml", "status": "queued", "started": stamp(8 * DAY), "attempt": 1}
        self.assertEqual(stuckrule.evaluate(run, 60, cfg, labels=(), offline_labels=(), now=NOW)[:2], (False, "ghost"))


class AWorkflowSwitchedOnAgain(unittest.TestCase):
    def row(self, seconds_ago):
        return {"repo": "fork", "file": ".github/workflows/publish.yml", "since": stamp(seconds_ago), "workflow": "Publish"}

    def test_a_failure_before_the_reading_is_apart_and_one_after_it_is_red(self):
        perms = {"fork": {"at": NOW - 3600, "wf_manual_files": ["publish.yml"]}}
        kept, apart = redrule.split_disabled([self.row(7200), self.row(60)], perms)
        self.assertEqual(([r["since"] for r in kept], [r["since"] for r in apart]), ([stamp(60)], [stamp(7200)]))

    def test_without_a_moment_of_reading_the_old_rule_holds(self):
        kept, apart = redrule.split_disabled([self.row(60)], {"fork": {"wf_manual_files": ["publish.yml"]}})
        self.assertEqual((kept, len(apart)), ([], 1))


if __name__ == "__main__":
    unittest.main()
