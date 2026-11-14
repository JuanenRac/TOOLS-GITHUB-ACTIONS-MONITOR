# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Installs, checks and removes the gate script `ai_hook.py` in the settings of an AI tool (`monitor_cli.py ai-hook install|status|uninstall`).

The settings file of the tool is MERGED, never replaced: the hooks of other programs stay as they are, only the entries that run `ai_hook.py` are added, replaced or removed. A copy of the file
is kept next to it before every change (the last three), a file that is not valid JSON is refused untouched, and what is written is plain ASCII JSON (no accented letter is garbled by an old
Windows console or editor). Nothing here talks to GitHub or to the network.

  --assistant  the default tool  project: <folder>/.claude/settings.local.json   user: ~/.claude/settings.json      events SessionStart, UserPromptSubmit, Stop
  --cursor   Cursor           project: <folder>/.cursor/hooks.json            user: ~/.cursor/hooks.json          events sessionStart, stop (best effort, see docs/AI_ALERTS.md)
  --generic  any other tool   nothing is written: the commands to put in its settings are printed
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

from github_actions_monitor.security import private_io

from github_actions_monitor.util import paths
SCRIPT = paths.BIN / "ai_hook.py"
MARKER = "ai_hook.py"
TARGETS = ("assistant", "cursor", "generic")
SCOPES = ("project", "user")
EVENTS = {"assistant": ("SessionStart", "UserPromptSubmit", "Stop"), "cursor": ("sessionStart", "stop"), "generic": ("SessionStart", "UserPromptSubmit", "Stop")}
KEEP_BACKUPS = 3


class InstallError(Exception):
    """The settings file cannot be merged safely (not JSON, not the shape the tool uses, cannot be written)."""


def posix(path):
    return str(path).replace("\\", "/")


def command_for(event, target, python=None, script=None):
    return f'"{posix(python or sys.executable)}" "{posix(script or SCRIPT)}" {event} --format {target}'


def settings_path(target, scope, project_dir=None, home=None):
    """The file of the tool for this scope, or None for `generic`."""
    base = Path(project_dir or os.getcwd()) if scope == "project" else Path(home or Path.home())
    if target == "assistant":
        return base / ".claude" / ("settings.local.json" if scope == "project" else "settings.json")
    if target == "cursor":
        return base / ".cursor" / "hooks.json"
    return None


def load(path):
    """(data, existed). A missing or empty file is an empty document; anything that is not a JSON object is refused."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return {}, False
    except OSError as error:
        raise InstallError(f"cannot read {posix(path)}: {error.__class__.__name__}") from None
    if not text.strip():
        return {}, True
    try:
        data = json.loads(text)
    except ValueError:
        raise InstallError(f"{posix(path)} is not valid JSON: nothing was changed") from None
    if not isinstance(data, dict):
        raise InstallError(f"{posix(path)} is not a JSON object: nothing was changed")
    return data, True


def ours(command):
    return isinstance(command, str) and MARKER in command


def _strip_nested(hooks):
    """Removes our entries from the {"Event": [{"hooks": [...]}]} map; groups that were only ours disappear. Returns the events that had one."""
    found = []
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept = []
        for group in groups:
            inner = group.get("hooks") if isinstance(group, dict) else None
            if isinstance(inner, list) and any(isinstance(h, dict) and ours(h.get("command")) for h in inner):
                found.append(event)
                rest = [h for h in inner if not (isinstance(h, dict) and ours(h.get("command")))]
                if rest:
                    kept.append(dict(group, hooks=rest))
            else:
                kept.append(group)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    return sorted(set(found))


def _strip_cursor(hooks):
    found = []
    for event in list(hooks):
        items = hooks[event]
        if not isinstance(items, list):
            continue
        kept = [h for h in items if not (isinstance(h, dict) and ours(h.get("command")))]
        if len(kept) != len(items):
            found.append(event)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    return sorted(set(found))


def merged(data, target, python=None, script=None, remove_only=False):
    """(new document, events found before). Pure: the caller decides whether to write it."""
    data = json.loads(json.dumps(data))      # a copy
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallError("the key \"hooks\" of the settings is not an object: nothing was changed")
    found = (_strip_cursor if target == "cursor" else _strip_nested)(hooks)
    if not remove_only:
        for event in EVENTS[target]:
            command = command_for(event, target, python, script)
            if target == "cursor":
                hooks.setdefault(event, []).append({"command": command})
            else:
                hooks.setdefault(event, []).append({"hooks": [{"type": "command", "command": command, "timeout": 10}]})
        if target == "cursor":
            data.setdefault("version", 1)
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    return data, found


def dump(data):
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


def backup(path, now=None):
    """A copy next to the file, `NAME.monitor-backup-YYYYmmddHHMMSS`; only the last KEEP_BACKUPS stay. Returns the path of the copy."""
    path = Path(path)
    stamp = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time() if now is None else now))
    copy = path.with_name(f"{path.name}.monitor-backup-{stamp}")
    shutil.copy2(path, copy)
    try:
        os.chmod(copy, 0o600)
    except OSError:
        pass
    old = sorted(path.parent.glob(path.name + ".monitor-backup-*"))
    for extra in old[:-KEEP_BACKUPS]:
        try:
            extra.unlink()
        except OSError:
            pass
    return copy


def _write(path, text):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        private_io.write_private(path, text)      # mode 0600, like every file of the monitor
    except OSError as error:
        raise InstallError(f"cannot write {posix(path)}: {error.__class__.__name__}") from None


def install(target="assistant", scope="project", project_dir=None, home=None, python=None, script=None, now=None, dry_run=False):
    """Adds the three (two for Cursor) entries. Returns a report; `action` is installed, updated (already there, changed), unchanged or printed (generic)."""
    commands = {event: command_for(event, target, python, script) for event in EVENTS[target]}
    if target == "generic":
        return {"target": target, "scope": None, "file": None, "action": "printed", "events": list(EVENTS[target]), "commands": commands, "backup": None}
    path = settings_path(target, scope, project_dir, home)
    before, existed = load(path)
    after, found = merged(before, target, python, script)
    changed = dump(after) != dump(before) or not existed
    action = "unchanged" if not changed else ("updated" if found else "installed")
    copy = None
    if changed and not dry_run:
        if existed and path.stat().st_size:
            copy = backup(path, now)
        _write(path, dump(after))
    return {"target": target, "scope": scope, "file": posix(path), "action": action if not dry_run or not changed else "would_" + action, "events": list(EVENTS[target]), "commands": commands,
            "backup": posix(copy) if copy else None}


def uninstall(target="assistant", scope="project", project_dir=None, home=None, now=None, dry_run=False):
    """Removes only the entries that run ai_hook.py. Returns a report; `action` is removed or absent."""
    if target == "generic":
        return {"target": target, "scope": None, "file": None, "action": "absent", "events": [], "commands": {}, "backup": None}
    path = settings_path(target, scope, project_dir, home)
    before, existed = load(path)
    if not existed:
        return {"target": target, "scope": scope, "file": posix(path), "action": "absent", "events": [], "commands": {}, "backup": None}
    after, found = merged(before, target, remove_only=True)
    if not found:
        return {"target": target, "scope": scope, "file": posix(path), "action": "absent", "events": [], "commands": {}, "backup": None}
    copy = None
    if not dry_run:
        copy = backup(path, now)
        _write(path, dump(after))
    return {"target": target, "scope": scope, "file": posix(path), "action": "would_remove" if dry_run else "removed", "events": found, "commands": {}, "backup": posix(copy) if copy else None}


def status(project_dir=None, home=None, config=None):
    """Where the gate script is installed: one row per tool and scope (the file, whether it exists, the events that run ai_hook.py, whether the script they call exists), plus the settings
    that rule it (`ai_alerts.client_hook`) and the last time it read the brief."""
    rows = []
    for target in ("assistant", "cursor"):
        for scope in SCOPES:
            path = settings_path(target, scope, project_dir, home)
            row = {"target": target, "scope": scope, "file": posix(path), "exists": path.is_file(), "events": [], "script_ok": None, "error": None}
            try:
                data, existed = load(path)
                hooks = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
                scripts = []
                for event, groups in hooks.items():
                    for group in groups if isinstance(groups, list) else []:
                        for hook in (group.get("hooks") if isinstance(group, dict) and isinstance(group.get("hooks"), list) else [group]):
                            if isinstance(hook, dict) and ours(hook.get("command")):
                                row["events"].append(event)
                                scripts.append(hook["command"])
                row["events"] = sorted(set(row["events"]))
                if scripts:
                    parts = [p for p in scripts[0].split('"') if MARKER in p]
                    row["script_ok"] = bool(parts) and Path(parts[0]).is_file()
            except InstallError as error:
                row["error"] = str(error)
            rows.append(row)
    return {"installed": any(r["events"] for r in rows), "targets": rows, "script": posix(SCRIPT), "script_present": SCRIPT.is_file(), "settings": client_settings(config)}


def client_settings(config=None):
    from github_actions_monitor.integrations import ai_alerts
    cfg = ai_alerts.settings(config if config is not None else _config())
    return cfg["client_hook"]


def _config():
    try:
        from github_actions_monitor.app import toolconfig
        return toolconfig.raw_config()
    except Exception:      # noqa: BLE001 - the status is still useful without the file
        return {}
