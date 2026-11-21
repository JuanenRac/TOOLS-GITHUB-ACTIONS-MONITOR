# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Time saved: an honest estimate of the time the monitor gives back, task by task, with the formula of docs/PRODUCTIVITY.md.

Time saved in a week = the sum, over the tasks, of (times a week x minutes each time without the monitor) x the saving of that task. Two tasks are quantified:

  watch    looking at the Actions tabs by hand and deciding what is really red. The times a week and the minutes each time come from the notes of the person (settings): the monitor cannot
           see what somebody did before it was installed.
  triage   finding the cause of a failed run. The times a week are COUNTED from the failed runs the monitor has in view over `window_days`; the minutes each time come from the notes of the person.

Where the "before" is missing the task says `no_data`: no number is invented. The saving of a task is `measured` when the person wrote also the minutes it takes now (`1 - after / before`) and `assumed`
otherwise (the percentage of the public model, shown as an assumption and never as a measurement). Fixing a failure takes the same time with or without the monitor and is not counted.
Everything is local and read only; it is off by default and it never makes a call to GitHub.
"""
import time

from github_actions_monitor.data_pipeline import analytics

DEFAULTS = {"enabled": False, "window_days": 7, "watch_times_per_week": 0, "watch_minutes_before": 0, "watch_minutes_after": -1,
            "triage_minutes_before": 0, "triage_minutes_after": -1, "saving_percent": 90, "team_hours_per_week": 0}
RANGES = {"window_days": (1, 90), "watch_times_per_week": (0, 1000), "watch_minutes_before": (0, 600), "watch_minutes_after": (-1, 600),
          "triage_minutes_before": (0, 600), "triage_minutes_after": (-1, 600), "saving_percent": (0, 100), "team_hours_per_week": (0, 10000)}
NOT_QUANTIFIED = ("fixing_failures",)      # it takes the same time with or without the monitor


def settings(config):
    """`productivity` of the configuration merged over DEFAULTS (a value of the wrong type or out of its range keeps the default)."""
    merged = dict(DEFAULTS)
    user = (config or {}).get("productivity")
    if isinstance(user, dict):
        if isinstance(user.get("enabled"), bool):
            merged["enabled"] = user["enabled"]
        for key, (low, high) in RANGES.items():
            value = user.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
                merged[key] = value
    return merged


def off():
    """What the page and the API say while the analysis is off."""
    return {"enabled": False}


def failed_in_window(runs, window_days, now):
    """How many runs in view ended red inside the window, and how many runs carry a usable date (the latter says whether anything was seen at all)."""
    failed, dated = 0, 0
    for run in runs or []:
        started = analytics._ts(run.get("started"))
        if started is None:
            continue
        dated += 1
        if now - started <= window_days * 86400 and run.get("conclusion") in analytics.BAD:
            failed += 1
    return failed, dated


def _task(name, times, before, after, percent):
    """One task: `no_data` while the times or the minutes without the monitor are unknown, otherwise `measured` (the person noted the minutes after) or `assumed` (the percentage of the model)."""
    row = {"task": name, "times_per_week": None if times is None else round(times, 1), "minutes_before": before or None, "minutes_after": after if after >= 0 else None,
           "saving_percent": None, "saved_minutes": None, "basis": "no_data"}
    if times is None or before <= 0:
        return row
    if after >= 0:
        fraction, row["basis"] = max(0.0, 1 - after / before), "measured"
    else:
        fraction, row["basis"] = percent / 100.0, "assumed"
    row["saving_percent"] = round(fraction * 100)
    row["saved_minutes"] = round(times * before * fraction)
    return row


def estimate(runs, cfg, now=None):
    """{"enabled", "window_days", "failed_seen", "tasks": [...], "saved_minutes_week", "share_percent", "not_quantified"} - the numbers are None where there is no data."""
    if not cfg.get("enabled"):
        return off()
    now = time.time() if now is None else now
    failed, dated = failed_in_window(runs, cfg["window_days"], now)
    triage_times = failed * 7.0 / cfg["window_days"] if dated else None
    tasks = [_task("watch", float(cfg["watch_times_per_week"]) if cfg["watch_times_per_week"] > 0 else None, cfg["watch_minutes_before"], cfg["watch_minutes_after"], cfg["saving_percent"]),
             _task("triage", triage_times, cfg["triage_minutes_before"], cfg["triage_minutes_after"], cfg["saving_percent"])]
    counted = [t["saved_minutes"] for t in tasks if t["saved_minutes"] is not None]
    saved = sum(counted) if counted else None
    share = round(100.0 * saved / (cfg["team_hours_per_week"] * 60), 1) if saved is not None and cfg["team_hours_per_week"] > 0 else None
    return {"enabled": True, "window_days": cfg["window_days"], "failed_seen": failed, "tasks": tasks, "saved_minutes_week": saved, "share_percent": share, "not_quantified": list(NOT_QUANTIFIED)}
