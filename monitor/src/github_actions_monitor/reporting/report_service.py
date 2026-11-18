# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The scheduled report as a service: the settings (`report_schedule.*`, all off by default), the schedule that asks whether a report is owed, the files it writes under `data/reports/`, their retention and a safe way to list and read them. One report is written at most once for a scheduled minute (the memory of the last run is a small file next to them), a failure is noted and never stops the monitor, and the first report waits for the first scheduled minute after the setting was switched on."""
import json
import re
import time
from pathlib import Path

from github_actions_monitor import i18n
from github_actions_monitor.app import degraded
from github_actions_monitor.reporting import report_builder as builder, report_render as render, report_schedule as schedule
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import locks
from github_actions_monitor.util import paths

DEFAULTS = {"enabled": False, "cron": "0 8 * * 1", "formats": "both", "keep": 12, "top": 10}
FORMATS = ("html", "markdown", "both")
EXT = {"html": "html", "markdown": "md"}
NAME_RE = re.compile(r"^report_([A-Za-z0-9._-]{1,60})_(\d{8}-\d{6})\.(html|md)\Z")
SAFE_ACCOUNT = re.compile(r"[^A-Za-z0-9._-]")
STATE_FILE = "_state.json"


def settings(config):
    """The settings with their defaults; a value of the wrong type or out of range is replaced by the default (the page checks them before writing, a hand-edited file may not)."""
    user = (config or {}).get("report_schedule") if isinstance((config or {}).get("report_schedule"), dict) else {}
    out = dict(DEFAULTS)
    if isinstance(user.get("enabled"), bool):
        out["enabled"] = user["enabled"]
    if isinstance(user.get("cron"), str) and schedule.parse(user["cron"]) is not None:
        out["cron"] = " ".join(user["cron"].split())
    if user.get("formats") in FORMATS:
        out["formats"] = user["formats"]
    for key, low, high in (("keep", 1, 500), ("top", 1, 50)):
        value = user.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    return out


def folder(base=None):
    return Path(paths.folder("data", base)) / "reports"


def _account(name):
    return SAFE_ACCOUNT.sub("_", str(name or "main"))[:60] or "main"


def _state(directory, strict=False):
    """The state file. With `strict` a file that exists and cannot be read raises OSError (the reader is going to write it back: it must not write an empty one over the accounts of the others)."""
    from github_actions_monitor.storage import file_storage
    return file_storage.read_json(directory / STATE_FILE, dict, {}, strict=strict)


def _save_state(directory, state):
    private_io.write_private(directory / STATE_FILE, json.dumps(state, indent=1, sort_keys=True))


def _update_entry(directory, key, **changes):
    """Changes the entry of ONE account in the state file that every account of the installation shares: read, change and write are one step under a lock (of the threads and of the processes), so two
    accounts that finish a report in the same moment never overwrite each other."""
    with locks.os_lock(directory / STATE_FILE, 10.0):
        try:
            state = _state(directory, strict=True)
        except OSError as error:      # the file is there but cannot be read now: nothing is written, the next report tries again
            from github_actions_monitor.app import degraded
            degraded.note("reports.state", error)
            return
        state.setdefault("accounts", {}).setdefault(key, {}).update(changes)
        for attempt in range(10):
            try:
                _save_state(directory, state)
                return
            except PermissionError:      # Windows: another process has the file open for a moment (a reader); the replace is tried again
                if attempt == 9:
                    raise
                time.sleep(0.02 * (attempt + 1))


def run(config, account, snapshot, alerts, team, now=None, base=None, lang=None):
    """Writes one report now (the formats of the settings) and returns {"files": [names], "at": iso}. The memory of what was in it goes to the state file so the next one can say what changed."""
    now = time.time() if now is None else now
    cfg = settings(config)
    directory = folder(base)
    private_io.private_dir(directory)
    key = _account(account)
    state = _state(directory)
    previous = (state.get("accounts") or {}).get(key, {}).get("memory")
    doc = builder.build(account, snapshot, alerts, team, now, previous, cfg["top"])
    language = lang or i18n.language()
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime(now))
    wanted = ("html", "markdown") if cfg["formats"] == "both" else (cfg["formats"],)
    files = []
    try:
        for kind in wanted:
            text = render.page(doc, language) if kind == "html" else render.markdown(doc, language)
            name = f"report_{key}_{stamp}.{EXT[kind]}"
            private_io.write_private(directory / name, text)
            files.append(name)
    except BaseException:      # a report is all its formats or nothing: the file already written would be listed as a report that has no pair
        for name in files:
            try:
                (directory / name).unlink()
            except OSError as error:
                degraded.note("reports.cleanup", error)
        raise
    _update_entry(directory, key, memory=builder.memory(doc, alerts), last_run=now, last_files=files)
    prune(directory, key, cfg["keep"])
    return {"files": files, "at": doc["generated_at"]}


def prune(directory, key, keep):
    """Keeps the newest `keep` runs of one account (a run is the set of files with the same stamp); the older ones go."""
    stamps = {}
    for path in directory.glob(f"report_{key}_*"):
        found = NAME_RE.match(path.name)
        if found and found.group(1) == key:
            stamps.setdefault(found.group(2), []).append(path)
    for stamp in sorted(stamps, reverse=True)[keep:]:
        for path in stamps[stamp]:
            try:
                path.unlink()
            except OSError as error:
                degraded.note("reports.prune", error)


def tick(config, account, gather, now=None, base=None):
    """Called every cycle: when the schedule says a report is owed it calls `gather()` for ({snapshot}, alerts, team) and writes one. Returns what `run` returns or None. The first call after the setting is
    switched on only starts the clock. A failure is noted, the slot is considered used (no retry storm) and the next scheduled minute tries again."""
    now = time.time() if now is None else now
    cfg = settings(config)
    if not cfg["enabled"]:
        return None
    directory = folder(base)
    key = _account(account)
    state = _state(directory)
    entry = (state.get("accounts") or {}).get(key, {})
    last = entry.get("last_run")
    if not isinstance(last, (int, float)):
        private_io.private_dir(directory)
        _update_entry(directory, key, last_run=now)
        return None
    if not schedule.due(cfg["cron"], now, last):
        return None
    try:
        snapshot, alerts, team = gather()
        return run(config, account, snapshot, alerts, team, now, base)
    except Exception as error:   # noqa: BLE001 - a report never stops the monitor
        degraded.note("reports.run", error)
        try:
            _update_entry(directory, key, last_run=now)
        except (OSError, TimeoutError) as inner:
            degraded.note("reports.state", inner)
        return None


def listing(account, base=None):
    """The reports of one account, newest first: [{name, kind, bytes, at}]."""
    directory, key, rows = folder(base), _account(account), []
    if not directory.is_dir():
        return rows
    for path in directory.iterdir():
        found = NAME_RE.match(path.name)
        if found and found.group(1) == key:
            try:
                rows.append({"name": path.name, "kind": "html" if found.group(3) == "html" else "markdown", "bytes": path.stat().st_size, "stamp": found.group(2)})
            except OSError:
                continue
    return sorted(rows, key=lambda r: (r["stamp"], r["name"]), reverse=True)


def read_file(account, name, base=None):
    """(bytes, content type) of one report of this account, or None: the name must be exactly the one the service writes and belong to the account, so no other path can be asked for."""
    found = NAME_RE.match(str(name or ""))
    if not found or found.group(1) != _account(account):
        return None
    path = folder(base) / name
    try:
        return path.read_bytes(), ("text/html; charset=utf-8" if found.group(3) == "html" else "text/markdown; charset=utf-8")
    except OSError:
        return None
