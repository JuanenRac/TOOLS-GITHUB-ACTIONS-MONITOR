# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""How much of a repository the list of runs really shows. Standard library only; pure functions plus a small counter of requests (block `sampling`).

A busy repository can start hundreds of runs an hour, so the newest 20-100 runs may span only a few minutes: a workflow that ran earlier is not in the sample and the picture is not
"all green" but "nothing seen". This module says it instead of hiding it:

  coverage     for each repository, how far back in time the sample reaches (`window_seconds`), whether the list is complete (shorter than what was asked for: the whole history is in it),
               whether the total GitHub reports is a floor (`at_least`: GitHub stops counting at 2,500 or 40,000) and whether the coverage is low (shorter than
               `sampling.min_coverage_minutes`; 0 turns the mark off).
  second probe `sampling.default_branch_probe` (off by default): a repository whose sample is full also asks for `branch=<default>&event=push&exclude_pull_requests=true`, one more
               request, so the runs that decide "red on main" are not pushed out of the sample by pull requests and schedules. The runs that only came from the probe are marked
               `probe` and never make a list "full".
  budget       `sampling.api_budget_per_hour` (0 = no budget): requests for run lists per hour. Past it the monitor goes on in order: repositories with a red workflow first, the
               others wait (a tenth of the budget is always kept for the red ones). `estimate_per_hour` tells, from the number of repositories and the intervals, what a setup will
               spend, so a large account is warned before it runs out of allowance.
"""
import time
from collections import deque

CAPPED_TOTALS = (2500, 40000)      # GitHub stops counting here: the real number is "at least" this
HOUR = 3600.0


def _int(block, key, low, high, default):
    value = block.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = config.get("sampling") if isinstance(config, dict) and isinstance(config.get("sampling"), dict) else {}
    return {"default_branch_probe": block.get("default_branch_probe") is True, "min_coverage_minutes": _int(block, "min_coverage_minutes", 0, 10080, 30),
            "api_budget_per_hour": _int(block, "api_budget_per_hour", 0, 100000, 0)}


def _stamp(text):
    from datetime import datetime, timezone
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() if text else None
    except (TypeError, ValueError):
        return None


def coverage(runs, asked, total=None, min_minutes=30, now=None):
    """What the sample of one repository covers. `asked` = how many runs were requested (None = unknown), `total` = the total_count of GitHub (None = unknown).
    -> {"runs", "complete", "window_seconds", "total", "at_least", "low"}; `window_seconds` is None when the list is complete (it reaches the beginning of the history)."""
    now = time.time() if now is None else now
    own = [r for r in runs or [] if not r.get("probe")]
    stamps = [t for t in (_stamp(r.get("started")) for r in own) if t is not None]
    full = bool(asked) and len(own) >= asked
    window = max(0.0, now - min(stamps)) if (full and stamps) else None
    at_least = total in CAPPED_TOTALS
    low = bool(full and min_minutes > 0 and window is not None and window < min_minutes * 60)
    return {"runs": len(runs or []), "complete": not full, "window_seconds": None if window is None else round(window), "total": total, "at_least": bool(at_least), "low": low}


def merge_probe(base, extra):
    """The runs of the probe that the base list does not have (by id), marked `probe`, joined to it and sorted newest first."""
    seen = {r.get("id") for r in base}
    added = [dict(r, probe=True) for r in extra if r.get("id") not in seen]
    return sorted(list(base) + added, key=lambda r: r.get("started") or "", reverse=True), len(added)


def estimate_per_hour(repos, refresh_seconds, cold_refresh_seconds, hot_share=0.2, probe=False):
    """Requests per hour for run lists: `hot_share` of the repositories read every `refresh_seconds`, the rest every `cold_refresh_seconds` (+ the probe of the busy ones)."""
    repos = max(0, int(repos))
    hot = repos * hot_share
    calls = hot * HOUR / max(1, refresh_seconds) + (repos - hot) * HOUR / max(1, cold_refresh_seconds)
    return int(round(calls * (1.5 if probe else 1.0)))


class Budget:
    """Requests of the last hour (memory only)."""

    def __init__(self):
        self.stamps = deque()

    def record(self, count=1, now=None):
        now = time.time() if now is None else now
        self.stamps.extend([now] * max(0, int(count)))
        self.trim(now)

    def trim(self, now):
        while self.stamps and now - self.stamps[0] > HOUR:
            self.stamps.popleft()

    def used(self, now=None):
        now = time.time() if now is None else now
        self.trim(now)
        return len(self.stamps)


def plan(todo, red, limit, used, cost=None):
    """(kept, dropped) of the reads of a cycle under a budget. todo = [(repo, ...)]; red = set of repositories with a red workflow. limit 0 = no budget: everything is kept.
    Repositories with red go first; a tenth of the budget is kept for them even when the rest is spent. `cost(item)` is how many requests reading that repository will make (1 when it is not given):
    a second look at the pushes to the default branch costs one more, and the budget counts requests, not repositories."""
    if limit <= 0:
        return list(todo), []
    left = max(0, limit - used)
    reserve = max(1, limit // 10)
    room_red = max(0, limit + reserve - used)      # the reserve of the reds belongs to the HOUR: what the hour has already spent (the reds of the cycles before included) is not given again every cycle
    ordered = [t for t in todo if t[0] in red] + [t for t in todo if t[0] not in red]
    kept, dropped, spent = [], [], 0
    for item in ordered:
        price = max(1, int(cost(item))) if cost else 1
        if item[0] in red and spent < room_red:
            kept.append(item)
            spent += price
        elif spent < left:
            kept.append(item)
            spent += price
        else:
            dropped.append(item)
    return kept, dropped
