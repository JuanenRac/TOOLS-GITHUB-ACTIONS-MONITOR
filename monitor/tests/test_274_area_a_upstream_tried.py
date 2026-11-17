# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A fork that GitHub does not give back, or a request that fails as a whole, does not keep the follow-up of the original repositories busy: the forks that were tried are written down."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_250_upstream as t250  # noqa: E402
from github_actions_monitor.data_pipeline import upstream  # noqa: E402

NOW = 1_800_000_000.0
HOUR = 3600


def fetch_for(names_by_text, gone):
    """A GraphQL double: the forks in `gone` come back null (deleted, renamed, not visible), the others have a parent."""
    def fetch(text):
        answer = {}
        for number in range(8):
            marker = 'r%d:repository(owner:"o",name:"' % number
            if marker in text:
                name = text.split(marker)[1].split('"')[0]
                names_by_text.append(name)
                answer["r%d" % number] = None if name in gone else t250.node()
        return answer
    return fetch


class ForksThatDoNotAnswer(unittest.TestCase):
    def test_eight_forks_without_a_node_do_not_hold_the_turn_for_ever(self):
        gone = {"aa-gone-%d" % n for n in range(8)}
        forks = sorted(gone) + ["fork-%02d" % n for n in range(40)]
        cfg = t250.on()
        store, asked, now = {}, [], NOW
        for _ in range(24 * 6):      # a day at the fastest pace
            names = upstream.pick_due(forks, store, now, cfg, 0)
            if names:
                upstream.read(fetch_for(asked, gone), "o", names, now, store)
            now += HOUR / 6
        healthy = [f for f in forks if f not in gone]
        self.assertTrue(all((store.get(f) or {}).get("parent") for f in healthy), "every healthy fork was read")
        self.assertTrue(all((store.get(f) or {}).get("unreadable") for f in gone))
        self.assertEqual(sorted(set(asked)), sorted(forks))

    def test_the_panel_tells_a_fork_that_cannot_be_read_from_one_not_read_yet(self):
        cfg = t250.on()
        store = {}
        upstream.read(fetch_for([], {"a-gone"}), "o", ["a-gone"], NOW, store)
        picture = upstream.build(store, ["a-gone", "b-new"], cfg, NOW)
        self.assertEqual((picture["unread"], picture["unreadable"], picture["tracked"]), (1, 1, 0))

    def test_a_request_that_fails_is_written_down_and_the_next_turn_takes_other_forks(self):
        forks = ["f%02d" % n for n in range(20)]
        cfg = t250.on()
        store, now = {}, NOW
        first = upstream.pick_due(forks, store, now, cfg, 0)
        upstream.mark_tried(store, first, now)
        second = upstream.pick_due(forks, store, now + 600, cfg, 0)
        self.assertFalse(set(first) & set(second))
        self.assertTrue(all(store[f]["unreadable"] for f in first))
        store["f19"] = {"parent": "x/y", "at": 5.0}
        upstream.mark_tried(store, ["f19"], now)
        self.assertEqual((store["f19"]["parent"], store["f19"]["at"]), ("x/y", now), "what was read is kept")


if __name__ == "__main__":
    unittest.main()
