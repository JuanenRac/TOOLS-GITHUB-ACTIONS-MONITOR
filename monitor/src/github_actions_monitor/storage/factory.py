# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""create_storage: the one place that decides which backend a process uses.

    storage = create_storage(config.get("storage"), account_id="personal")      # {"backend": "file" | "sqlite", "path": "..."}

  backend  "file" (the default, and the only one the lite edition has) keeps the layout of accounts/<id>/ as it has always been; `path` is the folder of the accounts.
           "sqlite" keeps the same data in a database: by default ONE FILE PER ACCOUNT (accounts/<id>/storage.sqlite3, model A: the process of an account is the only one that writes it);
           a `path` names ONE shared file for the whole installation (model B, kept ready: WAL and a busy timeout make several processes safe, see docs/STORAGE.md).
  lite     True = the lite edition: the backend is "file" whatever the configuration says, and nothing about SQLite is read, shown or created.
"""
from pathlib import Path

from github_actions_monitor.accounts import accounts
from github_actions_monitor.storage import base
from github_actions_monitor.storage.file_storage import FileStorage

BACKENDS = ("file", "sqlite")
DB_NAME = "storage.sqlite3"
DEFAULT_BACKEND = "file"
DEFAULT_BUSY_MS = 30000      # `storage.busy_timeout_ms`: how long SQLite waits for another writer (1000-600000)


def settings(block):
    """{"backend", "path"} from the `storage` block of a configuration (anything wrong reads as the default: the file backend)."""
    block = block if isinstance(block, dict) else {}
    backend = block.get("backend") if block.get("backend") in BACKENDS else DEFAULT_BACKEND
    path = block.get("path") if isinstance(block.get("path"), str) else ""
    wait = block.get("busy_timeout_ms")
    wait = wait if isinstance(wait, int) and not isinstance(wait, bool) and 1000 <= wait <= 600000 else DEFAULT_BUSY_MS
    return {"backend": backend, "path": path.strip(), "busy_timeout_ms": wait}


def create_storage(block=None, account_id=None, lite=False, base_dir=None):
    """The storage for a process. `block` is `config["storage"]` (None = the default). Without an accounts/ folder (and for the account "default") it is the flat installation, the files next
    to the launchers; with accounts/ the layout of accounts/<id>/. `base_dir` is the product folder (tests pass a temporary one)."""
    cfg = settings(None if lite else block)
    if cfg["backend"] == "sqlite":
        from github_actions_monitor.storage.sqlite_storage import SqliteStorage
        if cfg["path"]:
            return SqliteStorage(cfg["path"], cfg["busy_timeout_ms"])
        if accounts.layout(base_dir) == "accounts" or account_id not in (None, accounts.DEFAULT_ID):
            return SqliteStorage(accounts.account_dir(account_id or accounts.DEFAULT_ID, base_dir) / DB_NAME, cfg["busy_timeout_ms"])
        from github_actions_monitor.util import paths
        return SqliteStorage(paths.place(DB_NAME, base_dir), cfg["busy_timeout_ms"])
    if cfg["backend"] != "file":
        raise base.StorageError("backend")
    if cfg["path"]:
        return FileStorage(Path(cfg["path"]), "accounts")
    if accounts.layout(base_dir) == "accounts" or account_id not in (None, accounts.DEFAULT_ID):
        return FileStorage(accounts.root_dir(base_dir), "accounts")
    from github_actions_monitor.util.paths import ROOT
    return FileStorage(Path(base_dir) if base_dir else ROOT, "flat")      # the product folder: config/, data/, logs/ ... are resolved inside it


def create_global_storage(block=None, lite=False, base_dir=None):
    """The storage of the GLOBAL records (users, the accounts they may see, sessions): the supervisor of the accounts owns it, not an account process. With the file backend it is
    <accounts>/_global/*.json; with SQLite one database, accounts/_global/storage.sqlite3, or the shared file when `storage.path` names one."""
    cfg = settings(None if lite else block)
    if cfg["backend"] == "sqlite":
        from github_actions_monitor.storage.sqlite_storage import SqliteStorage
        return SqliteStorage(cfg["path"] or accounts.root_dir(base_dir) / "_global" / DB_NAME, cfg["busy_timeout_ms"])
    return FileStorage(Path(cfg["path"]) if cfg["path"] else accounts.root_dir(base_dir), "accounts")
