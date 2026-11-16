# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A lock file left by a process that died is taken over at once, not after the stale time, and the writer killed INSIDE the lock is the case that proves it."""
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.storage import file_storage, locks

HERE = Path(__file__).resolve().parent.parent

HOLDER = textwrap.dedent("""
    import sys, time
    sys.path.insert(0, sys.argv[1])
    from github_actions_monitor.storage import locks
    with locks.process_lock(sys.argv[2]):
        print("inside", flush=True)
        time.sleep(120)
""")


def finished_pid():
    proc = subprocess.Popen([sys.executable, "-I", "-c", "pass"])
    proc.wait()
    return proc.pid


class LockRescue(unittest.TestCase):
    def test_a_lock_of_a_finished_process_is_taken_at_once(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            target = Path(tmp) / "records.json"
            pid = finished_pid()
            Path(str(target) + ".lock").write_text(str(pid), encoding="ascii")
            old = time.time() - 10
            os.utime(str(target) + ".lock", (old, old))
            locks.RESCUED.clear()
            started = time.monotonic()
            with locks.process_lock(target, timeout=2.0):
                pass
            self.assertLess(time.monotonic() - started, 1.5)
            self.assertEqual(locks.RESCUED[-1], ("records.json.lock", pid))
            self.assertFalse(Path(str(target) + ".lock").exists())

    def test_a_lock_that_is_a_moment_old_is_not_opened_to_read_its_owner(self):
        from unittest import mock
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            lock_file = Path(tmp) / "records.json.lock"
            lock_file.write_text("1", encoding="ascii")
            with mock.patch.object(Path, "read_text", side_effect=AssertionError("opened")):
                self.assertIsNone(locks._owner_gone(lock_file))

    def test_the_owner_tries_again_while_windows_refuses_to_delete_its_lock(self):
        from unittest import mock
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            lock_file = Path(tmp) / "records.json.lock"
            lock_file.write_text("1", encoding="ascii")
            real, calls = Path.unlink, {"n": 0}

            def refuse(path, *args, **kwargs):
                calls["n"] += 1
                if calls["n"] <= 30:
                    raise PermissionError(13, "in use")
                return real(path, *args, **kwargs)
            with mock.patch.object(Path, "unlink", refuse), mock.patch.object(locks.time, "sleep"):
                self.assertTrue(locks.release(lock_file))
            self.assertEqual(calls["n"], 31)
            self.assertFalse(lock_file.exists())
            with mock.patch.object(Path, "unlink", side_effect=PermissionError(13, "in use")), mock.patch.object(locks.time, "sleep"):
                self.assertFalse(locks.release(lock_file, attempts=5))

    def test_a_lock_of_a_live_process_is_respected(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            target = Path(tmp) / "records.json"
            Path(str(target) + ".lock").write_text(str(os.getppid() or os.getpid()), encoding="ascii")
            with self.assertRaises(TimeoutError):
                with locks.process_lock(target, timeout=0.3):
                    pass

    def test_a_lock_without_a_number_waits_for_the_stale_time(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            target = Path(tmp) / "records.json"
            Path(str(target) + ".lock").write_text("", encoding="ascii")
            with self.assertRaises(TimeoutError):
                with locks.process_lock(target, timeout=0.3):
                    pass

    def test_the_stale_time_can_be_changed(self):
        old = os.environ.get("MONITOR_LOCK_STALE")
        os.environ["MONITOR_LOCK_STALE"] = "7"
        try:
            self.assertEqual(locks.stale_seconds(), 7.0)
            os.environ["MONITOR_LOCK_STALE"] = "junk"
            self.assertEqual(locks.stale_seconds(), locks.STALE)
        finally:
            if old is None:
                os.environ.pop("MONITOR_LOCK_STALE", None)
            else:
                os.environ["MONITOR_LOCK_STALE"] = old

    def test_the_feed_recovers_when_the_writer_is_killed_inside_the_lock(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp) / "accounts"
            storage = file_storage.FileStorage(str(root), "accounts")
            try:
                storage.append_event("alpha", {"kind": "first"})
                feed = next(root.rglob("events_monitor.jsonl"))
                proc = subprocess.Popen([sys.executable, "-I", "-c", HOLDER, str(HERE / "src"), str(feed)], stdout=subprocess.PIPE, text=True)
                try:
                    self.assertEqual(proc.stdout.readline().strip(), "inside")      # the lock is taken: now it dies holding it
                finally:
                    proc.kill()
                    proc.wait(timeout=30)
                    proc.stdout.close()
                self.assertTrue(Path(str(feed) + ".lock").exists())
                started = time.monotonic()
                storage.append_event("alpha", {"kind": "after"})
                self.assertLess(time.monotonic() - started, 5.0)
                self.assertEqual([e["kind"] for e in storage.load_events("alpha", None, None)], ["first", "after"])
            finally:
                storage.close()


if __name__ == "__main__":
    unittest.main()
