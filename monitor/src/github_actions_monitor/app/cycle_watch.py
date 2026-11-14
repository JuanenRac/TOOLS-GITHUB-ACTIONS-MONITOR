# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The heartbeat of the refresh loop, and what to do when it stops.

The loop of the monitor (collect, maintain, publish, write the log, sleep) runs in one thread. If one step hangs (a call that never returns) or the thread dies, the page keeps answering with the
last picture and nothing says it is old. This module keeps the facts that tell it apart: which phase the cycle is in and since when, when the last cycle ended well, the last error and whether the
log could be written. `check()` decides what the watchdog does: nothing, or restart the loop in a new thread (the old one, if it ever wakes up, sees it was replaced and leaves without publishing).
"""
import faulthandler
import subprocess
import threading
import time

PHASES = ("collect", "maintain", "publish", "log", "extras")


class CycleWatch:
    """Thread-safe record of the refresh loop. `clock` is injectable so the tests need no waiting."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.generation = 0
            self.cycles = 0
            self.restarts = 0
            self.phase_name = "idle"
            self.cycle_started = 0.0
            self.phase_since = 0.0
            self.last_ok = 0.0
            self.last_error = ""
            self.last_error_at = 0.0
            self.last_error_phase = ""
            self.log_error = ""
            self.log_error_at = 0.0
            self.started = self.clock()

    def new_generation(self):
        with self.lock:
            self.generation += 1
            return self.generation

    def current(self, generation):
        """False when the loop of this generation was replaced by a newer one: it must leave without publishing anything."""
        with self.lock:
            return generation is None or generation == self.generation

    def begin(self):
        with self.lock:
            now = self.clock()
            self.cycle_started = self.phase_since = now
            self.phase_name = "collect"

    def phase(self, name):
        with self.lock:
            self.phase_name = name
            self.phase_since = self.clock()

    def ok(self):
        with self.lock:
            self.cycles += 1
            self.last_ok = self.clock()
            self.cycle_started = 0.0
            self.phase_name = "idle"

    def fail(self, error):
        with self.lock:
            self.last_error = str(error)[:300]
            self.last_error_at = self.clock()
            self.last_error_phase = self.phase_name
            self.cycle_started = 0.0
            self.phase_name = "idle"

    def log_failed(self, error, kind="log"):
        """A file the monitor writes (its log, the brief for the AI) could not be written; `kind` says which."""
        with self.lock:
            self.log_error = (kind + ": " + repr(error))[:200]
            self.log_error_at = self.clock()

    def log_ok(self, kind="log"):
        with self.lock:
            if self.log_error.startswith(kind + ":"):
                self.log_error = ""

    def running_seconds(self, now=None):
        """How long the cycle in progress has been running (0 when none is)."""
        with self.lock:
            now = self.clock() if now is None else now
            return now - self.cycle_started if self.cycle_started else 0

    def snapshot(self, now=None, limit_seconds=0):
        """What /api/data tells the page: the phase, how long the cycle has been running, how long since the last good one and whether the loop looks stuck (or its log cannot be written)."""
        with self.lock:
            now = self.clock() if now is None else now
            running = now - self.cycle_started if self.cycle_started else 0
            since_ok = int(now - self.last_ok) if self.last_ok else None
            return {"phase": self.phase_name, "cycle_started": self.cycle_started or None, "running_seconds": int(running), "last_cycle_ok": self.last_ok or None,
                    "seconds_since_ok": since_ok, "cycles": self.cycles, "restarts": self.restarts, "last_error": self.last_error, "last_error_phase": self.last_error_phase,
                    "log_error": self.log_error, "stuck": bool(limit_seconds and running > limit_seconds), "limit_seconds": int(limit_seconds or 0), "abandoned_calls": abandoned()}


def check(watch, limit_seconds, thread_alive, now=None):
    """The decision of the watchdog: "" (all well), "stuck" (a cycle has run longer than the limit) or "dead" (the thread of the loop is gone). 0 as limit switches the stuck test off."""
    now = watch.clock() if now is None else now
    if not thread_alive:
        return "dead"
    if limit_seconds and watch.running_seconds(now) > limit_seconds:
        return "stuck"
    return ""


def dump_stacks(stream):
    """The traceback of every thread to an open text file (what each one is doing right now): the evidence of where the loop hangs. Never raises."""
    try:
        faulthandler.dump_traceback(file=stream, all_threads=True)
        stream.flush()
        return True
    except Exception:   # noqa: BLE001 - a stream without a file number must not break the watchdog
        return False


DEFAULT_MAX_ABANDONED = 8
ABANDONED = []      # the threads that bounded() left behind and that have not ended yet
_ABANDONED_LOCK = threading.Lock()


class TooManyAbandoned(subprocess.TimeoutExpired):
    """bounded() starts nothing new while `max_abandoned` calls that never returned are still alive (it is a timeout for whoever called it)."""


def abandoned():
    """How many of the calls that bounded() gave up on are still alive (the ones that ended are forgotten)."""
    with _ABANDONED_LOCK:
        ABANDONED[:] = [t for t in ABANDONED if t.is_alive()]
        return len(ABANDONED)


def blocked(max_abandoned=DEFAULT_MAX_ABANDONED):
    """True when the calls left behind reached the limit: the monitor is degraded (it cannot make more calls to GitHub until some of them end). 0 as limit switches this off."""
    return bool(max_abandoned) and abandoned() >= max_abandoned


def bounded(fn, deadline, max_abandoned=DEFAULT_MAX_ABANDONED):
    """Runs fn() and gives its result, but never waits longer than `deadline` seconds: a call that hangs (a child process that holds its pipes, a read without a timeout) is left behind in a daemon
    thread and TimeoutExpired is raised, so the loop goes on. The threads left behind are counted: with `max_abandoned` of them still alive nothing new is started (TooManyAbandoned), so a failure
    that never ends cannot pile up threads, sockets and memory without limit."""
    if blocked(max_abandoned):
        raise TooManyAbandoned("call", 0)
    box = {}

    def work():
        try:
            box["value"] = fn()
        except BaseException as error:   # noqa: BLE001 - handed to the caller
            box["error"] = error

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(deadline)
    if thread.is_alive():
        with _ABANDONED_LOCK:
            ABANDONED.append(thread)
        raise subprocess.TimeoutExpired("call", deadline)
    if "error" in box:
        raise box["error"]
    return box.get("value")
