# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Locks for the file backend (standard library only).

  path_lock(path)       one re-entrant lock per file inside this process: whoever appends to the feed and whoever rewrites it (the purge) take the same one, so a line is never lost
  process_lock(path)    a context manager that also excludes OTHER processes through a lock file created exclusively (the global records, read-modify-write); a lock file left by a process that
                        died is taken over at once (the file holds the number of its process) and, when that cannot be known, after STALE seconds (MONITOR_LOCK_STALE overrides it)
"""
import contextlib
import logging
import os
import threading
import time
from pathlib import Path

STALE = 30.0
RESCUED = []      # the lock files taken over from a process that was gone: (name, pid); read by the tests and by the doctor
_LOCKS = {}
_GUARD = threading.Lock()
_LOG = logging.getLogger("github_actions_monitor.locks")


def stale_seconds():
    try:
        return max(1.0, float(os.environ.get("MONITOR_LOCK_STALE", "") or STALE))
    except ValueError:
        return STALE


def pid_alive(pid):
    """True / False when it can be known whether the process exists, None when it cannot (then only the age of the lock file counts)."""
    if pid <= 0:
        return None
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(0x1000, False, pid)      # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                error = ctypes.get_last_error() or kernel.GetLastError()
                return False if error == 87 else (True if error == 5 else None)      # invalid parameter = no such process; access denied = it exists
            try:
                code = ctypes.c_ulong()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return None
                return code.value == 259      # STILL_ACTIVE
            finally:
                kernel.CloseHandle(handle)
        except Exception:      # noqa: BLE001 - not knowing is allowed
            return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


MIN_AGE = 1.0      # a lock younger than this is not opened to read its pid: a live owner lets go of it in milliseconds, and on Windows a file that is open for reading cannot be deleted by its owner


EMPTY_AFTER = 3.0      # a lock file that is still empty after this long: its writer died between creating it and writing its number (a live one writes it in microseconds)


def _owner_gone(lock_file):
    """The pid written in the lock file, when its process is gone (None when it is alive, unknown, not written yet or too recent to look at). An empty file that is older than `EMPTY_AFTER`
    belongs to a writer that died before it wrote its number: it answers 0 (no process), so that it is taken over at once and not after STALE seconds."""
    try:
        age = time.time() - lock_file.stat().st_mtime
        if age < MIN_AGE:
            return None
        text = lock_file.read_text(encoding="ascii", errors="ignore").strip()
        if not text and age >= EMPTY_AFTER:
            return 0
        pid = int(text)
    except (OSError, ValueError):
        return None
    return pid if pid_alive(pid) is False else None


def path_lock(path):
    key = os.path.normcase(os.path.abspath(str(path)))
    with _GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = _LOCKS[key] = threading.RLock()
        return lock


def release(lock_file, attempts=100, pause=0.01):
    """Deletes the lock file of the owner. On Windows the delete is refused for a moment while another process has the file open (a reader); it is tried again for about a second (100 x 10 ms)."""
    for attempt in range(attempts):
        try:
            lock_file.unlink()
            return True
        except FileNotFoundError:
            return True
        except OSError:
            if attempt + 1 < attempts:
                time.sleep(pause)
    return False


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
            except (FileExistsError, PermissionError):      # Windows answers "access denied" while another process is deleting the lock file: wait and try again
                try:
                    gone = _owner_gone(lock_file)
                    if gone is not None or time.time() - lock_file.stat().st_mtime > stale_seconds():
                        if gone is not None and _owner_gone(lock_file) != gone:      # another process took it over between the two looks: leave its lock alone
                            continue
                        lock_file.unlink()
                        if gone is not None:
                            RESCUED.append((lock_file.name, gone))
                            del RESCUED[:-50]
                            _LOG.warning("lock %s taken over: the process %s that held it is gone", lock_file.name, gone)
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
            release(lock_file)
