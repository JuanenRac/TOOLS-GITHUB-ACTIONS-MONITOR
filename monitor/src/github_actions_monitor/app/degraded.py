# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A counter of the failures that the monitor swallows on purpose. Some errors must never stop the monitor (a closed tab, a notification channel that is down, a worker that breaks); they
used to disappear. Now each one is counted by its origin and the last few are kept (the kind of error and a cleaned, short text, never a token), so `--doctor` and the page can show
that the monitor is working in a degraded way. Noting a failure never raises and never changes what the caller does."""
import json
from github_actions_monitor.security import private_io
import logging
import os
import re
import sys
import threading
import time
import traceback

LOG = logging.getLogger("monitor.degraded")
LOG.addHandler(logging.NullHandler())
LOCK = threading.Lock()
COUNTS = {}
RECENT = []
MAX_ORIGINS = 200
MAX_RECENT = 30
FILE = {"path": None, "saved": 0.0}      # where this process keeps its counters for `--doctor` (set by attach); None = memory only
SAVE_EVERY = 5.0
WRITER = {"fn": None}      # a function that appends one line to the log of the monitor (set by actions_monitor); None = the line goes only to the console
LINE_FULL = 20             # the first lines of each failure are all written; after that, one in LINE_EVERY (a failure that repeats every cycle does not fill the log)
LINE_EVERY = 25
_SEEN = {}
_SECRET = re.compile(r"(?i)(gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,}|bearer\s+\S+|(?:token|secret|password|key)=\S+)")


def clean(text):
    return _SECRET.sub("***", str(text))[:120]


def where(error):
    """"file.py:line in function" of the last frame of this package that the error went through, or "" (no traceback, or it never touched the code of the monitor)."""
    try:
        frames = traceback.extract_tb(error.__traceback__) if isinstance(error, BaseException) else []
        mine = [f for f in frames if "github_actions_monitor" in f.filename.replace("\\", "/")] or frames
        return f"{os.path.basename(mine[-1].filename)}:{mine[-1].lineno} in {mine[-1].name}" if mine else ""
    except Exception:   # noqa: BLE001
        return ""


def set_writer(function):
    WRITER["fn"] = function


def note(origin, error=None):
    """Counts one swallowed failure of `origin` (a short fixed name such as "actlocal.worker") and logs one structured line. Safe to call from anywhere."""
    try:
        name = re.sub(r"[^A-Za-z0-9_.-]", "", str(origin))[:60] or "unknown"
        kind = type(error).__name__ if isinstance(error, BaseException) else (str(error)[:40] if error else "")
        with LOCK:
            if name not in COUNTS and len(COUNTS) >= MAX_ORIGINS:
                name = "other"
            COUNTS[name] = COUNTS.get(name, 0) + 1
            place = where(error)
            RECENT.append({"origin": name, "kind": kind, "text": clean(error) if error else "", "where": place, "at": int(time.time())})
            del RECENT[:-MAX_RECENT]
            key = (name, kind, place)
            _SEEN[key] = _SEEN.get(key, 0) + 1
            write = _SEEN[key] <= LINE_FULL or _SEEN[key] % LINE_EVERY == 0
        LOG.warning("degraded origin=%s kind=%s count=%d", name, kind, COUNTS[name])
        if write and WRITER["fn"] is not None:      # always in the log file too: what failed, where and with which (cleaned) message, never a token
            WRITER["fn"](f"degraded origin={name} kind={kind} where={place or '-'} text={clean(error) if error else '-'} count={COUNTS[name]}")
        save()
    except Exception:   # noqa: BLE001 - the counter itself must never be a new reason to fail
        pass


def snapshot():
    """{"total", "origins": {origin: n}, "recent": [...]}; copies, safe to serialise."""
    with LOCK:
        return {"total": sum(COUNTS.values()), "origins": dict(COUNTS), "recent": [dict(r) for r in RECENT]}


def reset():
    with LOCK:
        COUNTS.clear()
        _SEEN.clear()
        del RECENT[:]


def attach(path):
    """Keeps the counters of this process in `path` (a small JSON file next to the monitor) so that `--doctor`, which runs in another process, can read them. Starts from zero at each start."""
    FILE["path"], FILE["saved"] = path, 0.0
    if not any(getattr(h, "_degraded", False) for h in LOG.handlers):
        handler = logging.StreamHandler(sys.stderr)      # one structured line per swallowed failure: "degraded origin=... kind=... count=..."
        handler._degraded = True
        LOG.addHandler(handler)
    save(force=True)


def save(force=False):
    path = FILE["path"]
    if path is None or (not force and time.time() - FILE["saved"] < SAVE_EVERY):
        return
    FILE["saved"] = time.time()
    try:
        tmp = f"{path}.tmp"
        private_io.write_tmp(tmp, json.dumps({"total": sum(COUNTS.values()), "origins": dict(COUNTS), "at": int(time.time())}))
        os.replace(tmp, path)
    except (OSError, ValueError):
        pass      # the counter is a courtesy: a folder that cannot be written is not one more failure to report


def read(folder):
    """(total, {origin: n}) of the files that the running monitors keep in `folder` (full and lite), or (0, {}) when there are none."""
    total, origins = 0, {}
    for name in ("degraded.json", "degraded_lite.json"):
        try:
            with open(os.path.join(str(folder), name), encoding="utf-8") as handle:
                data = json.load(handle)
            total += int(data.get("total", 0))
            for key, value in (data.get("origins") or {}).items():
                origins[str(key)[:60]] = origins.get(str(key)[:60], 0) + int(value)
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return total, origins
