# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Locks for the file backend (standard library only).

  path_lock(path)       one re-entrant lock per file inside this process: whoever appends to the feed and whoever rewrites it (the purge) take the same one, so a line is never lost
  process_lock(path)    a context manager that also excludes OTHER processes through a lock file created exclusively (the global records, read-modify-write); a lock file left by a process that
                        died is taken over after STALE seconds
"""
import contextlib
import os
import threading
import time
from pathlib import Path

STALE = 30.0
_LOCKS = {}
_GUARD = threading.Lock()


def path_lock(path):
    key = os.path.normcase(os.path.abspath(str(path)))
    with _GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = _LOCKS[key] = threading.RLock()
        return lock


@contextlib.contextmanager
def process_lock(path, timeout=10.0):
    """Excludes other threads and other processes while the block runs. Raises TimeoutError when the lock cannot be taken in `timeout` seconds."""
    lock_file = Path(str(path) + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with path_lock(path):
        deadline = time.monotonic() + timeout
        fd = None
        while fd is None:
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("ascii"))
            except FileExistsError:
                try:
                    if time.time() - lock_file.stat().st_mtime > STALE:
                        lock_file.unlink()
                        continue
                except OSError:
                    continue
                if time.monotonic() > deadline:
                    raise TimeoutError(str(lock_file.name))
                time.sleep(0.02)
        try:
            yield
        finally:
            os.close(fd)
            try:
                lock_file.unlink()
            except OSError:
                pass
