# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The settings menu of the web panel: which values of actions_monitor.json can be changed from the page, how they are checked and how they are written.

Safety rules (every one of them is tested):

  * Only the keys of SCHEMA can be read or written from the page. Anything else in the file (tokens, secrets, commands, keys of other tools) is neither shown
    nor touched: a write changes the listed keys and keeps every other key exactly as it was. The webhook secret, the signature keys, the command the
    sentinel can run and the AI settings with credentials are NOT in the schema, so the page can neither show nor change them.
  * Every value is checked against its type and range before anything is written; one invalid value refuses the whole request and nothing is written.
  * The file is written atomically (temporary file + replace) after a copy of the previous one goes to config_backups/ (the last BACKUPS copies are kept).
  * A path must be text without control characters, never a network (UNC) path and never on the D: drive.
  * Each setting says whether it needs a restart of the monitor (the loop reads the configuration once) or applies at once.

The web server only answers these requests to the page of the same machine (the same Host/Origin checks as every other endpoint).
"""
import json
import os
import re
import shutil
import time
from pathlib import Path

import i18n
import toolconfig

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "actions_monitor.json"
BACKUP_DIR = HERE / "config_backups"
BACKUPS = 10
MAX_BODY = 16384

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{0,39}$")
_FOREIGN = re.compile(r"^(?:[Dd]:|/mnt/[dD](?:/|$)|/[dD](?:/|$))")

# group, path, type, bounds / enum, restart.   Types: int, float, bool, enum, text, path, names (list of repository names), eco (the string "all" or a list of ecosystem names)
_G_GENERAL, _G_POLL, _G_SENT, _G_SURF, _G_READY, _G_PATHS, _G_OUT = "general", "polling", "sentinel", "surface", "readiness", "paths", "outputs"
SCHEMA = [
    (_G_GENERAL, "language", "enum", ("",) + tuple(i18n.LANGS), False),
    (_G_GENERAL, "github_owner", "text", OWNER_RE, True),
    (_G_GENERAL, "mode", "enum", ("full", "lite"), True),
    (_G_GENERAL, "ecosystems", "eco", None, True),
    (_G_GENERAL, "exclude", "names", None, True),
    (_G_GENERAL, "report_history_days", "int", (1, 365), True),
    (_G_POLL, "refresh_seconds", "int", (10, 3600), True),
    (_G_POLL, "cold_refresh_seconds", "int", (60, 86400), True),
    (_G_POLL, "issues_refresh_seconds", "int", (30, 86400), True),
    (_G_POLL, "discover_refresh_seconds", "int", (300, 86400), True),
    (_G_POLL, "stuck_minutes", "int", (10, 1440), True),
    (_G_POLL, "runs_per_repo", "int", (5, 100), True),
    (_G_POLL, "cold_runs_per_repo", "int", (1, 100), True),
    (_G_POLL, "hot_hours", "int", (1, 48), True),
    (_G_POLL, "max_workers", "int", (1, 32), True),
    (_G_POLL, "min_rate_remaining", "int", (100, 5000), True),
    (_G_SENT, "sentinel.enabled", "bool", None, True),
    (_G_SENT, "sentinel.refresh_seconds", "int", (60, 86400), True),
    (_G_SENT, "sentinel.alerts_hot_seconds", "int", (60, 86400), True),
    (_G_SENT, "sentinel.alerts_cold_seconds", "int", (60, 86400), True),
    (_G_SENT, "sentinel.hygiene_seconds", "int", (300, 604800), True),
    (_G_SENT, "sentinel.max_calls_per_tick", "int", (10, 500), True),
    (_G_SENT, "sentinel.budget_per_hour", "int", (50, 5000), True),
    (_G_SENT, "sentinel.workers", "int", (1, 32), True),
    (_G_SENT, "sentinel.min_rate_remaining", "int", (100, 5000), True),
    (_G_SENT, "sentinel.candidate_days", "int", (0, 60), True),
    (_G_SENT, "sentinel.candidate_min_entries", "int", (1, 100), True),
    (_G_SENT, "sentinel.stale_pr_days", "int", (1, 90), True),
    (_G_SENT, "sentinel.pending_sign_hours", "int", (1, 720), True),
    (_G_SENT, "sentinel.require_verified_signature", "bool", None, True),
    (_G_SENT, "sentinel.a2_resolve_max_calls_per_tick", "int", (0, 50), True),
    (_G_SENT, "sentinel.a2_resolve_ttl_seconds", "int", (60, 86400), True),
    (_G_SURF, "sentinel.surface.enabled", "bool", None, True),
    (_G_SURF, "sentinel.surface.refresh_seconds", "int", (600, 604800), True),
    (_G_SURF, "sentinel.surface.local_seconds", "int", (60, 86400), True),
    (_G_SURF, "sentinel.surface.max_repos_per_tick", "int", (1, 50), True),
    (_G_SURF, "sentinel.surface.min_rate_factor", "float", (1.0, 10.0), True),
    (_G_SURF, "sentinel.surface.budget_share", "float", (0.1, 1.0), True),
    (_G_READY, "sentinel.readiness.enabled", "bool", None, True),
    (_G_READY, "sentinel.readiness.min_coverage", "float", (0.0, 1.0), True),
    (_G_READY, "sentinel.readiness.warn_below", "int", (0, 100), True),
    (_G_PATHS, "workspace_root", "path", None, True),
    (_G_PATHS, "signed_dir", "path", None, True),
    (_G_PATHS, "audit_dir", "path", None, True),
    (_G_PATHS, "ecosystems_file", "path", None, True),
    (_G_PATHS, "targets_file", "path", None, True),
    (_G_PATHS, "profiles_file", "path", None, True),
    (_G_PATHS, "tools_dir", "path", None, True),
    (_G_PATHS, "sentinel.ci_red_file", "path", None, True),
    (_G_PATHS, "sentinel.ci_red_audit_copy", "bool", None, True),
    (_G_OUT, "outputs.prometheus.enabled", "bool", None, False),
    (_G_OUT, "outputs.prometheus.per_repo", "bool", None, False),
    (_G_OUT, "outputs.json.enabled", "bool", None, False),
    (_G_OUT, "outputs.dashboard.enabled", "bool", None, False),
]
FIELDS = {row[1]: row for row in SCHEMA}
GROUPS = (_G_GENERAL, _G_POLL, _G_SENT, _G_SURF, _G_READY, _G_PATHS, _G_OUT)
OUTPUT_DEFAULTS = {"prometheus": {"enabled": False, "per_repo": True}, "json": {"enabled": False}, "dashboard": {"enabled": False}}


def _get(tree, dotted, default=None):
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _set(tree, dotted, value):
    node = tree
    parts = dotted.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def check_value(path, value):
    """(ok, clean value or the reason as a stable code). Reasons: unknown, type, range, enum, text, path, names, ecosystems."""
    row = FIELDS.get(path)
    if row is None:
        return False, "unknown"
    kind, bounds = row[2], row[3]
    if kind == "bool":
        return (True, value) if isinstance(value, bool) else (False, "type")
    if kind == "int":
        if not _is_int(value):
            return False, "type"
        return (True, value) if bounds[0] <= value <= bounds[1] else (False, "range")
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, "type"
        return (True, float(value)) if bounds[0] <= value <= bounds[1] else (False, "range")
    if kind == "enum":
        if not isinstance(value, str):
            return False, "type"
        return (True, value) if value in bounds else (False, "enum")
    if kind == "text":
        if not isinstance(value, str):
            return False, "type"
        return (True, value.strip()) if bounds.match(value.strip()) else (False, "text")
    if kind == "path":
        if not isinstance(value, str):
            return False, "type"
        text = value.strip()
        if len(text) > 260 or any(ord(c) < 32 for c in text) or text.startswith(("\\\\", "//")) or _FOREIGN.match(text):
            return False, "path"
        return True, text
    if kind == "names":
        if not isinstance(value, list) or len(value) > 200 or not all(isinstance(v, str) and NAME_RE.match(v) for v in value):
            return False, "names"
        return True, list(value)
    if kind == "eco":
        if value == "all":
            return True, "all"
        known = set(toolconfig.ecosystem_names())
        if isinstance(value, list) and len(value) <= 50 and all(isinstance(v, str) and (v in known or not known) and NAME_RE.match(v) for v in value):
            return True, list(value)
        return False, "ecosystems"
    return False, "unknown"


def validate(changes):
    """({path: clean value}, {path: reason}) for a request {path: value}. A non-dict or an empty request is an error."""
    if not isinstance(changes, dict) or not changes or len(changes) > len(SCHEMA):
        return {}, {"_": "request"}
    clean, errors = {}, {}
    for path, value in changes.items():
        ok, result = check_value(path, value) if isinstance(path, str) else (False, "unknown")
        if ok:
            clean[path] = result
        else:
            errors[str(path)[:80]] = result
    return clean, errors


def _read_file(path):
    """The dict in the file; None when it is missing, FileNotFoundError aside; ValueError when it is not a JSON object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value


def describe(path=CONFIG_FILE):
    """What the page shows: {"groups": [{"id", "fields": [{"key", "type", "value", "default", "min", "max", "enum", "restart"}]}], "backups": N}.
    Values come from the file over the template; nothing outside SCHEMA is ever included."""
    template = {}
    try:
        template = _read_file(HERE / "actions_monitor.example.json")
    except (OSError, ValueError):
        pass
    try:
        current = _read_file(path)
    except (OSError, ValueError):
        current = {}
    groups = {g: [] for g in GROUPS}
    for group, key, kind, bounds, restart in SCHEMA:
        default = _get(template, key)
        if default is None and key.startswith("outputs."):
            default = _get(OUTPUT_DEFAULTS, key[len("outputs."):], False)
        value = _get(current, key, default)
        item = {"key": key, "type": kind, "value": value if value is not None else ("" if kind in ("text", "path", "enum") else None), "default": default, "restart": restart}
        if kind in ("int", "float"):
            item["min"], item["max"] = bounds
        if kind == "enum":
            item["enum"] = list(bounds)
        if kind == "eco":
            item["choices"] = toolconfig.ecosystem_names()
        groups[group].append(item)
    try:
        backups = len(list(BACKUP_DIR.glob("actions_monitor-*.json")))
    except OSError:
        backups = 0
    return {"groups": [{"id": g, "fields": groups[g]} for g in GROUPS], "backups": backups}


def _backup(path):
    """Copies the file to config_backups/ (keeps the newest BACKUPS). Returns the copy or None when there was nothing to copy."""
    if not Path(path).is_file():
        return None
    BACKUP_DIR.mkdir(exist_ok=True)
    name = BACKUP_DIR / ("actions_monitor-" + time.strftime("%Y%m%d-%H%M%S") + ".json")
    n = 1
    while name.exists():
        n += 1
        name = BACKUP_DIR / ("actions_monitor-" + time.strftime("%Y%m%d-%H%M%S") + f"-{n}.json")
    shutil.copy2(path, name)
    old = sorted(BACKUP_DIR.glob("actions_monitor-*.json"))
    for extra in old[:-BACKUPS]:
        try:
            extra.unlink()
        except OSError:
            pass
    return name


def apply(changes, path=CONFIG_FILE):
    """Checks and writes. {"ok": True, "changed": [paths], "restart": [paths that need a restart], "backup": bool} or {"ok": False, "errors": {path: reason}}.
    Nothing is written when any value is invalid or when nothing changes."""
    clean, errors = validate(changes)
    if errors:
        return {"ok": False, "errors": errors}
    path = Path(path)
    try:
        current = _read_file(path) if path.is_file() else {}
    except (OSError, ValueError):
        return {"ok": False, "errors": {"_": "unreadable"}}     # a broken file is never overwritten from the page
    changed = [key for key, value in clean.items() if _get(current, key, "\0missing") != value]
    if not changed:
        return {"ok": True, "changed": [], "restart": [], "backup": False}
    for key in changed:
        _set(current, key, clean[key])
    backup = _backup(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    toolconfig.forget()
    if "language" in changed:
        i18n.set_language(None)      # detect again with the new value
    return {"ok": True, "changed": changed, "restart": [k for k in changed if FIELDS[k][4]], "backup": backup is not None}


def output_enabled(config, name, sub="enabled"):
    """True when outputs.<name>.<sub> is on in the configuration (off when missing)."""
    return _get(config or {}, f"outputs.{name}.{sub}", OUTPUT_DEFAULTS.get(name, {}).get(sub, False)) is True
