# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of actions (Complete only): who did what, when and on which account, one JSON line each, appended and never rewritten. Every line carries the hash of the line before it, so a line that is changed, cut out or put in later breaks the chain and `verify` says where. It never holds a secret: names of settings and short identifiers go in, never a value of a setting, a password, a token, a cookie or a body; every text passes through the same cleaning as the notes for AIs and a key whose name looks like a secret is dropped.

It sits next to the audit of the accesses (`auth.audit`: logins, locks, refusals), which stays as it is; the log of actions is the one an administrator reads to know WHAT was changed. The file is private; past `max_mb` the old part is kept as `.1` (one generation) and the chain goes on in the new file. A failure to write never stops a request."""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

from github_actions_monitor.security import private_io

DEFAULTS = {"enabled": True, "max_mb": 10, "maintainers_can_read": False}
FILE_NAME = "audit_actions.jsonl"
SECRET_KEY = re.compile(r"(?i)(token|passw|secret|key|cookie|authorization|credential|bearer|hash|salt|csrf|session)")
ACTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,39}\Z")
FILE = None                       # tests point this to a temporary file; None = audit_actions.jsonl in the logs folder
_lock = threading.RLock()
_last = {"path": None, "hash": ""}


def settings(config):
    """The settings with their defaults; a value of the wrong type or out of range is replaced by the default."""
    user = (config or {}).get("audit_log") if isinstance((config or {}).get("audit_log"), dict) else {}
    out = dict(DEFAULTS)
    for key in ("enabled", "maintainers_can_read"):
        if isinstance(user.get(key), bool):
            out[key] = user[key]
    value = user.get("max_mb")
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 500:
        out["max_mb"] = value
    return out


def path():
    if FILE is not None:
        return Path(FILE)
    from github_actions_monitor.security import auth
    if auth.AUDIT_FILE is not None:      # where the audit of the accesses is pointed (the tests), the log of actions lives next to it
        return Path(auth.AUDIT_FILE).with_name(FILE_NAME)
    from github_actions_monitor.util import paths
    chosen = os.environ.get("MONITOR_STATE_DIR", "").strip()
    return (Path(chosen) if chosen else paths.folder("logs")) / FILE_NAME


def clean(value, depth=0):
    """A structure cleaned for the log: a key that looks like a secret is dropped, every text is cleaned and cut, depth and size are limited."""
    from github_actions_monitor.integrations import ai_alerts
    if depth > 3:
        return None
    if isinstance(value, dict):
        return {str(k)[:40]: clean(v, depth + 1) for k, v in list(value.items())[:30] if not SECRET_KEY.search(str(k))}
    if isinstance(value, (list, tuple)):
        return [clean(v, depth + 1) for v in list(value)[:30]]
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    return ai_alerts.redact(str(value), 200)


def _digest(previous, entry):
    body = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256((previous + "\n" + body).encode("utf-8")).hexdigest()


def _tail_hash(target):
    """The hash of the last good line of the file (or of its `.1` when this one is new)."""
    for candidate in (target, target.with_name(target.name + ".1")):
        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            try:
                found = json.loads(line)
            except ValueError:
                continue
            if isinstance(found, dict) and isinstance(found.get("hash"), str):
                return found["hash"]
    return ""


def record(config, action, user="", role="", account="", target="", result="ok", details=None, now=None):
    """Appends one line. `target` is a short identifier (a setting name, an alert code, a user name), `details` a small structure that is cleaned. Returns the line, or None when it is off or could not be written."""
    cfg = settings(config)
    if not cfg["enabled"] or not ACTION_RE.match(str(action)):
        return None
    now = time.time() if now is None else now
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "action": str(action), "user": str(user)[:40], "role": str(role)[:12], "account": str(account)[:60],
             "target": clean(str(target)[:120]), "result": "ok" if result == "ok" else "denied" if result == "denied" else "error"}
    if details:
        entry["details"] = clean(details)
    where = path()
    try:
        with _lock:
            if where.exists() and where.stat().st_size > cfg["max_mb"] * 1_000_000:
                os.replace(where, where.with_name(where.name + ".1"))
            private_io.private_dir(where.parent)
            if _last["path"] != str(where) or not where.exists():
                _last.update(path=str(where), hash=_tail_hash(where))
            entry["prev"] = _last["hash"]
            entry["hash"] = _digest(entry["prev"], {k: v for k, v in entry.items() if k != "hash"})
            with private_io.open_append(where) as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            _last["hash"] = entry["hash"]
        return entry
    except OSError:
        return None


def read(limit=200):
    """The last `limit` lines, newest last."""
    try:
        lines = path().read_text(encoding="utf-8").splitlines()[-max(1, min(int(limit), 1000)):]
    except (OSError, ValueError):
        return []
    out = []
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out


def verify(target=None):
    """{"ok", "entries", "broken_at"}: the chain of the file, from its first line (whose `prev` is taken as given, it may come from the `.1` file). `broken_at` is the 1-based line that does not follow from the one before, or that does not hash to what it says."""
    where = Path(target) if target else path()
    try:
        lines = where.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"ok": True, "entries": 0, "broken_at": None}
    previous = None
    for number, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except ValueError:
            return {"ok": False, "entries": number - 1, "broken_at": number}
        if not isinstance(entry, dict) or not isinstance(entry.get("hash"), str) or not isinstance(entry.get("prev"), str):
            return {"ok": False, "entries": number - 1, "broken_at": number}
        if previous is not None and entry["prev"] != previous:
            return {"ok": False, "entries": number - 1, "broken_at": number}
        if _digest(entry["prev"], {k: v for k, v in entry.items() if k != "hash"}) != entry["hash"]:
            return {"ok": False, "entries": number - 1, "broken_at": number}
        previous = entry["hash"]
    return {"ok": True, "entries": len(lines), "broken_at": None}


def may_read(config, role):
    """Who reads it: an administrator (and the person at the computer in the individual mode, role ''), a maintainer only when the setting says so, nobody else."""
    if role in ("", "admin"):
        return True
    return role == "maintainer" and settings(config)["maintainers_can_read"]
