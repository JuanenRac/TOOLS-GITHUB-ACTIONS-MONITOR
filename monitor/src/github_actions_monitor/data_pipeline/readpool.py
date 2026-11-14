# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who does each READ: the pool of sources of the monitor. Standard library only.

  user    the login of `gh` (or the token the monitor keeps)                       always there
  app     the installation token of a GitHub App (github_app.py)                   with github_app.enabled
  extra   a second read-only account, given as the PATH of a file with its token   with extra_reader.enabled + extra_reader.file

Each source has its own allowance. By default a read goes to the source with the most calls left (the figure of the last free `rate_limit` probe, minus the reads made since), so the reads are spread and none runs
dry first. Two settings change that (block `readpool`, both off by default): `readpool.prefer.<kind>` names the source that answers a KIND of read first (runs, security alerts, issues and pull requests, history, discovery, the rest;
`auto` keeps the spread) and `readpool.reserve.<source>` keeps at least that many calls free in a source for what other programs do with it (the `gh` of your tools and agents on the allowance of the user): a source under its
reserve takes no read while another one can. The allowances are added up for the figure the working modes and the page use. A source that fails (a refused token, a missing permission) is left out for five minutes and the read is made again with the next one, the user last. Only READS are spread (github_app.is_read):
writes and actions keep the token of the user.

The token of the extra account is read from its file at the moment of use, kept only in the memory of the call, and never stored in the configuration, printed, logged or sent anywhere but to `gh` as
GH_TOKEN. Create it as a fine-grained token with read-only permissions, in a file only you can read, outside any repository.
"""
import os
import re
import time
from pathlib import Path

from github_actions_monitor.integrations import github_app

DEFAULTS = {"enabled": False, "file": "", "any_folder": False}
TOKEN_RE = re.compile(r"^(?:gh[pousr]_[A-Za-z0-9_]{20,255}|github_pat_[A-Za-z0-9_]{20,255}|[A-Fa-f0-9]{40})\Z")
KINDS = ("runs", "security", "issues", "history", "discovery", "other")
SOURCES = ("user", "app", "extra")
PREFERENCES = ("auto",) + SOURCES
KIND_RE = (("security", re.compile(r"code-scanning|dependabot|secret-scanning|vulnerab|security-advisor", re.I)), ("runs", re.compile(r"actions/|/runs?\b|/workflows?\b|check-runs|check-suites", re.I)),
           ("issues", re.compile(r"/issues\b|/pulls?\b", re.I)), ("history", re.compile(r"/releases?\b|/commits?\b|/tags\b|/compare/|/contents/|/git/", re.I)),
           ("discovery", re.compile(r"^(?:orgs|search|users)/|/repos\?|^repositories|^orgs/[^/]+/repos", re.I)))
PAUSE = 300      # seconds a failing source is left out
ASSUMED = 3000   # the calls assumed left in a source that has not been probed yet
_STATE = {"left": {}, "failed": {}, "turn": 0}


def inside_accounts(path):
    """True when `path` is a file under the folder of the accounts of the monitor (`accounts/`, or MONITOR_ACCOUNTS_DIR) and no part of the way from that folder to the file is a link."""
    from github_actions_monitor.accounts import accounts
    try:
        root = Path(os.path.abspath(accounts.root_dir()))
        target = Path(os.path.abspath(path))
        relative = target.relative_to(root)
    except (ValueError, OSError):
        return False
    if not relative.parts:
        return False
    step = root
    for part in relative.parts:
        step = step / part
        if os.path.islink(step):
            return False
    return True


def settings(config):
    """`file` is empty unless the path is acceptable: plain text, no network path, never the D: drive and, unless `extra_reader.any_folder` is on (off by default), inside the accounts folder."""
    block = (config or {}).get("extra_reader") if isinstance((config or {}).get("extra_reader"), dict) else {}
    path = block.get("file") if isinstance(block.get("file"), str) else ""
    good = bool(path) and len(path) <= 260 and not any(ord(c) < 32 for c in path) and not path.startswith(("\\\\", "//")) and not re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", path)
    anywhere = block.get("any_folder") is True
    if good and not anywhere and not inside_accounts(path):
        good = False
    return {"enabled": block.get("enabled") is True, "file": path if good else "", "any_folder": anywhere}


def token_from_file(path):
    """The token inside the file (first line), or "" when the file is missing, too big, a link or does not hold a token. The value is returned to the caller and kept nowhere. The file is opened
    without following a link (where the system can: O_NOFOLLOW) and only a regular file is read."""
    try:
        if not path or os.path.islink(path):
            return ""
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "rb") as handle:
            import stat
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 1024:
                return ""
            line = handle.readline(1100).decode("utf-8", "ignore").strip()
        return line if TOKEN_RE.match(line) else ""
    except OSError:
        return ""


def file_warning(path):
    return github_app.key_warning(path) if path else ""


def pool_settings(config):
    """`readpool.prefer.<kind>` (auto, user, app, extra) and `readpool.reserve.<source>` (calls kept free, 0 to 4000), each with its conservative default: the spread of always and no reserve."""
    block = (config or {}).get("readpool") if isinstance((config or {}).get("readpool"), dict) else {}
    prefer = block.get("prefer") if isinstance(block.get("prefer"), dict) else {}
    reserve = block.get("reserve") if isinstance(block.get("reserve"), dict) else {}
    return {"prefer": {k: prefer[k] if prefer.get(k) in PREFERENCES else "auto" for k in KINDS},
            "reserve": {s: reserve[s] if isinstance(reserve.get(s), int) and not isinstance(reserve.get(s), bool) and 0 <= reserve[s] <= 4000 else 0 for s in SOURCES}}


def kind_of(args):
    """The kind of a read, from the call: `gh api ENDPOINT` by its endpoint, `gh run list` by its verb. The endpoint decides, not the repository."""
    args = [str(a) for a in args]
    if args and args[0] == "api":
        endpoint = next((a for a in args[1:] if not a.startswith("-")), "").lstrip("/")
        for kind, pattern in KIND_RE:
            if pattern.search(endpoint):
                return kind
        return "other"
    return {"run": "runs", "workflow": "runs", "issue": "issues", "pr": "issues", "release": "history", "search": "discovery"}.get(args[0] if args else "", "other")


def below_reserve(name, config):
    """True when the last known allowance of the source is not above the reserve asked for it (nothing known = not below)."""
    keep = pool_settings(config)["reserve"].get(name, 0)
    left = _STATE["left"].get(name)
    return bool(keep) and left is not None and left <= keep


def pooled(sources):
    """The allowance of ALL the sources added up: {"remaining", "limit", "reset"} (the reset of the user when there is one, else the earliest). `sources` is {name: {"remaining", "limit", "reset"}}; raises
    ValueError when it is empty. One source gives its own figures unchanged."""
    if not sources:
        raise ValueError("no source")
    if len(sources) == 1:
        return dict(next(iter(sources.values())))
    first = sources.get("user") or min(sources.values(), key=lambda s: str(s.get("reset")))
    return {"remaining": sum(int(s["remaining"]) for s in sources.values()), "limit": sum(int(s["limit"]) for s in sources.values()), "reset": first["reset"]}


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
    ranked = [n for n in ranked if not below_reserve(n, config)] + [n for n in ranked if below_reserve(n, config)]      # a source under its reserve answers only when no other can
    wanted = pool_settings(config)["prefer"][kind_of(args)]
    if wanted in ranked and not below_reserve(wanted, config):
        ranked.remove(wanted)
        ranked.insert(0, wanted)      # the preferred source of this kind first; if it fails the others follow, the user last
    for name in ranked:
        token = ""
        if name == "app":
            token = github_app.token(config)
        elif name == "extra":
            token = token_from_file(settings(config)["file"])
        if name == "user":
            if "user" in _STATE["left"]:
                _STATE["left"]["user"] -= 1      # the reads made since the last probe count against the reserve of the user too
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
