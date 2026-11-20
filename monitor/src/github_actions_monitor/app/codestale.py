# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Is the code that runs the one that is on the disk? After an update the files change but a process that was already running keeps the old code in memory until it restarts. The monitor compares the
version it was started with with the version written in `tool_version.py` today and says so in `/api/health` (`code_stale`), in `monitor_cli.py status` (a reason to look at it) and in `--doctor`.
It reads one small file, caches the answer until that file changes and never raises. Standard library only."""
import re
from pathlib import Path

from github_actions_monitor import tool_version

_FILE = Path(tool_version.__file__).resolve()
_RE = re.compile(r'^TOOL_VERSION\s*=\s*"([^"]+)"', re.M)
_CACHE = {"stamp": None, "version": ""}


def disk_version(path=None):
    """The TOOL_VERSION written in the file today ('' when it cannot be read)."""
    target = Path(path) if path else _FILE
    try:
        stamp = (target.stat().st_mtime_ns, target.stat().st_size)
        if path is None and _CACHE["stamp"] == stamp:
            return _CACHE["version"]
        found = _RE.search(target.read_text(encoding="utf-8"))
        version = found.group(1) if found else ""
    except (OSError, ValueError):
        return ""
    if path is None:
        _CACHE.update(stamp=stamp, version=version)
    return version


def stale(running=None, path=None):
    """True when the file on the disk names another version than the one this process started with. False when the file cannot be read (nothing is claimed that is not known)."""
    running = running or tool_version.TOOL_VERSION
    found = disk_version(path)
    return bool(found) and found != running
