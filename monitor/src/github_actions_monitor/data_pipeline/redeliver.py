# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Recovering the deliveries a switched-off computer missed.

A monitor at home is not always on: the computer is off at night, the tunnel drops, the process restarts. GitHub keeps the recent deliveries of a webhook and says which ones failed, and lets a
failed one be sent again. This reads that list for the webhooks you name and asks GitHub to send again the ones that never arrived, with a limit and without repeating itself. OFF by default and it
WRITES to GitHub (the request to deliver again), so it needs a token that can manage the webhook.

  webhook.redeliver.enabled        off by default
  webhook.redeliver.hooks          the webhooks to look at, `repo:OWNER/REPO#ID` or `org:OWNER#ID` (the id is the number in the address of the webhook in GitHub); empty by default
  webhook.redeliver.max_per_run    at most this many deliveries are asked for again in one run (20 by default)
  webhook.redeliver.max_age_hours  older deliveries are left alone (24 by default; GitHub keeps them for three days)
  webhook.redeliver.interval_minutes  how often it looks (60 by default) after the first look a minute after start

A delivery counts as lost when none of its attempts (the same `guid`) was answered 2xx. Each is asked for again with a growing wait (5, 10, 20, 40, 80, 160 and 300 seconds between asks, counted
from the first look) and after the eighth ask it is left as `dead` and never asked again. What was asked is remembered in a private file (the guid, the number of asks and the state; never a payload),
so a restart does not ask again for what was already asked.
Applications that use a GitHub App (the deliveries of the App are read with its key, not with a token) are not covered here. Standard library only; the reads and the asks are given by the caller.
"""
import calendar
import json
import re
import threading
import time

DEFAULTS = {"enabled": False, "hooks": [], "max_per_run": 20, "max_age_hours": 24, "interval_minutes": 60}
SCHEDULE = (5, 10, 20, 40, 80, 160, 300)      # seconds to wait before asking again, after the first ask, the second...
MAX_ASKS = 8
HOOK_RE = re.compile(r"^(repo:[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}|org:[A-Za-z0-9-]{1,39})#([0-9]{1,12})\Z")
GUID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}\Z")
MAX_STATE = 2000


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = ((config or {}).get("webhook") or {}).get("redeliver") if isinstance((config or {}).get("webhook"), dict) else None
    block = block if isinstance(block, dict) else {}
    hooks = []
    for item in block.get("hooks") if isinstance(block.get("hooks"), list) else []:
        if isinstance(item, str) and HOOK_RE.match(item.strip()) and item.strip() not in hooks:
            hooks.append(item.strip())
    return {"enabled": block.get("enabled") is True, "hooks": hooks[:20], "max_per_run": _int(block.get("max_per_run"), 1, 100, DEFAULTS["max_per_run"]),
            "max_age_hours": _int(block.get("max_age_hours"), 1, 72, DEFAULTS["max_age_hours"]), "interval_minutes": _int(block.get("interval_minutes"), 5, 1440, DEFAULTS["interval_minutes"])}


def base_of(hook):
    """The address of the deliveries of a hook: `repos/OWNER/REPO/hooks/ID` or `orgs/OWNER/hooks/ID`."""
    found = HOOK_RE.match(hook)
    scope, ident = found.group(1), found.group(2)
    return ("repos/" + scope[5:] if scope.startswith("repo:") else "orgs/" + scope[4:]) + "/hooks/" + ident


def _stamp(text):
    try:
        return calendar.timegm(time.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ"))
    except (TypeError, ValueError, OverflowError):
        return None


def lost(deliveries, now, max_age_hours):
    """[(guid, delivery id)] of the deliveries that never arrived, newest first: no attempt of the same guid was answered 2xx, the newest attempt is the one to ask again, and it is not older than
    `max_age_hours`. Pure."""
    by_guid = {}
    for item in deliveries if isinstance(deliveries, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int) or not GUID_RE.match(str(item.get("guid", ""))):
            continue
        by_guid.setdefault(item["guid"], []).append(item)
    out = []
    for guid, items in by_guid.items():
        if any(isinstance(i.get("status_code"), int) and 200 <= i["status_code"] < 300 for i in items):
            continue
        newest = max(items, key=lambda i: (i.get("delivered_at") or "", i["id"]))
        moment = _stamp(newest.get("delivered_at"))
        if moment is not None and now - moment > max_age_hours * 3600:
            continue
        out.append((guid, newest["id"], moment or 0))
    out.sort(key=lambda row: -row[2])
    return [(g, i) for g, i, _m in out]


class Recovery:
    def __init__(self, path=None):
        self.lock = threading.Lock()
        self.path = path
        self.reset()

    def reset(self):
        self.state = {}      # guid -> {"asks", "next_at", "state": "asked" | "dead"}
        self.stats = {"runs": 0, "asked": 0, "dead": 0, "errors": 0, "last_at": None, "last_error": "", "hooks": 0}
        self.next_run = 0.0

    def load(self, path):
        from pathlib import Path
        self.path = Path(path)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            return 0
        if not isinstance(data, dict):
            return 0
        with self.lock:
            for guid, row in list(data.items())[-MAX_STATE:]:
                if GUID_RE.match(str(guid)) and isinstance(row, dict) and isinstance(row.get("asks"), int) and row.get("state") in ("asked", "dead"):
                    self.state[guid] = {"asks": min(row["asks"], MAX_ASKS), "next_at": float(row.get("next_at") or 0), "state": row["state"]}
            return len(self.state)

    def save(self):
        if self.path is None:
            return False
        with self.lock:
            snapshot = dict(list(self.state.items())[-MAX_STATE:])
        try:
            from github_actions_monitor.security import private_io
            private_io.write_private(self.path, json.dumps(snapshot, separators=(",", ":")))
        except (OSError, ValueError):
            return False
        return True

    def due(self, guid, now):
        row = self.state.get(guid)
        return row is None or (row["state"] == "asked" and row["asks"] < MAX_ASKS and now >= row["next_at"])

    def asked(self, guid, now):
        with self.lock:
            row = self.state.get(guid) or {"asks": 0, "next_at": 0.0, "state": "asked"}
            row["asks"] += 1
            row["next_at"] = now + SCHEDULE[min(row["asks"] - 1, len(SCHEDULE) - 1)]
            if row["asks"] >= MAX_ASKS:
                row["state"] = "dead"
                self.stats["dead"] += 1
            self.state[guid] = row
            while len(self.state) > MAX_STATE:
                self.state.pop(next(iter(self.state)))

    def run(self, config, run_gh, now=None, force=False):
        """One look at every named hook. `run_gh(args)` = (code, stdout, stderr). Returns how many deliveries were asked for again. Never raises: a failure is counted."""
        now = time.time() if now is None else now
        cfg = settings(config)
        with self.lock:
            if not cfg["enabled"] and not force or not cfg["hooks"]:
                return 0
            if not force and now < self.next_run:
                return 0
            self.next_run = now + cfg["interval_minutes"] * 60
            self.stats["runs"] += 1
            self.stats["last_at"] = now
            self.stats["hooks"] = len(cfg["hooks"])
        asked = 0
        for hook in cfg["hooks"]:
            if asked >= cfg["max_per_run"]:
                break
            base = base_of(hook)
            code, out, err = run_gh(["api", f"{base}/deliveries?per_page=100"])
            if code != 0:
                with self.lock:
                    self.stats["errors"] += 1
                    self.stats["last_error"] = (err or out or "gh failed").strip()[:120]
                continue
            try:
                items = json.loads(out)
            except ValueError:
                items = []
            for guid, ident in sorted(lost(items, now, cfg["max_age_hours"]), key=lambda row: self.state.get(row[0], {}).get("asks", 0)):      # what was never asked for goes first, newest first
                if asked >= cfg["max_per_run"]:
                    break
                if not self.due(guid, now):
                    continue
                code, _o, err = run_gh(["api", "-X", "POST", f"{base}/deliveries/{ident}/attempts"])
                if code == 0:
                    self.asked(guid, now)
                    asked += 1
                else:
                    with self.lock:
                        self.stats["errors"] += 1
                        self.stats["last_error"] = (err or "gh failed").strip()[:120]
        with self.lock:
            self.stats["asked"] += asked
        if asked:
            self.save()
        return asked

    def snapshot(self, config=None):
        cfg = settings(config)
        with self.lock:
            pending = sum(1 for r in self.state.values() if r["state"] == "asked")
            return {"enabled": cfg["enabled"], "hooks": len(cfg["hooks"]), "pending": pending, **self.stats}


RECOVERY = Recovery()
