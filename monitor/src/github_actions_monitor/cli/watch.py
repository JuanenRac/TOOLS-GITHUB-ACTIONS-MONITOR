# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`watch status|alerts`: the same read as the command, repeated. It reads the API of the monitor on this computer (never GitHub), so a short interval spends no allowance; the floor of the
interval is a setting (`cli.watch.min_interval_seconds`) and an interval below it is raised to it, not refused. A monitor that cannot be reached is retried with a growing pause (the interval
doubled each time, never more than a minute), and Ctrl-C ends the loop with exit 0. With --exit-on-change the loop ends with exit 6 when what it watches is not what it was at the first read;
without the flag the exit codes are the ones of the command.

The loop knows nothing of the network: the caller hands it the read, the way to write and the clock, so it is tested with a false clock and a false monitor.
"""
import hashlib
import json
import time

EXIT_CHANGED = 6
MIN_INTERVAL, DEFAULT_INTERVAL = 2, 5
BACKOFF_CAP_SECONDS = 60
WATCHABLE = ("status", "alerts")


def limits(raw):
    """(minimum, default) interval in seconds from the configuration, both within 1..3600 and the default never below the minimum."""
    block = (((raw or {}).get("cli") or {}).get("watch") or {}) if isinstance(raw, dict) else {}

    def number(name, fallback):
        value = block.get(name)
        return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 3600 else fallback
    low = number("min_interval_seconds", MIN_INTERVAL)
    return low, max(low, number("default_interval_seconds", DEFAULT_INTERVAL))


def interval_for(asked, raw):
    """The pause between two reads: what was asked, raised to the floor; the default when nothing was asked."""
    low, default = limits(raw)
    if asked is None or asked <= 0:
        return default
    return max(low, min(3600, asked))


def signature(command, payload):
    """What counts as a change: the figures that matter of a status, the set of alerts (sentinel, level, code, repository, muted or not) of the alerts. A clock that ticks is not a change."""
    if not isinstance(payload, dict):
        return ""
    if command == "alerts":
        keys = sorted((str(a.get("sentinel")), str(a.get("level")), str(a.get("code")), str(a.get("repo")), bool(a.get("muted_until"))) for a in payload.get("alerts") or [] if isinstance(a, dict))
    else:
        keys = [payload.get(k) for k in ("repos", "active", "queued", "failures_24h", "red_workflows", "offline", "credential", "edition")]
    return hashlib.sha256(json.dumps(keys, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def backoff(interval, failures):
    """The pause after `failures` reads in a row that failed: the interval doubled for each one, at most a minute (but never below the interval itself)."""
    return max(interval, min(BACKOFF_CAP_SECONDS, interval * (2 ** max(0, failures))))


def run(command, read, show, interval, once=False, exit_on_change=False, sleep=time.sleep, error=None, clear=None, max_cycles=None):
    """The loop. `read()` returns (payload, lines, code) or raises an exception with `.code` and `.text` (a CliError); `show(payload, lines, code)` writes one result; `error(text)` writes a
    message; `clear()` clears the screen before each result (None = never). `max_cycles` stops the loop after that many reads (tests). Returns the exit code."""
    first, failures, cycles, last = None, 0, 0, 0
    try:
        while True:
            cycles += 1
            try:
                payload, lines, code = read()
                failures, last = 0, code
                if clear:
                    clear()
                show(payload, lines, code)
                if exit_on_change:
                    now = signature(command, payload)
                    if first is None:
                        first = now
                    elif now != first:
                        return EXIT_CHANGED
            except Exception as problem:      # a CliError, or an answer that cannot be read: said, and tried again after a longer pause
                if not hasattr(problem, "code"):
                    raise
                failures, last = failures + 1, problem.code
                if error:
                    error(problem.text)
                if once:
                    return problem.code
            if once or (max_cycles is not None and cycles >= max_cycles):
                return last
            sleep(backoff(interval, failures) if failures else interval)
    except KeyboardInterrupt:
        return 0
