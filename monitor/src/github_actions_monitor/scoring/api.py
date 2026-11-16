# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What `GET /api/score` and `GET /api/score/history` answer, for the account of the process. Read only: the answers come from the snapshots the pass of the score wrote, nothing is
computed or read from GitHub here. Who may ask is decided before this code runs: the request is served only to somebody who may see the account (the same filter as the alerts).

Every answer of /api/score carries `state`, `coverage` and `data_quality` (a missing number is null, never 0), and `complete: false` with `missing_parts` while a part of the design is not
collected yet, so a reader of the API cannot take a number for more than it is.
"""
import time

from github_actions_monitor.scoring import engine

SCHEMA = 1
STALE_AFTER = 3 * 3600          # a snapshot older than this is said to be old (the pass writes one every few minutes)
MAX_POINTS = 2000
HISTORY_FIELDS = ("hour", "at", "state", "score", "letter", "coverage", "window_days")


def _parse_int(value, low, high, default):
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def empty(account, cfg, reason):
    """The answer when there is no snapshot to show: the score is off, or nothing was written yet."""
    state = "off" if not cfg["enabled"] else "calibrating"
    return {"schema": SCHEMA, "account": account, "enabled": cfg["enabled"], "state": state, "score": None, "letter": None, "trend": None, "coverage": 0.0,
            "complete": False, "missing_parts": list(engine.MISSING_PARTS), "window_days": cfg["window_days"], "parts": [], "repos": [], "at": None, "age_seconds": None, "stale": False,
            "data_quality": {"runs": 0, "min_runs": cfg["min_runs"], "coverage": 0.0, "min_coverage": cfg["min_coverage"], "watched_hours": None, "calibrating_hours": cfg["calibrating_hours"], "reasons": [reason]}}


def latest(storage, account, config, now=None):
    """The newest snapshot of the account in the shape of the API."""
    now = time.time() if now is None else now
    cfg = engine.settings(config)
    if not cfg["enabled"]:
        return empty(account, cfg, "off")
    rows = storage.load_score_snapshots(account, limit=1)
    if not rows:
        return empty(account, cfg, "no_snapshot_yet")
    snap = rows[0]
    age = max(0, int(now - snap["at"])) if isinstance(snap.get("at"), (int, float)) else None
    out = {k: v for k, v in snap.items() if k != "hour"}
    out.update(schema=SCHEMA, account=account, enabled=True, age_seconds=age, stale=age is None or age > STALE_AFTER)
    out.setdefault("complete", False)
    out.setdefault("missing_parts", list(engine.MISSING_PARTS))
    return out


def history(storage, account, config, ask=None, now=None):
    """The points of the score over time, oldest first: `?hours=` back from now (default the window of the account, at most 90 days) and `?limit=` points (the newest, at most 2000)."""
    now = time.time() if now is None else now
    ask = ask or {}
    cfg = engine.settings(config)
    hours = _parse_int(ask.get("hours"), 1, 24 * 90, cfg["window_days"] * 24)
    limit = _parse_int(ask.get("limit"), 1, MAX_POINTS, MAX_POINTS)
    since = time.strftime("%Y-%m-%dT%H", time.gmtime(now - hours * 3600))
    rows = storage.load_score_snapshots(account, since=since, limit=limit) if cfg["enabled"] else []
    points = [{k: row.get(k) for k in HISTORY_FIELDS} for row in rows]
    return {"schema": SCHEMA, "account": account, "enabled": cfg["enabled"], "hours": hours, "points": points}
