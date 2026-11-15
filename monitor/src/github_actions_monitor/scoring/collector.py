# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""MetricCollector of the score. Pure functions: the runs and the collaboration items go in, plain numbers come out; nothing here reads a file or calls GitHub.

For one window of time [start, end) it computes, from the runs that STARTED inside it:

  success_rate               successes / (successes + failures); cancelled, skipped and unfinished runs are not counted either way
  duration_p50, duration_p95 seconds of the successful runs
  mttr                       median seconds from the first failure of a workflow to its next success (only recoveries that ended inside the window); 0 when the window has runs and no failure at all
                             (nothing had to recover: that is data, not a gap), None while a failure has not recovered yet
  throughput                 finished runs per day
  collab_resolution_time     median seconds an item of the collaboration sentinel stayed open (only items closed inside the window)
  collab_open                items still open at the end of the window

and the amount of data behind every number (`samples`), which the engine needs to say "not enough data" instead of inventing a value. A metric with nothing behind it is None, never 0.
"""
from datetime import datetime, timezone

from github_actions_monitor.data_pipeline.analytics import BAD, percentile

DAY = 86400.0


def to_ts(value):
    """Epoch seconds of an ISO time ("2026-01-02T03:04:05Z" or with an offset) or of a number; None when it cannot be read."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def runs_in_window(runs, start, end):
    """The completed runs that started inside [start, end), oldest first, as (epoch, run); runs with no readable start are left out."""
    out = []
    for run in runs or []:
        if not isinstance(run, dict) or run.get("status") != "completed":
            continue
        t = to_ts(run.get("started"))
        if t is not None and start <= t < end:
            out.append((t, run))
    out.sort(key=lambda pair: (pair[0], str(pair[1].get("repo")), str(pair[1].get("name")), str(pair[1].get("conclusion"))))
    return out


def recoveries(timed_runs):
    """Seconds each workflow stayed red: from its first failure to the next success of the same repository and workflow."""
    open_since, spans = {}, []
    for t, run in timed_runs:
        key = (run.get("repo"), run.get("name"))
        conclusion = run.get("conclusion")
        if conclusion in BAD:
            open_since.setdefault(key, t)
        elif conclusion == "success" and key in open_since:
            spans.append(max(0.0, t - open_since.pop(key)))
    return spans


def collect_runs(runs, start, end):
    """The metrics of the runs of one window (see the module text)."""
    timed = runs_in_window(runs, start, end)
    good = [r for _, r in timed if r.get("conclusion") == "success"]
    bad = [r for _, r in timed if r.get("conclusion") in BAD]
    seconds = [r["seconds"] for r in good if isinstance(r.get("seconds"), (int, float)) and not isinstance(r.get("seconds"), bool) and r["seconds"] > 0]
    spans = recoveries(timed)
    judged = len(good) + len(bad)
    quiet = judged > 0 and not bad
    days = max((end - start) / DAY, 1e-9)
    return {
        "success_rate": (len(good) / judged) if judged else None,
        "duration_p50": percentile(seconds, 50), "duration_p95": percentile(seconds, 95),
        "mttr": percentile(spans, 50) if spans else (0.0 if quiet else None),
        "throughput": (judged / days) if judged else None,
        "samples": {"runs": judged, "durations": len(seconds), "recoveries": len(spans)},
    }


def collect_collab(items, start, end):
    """The metrics of the collaboration items ({"opened", "closed"} as ISO times or numbers; `closed` is None while open) for one window."""
    spans, still_open = [], 0
    for item in items or []:
        if not isinstance(item, dict):
            continue
        opened, closed = to_ts(item.get("opened")), to_ts(item.get("closed"))
        if opened is None or opened >= end:
            continue
        if closed is None or closed >= end:
            still_open += 1
        elif closed >= start:
            spans.append(max(0.0, closed - opened))
    return {"collab_resolution_time": percentile(spans, 50) if spans else None, "collab_open": still_open,
            "samples": {"collab_closed": len(spans), "collab_open": still_open}}


def collect(runs, collab_items, start, end):
    """Every metric of the window, with the samples of both parts merged."""
    a, b = collect_runs(runs, start, end), collect_collab(collab_items, start, end)
    merged = {k: v for k, v in a.items() if k != "samples"}
    merged.update({k: v for k, v in b.items() if k != "samples"})
    merged["samples"] = {**a["samples"], **b["samples"]}
    merged["window"] = {"start": start, "end": end}
    return merged


def by_repo(runs, start, end):
    """The run metrics of each repository, so the detail can break the account down: {repo: metrics}."""
    groups = {}
    for run in runs or []:
        if isinstance(run, dict) and isinstance(run.get("repo"), str):
            groups.setdefault(run["repo"], []).append(run)
    return {repo: collect_runs(items, start, end) for repo, items in sorted(groups.items())}
