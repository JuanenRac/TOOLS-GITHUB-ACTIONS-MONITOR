# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""When a read meets the end of its allowance: another source, then the last good copy. Standard library only; block `quota`, setting `quota.failover` (off by default).

The reads of the monitor are spread over the sources of the pool (the login of the user, the GitHub App, a second read-only account: readpool.py). A read that answers 429 or "rate limit exceeded"
is, with this switch on, made ONCE more with another source that can read, and the source that ran dry is marked as spent until the next free probe of its allowance. When every source is spent the
LAST GOOD COPY of that read is served (the one the conditional-read cache or the memory of the monitor holds, no older than `quota.failover_max_age_minutes`, 60 by default) with its age, instead of
an error. Three rules do not change:

  * an answer that carries the marks of a limit is NEVER taken for "permission denied": the source is not left out for a refusal, it is only spent for a while;
  * the writes and the actions keep the token of the user, they never fail over;
  * a copy is served only for a read of the API (a GET); the age is counted, shown in the status of the quota and the copy is never kept longer than the limit asked for.
"""
import re
import threading
import time

DEFAULTS = {"failover": False, "failover_max_age_minutes": 60}
LIMIT_RE = re.compile(r"rate limit|secondary rate|abuse detection|\b429\b|too many requests|x-ratelimit-remaining: ?0", re.I)
MAX_COPIES = 300      # reads whose last good answer the memory keeps (the oldest goes first)
_LOCK = threading.Lock()
_COPIES = {}
STATE = {"switched": 0, "stale_served": 0, "spent": {}, "last_switch": None, "last_stale": None}


def settings(config):
    """{"failover": bool, "failover_max_age_minutes": 1..1440} with the conservative default for anything that is not of the right type."""
    block = (config or {}).get("quota") if isinstance((config or {}).get("quota"), dict) else {}
    minutes = block.get("failover_max_age_minutes")
    good = isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 1440
    return {"failover": block.get("failover") is True, "failover_max_age_minutes": minutes if good else DEFAULTS["failover_max_age_minutes"]}


def is_limit(text):
    """True when the text of a failed read is the end of an allowance (429, primary or secondary limit), not a refusal for lack of permission."""
    return bool(LIMIT_RE.search(str(text or "")))


def remember(key, data, now=None):
    """Keeps the last good answer of a read (memory only, bounded)."""
    with _LOCK:
        _COPIES.pop(key, None)
        _COPIES[key] = (time.time() if now is None else now, data)
        while len(_COPIES) > MAX_COPIES:
            _COPIES.pop(next(iter(_COPIES)))


def recall(key, config, now=None):
    """(data, age_seconds) of the last good answer of that read when it is not older than `quota.failover_max_age_minutes`, else None."""
    now = time.time() if now is None else now
    limit = settings(config)["failover_max_age_minutes"] * 60
    with _LOCK:
        held = _COPIES.get(key)
    if not held or now - held[0] > limit:
        return None
    return held[1], max(0, int(now - held[0]))


def served(copy, key, now=None):
    """Counts and names a copy that was served in place of an answer (the endpoint only, never a credential)."""
    STATE["stale_served"] += 1
    STATE["last_stale"] = {"read": str(key)[:120], "age_seconds": int(copy[1]), "at": int(time.time() if now is None else now)}


def switched(name, other, now=None):
    """Counts the change of source: `name` ran dry, `other` answers."""
    STATE["switched"] += 1
    STATE["spent"][name] = int(time.time() if now is None else now)
    STATE["last_switch"] = {"from": name, "to": other, "at": int(time.time() if now is None else now)}


def others(available, tried):
    """The sources that can still be asked after the ones already tried, in the order they came."""
    return [name for name in available if name not in tried]


def snapshot(config):
    """For the page and /api/quota-pool/status: the switch, how many times it acted and the last of each (no token, no path)."""
    cfg = settings(config)
    return {"enabled": cfg["failover"], "max_age_minutes": cfg["failover_max_age_minutes"], "switched": STATE["switched"], "stale_served": STATE["stale_served"],
            "last_switch": STATE["last_switch"], "last_stale": STATE["last_stale"]}


def reset():
    with _LOCK:
        _COPIES.clear()
    STATE.update({"switched": 0, "stale_served": 0, "spent": {}, "last_switch": None, "last_stale": None})
