# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The limits of the monitor against what it is asked to do: a table of ceilings with how much of each one is used, for the doctor (`capacity`) and for /metrics (`ghamon_limit_used_percent`).

Two views of the same table:
  * `planned(config, repos)`   from the configuration only (no monitor needs to run): the reads an hour the setup will cost against the allowance (and the budget of the sampler), the memory the held
                               runs will take against `limits.memory_mb`, and the repositories against `discover_limit`;
  * `live(config, figures)`    from what the running monitor holds: events kept, live streams, reads waiting in the queue, series of the histograms.
Every row is {"id", "used", "limit", "percent", "level"} with level ok | warn | bad: warn from `limits.warn_percent` of the ceiling (80 by default), bad from 100. Read only: nothing is changed or sent.
"""
from github_actions_monitor.data_pipeline import sampling

DEFAULTS = {"warn_percent": 80, "memory_mb": 512}
RUN_BYTES = 1500          # what a run held in memory takes, rounded up (the dictionary of a run with its short fields)
CORE_ALLOWANCE = 5000     # calls an hour of a normal login; the page shows the real limit read from GitHub, this is only the ceiling the planner compares with when none is known


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = config.get("limits") if isinstance(config, dict) and isinstance(config.get("limits"), dict) else {}
    return {"warn_percent": _int(block.get("warn_percent"), 50, 99, DEFAULTS["warn_percent"]), "memory_mb": _int(block.get("memory_mb"), 64, 65536, DEFAULTS["memory_mb"])}


def row(name, used, limit, warn_percent):
    """One row; a ceiling of 0 or None means no ceiling and the row is left out by the caller."""
    percent = round(100.0 * used / limit, 1) if limit else 0.0
    level = "bad" if percent >= 100 else "warn" if percent >= warn_percent else "ok"
    return {"id": name, "used": used, "limit": limit, "percent": percent, "level": level}


def planned(config, repos, allowance=None):
    """The rows of the setup in `config` for `repos` watched repositories (an int)."""
    cfg = settings(config)
    config = config if isinstance(config, dict) else {}
    repos = max(0, int(repos or 0))
    refresh, cold = _int(config.get("refresh_seconds"), 1, 86400, 120), _int(config.get("cold_refresh_seconds"), 1, 86400, 600)
    samp = sampling.settings(config)
    calls = sampling.estimate_per_hour(repos, refresh, cold, probe=samp["default_branch_probe"] or samp["active_probe"])
    rows = [row("api_calls_per_hour", calls, allowance or CORE_ALLOWANCE, cfg["warn_percent"])]
    if samp["api_budget_per_hour"]:
        rows.append(row("sampler_budget", calls, samp["api_budget_per_hour"], cfg["warn_percent"]))
    per_repo = _int(config.get("runs_per_repo"), 1, 200, 20)
    rows.append(row("memory_mb", round(repos * per_repo * RUN_BYTES / 1048576, 1), cfg["memory_mb"], cfg["warn_percent"]))
    limit = _int(config.get("discover_limit"), 1, 100000, 1000)
    rows.append(row("repos_listed", repos, limit, cfg["warn_percent"]))
    return rows


def live(config, figures):
    """The rows of what the running monitor holds. `figures` = {"live_events", "live_events_keep", "sse_clients", "sse_max", "read_queue_depth", "read_queue_wanted", "histogram_series", "histogram_max"};
    a figure that is missing leaves its row out."""
    warn = settings(config)["warn_percent"]
    out = []
    for name, used_key, limit_key in (("live_events", "live_events", "live_events_keep"), ("live_streams", "sse_clients", "sse_max"), ("histogram_series", "histogram_series", "histogram_max")):
        used, limit = figures.get(used_key), figures.get(limit_key)
        if isinstance(used, int) and isinstance(limit, int) and limit > 0:
            out.append(row(name, used, limit, warn))
    wanted, depth = figures.get("read_queue_wanted"), figures.get("read_queue_depth")
    if isinstance(wanted, int) and isinstance(depth, int) and wanted > 0:
        out.append(row("read_queue", depth, wanted, warn))
    return out


def verdict(rows):
    """("ok" | "warn" | "fail", one line) for the doctor: the worst level and the rows that are not ok."""
    bad = [r for r in rows if r["level"] == "bad"]
    warn = [r for r in rows if r["level"] == "warn"]
    status = "fail" if bad else "warn" if warn else "ok"
    names = ", ".join(f"{r['id']} {r['percent']}%" for r in bad + warn)
    return status, names or "; ".join(f"{r['id']} {r['percent']}%" for r in rows)


def lines(prefix, rows):
    if not rows:
        return []
    out = [f"# HELP {prefix}limit_used_percent How much of a ceiling of the monitor is used (100 = reached).", f"# TYPE {prefix}limit_used_percent gauge"]
    out += [f'{prefix}limit_used_percent{{limit="{r["id"]}"}} {r["percent"]}' for r in rows]
    return out
