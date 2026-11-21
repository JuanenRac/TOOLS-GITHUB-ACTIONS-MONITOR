# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""An outside heartbeat: somebody else notices when the monitor stops.

The monitor runs on a computer that is switched off, put to sleep or restarted, and then nobody is told that nobody is watching. This sends a small ping, every few minutes, to a service that
raises the alarm when the pings stop (healthchecks.io, Cronitor, Uptime Kuma, or any address that takes a plain GET). OFF by default.

  heartbeat.enabled           off by default (it reaches an outside address)
  heartbeat.url_env           the NAME of the environment variable that holds the ping address (MONITOR_HEARTBEAT_URL by default); the address is a secret, so it is never written in the configuration
  heartbeat.interval_seconds  300 by default (30 to 86400)
  heartbeat.send_state        on: the ping carries `msg=<version> <ok|degraded>` and nothing else (no repository, no alert, no name)
  heartbeat.fail_suffix       empty by default: when the monitor is not fit to serve (its refresh loop is stuck or gone) the ping is NOT sent, and the silence is the alarm. A service that takes a fail
                              address (healthchecks.io: `/fail`) can be given the suffix and then it is told at once

The address must be `https` (or `http` only with `notify.allow_private_targets`, for a service in your own network), carry no user name or password, and is opened with the same guard as the
notifications (a private or metadata address is refused unless you allowed it). Never logged or shown: the status only says whether one is defined.
"""
import re
import threading
import time
import urllib.request
from urllib.parse import quote, urlparse

from github_actions_monitor.security import envguard

ENV_NAME = "MONITOR_HEARTBEAT_URL"
DEFAULTS = {"enabled": False, "url_env": ENV_NAME, "interval_seconds": 300, "send_state": True, "fail_suffix": ""}
SUFFIX_RE = re.compile(r"^(/[a-z]{1,10})?\Z")
ENV_RE = envguard.NamePattern(own=(ENV_NAME,))
TIMEOUT = 8


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = (config or {}).get("heartbeat")
    block = block if isinstance(block, dict) else {}
    name = block.get("url_env")
    suffix = block.get("fail_suffix")
    return {"enabled": block.get("enabled") is True, "url_env": name if isinstance(name, str) and ENV_RE.match(name) else ENV_NAME,
            "interval_seconds": _int(block.get("interval_seconds"), 30, 86400, DEFAULTS["interval_seconds"]), "send_state": block.get("send_state", True) is True,
            "fail_suffix": suffix if isinstance(suffix, str) and SUFFIX_RE.match(suffix) else ""}


def address(config):
    """The ping address from the environment variable the setting names (held by envguard once the process started), or ''. Never printed."""
    return envguard.get(settings(config)["url_env"]).strip()


def check_url(url, allow_private=False):
    """None when the address may be used, else the reason: "empty", "bad_url", "not_https" or "credentials"."""
    if not url:
        return "empty"
    if len(url) > 400 or any(ord(c) < 33 for c in url):
        return "bad_url"
    parts = urlparse(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        return "bad_url"
    if parts.username or parts.password:
        return "credentials"
    if parts.scheme == "http" and not allow_private:
        return "not_https"
    return None


def target(config, healthy, url, version):
    """The address to ask for this ping, or '' when none is sent (an unhealthy monitor with no fail address stays silent on purpose)."""
    cfg = settings(config)
    base = url.split("?")[0].rstrip("/")
    if not healthy:
        if not cfg["fail_suffix"]:
            return ""
        base += cfg["fail_suffix"]
    query = url.partition("?")[2]
    if cfg["send_state"]:
        extra = "msg=" + quote(f"{version} {'ok' if healthy else 'degraded'}", safe="")
        query = (query + "&" if query else "") + extra
    return base + ("?" + query if query else "")


class Heartbeat:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.next_at = 0.0
        self.stats = {"sent": 0, "failed": 0, "skipped": 0, "last_at": None, "last_ok": None, "last_reason": ""}

    def tick(self, config, healthy, version, allow_private=False, opener=None, now=None):
        """One turn: sends the ping when it is time. Returns "sent", "failed", "skipped" (unhealthy and no fail address) or "" (not time, off, or no valid address). Never raises."""
        now = time.time() if now is None else now
        cfg = settings(config)
        with self.lock:
            if not cfg["enabled"] or now < self.next_at:
                return ""
            self.next_at = now + cfg["interval_seconds"]
        url = address(config)
        reason = check_url(url, allow_private)
        with self.lock:
            self.stats["last_reason"] = reason or ""
        if reason:
            return ""
        where = target(config, healthy, url, version)
        if not where:
            with self.lock:
                self.stats["skipped"] += 1
            return "skipped"
        from github_actions_monitor.security import netguard
        send = opener or netguard.opener_for(allow_private, follow_redirects=False)
        try:
            with send(urllib.request.Request(where, headers={"User-Agent": "github-actions-monitor"}, method="GET"), timeout=TIMEOUT) as answer:
                ok = 200 <= getattr(answer, "status", 200) < 300
        except OSError:
            ok = False
        with self.lock:
            self.stats["sent" if ok else "failed"] += 1
            self.stats["last_at"], self.stats["last_ok"] = now, ok
        return "sent" if ok else "failed"

    def snapshot(self, config=None):
        cfg = settings(config)
        defined = bool(address(config)) if cfg["enabled"] else False
        with self.lock:
            return {"enabled": cfg["enabled"], "address_defined": defined, "interval_seconds": cfg["interval_seconds"], **self.stats}


HEARTBEAT = Heartbeat()
