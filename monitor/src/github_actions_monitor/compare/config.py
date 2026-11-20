# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`compare` of the configuration merged over DEFAULTS. A value of the wrong type, out of range or unknown keeps the default; the feature is OFF until it is switched on."""
import copy

DEFAULTS = {
    "enabled": False,
    "default_window_days": 7,           # 1..90 (7 and 30 are the usual ones)
    "default_days_filter": "all",       # all | workdays | weekend
    "workdays": [1, 2, 3, 4, 5],        # Monday = 1 ... Sunday = 7
    "min_runs_per_window": 20,          # fewer finished runs in a window: that window has insufficient data
    "min_days_of_history": 14,          # the monitor must have watched this long for the baseline to count
    "min_resolved": 3,                  # fewer alerts resolved in a window: no resolution time
    "min_snapshots": 12,                # fewer hourly snapshots in a window: no mean score
    "min_repo_runs": 3,                 # a repository needs this many finished runs in both windows to be ranked
    "top_changes": 10,
    "include_in_report": False,
    "cache_seconds": 60,
    "progressive": False,               # a long window (more than progressive_days) is answered at once with its recent part, and the whole one is finished in the background
    "progressive_days": 7,              # 1..29: how many days the first answer covers
}
FILTERS = ("all", "workdays", "weekend")
BOUNDS = {"progressive_days": (1, 29), "default_window_days": (1, 90), "min_runs_per_window": (1, 10000), "min_days_of_history": (1, 3650), "min_resolved": (1, 1000), "min_snapshots": (1, 10000), "min_repo_runs": (1, 1000), "top_changes": (3, 50), "cache_seconds": (0, 3600)}


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _days(value):
    """The sorted weekday numbers of a list ("1" and 1 are the same), or None when any item is not a day from 1 to 7."""
    clean = set()
    for item in value:
        if isinstance(item, bool):
            return None
        try:
            number = int(str(item).strip())
        except ValueError:
            return None
        if not 1 <= number <= 7:
            return None
        clean.add(number)
    return sorted(clean) or None


def settings(config):
    merged = copy.deepcopy(DEFAULTS)
    user = (config or {}).get("compare") if isinstance((config or {}).get("compare"), dict) else None
    if not user:
        return merged
    for key in ("enabled", "include_in_report", "progressive"):
        if isinstance(user.get(key), bool):
            merged[key] = user[key]
    if user.get("default_days_filter") in FILTERS:
        merged["default_days_filter"] = user["default_days_filter"]
    for key, (low, high) in BOUNDS.items():
        if _int(user.get(key)) and low <= user[key] <= high:
            merged[key] = user[key]
    if isinstance(user.get("workdays"), list):
        days = _days(user["workdays"])
        if days:
            merged["workdays"] = days
    return merged
