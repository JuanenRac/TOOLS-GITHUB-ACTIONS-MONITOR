# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Screens menu of the page: ONE closed catalogue of every kind of screen the monitor can open, with its address, the parameters that address accepts and what each one needs. It is navigation
only: it lists, builds addresses and (in the page) opens windows; nothing here writes, reads GitHub or starts anything.

  entries(config, lite)       the catalogue for /api/screens/menu: id, group, path, fixed parameters, the parameters a person may change (kind, range or choices, default), whether it is available
                              here and, if not, why
  build_url(entry, values)    the address of one entry with the values given, each one checked against the range of its parameter (a value that is not valid is left out)
  menu_settings(config)       the settings that belong to the menu (screens.menu, screens.menu_target, screens.menu_max_windows, screens.menu_rotate_seconds, screens.menu_tv_scale), inside their ranges

Kinds of screen: the whole page and its kiosk views (?chrome=0&view=), the three screens of tabs (/screen/1..3), the three wall screens (/screen/overview, /screen/now, /screen/sentinels), a wall screen
that turns through the three, the TV preset, and a multi-monitor set (N windows, one per monitor). The wall screens answer 404 while `screens.enabled` is off: the menu says so instead of opening a 404.
Standard library only."""
from urllib.parse import quote

from github_actions_monitor.app import screens

SCHEMA = 1
TARGETS = ("new", "same")
DEFAULTS = {key: screens.DEFAULTS[key] for key in ("menu", "menu_target", "menu_max_windows", "menu_rotate_seconds", "menu_tv_scale")}
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
#: the views the page opens with ?view= (the same names as the VIEWS of the page) that make sense as a kiosk
VIEWS = ("now", "alerts", "charts", "repos", "sentinel", "sentinel-ci", "sentinel-collab", "sentinel-security", "sentinel-delivery", "sentinel-supply", "sentinel-trend", "sentinel-yesterday", "team", "fleet", "reports", "lessons", "live")
TAB_IDS = ("now", "al", "charts", "sent", "sci", "scol", "ssec", "sdel", "ssup", "strend", "syvt", "team", "fleet", "repos", "rep", "trep", "les", "hist", "upd", "cfg")
ORIENTATIONS = ("auto", "portrait", "landscape")
LAYOUTS = ("row", "column", "grid")
SETS = ("wall", "wall_turning", "tabs")
GROUPS = ("page", "wall", "multi")
#: the parameters a person may change, by name: (kind, low/choices, high). `int` and `float` are ranges; `choice` is a closed list; `text` is a repository filter (letters, digits and . _ - / only)
PARAMS = {
    "lang": ("choice", ("",) + LANGS, None), "theme": ("choice", ("",) + screens.SCREEN_THEMES, None), "density": ("choice", ("",) + screens.DENSITIES, None),
    "refresh": ("int", 5, 120), "scale": ("float", 0.5, 3.0), "rotate": ("int", 0, 3600), "monitor": ("int", 1, 9), "blink": ("choice", ("", "off"), None), "jump": ("choice", ("", "off"), None),
    "view": ("choice", VIEWS, None), "tabs": ("list", TAB_IDS, None), "orient": ("choice", ORIENTATIONS, None), "repo": ("text", None, 80),
    "windows": ("int", 1, 9), "layout": ("choice", LAYOUTS, None), "set": ("choice", SETS, None),
}
WALL_PARAMS = ("theme", "density", "refresh", "scale", "lang", "monitor", "blink", "repo")
#: the catalogue: id, group, path, the parameters of the address that are fixed, the names of the parameters a person may change, the edition(s) that have it and what it needs
CATALOGUE = (
    {"id": "dashboard", "group": "page", "path": "/", "fixed": {}, "params": ("lang", "repo"), "needs": ""},
    {"id": "kiosk", "group": "page", "path": "/", "fixed": {"chrome": "0"}, "params": ("view", "lang", "repo"), "needs": ""},
    {"id": "team", "group": "page", "path": "/", "fixed": {"chrome": "0", "view": "team"}, "params": ("lang", "repo"), "needs": "complete"},
    {"id": "screen1", "group": "page", "path": "/screen/1", "fixed": {}, "params": ("tabs", "orient", "rotate", "lang", "repo"), "needs": ""},
    {"id": "screen2", "group": "page", "path": "/screen/2", "fixed": {}, "params": ("tabs", "orient", "rotate", "lang", "repo"), "needs": ""},
    {"id": "screen3", "group": "page", "path": "/screen/3", "fixed": {}, "params": ("tabs", "orient", "rotate", "lang", "repo"), "needs": ""},
    {"id": "overview", "group": "wall", "path": "/screen/overview", "fixed": {}, "params": WALL_PARAMS, "needs": "wall"},
    {"id": "fleet", "group": "wall", "path": "/screen/fleet", "fixed": {}, "params": WALL_PARAMS, "needs": "wall"},
    {"id": "now", "group": "wall", "path": "/screen/now", "fixed": {}, "params": WALL_PARAMS, "needs": "wall"},
    {"id": "sentinels", "group": "wall", "path": "/screen/sentinels", "fixed": {}, "params": WALL_PARAMS, "needs": "wall"},
    {"id": "wall_turning", "group": "wall", "path": "/screen/overview", "fixed": {}, "params": WALL_PARAMS + ("rotate", "jump"), "needs": "wall"},
    {"id": "tv", "group": "wall", "path": "/screen/overview", "fixed": {}, "params": WALL_PARAMS + ("rotate", "jump"), "needs": "wall"},
    {"id": "multi", "group": "multi", "path": "/screen/overview", "fixed": {}, "params": ("windows", "layout", "set") + WALL_PARAMS[:5] + ("repo",), "needs": "wall"},
)
IDS = tuple(e["id"] for e in CATALOGUE)


def _clean(config):
    block = (config or {}).get("screens")
    return block if isinstance(block, dict) else {}


def menu_settings(config):
    """The settings of the menu from the configuration, each one inside its range (a value that is not valid is the default); they are part of screens.settings."""
    cfg = screens.settings(config)
    return {key: cfg[key] for key in DEFAULTS}


def _spec(name, cfg, entry):
    """One parameter as the page needs it: its kind, its range or choices and its default for this entry."""
    kind, low, high = PARAMS[name]
    row = {"name": name, "kind": kind, "default": defaults(entry, cfg).get(name, "")}
    if kind in ("choice", "list"):
        row["choices"] = list(low)
    elif kind in ("int", "float"):
        row["min"], row["max"] = low, high
        if name == "windows":
            row["max"] = min(high, cfg["menu_max_windows"])
    else:
        row["max_length"] = high
    return row


def defaults(entry, cfg):
    """The values an entry starts with: the ones the preset gives it, from the settings of the menu."""
    out = {}
    if entry["id"] in ("wall_turning", "tv"):
        out["rotate"] = cfg["menu_rotate_seconds"]
    if entry["id"] == "tv":
        out.update({"density": "large", "scale": cfg["menu_tv_scale"], "theme": "contrast"})
    if entry["id"] == "kiosk":
        out["view"] = "now"
    if entry["id"] == "multi":
        out.update({"windows": min(3, cfg["menu_max_windows"]), "layout": "row", "set": "wall"})
    return out


def _value(name, raw):
    """The value as text if it is valid for the parameter, else None (so it is left out of the address)."""
    kind, low, high = PARAMS[name]
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip()
    if text == "":
        return None
    if kind == "choice":
        return text if text in low else None
    if kind == "list":
        parts = [p.strip() for p in text.split(",") if p.strip()]
        return ",".join(parts) if parts and all(p in low for p in parts) else None
    if kind in ("int", "float"):
        try:
            number = int(text) if kind == "int" else float(text)
        except ValueError:
            return None
        if not low <= number <= high:
            return None
        return str(number)
    if len(text) > high or not all(c.isalnum() or c in "._-/" for c in text):
        return None
    return text


def build_url(entry, values=None, cfg=None):
    """The address of one entry: its fixed parameters, then the ones asked for (checked), in the order of the catalogue. `windows`, `layout` and `set` belong to the multi-monitor set and are not part of one address.
    A rotation below 5 seconds is no rotation (it would flash), so it is left out."""
    cfg = cfg or dict(DEFAULTS)
    chosen = dict(defaults(entry, cfg))
    chosen.update({k: v for k, v in (values or {}).items() if k in entry["params"]})
    query = dict(entry["fixed"])
    for name in entry["params"]:
        if name in ("windows", "layout", "set"):
            continue
        text = _value(name, chosen.get(name))
        if text is None or (name == "rotate" and int(text) < 5):
            continue
        query[name] = text
    pairs = "&".join(f"{k}={quote(v, safe=',/')}" for k, v in query.items())
    return entry["path"] + ("?" + pairs if pairs else "")


def multi_urls(values, cfg, lite=False):
    """The windows of a multi-monitor set: a list of {n, id, url}, one per window. `set` = wall: overview, now and sentinels in turn; wall_turning: all of them turn (each one starts on another screen, a few seconds
    apart is not needed: the window turns by itself); tabs: /screen/1, /screen/2 and /screen/3 in turn. The number is clamped to screens.menu_max_windows."""
    values = values or {}
    count = _value("windows", values.get("windows"))
    count = max(1, min(int(count) if count else defaults({"id": "multi"}, cfg)["windows"], cfg["menu_max_windows"]))
    chosen = _value("set", values.get("set")) or "wall"
    order = {"wall": ("overview", "now", "sentinels", "fleet"), "wall_turning": ("wall_turning",), "tabs": ("screen1", "screen2", "screen3")}[chosen]
    by_id = {e["id"]: e for e in CATALOGUE}
    out = []
    for n in range(1, count + 1):
        entry = by_id[order[(n - 1) % len(order)]]
        extra = {k: v for k, v in values.items() if k in entry["params"] and k != "monitor"}
        if "monitor" in entry["params"]:
            extra["monitor"] = n
        out.append({"n": n, "id": entry["id"], "url": build_url(entry, extra, cfg)})
    return out


def entries(config, lite=False):
    """The catalogue for the page: every entry with its parameters, its default address and whether it can be opened here (`available`, else `reason`: wall_off = screens.enabled is off, edition = not in this edition)."""
    cfg, wall = menu_settings(config), screens.enabled(config)
    rows = []
    for entry in CATALOGUE:
        reason = ""
        if entry["needs"] == "wall" and not wall:
            reason = "wall_off"
        elif entry["needs"] == "complete" and lite:
            reason = "edition"
        row = {"id": entry["id"], "group": entry["group"], "path": entry["path"], "fixed": dict(entry["fixed"]), "params": [_spec(name, cfg, entry) for name in entry["params"]],
               "available": not reason, "reason": reason, "url": build_url(entry, None, cfg)}
        if entry["id"] == "multi":
            row["windows"] = multi_urls(None, cfg, lite)
        rows.append(row)
    return rows


def payload(config, lite=False):
    """GET /api/screens/menu."""
    cfg = menu_settings(config)
    return {"schema": SCHEMA, "enabled": cfg["menu"], "target": cfg["menu_target"], "max_windows": cfg["menu_max_windows"], "wall_enabled": screens.enabled(config),
            "groups": list(GROUPS), "entries": entries(config, lite) if cfg["menu"] else []}
