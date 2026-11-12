#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Event feed of the sentinel: turns the difference between two snapshots into one JSON line per thing that CHANGED.

The assistant (or anybody) can follow the file with `tail -F events_monitor.jsonl` and is told the moment something happens, instead of polling.

  events_monitor.jsonl   one JSON object per line: {"at", "kind", "code", "level", "repo", "owner", "text", "url", "args"}
                          `code` is the stable key of the event (it never depends on the language; today it equals `kind`) and `args` the values the text was made
                          from, so a consumer can match on `code` and build its own message; `text` is written in the configured language
  events_state.json     what was already announced (survives restarts, so a restart never floods the feed)

Kinds: red_new, red_fixed, stuck_new, release_due, pending_sign, budget_warn, budget_over, alerts_up, prs_up, rate_low, rate_ok, loaded,
and (1.2.0, from the A10 layer) issue_close_suggest (text of a `gh issue close`, never executed), release_incomplete, workflow_risk, required_check_red,
security_aged, pr_workflow_touch.  Nothing is emitted while the sentinel is still loading.
Only local data is used: it never calls GitHub.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import i18n
import toolconfig

HERE = Path(__file__).resolve().parent
EVENTS_FILE = HERE / "events_monitor.jsonl"
STATE_FILE = HERE / "events_state.json"
MAX_BYTES = 512 * 1024   # the feed is trimmed to its newest half when it grows beyond this
LOW_RATE = 1500
DUE_ENTRIES = 2   # a repository with this many entries under [Unreleased] is due for its version and release


def owner_of(repo):
    """"main" for the ecosystems this tool handles, the ecosystem key for one marked "external" in the ecosystems file (reported, never notified)."""
    key = toolconfig.ecosystem_of(repo or "")
    return key if toolconfig.is_external(key) else "main"


def summarize(snapshot):
    """The few facts the feed cares about, as plain comparable data."""
    a1, a2, a3, a4 = (snapshot.get(k) or {} for k in ("a1", "a2", "a3", "a4"))
    reds = {f"{r.get('repo')}|{r.get('workflow')}": {"repo": r.get("repo"), "workflow": r.get("workflow"), "url": r.get("url"),
                                                     "streak": r.get("streak"), "since": r.get("since")} for r in a2.get("red") or []}
    stuck = {f"{r.get('repo')}|{r.get('name')}": {"repo": r.get("repo"), "name": r.get("name"), "url": r.get("url")} for r in a1.get("stuck") or []}
    alerts = {}
    for row in a3.get("rows") or []:
        alerts[row["repo"]] = [row.get("codeql") or 0, row.get("dependabot") or 0, row.get("secret") or 0,
                               (row.get("sev") or {}).get("critical", 0), (row.get("sev") or {}).get("high", 0)]
    prs = {}
    for pr in a4.get("dependabot") or []:
        prs[pr.get("repo")] = prs.get(pr.get("repo"), 0) + 1
    pending = {f"{g.get('repo')}|{g.get('workflow')}": {"repo": g.get("repo"), "hours": g.get("hours"), "url": g.get("url")} for g in (snapshot.get("a5") or {}).get("pending_sign") or []}
    due = {c.get("repo"): c.get("entries") for c in (snapshot.get("a5") or {}).get("candidates") or [] if (c.get("entries") or 0) >= DUE_ENTRIES}
    rate = (snapshot.get("rate") or {}).get("remaining")
    budget = {b.get("ecosystem"): {"level": b.get("level"), "pct": b.get("pct"), "used": b.get("used"), "limit": b.get("limit"), "period": b.get("period")}
              for b in (snapshot.get("a7") or {}).get("budget") or [] if b.get("level") in ("warn", "over")}
    a10 = {k: v for k, v in ((snapshot.get("a10") or {}).get("events") or {}).items() if isinstance(v, dict)}
    return {"reds": reds, "stuck": stuck, "alerts": alerts, "prs": prs, "rate": rate, "pending": pending, "due": due, "budget": budget, "a10ev": a10}


def diff(old, new, loaded):
    """List of events for what is in `new` and was not in `old`. `old` None = first look: only the baseline is stored."""
    if old is None:
        return []
    events = []

    def ev(kind, level, where, url=None, **args):
        events.append({"kind": kind, "code": kind, "level": level, "repo": where, "owner": owner_of(where), "text": i18n.t("evt." + kind, **args), "url": url, "args": args})

    for key, r in new["reds"].items():
        if key not in old["reds"]:
            ev("red_new", "bad", r["repo"], r.get("url"), repo=r["repo"], workflow=r["workflow"])
    for key, r in old["reds"].items():
        if key not in new["reds"]:
            ev("red_fixed", "ok", r["repo"], r.get("url"), repo=r["repo"], workflow=r["workflow"])
    for key, r in new["stuck"].items():
        if key not in old["stuck"]:
            ev("stuck_new", "bad", r["repo"], r.get("url"), repo=r["repo"], name=r["name"])
    for repo, count in new.get("due", {}).items():
        if repo not in (old.get("due") or {}):
            ev("release_due", "warn", repo, repo=repo, count=count)
    for key, g in new.get("pending", {}).items():
        if key not in (old.get("pending") or {}):
            ev("pending_sign", "warn", g["repo"], g.get("url"), repo=g["repo"], hours=g.get("hours"))
    for eco, b in new.get("budget", {}).items():   # the 80 % warning, and the ceiling itself: each announced once when it is crossed
        was = (old.get("budget") or {}).get(eco, {}).get("level")
        if b["level"] == "over" and was != "over":
            ev("budget_over", "bad", "", eco=eco, used=b["used"], limit=b["limit"], pct=f"{b['pct']:.0f}", period=b["period"])
        elif b["level"] == "warn" and was is None:
            ev("budget_warn", "warn", "", eco=eco, used=b["used"], limit=b["limit"], pct=f"{b['pct']:.0f}", period=b["period"])
    if "a10ev" in old:   # a state saved by an older version has no baseline for these: announcing them all at once would flood the feed
        for key, item in new.get("a10ev", {}).items():
            if key not in old["a10ev"]:
                events.append({"kind": item.get("kind", "a10"), "code": item.get("code") or item.get("kind", "a10"), "level": item.get("level", "info"), "repo": item.get("repo", ""),
                               "owner": owner_of(item.get("repo", "")), "text": item.get("text", ""), "url": item.get("url"), "args": {}})   # the text was made by the A10 layer
    for repo, now in new["alerts"].items():
        before = old["alerts"].get(repo)
        if before is None:
            continue
        if now[0] > before[0] or now[1] > before[1] or now[2] > before[2]:
            ev("alerts_up", "bad" if (now[3] > before[3] or now[4] > before[4] or now[2] > before[2]) else "warn", repo, repo=repo, codeql=f"{before[0]}→{now[0]}",
               dependabot=f"{before[1]}→{now[1]}", secrets=f"{before[2]}→{now[2]}", critical=now[3], high=now[4])
    for repo, count in new["prs"].items():
        if count > old["prs"].get(repo, 0):
            ev("prs_up", "info", repo, repo=repo, change=f"{old['prs'].get(repo, 0)}→{count}")
    if new["rate"] is not None and old["rate"] is not None:
        if new["rate"] < LOW_RATE <= old["rate"]:
            ev("rate_low", "warn", "", left=new["rate"])
        elif old["rate"] < LOW_RATE <= new["rate"]:
            ev("rate_ok", "ok", "", left=new["rate"])
    return events


class Feed:
    def __init__(self, events_file=EVENTS_FILE, state_file=STATE_FILE, notify_command=None):
        self.events_file, self.state_file = Path(events_file), Path(state_file)
        self.notify_command = [str(x) for x in notify_command] if isinstance(notify_command, list) and notify_command else None
        try:
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.state = None
        self.was_loading = True
        self.listeners = []   # functions called with the list of new events (the notifications hang here); a failing one never stops the feed

    def feed(self, snapshot):
        """Call with every snapshot. Returns the events written (possibly none)."""
        if snapshot.get("loading") or not snapshot.get("enabled", True):
            self.was_loading = True
            return []
        new = summarize(snapshot)
        events = diff(self.state, new, True)
        if self.was_loading and self.state is not None:
            events.insert(0, {"kind": "loaded", "code": "loaded", "level": "info", "repo": "", "owner": "main",
                              "text": i18n.t("evt.loaded", reds=len(new["reds"]), rate=new["rate"]), "url": None, "args": {"reds": len(new["reds"]), "rate": new["rate"]}})
        self.was_loading = False
        self.state = new
        self._write_state()
        self._append(events)
        self._notify(events)
        for listener in self.listeners:
            try:
                if events:
                    listener(events)
            except Exception:   # noqa: BLE001 - a notification problem must never stop the feed
                pass
        return events

    def emit(self, events):
        """Writes events that another sentinel made (their own kind, code, text and url) to the same file and gives them to the same listeners (1.7.3). Returns them."""
        events = [e for e in events if isinstance(e, dict) and e.get("kind")]
        self._append(events)
        for listener in self.listeners:
            try:
                if events:
                    listener(events)
            except Exception:   # noqa: BLE001 - a notification problem must never stop the feed
                pass
        return events

    def _notify(self, events):
        """Optional hook (sentinel.notify_command in actions_monitor.json: a list, run WITHOUT a shell with the text as last argument)
        for what asks for a decision: a new red, a stuck build, a build waiting for its signature. Failures are ignored."""
        if not self.notify_command:
            return
        import subprocess
        for event in events:
            if event.get("kind") in ("red_new", "stuck_new", "pending_sign") and event.get("owner") == "main":
                try:
                    subprocess.Popen(self.notify_command + [event["text"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except OSError:
                    pass

    def _write_state(self):
        try:
            tmp = self.state_file.with_name(self.state_file.name + ".tmp")
            tmp.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.state_file)
        except OSError:
            pass

    def _append(self, events):
        if not events:
            return
        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            with open(self.events_file, "a", encoding="utf-8", newline="\n") as handle:
                for event in events:
                    handle.write(json.dumps({"at": at, **event}, ensure_ascii=False) + "\n")
            if self.events_file.stat().st_size > MAX_BYTES:
                lines = self.events_file.read_text(encoding="utf-8").splitlines()
                self.events_file.write_text("\n".join(lines[len(lines) // 2:]) + "\n", encoding="utf-8", newline="\n")
        except OSError:
            pass


def clock():
    return time.time()
