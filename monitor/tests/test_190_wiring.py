# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The pass of the score inside the refresh cycle: it runs in the Complete edition, never in Lite, and a failure of it is counted and never raised."""
import inspect
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, degraded  # noqa: E402
from github_actions_monitor.storage import file_storage  # noqa: E402


class FakeCollab:
    enabled = True

    def __init__(self, loading=""):
        self.loading = loading

    def get_status(self):
        return {"loading": self.loading}

    def get_alerts(self):
        return [{"id": "collab.issue.stale:a/x:1", "created_at": "2026-11-10T00:00:00Z"}]


class FakeRegistry:
    def __init__(self, collab):
        self.collab = collab

    def get(self, name):
        return self.collab if name == "collab" else None


def runs(n=5):
    now = time.time()
    return [{"id": i, "repo": "a/x", "name": "ci", "status": "completed", "conclusion": "success", "seconds": 60, "started": now - i * 60} for i in range(1, n + 1)]


class Wiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = file_storage.FileStorage(Path(self.tmp.name))
        patch = mock.patch("github_actions_monitor.storage.runtime.process_storage", return_value=(self.storage, "alpha"))
        patch.start()
        self.addCleanup(patch.stop)
        self.old_lite = actions_monitor.LITE["on"]
        self.old_registry = actions_monitor.SENTINEL["registry"]
        self.addCleanup(lambda: (actions_monitor.LITE.update(on=self.old_lite), actions_monitor.SENTINEL.update(registry=self.old_registry)))
        actions_monitor.LITE["on"] = False

    def test_the_cycle_calls_the_pass_of_the_score(self):
        self.assertIn("score_tick(", inspect.getsource(actions_monitor.maintain))

    def test_a_pass_writes_the_snapshot_and_follows_the_collaboration_alerts(self):
        actions_monitor.SENTINEL["registry"] = FakeRegistry(FakeCollab())
        actions_monitor.score_tick({}, {"runs": runs()})
        self.assertEqual(len(self.storage.load_score_snapshots("alpha")), 1)
        self.assertIn("collab.issue.stale:a/x:1", self.storage.load_doc("alpha", "score_ledger")["collab"])

    def test_a_collaboration_sentinel_that_is_still_loading_is_not_read(self):
        actions_monitor.SENTINEL["registry"] = FakeRegistry(FakeCollab(loading="scanning"))
        actions_monitor.score_tick({}, {"runs": runs()})
        self.assertEqual(self.storage.load_doc("alpha", "score_ledger")["collab"], {})

    def test_lite_never_scores(self):
        actions_monitor.LITE["on"] = True
        actions_monitor.score_tick({}, {"runs": runs()})
        self.assertEqual(self.storage.load_score_snapshots("alpha"), [])

    def test_nothing_is_written_while_loading_or_offline(self):
        actions_monitor.score_tick({}, {"runs": runs(), "loading": True})
        actions_monitor.score_tick({}, {"runs": runs(), "offline": {"offline": True}})
        self.assertEqual(self.storage.load_score_snapshots("alpha"), [])

    def test_a_failure_is_counted_and_not_raised(self):
        before = degraded.COUNTS.get("score", 0)
        with mock.patch("github_actions_monitor.scoring.ledger.tick", side_effect=RuntimeError("boom")):
            actions_monitor.score_tick({}, {"runs": runs()})
        self.assertEqual(degraded.COUNTS.get("score", 0), before + 1)


if __name__ == "__main__":
    unittest.main()
