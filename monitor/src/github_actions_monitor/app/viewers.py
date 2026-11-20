# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Polling that knows whether anybody is looking. With `modes.idle_minutes` above 0 (off by default; 10 is a good start) the monitor notices that no page, no wall screen and no live stream has asked it for data
for that many minutes and goes cold: the refresh cycle stretches to the cold interval (`cold_refresh_seconds` of the mode in force) until somebody looks again, when it goes back to its pace at the next cycle.
A page or a wall screen whose tab is hidden stops asking while it is hidden (and asks at once when it comes back), so a forgotten tab does not keep the monitor awake.

Nothing that guards the fleet goes cold: while an alert can leave the computer (a channel of notices, the webhook receiver, the feed for an AI, the chat, the beep of this computer) the cycle keeps its pace,
because an alert must not wait for somebody to open a page. The sentinels run on their own clocks and are not touched. Standard library only."""
import time

WATCHED = ("/api/data", "/api/screens/data", "/api/live-events/stream")      # what a page, a wall screen or a live stream asks for while somebody is looking
DEFAULTS = {"idle_minutes": 0}
_LAST = {"at": None}


def settings(config):
    """`modes.idle_minutes`: 0 (off, the default) or 1 to 1440 minutes without a look before the monitor goes cold."""
    block = config.get("modes") if isinstance(config, dict) and isinstance(config.get("modes"), dict) else {}
    value = block.get("idle_minutes")
    ok = isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1440
    return {"idle_minutes": value if ok else DEFAULTS["idle_minutes"]}


def touch(path, now=None):
    """Somebody asked for the data of a page, a screen or a stream: remember when. Any other path is not a look."""
    if str(path or "").split("?")[0] in WATCHED:
        _LAST["at"] = time.time() if now is None else now


def idle_seconds(now=None):
    """Seconds since the last look; the start of the monitor counts as a look (somebody has just opened it)."""
    now = time.time() if now is None else now
    if _LAST["at"] is None:
        _LAST["at"] = now
    return max(0.0, now - _LAST["at"])


def exceptions(config):
    """What keeps the monitor at its pace even when nobody looks: the ways an alert can leave this computer. Names only."""
    config = config if isinstance(config, dict) else {}
    found = []

    def block(name):
        value = config.get(name)
        return value if isinstance(value, dict) else {}
    try:
        from github_actions_monitor.integrations import notifiers
        if notifiers.settings(config).get("enabled") is True:
            found.append("notify")
    except Exception:   # noqa: BLE001 - a check of the exceptions never stops the cycle
        found.append("notify")
    if block("webhook").get("enabled") is True:
        found.append("webhook")
    if block("ai_alerts").get("enabled") is True:
        found.append("ai_alerts")
    if block("chatops").get("enabled") is True:
        found.append("chatops")
    sound = block("sound")
    if sound.get("enabled", True) is not False and sound.get("server_beep") is True:
        found.append("server_beep")
    return found


def cold(config, now=None):
    """True when the monitor should be cold now: the setting is on, nobody has looked for that long and nothing keeps it at its pace."""
    minutes = settings(config)["idle_minutes"]
    return bool(minutes) and idle_seconds(now) >= minutes * 60 and not exceptions(config)


def stretch(config, delay, cold_seconds, now=None):
    """The pause before the next cycle: `delay`, or the cold interval when the monitor is cold (never shorter than `delay`)."""
    try:
        if cold(config, now) and isinstance(cold_seconds, (int, float)) and not isinstance(cold_seconds, bool):
            return max(delay, int(cold_seconds))
    except Exception:   # noqa: BLE001
        pass
    return delay


def public(config, now=None):
    """What /api/health says: whether the polling is aware of viewers, how long since the last look, whether it is cold and what keeps it at its pace."""
    minutes = settings(config)["idle_minutes"]
    return {"aware": bool(minutes), "idle_minutes": minutes, "idle_seconds": int(idle_seconds(now)), "cold": cold(config, now), "kept_by": exceptions(config) if minutes else []}


def reset():
    """For the tests."""
    _LAST["at"] = None
