# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor watches itself: how much memory it holds, how many threads it runs and how much processor it uses, so that it says so BEFORE the system (a container with a limit, the OOM killer) ends it.

  * `sample()` reads the numbers with the standard library only (/proc on Linux, the system call of Windows, `resource` elsewhere); a number that cannot be read is None, never a guess.
  * `Watch` keeps the last sample and decides: `ok`, or `high` when the resident memory is over `selfwatch.rss_warn_mb` or the threads over `selfwatch.threads_warn`. Going high is noted once in the
    counter of swallowed failures (`degraded`) with its numbers, runs the registered relief functions (by default a garbage collection) and shows in `/api/health` as `selfwatch`; going back to ok is noted too.
  * `selfwatch.enabled` (on by default: reading a few numbers costs nothing), `selfwatch.rss_warn_mb` (1024), `selfwatch.threads_warn` (400), `selfwatch.interval_seconds` (60).
Nothing here leaves the machine and nothing is written to disk."""
import gc
import os
import sys
import threading
import time

DEFAULTS = {"enabled": True, "rss_warn_mb": 1024, "threads_warn": 400, "interval_seconds": 60}
RANGES = {"rss_warn_mb": (64, 262144), "threads_warn": (20, 100000), "interval_seconds": (5, 3600)}


def settings(config):
    block = (config or {}).get("selfwatch") if isinstance(config, dict) else None
    out = dict(DEFAULTS)
    if not isinstance(block, dict):
        return out
    if isinstance(block.get("enabled"), bool):
        out["enabled"] = block["enabled"]
    for key, (low, high) in RANGES.items():
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    return out


def rss_mb():
    """Resident memory of this process in MB, or None."""
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/status", "r", encoding="ascii", errors="replace") as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        return round(int(line.split()[1]) / 1024, 1)
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            counters = Counters()
            counters.cb = ctypes.sizeof(Counters)
            kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return round(counters.WorkingSetSize / 1048576, 1)
            return None
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss      # the PEAK, in bytes on macOS and kilobytes elsewhere: the best a system without /proc gives
        return round(peak / (1048576 if sys.platform == "darwin" else 1024), 1)
    except (OSError, ValueError, ImportError, AttributeError):
        return None
    return None


def sample(previous=None, clock=time.monotonic, cpu=time.process_time):
    """{"rss_mb", "threads", "cpu_percent", "at"}; cpu_percent is the processor time used since `previous` (None for the first sample), where 100 = one whole core."""
    now, used = clock(), cpu()
    percent = None
    if previous and now > previous["_wall"]:
        percent = round(100 * (used - previous["_cpu"]) / (now - previous["_wall"]), 1)
    return {"rss_mb": rss_mb(), "threads": threading.active_count(), "cpu_percent": percent, "at": int(time.time()), "_wall": now, "_cpu": used}


class Watch:
    def __init__(self, note=None):
        self.cfg = dict(DEFAULTS)
        self.last = None
        self.state = "ok"
        self.reason = ""
        self.high_since = 0
        self.relief = [gc.collect]
        self.note = note      # note(origin, text): the counter of swallowed failures
        self.lock = threading.Lock()

    def configure(self, config):
        self.cfg = settings(config)

    def tick(self, sampled=None, previous=None):
        """Takes a sample (or uses the one given), decides and, when the state changes, notes it. Returns the snapshot."""
        with self.lock:
            sampled = sampled or sample(self.last if previous is None else previous)
            self.last = sampled
            reason = ""
            if sampled.get("rss_mb") is not None and sampled["rss_mb"] >= self.cfg["rss_warn_mb"]:
                reason = f"memory {sampled['rss_mb']} MB >= {self.cfg['rss_warn_mb']} MB"
            elif sampled.get("threads") is not None and sampled["threads"] >= self.cfg["threads_warn"]:
                reason = f"threads {sampled['threads']} >= {self.cfg['threads_warn']}"
            before = self.state
            self.state = "high" if reason else "ok"
            self.reason = reason
            changed = before != self.state
            if changed and self.state == "high":
                self.high_since = sampled["at"]
        if changed and self.note:
            try:
                self.note("selfwatch." + self.state, reason or "back to normal")
            except Exception:   # noqa: BLE001 - noting never stops the watch
                pass
        if changed and self.state == "high":
            for function in list(self.relief):
                try:
                    function()
                except Exception:   # noqa: BLE001
                    pass
        return self.snapshot()

    def snapshot(self):
        last = self.last or {}
        return {"state": self.state, "reason": self.reason, "rss_mb": last.get("rss_mb"), "threads": last.get("threads"), "cpu_percent": last.get("cpu_percent"),
                "rss_warn_mb": self.cfg["rss_warn_mb"], "threads_warn": self.cfg["threads_warn"], "high_since": self.high_since or None}

    def run(self, stop):
        """The loop of the thread: one sample every `interval_seconds` until `stop` (a threading.Event) is set."""
        while not stop.is_set():
            if self.cfg["enabled"]:
                self.tick()
            stop.wait(self.cfg["interval_seconds"])


WATCH = Watch()
_STOP = threading.Event()


def start(config, note=None):
    """Starts the thread once (a second call only reads the settings again). Returns the watch."""
    WATCH.configure(config)
    if note is not None:
        WATCH.note = note
    if not any(t.name == "selfwatch" and t.is_alive() for t in threading.enumerate()):
        _STOP.clear()
        threading.Thread(target=WATCH.run, args=(_STOP,), name="selfwatch", daemon=True).start()
    return WATCH
