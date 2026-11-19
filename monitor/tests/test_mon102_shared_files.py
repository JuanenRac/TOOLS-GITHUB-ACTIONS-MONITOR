# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Several processes at once on the files they share (storage/locks.py): no update is lost when four processes read, change and write the same file under the lock of the operating system or under the lock
file; a process that dies while it holds the lock does not leave the file blocked; a lock that is held makes the others wait and, past their limit, fail with TimeoutError instead of hanging. Real
processes, deterministic counts, a few seconds."""
import json
import subprocess
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

SRC = str(HERE / "src")
CHILD = """
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
from github_actions_monitor.storage import locks
from pathlib import Path
mode, target = sys.argv[2], Path(sys.argv[3])
lock = locks.os_lock if sys.argv[4] == "os" else locks.process_lock
if mode == "count":
    for _ in range(int(sys.argv[5])):
        with lock(target, 60):
            data = json.loads(target.read_text(encoding="utf-8"))
            data["n"] += 1
            target.write_text(json.dumps(data), encoding="utf-8")
elif mode == "die":
    with lock(target, 10):
        Path(sys.argv[5]).write_text("held", encoding="ascii")
        os._exit(7)      # the process dies with the lock taken: no finally runs
elif mode == "hold":
    with lock(target, 10):
        Path(sys.argv[5]).write_text("held", encoding="ascii")
        time.sleep(float(sys.argv[6]))
"""


def child(mode, target, kind, *extra):
    return subprocess.Popen([sys.executable, "-I", "-c", CHILD, SRC, mode, str(target), kind, *map(str, extra)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def wait_for(path, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if path.is_file():
            return True
        time.sleep(0.02)
    return False


class NoUpdateIsLost(unittest.TestCase):
    def count(self, kind):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "shared.json"
            target.write_text(json.dumps({"n": 0}), encoding="utf-8")
            procs = [child("count", target, kind, 40) for _ in range(4)]
            errors = [p.communicate(timeout=120)[1].decode("utf-8", "replace") for p in procs]
            self.assertEqual([p.returncode for p in procs], [0, 0, 0, 0], errors)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["n"], 160)

    def test_four_processes_counting_under_the_lock_of_the_operating_system(self):
        self.count("os")

    def test_four_processes_counting_under_the_lock_file(self):
        self.count("file")


class ADeadWriter(unittest.TestCase):
    def test_the_lock_of_the_operating_system_is_free_the_moment_its_holder_dies(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "shared.json"
            marker = Path(tmp) / "held"
            holder = child("die", target, "os", marker)
            self.assertTrue(wait_for(marker))
            holder.communicate(timeout=30)
            self.assertEqual(holder.returncode, 7)
            started = time.monotonic()
            with locks.os_lock(target, 5.0):
                pass
            self.assertLess(time.monotonic() - started, 4.0)

    def test_the_lock_file_of_a_dead_process_is_taken_over_without_waiting_for_the_stale_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "shared.json"
            marker = Path(tmp) / "held"
            holder = child("die", target, "file", marker)
            self.assertTrue(wait_for(marker))
            holder.communicate(timeout=30)
            self.assertTrue(Path(str(target) + ".lock").is_file())      # what the dead process left
            before = len(locks.RESCUED)
            started = time.monotonic()
            with locks.process_lock(target, 20.0):
                pass
            self.assertLess(time.monotonic() - started, 15.0)      # the age of the file (a second) and not the thirty seconds of the stale time
            self.assertGreater(len(locks.RESCUED), before)


class ALockThatIsHeld(unittest.TestCase):
    def test_the_others_wait_then_fail_with_a_timeout_and_work_again_afterwards(self):
        for kind, lock in (("os", locks.os_lock), ("file", locks.process_lock)):
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "shared.json"
                marker = Path(tmp) / "held"
                holder = child("hold", target, kind, marker, 3.0)
                self.assertTrue(wait_for(marker), kind)
                started = time.monotonic()
                with self.assertRaises(TimeoutError, msg=kind):
                    with lock(target, 0.4):
                        pass
                self.assertLess(time.monotonic() - started, 2.5, kind)      # it gave up at its limit, it did not hang until the holder finished
                holder.communicate(timeout=30)
                with lock(target, 10.0):      # the holder let go: the file is usable again
                    pass


if __name__ == "__main__":
    unittest.main()
