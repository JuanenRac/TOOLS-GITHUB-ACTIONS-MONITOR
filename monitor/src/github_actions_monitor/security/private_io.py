# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Files of the monitor that only their owner may read (1.7.6).

The state of the monitor (silences, events, the feed for AIs, caches, the settings) can name repositories, workflows and short error messages of your CI. With a lax `umask` a plain
`write_text` leaves such a file readable by every other user of the computer. Every state file is created here with mode 0600 (and the folders this code creates with 0700):

    write_private(path, text)        replace the file (atomic: a temporary file next to it, then os.replace)
    write_tmp(tmp, text)             write a temporary file of the callers that do their own os.replace
    open_append(path)                append (text, UTF-8, "\\n"); the file is created with 0600
    private_dir(path)                create a folder (and its parents) with 0700

On Windows `os.chmod` only knows the read-only flag and the folders inherit the permissions of their parent, so there the mode cannot be enforced from here: the helpers do the same work and
never fail because of it (use the folder permissions of your account to keep other users out). Nothing in this module reads or sends anything.
"""
import itertools
import os
import threading
import time
from pathlib import Path

FILE_MODE = 0o600
DIR_MODE = 0o700
_BINARY = getattr(os, "O_BINARY", 0)
#: how long a replace that the system refuses (another process, or an antivirus, holds the file for a moment on Windows) is tried again, and the first wait between tries (it doubles up to the cap)
REPLACE_RETRY_SECONDS = 2.0
REPLACE_FIRST_WAIT = 0.005
REPLACE_WAIT_CAP = 0.1
_TMP_COUNTER = itertools.count()


def _fix_mode(path, mode):
    try:
        os.chmod(path, mode)
    except OSError:      # Windows, a file system without modes: nothing more to do
        pass


def _make_parent(path):
    """A file of config/, data/, logs/ or ai/ can be written before those folders exist (a fresh install, a test that does not start the monitor); any other folder must exist already."""
    from github_actions_monitor.util import paths
    if paths.is_own(path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_tmp(tmp, text):
    """Writes `text` (str or bytes) to `tmp`, creating it with mode 0600 and tightening one that already existed."""
    _make_parent(tmp)
    data = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | _BINARY, FILE_MODE)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    _fix_mode(tmp, FILE_MODE)


def unique_tmp(path):
    """A temporary name next to `path` that no other process or thread uses (process id, thread id, a counter): two writers of the same file never share their temporary file."""
    path = Path(path)
    return path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{next(_TMP_COUNTER)}.tmp")


def replace_with_retry(tmp, path):
    """`os.replace(tmp, path)`; a replace refused with PermissionError or FileNotFoundError (transient on Windows while another process has the file open) is tried again for REPLACE_RETRY_SECONDS.
    When it still fails the temporary file is removed and the last error is raised (an OSError, like any failed write)."""
    deadline = time.monotonic() + REPLACE_RETRY_SECONDS
    wait = REPLACE_FIRST_WAIT
    while True:
        try:
            os.replace(tmp, path)
            return
        except (PermissionError, FileNotFoundError):
            if time.monotonic() >= deadline or not Path(tmp).exists():
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
            time.sleep(wait)
            wait = min(wait * 2, REPLACE_WAIT_CAP)


def read_text_with_retry(path):
    """The text of `path` (UTF-8). A read refused with PermissionError (on Windows, while another process is replacing the file) is tried again for REPLACE_RETRY_SECONDS, so that a reader never
    takes the moment of a replace for a file it may not read; a missing file or any other error is raised at once."""
    deadline = time.monotonic() + REPLACE_RETRY_SECONDS
    wait = REPLACE_FIRST_WAIT
    while True:
        try:
            return Path(path).read_text(encoding="utf-8")
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(wait)
            wait = min(wait * 2, REPLACE_WAIT_CAP)


def write_private(path, text):
    """Replaces `path` with `text` through a temporary file, so a crash never leaves half a file. The result has mode 0600."""
    path = Path(path)
    tmp = unique_tmp(path)
    write_tmp(tmp, text)
    replace_with_retry(tmp, path)
    _fix_mode(path, FILE_MODE)


def open_append(path):
    """A text file object (UTF-8, "\\n") open for appending; a file that did not exist is created with mode 0600."""
    _make_parent(path)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND | _BINARY, FILE_MODE)
    _fix_mode(path, FILE_MODE)
    return os.fdopen(fd, "a", encoding="utf-8", newline="\n")


def private_dir(path):
    """Creates the folder with mode 0700 (the parents that are missing too). A folder that already exists is left as it is: it may belong to something else."""
    path = Path(path)
    missing = [p for p in [path, *path.parents] if not p.exists()]
    path.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
    for created in missing:
        _fix_mode(created, DIR_MODE)      # mkdir(mode=) is filtered by the umask; the chmod is not
