# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""state_io: the bridge between the modules that always read and wrote a file and a storage that is not made of files.

A module that keeps state calls `state_io.load_json(path)` / `state_io.save_text(path, text)` / `state_io.append_events(path, events)` with the path it always used. While no storage is bound
(the file backend: Lite, and Complete by default) these do exactly what the module did before: read the file, or replace it through a temporary file. When a process binds a SQLite storage
(`bind`), the paths that the storage keeps (`ROUTES`: the feed, what the feed announced, the analytics, the sentinel states, the silences, the update notice) go to the database instead and
the other paths (the cache of conditional reads, the logs, the AI action log) stay files: they are caches and logs, not state worth a database.

`load_json` raises the same errors a missing or damaged file raised (OSError, ValueError), so the callers' `except` clauses stay as they are.

Every record written here carries `schema_version` (RECORD_SCHEMA) at the top of the object; the callers never see it (`load_json` removes it). A record without the mark is version 0 and reads as always.
A record of a NEWER version than this program understands is not read half way: it reads as a damaged file (ValueError, so the callers start from their defaults) and its name goes to `NEWER`
and to the degraded list, so the person is told which file was left aside and why.
"""
import json
import os
import sys
from pathlib import Path

from github_actions_monitor.security import private_io

#: (module, attribute holding the path, kind, name): where the state of each module lives and what it is called in the storage
ROUTES = (
    ("github_actions_monitor.data_pipeline.events", "EVENTS_FILE", "events", None),
    ("github_actions_monitor.data_pipeline.events", "STATE_FILE", "doc", "events_state"),
    ("github_actions_monitor.data_pipeline.analytics", "HISTORY_FILE", "analytics", None),
    ("github_actions_monitor.sentinels.sentinel_local", "CACHE_FILE", "sentinel", "sentinel_cache"),
    ("github_actions_monitor.sentinels.sentinel_local", "HISTORY_FILE", "sentinel", "sentinel_history"),
    ("github_actions_monitor.sentinels.sentinel_ai", "CACHE_FILE", "sentinel", "sentinel_ai_cache"),
    ("github_actions_monitor.sentinels.sentinel_collab", "STATE_FILE", "sentinel", "collab_state"),
    ("github_actions_monitor.sentinels.sentinel_security", "STATE_FILE", "sentinel", "security_state"),
    ("github_actions_monitor.sentinels.sentinel_supply", "STATE_FILE", "sentinel", "supply_state"),
    ("github_actions_monitor.sentinels.sentinel_delivery", "STATE_FILE", "sentinel", "delivery_state"),
    ("github_actions_monitor.sentinels.alert_center", "STATE_FILE", "doc", "alert_mutes"),
    ("github_actions_monitor.app.updatecheck", "STATE_FILE", "doc", "update_check"),
)
_BOUND = {"storage": None, "account": None, "routes": {}}
RECORD_SCHEMA = 1
NEWER = {}      # name of a record left aside because it is of a newer version -> that version


def _name(path):
    return Path(str(path)).name


def mark(text):
    """`text` (a JSON object) with `schema_version` as its first member; anything that is not an object, or already says its version, is returned as it came."""
    stripped = text.lstrip() if isinstance(text, str) else ""
    if not stripped.startswith("{"):
        return text
    try:
        document = json.loads(text)
    except ValueError:
        return text
    if not isinstance(document, dict) or "schema_version" in document:
        return text
    start = text.index("{") + 1
    rest = text[start:]
    return text[:start] + '"schema_version":%d%s' % (RECORD_SCHEMA, "," if rest.strip() != "}" else "") + rest


def unmark(data, path):
    """The object without its `schema_version`; raises ValueError (and remembers the name) when the record is newer than RECORD_SCHEMA."""
    if not isinstance(data, dict) or "schema_version" not in data:
        NEWER.pop(_name(path), None)
        return data
    version = data["schema_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 0 or version > RECORD_SCHEMA:
        NEWER[_name(path)] = version
        try:
            from github_actions_monitor.app import degraded
            degraded.note("records.newer", ValueError(f"{_name(path)} is of version {version}, this program reads up to {RECORD_SCHEMA}: left aside"))
        except Exception:   # noqa: BLE001 - naming it is best effort; leaving it aside is what matters
            pass
        raise ValueError(f"record {_name(path)} has schema_version {version}, newer than {RECORD_SCHEMA}")
    NEWER.pop(_name(path), None)
    return {key: value for key, value in data.items() if key != "schema_version"}


def _key(path):
    return os.path.normcase(os.path.abspath(str(path)))


def bind(storage, account_id):
    """Routes the paths of ROUTES (as the modules hold them NOW, after an account pointed them at its folder) to `storage`."""
    routes = {}
    for module, attribute, kind, name in ROUTES:
        loaded = sys.modules.get(module)
        if loaded is not None and hasattr(loaded, attribute):
            routes[_key(getattr(loaded, attribute))] = (kind, name)
    _BOUND.update(storage=storage, account=account_id, routes=routes)
    return routes


def unbind():
    _BOUND.update(storage=None, account=None, routes={})


def bound():
    """(storage, account_id) while a storage is bound, else (None, None)."""
    return _BOUND["storage"], _BOUND["account"]


def routed(path):
    return _BOUND["routes"].get(_key(path)) if _BOUND["storage"] is not None else None


def load_json(path):
    """The JSON object kept for `path`. Raises FileNotFoundError when there is none and ValueError when it is damaged, like reading the file."""
    route = routed(path)
    if route is None:
        return unmark(json.loads(private_io.read_text_with_retry(path)), path)
    storage, account = _BOUND["storage"], _BOUND["account"]
    kind, name = route
    try:
        if kind == "sentinel":
            data = storage.load_sentinel_state(account, name) or None
        elif kind == "analytics":
            data = storage.load_analytics(account) or None
        else:
            data = storage.load_doc(account, name)
    except Exception as error:      # a database that cannot be read reads as a file that cannot be read
        raise OSError(str(error)) from error
    if data is None:
        raise FileNotFoundError(str(path))
    return unmark(data, path)


def save_text(path, text):
    """Keeps `text` (a JSON object) for `path`: replaces the file through a temporary file (a name of its own) or, when the path is routed, stores it. Raises OSError like a failed write."""
    route = routed(path)
    if route is None:
        text = mark(text)
        path = Path(path)
        tmp = private_io.unique_tmp(path)
        try:
            private_io.write_tmp(tmp, text)
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        private_io.replace_with_retry(tmp, path)
        return
    storage, account = _BOUND["storage"], _BOUND["account"]
    kind, name = route
    try:
        data = json.loads(mark(text))
        if kind == "sentinel":
            storage.save_sentinel_state(account, name, data)
        elif kind == "analytics":
            storage.save_analytics(account, data)
        else:
            storage.save_doc(account, name, data)
    except Exception as error:      # text that is not JSON, a database that cannot be written: both read as a file that cannot be written, which the callers already handle
        raise OSError(str(error)) from error


def append_events(path, events):
    """Appends the events (dicts with their `at`) to the feed of `path`. Routed: one transaction of the storage. Otherwise False: the caller writes its file as before."""
    if routed(path) is None:
        return False
    try:
        _BOUND["storage"].append_events(_BOUND["account"], events)
    except Exception as error:
        raise OSError(str(error)) from error
    return True
