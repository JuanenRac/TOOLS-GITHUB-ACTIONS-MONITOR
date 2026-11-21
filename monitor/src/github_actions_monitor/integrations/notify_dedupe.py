# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Do not repeat a notification (`notify.dedupe_ledger`, OFF by default).

A notification is identified by a LABEL: the kind of the event plus the repository and the workflow it is about (the link of the run when it has one is part of it, so a new run of the same
workflow is a new notification). The ledger remembers the labels that already left, in memory and in a small file of the state folder, so the same event is not sent again

  * when the page is reloaded or the same event is read again by the next cycle,
  * after the monitor restarts (the file survives it),
  * when a pipeline leaves the window for a while and comes back (a label stays remembered for `notify.dedupe_hours`).

`notify.max_event_age_hours` (0 = off) also drops an event whose own evidence is older than that: the news of something that happened days ago is not news. Nothing here reads GitHub; the file holds
only hashes and times (no repository name, no text).
"""
import hashlib
import json
import threading
import time

from github_actions_monitor.util import paths

FILE_NAME = "notify_ledger.json"
LEDGER_FILE = paths.place("notify_ledger.json")      # moved into the folder of each account by accounts.STATE_FILES
MAX_ENTRIES = 5000
DEFAULTS = {"dedupe_ledger": False, "dedupe_hours": 24, "max_event_age_hours": 0}
_lock = threading.Lock()
_state = {"labels": {}, "path": "default", "loaded": False, "dropped": 0, "stale": 0}


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    cfg = config.get("notify") if isinstance(config, dict) and isinstance(config.get("notify"), dict) else {}
    return {"dedupe_ledger": cfg.get("dedupe_ledger") is True, "dedupe_hours": _int(cfg.get("dedupe_hours"), 1, 720, DEFAULTS["dedupe_hours"]),
            "max_event_age_hours": _int(cfg.get("max_event_age_hours"), 0, 8760, DEFAULTS["max_event_age_hours"])}


def label(event):
    """The label of an event: a hash of kind, repository, workflow and link (never the text, which may carry a time or a count)."""
    parts = [str(event.get("kind") or event.get("code") or ""), str(event.get("repo") or ""), str(event.get("workflow") or ""), str(event.get("url") or "")]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]


def reset(path="default"):
    """Forgets what is held in memory. `path` = the file of the ledger ("default" = LEDGER_FILE, None = memory only, as the tests ask)."""
    with _lock:
        _state.update({"labels": {}, "path": str(path) if path else None, "loaded": False, "dropped": 0, "stale": 0})


def _path():
    return str(LEDGER_FILE) if _state["path"] == "default" else _state["path"]


def _load():
    if _state["loaded"]:
        return
    _state["loaded"] = True
    if not _path():
        return
    try:
        with open(_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("labels"), dict):
            _state["labels"] = {k: float(v) for k, v in data["labels"].items() if isinstance(k, str) and isinstance(v, (int, float))}
    except (OSError, ValueError):
        _state["labels"] = {}


def _save():
    if not _path():
        return
    try:
        from github_actions_monitor.security import private_io
        private_io.write_private(_path(), json.dumps({"format": 1, "labels": _state["labels"]}, separators=(",", ":")))
    except OSError:
        pass      # a folder that cannot be written still has the memory


def _event_age_hours(event, now):
    stamp = event.get("at") or event.get("since") or event.get("started")
    if not isinstance(stamp, str):
        return None
    try:
        t = time.mktime(time.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except (ValueError, OverflowError):
        return None
    return max(0.0, (now - t) / 3600)


def allow(config, event, now=None):
    """True when the event may be sent. With the setting off it is always True. A label that was sent less than `dedupe_hours` ago is refused; an allowed one is written to the ledger."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not cfg["dedupe_ledger"] and not cfg["max_event_age_hours"]:
        return True
    age = _event_age_hours(event, now) if cfg["max_event_age_hours"] else None
    if age is not None and age > cfg["max_event_age_hours"]:
        with _lock:
            _state["stale"] += 1
        return False
    if not cfg["dedupe_ledger"]:
        return True
    key, window = label(event), cfg["dedupe_hours"] * 3600
    with _lock:
        _load()
        labels = _state["labels"]
        last = labels.get(key)
        if last is not None and now - last < window:
            _state["dropped"] += 1
            return False
        labels[key] = now
        if len(labels) > MAX_ENTRIES:
            for old in sorted(labels, key=labels.get)[:len(labels) - MAX_ENTRIES // 2]:
                labels.pop(old, None)
        for old in [k for k, t in labels.items() if now - t > max(window, 86400) * 2]:
            labels.pop(old, None)
        _save()
    return True


def stats():
    with _lock:
        return {"remembered": len(_state["labels"]), "dropped": _state["dropped"], "stale": _state["stale"]}
