# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
import json
import tempfile
import unittest
import _testenv  # noqa: F401
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import events


def snap(reds=(), alerts=None, prs=(), rate=4000, loading=""):
    return {"enabled": True, "loading": loading, "rate": {"remaining": rate},
            "a1": {"stuck": []}, "a2": {"red": [{"repo": r, "workflow": w, "url": "u", "streak": 1, "since": "x"} for r, w in reds]},
            "a3": {"rows": [{"repo": r, "codeql": c, "dependabot": d, "secret": 0, "sev": {}} for r, (c, d) in (alerts or {}).items()]},
            "a4": {"dependabot": [{"repo": r} for r in prs]}}


class Feed(unittest.TestCase):
    def make(self, tmp):
        return events.Feed(Path(tmp) / "e.jsonl", Path(tmp) / "s.json")

    def test_first_look_only_sets_the_baseline_then_changes_are_announced(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed = self.make(tmp)
            self.assertEqual(feed.feed(snap(reds=[("A", "CI")], alerts={"A": (0, 0)})), [])
            events = feed.feed(snap(reds=[("A", "CI"), ("B", "CI")], alerts={"A": (2, 0)}, prs=["A"]))
            kinds = sorted(e["kind"] for e in events)
            self.assertEqual(kinds, ["alerts_up", "prs_up", "red_new"])
            events = feed.feed(snap(reds=[("B", "CI")], alerts={"A": (2, 0)}, prs=["A"]))
            self.assertEqual([e["kind"] for e in events], ["red_fixed"])
            lines = (Path(tmp) / "e.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(json.loads(lines[0])["owner"], "main")

    def test_nothing_is_said_while_loading_and_a_restart_does_not_flood(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed = self.make(tmp)
            feed.feed(snap(reds=[("A", "CI")]))
            self.assertEqual(self.make(tmp).feed(snap(reds=[("A", "CI")], loading="3/9")), [])
            again = self.make(tmp)   # restart: the state file remembers what was announced
            self.assertEqual([e["kind"] for e in again.feed(snap(reds=[("A", "CI")]))], ["loaded"])

    def test_eh3d_is_marked_and_low_rate_is_announced_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed = self.make(tmp)
            feed.feed(snap())
            events = feed.feed(snap(reds=[("EH3D-X", "CI")], rate=900))
            self.assertEqual(sorted((e["kind"], e["owner"]) for e in events), [("rate_low", "main"), ("red_new", "eh3d")])
            self.assertEqual(feed.feed(snap(reds=[("EH3D-X", "CI")], rate=800)), [])


if __name__ == "__main__":
    unittest.main()


class ReleaseDue(unittest.TestCase):
    def test_a_repo_reaching_two_entries_is_announced_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed = events.Feed(Path(tmp) / "e.jsonl", Path(tmp) / "s.json")
            base = snap()
            base["a5"] = {"candidates": [{"repo": "R", "entries": 1}], "pending_sign": []}
            feed.feed(base)
            base["a5"] = {"candidates": [{"repo": "R", "entries": 2}], "pending_sign": []}
            self.assertEqual([e["kind"] for e in feed.feed(base)], ["release_due"])
            base["a5"] = {"candidates": [{"repo": "R", "entries": 5}], "pending_sign": []}
            self.assertEqual(feed.feed(base), [])
