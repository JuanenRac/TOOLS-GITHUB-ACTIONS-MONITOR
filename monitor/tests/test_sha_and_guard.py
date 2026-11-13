# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A run built on another commit is never offered for signing, and /api/data goes through the local guard."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.cli import gha_dispatch_all as gd  # noqa: E402


def state(repo, run):
    return "completed", "success", f"https://example.invalid/{run}", []


class ShaCorrelation(unittest.TestCase):
    def batch(self, matched):
        name = next(iter(gd.TARGETS))
        info = {"run": 11, "sha": "a" * 40, "workflow": "x.yml"}
        if matched is not None:
            info["sha_matched"] = matched
        return name, {"targets": {name: info}}

    def test_a_run_on_another_commit_is_not_ready_and_has_no_command(self):
        name, batch = self.batch(False)
        row = gd.finalize_rows(batch, state_fn=state)[0]
        self.assertEqual(row["state"], "not_ready")
        self.assertEqual(row["reason"], "sha_mismatch")
        self.assertNotIn("command", row)
        self.assertNotIn("argv", row)

    def test_two_concurrent_runs_with_different_commits_only_the_matched_one_is_ready(self):
        names = list(gd.TARGETS)[:2]
        batch = {"targets": {names[0]: {"run": 1, "sha": "b" * 40, "sha_matched": True},
                             names[1]: {"run": 2, "sha": "c" * 40, "sha_matched": False}}}
        rows = {r["name"]: r for r in gd.finalize_rows(batch, state_fn=state)}
        self.assertEqual(rows[names[0]]["state"], "ready")
        self.assertEqual(rows[names[1]]["state"], "not_ready")

    def test_a_matched_run_is_ready_and_an_old_batch_without_the_field_needs_review(self):
        name, batch = self.batch(True)
        self.assertEqual(gd.finalize_rows(batch, state_fn=state)[0]["state"], "ready")
        name, batch = self.batch(None)
        row = gd.finalize_rows(batch, state_fn=state)[0]
        self.assertEqual((row["state"], row["reason"]), ("not_ready", "needs_review"))
        self.assertNotIn("command", row)


class ApiDataGuard(unittest.TestCase):
    def test_api_data_calls_the_guard(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        start = text.index('elif path.startswith("/api/data")')
        self.assertIn("self.guard()", text[start:start + 200])


if __name__ == "__main__":
    unittest.main()
