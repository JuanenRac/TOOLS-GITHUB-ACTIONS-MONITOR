# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A workflow that only runs on pull requests has no run on the default branch: main_triggered says False, so A2 does not ask for one."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import surface  # noqa: E402


class PullRequestOnly(unittest.TestCase):
    def test_only_pull_request_is_not_main_triggered(self):
        text = "name: x\non:\n  pull_request:\n    paths:\n      - 'a/**'\njobs:\n  j:\n    runs-on: ubuntu-latest\n"
        self.assertFalse(surface.main_triggered(text))

    def test_pull_request_target_and_dispatch_only_is_not_main_triggered(self):
        text = "name: x\non:\n  pull_request_target:\n  workflow_dispatch:\njobs: {}\n"
        self.assertFalse(surface.main_triggered(text))

    def test_pull_request_plus_push_still_counts(self):
        text = "name: x\non:\n  push:\n    branches: [main]\n  pull_request:\njobs: {}\n"
        self.assertTrue(surface.main_triggered(text))

    def test_pull_request_plus_schedule_still_counts(self):
        text = "name: x\non:\n  pull_request:\n  schedule:\n    - cron: '0 3 * * *'\njobs: {}\n"
        self.assertTrue(surface.main_triggered(text))

    def test_list_form_of_pull_request_only(self):
        text = "name: x\non: [pull_request]\njobs: {}\n"
        self.assertFalse(surface.main_triggered(text))


if __name__ == "__main__":
    unittest.main()
