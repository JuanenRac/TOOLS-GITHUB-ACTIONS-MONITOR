# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One list of alerts for every sentinel, and the local silencing of them (1.7.3).

`collect()` puts the alerts of all the sentinels of the registry (CI and Collab) in one list, in the shape of `sentinel_base.Alert`, each one marked with whether it is silenced and until
when. `GET /api/alerts` serves it (`?sentinel=ci|collab`, `?level=`, `?muted=show|hide|only`) and the Alerts tab draws it; the command line reads the same endpoint.

Silencing is local, a note of this monitor and never a change on GitHub. It has a scope (this alert, a rule code, or a whole sentinel), an end (a number of hours, `alerts.mute_hours` by
default, at most `MAX_HOURS`) and it lapses by itself. A silence of one alert can also be "until the item changes" (`until_change`): it keeps the `updated_at` that the alert carried and ends
at once when that value changes (a new comment, a push), or at the usual end of the hours, whichever comes first. What was silenced stays in a short history, so it is visible who muted what and until when. Nothing here reads GitHub.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from github_actions_monitor.data_pipeline import alertflow
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import state_io

from github_actions_monitor.util import paths
STATE_FILE = paths.place("alert_mutes.json")      # an account moves it into its own folder (accounts.STATE_FILES)
SCOPES = ("alert", "code", "sentinel")
DEFAULT_HOURS = 24
MAX_HOURS = 720
HISTORY = 100
SEEN_MAX = 500               # alerts followed in the ledger of what was open (the oldest closed ones go first)
SEEN_KEEP_DAYS = 90          # a closed alert stays this long in the ledger
RESOLVE_GRACE = 600          # seconds an alert must be missing before it counts as resolved (a restart or a cycle that has not run yet is not a resolution)
TOUCH_EVERY = 300            # seconds between two writes of "still open"
LOCK = threading.RLock()


def hours_setting(config):
    """The default length of a silence in hours (`alerts.mute_hours`), kept inside 1..MAX_HOURS."""
    value = ((config or {}).get("alerts") or {}).get("mute_hours") if isinstance((config or {}).get("alerts"), dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_HOURS else DEFAULT_HOURS


def _load():
    try:
        data = state_io.load_json(STATE_FILE)
        if isinstance(data, dict) and isinstance(data.get("active"), list) and isinstance(data.get("history"), list):
            return {"active": [e for e in data["active"] if _valid_entry(e)], "history": [e for e in data["history"] if isinstance(e, dict) and isinstance(e.get("value"), str)],
                    "seen": _clean_seen(data.get("seen"))}
    except (OSError, ValueError):
        pass
    return {"active": [], "history": [], "seen": {}}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _clean_seen(raw):
    """The ledger of the alerts seen, read back: only rows with the two moments and the right types (a file edited by hand never breaks the Alerts tab)."""
    out = {}
    for key, row in (raw.items() if isinstance(raw, dict) else []):
        if isinstance(key, str) and isinstance(row, dict) and _number(row.get("first_seen")) and _number(row.get("last_seen")):
            out[key] = {"code": str(row.get("code") or "")[:80], "sentinel": str(row.get("sentinel") or "")[:30], "repo": str(row.get("repo") or "")[:140], "level": str(row.get("level") or "")[:12],
                        "title": str(row.get("title") or "")[:160], "first_seen": float(row["first_seen"]), "last_seen": float(row["last_seen"]),
                        "resolved_at": float(row["resolved_at"]) if _number(row.get("resolved_at")) else None,
                        "missing_since": float(row["missing_since"]) if _number(row.get("missing_since")) else None}
    return out


def _valid_entry(entry):
    """A silence read from the file: the right types, a known scope and an end. Anything else is dropped (a file edited by hand never breaks the Alerts tab)."""
    return (isinstance(entry, dict) and entry.get("scope") in SCOPES and isinstance(entry.get("value"), str) and bool(entry["value"])
            and isinstance(entry.get("until_ts"), int) and not isinstance(entry.get("until_ts"), bool) and isinstance(entry.get("until"), str))


def _save(data):
    try:
        state_io.save_text(STATE_FILE, json.dumps(data, ensure_ascii=False))
        return True
    except OSError:
        return False


def _iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_value(value):
    return str(value or "").strip()[:200]


def mute(scope, value, hours=None, config=None, now=None, who="", until_change=None):
    """Silences one alert id, one rule code or one sentinel for `hours` (default from the settings). Returns the entry, or None when the scope or the value is not valid.
    `until_change` is the `updated_at` the alert carries now (a string): only for the scope `alert`, the silence ends as soon as the alert carries another one."""
    value = _clean_value(value)
    if scope not in SCOPES or not value:
        return None
    now = time.time() if now is None else now
    length = hours if isinstance(hours, int) and not isinstance(hours, bool) and 1 <= hours <= MAX_HOURS else hours_setting(config)
    entry = {"scope": scope, "value": value, "from": _iso(now), "until": _iso(now + length * 3600), "until_ts": int(now + length * 3600), "hours": length, "who": str(who or "")[:60]}
    if scope == "alert" and isinstance(until_change, str) and until_change.strip():
        entry["until_change"] = until_change.strip()[:40]
    with LOCK:
        data = _load()
        data["active"] = [e for e in data["active"] if not (e.get("scope") == scope and e.get("value") == value)] + [entry]
        data["history"] = (data["history"] + [dict(entry, ended=None)])[-HISTORY:]
        if not _save(data):
            return None      # the file could not be written: the caller must not say "saved"
    return entry


def unmute(scope, value, now=None):
    """Lifts a silence early. True when there was one."""
    value, now = _clean_value(value), time.time() if now is None else now
    with LOCK:
        data = _load()
        keep = [e for e in data["active"] if not (e.get("scope") == scope and e.get("value") == value)]
        found = len(keep) != len(data["active"])
        if found:
            for item in reversed(data["history"]):
                if item.get("scope") == scope and item.get("value") == value and not item.get("ended"):
                    item["ended"] = _iso(now)
                    break
            data["active"] = keep
            if not _save(data):
                return False
    return found


def active(now=None):
    """The silences that have not lapsed. The lapsed ones are dropped from the active list (they stay in the history)."""
    now = time.time() if now is None else now
    with LOCK:
        data = _load()
        live = [e for e in data["active"] if isinstance(e.get("until_ts"), int) and e["until_ts"] > now]
        if len(live) != len(data["active"]):
            data["active"] = live
            _save(data)
    return live


def history(limit=30):
    with LOCK:
        return list(reversed(_load()["history"]))[:limit]


def covering(alert, live):
    """The silences that cover this alert."""
    return [e for e in live if (e["scope"] == "alert" and e["value"] == alert.get("id") and not changed(e, alert)) or (e["scope"] == "code" and e["value"] == alert.get("code"))
            or (e["scope"] == "sentinel" and e["value"] == alert.get("sentinel"))]


def muted_until(alert, live):
    """The end of the silence that covers this alert (the longest one that does), or None."""
    ends = [e["until"] for e in covering(alert, live)]
    return max(ends) if ends else None


def muted_by(alert, live):
    """Who made the silence that lasts longest on this alert ('' when nobody is named: the individual mode, or no silence)."""
    found = covering(alert, live)
    return str(max(found, key=lambda e: e["until"]).get("who") or "") if found else ""


def changed(entry, alert):
    """True when a silence "until the item changes" no longer applies: the `updated_at` the alert carries now is not the one it carried when the silence began."""
    kept = entry.get("until_change")
    if not kept:
        return False
    now = (alert.get("details") or {}).get("updated") if isinstance(alert.get("details"), dict) else None
    return bool(now) and str(now) != kept


def track(alerts, now=None, complete=True):
    """The ledger of what was open (`alerts --since`): every alert present keeps its first and last moment; one that is missing is closed only after it has been missing for RESOLVE_GRACE seconds
    (and only when the list is `complete`: a sentinel that failed to answer closes nothing, because not looking is not fixing). An alert that comes back after it was closed starts a new row.
    Returns True when something was written. Nothing here reads GitHub."""
    now = time.time() if now is None else now
    present = {a["id"]: a for a in alerts if isinstance(a, dict) and isinstance(a.get("id"), str) and a["id"]}
    with LOCK:
        data = _load()
        seen, changed = data["seen"], False
        for key, alert in present.items():
            row = seen.get(key)
            fresh = {"code": str(alert.get("code") or "")[:80], "sentinel": str(alert.get("sentinel") or "")[:30], "repo": str(alert.get("repo") or "")[:140], "level": str(alert.get("level") or "")[:12],
                     "title": str(alert.get("title") or "")[:160], "first_seen": now, "last_seen": now, "resolved_at": None, "missing_since": None}
            if row is None or row["resolved_at"] is not None:
                seen[key], changed = fresh, True
            elif row["missing_since"] is not None or now - row["last_seen"] >= TOUCH_EVERY or row["level"] != fresh["level"]:
                row.update(level=fresh["level"], title=fresh["title"], last_seen=now, missing_since=None)
                changed = True
        if complete:
            for key, row in seen.items():
                if key in present or row["resolved_at"] is not None:
                    continue
                if row["missing_since"] is None:
                    row["missing_since"], changed = now, True
                elif now - row["missing_since"] >= RESOLVE_GRACE:
                    row["resolved_at"], changed = row["missing_since"], True
        old = [k for k, r in seen.items() if r["resolved_at"] is not None and now - r["resolved_at"] > SEEN_KEEP_DAYS * 86400]
        if len(seen) - len(old) > SEEN_MAX:
            old += sorted((k for k in seen if k not in old), key=lambda k: (seen[k]["resolved_at"] is None, seen[k]["last_seen"]))[:len(seen) - len(old) - SEEN_MAX]
        for key in old:
            del seen[key]
            changed = True
        return bool(changed and _save(data))


def parse_since(text):
    """Seconds of a length like 90m, 24h, 7d or 2w (a bare number is seconds), at most SEEN_KEEP_DAYS days; None when it is not one."""
    import re
    match = re.fullmatch(r"\s*(\d{1,6})\s*([smhdw]?)\s*", str(text or "").lower())
    if not match:
        return None
    seconds = int(match.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[match.group(2)]
    return seconds if 0 < seconds <= SEEN_KEEP_DAYS * 86400 else None


def recent(seconds, sentinel="", level="", now=None):
    """The ledger rows that were open at some moment of the last `seconds`, newest first: {"id", "code", "sentinel", "repo", "level", "title", "first_seen", "last_seen", "resolved_at", "state"}
    with the moments as ISO text and `state` "open" or "resolved"."""
    now = time.time() if now is None else now
    cutoff, rows = now - seconds, []
    with LOCK:
        seen = _load()["seen"]
    for key, row in seen.items():
        end = row["resolved_at"] if row["resolved_at"] is not None else now
        if end < cutoff or (sentinel and row["sentinel"] != sentinel) or (level and row["level"] != level):
            continue
        rows.append({"id": key, "code": row["code"], "sentinel": row["sentinel"], "repo": row["repo"] or None, "level": row["level"], "title": row["title"], "first_seen": _iso(row["first_seen"]),
                     "last_seen": _iso(row["last_seen"]), "resolved_at": _iso(row["resolved_at"]) if row["resolved_at"] is not None else None,
                     "state": "resolved" if row["resolved_at"] is not None else "open"})
    return sorted(rows, key=lambda r: r["first_seen"], reverse=True)


def collect(registry, now=None, extra=()):
    """Every alert of every sentinel of the registry, each with `muted_until` (None when it is not silenced). A sentinel that fails leaves its alerts out and the others still answer. `extra` are the
    alerts of the system itself (a login of GitHub that no longer works): they belong to no sentinel, carry `sentinel: "system"` and are listed even when there is no registry."""
    live, out = active(now), []
    alerts, complete = [], registry is not None
    if registry is not None:
        try:
            alerts = list(registry.alerts())
        except Exception:       # noqa: BLE001 - the list is for reading; one broken sentinel must not blank the tab
            alerts, complete = [], False
    alerts = list(extra or ()) + alerts
    for alert in alerts:
        if isinstance(alert, dict) and alert.get("id"):
            row = dict(alert, muted_until=muted_until(alert, live), muted_by=muted_by(alert, live))
            hit = permanent(alert)
            if hit:      # a permanent silence by pattern (alerts.silences): it has no end, and says why
                row.update(muted_until=row["muted_until"] or alertflow.FOREVER, muted_permanent=True, muted_reason=hit["reason"], muted_review_by=hit["review_by"])
            out.append(row)
    try:
        track(out, now, complete)      # what was open and when (alerts --since); a failure to write it never costs the list
    except Exception:       # noqa: BLE001
        pass
    return out


def permanent(alert):
    """The silence by pattern (alerts.silences) that covers this alert, else None. Only the alerts of a workflow (red, stuck) have something to match."""
    if not alert.get("repo") or alert.get("code") not in alertflow.SILENCE_ALERT_CODES:
        return None
    details = alert.get("details") if isinstance(alert.get("details"), dict) else {}
    return alertflow.silence_of(alert["repo"], (details.get("workflow"), details.get("name"), details.get("file")), details.get("branch"))


def select(alerts, sentinel="", level="", muted="show"):
    """The filters of the endpoint: sentinel name, level, and whether to show (`show`), hide (`hide`) or only list (`only`) the silenced ones."""
    chosen = [a for a in alerts if (not sentinel or a.get("sentinel") == sentinel) and (not level or a.get("level") == level)]
    if muted == "hide":
        chosen = [a for a in chosen if not a.get("muted_until")]
    elif muted == "only":
        chosen = [a for a in chosen if a.get("muted_until")]
    order = {"critical": -1, "error": 0, "warning": 1, "info": 2}
    return sorted(chosen, key=lambda a: (order.get(a.get("level"), 3), str(a.get("created_at") or ""), a.get("id", "")))


def summary(alerts):
    """Counts by sentinel and level, silenced ones apart: the figures of the filter chips."""
    out = {"total": 0, "muted": 0, "by_sentinel": {}, "by_level": {}}
    for a in alerts:
        if a.get("muted_until"):
            out["muted"] += 1
            continue
        out["total"] += 1
        out["by_sentinel"][a.get("sentinel", "")] = out["by_sentinel"].get(a.get("sentinel", ""), 0) + 1
        out["by_level"][a.get("level", "")] = out["by_level"].get(a.get("level", ""), 0) + 1
    return out


def read_events(path, sentinel="", since="", limit=200):
    """The latest events of the events file (newest first), filtered by sentinel and by a start time (`since`, ISO text). Nothing is read from GitHub; a damaged line is skipped."""
    rows = []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()[-2000:]
    except OSError:
        return rows
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if sentinel and event.get("sentinel", "ci") != sentinel:
            continue
        if since and str(event.get("at") or "") < since:
            break
        rows.append(event)
        if len(rows) >= limit:
            break
    return rows
