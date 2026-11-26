# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tells you when a newer version of the monitor is published. It only NOTIFIES: nothing is downloaded, installed or changed.

  * One read-only request to the public releases page of the project (`releases/latest`), through the same GitHub client as the rest of the monitor (conditional
    read: a 304 answer costs no quota). The request carries nothing about you, your repositories or your settings.
  * The answer is kept for about 24 hours in `update_check.json` next to the monitor; between two checks nothing is requested.
  * Switch: `updates.check` (Settings > Basic). It is off whenever `airgapped` is on or the connection is down; a failed check is silent (the last answer stays).
  * Versions are compared as numbers (1.6.10 is newer than 1.6.9); a pre-release or a draft is never offered.
  * The notes of the release come in the same answer: the marked blocks `<!-- whats-new:<language> ... -->` hold a short summary per language and only those are kept (plain text, bounded).
  * A person may dismiss the notice of ONE version (`dismiss`); a newer one is announced again.
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
URL_RE = re.compile(r"^https://github\.com/" + re.escape(REPO) + r"/releases/tag/[A-Za-z0-9._-]{1,40}\Z")
TAG_RE = re.compile(r"^v?(\d{1,6})\.(\d{1,6})\.(\d{1,6})(?:\.(\d{1,6}))?\Z")
INTERVAL = 24 * 3600
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NOTES_RE = re.compile(r"<!--\s*whats-new:(en|es|de|fr|it|ja|zh|pt)[ \t]*\r?\n(.*?)-->", re.S)
MAX_NOTE = 900
MAX_BODY = 200_000


def parse_notes(body):
    """{language: text} of the marked blocks of the notes of a release ({} when there are none). The text is what GitHub gave: it is shown as plain text, never as markup."""
    found = {}
    for lang, text in NOTES_RE.findall(str(body or "")[:MAX_BODY]):
        clean = "".join(c for c in text.replace("\r\n", "\n") if c == "\n" or c.isprintable()).strip()
        if clean and lang not in found:
            found[lang] = clean[:MAX_NOTE]
    return found


def _clean_notes(value):
    return {k: v[:MAX_NOTE] for k, v in value.items() if k in LANGS and isinstance(v, str) and v} if isinstance(value, dict) else {}


def pick_notes(notes, language):
    """The summary in `language`, else in English, else ""."""
    notes = notes or {}
    return notes.get(str(language or "")[:2].lower()) or notes.get("en") or ""


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


CHANNELS = ("docker", "service", "pipx", "uv", "gh-extension", "zip")
IMAGE = "ghcr.io/" + REPO.lower()
COMMANDS = {"zip": "py -3 monitor/bin/monitor_cli.py update", "service": "py -3 monitor/bin/monitor_cli.py update apply --systemd-unit <unit>", "pipx": "pipx upgrade github-actions-monitor",
            "uv": "uv tool upgrade github-actions-monitor", "gh-extension": "gh extension upgrade actions-monitor", "docker": "docker pull {image}:{tag}"}


def install_channel(env=None, prefix=None, exists=None):
    """How this monitor was installed, from what the process can see: docker (a container), service (a service manager or MONITOR_SERVICE=1), pipx, uv (a tool of uv), gh-extension (an extension of the gh
    command) or zip (the unpacked product: the default). `env`, `prefix` and `exists` are given by the tests."""
    env = os.environ if env is None else env
    exists = exists or os.path.exists
    where = str(prefix if prefix is not None else __file__).replace("\\", "/").lower()
    if exists("/.dockerenv") or str(env.get("MONITOR_IN_CONTAINER", "")).strip() == "1":
        return "docker"
    if "/pipx/venvs/" in where:
        return "pipx"
    if "/uv/tools/" in where or "/uv/archive" in where or "/.cache/uv/" in where:
        return "uv"
    if "/gh/extensions/" in where:
        return "gh-extension"
    if str(env.get("MONITOR_SERVICE", "")).strip() == "1" or env.get("INVOCATION_ID"):
        return "service"
    return "zip"


def update_command(channel, tag=""):
    """The exact command to update for that channel (the tag is the one of the newer release)."""
    template = COMMANDS.get(channel) or COMMANDS["zip"]
    return template.format(image=IMAGE, tag=str(tag or "latest").lstrip("v"))


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
        if _clean_notes(release.get("notes")):
            clean["release"]["notes"] = _clean_notes(release.get("notes"))
    if isinstance(value.get("dismissed"), str) and parse_semver(value["dismissed"]):
        clean["dismissed"] = value["dismissed"].strip().lstrip("v")
    return clean


def _save(path, state):
    try:
        state_io.save_text(path, json.dumps(state, indent=1) + "\n")
    except OSError:
        pass


def clean_release(body):
    """{"tag", "url", "published"[, "notes"]} from the answer of GitHub, or None for a draft, a pre-release or anything that is not a plain version tag from this project."""
    if not isinstance(body, dict) or body.get("draft") or body.get("prerelease"):
        return None
    tag = body.get("tag_name")
    if not isinstance(tag, str) or parse_semver(tag) is None:
        return None
    url = body.get("html_url")
    if not isinstance(url, str) or not URL_RE.match(url):
        url = f"https://github.com/{REPO}/releases/tag/{tag}"
    published = body.get("published_at")
    release = {"tag": tag, "url": url, "published": published if isinstance(published, str) and len(published) <= 30 else ""}
    notes = parse_notes(body.get("body"))
    if notes:
        release["notes"] = notes
    return release


def dismiss(version, state_file=None):
    """The person does not want to hear again about `version`: kept next to the last answer. False for a text that is not a version."""
    if parse_semver(version) is None:
        return False
    path = state_file or STATE_FILE
    _save(path, dict(_load(path), dismissed=str(version).strip().lstrip("v")))
    return True


def view(config, current, state, offline=False):
    """What the page, the console and `doctor` show: {"enabled", "airgapped", "current", "latest", "newer", "url", "changelog", "checked_at", "offline", "notes", "dismissed"}.
    `notes` is {language: summary} of the newer release; `dismissed` says that the person asked not to be told about that version again."""
    cfg = settings(config)
    release = state.get("release") if isinstance(state.get("release"), dict) else None
    latest = release.get("tag", "").lstrip("v") if release else ""
    newer = bool(cfg["check"] and release and is_newer(latest, current))
    channel = install_channel()
    return {"enabled": cfg["check"], "airgapped": cfg["airgapped"], "current": current, "latest": latest if release else "", "newer": newer,
            "channel": channel, "command": update_command(channel, latest) if newer else "",
            "url": release.get("url", "") if newer else "", "changelog": f"https://github.com/{REPO}/blob/{release['tag']}/monitor/CHANGELOG.md" if newer else "",
            "checked_at": state.get("checked_at") or 0, "offline": bool(offline), "notes": dict(release.get("notes") or {}) if newer else {},
            "dismissed": bool(newer and state.get("dismissed") == latest)}


_BUSY = set()
_BUSY_LOCK = threading.Lock()


def _keep(state, now, release):
    """The state written after a good answer: the dismissed version stays."""
    new = {"checked_at": int(now), "release": release}
    if state.get("dismissed"):
        new["dismissed"] = state["dismissed"]
    return new


def _refresh(reader, path, now, state):
    try:
        release = clean_release(reader(ENDPOINT))
        _save(path, _keep(_load(path) or state, now, release))
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
                state = _keep(state, now, release)
                _save(path, state)
            except Exception:   # noqa: BLE001
                state = dict(state, checked_at=int(now) - INTERVAL + 3600)
                _save(path, state)
    return view(config, current, state, offline)


def notice(info, translate):
    """The one line shown in the console and in `doctor` ('' when there is nothing to say)."""
    if info.get("newer"):
        if info.get("command"):
            return translate("upd.available_cmd", version=info["latest"], current=info["current"], url=info["url"], command=info["command"])
        return translate("upd.available", version=info["latest"], current=info["current"], url=info["url"])
    return ""
