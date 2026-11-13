# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The SQLite backend (standard library only).

One database file. With the default model (A) each account has its own file, accounts/<id>/storage.sqlite3, opened by the one process that watches that account; with a `path` in the
configuration several accounts and processes share one file (model B). The schema carries `account_id` in every table, so both work with the same code.

  accounts, configs, sentinel_states, docs, events, analytics_snapshots     per account
  users, user_accounts, sessions                                            global (key -> JSON, with an optional expiry)
  meta                                                                      schema_version

How it stays sound:

  * WAL journal, synchronous=NORMAL, busy_timeout (30 s by default, `storage.busy_timeout_ms`) and a bounded retry with growing pauses for the steps SQLite does not make wait: readers never block the writer and the writer never blocks readers; a process killed at any point leaves a database
    that the next open recovers by itself (every commit is atomic).
  * Every write is ONE short transaction (BEGIN IMMEDIATE ... COMMIT): the batch of events, the replacement of a document, the purge. A failed one is rolled back whole.
  * Schema migrations are versioned (`schema_version` in `meta`) and each runs inside the same transaction as the bump of the version: a migration that is interrupted leaves the
    database exactly as it was and the next open runs it again. A database written by a NEWER version of the monitor is refused, never downgraded.
  * One connection per thread (a connection is never shared by two threads at the same time).
"""
import json
import os
import random
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from github_actions_monitor.storage import archive, base

SCHEMA_VERSION = 1
BUSY_MS = 30000      # how long a statement waits for another writer before it gives up (SQLite's own busy handler)
RETRIES = 8          # and how many times the steps that SQLite does not make wait (switching to WAL, taking the writer lock) are tried again, with a growing pause
#: version -> the statements that bring a database from version-1 to version
MIGRATIONS = {
    1: [
        "CREATE TABLE accounts (id TEXT PRIMARY KEY, created REAL NOT NULL)",
        "CREATE TABLE configs (account_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)",
        "CREATE TABLE sentinel_states (account_id TEXT NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (account_id, name))",
        "CREATE TABLE docs (account_id TEXT NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (account_id, name))",
        "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL, ts TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL)",
        "CREATE INDEX events_account_ts ON events (account_id, ts)",
        "CREATE TABLE analytics_snapshots (account_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)",
        "CREATE TABLE users (key TEXT PRIMARY KEY, data TEXT NOT NULL, expires REAL, updated REAL NOT NULL)",
        "CREATE TABLE user_accounts (key TEXT PRIMARY KEY, data TEXT NOT NULL, expires REAL, updated REAL NOT NULL)",
        "CREATE TABLE sessions (key TEXT PRIMARY KEY, data TEXT NOT NULL, expires REAL, updated REAL NOT NULL)",
        "CREATE INDEX sessions_expires ON sessions (expires)",
    ],
}


def _busy(error):
    text = str(error).lower()
    return "locked" in text or "busy" in text


def retrying(step, attempts=RETRIES):
    """Runs `step()`; when SQLite answers "database is locked / busy" (which its busy handler does not cover for some steps, such as the first switch to WAL on a database that another process
    is creating) it waits a growing, slightly random time and tries again, up to `attempts` times. Any other error, and the last busy one, is raised."""
    for attempt in range(attempts):
        try:
            return step()
        except sqlite3.OperationalError as error:
            if not _busy(error) or attempt == attempts - 1:
                raise
            time.sleep(min(2.0, 0.05 * (2 ** attempt)) * (0.5 + random.random()))


def _dumps(value):
    return json.dumps(value, ensure_ascii=False)


def _loads(text, kind=dict, default=None):
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return default
    return value if isinstance(value, kind) else default


class SqliteStorage(base.Storage):
    backend = "sqlite"

    def __init__(self, path, busy_ms=BUSY_MS, migrations=None, hook=None):
        """`migrations` and `hook` exist for the tests (a future schema; a function called inside the migration transaction after each statement)."""
        self.path = Path(path)
        self.busy_ms = int(busy_ms)
        self.migrations = migrations or MIGRATIONS
        self.target = max(self.migrations)
        self._hook = hook
        self._local = threading.local()
        self._all = []
        self._guard = threading.Lock()
        self._ready = False
        self.journal_mode = ""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn()      # opens, sets the pragmas and migrates now: a database that cannot be used says so here
        except BaseException:
            self.close()
            raise

    # -- connections
    def _conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn
        conn = sqlite3.connect(str(self.path), timeout=self.busy_ms / 1000.0, isolation_level=None, check_same_thread=False)
        conn.execute(f"PRAGMA busy_timeout = {self.busy_ms}")
        mode = retrying(lambda: conn.execute("PRAGMA journal_mode = WAL").fetchone())
        self.journal_mode = str(mode[0]).lower() if mode else ""
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        with self._guard:
            self._all.append(conn)
        if not self._ready:
            with self._guard:
                if not self._ready:
                    try:
                        self._migrate(conn)
                    except BaseException:
                        conn.close()
                        self._all.remove(conn)
                        raise
                    self._ready = True
        self._local.conn = conn
        return conn

    @contextmanager
    def _write(self):
        """One short write transaction (the lock of the writer is taken at once, so a busy database is waited for here, not half way)."""
        conn = self._conn()
        retrying(lambda: conn.execute("BEGIN IMMEDIATE"))
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")

    @contextmanager
    def _read(self):
        """A consistent view of several reads (a snapshot, in WAL mode)."""
        conn = self._conn()
        conn.execute("BEGIN")
        try:
            yield conn
        finally:
            conn.execute("COMMIT")

    # -- schema
    def schema_version(self):
        conn = self._conn()
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        except sqlite3.OperationalError:
            return 0
        return int(row[0]) if row else 0

    def _migrate(self, conn):
        retrying(lambda: conn.execute("BEGIN IMMEDIATE"))
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
            current = int(row[0]) if row else 0
            if current > self.target:
                raise base.StorageError(f"the database has schema {current}, newer than this version of the monitor ({self.target}): update the monitor")
            for version in range(current + 1, self.target + 1):
                for statement in self.migrations[version]:
                    conn.execute(statement)
                    if self._hook:
                        self._hook(version, statement)
                conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)", (str(version),))
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")

    def describe(self):
        return {"backend": self.backend, "path": str(self.path), "schema_version": self.schema_version(), "journal_mode": self.journal_mode, "busy_timeout_ms": self.busy_ms}

    def close(self):
        with self._guard:
            conns, self._all = self._all, []
        for conn in conns:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        self._local = threading.local()
        self._ready = False

    # -- helpers
    @staticmethod
    def _touch(conn, account_id):
        conn.execute("INSERT OR IGNORE INTO accounts (id, created) VALUES (?, ?)", (account_id, time.time()))

    # -- configuration, sentinels, documents, analytics
    def load_config(self, account_id):
        row = self._conn().execute("SELECT data FROM configs WHERE account_id = ?", (base.check_account(account_id),)).fetchone()
        return _loads(row[0], dict, {}) if row else {}

    def save_config(self, account_id, data):
        base.check_account(account_id)
        with self._write() as conn:
            self._touch(conn, account_id)
            conn.execute("INSERT OR REPLACE INTO configs (account_id, data, updated) VALUES (?, ?, ?)", (account_id, _dumps(data), time.time()))

    def load_sentinel_state(self, account_id, sentinel):
        row = self._conn().execute("SELECT data FROM sentinel_states WHERE account_id = ? AND name = ?", (base.check_account(account_id), base.check_name(sentinel))).fetchone()
        return _loads(row[0], dict, {}) if row else {}

    def save_sentinel_state(self, account_id, sentinel, data):
        base.check_account(account_id)
        base.check_name(sentinel)
        with self._write() as conn:
            self._touch(conn, account_id)
            conn.execute("INSERT OR REPLACE INTO sentinel_states (account_id, name, data, updated) VALUES (?, ?, ?, ?)", (account_id, sentinel, _dumps(data), time.time()))

    def load_doc(self, account_id, name, default=None):
        row = self._conn().execute("SELECT data FROM docs WHERE account_id = ? AND name = ?", (base.check_account(account_id), base.check_name(name))).fetchone()
        return _loads(row[0], dict, default) if row else default

    def save_doc(self, account_id, name, data):
        base.check_account(account_id)
        base.check_name(name)
        with self._write() as conn:
            self._touch(conn, account_id)
            conn.execute("INSERT OR REPLACE INTO docs (account_id, name, data, updated) VALUES (?, ?, ?, ?)", (account_id, name, _dumps(data), time.time()))

    def load_analytics(self, account_id):
        row = self._conn().execute("SELECT data FROM analytics_snapshots WHERE account_id = ?", (base.check_account(account_id),)).fetchone()
        return _loads(row[0], dict, {}) if row else {}

    def save_analytics(self, account_id, data):
        base.check_account(account_id)
        with self._write() as conn:
            self._touch(conn, account_id)
            conn.execute("INSERT OR REPLACE INTO analytics_snapshots (account_id, data, updated) VALUES (?, ?, ?)", (account_id, _dumps(data), time.time()))

    # -- events
    def append_events(self, account_id, events):
        base.check_account(account_id)
        rows = base.stamp_events(events)
        if not rows:
            return
        with self._write() as conn:
            self._touch(conn, account_id)
            conn.executemany("INSERT INTO events (account_id, ts, kind, data) VALUES (?, ?, ?, ?)",
                             [(account_id, e["at"], str(e.get("kind") or ""), _dumps(e)) for e in rows])

    def load_events(self, account_id, since=None, limit=100):
        base.check_account(account_id)
        if limit is not None and limit <= 0:
            return []
        sql, args = "SELECT data FROM events WHERE account_id = ?", [account_id]
        if since:
            sql, args = sql + " AND ts >= ?", args + [since]
        if limit is None:
            rows = self._conn().execute(sql + " ORDER BY ts ASC, id ASC", args).fetchall()
        else:
            rows = self._conn().execute(sql + " ORDER BY ts DESC, id DESC LIMIT ?", args + [int(limit)]).fetchall()[::-1]
        return [e for e in (_loads(r[0], dict) for r in rows) if e is not None]

    def event_stats(self, account_id):
        row = self._conn().execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(data)), 0), MIN(NULLIF(ts, '')), MAX(NULLIF(ts, '')) FROM events WHERE account_id = ?", (base.check_account(account_id),)).fetchone()
        return {"count": row[0], "bytes": row[1], "oldest": row[2] or "", "newest": row[3] or "", "damaged": 0}

    def purge_events(self, account_id, before, archive_dir=None):
        base.check_account(account_id)
        with self._write() as conn:      # the read and the delete are one transaction: an event appended meanwhile is neither archived nor lost
            rows = conn.execute("SELECT id, data FROM events WHERE account_id = ? AND ts != '' AND ts < ? ORDER BY ts, id", (account_id, before)).fetchall()
            kept = conn.execute("SELECT COUNT(*) FROM events WHERE account_id = ?", (account_id,)).fetchone()[0] - len(rows)
            if not rows:
                return {"removed": 0, "kept": kept, "archived": ""}
            archived = str(archive.write_archive(archive_dir, "events", [r[1] for r in rows])) if archive_dir else ""      # complete on the disk BEFORE the rows go (a failure rolls back)
            conn.executemany("DELETE FROM events WHERE id = ?", [(r[0],) for r in rows])
            return {"removed": len(rows), "kept": kept, "archived": archived}

    def purge_analytics(self, account_id, before_day):
        base.check_account(account_id)
        with self._write() as conn:
            row = conn.execute("SELECT data FROM analytics_snapshots WHERE account_id = ?", (account_id,)).fetchone()
            data = _loads(row[0], dict, None) if row else None
            if not data or not isinstance(data.get("daily"), dict):
                return {"removed": 0}
            old = [d for d in data["daily"] if isinstance(d, str) and d < before_day]
            for day in old:
                del data["daily"][day]
            if old:
                conn.execute("UPDATE analytics_snapshots SET data = ?, updated = ? WHERE account_id = ?", (_dumps(data), time.time(), account_id))
            return {"removed": len(old)}

    def archive_dir(self, account_id):
        return self.path.parent / "archive" / base.check_account(account_id)

    # -- global records
    @staticmethod
    def _table(kind):
        return base.check_kind(kind)      # one of three fixed names: safe to put in the statement

    def put_record(self, kind, key, data, expires=None):
        table = self._table(kind)
        base.check_key(key)
        if not isinstance(data, dict):
            raise base.StorageError("record data")
        with self._write() as conn:
            conn.execute(f"INSERT OR REPLACE INTO {table} (key, data, expires, updated) VALUES (?, ?, ?, ?)", (key, _dumps(data), expires, time.time()))

    def get_record(self, kind, key):
        row = self._conn().execute(f"SELECT data FROM {self._table(kind)} WHERE key = ?", (base.check_key(key),)).fetchone()
        return _loads(row[0], dict) if row else None

    def delete_record(self, kind, key):
        table = self._table(kind)
        with self._write() as conn:
            return conn.execute(f"DELETE FROM {table} WHERE key = ?", (base.check_key(key),)).rowcount > 0

    def list_records(self, kind):
        rows = self._conn().execute(f"SELECT key, data FROM {self._table(kind)} ORDER BY key").fetchall()
        return {k: v for k, v in ((r[0], _loads(r[1], dict)) for r in rows) if v is not None}

    def purge_records(self, kind, expired_before):
        table = self._table(kind)
        with self._write() as conn:
            return conn.execute(f"DELETE FROM {table} WHERE expires IS NOT NULL AND expires < ?", (expired_before,)).rowcount

    def export_records(self):
        out = {}
        with self._read() as conn:
            for kind in base.RECORD_KINDS:
                out[kind] = {r[0]: {"data": _loads(r[1], dict, {}), "expires": r[2]} for r in conn.execute(f"SELECT key, data, expires FROM {kind} ORDER BY key")}
        return out

    def import_records(self, records):
        with self._write() as conn:
            for kind in base.RECORD_KINDS:
                for key, row in ((records or {}).get(kind) or {}).items():
                    conn.execute(f"INSERT OR REPLACE INTO {kind} (key, data, expires, updated) VALUES (?, ?, ?, ?)", (base.check_key(key), _dumps(row["data"]), row.get("expires"), time.time()))

    # -- accounts, export, import, verification
    def list_accounts(self):
        return [r[0] for r in self._conn().execute("SELECT id FROM accounts ORDER BY id")]

    def export_account(self, account_id):
        base.check_account(account_id)
        with self._read() as conn:
            config = conn.execute("SELECT data FROM configs WHERE account_id = ?", (account_id,)).fetchone()
            analytics = conn.execute("SELECT data FROM analytics_snapshots WHERE account_id = ?", (account_id,)).fetchone()
            sentinels = {r[0]: _loads(r[1], dict, {}) for r in conn.execute("SELECT name, data FROM sentinel_states WHERE account_id = ? ORDER BY name", (account_id,))}
            docs = {r[0]: _loads(r[1], dict, {}) for r in conn.execute("SELECT name, data FROM docs WHERE account_id = ? ORDER BY name", (account_id,))}
            events = [_loads(r[0], dict) for r in conn.execute("SELECT data FROM events WHERE account_id = ? ORDER BY ts, id", (account_id,))]
        return {"config": _loads(config[0], dict, {}) if config else {}, "sentinels": sentinels, "docs": docs, "events": [e for e in events if e is not None],
                "analytics": _loads(analytics[0], dict, {}) if analytics else {}}

    def import_account(self, account_id, payload):
        base.check_account(account_id)
        for name in list((payload.get("sentinels") or {})) + list((payload.get("docs") or {})):
            base.check_name(name)
        now = time.time()
        with self._write() as conn:      # the whole account or nothing: an interrupted import leaves what was there
            self._touch(conn, account_id)
            if payload.get("config"):
                conn.execute("INSERT OR REPLACE INTO configs (account_id, data, updated) VALUES (?, ?, ?)", (account_id, _dumps(payload["config"]), now))
            for name, data in (payload.get("sentinels") or {}).items():
                conn.execute("INSERT OR REPLACE INTO sentinel_states (account_id, name, data, updated) VALUES (?, ?, ?, ?)", (account_id, name, _dumps(data), now))
            for name, data in (payload.get("docs") or {}).items():
                conn.execute("INSERT OR REPLACE INTO docs (account_id, name, data, updated) VALUES (?, ?, ?, ?)", (account_id, name, _dumps(data), now))
            if payload.get("analytics"):
                conn.execute("INSERT OR REPLACE INTO analytics_snapshots (account_id, data, updated) VALUES (?, ?, ?)", (account_id, _dumps(payload["analytics"]), now))
            conn.execute("DELETE FROM events WHERE account_id = ?", (account_id,))
            conn.executemany("INSERT INTO events (account_id, ts, kind, data) VALUES (?, ?, ?, ?)",
                             [(account_id, base.event_ts(e), str(e.get("kind") or ""), _dumps(e)) for e in payload.get("events") or [] if isinstance(e, dict)])

    def verify(self):
        problems = []
        conn = self._conn()
        result = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
        if result != ["ok"]:
            problems.append("integrity check: " + "; ".join(result[:3]))
        if self.schema_version() != self.target:
            problems.append(f"schema version {self.schema_version()} (expected {self.target})")
        try:
            for table, column in (("configs", "data"), ("sentinel_states", "data"), ("docs", "data"), ("events", "data"), ("analytics_snapshots", "data")):
                bad = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE json_valid({column}) = 0").fetchone()[0]
                if bad:
                    problems.append(f"{table}: {bad} row(s) that are not JSON")
        except sqlite3.OperationalError:      # a build of SQLite without the JSON functions: the integrity check above is what can be done
            pass
        return problems

    def backup_file(self, dest):
        """A raw, consistent copy of the database (SQLite's own online backup, safe while other processes write) to the file `dest`, replaced atomically. Returns its size."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
        copy = sqlite3.connect(str(tmp))
        try:
            self._conn().backup(copy)
            copy.execute("PRAGMA journal_mode = DELETE")
        finally:
            copy.close()
        os.replace(tmp, dest)
        return dest.stat().st_size
