# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A writer killed between creating its lock file and writing its process number leaves an EMPTY lock file. Nobody could tell whose it was, so the next writer waited for the age limit (30 s),
longer than its own wait (10 s), and failed (seen on macOS, where a loaded runner makes that window wide). An empty file older than a few seconds is now taken over at once; a recent one,
one with the number of a live process and one with the number of a dead process keep their behaviour."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
import _testenv  # noqa: F401,E402
from github_actions_monitor.storage import locks  # noqa: E402


def old(lock_file, seconds):
    stamp = time.time() - seconds
    os.utime(lock_file, (stamp, stamp))


class EmptyLockFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "feed.jsonl"
        self.lock = Path(str(self.target) + ".lock")
        locks.RESCUED.clear()

    def test_an_old_empty_lock_is_taken_over_at_once(self):
        self.lock.write_bytes(b"")
        old(self.lock, 10)
        started = time.monotonic()
        with locks.process_lock(self.target, timeout=5):
            self.assertTrue(self.lock.exists())
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(locks.RESCUED, [(self.lock.name, 0)])
        self.assertFalse(self.lock.exists())

    def test_a_recent_empty_lock_is_left_alone(self):
        self.lock.write_bytes(b"")      # its writer may be about to write its number
        with self.assertRaises(TimeoutError):
            with locks.process_lock(self.target, timeout=0.4):
                self.fail("the lock of a writer that may be alive was taken")
        self.assertEqual(locks.RESCUED, [])

    def test_the_number_of_a_live_process_is_respected_and_a_dead_one_is_taken(self):
        self.lock.write_bytes(str(os.getpid()).encode("ascii"))
        old(self.lock, 10)
        with self.assertRaises(TimeoutError):
            with locks.process_lock(self.target, timeout=0.4):
                self.fail("the lock of a live process was taken")
        self.lock.write_bytes(b"4194301")      # a number no process has
        old(self.lock, 10)
        self.assertIs(locks.pid_alive(4194301), False)
        with locks.process_lock(self.target, timeout=5):
            pass
        self.assertEqual(locks.RESCUED, [(self.lock.name, 4194301)])

    def test_the_wait_of_a_writer_is_longer_than_the_age_after_which_an_empty_lock_is_dead(self):
        self.assertLess(locks.EMPTY_AFTER, 10.0)      # the default wait of process_lock
        self.assertGreater(locks.EMPTY_AFTER, locks.MIN_AGE)


if __name__ == "__main__":
    unittest.main()
