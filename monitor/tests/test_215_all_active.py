# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Every run that is still going, workflow by workflow (`fleet.show_all_active`): two runs of the same workflow that go at once are both counted and listed, with the newest run of each branch; with the setting
off a workflow shows only its newest run."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.health import fleet, repo_view  # noqa: E402

NOW = 1_800_000_000.0


def go(i, name="Release", branch="main", status="in_progress", repo="r"):
    return {"repo": repo, "id": i, "name": name, "branch": branch, "status": status, "started": f"2027-01-15T10:{i % 60:02d}:00Z", "url": f"https://x/{i}"}


ACTIVE = [go(1), go(2, branch="v2"), go(3, status="queued"), go(4, "Docs"), go(5, "Docs", status="waiting"), go(9, repo="other")]


class AllTheRunsThatGo(unittest.TestCase):
    def test_every_run_of_a_workflow_is_counted_and_the_newest_of_each_branch_is_listed(self):
        part = repo_view.active_part("r", ACTIVE)
        self.assertEqual((part["runs"], part["running"], part["queued"], part["all"]), (5, 3, 2, True))
        release, docs = part["workflows"]
        self.assertEqual((release["workflow"], release["running"], release["queued"]), ("Release", 2, 1))
        self.assertEqual(sorted(b["branch"] for b in release["branches"]), ["main", "v2"])
        self.assertEqual(next(b for b in release["branches"] if b["branch"] == "main")["id"], 3)      # the newest of the branch
        self.assertEqual((docs["workflow"], docs["running"], docs["queued"]), ("Docs", 1, 1))

    def test_with_the_setting_off_a_workflow_shows_only_its_newest_run(self):
        part = repo_view.active_part("r", ACTIVE, all_runs=False)
        self.assertEqual((part["runs"], part["all"]), (2, False))
        self.assertEqual([(w["workflow"], w["running"] + w["queued"]) for w in part["workflows"]], [("Docs", 1), ("Release", 1)])

    def test_other_repositories_and_odd_items_do_not_count(self):
        self.assertEqual(repo_view.active_part("none", ACTIVE)["runs"], 0)
        self.assertEqual(repo_view.active_part("r", [None, "x", {"repo": "r"}])["runs"], 1)      # a run with no name counts under an empty name
        self.assertEqual(repo_view.active_part("r", None)["workflows"], [])

    def test_the_list_is_bounded(self):
        many = [go(i, name=f"w{i:03d}") for i in range(1, 60)]
        part = repo_view.active_part("r", many)
        self.assertEqual((part["runs"], len(part["workflows"])), (59, repo_view.ACTIVE_WORKFLOWS))

    def test_the_health_of_the_repository_and_the_rows_of_the_fleet_carry_it(self):
        view = repo_view.repo_view("r", [], [], ACTIVE, [], None, {"ci": "healthy"}, "alpha", NOW)
        self.assertEqual(view["ci"]["active"]["runs"], 5)
        rows = fleet.fleet_view([view], {})["rows"]
        self.assertEqual((rows[0]["running"], rows[0]["queued"]), (3, 2))
        flat = repo_view.repo_view("r", [], [], ACTIVE, [], None, {"ci": "healthy"}, "alpha", NOW, None, False)
        self.assertEqual(flat["ci"]["active"]["runs"], 2)

    def test_the_setting_is_on_by_default_and_on_the_settings_page(self):
        self.assertTrue(fleet.settings({})["show_all_active"])
        self.assertFalse(fleet.settings({"fleet": {"show_all_active": False}})["show_all_active"])
        self.assertTrue(fleet.settings({"fleet": {"show_all_active": "no"}})["show_all_active"])
        self.assertTrue(am.DEFAULTS["fleet"]["show_all_active"])
        self.assertIn("fleet.show_all_active", {row[2] for row in settings_api.ROWS})


if __name__ == "__main__":
    unittest.main()
