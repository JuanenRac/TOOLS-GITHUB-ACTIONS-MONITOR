# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One read for everybody (`refresh.share_by_workflow`, OFF by default).

When several things ask for the same workflow at the same moment (the cycle that reads the jobs of a run, a page that opens it, a wall screen, an API client, the AI), each one used to make its own
call to GitHub. With this on the first one reads and the others wait for its answer (a read in flight is shared), and the answer stays valid for `refresh.share_seconds` seconds, so the next
callers of that workflow take it from memory. The key is the repository and the workflow (or the run): a read of another workflow is never shared. A read that failed is not remembered: the next
caller tries again. Everybody sees the same figures, and the allowance is spent once.

Reads that change what GitHub holds never go through here: only reads, which the caller names as `fetch`.
"""
import threading
import time

DEFAULTS = {"share_by_workflow": False, "share_seconds": 20}
MAX_ENTRIES = 500


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    cfg = config.get("refresh") if isinstance(config, dict) and isinstance(config.get("refresh"), dict) else {}
    return {"share_by_workflow": cfg.get("share_by_workflow") is True, "share_seconds": _int(cfg.get("share_seconds"), 1, 600, DEFAULTS["share_seconds"])}


class Shared:
    """A cache with a lifetime and a lock per key: `get(key, fetch)` calls `fetch()` once for all the callers that arrive while it runs or within the lifetime."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self.done = {}          # key -> (at, value)
        self.flying = {}        # key -> threading.Event, with the outcome in self.result
        self.result = {}
        self.stats = {"reads": 0, "shared": 0, "waited": 0}

    def reset(self):
        with self.lock:
            self.done.clear()
            self.flying.clear()
            self.result.clear()
            self.stats.update({"reads": 0, "shared": 0, "waited": 0})

    def get(self, key, fetch, ttl, wait=60.0):
        now = self.clock()
        with self.lock:
            held = self.done.get(key)
            if held and now - held[0] <= ttl:
                self.stats["shared"] += 1
                return held[1]
            event = self.flying.get(key)
            if event is None:
                event = self.flying[key] = threading.Event()
                leader = True
            else:
                leader = False
        if not leader:
            if event.wait(wait):
                with self.lock:
                    outcome = self.result.get(key)
                    if outcome and outcome[0]:
                        self.stats["waited"] += 1
                        return outcome[1]
            return fetch()      # the leader failed or took too long: this caller reads for itself
        ok, value = False, None
        try:
            value = fetch()
            ok = True
            return value
        finally:
            with self.lock:
                self.stats["reads"] += 1
                self.result[key] = (ok, value)
                if ok:
                    self.done[key] = (self.clock(), value)
                    if len(self.done) > MAX_ENTRIES:
                        for old in sorted(self.done, key=lambda k: self.done[k][0])[:len(self.done) - MAX_ENTRIES // 2]:
                            self.done.pop(old, None)
                self.flying.pop(key, None)
            event.set()


SHARED = Shared()


def read(config, key, fetch):
    """`fetch()` through the shared reader when `refresh.share_by_workflow` is on, else straight."""
    cfg = settings(config)
    if not cfg["share_by_workflow"]:
        return fetch()
    return SHARED.get(key, fetch, cfg["share_seconds"])


def lines(prefix, config):
    if not settings(config)["share_by_workflow"]:
        return []
    s = SHARED.stats
    return [f"# HELP {prefix}shared_reads_total Reads of GitHub made through the shared reader.", f"# TYPE {prefix}shared_reads_total counter", f"{prefix}shared_reads_total {s['reads']}",
            f"# HELP {prefix}shared_reads_spared_total Reads answered from the shared reader instead of calling GitHub (from memory or from a read in flight).", f"# TYPE {prefix}shared_reads_spared_total counter",
            f"{prefix}shared_reads_spared_total {s['shared'] + s['waited']}"]
