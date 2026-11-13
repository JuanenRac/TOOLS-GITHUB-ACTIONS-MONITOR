# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What a monitor process does with the `storage` block of its configuration when it starts.

    storage = runtime.bind(config, account_id)        # None while the backend is "file"

With the file backend (the default; always in Lite) nothing is bound: the modules go on reading and writing their files exactly as before. With "sqlite" the storage of the process is created
(one database per account, or the shared one named by `storage.path`) and `state_io` is told to keep the state in it. The configuration itself stays a JSON file in both cases: it is what
says which backend to use, and the person edits it, so it cannot live inside the thing it configures.
"""
from github_actions_monitor.storage import factory, retention, state_io

_FILE_STORAGES = {}


def bind(config, account_id=None, base_dir=None, lite=False):
    """Creates and binds the storage the configuration asks for. Returns it, or None when the state stays in files. A database that cannot be opened raises StorageError / sqlite3.Error:
    the monitor must not start writing its state somewhere else behind the back of the person who asked for a database."""
    state_io.unbind()
    block = config.get("storage") if isinstance(config, dict) else None
    if not lite:
        from github_actions_monitor.data_pipeline import events
        events.MAX_BYTES = retention.settings(config)["events_max_kb"] * 1024      # the ceiling of the feed FILE (the default is the 512 KB it always had)
    if lite or factory.settings(block)["backend"] != "sqlite":
        return None
    storage = factory.create_storage(block, account_id, base_dir=base_dir)
    state_io.bind(storage, account_id or "default")
    return storage


def current():
    """(storage, account_id) of the bound storage, else (None, None)."""
    return state_io.bound()


def process_storage(account_id=None, base_dir=None):
    """(storage, account_id) that the maintenance of this process works on (the purge of the retention, the doctor): the bound database, or else the file storage of the layout in use
    (accounts/<id>/ for an account process, the files next to the launchers for a single installation)."""
    storage, account = state_io.bound()
    if storage is not None:
        return storage, account
    account = account_id or "default"
    key = (account, str(base_dir))
    if key not in _FILE_STORAGES:
        _FILE_STORAGES[key] = factory.create_storage(None, account, base_dir=base_dir)
    return _FILE_STORAGES[key], account
