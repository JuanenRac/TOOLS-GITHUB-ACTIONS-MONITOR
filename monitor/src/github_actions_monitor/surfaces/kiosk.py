# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The kiosk profile: the page of the monitor for a TV or a wall, with larger type and, when you ask for it, a high contrast and a rotation through a few tabs. It reuses what the page already
knows (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`) and adds two parameters: `kiosk=1` (turn the profile on) and `scale=` (the type size in percent). Everything is opt-in:
`kiosk.enabled` is off by default, and with it off the page ignores `kiosk=1`, so a link copied from somewhere else changes nothing.

The profile reads nothing from GitHub and writes nothing: it only decides how the page looks. The presets are fixed lists of tabs (see PRESETS); the tab ids are the ones of the page.
"""
import json
import re
from urllib.parse import parse_qs, urlencode

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
    """What the page is given: the same values, and the pace at which it asks /api/version to reload itself when the monitor was updated (`screens.version_check_seconds`, shared with the wall screens; 0 = never)."""
    from github_actions_monitor.app import screens
    return {**settings(raw), "version_check_seconds": screens.settings(raw)["version_check_seconds"]}


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


# what a row of a repository says besides its name: the titles of a commit or a pull request, the branch, the workflow and the addresses; a hidden repository gives none of it to a kiosk
HIDDEN_TEXT_KEYS = ("title", "display_title", "message", "commit_message", "commit", "branch", "head_branch", "pr_title", "workflow", "workflow_name", "url", "html_url", "run_url", "actor", "name", "step", "runner")


def asked(raw, query):
    """True when the address of /api/data asks for the data of a kiosk (`kiosk=1`) and the profile is on: a link copied from somewhere else changes nothing."""
    ask = parse_qs(query or "")
    return settings(raw)["enabled"] and (ask.get("kiosk") or [""])[0] == "1"


def _blank(node, names):
    if isinstance(node, dict):
        repo = node.get("repo")
        if isinstance(repo, str) and names.hidden(repo):
            for key in HIDDEN_TEXT_KEYS:
                if key in node and isinstance(node[key], str):
                    node[key] = ""
            if isinstance(node.get("jobs"), list):
                node["jobs"] = []
        for value in node.values():
            _blank(value, names)
    elif isinstance(node, list):
        for value in node:
            _blank(value, names)


def redact(picture, names):
    """The answer of /api/data for a kiosk, as JSON text, with the repositories named the way the wall screens name them (`screens.show_repo_names`): every hidden repository is private-N (or repo-N),
    whole or by its short name, wherever it stands in the data, and its rows lose the text that tells what it holds (HIDDEN_TEXT_KEYS). `names` is a screens.Names; nothing is changed when no repository is hidden."""
    text = json.dumps(picture)
    hidden = [r for r in names.repos if names.hidden(r)]
    if not hidden:
        return text
    doc = json.loads(text)
    _blank(doc, names)
    text = json.dumps(doc)
    swaps = {}
    for repo in hidden:
        swaps[repo] = names.name(repo)
        short = repo.rsplit("/", 1)[-1]
        if len(short) >= 3:
            swaps.setdefault(short, names.name(repo))
    for old in sorted(swaps, key=len, reverse=True):
        text = re.sub(r"(?<![\w.-])" + re.escape(json.dumps(old)[1:-1]) + r"(?![\w.-])", lambda _m, new=swaps[old]: new, text)
    return text
