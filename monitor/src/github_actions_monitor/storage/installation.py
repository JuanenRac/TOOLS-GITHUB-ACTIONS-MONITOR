# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A whole installation seen as one storage, for the tools that work on every account at once (the migration and the backup).

At run time a process only ever opens ITS account (`factory.create_storage`). The tools need all of them, and with the SQLite backend in model A that means one database per account plus one
for the global records, so this class opens them as one set:

    inst = open_installation("sqlite", "path/to/accounts")                 # accounts/<id>/storage.sqlite3 for each account, accounts/_global/storage.sqlite3 for the records
    inst = open_installation("sqlite", "path/to/accounts", db="all.db")    # model B: one shared database
    inst = open_installation("file", "path/to/accounts")                   # the layout of accounts/<id>/
    inst = open_installation("file", "path/to/product", flat=True)         # one account, "default", with its files next to the launchers

It offers what `backup` and `migrate` need (list_accounts, export_account, import_account, export_records, import_records, verify, close) and nothing more.
"""
from pathlib import Path

from github_actions_monitor.storage import base
from github_actions_monitor.storage.file_storage import FLAT_ACCOUNT, FileStorage
from github_actions_monitor.storage.sqlite_storage import SqliteStorage

DB_NAME = "storage.sqlite3"
GLOBAL_FOLDER = "_global"


class Installation:
    def __init__(self, backend, root, db=None, flat=False):
        if backend not in ("file", "sqlite"):
            raise base.StorageError("backend")
        self.backend, self.root, self.db, self.flat = backend, Path(root), (Path(db) if db else None), bool(flat)
        self._open = {}
        self._files = FileStorage(self.root, "flat" if self.flat else "accounts") if backend == "file" else None

    # -- the storage of one account, and of the global records
    def account_storage(self, account_id):
        base.check_account(account_id)
        if self._files is not None:
            return self._files
        path = self.db or (self.root / DB_NAME if self.flat else self.root / account_id / DB_NAME)
        if str(path) not in self._open:
            self._open[str(path)] = SqliteStorage(path)
        return self._open[str(path)]

    def global_storage(self):
        if self._files is not None:
            return self._files
        path = self.db or (self.root / DB_NAME if self.flat else self.root / GLOBAL_FOLDER / DB_NAME)
        if str(path) not in self._open:
            self._open[str(path)] = SqliteStorage(path)
        return self._open[str(path)]

    # -- what the tools use
    def list_accounts(self):
        if self._files is not None:
            return self._files.list_accounts()
        if self.db:
            return self.account_storage(FLAT_ACCOUNT).list_accounts() if self.db.is_file() else []
        if self.flat:
            return [FLAT_ACCOUNT] if (self.root / DB_NAME).is_file() else []
        try:
            candidates = sorted(p.name for p in self.root.iterdir() if p.is_dir() and base.ACCOUNT_RE.match(p.name) and (p / DB_NAME).is_file())
        except OSError:
            return []
        return [name for name in candidates if name in self.account_storage(name).list_accounts()]      # a database that holds no account (a copy that never got going) is not an account

    def export_account(self, account_id):
        return self.account_storage(account_id).export_account(account_id)

    def import_account(self, account_id, payload):
        self.account_storage(account_id).import_account(account_id, payload)

    def export_records(self):
        if self._files is None and not self.db and not self.flat and not (self.root / GLOBAL_FOLDER / DB_NAME).is_file():
            return {kind: {} for kind in base.RECORD_KINDS}      # a read must not create the database of the records
        return self.global_storage().export_records()

    def import_records(self, records):
        if any((records or {}).get(kind) for kind in base.RECORD_KINDS):
            self.global_storage().import_records(records)

    def verify(self):
        problems = []
        stores = {id(self.account_storage(a)): self.account_storage(a) for a in self.list_accounts()}
        for store in stores.values():
            problems += store.verify()
        return problems

    def event_stats(self, account_id):
        return self.account_storage(account_id).event_stats(account_id)

    def describe(self):
        return {"backend": self.backend, "root": str(self.root), "db": str(self.db) if self.db else "", "flat": self.flat}

    def close(self):
        for store in self._open.values():
            store.close()
        self._open = {}


def open_installation(backend, root, db=None, flat=False):
    return Installation(backend, root, db, flat)
