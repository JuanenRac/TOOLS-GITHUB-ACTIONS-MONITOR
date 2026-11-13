# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who does each READ: the pool of sources of the monitor. Standard library only.

  user    the login of `gh` (or the token the monitor keeps)                       always there
  app     the installation token of a GitHub App (github_app.py)                   with github_app.enabled
  extra   a second read-only account, given as the PATH of a file with its token   with extra_reader.enabled + extra_reader.file

Each source has its own allowance. A read goes to the source with the most calls left (the figure of the last free `rate_limit` probe, minus the reads made since), so the reads are spread and none runs
dry first; a source that fails (a refused token, a missing permission) is left out for five minutes and the read is made again with the next one, the user last. Only READS are spread (github_app.is_read):
writes and actions keep the token of the user.

The token of the extra account is read from its file at the moment of use, kept only in the memory of the call, and never stored in the configuration, printed, logged or sent anywhere but to `gh` as
GH_TOKEN. Create it as a fine-grained token with read-only permissions, in a file only you can read, outside any repository.
"""
import os
import re
import time

from github_actions_monitor.integrations import github_app

DEFAULTS = {"enabled": False, "file": ""}
TOKEN_RE = re.compile(r"^(?:gh[pousr]_[A-Za-z0-9_]{20,255}|github_pat_[A-Za-z0-9_]{20,255}|[A-Fa-f0-9]{40})$")
PAUSE = 300      # seconds a failing source is left out
ASSUMED = 3000   # the calls assumed left in a source that has not been probed yet
_STATE = {"left": {}, "failed": {}, "turn": 0}


def settings(config):
    block = (config or {}).get("extra_reader") if isinstance((config or {}).get("extra_reader"), dict) else {}
    path = block.get("file") if isinstance(block.get("file"), str) else ""
    good = bool(path) and len(path) <= 260 and not any(ord(c) < 32 for c in path) and not path.startswith(("\\\\", "//")) and not re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", path)
    return {"enabled": block.get("enabled") is True, "file": path if good else ""}


def token_from_file(path):
    """The token inside the file (first line), or "" when the file is missing, too big or does not hold a token. The value is returned to the caller and kept nowhere."""
    try:
        if not path or os.path.getsize(path) > 1024:
            return ""
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            line = handle.readline().strip()
        return line if TOKEN_RE.match(line) else ""
    except OSError:
        return ""


def file_warning(path):
    return github_app.key_warning(path) if path else ""


def available(config, now=None):
    """The names of the sources that can read now, in the order of preference when the allowances are equal."""
    now = time.time() if now is None else now
    names = []
    if github_app.settings(config)["enabled"] and _STATE["failed"].get("app", 0) + PAUSE < now:
        names.append("app")
    extra = settings(config)
    if extra["enabled"] and extra["file"] and _STATE["failed"].get("extra", 0) + PAUSE < now:
        names.append("extra")
    names.append("user")
    return names


def note_probe(name, remaining):
    """The figure of a free `rate_limit` call of that source."""
    if isinstance(remaining, int) and not isinstance(remaining, bool):
        _STATE["left"][name] = remaining


def note_failure(name, now=None):
    _STATE["failed"][name] = time.time() if now is None else now


def pick(config, args, now=None):
    """(name, env) for a read: the source with the most calls left and the environment to hand to `gh` ({} for the user). Writes and anything that is not a read: ("user", {})."""
    if not github_app.is_read(args):
        return "user", {}
    names = available(config, now)
    if len(names) == 1:
        return "user", {}
    _STATE["turn"] += 1
    ranked = sorted(names, key=lambda n: (-_STATE["left"].get(n, ASSUMED), (names.index(n) + _STATE["turn"]) % len(names)))
    for name in ranked:
        token = ""
        if name == "app":
            token = github_app.token(config)
        elif name == "extra":
            token = token_from_file(settings(config)["file"])
        if name == "user":
            return "user", {}
        if token:
            _STATE["left"][name] = _STATE["left"].get(name, ASSUMED) - 1      # the reads made since the last probe
            env = dict(os.environ)
            env["GH_TOKEN"] = token
            return name, {"env": env}
        note_failure(name, now)
    return "user", {}


def env_for(config, name):
    """The environment for a call that must use one source ("app", "extra") or the user ("user": {})."""
    token = github_app.token(config) if name == "app" else token_from_file(settings(config)["file"]) if name == "extra" else ""
    if name == "user" or not token:
        return {}
    env = dict(os.environ)
    env["GH_TOKEN"] = token
    return {"env": env}


def snapshot():
    """For the page: how many calls each source has left, as last probed (no token, no path)."""
    return {"left": dict(_STATE["left"]), "failed": [n for n, t in _STATE["failed"].items() if t + PAUSE > time.time()]}


def reset():
    _STATE.update({"left": {}, "failed": {}, "turn": 0})
