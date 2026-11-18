# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The figures of one window, computed from the ledger and the snapshots of the score. Pure functions.

  red_rate          failures / (successes + failures) of the finished runs that started in the window (cancelled, skipped and unfinished runs count neither way)
  duration_p50      median seconds of the successful runs
  resolution        median seconds an alert of the collaboration sentinel took to close (only the ones closed in the window; see resolution.py)
  score_mean        mean of the score of the hourly snapshots that had a number
  score_coverage    mean share of the score that had data (what `coverage` of the snapshots says)

A figure with too little behind it is None with the reason in `missing`; it is never 0 and never 100. Every figure respects the calendar filter (`days`)."""
from datetime import datetime, timezone

from github_actions_monitor.compare import resolution, windows
from github_actions_monitor.data_pipeline.analytics import BAD, percentile

METRICS = ("red_rate", "duration_p50", "resolution", "score_mean", "score_coverage")
LOWER_IS_BETTER = {"red_rate": True, "duration_p50": True, "resolution": True, "score_mean": False, "score_coverage": False}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value


def snapshot_time(snap):
    """Epoch seconds of a snapshot: its `at`, else its hour ("2026-11-20T12", UTC); None when neither can be read."""
    if _number(snap.get("at")):
        return float(snap["at"])
    try:
        return datetime.strptime(str(snap.get("hour")), "%Y-%m-%dT%H").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def window_runs(ledger, window, days, workdays, zone=None):
    """The finished runs of the ledger that started in the window on a day the filter keeps: [(started, conclusion, seconds, repo, workflow)]."""
    start, end = window
    rows = []
    for row in (ledger.get("runs") or {}).values():
        if isinstance(row, list) and len(row) == 5 and _number(row[0]) and start <= row[0] < end and windows.day_matches(row[0], days, workdays, zone):
            rows.append(row)
    return rows


def window_snapshots(snapshots, window, days, workdays, zone=None):
    start, end = window
    rows = []
    for snap in snapshots or []:
        moment = snapshot_time(snap) if isinstance(snap, dict) else None
        if moment is not None and start <= moment < end and windows.day_matches(moment, days, workdays, zone):
            rows.append(snap)
    return rows


def compute(ledger, snapshots, window, days, cfg, zone=None):
    """{"values": {metric: number or None}, "missing": {metric: reason}, "samples": {...}} for one window."""
    workdays = cfg["workdays"]
    runs = window_runs(ledger, window, days, workdays, zone)
    good = [r for r in runs if r[1] == "success"]
    bad = [r for r in runs if r[1] in BAD]
    judged = len(good) + len(bad)
    seconds = [r[2] for r in good if _number(r[2]) and r[2] > 0]
    collab = resolution.summarize(ledger.get("collab"), window, days, workdays, zone)
    snaps = window_snapshots(snapshots, window, days, workdays, zone)
    scored = [s["score"] for s in snaps if s.get("state") == "scored" and _number(s.get("score"))]
    covered = [s["coverage"] for s in snaps if _number(s.get("coverage"))]
    values, missing = {}, {}

    def put(name, value, enough, reason):
        values[name] = value if enough else None
        if not enough:
            missing[name] = reason

    put("red_rate", len(bad) / judged if judged else None, judged >= cfg["min_runs_per_window"], "few_runs")
    put("duration_p50", percentile(seconds, 50) if seconds else None, judged >= cfg["min_runs_per_window"] and bool(seconds), "few_runs")
    put("resolution", collab["median_seconds"], collab["resolved"] >= cfg["min_resolved"], "few_resolved")
    put("score_mean", round(sum(scored) / len(scored), 1) if scored else None, len(scored) >= cfg["min_snapshots"], "few_snapshots")
    put("score_coverage", round(sum(covered) / len(covered), 3) if covered else None, len(covered) >= cfg["min_snapshots"], "few_snapshots")
    samples = {"runs": judged, "durations": len(seconds), "resolved": collab["resolved"], "alerts_opened": collab["opened"], "alerts_open_at_end": collab["open_at_end"], "snapshots": len(scored)}
    return {"values": values, "missing": missing, "samples": samples}


def humanize(name, value):
    """A figure as text for people: shares as a percentage, durations as time, the rest as a plain number; a missing one as a dash."""
    if not _number(value):
        return "-"
    if name in ("red_rate", "score_coverage"):
        return f"{value * 100:.1f}%"
    if name in ("duration_p50", "resolution"):
        seconds = int(value)
        return f"{seconds // 3600} h {seconds % 3600 // 60} min" if seconds >= 3600 else (f"{seconds // 60} min" if seconds >= 60 else f"{seconds} s")
    return f"{value:g}"


def direction(name, now, base):
    """`better`, `worse` or `same` for a figure that exists in both windows (a change smaller than a thousandth counts as the same)."""
    if not (_number(now) and _number(base)):
        return "unknown"
    if abs(now - base) < 1e-3:
        return "same"
    return "better" if (now < base) == LOWER_IS_BETTER[name] else "worse"
