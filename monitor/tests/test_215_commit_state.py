# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The state of the last commit as GitHub shows it on a pull request: a check is (name, app), only the most recent run of each counts, the statuses of older services count when asked."""
import tempfile
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.app import surface


def run(name, app="github-actions", started="2026-01-01T10:00:00Z", status="completed", conclusion="success", ident=1):
    return {"name": name, "app": app, "started_at": started, "status": status, "conclusion": conclusion, "id": ident}


class CommitState(unittest.TestCase):
    def test_a_re_run_replaces_the_older_run_of_the_same_check(self):
        runs = [run("ci", conclusion="failure", ident=1), run("ci", started="2026-01-01T11:00:00Z", conclusion="success", ident=2)]
        state = surface.commit_state(runs)
        self.assertEqual((state["total"], state["passed"], state["failed"], state["superseded"]), (1, 1, [], 1))

    def test_a_check_is_its_name_and_its_app(self):
        runs = [run("scan", app="github-actions"), run("scan", app="codecov", conclusion="failure", ident=2)]
        state = surface.commit_state(runs)
        self.assertEqual((state["total"], state["passed"]), (2, 1))
        self.assertEqual(state["failed"], ["scan (codecov)"])

    def test_the_checks_of_other_apps_can_be_left_out(self):
        runs = [run("ci"), run("scan", app="codecov", conclusion="failure", ident=2)]
        state = surface.commit_state(runs, include_other_apps=False)
        self.assertEqual((state["total"], state["failed"]), (1, []))

    def test_pending_and_failed_are_told_apart(self):
        runs = [run("a", status="in_progress", conclusion=None), run("b", conclusion="timed_out", ident=2), run("c", conclusion="skipped", ident=3), run("d", conclusion="cancelled", ident=4)]
        state = surface.commit_state(runs)
        self.assertEqual((state["passed"], state["pending"], state["failed"]), (1, ["a"], ["b", "d"]))

    def test_statuses_count_only_when_asked_and_the_latest_of_each_context_wins(self):
        statuses = [{"context": "cov", "state": "failure", "id": 1, "updated_at": "2026-01-01T10:00:00Z"}, {"context": "cov", "state": "success", "id": 2, "updated_at": "2026-01-01T11:00:00Z"},
                    {"context": "lic", "state": "pending", "id": 3, "updated_at": "2026-01-01T11:00:00Z"}]
        self.assertEqual(surface.commit_state([run("ci")], statuses)["total"], 1)
        state = surface.commit_state([run("ci")], statuses, include_statuses=True)
        self.assertEqual((state["total"], state["passed"], state["pending"]), (3, 2, ["lic (status)"]))

    def test_nothing_to_judge_gives_no_row_and_a_green_commit_gives_none_either(self):
        cfg = surface.settings({"checks": {"commit_state": {"enabled": True}}})
        raw = {"A": {"check_runs_full": [run("ci")]}, "B": {"check_runs_full": [run("ci", conclusion="failure")]}, "C": {"check_runs_full": []}, "D": {}}
        rows, bad = surface.commit_state_rows(raw, ["A", "B", "C", "D"], cfg)
        self.assertEqual([r[0] for r in rows], ["B"])
        self.assertTrue(bad)
        self.assertIn("ci", rows[0][2])

    def test_it_is_off_by_default_and_makes_no_call_then(self):
        self.assertFalse(surface.DEFAULTS["checks"]["commit_state"]["enabled"])
        self.assertTrue(surface.DEFAULTS["checks"]["commit_state"]["include_other_apps"])
        self.assertFalse(surface.DEFAULTS["checks"]["commit_state"]["include_statuses"])


class CommitStateReading(unittest.TestCase):
    def collector(self, **options):
        calls = []

        def gh(*args, **kw):
            calls.append(" ".join(args))
            if "check-runs" in args[1]:
                return {"check_runs": [{"name": "ci", "status": "completed", "conclusion": "failure", "id": 5, "started_at": "2026-01-01T10:00:00Z", "app": {"slug": "github-actions"}}]}
            if "/statuses" in args[1]:
                return [{"context": "cov", "state": "pending", "id": 1, "updated_at": "2026-01-01T10:00:00Z"}]
            return {}

        cfg = surface.settings({})
        for name in cfg["checks"]:
            cfg["checks"][name]["enabled"] = name == "commit_state"
        cfg["checks"]["commit_state"].update(options)
        return surface.Collector(gh, tempfile.gettempdir(), cfg), calls

    def test_one_call_for_the_check_runs_and_a_second_only_with_the_statuses_on(self):
        c, calls = self.collector(enabled=True)
        out, used = c.fetch_repo("A", "main")
        self.assertEqual((len(calls), used), (1, 1))
        self.assertEqual(out["check_runs_full"][0]["app"], "github-actions")
        self.assertNotIn("commit_statuses", out)
        c, calls = self.collector(enabled=True, include_statuses=True)
        out, used = c.fetch_repo("A", "main")
        self.assertEqual((len(calls), used), (2, 2))
        self.assertEqual(out["commit_statuses"][0]["context"], "cov")

    def test_switched_off_it_reads_nothing(self):
        c, calls = self.collector(enabled=False)
        c.fetch_repo("A", "main")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
