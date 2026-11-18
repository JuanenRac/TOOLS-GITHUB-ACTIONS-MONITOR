# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Locks for the file backend (standard library only).

  path_lock(path)       one re-entrant lock per file inside this process: whoever appends to the feed and whoever rewrites it (the purge) take the same one, so a line is never lost
  os_lock(path)         an exclusion between processes made by the operating system itself (msvcrt.locking on Windows, fcntl.flock elsewhere) on a side file: when the process that holds it dies, the system
                        lets it go at once, so there is never an orphan to rescue. For the files that are read, changed and written again by several processes (the store of the AI)
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


def _owner_gone(lock_file):
    """The pid written in the lock file, when its process is gone (None when it is alive, unknown, not written yet or too recent to look at)."""
    try:
        if time.time() - lock_file.stat().st_mtime < MIN_AGE:
            return None
        text = lock_file.read_text(encoding="ascii", errors="ignore").strip()
        pid = int(text)
    except (OSError, ValueError):
        return None
    return pid if pid_alive(pid) is False else None


LIVE_FACTOR = 10      # a lock older than STALE whose owner is still alive is left alone until it is this many times older (a slow owner is not robbed; a pid that was reused by another program does not block for ever)


def _owner_alive(lock_file):
    try:
        return pid_alive(int(lock_file.read_text(encoding="ascii", errors="ignore").strip())) is True
    except (OSError, ValueError):
        return False


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


def _try_lock(fd):
    """One try to take the lock of the operating system on the first byte of the file; OSError when somebody else holds it."""
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(fd):
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass      # closing the descriptor lets go of it anyway


@contextlib.contextmanager
def os_lock(path, timeout=10.0):
    """Excludes other threads and other processes while the block runs, with a lock of the operating system on `<path>.oslock`. Raises TimeoutError when it cannot be taken in `timeout` seconds."""
    lock_file = Path(str(path) + ".oslock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with path_lock(path):
        fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)      # private like every state file
        try:
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")      # Windows locks a byte that exists
            deadline = time.monotonic() + timeout
            while True:
                try:
                    _try_lock(fd)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(lock_file.name) from None
                    time.sleep(0.02)
            try:
                yield
            finally:
                _unlock(fd)
        finally:
            os.close(fd)


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
                    age = time.time() - lock_file.stat().st_mtime
                    old = age > stale_seconds() and (gone is not None or age > stale_seconds() * LIVE_FACTOR or not _owner_alive(lock_file))
                    if gone is not None or old:
                        if gone is not None and _owner_gone(lock_file) != gone:      # another process took it over between the two looks: leave its lock alone
                            continue
                        try:
                            lock_file.unlink()
                        except OSError:      # Windows refuses to delete a file its owner has open: the owner is alive, so wait (and respect the deadline) instead of trying again at full speed
                            pass
                        else:
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
