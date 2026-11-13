# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The file backend: the layout of accounts/<id>/ exactly as the monitor has always written it.

    <root>/<id>/actions_monitor.json                  the configuration
    <root>/<id>/sentinel_state/<name>.json            the state of the sentinels (sentinel_cache, sentinel_history, sentinel_ai_cache, collab_state ...)
    <root>/<id>/events/events_monitor.jsonl           the feed, one JSON object per line
    <root>/<id>/events/events_state.json              what the feed already announced
    <root>/<id>/analytics/analytics_history.json      the samples of the analytics
    <root>/<id>/alert_mutes.json, update_check.json ...   the small documents
    <root>/_global/<kind>.json                        the global records (users, user_accounts, sessions)

`layout="flat"` is the installation without an accounts/ folder (one account, "default", with its files next to the launchers): the same items under the old names
(`events_monitor.jsonl`, `sentinel_cache.json`, ...), so a person who never moved to accounts/ keeps every file where it is. Lite and the individual mode of Complete use this backend.

Every write goes to a temporary file with a name of its own, is flushed to the disk and replaces the target with os.replace; the feed is appended with one write per line.
"""
import json
import os
import shutil
import time
from pathlib import Path

from github_actions_monitor.accounts import accounts as accounts_module
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import archive, base, locks

EVENTS_REL = "events/events_monitor.jsonl"
ANALYTICS_REL = "analytics/analytics_history.json"
CONFIG_REL = "actions_monitor.json"
SENTINEL_DIR = "sentinel_state"
#: documents with a home of their own in the layout of 1.7; any other name goes to state/<name>.json
DOC_PATHS = {"events_state": "events/events_state.json", "alert_mutes": "alert_mutes.json", "update_check": "update_check.json", "welcome_state": "welcome_state.json",
             "orgs_state": "orgs_state.json", "degraded": "degraded.json"}
#: the sentinel states that exist in the flat installation
FLAT_SENTINELS = ("sentinel_cache", "sentinel_history", "sentinel_ai_cache", "collab_state")
FLAT_ACCOUNT = "default"
GLOBAL_DIR = "_global"      # not a valid account id (it starts with an underscore), so it can never be the folder of an account
_FLAT_NAMES = {new: old for old, new in accounts_module.LEGACY}
_RETRIES = 6


def _unique_tmp(path):
    return archive.unique_tmp(path)


def atomic_write(path, text):
    """Replaces `path` with `text`: temporary file next to it (own name per process and thread), flushed to the disk, then os.replace; mode 0600. Retries a few times where the
    system holds the target for a moment (Windows)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _unique_tmp(path)
    data = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), private_io.FILE_MODE)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(_RETRIES):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == _RETRIES - 1:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    private_io._fix_mode(path, private_io.FILE_MODE)


def read_json(path, kind=dict, default=None):
    """The JSON of a file when it is a `kind` (dict / list), else `default` (a missing, empty, damaged or wrong-shaped file reads as nothing)."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return value if isinstance(value, kind) else default


def parse_lines(text):
    """(events, bad): the lines of a feed that are JSON objects, and how many were not."""
    out, bad = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(value, dict):
            out.append(value)
        else:
            bad += 1
    return out, bad


class FileStorage(base.Storage):
    backend = "file"

    def __init__(self, root, layout="accounts"):
        if layout not in ("accounts", "flat"):
            raise base.StorageError("layout")
        self.root, self.layout = Path(root), layout

    def describe(self):
        return {"backend": self.backend, "layout": self.layout, "path": str(self.root)}

    # -- where things are
    def _account_dir(self, account_id):
        base.check_account(account_id)
        return self.root if self.layout == "flat" else self.root / account_id

    def _path(self, account_id, rel):
        """The file for `rel` (a name of the layout of accounts/<id>/); in the flat installation the old name of that file next to the launchers."""
        folder = self._account_dir(account_id)
        return folder / (_FLAT_NAMES.get(rel, rel) if self.layout == "flat" else rel)

    def _doc_rel(self, name):
        base.check_name(name)
        return DOC_PATHS.get(name, f"state/{name}.json")

    def _sentinel_rel(self, sentinel):
        return f"{SENTINEL_DIR}/{base.check_name(sentinel)}.json"

    def events_path(self, account_id):
        return self._path(account_id, EVENTS_REL)

    def archive_dir(self, account_id):
        """Where the purge in mode "archive" puts the old events: events/archive/ of the account, outside the hot file."""
        return self.events_path(account_id).parent / "archive"

    def lock(self, account_id):
        """The lock the feed of this account is written under (the monitor's own feed takes the same one)."""
        return locks.path_lock(self.events_path(account_id))

    # -- configuration, sentinels, documents, analytics
    def load_config(self, account_id):
        return read_json(self._path(account_id, CONFIG_REL), dict, {})

    def save_config(self, account_id, data):
        atomic_write(self._path(account_id, CONFIG_REL), json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def load_sentinel_state(self, account_id, sentinel):
        return read_json(self._path(account_id, self._sentinel_rel(sentinel)), dict, {})

    def save_sentinel_state(self, account_id, sentinel, data):
        atomic_write(self._path(account_id, self._sentinel_rel(sentinel)), json.dumps(data, ensure_ascii=False))

    def load_doc(self, account_id, name, default=None):
        return read_json(self._path(account_id, self._doc_rel(name)), dict, default)

    def save_doc(self, account_id, name, data):
        atomic_write(self._path(account_id, self._doc_rel(name)), json.dumps(data, ensure_ascii=False))

    def load_analytics(self, account_id):
        return read_json(self._path(account_id, ANALYTICS_REL), dict, {})

    def save_analytics(self, account_id, data):
        atomic_write(self._path(account_id, ANALYTICS_REL), json.dumps(data))

    # -- events
    def append_events(self, account_id, events):
        events = base.stamp_events(events)
        if not events:
            return
        path = self.events_path(account_id)
        lines = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events)
        path.parent.mkdir(parents=True, exist_ok=True)
        with locks.path_lock(path):
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0), private_io.FILE_MODE)
            try:
                os.write(fd, lines.encode("utf-8"))      # one write for the whole batch: a line is never cut in two by another writer
                os.fsync(fd)
            finally:
                os.close(fd)

    def _read_events(self, account_id):
        try:
            text = self.events_path(account_id).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [], 0
        return parse_lines(text)

    def load_events(self, account_id, since=None, limit=100):
        events, _bad = self._read_events(account_id)
        if since:
            events = [e for e in events if base.event_ts(e) >= since]
        events.sort(key=base.event_ts)      # stable: the order of writing is kept inside one second
        if limit is not None:
            events = events[-limit:] if limit > 0 else []
        return events

    def event_stats(self, account_id):
        path = self.events_path(account_id)
        events, bad = self._read_events(account_id)
        stamps = [base.event_ts(e) for e in events if base.event_ts(e)]
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        return {"count": len(events), "bytes": size, "oldest": min(stamps) if stamps else "", "newest": max(stamps) if stamps else "", "damaged": bad}

    def purge_events(self, account_id, before, archive_dir=None):
        path = self.events_path(account_id)
        with locks.path_lock(path):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return {"removed": 0, "kept": 0, "archived": ""}
            keep, gone = [], []
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except ValueError:
                    keep.append(line)      # a damaged line is not ours to delete
                    continue
                stamp = base.event_ts(value)
                (gone if stamp and stamp < before else keep).append(line)
            if not gone:
                return {"removed": 0, "kept": len(keep), "archived": ""}
            archived = ""
            if archive_dir:      # the archive is complete on the disk BEFORE the hot file loses a line
                archived = str(archive.write_archive(archive_dir, "events", gone))
            atomic_write(path, "".join(line + "\n" for line in keep))
            return {"removed": len(gone), "kept": len(keep), "archived": archived}

    def purge_analytics(self, account_id, before_day):
        path = self._path(account_id, ANALYTICS_REL)
        with locks.path_lock(path):
            data = read_json(path, dict, None)
            if not data or not isinstance(data.get("daily"), dict):
                return {"removed": 0}
            old = [d for d in data["daily"] if isinstance(d, str) and d < before_day]
            for day in old:
                del data["daily"][day]
            if old:
                atomic_write(path, json.dumps(data))
            return {"removed": len(old)}

    # -- global records
    def _records_path(self, kind):
        return self.root / GLOBAL_DIR / f"{base.check_kind(kind)}.json"

    def _read_records(self, kind):
        data = read_json(self._records_path(kind), dict, {})
        rows = data.get("records")
        return rows if isinstance(rows, dict) else {}

    def _write_records(self, kind, rows):
        atomic_write(self._records_path(kind), json.dumps({"records": rows}, ensure_ascii=False))

    def put_record(self, kind, key, data, expires=None):
        base.check_key(key)
        if not isinstance(data, dict):
            raise base.StorageError("record data")
        with locks.process_lock(self._records_path(kind)):
            rows = self._read_records(kind)
            rows[key] = {"data": data, "expires": expires}
            self._write_records(kind, rows)

    def get_record(self, kind, key):
        row = self._read_records(kind).get(base.check_key(key))
        return row.get("data") if isinstance(row, dict) else None

    def delete_record(self, kind, key):
        with locks.process_lock(self._records_path(kind)):
            rows = self._read_records(kind)
            if base.check_key(key) not in rows:
                return False
            del rows[key]
            self._write_records(kind, rows)
            return True

    def list_records(self, kind):
        return {k: v.get("data") for k, v in self._read_records(kind).items() if isinstance(v, dict) and isinstance(v.get("data"), dict)}

    def purge_records(self, kind, expired_before):
        with locks.process_lock(self._records_path(kind)):
            rows = self._read_records(kind)
            old = [k for k, v in rows.items() if isinstance(v, dict) and isinstance(v.get("expires"), (int, float)) and v["expires"] < expired_before]
            for key in old:
                del rows[key]
            if old:
                self._write_records(kind, rows)
            return len(old)

    def export_records(self):
        return {kind: {k: {"data": v.get("data"), "expires": v.get("expires")} for k, v in self._read_records(kind).items() if isinstance(v, dict) and isinstance(v.get("data"), dict)}
                for kind in base.RECORD_KINDS}

    def import_records(self, records):
        for kind in base.RECORD_KINDS:
            incoming = (records or {}).get(kind) or {}
            if not incoming:
                continue
            with locks.process_lock(self._records_path(kind)):
                rows = self._read_records(kind)
                for key, row in incoming.items():
                    rows[base.check_key(key)] = {"data": row["data"], "expires": row.get("expires")}
                self._write_records(kind, rows)

    # -- accounts, export, import, verification
    def list_accounts(self):
        if self.layout == "flat":
            return [FLAT_ACCOUNT] if (self.root / CONFIG_REL).is_file() else []
        try:
            return sorted(p.name for p in self.root.iterdir() if p.is_dir() and base.ACCOUNT_RE.match(p.name) and (p / CONFIG_REL).is_file())
        except OSError:
            return []

    def _sentinel_names(self, account_id):
        if self.layout == "flat":
            return [n for n in FLAT_SENTINELS if self._path(account_id, self._sentinel_rel(n)).is_file()]
        folder = self._account_dir(account_id) / SENTINEL_DIR
        try:
            return sorted(p.stem for p in folder.glob("*.json") if base.NAME_RE.match(p.stem))
        except OSError:
            return []

    def _doc_names(self, account_id):
        names = [n for n in DOC_PATHS if self._path(account_id, DOC_PATHS[n]).is_file()]
        if self.layout != "flat":
            try:
                names += sorted(p.stem for p in (self._account_dir(account_id) / "state").glob("*.json") if base.NAME_RE.match(p.stem))
            except OSError:
                pass
        return names

    def export_account(self, account_id):
        events, _bad = self._read_events(account_id)
        return {"config": self.load_config(account_id),
                "sentinels": {n: self.load_sentinel_state(account_id, n) for n in self._sentinel_names(account_id)},
                "docs": {n: self.load_doc(account_id, n, {}) for n in self._doc_names(account_id)},
                "events": events, "analytics": self.load_analytics(account_id)}

    def import_account(self, account_id, payload):
        if payload.get("config"):
            self.save_config(account_id, payload["config"])
        for name, data in (payload.get("sentinels") or {}).items():
            self.save_sentinel_state(account_id, name, data)
        for name, data in (payload.get("docs") or {}).items():
            self.save_doc(account_id, name, data)
        if payload.get("analytics"):
            self.save_analytics(account_id, payload["analytics"])
        events = [e for e in payload.get("events") or [] if isinstance(e, dict)]
        path = self.events_path(account_id)
        with locks.path_lock(path):
            if events or path.exists():
                atomic_write(path, "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events))

    def verify(self):
        problems = []
        for account_id in self.list_accounts():
            _events, bad = self._read_events(account_id)
            if bad:
                problems.append(f"{account_id}: {bad} damaged line(s) in the feed")
            folder = self._account_dir(account_id)
            for rel in [CONFIG_REL, ANALYTICS_REL, *DOC_PATHS.values(), *(f"{SENTINEL_DIR}/{n}.json" for n in self._sentinel_names(account_id))]:
                path = self._path(account_id, rel)
                if path.is_file() and read_json(path, dict, None) is None:
                    problems.append(f"{account_id}: {path.relative_to(folder).as_posix()} is not a JSON object")
        return problems


def move_aside(path, suffix):
    """Renames a file or folder to <name>.<suffix> (numbered if taken) and returns the new path; used by the restore to keep what it replaces."""
    path = Path(path)
    target, n = path.with_name(path.name + "." + suffix), 1
    while target.exists():
        n += 1
        target = path.with_name(f"{path.name}.{suffix}{n}")
    shutil.move(str(path), str(target))
    return target
