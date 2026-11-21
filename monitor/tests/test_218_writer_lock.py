# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The writer lock is not kept by a pid that another program inherited, and it is let go when the monitor ends."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import ghactions  # noqa: E402

CONFIG = {"github_actions": {"enabled": True, "writer_lock": True}}


class WriterLock(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.dir.cleanup)
        self.lock = Path(self.dir.name) / "writer.lock"

    def test_a_pid_that_was_given_to_another_program_does_not_keep_the_lock(self):
        other = os.getppid()      # a live process that is not a monitor
        if not ghactions.process_started(other):
            self.skipTest("the start of a process cannot be read here")
        self.lock.write_text(f"{other} 1", encoding="ascii")      # written by a monitor that started at another time
        self.assertEqual(ghactions.writer_state(CONFIG, {}, self.lock), ("writer", ""))
        self.assertEqual(self.lock.read_text(encoding="ascii").split()[0], str(os.getpid()))

    def test_the_same_process_that_wrote_the_lock_still_holds_it(self):
        other = os.getppid()
        started = ghactions.process_started(other)
        if not started:
            self.skipTest("the start of a process cannot be read here")
        self.lock.write_text(f"{other} {started}", encoding="ascii")
        self.assertEqual(ghactions.writer_state(CONFIG, {}, self.lock), ("observer", "lock"))

    def test_an_old_lock_with_the_pid_only_keeps_working_as_before(self):
        self.lock.write_text(str(os.getppid()), encoding="ascii")
        self.assertEqual(ghactions.writer_state(CONFIG, {}, self.lock), ("observer", "lock"))

    def test_the_lock_of_a_dead_process_with_the_pid_of_this_one_is_taken_over(self):
        started = ghactions.process_started(os.getpid())
        if not started:
            self.skipTest("the start of a process cannot be read here")
        self.lock.write_text(f"{os.getpid()} 1", encoding="ascii")
        self.assertEqual(ghactions.writer_state(CONFIG, {}, self.lock), ("writer", ""))
        self.assertEqual(self.lock.read_text(encoding="ascii"), f"{os.getpid()} {started}")

    def test_the_file_goes_away_when_the_monitor_ends(self):
        self.assertEqual(ghactions.writer_state(CONFIG, {}, self.lock), ("writer", ""))
        self.assertTrue(self.lock.exists())
        ghactions.release_writer(self.lock)
        self.assertFalse(self.lock.exists())

    def test_the_lock_of_another_process_is_not_deleted_by_the_release(self):
        self.lock.write_text(str(os.getppid()), encoding="ascii")
        ghactions.release_writer(self.lock)
        self.assertTrue(self.lock.exists())


if __name__ == "__main__":
    unittest.main()
