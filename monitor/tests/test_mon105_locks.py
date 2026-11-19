# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A lock file its owner could not delete (Windows refuses while a reader has it open) is marked as released, so the next process takes it over after a moment and not after ten stale periods;
and the wait of os_lock on Windows is never shorter than the floor when the caller asked for a real wait."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.storage import locks


class ReleasedMarker(unittest.TestCase):
    def test_a_lock_file_that_could_not_be_deleted_is_marked_and_taken_over(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            target = Path(tmp) / "records.json"
            lock_file = Path(str(target) + ".lock")
            with mock.patch.object(locks, "release", return_value=False):
                with locks.process_lock(target, timeout=2.0):
                    pass
            self.assertEqual(lock_file.read_text(encoding="ascii"), str(locks.RELEASED))
            young = locks._owner_gone(lock_file)
            self.assertIsNone(young, "a mark younger than MIN_AGE is not opened")
            old = time.time() - 5
            os.utime(lock_file, (old, old))
            self.assertEqual(locks._owner_gone(lock_file), locks.RELEASED)
            locks.RESCUED.clear()
            started = time.monotonic()
            with locks.process_lock(target, timeout=3.0):
                pass
            self.assertLess(time.monotonic() - started, 2.0)
            self.assertEqual(locks.RESCUED[-1][0], "records.json.lock")
            self.assertFalse(lock_file.exists())

    def test_a_lock_of_a_live_owner_is_not_mistaken_for_a_released_one(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            lock_file = Path(tmp) / "x.lock"
            lock_file.write_text(str(os.getpid()), encoding="ascii")
            old = time.time() - 5
            os.utime(lock_file, (old, old))
            self.assertIsNone(locks._owner_gone(lock_file))


if __name__ == "__main__":
    unittest.main()
