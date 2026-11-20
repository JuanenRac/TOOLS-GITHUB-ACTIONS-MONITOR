# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The state of GitHub itself (githubstatus.com), and what it says about a red.

A workflow that turns red while GitHub Actions has an incident is not a defect of the repository. When this is on, the monitor reads the public summary of githubstatus.com (one small JSON, no
account, nothing about you is sent), shows the state of GitHub in the bar of the page and, while Actions has an incident, marks the reds that appear with "possible cause: an incident of GitHub".

  github_status.enabled          off by default (it reaches an outside site)
  github_status.interval_seconds 300 by default (60 to 3600)
  github_status.mark_reds        on: while Actions has an incident the new reds say so (the red itself is never hidden)
  github_status.quiet_notices    off: when on, the notices of those reds are held until the incident is over and then told once, with how many are still red

Pure functions plus one small class: the read is given by the caller (`opener`), so nothing here needs the network to be tested.
"""
import json
import threading
import time
from urllib.parse import urlparse

URL = "https://www.githubstatus.com/api/v2/summary.json"
HOST = "www.githubstatus.com"
MAX_BYTES = 600_000
DEFAULTS = {"enabled": False, "interval_seconds": 300, "mark_reds": True, "quiet_notices": False}
INDICATORS = ("none", "minor", "major", "critical")
LEVELS = ("operational", "degraded_performance", "partial_outage", "major_outage", "under_maintenance")
TRACKED = ("Actions", "API Requests", "Git Operations", "Issues", "Pull Requests", "Webhooks", "Packages", "Pages")      # the parts of GitHub the monitor depends on, as githubstatus.com names them
ACTIONS = "Actions"


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = (config or {}).get("github_status")
    block = block if isinstance(block, dict) else {}
    return {"enabled": block.get("enabled") is True, "interval_seconds": _int(block.get("interval_seconds"), 60, 3600, DEFAULTS["interval_seconds"]),
            "mark_reds": block.get("mark_reds", True) is True, "quiet_notices": block.get("quiet_notices") is True}


def _text(value, size=120):
    return " ".join(str(value or "").split())[:size] if isinstance(value, (str, int)) else ""


def parse(summary):
    """The facts the monitor uses from the summary of githubstatus.com, or None when it does not look like one:
    {"indicator", "description", "components": {name: level}, "incidents": [{"name", "impact", "status", "parts": [...]}], "actions": bool}. `actions` is true when the component Actions is not
    operational or an incident that is not resolved names it."""
    if not isinstance(summary, dict) or not isinstance(summary.get("status"), dict):
        return None
    indicator = summary["status"].get("indicator")
    out = {"indicator": indicator if indicator in INDICATORS else "none", "description": _text(summary["status"].get("description")), "components": {}, "incidents": [], "actions": False}
    for item in summary.get("components") or []:
        if isinstance(item, dict) and item.get("name") in TRACKED:
            level = item.get("status")
            out["components"][item["name"]] = level if level in LEVELS else "operational"
    for item in summary.get("incidents") or []:
        if not isinstance(item, dict) or item.get("status") in ("resolved", "postmortem"):
            continue
        parts = [_text(c.get("name"), 60) for c in item.get("components") or [] if isinstance(c, dict)]
        out["incidents"].append({"name": _text(item.get("name")), "impact": item.get("impact") if item.get("impact") in INDICATORS else "none", "status": _text(item.get("status"), 30), "parts": parts[:8]})
    out["incidents"] = out["incidents"][:5]
    out["actions"] = out["components"].get(ACTIONS, "operational") not in ("operational", "under_maintenance") or any(ACTIONS in i["parts"] for i in out["incidents"])
    return out


def fetch(opener, timeout=10):
    """The parsed summary, or None. `opener(request, timeout=...)` is the way to open an address (netguard.opener_for: public hosts only). Only the one address of githubstatus.com is ever asked for."""
    import urllib.request
    if urlparse(URL).hostname != HOST:
        return None
    request = urllib.request.Request(URL, headers={"Accept": "application/json", "User-Agent": "github-actions-monitor"})
    try:
        with opener(request, timeout=timeout) as answer:
            return parse(json.loads(answer.read(MAX_BYTES).decode("utf-8")))
    except (OSError, ValueError, UnicodeError):
        return None


class Status:
    """What the monitor knows of the state of GitHub: the last good summary, when it was read and the transitions of an Actions incident."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.summary = None
        self.at = 0.0
        self.failed = 0
        self.since = 0.0      # when the incident of Actions was first seen (0 = none)
        self.next_at = 0.0
        self.mark = True      # `github_status.mark_reds` as of the last turn

    def update(self, summary, now=None):
        """Takes a read (None = it failed). Returns "start" when an incident of Actions began, "over" when it ended, else ""."""
        now = time.time() if now is None else now
        with self.lock:
            if summary is None:
                self.failed += 1
                return ""
            self.failed = 0
            was = self.since > 0
            self.summary, self.at = summary, now
            if summary["actions"] and not was:
                self.since = now
                return "start"
            if not summary["actions"] and was:
                self.since = 0.0
                return "over"
            return ""

    def tick(self, opener, config, now=None):
        """One turn of the loop: reads when it is time (and only when switched on). Returns the transition ("start", "over" or "")."""
        now = time.time() if now is None else now
        cfg = settings(config)
        with self.lock:
            self.mark = cfg["mark_reds"]
            if not cfg["enabled"] or now < self.next_at:
                return ""
            self.next_at = now + cfg["interval_seconds"]
        return self.update(fetch(opener), now)

    def incident(self):
        """True while GitHub Actions has an incident and the marking of reds is on."""
        with self.lock:
            return self.since > 0 and self.mark

    def snapshot(self, config=None, now=None):
        now = time.time() if now is None else now
        cfg = settings(config)
        with self.lock:
            summary = self.summary
            return {"enabled": cfg["enabled"], "ok": summary is not None and self.failed == 0, "indicator": summary["indicator"] if summary else "", "description": summary["description"] if summary else "",
                    "components": dict(summary["components"]) if summary else {}, "incidents": list(summary["incidents"]) if summary else [], "actions_incident": self.since > 0,
                    "incident_seconds": int(now - self.since) if self.since > 0 else 0, "age_seconds": int(now - self.at) if self.at else None, "failed_reads": self.failed}


STATUS = Status()
