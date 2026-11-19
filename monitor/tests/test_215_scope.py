# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Repositories left out by visibility, and the count of what each rule left out (discovery.hide = public, discovery.exclusions)."""
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.data_pipeline import discovery

ITEMS = [
    {"name": "a", "isPrivate": True}, {"name": "b", "isPrivate": False}, {"name": "c"},
    {"name": "d", "isPrivate": False, "isFork": True}, {"name": "e", "isArchived": True}, {"name": "f", "isEmpty": True, "isPrivate": True},
]


class ScopeTests(unittest.TestCase):
    def test_public_is_a_kind_that_can_be_hidden(self):
        self.assertEqual(discovery.settings({"discovery": {"hide": ["public", "nonsense"]}})["hide"], ["public"])

    def test_public_leaves_out_only_what_was_read_as_public(self):
        keep = discovery.lifecycle(ITEMS, {"hide": ["public"]})
        self.assertEqual(keep, ["a", "c", "f"])      # "c" has no visibility: not read, so never a reason

    def test_private_leaves_out_only_what_was_read_as_private(self):
        self.assertEqual(discovery.lifecycle(ITEMS, {"hide": ["private"]}), ["b", "c", "d"])

    def test_every_repository_left_out_is_counted_once_under_its_reason(self):
        counts = discovery.exclusions(ITEMS, {"hide": ["public", "empty"], "fork_policy": "skip"})
        self.assertEqual(counts, {"archived": 1, "empty": 1, "public": 2})
        self.assertEqual(sum(counts.values()), len(ITEMS) - len(discovery.lifecycle(ITEMS, {"hide": ["public", "empty"], "fork_policy": "skip"})))

    def test_nothing_hidden_counts_nothing_but_the_archived(self):
        self.assertEqual(discovery.exclusions(ITEMS, {}), {"archived": 1})

    def test_the_box_carries_the_counts(self):
        self.assertEqual(discovery.box("o", 3, 6, ["x"], {"public": 2})["excluded"], {"public": 2})
        self.assertEqual(discovery.box("o", 3, 6, [])["excluded"], {})


if __name__ == "__main__":
    unittest.main()
