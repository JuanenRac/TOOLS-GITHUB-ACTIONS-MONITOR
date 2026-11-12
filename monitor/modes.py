# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Working modes: normal, fast and turbo. For when you want to watch something closer for a while (an hour, say) even if it spends the allowance of the API faster.

  * `normal` changes nothing: it is YOUR configuration. `fast` and `turbo` override a few values (the presets live in the `modes` block of the configuration and can be edited).
  * A mode can have a duration; when it ends the monitor goes back to normal by itself, and it also goes back when the allowance left falls under `min_rate_remaining` (a persistent notice says why).
  * Without a login the API gives 60 calls an hour: fast and turbo are refused with the reason. The real limit is the one of GitHub's own headers.
  * Nothing keeps turbo after a restart unless you write `modes.start` yourself; the default is normal. Changing the mode is a local setting and needs the one-use token like any other change.
  * A 304 answer to a conditional read does not count against the primary allowance (it is what the ETag cache is for), so the estimate shows the worst case and the figure the cache really saves.
"""
import time

NAMES = ("normal", "fast", "turbo", "low")
DEFAULTS = {
    "start": "normal",
    "default_minutes": 60,
    "fast": {"refresh_seconds": 30, "cold_refresh_seconds": 300, "runs_per_repo": 30, "hot_hours": 6},
    "turbo": {"refresh_seconds": 15, "cold_refresh_seconds": 90, "runs_per_repo": 50, "hot_hours": 12},
    # low: the opposite of fast, for when many tools spend the same allowance: only the hot repositories (a run in progress or a red one) every few minutes, the rest every half hour, short run lists
    "low": {"refresh_seconds": 240, "cold_refresh_seconds": 1800, "runs_per_repo": 10, "hot_hours": 2},
    "auto_low": True,             # go to low by itself when the allowance left falls under auto_low_enter and come back when it passes auto_low_exit (or renews)
    "auto_low_enter": 1000,
    "auto_low_exit": 2500,
}
MIN_REFRESH = 10            # never faster than the minimum of the Settings page: it keeps clear of the secondary limits of GitHub
KEYS = ("refresh_seconds", "cold_refresh_seconds", "runs_per_repo", "hot_hours")
BOUNDS = {"refresh_seconds": (MIN_REFRESH, 3600), "cold_refresh_seconds": (30, 86400), "runs_per_repo": (5, 100), "hot_hours": (1, 48)}


def presets(config):
    block = (config or {}).get("modes") if isinstance((config or {}).get("modes"), dict) else {}
    out = {"normal": {}}
    for name in ("fast", "turbo", "low"):
        merged = dict(DEFAULTS[name])
        given = block.get(name) if isinstance(block.get(name), dict) else {}
        for key in KEYS:
            value = given.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and BOUNDS[key][0] <= value <= BOUNDS[key][1]:
                merged[key] = value
        out[name] = merged
    return out


def settings(config):
    block = (config or {}).get("modes") if isinstance((config or {}).get("modes"), dict) else {}
    minutes = block.get("default_minutes")
    def number(key, low, high):
        value = block.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else DEFAULTS[key]
    enter, leave = number("auto_low_enter", 50, 4000), number("auto_low_exit", 100, 5000)
    if leave <= enter:      # a gap between going in and coming out (hysteresis), or it would flap
        enter, leave = DEFAULTS["auto_low_enter"], DEFAULTS["auto_low_exit"]
    return {"start": block.get("start") if block.get("start") in NAMES else "normal", "default_minutes": minutes if isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 1440 else 60,
            "auto_low": block.get("auto_low") is not False, "auto_low_enter": enter, "auto_low_exit": leave}


class State:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.name, self.until, self.notice, self.started, self.auto = "normal", None, "", None, False

    def current(self, config, remaining=None):
        """The mode in force now: ends a mode whose time is up or whose allowance fell under the floor (and keeps the reason as a notice). With `auto_low` (on by default) normal becomes low when
        the allowance left falls under `auto_low_enter` and low comes back to normal above `auto_low_exit`: two different numbers, so it does not flap."""
        now = self.clock()
        cfg = settings(config)
        if self.name != "normal":
            if self.until is not None and now >= self.until:
                self._back("expired")
            elif self.name in ("fast", "turbo") and remaining is not None and remaining < int((config or {}).get("min_rate_remaining", 800)):
                self._back("quota")
            elif self.name == "low" and self.auto and remaining is not None and remaining > cfg["auto_low_exit"]:
                self._back("auto_low_end")
        elif cfg["auto_low"] and remaining is not None and remaining < cfg["auto_low_enter"]:
            self.name, self.until, self.started, self.auto, self.notice = "low", None, now, True, "auto_low"
        return self.name

    def _back(self, why):
        self.name, self.until, self.started, self.auto = "normal", None, None, False
        self.notice = why

    def set(self, name, minutes, config, rate_limit=None, remaining=None):
        """(ok, reason). `minutes` 0 or None = until you change it (or until the allowance falls under the floor)."""
        if name not in NAMES:
            return False, "unknown"
        if name not in ("normal", "low"):      # low is always allowed: it spends less
            if rate_limit is not None and isinstance(rate_limit, int) and rate_limit <= 60:
                return False, "no_token"
            if remaining is not None and remaining < int((config or {}).get("min_rate_remaining", 800)):
                return False, "low_quota"
        if name == "normal":
            self._back("manual")
            self.notice = ""
            return True, "ok"
        if minutes is not None and (not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 0 or minutes > 1440):
            return False, "minutes"
        self.name, self.notice, self.started, self.auto = name, "", self.clock(), False
        self.until = self.clock() + minutes * 60 if minutes else None
        return True, "ok"

    def seconds_left(self):
        return max(0, int(self.until - self.clock())) if self.name != "normal" and self.until else None


def effective(config, key, state_name):
    """The value in force: yours in normal mode; in fast and turbo the preset, but never slower (or smaller) than what you set yourself."""
    base = (config or {}).get(key)
    if state_name == "normal" or base is None:
        return base
    preset = presets(config)[state_name].get(key)
    if preset is None:
        return base
    if state_name == "low":      # the opposite direction: never faster (or bigger) than what you set yourself
        return max(base, preset) if key in ("refresh_seconds", "cold_refresh_seconds") else min(base, preset)
    return max(base, preset) if key in ("runs_per_repo", "hot_hours") else min(base, preset)


def estimate(config, repos, hot, remaining, saved_share=0.0):
    """Worst-case calls per hour of each mode and how long the allowance left would last: {mode: {"calls_per_hour", "minutes_left", "with_cache_per_hour"}}. A cycle costs one call per hot repository
    plus a few; cold repositories are read every `cold_refresh_seconds`. `saved_share` (0-1) is what the conditional reads really saved lately."""
    out = {}
    for name, preset in presets(config).items():
        refresh = preset.get("refresh_seconds") or config.get("refresh_seconds", 45)
        cold = preset.get("cold_refresh_seconds") or config.get("cold_refresh_seconds", 600)
        per_hour = round(3600 / max(1, refresh) * (max(1, hot) + 3) + 3600 / max(1, cold) * max(0, repos - hot))
        cached = round(per_hour * (1 - min(max(saved_share, 0.0), 0.95)))
        out[name] = {"calls_per_hour": per_hour, "with_cache_per_hour": cached, "refresh_seconds": refresh,
                     "minutes_left": round(60 * remaining / per_hour) if (remaining is not None and per_hour) else None}
    return out
