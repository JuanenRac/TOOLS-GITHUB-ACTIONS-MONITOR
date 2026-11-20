# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What a refresh cycle (a tick) cost and how it went, for /metrics: duration of the cycle and of its phases, cycles that failed, the reads that were repeated (retries) and the repositories that
wait before their next read because they failed several times in a row (the circuit of that repository). Memory only: nothing is written to disk and nothing leaves the computer.
"""
import threading
import time

from github_actions_monitor.integrations.job_metrics import Histogram

TICK_BUCKETS = (1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1800)
PHASES = ("collect", "maintain", "publish", "log", "extras")
LOCK = threading.Lock()
STATE = {}


def reset():
    with LOCK:
        STATE.clear()
        STATE.update({"cycles": 0, "failed": 0, "retries": 0, "last_seconds": None, "last_at": None, "last_ok_at": None, "reads_last": 0,
                      "hist": Histogram("tick_seconds", "Duration of a refresh cycle, from its start to the end of its last phase.", TICK_BUCKETS), "phases": {}})


reset()


def note_retry(count=1):
    """A read that failed for a passing reason and will be repeated."""
    with LOCK:
        STATE["retries"] += count


def note_cycle(seconds, ok=True, phases=None, reads=None, now=None):
    """Called at the end of every cycle (also one that failed)."""
    now = time.time() if now is None else now
    with LOCK:
        STATE["cycles"] += 1
        STATE["last_seconds"], STATE["last_at"] = round(float(seconds), 3), now
        if ok:
            STATE["last_ok_at"] = now
        else:
            STATE["failed"] += 1
        if isinstance(reads, int):
            STATE["reads_last"] = reads
        STATE["hist"].observe({}, float(seconds), 1)
        for name, value in (phases or {}).items():
            if name in PHASES and isinstance(value, (int, float)):
                STATE["phases"][name] = round(float(value), 3)


def circuit(cache, now=None, transient_cycles=3):
    """{"open": repositories waiting before the next read, "failing": repositories with a failed last read, "max_fails": the longest streak} from the run cache of the monitor."""
    now = time.time() if now is None else now
    entries = [e for e in (cache or {}).values() if isinstance(e, dict)]
    return {"open": sum(1 for e in entries if (e.get("retry_at") or 0) > now), "failing": sum(1 for e in entries if (e.get("fails") or 0) > 0),
            "max_fails": max([e.get("fails") or 0 for e in entries] or [0]), "hot_retry": sum(1 for e in entries if 0 < (e.get("fails") or 0) < transient_cycles)}


def snapshot(cache=None, now=None):
    with LOCK:
        out = {k: v for k, v in STATE.items() if k != "hist"}
        out["phases"] = dict(STATE["phases"])
    out["circuit"] = circuit(cache, now)
    return out


def lines(prefix, esc, cache=None, now=None):
    """Exposition lines (empty until a cycle has finished)."""
    snap = snapshot(cache, now)
    if not snap["cycles"]:
        return []
    out = []

    def add(name, text, value, kind="gauge"):
        if value is None:
            return
        out.extend([f"# HELP {prefix}{name} {text}", f"# TYPE {prefix}{name} {kind}", f"{prefix}{name} {value}"])
    add("ticks_total", "Refresh cycles finished since the process started.", snap["cycles"], "counter")
    add("tick_failures_total", "Refresh cycles that ended with an error.", snap["failed"], "counter")
    add("tick_last_seconds", "Duration of the last refresh cycle.", snap["last_seconds"])
    add("tick_last_ok_timestamp_seconds", "Unix time of the last cycle that ended well.", int(snap["last_ok_at"]) if snap["last_ok_at"] else None)
    add("tick_reads_last", "Repositories read in the last cycle.", snap["reads_last"])
    add("read_retries_total", "Reads of a repository that failed for a passing reason and were repeated.", snap["retries"], "counter")
    if snap["phases"]:
        out.extend([f"# HELP {prefix}tick_phase_seconds Seconds of each phase of the last cycle.", f"# TYPE {prefix}tick_phase_seconds gauge"])
        out.extend(f'{prefix}tick_phase_seconds{{phase="{esc(name)}"}} {value}' for name, value in sorted(snap["phases"].items()))
    state = snap["circuit"]
    add("repos_circuit_open", "Repositories that wait before the next read because they failed several times in a row.", state["open"])
    add("repos_read_failing", "Repositories whose last read failed.", state["failing"])
    add("repos_read_fail_streak_max", "The longest streak of failed reads of one repository.", state["max_fails"])
    with LOCK:
        out.extend(STATE["hist"].lines(prefix, esc))
    return out
