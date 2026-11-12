# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who spends the allowance: the trend of the consumption of the account against the consumption of the monitor itself. Standard library only.

At every cycle the monitor notes the calls left of the user's allowance (the free `rate_limit` call) and how many calls it has made itself. Inside the same hourly window (the same renewal time) the
difference is what the whole account spent and the monitor's own calls are what it spent: the rest is spent by OTHER tools (GitHub does not say which). When the monitor's share is small and the rest is
large the page and the brief say so, so the person knows where the allowance goes. Nothing is stored on disk and no call is made.
"""
from collections import deque

_HIST = deque(maxlen=240)
MIN_MINUTES = 5           # not before five minutes of samples inside one window
OTHERS_PER_HOUR = 300     # calls an hour spent by others from which it is worth saying so


def note(remaining, limit, reset, own_calls, now):
    if not isinstance(remaining, int) or isinstance(remaining, bool):
        return
    _HIST.append({"t": float(now), "left": remaining, "limit": limit, "reset": reset, "own": int(own_calls)})


def trend(now=None):
    """{"minutes", "own_per_hour", "all_per_hour", "others_per_hour", "others_warn"} over the samples of the current window, or {} when there are not enough."""
    if len(_HIST) < 2:
        return {}
    last = _HIST[-1]
    window = [s for s in _HIST if s["reset"] == last["reset"]]
    if len(window) < 2:
        return {}
    first = window[0]
    minutes = (last["t"] - first["t"]) / 60
    if minutes < MIN_MINUTES:
        return {}
    hours = minutes / 60
    spent = max(0, first["left"] - last["left"])
    own = max(0, last["own"] - first["own"])
    others = max(0, spent - own)
    out = {"minutes": round(minutes), "own_per_hour": round(own / hours), "all_per_hour": round(spent / hours), "others_per_hour": round(others / hours)}
    out["others_warn"] = out["others_per_hour"] >= OTHERS_PER_HOUR and out["others_per_hour"] > 3 * max(1, out["own_per_hour"])
    return out


def reset():
    _HIST.clear()
