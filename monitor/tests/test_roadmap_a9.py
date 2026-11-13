# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Offline tests of A9 (the GitHub Roadmap boards and whether they are alive). Run:  py -3 -m unittest discover -s tests -v"""
import sys
import unittest
import _testenv  # noqa: F401
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_actions_monitor.sentinels import roadmap_a9 as rm  # noqa: E402

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
DEFS = {k: {"title": t, "cards": 10, "status": {"Done": 4, "Backlog": 6}} for k, t in rm.BOARDS}


def run(age=1.0, conclusion="success"):
    return {"age_days": age, "conclusion": conclusion, "url": "https://example.test/run"}


class Build(_testenv.Spanish, unittest.TestCase):
    def build(self, runs, last_any=None, live=None, live_error=None, defs_age=3.0, defs=None):
        return rm.build(DEFS if defs is None else defs, None, live, live_error, runs, last_any, None, defs_age)

    def test_all_alive(self):
        r = self.build({k: run() for k, _ in rm.BOARDS})
        self.assertEqual(r["level"], "info")
        self.assertTrue(all(not b["problems"] for b in r["boards"]))

    def test_never_ran_is_a_warning(self):
        r = self.build({})
        self.assertEqual(r["level"], "warn")
        self.assertIn("el workflow de siembra nunca ha corrido", r["boards"][0]["problems"])

    def test_stale_board(self):
        r = self.build({"urtc": run(age=20.0), **{k: run() for k, _ in rm.BOARDS if k != "urtc"}})
        urtc = next(b for b in r["boards"] if b["key"] == "urtc")
        self.assertTrue(any("sin reconciliar" in p for p in urtc["problems"]))
        self.assertEqual(r["level"], "warn")

    def test_failed_last_run(self):
        r = self.build({k: run(conclusion="failure") for k, _ in rm.BOARDS})
        self.assertTrue(all(any("terminó en failure" in p for p in b["problems"]) for b in r["boards"]))

    def test_definitions_changed_after_the_last_run(self):
        r = self.build({k: run(age=5.0) for k, _ in rm.BOARDS}, defs_age=1.0)
        self.assertTrue(all(any("falta aplicarlas" in p for p in b["problems"]) for b in r["boards"]))

    def test_definitions_older_than_the_run_are_fine(self):
        r = self.build({k: run(age=1.0) for k, _ in rm.BOARDS}, defs_age=4.0)
        self.assertEqual(r["level"], "info")

    def test_drift_between_github_and_the_definitions(self):
        live = {"URTC Roadmap": {"cards": 10, "status": {"Done": 1, "Backlog": 9}, "url": "https://github.com/users/JuanenRac/projects/2"}}
        r = self.build({k: run() for k, _ in rm.BOARDS}, live=live)
        urtc = next(b for b in r["boards"] if b["key"] == "urtc")
        self.assertTrue(urtc["drift"])
        self.assertEqual(urtc["url"], "https://github.com/users/JuanenRac/projects/2")
        self.assertEqual(r["level"], "warn")

    def test_matching_github_has_no_drift(self):
        live = {"URTC Roadmap": {"cards": 10, "status": {"Done": 4, "Backlog": 6}, "url": "u"}}
        r = self.build({k: run() for k, _ in rm.BOARDS}, live=live)
        self.assertFalse(next(b for b in r["boards"] if b["key"] == "urtc")["drift"])

    def test_without_the_scope_the_tab_still_works(self):
        r = self.build({k: run() for k, _ in rm.BOARDS}, live={}, live_error=rm.SCOPE_HELP)
        self.assertEqual(r["live_error"], rm.SCOPE_HELP)
        self.assertEqual(r["level"], "info")
        self.assertIsNone(r["boards"][0]["drift"])


class Github(_testenv.Spanish, unittest.TestCase):
    def test_live_boards_counts_pages_and_states(self):
        calls = []

        def gh(*args):
            calls.append(args)
            query = " ".join(args)
            if "projectsV2(first:20)" in query:
                return {"data": {"user": {"projectsV2": {"nodes": [{"id": "P1", "title": "URTC Roadmap", "number": 2, "url": "https://x/p/2"}]}}}}
            first = not any(a.startswith("after=") for a in args)
            nodes = [{"fieldValueByName": {"name": "Done"}}, {"fieldValueByName": None}] if first else [{"fieldValueByName": {"name": "Blocked"}}]
            return {"data": {"node": {"items": {"pageInfo": {"hasNextPage": first, "endCursor": "C"}, "nodes": nodes}}}}

        boards, error = rm.live_boards(gh)
        self.assertIsNone(error)
        self.assertEqual(boards["URTC Roadmap"]["cards"], 3)
        self.assertEqual(boards["URTC Roadmap"]["status"], {"Done": 1, "Sin estado": 1, "Blocked": 1})

    def test_missing_scope_gives_the_exact_instruction(self):
        def gh(*args):
            raise RuntimeError("your authentication token is missing required scopes [read:project]")

        boards, error = rm.live_boards(gh)
        self.assertEqual(boards, {})
        self.assertIn("gh auth refresh -s read:project", error)

    def test_last_runs_maps_jobs_to_boards(self):
        def gh(*args):
            path = args[1]
            if path.endswith("status=completed"):
                return {"workflow_runs": [{"id": 7, "created_at": "2026-11-04T12:00:00Z", "conclusion": "success", "event": "schedule", "html_url": "u"}]}
            return {"jobs": [{"name": "Seed urtc", "conclusion": "success"}, {"name": "Seed armor", "conclusion": "failure"}]}

        per_board, last_any, error = rm.last_runs(gh, NOW)
        self.assertIsNone(error)
        self.assertEqual(per_board["urtc"]["conclusion"], "success")
        self.assertEqual(per_board["armor"]["conclusion"], "failure")
        self.assertEqual(last_any["age_days"], 1.0)

    def test_last_runs_survive_a_missing_workflow(self):
        def gh(*args):
            raise RuntimeError("404 Not Found")

        per_board, last_any, error = rm.last_runs(gh, NOW)
        self.assertEqual(per_board, {})
        self.assertIsNone(last_any)
        self.assertIn("404", error)


class Definitions(unittest.TestCase):
    def test_the_real_definitions_are_readable(self):
        from github_actions_monitor.app import workspace
        if not workspace.available():
            self.skipTest("integration test: needs the workspace of the repositories")
        profile = workspace.workspace_root() / "JuanenRac"
        if not (profile / "tools" / "roadmap_defs.py").is_file():
            self.skipTest("the profile repository is not next to this one")
        defs, error = rm.defs_summary(profile)
        self.assertIsNone(error)
        self.assertEqual(set(defs), {k for k, _ in rm.BOARDS})
        for board in defs.values():
            self.assertEqual(sum(board["status"].values()), board["cards"])

    def test_a_missing_repository_is_reported_not_raised(self):
        defs, error = rm.defs_summary(Path("Z:/nowhere"))
        self.assertEqual(defs, {})
        self.assertIn("roadmap_defs.py", error)


if __name__ == "__main__":
    unittest.main()
