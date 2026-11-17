# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Is a repository alive? A state of its own, neither green nor red.

A repository that has never had a run (an account that collects forks and bookmarks has hundreds of them) is "no signal", not "healthy", and a repository whose newest run is months old is not healthy
either: counting both as green makes the score a figure of noise, counting them as red makes hundreds of alarms. So each repository is one of

  active    it has a run of its own newer than `ci.inactive_days` days
  dormant   it has never run anything of its own (the list of its runs is complete and holds no run, or only the ones GitHub makes for itself)
  inactive  its newest run of its own is older than `ci.inactive_days` days
  unknown   the monitor could not tell (the read failed, or the list of runs is cut and says nothing)

They are counted apart (`figures.dormant`, `figures.inactive_repos`, `activity` of the data and of the score) and never enter the colours of the header. `ci.dormant_repos` turns the counting off.
Pure functions: no network; the clock is given by the caller."""
import time
from datetime import datetime

from github_actions_monitor.data_pipeline import redrule

STATES = ("active", "dormant", "inactive", "unknown")
SAMPLE_LIMIT = 200      # names listed in the answer; the counts are always complete


def settings(config):
    """{"enabled", "inactive_days"}: `ci.dormant_repos` (on by default) and the days of `ci.inactive_days` (the same limit as for a workflow)."""
    block = (config or {}).get("ci")
    block = block if isinstance(block, dict) else {}
    days = redrule.POLICY["inactive_days"]
    return {"enabled": block.get("dormant_repos") is not False, "inactive_days": days}


def _epoch(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def state_of(runs, total, failed, now, inactive_days):
    """The state of one repository from the runs the monitor holds, the `total_count` GitHub gave for them (None = unknown) and whether the read failed."""
    if failed:
        return "unknown"
    own = [r for r in runs or [] if not redrule.is_dynamic(r)]
    if not own:
        complete = total == 0 or (isinstance(total, int) and not isinstance(total, bool) and len(runs or []) >= total)
        return "dormant" if complete else "unknown"
    newest = max((_epoch(r.get("started")) or 0 for r in own), default=0)
    if inactive_days and newest and now - newest > inactive_days * 86400:
        return "inactive"
    return "active"


def summarize(repos, runs_by_repo, totals, errors, now=None, cfg=None):
    """{"enabled", "inactive_days", "active", "unknown", "dormant": [repos], "inactive": [repos], "counts": {state: n}} for the watched repositories; empty lists when the counting is off."""
    cfg = cfg or {"enabled": True, "inactive_days": redrule.POLICY["inactive_days"]}
    now = time.time() if now is None else now
    out = {"enabled": cfg["enabled"], "inactive_days": cfg["inactive_days"], "active": 0, "unknown": 0, "dormant": [], "inactive": [], "counts": {s: 0 for s in STATES}}
    if not cfg["enabled"]:
        return out
    for repo in repos:
        state = state_of(runs_by_repo.get(repo), (totals or {}).get(repo), bool((errors or {}).get(repo)), now, cfg["inactive_days"])
        out["counts"][state] += 1
        if state in ("dormant", "inactive"):
            out[state].append(repo)
        else:
            out[state] += 1
    out["dormant"], out["inactive"] = sorted(out["dormant"])[:SAMPLE_LIMIT], sorted(out["inactive"])[:SAMPLE_LIMIT]
    return out
