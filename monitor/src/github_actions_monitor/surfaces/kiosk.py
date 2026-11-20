# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The kiosk profile: the page of the monitor for a TV or a wall, with larger type and, when you ask for it, a high contrast and a rotation through a few tabs. It reuses what the page already
knows (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`) and adds two parameters: `kiosk=1` (turn the profile on) and `scale=` (the type size in percent). Everything is opt-in:
`kiosk.enabled` is off by default, and with it off the page ignores `kiosk=1`, so a link copied from somewhere else changes nothing.

The profile reads nothing from GitHub and writes nothing: it only decides how the page looks. The presets are fixed lists of tabs (see PRESETS); the tab ids are the ones of the page.
"""
from urllib.parse import urlencode

PRESETS = {"ops": ("now", "al", "charts"), "team": ("al", "team"), "release": ("now", "repos", "rep"), "quiet": ("al",)}
SCALE_RANGE = (100, 400)
ROTATE_RANGE = (5, 600)
SAFE_RANGE = (0, 10)      # percent of each edge that a television may cut (overscan) and the page keeps clear
DEFAULTS = {"enabled": False, "font_scale_percent": 150, "high_contrast": False, "rotate_views": False, "rotate_seconds": 30, "safe_margin_percent": 0, "scale_with_window": False}


def _int(value, low, high, fallback):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else fallback


def settings(raw):
    """The `kiosk` block of the configuration with every value inside its range; a missing or wrong value is the default."""
    block = (raw or {}).get("kiosk") if isinstance(raw, dict) else None
    block = block if isinstance(block, dict) else {}
    return {"enabled": block.get("enabled") is True, "font_scale_percent": _int(block.get("font_scale_percent"), *SCALE_RANGE, DEFAULTS["font_scale_percent"]),
            "high_contrast": block.get("high_contrast") is True, "rotate_views": block.get("rotate_views") is True,
            "rotate_seconds": _int(block.get("rotate_seconds"), *ROTATE_RANGE, DEFAULTS["rotate_seconds"]),
            "safe_margin_percent": _int(block.get("safe_margin_percent"), *SAFE_RANGE, DEFAULTS["safe_margin_percent"]), "scale_with_window": block.get("scale_with_window") is True}


def public(raw):
    """What the page is given (the same values, nothing else)."""
    return settings(raw)


def clamp_scale(value, fallback=100):
    """The type size of the address (`scale=`) in percent, kept inside the range the setting allows."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return max(SCALE_RANGE[0], min(SCALE_RANGE[1], number))


def url(base, preset, raw, account=""):
    """The address of a preset: `<base>/?screen=1&tabs=...&chrome=0&kiosk=1&scale=...` plus `rotate=` when the rotation is on and `contrast=1` when the high contrast is on.
    Raises KeyError for a preset that does not exist."""
    config = settings(raw)
    tabs = PRESETS[preset]
    query = {"screen": 1, "tabs": ",".join(tabs), "chrome": 0, "kiosk": 1, "scale": config["font_scale_percent"]}
    if config["rotate_views"] and len(tabs) > 1:
        query["rotate"] = config["rotate_seconds"]
    if config["high_contrast"]:
        query["contrast"] = 1
    if account:
        query["account"] = account
    return base.rstrip("/") + "/?" + urlencode(query, safe=",")
