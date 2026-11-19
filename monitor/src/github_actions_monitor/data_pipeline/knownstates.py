# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The states and conclusions GitHub is known to send for a run, and a count of the ones it sends that the monitor does not know.

GitHub adds a value from time to time. A value the monitor does not know is never red and never green: it is shown as it came, counted here, and named in the brief for the AI tools (`schema.drift`) so that
the rules can learn it. Nothing here reads GitHub or writes a file; the counter lives in memory and is bounded.

  observe(run)   records the status and the conclusion of one run of the list (a run that is not an object or has no number is counted as "malformed" and left out by the caller)
  drift()        {"status": {value: count}, "conclusion": {value: count}, "malformed": count} of what was seen since the start
"""
import threading

KNOWN_STATUS = frozenset({"queued", "in_progress", "completed", "waiting", "requested", "pending"})
KNOWN_CONCLUSION = frozenset({"success", "failure", "cancelled", "skipped", "timed_out", "neutral", "action_required", "stale", "startup_failure"})
MAX_VALUES = 20          # different unknown values kept for each field
MAX_TEXT = 40

_LOCK = threading.Lock()
_SEEN = {"status": {}, "conclusion": {}, "malformed": 0}


def _clip(value):
    return str(value)[:MAX_TEXT]


def is_well_formed(run):
    """A run the page can use: an object with a whole number as its id."""
    return isinstance(run, dict) and isinstance(run.get("id"), int) and not isinstance(run.get("id"), bool)


def observe(run):
    """Counts the unknown status or conclusion of a run (None and "" are normal: a run in progress has no conclusion). Returns True when something unknown was seen."""
    if not is_well_formed(run):
        with _LOCK:
            _SEEN["malformed"] += 1
        return True
    found = False
    for field, known in (("status", KNOWN_STATUS), ("conclusion", KNOWN_CONCLUSION)):
        value = run.get(field)
        if value in (None, "") or value in known:
            continue
        found = True
        with _LOCK:
            bucket = _SEEN[field]
            key = _clip(value)
            if key in bucket or len(bucket) < MAX_VALUES:
                bucket[key] = bucket.get(key, 0) + 1
    return found


def drift():
    with _LOCK:
        return {"status": dict(_SEEN["status"]), "conclusion": dict(_SEEN["conclusion"]), "malformed": _SEEN["malformed"]}


def reset():
    with _LOCK:
        _SEEN.update(status={}, conclusion={}, malformed=0)


def is_empty(info):
    return not (info.get("status") or info.get("conclusion") or info.get("malformed"))
