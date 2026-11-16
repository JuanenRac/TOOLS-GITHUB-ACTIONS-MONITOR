# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Reds that share a reusable workflow are one cause (one notification, one group line) and a red run says which of its jobs failed, grouped by platform. Synthetic data only; off by default."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import causes, events, redrule  # noqa: E402

SHARED = "demo-org/shared/.github/workflows/build.yml"


def red_row(repo, workflow="ci", reusable=(SHARED,), run_id=1):
    return {"repo": repo, "workflow": workflow, "url": f"https://example.invalid/{repo}/runs/{run_id}", "streak": 1, "since": "2026-01-01T00:00:00Z", "reusable": list(reusable), "run_id": run_id}


def snap(*rows):
    return {"a1": {"stuck": []}, "a2": {"red": list(rows)}, "a3": {"rows": []}, "a4": {"dependabot": []}, "a5": {}, "rate": {"remaining": 4000}}


class Base(unittest.TestCase):
    def setUp(self):
        causes.configure({})

    def tearDown(self):
        causes.configure({})


class ReusableCause(Base):
    def test_paths_come_from_the_referenced_workflows_of_the_run(self):
        body = {"referenced_workflows": [{"path": SHARED + "@refs/heads/main", "sha": "abc"}, {"path": SHARED + "@refs/tags/v1"}, {"path": "o/r/.github/workflows/x.yml@main"}]}
        self.assertEqual(causes.reusable_paths(body), [SHARED, "o/r/.github/workflows/x.yml"])
        self.assertEqual(causes.reusable_paths({}), [])
        self.assertEqual(causes.reusable_paths(None), [])

    def test_off_by_default(self):
        rows = [red_row("a"), red_row("b"), red_row("c")]
        self.assertEqual(causes.groups(rows), [])
        found = events.diff(events.summarize(snap()), events.summarize(snap(*rows)), True)
        self.assertEqual([e["kind"] for e in found], ["red_new"] * 3)

    def test_group_row_names_the_shared_workflow_and_what_it_touches(self):
        causes.configure({"ci": {"group": {"reusable": True}}})
        rows = [red_row("a"), red_row("b"), red_row("b", workflow="docs", run_id=2), red_row("c", reusable=("o/other/.github/workflows/z.yml",))]
        found = causes.groups(rows)
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["workflow"], found[0]["count"], found[0]["repos"]), (SHARED, 3, ["a", "b"]))

    def test_one_notification_for_many_reds_of_one_cause(self):
        causes.configure({"ci": {"group": {"reusable": True, "min": 2}}})
        rows = [red_row("a"), red_row("b"), red_row("c"), red_row("d", reusable=()), red_row("e", reusable=("o/other/.github/workflows/z.yml",))]
        found = events.diff(events.summarize(snap()), events.summarize(snap(*rows)), True)
        self.assertEqual(len(found), 3)      # one for the shared cause, and the two reds with nothing in common
        shared = [e for e in found if e.get("grouped")]
        self.assertEqual(len(shared), 1)
        self.assertEqual((shared[0]["kind"], shared[0]["args"]["count"], shared[0]["args"]["repos"]), ("red_new", 3, ["a", "b", "c"]))
        self.assertIn("build.yml", shared[0]["text"])
        self.assertIn("3 workflows in 3 repositories", shared[0]["text"])

    def test_a_single_red_is_not_a_group(self):
        causes.configure({"ci": {"group": {"reusable": True}}})
        found = events.diff(events.summarize(snap()), events.summarize(snap(red_row("a"))), True)
        self.assertEqual([bool(e.get("grouped")) for e in found], [False])

    def test_rows_and_the_snapshot_carry_the_reusable_paths(self):
        run = {"repo": "demo", "id": 7, "name": "ci", "path": "ci.yml", "branch": "main", "event": "push", "status": "completed", "conclusion": "failure", "started": "2026-01-02T00:00:00Z",
               "reusable": [SHARED]}
        row = redrule.red_workflows({"demo": [run]}, {"demo": "main"}, now=1_769_904_000.0)[0][0]
        self.assertEqual((row["reusable"], row["run_id"]), ([SHARED], 7))


class FailedJobs(Base):
    BODY = {"jobs": [{"name": "build (ubuntu-latest, 3.11)", "conclusion": "success"}, {"name": "build (ubuntu-latest, 3.13)", "conclusion": "success"},
                     {"name": "build (windows-latest, 3.11)", "conclusion": "failure"}, {"name": "build (windows-latest, 3.13)", "conclusion": "failure"},
                     {"name": "build (macos-15, 3.13)", "conclusion": "timed_out"}, {"name": "lint", "conclusion": "skipped"}]}

    def test_failed_jobs_are_grouped_by_platform(self):
        out = causes.summarize_jobs(self.BODY)
        self.assertEqual((out["total"], out["failed"]), (6, 3))
        self.assertEqual([(g["group"], g["failed"], g["total"]) for g in out["groups"]], [("windows-latest", 2, 2), ("macos-15", 1, 1)])
        self.assertEqual(out["groups"][0]["jobs"], ["build (windows-latest, 3.11)", "build (windows-latest, 3.13)"])

    def test_group_by_modes(self):
        self.assertEqual(causes.platform_of("build (ubuntu-latest, 3.11)", "matrix"), "ubuntu-latest")
        self.assertEqual(causes.platform_of("release / test (linux, x64)", "prefix"), "release")
        self.assertEqual(causes.platform_of("release / test (linux, x64)", "auto"), "linux")
        self.assertEqual(causes.platform_of("release / package", "auto"), "release")
        self.assertEqual(causes.platform_of("lint", "auto"), "lint")

    def test_nothing_to_report_when_no_job_failed_or_no_answer(self):
        self.assertEqual(causes.summarize_jobs({"jobs": [{"name": "a", "conclusion": "success"}]})["groups"], [])
        self.assertEqual(causes.summarize_jobs(None), {"total": 0, "failed": 0, "groups": []})

    def test_the_snapshot_puts_the_jobs_on_the_row_and_the_groups_next_to_it(self):
        causes.configure({"ci": {"group": {"reusable": True}}})
        rows = [red_row("a", run_id=5), red_row("b", run_id=6)]
        known = {"a|5": causes.summarize_jobs(self.BODY)}
        for row in rows:
            found = known.get(f"{row['repo']}|{row.get('run_id')}")
            if found:
                row["failed_jobs"] = found
        self.assertEqual(rows[0]["failed_jobs"]["failed"], 3)
        self.assertNotIn("failed_jobs", rows[1])
        self.assertEqual(causes.groups(rows)[0]["count"], 2)


class Wiring(Base):
    def test_settings_are_editable_with_checks(self):
        for path, good, bad in (("ci.group.reusable", True, "yes"), ("ci.group.min", 2, 1), ("ci.failed_jobs.enabled", False, 1), ("ci.failed_jobs.max_per_cycle", 4, 0),
                                ("ci.failed_jobs.group_by", "platform", "none")):
            self.assertTrue(settings_api.check_value(path, good)[0], path)
            self.assertFalse(settings_api.check_value(path, bad)[0], path)

    def test_defaults_change_nothing(self):
        block = actions_monitor.DEFAULTS["ci"]
        self.assertFalse(block["group"]["reusable"])
        self.assertFalse(block["failed_jobs"]["enabled"])
        self.assertEqual(causes.settings({}), causes.DEFAULTS)
        self.assertEqual(causes.settings({"ci": {"failed_jobs": {"group_by": "weird", "max_per_cycle": "x"}}})["failed_jobs"], {"enabled": False, "max_per_cycle": 4, "group_by": "auto"})


if __name__ == "__main__":
    unittest.main()
