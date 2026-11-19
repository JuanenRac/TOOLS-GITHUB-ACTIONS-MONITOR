# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A round of the Security, Supply chain and Delivery sentinels has a time ceiling: past it no new repository is started, and the ones not reached are named as not checked."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.sentinels import sentinel_base, sentinel_delivery, sentinel_security, sentinel_supply  # noqa: E402
from test_191_sentinel import NOW, build, quiet_repo  # noqa: E402


class TheHelpers(unittest.TestCase):
    def test_zero_means_no_ceiling(self):
        self.assertIsNone(sentinel_base.round_deadline(0))
        self.assertFalse(sentinel_base.expired(None))

    def test_a_ceiling_expires(self):
        with mock.patch.object(sentinel_base.time, "monotonic", side_effect=[100.0, 129.0, 131.0]):
            deadline = sentinel_base.round_deadline(30)
            self.assertFalse(sentinel_base.expired(deadline))
            self.assertTrue(sentinel_base.expired(deadline))

    def test_unchecked_names_what_was_never_read_and_is_bounded(self):
        per_repo = {"a": {"scanned": 5}, "b": {}, "c": {"scanned": 0}}
        self.assertEqual(sentinel_base.unchecked(["a", "b", "c", "d"], per_repo), ["b", "c", "d"])
        self.assertEqual(len(sentinel_base.unchecked([f"r{n}" for n in range(100)], {})), 20)


class TheSettings(unittest.TestCase):
    def test_the_default_is_thirty_seconds_and_zero_is_allowed(self):
        for module in (sentinel_security, sentinel_supply, sentinel_delivery):
            self.assertEqual(module.settings({})["deadline_s"], 30)
            self.assertEqual(module.settings({"sentinels": {module.__name__.rsplit("_", 1)[1]: {"deadline_s": 0}}})["deadline_s"], 0)
            self.assertEqual(module.settings({"sentinels": {module.__name__.rsplit("_", 1)[1]: {"deadline_s": 9999}}})["deadline_s"], 30)


class InTheSecuritySentinel(unittest.TestCase):
    def test_a_round_with_no_time_left_starts_nothing_and_names_the_repositories(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2", "r3"))
        quiet_repo(fake)
        with mock.patch.object(sentinel_base, "expired", return_value=True):
            sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertTrue(status["round_cut"])
        self.assertEqual(status["unchecked"], ["r1", "r2", "r3"])
        self.assertEqual(status["repos_checked"], 0)
        self.assertEqual(fake.calls, [])

    def test_with_time_the_round_reads_them_all_and_nothing_is_unchecked(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2"))
        quiet_repo(fake)
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertFalse(status["round_cut"])
        self.assertEqual(status["unchecked"], [])
        self.assertEqual(status["repos_checked"], 2)

    def test_the_next_round_goes_on_where_the_last_stopped(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2", "r3"))
        quiet_repo(fake)
        answers = iter([False, True, True])      # the first repository is started, then the time is over
        with mock.patch.object(sentinel_base, "expired", side_effect=lambda d: next(answers, True)):
            sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["repos_checked"], 1)
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_status()["repos_checked"], 3)
        self.assertEqual(sentinel.get_status()["unchecked"], [])


if __name__ == "__main__":
    unittest.main()
