# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Queues and backpressure for the reads of a refresh cycle (`backpressure.enabled`, OFF by default).

A big account (hundreds of repositories) can ask for more reads than one cycle can do. Without a limit the cycle grows until the watchdog complains. With this on, the reads wanted in a cycle
are put in ONE bounded queue in a fixed order of importance and only the first `max_reads_per_cycle` are done; the rest wait for the next cycle, where the ones that waited longest go first, so
nothing starves. When the last cycle was longer than `shed_percent` percent of the pause between cycles the allowed number is cut in half (never under `min_reads`) and it grows by a tenth
after each cycle that was fast enough, so the monitor slows down by itself instead of piling work up. Nothing is dropped for good: a repository that waits keeps its last picture.

Order of importance: repositories with a red workflow, hot repositories, repositories never read, then the rest by the age of their last read (the oldest first).
"""
import threading

DEFAULTS = {"enabled": False, "max_reads_per_cycle": 0, "shed_percent": 150, "min_reads": 20}
LOCK = threading.Lock()
STATE = {"allowed": None, "depth": 0, "deferred_total": 0, "shed_cycles": 0, "oldest_wait_cycles": 0, "last_wanted": 0, "waits": {}}


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    cfg = config.get("backpressure") if isinstance(config, dict) and isinstance(config.get("backpressure"), dict) else {}
    return {"enabled": cfg.get("enabled") is True, "max_reads_per_cycle": _int(cfg.get("max_reads_per_cycle"), 0, 5000, DEFAULTS["max_reads_per_cycle"]),
            "shed_percent": _int(cfg.get("shed_percent"), 100, 1000, DEFAULTS["shed_percent"]), "min_reads": _int(cfg.get("min_reads"), 1, 500, DEFAULTS["min_reads"])}


def reset():
    with LOCK:
        STATE.update({"allowed": None, "depth": 0, "deferred_total": 0, "shed_cycles": 0, "oldest_wait_cycles": 0, "last_wanted": 0, "waits": {}})


def allowed(cfg, last_seconds=None, interval=None):
    """How many reads this cycle may do: the fixed cap, cut in half after a cycle that was too long and growing back by a tenth after a fast one (None = no limit)."""
    cap = cfg["max_reads_per_cycle"]
    with LOCK:
        current = STATE["allowed"]
        slow = bool(last_seconds and interval and last_seconds * 100 > interval * cfg["shed_percent"])
        if current is None:
            current = cap or None
        if current is not None:
            if slow:
                current = max(cfg["min_reads"], current // 2)
                STATE["shed_cycles"] += 1
            elif cap and current < cap:
                current = min(cap, current + max(1, current // 10))
        elif slow and STATE["last_wanted"]:      # no cap set: the first slow cycle sets one, from what it had to read
            current = max(cfg["min_reads"], STATE["last_wanted"] // 2)
            STATE["shed_cycles"] += 1
        STATE["allowed"] = current
        return current


def order(todo, hot, red, held):
    """`todo` = [(repo, runs_wanted)] in order of importance: red, hot, never read, then the oldest read first. `held` = the run cache ({repo: {"at": time}})."""
    def key(item):
        repo = item[0]
        entry = held.get(repo)
        return (0 if repo in red else 1 if repo in hot else 2 if not entry else 3, (entry or {}).get("at") or 0)
    return sorted(todo, key=key)


def plan(todo, config, hot=(), red=(), held=None, last_seconds=None, interval=None):
    """(to_read, waiting): the part of `todo` this cycle reads and the part that waits for the next one. With the setting off everything is read."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return todo, []
    ordered = order(todo, set(hot), set(red), held or {})
    with LOCK:
        STATE["last_wanted"] = len(ordered)
    limit = allowed(cfg, last_seconds, interval)
    if limit is None or len(ordered) <= limit:
        with LOCK:
            STATE["depth"] = 0
            STATE["waits"] = {}
            STATE["oldest_wait_cycles"] = 0
        return ordered, []
    wait = ordered[limit:]
    with LOCK:
        STATE["depth"] = len(wait)
        STATE["deferred_total"] += len(wait)
        waits = {item[0]: STATE["waits"].get(item[0], 0) + 1 for item in wait}
        STATE["waits"] = waits
        STATE["oldest_wait_cycles"] = max(waits.values())
    return ordered[:limit], wait


def snapshot():
    with LOCK:
        return {k: v for k, v in STATE.items() if k != "waits"}


def lines(prefix, config=None):
    cfg = settings(config or {})
    if not cfg["enabled"]:
        return []
    snap = snapshot()
    out = []
    for name, text, value, kind in (("read_queue_depth", "Reads wanted in the last cycle that wait for the next one (backpressure).", snap["depth"], "gauge"),
                                    ("read_queue_allowed", "Reads the last cycle was allowed to do (absent while there is no limit).", snap["allowed"], "gauge"),
                                    ("read_queue_oldest_wait_cycles", "Cycles the longest waiting repository has waited.", snap["oldest_wait_cycles"], "gauge"),
                                    ("read_queue_deferred_total", "Reads put off to a later cycle since the process started.", snap["deferred_total"], "counter"),
                                    ("read_queue_shed_cycles_total", "Cycles after which the number of reads was cut because the cycle was too long.", snap["shed_cycles"], "counter")):
        if value is not None:
            out.extend([f"# HELP {prefix}{name} {text}", f"# TYPE {prefix}{name} {kind}", f"{prefix}{name} {value}"])
    return out
