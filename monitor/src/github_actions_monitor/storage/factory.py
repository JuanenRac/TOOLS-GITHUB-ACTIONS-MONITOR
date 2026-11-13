# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""create_storage: the one place that decides which backend a process uses.

    storage = create_storage(config.get("storage"), account_id="personal")      # {"backend": "file", "path": "..."}

  backend  "file" (the default, and the only one the lite edition has) keeps the layout of accounts/<id>/ as it has always been; `path` is the folder of the accounts.
  lite     True = the lite edition: the backend is "file" whatever the configuration says, and nothing but the files is read, shown or created.
"""
from pathlib import Path

from github_actions_monitor.accounts import accounts
from github_actions_monitor.storage import base
from github_actions_monitor.storage.file_storage import FileStorage

BACKENDS = ("file",)
DEFAULT_BACKEND = "file"


def settings(block):
    """{"backend", "path"} from the `storage` block of a configuration (anything wrong reads as the default: the file backend)."""
    block = block if isinstance(block, dict) else {}
    backend = block.get("backend") if block.get("backend") in BACKENDS else DEFAULT_BACKEND
    path = block.get("path") if isinstance(block.get("path"), str) else ""
    return {"backend": backend, "path": path.strip()}


def create_storage(block=None, account_id=None, lite=False, base_dir=None):
    """The storage for a process. `block` is `config["storage"]` (None = the default). Without an accounts/ folder (and for the account "default") it is the flat installation, the files next
    to the launchers; with accounts/ the layout of accounts/<id>/. `base_dir` is the product folder (tests pass a temporary one)."""
    cfg = settings(None if lite else block)
    if cfg["backend"] != "file":
        raise base.StorageError("backend")
    if cfg["path"]:
        return FileStorage(Path(cfg["path"]), "accounts")
    if accounts.layout(base_dir) == "accounts" or account_id not in (None, accounts.DEFAULT_ID):
        return FileStorage(accounts.root_dir(base_dir), "accounts")
    from github_actions_monitor.util.paths import ROOT
    return FileStorage(Path(base_dir) if base_dir else ROOT, "flat")
