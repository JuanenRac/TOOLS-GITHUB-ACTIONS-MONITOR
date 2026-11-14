# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tells you when a newer version of the monitor is published. It only NOTIFIES: nothing is downloaded, installed or changed.

  * One read-only request to the public releases page of the project (`releases/latest`), through the same GitHub client as the rest of the monitor (conditional
    read: a 304 answer costs no quota). The request carries nothing about you, your repositories or your settings.
  * The answer is kept for about 24 hours in `update_check.json` next to the monitor; between two checks nothing is requested.
  * Switch: `updates.check` (Settings > Basic). It is off whenever `airgapped` is on or the connection is down; a failed check is silent (the last answer stays).
  * Versions are compared as numbers (1.6.10 is newer than 1.6.9); a pre-release or a draft is never offered.
"""
import json
import os
import re
import threading
import time
from pathlib import Path
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import state_io

from github_actions_monitor.util import paths
STATE_FILE = paths.place("update_check.json")
REPO = "JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR"
ENDPOINT = f"repos/{REPO}/releases/latest"
URL_RE = re.compile(r"^https://github\.com/" + re.escape(REPO) + r"/releases/tag/[A-Za-z0-9._-]{1,40}$")
TAG_RE = re.compile(r"^v?(\d{1,6})\.(\d{1,6})\.(\d{1,6})(?:\.(\d{1,6}))?$")
INTERVAL = 24 * 3600


def parse_semver(text):
    """(major, minor, patch[, build]) of '1.6.3' / 'v1.6.3' as numbers, or None for anything else (a pre-release such as '1.7.0-rc1' is None on purpose)."""
    match = TAG_RE.match(str(text or "").strip())
    return tuple(int(part) for part in match.groups() if part is not None) if match else None


def is_newer(latest, current):
    """True only when both are plain versions and `latest` is greater than `current`."""
    a, b = parse_semver(latest), parse_semver(current)
    if a is None or b is None:
        return False
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def settings(config):
    """{"check": bool, "airgapped": bool}: the check is on by default and always off in an air-gapped installation (setting or MONITOR_AIRGAPPED)."""
    cfg = config if isinstance(config, dict) else {}
    updates = cfg.get("updates") if isinstance(cfg.get("updates"), dict) else {}
    airgapped = cfg.get("airgapped") is True or os.environ.get("MONITOR_AIRGAPPED", "").strip().lower() in ("1", "true", "yes")
    return {"check": updates.get("check", True) is True and not airgapped, "airgapped": airgapped}


def _load(path):
    try:
        value = state_io.load_json(path)
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    clean = {}      # a file edited by hand (or damaged) never reaches the page with a field of the wrong type
    if isinstance(value.get("checked_at"), (int, float)) and not isinstance(value.get("checked_at"), bool):
        clean["checked_at"] = value["checked_at"]
    release = value.get("release")
    if isinstance(release, dict) and isinstance(release.get("tag"), str) and isinstance(release.get("url", ""), str):
        clean["release"] = {"tag": release["tag"][:40], "url": release.get("url", "")[:300], "published": release.get("published", "") if isinstance(release.get("published"), str) else ""}
    return clean


def _save(path, state):
    try:
        state_io.save_text(path, json.dumps(state, indent=1) + "\n")
    except OSError:
        pass


def clean_release(body):
    """{"tag", "url", "published"} from the answer of GitHub, or None for a draft, a pre-release or anything that is not a plain version tag from this project."""
    if not isinstance(body, dict) or body.get("draft") or body.get("prerelease"):
        return None
    tag = body.get("tag_name")
    if not isinstance(tag, str) or parse_semver(tag) is None:
        return None
    url = body.get("html_url")
    if not isinstance(url, str) or not URL_RE.match(url):
        url = f"https://github.com/{REPO}/releases/tag/{tag}"
    published = body.get("published_at")
    return {"tag": tag, "url": url, "published": published if isinstance(published, str) and len(published) <= 30 else ""}


def view(config, current, state, offline=False):
    """What the page, the console and `doctor` show: {"enabled", "airgapped", "current", "latest", "newer", "url", "changelog", "checked_at", "offline"}."""
    cfg = settings(config)
    release = state.get("release") if isinstance(state.get("release"), dict) else None
    latest = release.get("tag", "").lstrip("v") if release else ""
    newer = bool(cfg["check"] and release and is_newer(latest, current))
    return {"enabled": cfg["check"], "airgapped": cfg["airgapped"], "current": current, "latest": latest if release else "", "newer": newer,
            "url": release.get("url", "") if newer else "", "changelog": f"https://github.com/{REPO}/blob/{release['tag']}/monitor/CHANGELOG.md" if newer else "",
            "checked_at": state.get("checked_at") or 0, "offline": bool(offline)}


_BUSY = set()
_BUSY_LOCK = threading.Lock()


def _refresh(reader, path, now, state):
    try:
        release = clean_release(reader(ENDPOINT))
        _save(path, {"checked_at": int(now), "release": release})
    except Exception:   # noqa: BLE001 - offline, air-gapped networks, rate limits: the check is silent, it tries again later
        _save(path, dict(state, checked_at=int(now) - INTERVAL + 3600))      # tried again in an hour, not at every request


def check(config, current, reader, now=None, state_file=None, offline=False, force=False, background=False):
    """The update state; reads the releases page through `reader(endpoint) -> dict` only when the check is on, the connection is up and the last answer is older than 24 hours.
    Any error leaves the last answer in place and is never raised. With `background` the answer of the cache is returned AT ONCE and the read is made by a thread (never more than one at a time per file):
    a page or an endpoint must not wait for the network (a `gh` without a login can take half a minute)."""
    now = time.time() if now is None else now
    path = state_file or STATE_FILE
    state = _load(path)
    cfg = settings(config)
    if cfg["check"] and not offline and (force or not state.get("checked_at") or now - float(state["checked_at"]) >= INTERVAL):
        if background:
            with _BUSY_LOCK:
                start = str(path) not in _BUSY
                _BUSY.add(str(path))
            if start:
                def work():
                    try:
                        _refresh(reader, path, now, state)
                    finally:
                        with _BUSY_LOCK:
                            _BUSY.discard(str(path))
                threading.Thread(target=work, daemon=True).start()
        else:
            try:
                release = clean_release(reader(ENDPOINT))
                state = {"checked_at": int(now), "release": release}
                _save(path, state)
            except Exception:   # noqa: BLE001
                state = dict(state, checked_at=int(now) - INTERVAL + 3600)
                _save(path, state)
    return view(config, current, state, offline)


def notice(info, translate):
    """The one line shown in the console and in `doctor` ('' when there is nothing to say)."""
    if info.get("newer"):
        return translate("upd.available", version=info["latest"], current=info["current"], url=info["url"])
    return ""
