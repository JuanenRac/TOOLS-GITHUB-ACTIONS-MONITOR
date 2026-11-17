# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The exact edges of rules that only had tests in the middle: the day on which a fork still counts as maintained, the day on which a queued run becomes a ghost, the entry of the ETag cache that has just
expired, and the cases of the lock between processes in which the owner cannot be known (an unknown process is not a dead one, a lock taken over by someone else in the meantime is left alone, a refused creation
is a busy lock)."""
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import etagcache, fork_ci, stuckrule  # noqa: E402
from github_actions_monitor.storage import locks  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def stamp(seconds_ago):
    return datetime.fromtimestamp(NOW - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TheDayOfAFork(unittest.TestCase):
    def own(self, seconds_ago):
        return {"event": "push", "fork": False, "started": stamp(seconds_ago), "path": "ci.yml"}

    def test_a_run_exactly_on_the_edge_still_counts(self):
        self.assertTrue(fork_ci.has_own_ci([self.own(90 * DAY)], False, NOW, 90))
        self.assertFalse(fork_ci.has_own_ci([self.own(90 * DAY + 1)], False, NOW, 90))

    def test_a_full_list_that_starts_exactly_on_the_edge_cannot_be_told(self):
        self.assertIsNone(fork_ci.has_own_ci([{"event": "schedule", "fork": False, "started": stamp(90 * DAY)}], True, NOW, 90))
        self.assertFalse(fork_ci.has_own_ci([{"event": "schedule", "fork": False, "started": stamp(90 * DAY + 1)}], True, NOW, 90))


class TheDayOfAGhost(unittest.TestCase):
    cfg = {"ghost_enabled": True, "ghost_days": 7}

    def queued(self, seconds_ago):
        return {"status": "queued", "started": stamp(seconds_ago), "attempt": 1}

    def test_exactly_seven_days_is_still_waiting_and_a_second_more_is_a_ghost(self):
        self.assertFalse(stuckrule.is_ghost(self.queued(7 * DAY), self.cfg, NOW))
        self.assertTrue(stuckrule.is_ghost(self.queued(7 * DAY + 60), self.cfg, NOW))

    def test_a_re_run_is_never_a_ghost(self):
        run = self.queued(30 * DAY)
        run["attempt"] = 2
        self.assertFalse(stuckrule.is_ghost(run, self.cfg, NOW))


class TheEtagThatJustExpired(unittest.TestCase):
    def cache(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cache = etagcache.EtagCache(Path(tmp.name) / "etag.json", ttl_hours=1)
        cache.entries["repos/a/b/actions/runs"] = {"etag": 'W/"abc"', "data": {"x": 1}, "at": NOW}
        return cache

    def test_an_entry_on_the_edge_is_used_and_one_second_older_is_read_again(self):
        cache = self.cache()
        self.assertEqual(cache.etag_for("repos/a/b/actions/runs", NOW + 3600), 'W/"abc"')
        self.assertIsNone(cache.etag_for("repos/a/b/actions/runs", NOW + 3601))

    def test_an_expired_entry_is_not_sent_as_if_none_match(self):
        cache = self.cache()
        sent = []

        def run(args):
            sent.append(args)
            return 0, 'HTTP/2 200 OK\nEtag: W/"new"\n\n{"x": 2}', ""
        data, status = cache.fetch("repos/a/b/actions/runs", run, now=NOW + 7200)
        self.assertEqual((status, data), ("200", {"x": 2}))
        self.assertFalse(any("If-None-Match" in " ".join(a) for a in sent))


class TheLockWhoseOwnerIsUnknown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "doc.json"
        self.lock_file = Path(str(self.target) + ".lock")

    def old_lock(self, pid, age=5):
        self.lock_file.write_text(str(pid), encoding="ascii")
        past = time.time() - age
        os.utime(self.lock_file, (past, past))

    def test_a_process_that_cannot_be_looked_up_is_not_taken_for_dead(self):
        self.old_lock(4242424)
        with mock.patch.object(locks, "pid_alive", return_value=None):
            with self.assertRaises(TimeoutError):
                with locks.process_lock(self.target, 0.4):
                    self.fail("a lock whose owner is unknown was taken")
        self.assertTrue(self.lock_file.exists())

    def test_a_lock_that_someone_else_took_in_the_meantime_is_left_alone(self):
        self.old_lock(4242424)
        looks = iter([4242424] + [None] * 10_000)
        with mock.patch.object(locks, "_owner_gone", side_effect=lambda f: next(looks)):
            with self.assertRaises(TimeoutError):
                with locks.process_lock(self.target, 0.4):
                    self.fail("the lock was taken over after the second look said that another process had it")
        self.assertTrue(self.lock_file.exists())

    def test_a_refused_creation_counts_as_a_busy_lock_and_is_tried_again(self):
        real = os.open
        refused = []

        def open_once_refused(path, *args, **kwargs):
            if str(path).endswith(".lock") and not refused:
                refused.append(1)
                raise PermissionError("another process is deleting the lock file")
            return real(path, *args, **kwargs)
        with mock.patch.object(locks.os, "open", open_once_refused):
            with locks.process_lock(self.target, 2.0):
                pass
        self.assertEqual(refused, [1])


if __name__ == "__main__":
    unittest.main()
