# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Resilience to network cuts: the monitor keeps showing the last picture, says since when it has no connection and resumes by itself.

`Link` is told, for every read of GitHub, whether it worked or failed with what text. When every read of a cycle fails with a connection problem (not an authentication or a
permission problem, which are different things) the link goes offline: the page shows the last picture marked "offline since HH:MM", nothing raises, and the next successful read
brings it back online. Both changes are reported once (`offline` / `online`, to the event feed and to the notifications).
"""
import re
import threading
import time
from datetime import datetime, timezone

NETWORK_RE = re.compile(r"(dial tcp|no such host|temporary failure in name resolution|name or service not known|getaddrinfo|network is unreachable|connection (?:refused|reset|timed out|aborted)|"
                        r"timed? ?out|timeout|i/o timeout|eof|tls handshake|error connecting|could not resolve|unreachable|proxyconnect|socket)", re.I)
AUTH_RE = re.compile(r"(401|bad credentials|403|rate limit|not logged|gh auth)", re.I)


def is_network_error(text):
    """True for an error text that is about the connection, False for authentication, quota or "not found" answers."""
    text = str(text or "")
    if AUTH_RE.search(text) and not NETWORK_RE.search(text):
        return False
    return bool(NETWORK_RE.search(text))


def stamp(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Link:
    """Counts the successes and the connection failures of one cycle and changes state at the end of it (`end_cycle`)."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self.ok = self.bad = 0
        self.offline_since = None
        self.last_ok = None

    def record(self, error=None):
        """Call after each read of GitHub: error=None when it worked, or the error text."""
        with self.lock:
            if error is None:
                self.ok += 1
                self.last_ok = self.clock()
            elif is_network_error(error):
                self.bad += 1

    def end_cycle(self):
        """Closes the cycle. Returns the transition event {"kind": "offline" | "online", "at"} or None."""
        with self.lock:
            ok, bad, self.ok, self.bad = self.ok, self.bad, 0, 0
            now = self.clock()
            if bad and not ok and self.offline_since is None:
                self.offline_since = now
                return {"kind": "offline", "at": stamp(now)}
            if ok and self.offline_since is not None:
                since, self.offline_since = self.offline_since, None
                return {"kind": "online", "at": stamp(now), "seconds_offline": int(now - since)}
            return None

    def state(self):
        """What the page shows: {"offline": bool, "since": iso text or None, "last_ok": iso or None}."""
        with self.lock:
            return {"offline": self.offline_since is not None, "since": stamp(self.offline_since) if self.offline_since else None, "last_ok": stamp(self.last_ok) if self.last_ok else None}
