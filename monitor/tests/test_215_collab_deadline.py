# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A round of the Collab sentinel has a time ceiling too: past it no new repository is started and the ones not reached are named as not checked."""
import sys
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
from github_actions_monitor.sentinels import sentinel_base, sentinel_collab  # noqa: E402
from test_173 import NOW, build  # noqa: E402


class TheSetting(unittest.TestCase):
    def test_default_thirty_zero_allowed_out_of_range_ignored(self):
        self.assertEqual(sentinel_collab.settings({})["deadline_s"], 30)
        self.assertEqual(sentinel_collab.settings({"sentinels": {"collab": {"deadline_s": 0}}})["deadline_s"], 0)
        self.assertEqual(sentinel_collab.settings({"sentinels": {"collab": {"deadline_s": 9999}}})["deadline_s"], 30)


class TheRound(unittest.TestCase):
    def test_no_time_left_starts_nothing_and_names_the_repositories(self):
        sentinel, fake, _ = build(self, {}, repos=("r1", "r2", "r3"))
        with mock.patch.object(sentinel_base, "expired", return_value=True):
            sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertTrue(status["round_cut"])
        self.assertEqual(status["unchecked"], ["r1", "r2", "r3"])
        self.assertEqual(status["repos_checked"], 0)

    def test_with_time_the_round_reads_them_all(self):
        sentinel, fake, _ = build(self, {}, repos=("r1", "r2"))
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertFalse(status["round_cut"])
        self.assertEqual(status["unchecked"], [])
        self.assertEqual(status["repos_checked"], 2)

    def test_the_next_round_goes_on_where_the_last_stopped(self):
        sentinel, fake, _ = build(self, {}, repos=("r1", "r2", "r3"))
        answers = iter([False, True, True])
        with mock.patch.object(sentinel_base, "expired", side_effect=lambda d: next(answers, True)):
            sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["repos_checked"], 1)
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_status()["repos_checked"], 3)
        self.assertEqual(sentinel.get_status()["unchecked"], [])


if __name__ == "__main__":
    unittest.main()
