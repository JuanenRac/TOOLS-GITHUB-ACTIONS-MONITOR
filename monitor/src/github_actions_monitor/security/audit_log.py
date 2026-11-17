# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of actions (Complete only): who did what, when and on which account, one JSON line each, appended and never rewritten. Every line carries the hash of the line before it, so a line that is changed, cut out or put in later breaks the chain and `verify` says where. It never holds a secret: names of settings and short identifiers go in, never a value of a setting, a password, a token, a cookie or a body; every text passes through the same cleaning as the notes for AIs and a key whose name looks like a secret is dropped.

It sits next to the audit of the accesses (`auth.audit`: logins, locks, refusals), which stays as it is; the log of actions is the one an administrator reads to know WHAT was changed. The file is private; past `max_mb` the old part is kept as `.1` (one generation) and the chain goes on in the new file. Several processes may write the same file (the supervisor and the accounts in a container share the state folder): each line is chained to the last line that is IN THE FILE, read under a lock between processes, so the chain stays whole. A failure to write never stops a request."""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.storage import locks

DEFAULTS = {"enabled": True, "max_mb": 10, "maintainers_can_read": False}
FILE_NAME = "audit_actions.jsonl"
SECRET_KEY = re.compile(r"(?i)(token|passw|secret|key|cookie|authorization|credential|bearer|hash|salt|csrf|session)")
ACTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,39}\Z")
FILE = None                       # tests point this to a temporary file; None = audit_actions.jsonl in the logs folder
_lock = threading.RLock()
_last = {"path": None, "hash": ""}      # the hash of the last line this process wrote (information only: the file, read under the lock, decides what the next line follows)
STATS = {"write_failures": 0, "last_write_error_at": None, "rotation_failures": 0}      # a line that could not be written is counted and shown (GET /api/audit-log), not silent
TAIL_BYTES = 65536                     # how much of the end of the file is read to find the last hash (the whole file only if no line in that part has one)


_NOTE = threading.local()


def note(target, details=None):
    """The handler of a route that knows what it is about (the action, the repository) leaves it here for the line the request will get (see take_note); it lives in the thread of the request."""
    _NOTE.value = (str(target)[:120], details if isinstance(details, dict) else None)


def take_note():
    """(target, details) left by note() in this thread since the last call, and forgets them; ("", None) when there are none."""
    value = getattr(_NOTE, "value", None)
    _NOTE.value = None
    return value or ("", None)


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


def _last_hash_of(candidate):
    """The hash of the last good line of one file, reading only its end first; None when there is none."""
    try:
        with open(candidate, "rb") as handle:
            size = handle.seek(0, 2)
            start = max(0, size - TAIL_BYTES)
            while True:
                handle.seek(start)
                lines = handle.read().decode("utf-8", errors="replace").splitlines()
                if start:
                    lines = lines[1:]      # the first one is probably cut in half
                for line in reversed(lines):
                    try:
                        found = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(found, dict) and isinstance(found.get("hash"), str):
                        return found["hash"]
                if not start:
                    return None
                start = 0
    except OSError:
        return None


def _tail_hash(target):
    """The hash of the last good line of the file (or of its `.1` when this one is new)."""
    for candidate in (target, target.with_name(target.name + ".1")):
        found = _last_hash_of(candidate)
        if found is not None:
            return found
    return ""


def degraded_note(where, error):
    try:
        from github_actions_monitor.app import degraded
        degraded.note(where, error)
    except Exception:   # noqa: BLE001 - noting the failure must not fail either
        pass


def record(config, action, user="", role="", account="", target="", result="ok", details=None, now=None, force=False):
    """Appends one line. `target` is a short identifier (a setting name, an alert code, a user name), `details` a small structure that is cleaned. Returns the line, or None when it is off or could not be written.
    `force` writes it even when the log is switched off (the change that switches it off is the last thing it records)."""
    cfg = settings(config)
    if (not cfg["enabled"] and not force) or not ACTION_RE.match(str(action)):
        return None
    now = time.time() if now is None else now
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "action": str(action), "user": str(user)[:40], "role": str(role)[:12], "account": str(account)[:60],
             "target": clean(str(target)[:120]), "result": "ok" if result == "ok" else "denied" if result == "denied" else "error"}
    if details:
        entry["details"] = clean(details)
    where = path()
    try:
        with _lock:
            private_io.private_dir(where.parent)
            with locks.process_lock(where):      # the supervisor and the accounts may append to the same file: one at a time, each one chained to the line that is really last
                try:
                    if where.exists() and where.stat().st_size > cfg["max_mb"] * 1_000_000:
                        os.replace(where, where.with_name(where.name + ".1"))
                except OSError as error:      # a reader keeps the file open (Windows): the action is still written to the current file and the rotation is tried again at the next one
                    STATS["rotation_failures"] += 1
                    degraded_note("audit_log.rotation", error)
                entry["prev"] = _tail_hash(where)
                entry["hash"] = _digest(entry["prev"], {k: v for k, v in entry.items() if k != "hash"})
                with private_io.open_append(where) as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                _last.update(path=str(where), hash=entry["hash"])
        return entry
    except OSError as error:      # includes the timeout of the lock between processes
        STATS["write_failures"] += 1
        STATS["last_write_error_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            from github_actions_monitor.app import degraded
            degraded.note("audit_log", error)
        except Exception:   # noqa: BLE001 - noting the failure must not fail either
            pass
        return None


def read(limit=200, account=None):
    """The last `limit` lines, newest last. With `account` only the lines of that account are kept (the file of an account holds no others; this is the second wall)."""
    try:
        lines = path().read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and (not account or item.get("account") == account):
            out.append(item)
    try:
        count = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        return []
    return out[-count:]


def _read_lines(where):
    """The lines of a file, or None when it cannot be read (a missing file)."""
    try:
        return where.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def _walk(lines, previous):
    """Checks one segment of the chain: (broken_at or None, entries, hash of its last line, `prev` of its first line). `previous` is the hash the first line must follow, or None to take it as given."""
    first = None
    for number, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except ValueError:
            return number, number - 1, previous, first
        if not isinstance(entry, dict) or not isinstance(entry.get("hash"), str) or not isinstance(entry.get("prev"), str):
            return number, number - 1, previous, first
        if first is None:
            first = entry["prev"]
        if previous is not None and entry["prev"] != previous:
            return number, number - 1, previous, first
        if _digest(entry["prev"], {k: v for k, v in entry.items() if k != "hash"}) != entry["hash"]:
            return number, number - 1, previous, first
        previous = entry["hash"]
    return None, len(lines), previous, first


def verify(target=None):
    """{"ok", "entries", "broken_at", "segments", "complete"}: the chain of the file AND of its rotated `.1` when there is one, with the link between the two (the first line of the file must follow the last line of the `.1`).
    `broken_at` is the 1-based line, inside `segment` ("rotated" or "active"), that does not follow from the one before or does not hash to what it says. `complete` is False when the chain does not begin at its
    first link (the `.1` that came before was replaced by a later rotation, or was deleted): what is there is whole but it is not all the history."""
    where = Path(target) if target else path()
    parts = [(name, lines) for name, lines in (("rotated", _read_lines(where.with_name(where.name + ".1"))), ("active", _read_lines(where))) if lines]
    previous, total, complete = None, 0, None
    for name, lines in parts:
        broken, count, previous, first = _walk(lines, previous)
        if complete is None:
            complete = first == ""
        if broken:
            return {"ok": False, "entries": total + count, "broken_at": broken, "segment": name, "segments": len(parts), "complete": bool(complete)}
        total += count
    return {"ok": True, "entries": total, "broken_at": None, "segments": len(parts), "complete": True if complete is None else bool(complete)}


def may_read(config, role):
    """Who reads it: an administrator (and the person at the computer in the individual mode, role ''), a maintainer only when the setting says so, nobody else."""
    if role in ("", "admin"):
        return True
    return role == "maintainer" and settings(config)["maintainers_can_read"]
