# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The complete backup package (format 2) of an installation.

It is the package of `storage/backup.py` (the dump of every account and the global records) plus `files.json`, the settings and lists of the installation that are not in the dump, and a manifest that
lists every member with its size and its SHA-256 (and the version of the product, the schema and the edition). It is built from the storage with the atomic reads of the backend: nothing is ever
copied "raw" from a database that is being written.

What never travels: the sessions, the tokens and keys of GitHub or of an App, passwords, the value of any `*_env` variable, the secrets of the webhook and of the AI providers, and the content of the
secret store. The settings go through a WHITE LIST (the keys of `settings_api.SCHEMA`, the same ones the page may show), then through a scrub that drops any key that looks like a secret and any
value that looks like a token or a private key. Secrets are named only by the variable that holds them. A restore does not bring credentials back: its checklist says so.

The package can be sealed (AES-256-GCM, a key from an environment variable) when the optional library is installed; otherwise sealing is refused, never faked (see `ops/sealing.py`).
"""
import contextlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from github_actions_monitor.ops import opsconf, sealing
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import backup, base, installation
from github_actions_monitor.util import paths

FILES = "files.json"
FORMAT = 2
LISTS = ("targets.json", "ecosystems.json", "profiles.json")
GLOBAL_FILES = ("alert_mutes.json",)
OPTIONAL_FILES = ("proposals.json", "devices.json")      # stores of modules that may be absent: they travel when present and are skipped without error when not
NAME_RE = re.compile(r"^ghamon-backup-(\d{8}T\d{6}Z)\.zip(\.enc)?\Z")
SECRET_KEY = re.compile(r"secret|token|passw|pubkey|private|credential|api_?key|signing|(?:^|_)key$", re.I)
SECRET_VALUE = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}")
LIST_MAX = 4 * 1024 * 1024
_GONE = object()


class OpsError(Exception):
    """A stable `code` (the texts are the catalogs' `ops.err.<code>`) and an optional `detail` (never a secret)."""

    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code, self.detail = code, str(detail)[:300]


# --- cleaning ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def scrub(value, counter=None):
    """`value` without any key that looks like a secret (except `*_env`, which holds a NAME) and without any text that looks like a token or a private key. `counter` ([n]) counts what was dropped."""
    counter = counter if counter is not None else [0]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str) or (SECRET_KEY.search(key) and not key.endswith("_env")):
                counter[0] += 1
                continue
            cleaned = scrub(item, counter)
            if cleaned is _GONE:
                counter[0] += 1
                continue
            out[key] = cleaned
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            cleaned = scrub(item, counter)
            if cleaned is _GONE:
                counter[0] += 1
            else:
                out.append(cleaned)
        return out
    if isinstance(value, str) and SECRET_VALUE.search(value):
        return _GONE
    return value


def _leaves(tree, prefix=""):
    if isinstance(tree, dict) and tree:
        for key, item in tree.items():
            yield from _leaves(item, f"{prefix}{key}.")
    else:
        yield prefix[:-1]


def clean_config(config):
    """(the settings of the white list found in `config`, how many keys were left out). The white list is `settings_api.FIELDS`."""
    from github_actions_monitor.app import settings_api
    config = config if isinstance(config, dict) else {}
    kept, dropped = {}, [0]
    for key, row in settings_api.FIELDS.items():
        if row[2] == "status":
            continue
        value = settings_api._get(config, key, _GONE)
        if value is _GONE:
            continue
        cleaned = scrub(value, dropped)
        if cleaned is _GONE:
            dropped[0] += 1
            continue
        settings_api._set(kept, key, cleaned)
    known = tuple(settings_api.FIELDS)
    outside = sum(1 for leaf in _leaves(config) if leaf and not any(leaf == key or leaf.startswith(key + ".") for key in known))
    return kept, outside + dropped[0]


def _read_list(path):
    try:
        if path.stat().st_size > LIST_MAX:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, (dict, list)) else None


def collect_files(config, folder=None, include_config=True):
    """(files.json as a dict, how many keys of the configuration were left out): the cleaned global settings and the lists of the installation. {} when `include_config` is off."""
    if not include_config:
        return {"schema": 1, "included": False}, 0
    cleaned, omitted = clean_config(config)
    files = {"schema": 1, "included": True, "config": cleaned, "lists": {}, "files": {}}
    counter = [0]
    for name in LISTS:
        data = _read_list(paths.place(name, folder))
        if data is not None:
            files["lists"][name] = scrub(data, counter)
    for name in GLOBAL_FILES + OPTIONAL_FILES:
        data = _read_list(paths.place(name, folder))
        if data is not None:
            files["files"][name] = scrub(data, counter)
    return files, omitted + counter[0]


# --- opening the installation ---------------------------------------------------------------------------------------------------------------------------------------------

def open_installation(config=None, folder=None, backend=None, db=None):
    """The whole installation as one storage, as the configuration says (the backend and the layout: accounts/ or the single account next to the launchers)."""
    from github_actions_monitor.accounts import accounts
    from github_actions_monitor.storage import factory
    chosen = factory.settings((config or {}).get("storage") if isinstance(config, dict) else None)
    backend = backend or chosen["backend"]
    where = db or chosen["path"]
    if accounts.layout(folder) == "accounts":
        return installation.open_installation(backend, Path(where) if (where and backend == "file") else accounts.root_dir(folder), Path(where) if (where and backend == "sqlite") else None)
    return installation.open_installation(backend, Path(where) if (where and backend == "file") else (folder or paths.ROOT), Path(where) if (where and backend == "sqlite") else None, flat=True)


# --- packages -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def stamp(now=None):
    return datetime.fromtimestamp(now if now is not None else datetime.now(timezone.utc).timestamp(), timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_name(sealed, now=None):
    return f"ghamon-backup-{stamp(now)}.zip" + (".enc" if sealed else "")


def _filter(include_config):
    def payload_filter(_account_id, payload):
        payload = dict(payload)
        if include_config:
            payload["config"] = clean_config(payload.get("config"))[0]
        else:
            payload.pop("config", None)
        return payload
    return payload_filter


def create(inst, dest, config=None, folder=None, include_config=None, level=None, encrypt=None, key_env=None, env=None, now=None, into_dir=False, account=None, include_files=True):
    """Writes the package of `inst` to `dest` (a file; a folder, or `into_dir`, gets the default name) and returns {"path", "bytes", "sealed", "manifest"}; with `account` the package holds that account alone (no user, no settings of the installation); `include_files` False leaves files.json empty. The sealing is checked BEFORE any work: without the library or a
    good key it raises OpsError(library_missing / key_missing / key_weak) and writes nothing. The package is verified before it is put in place."""
    cfg = opsconf.settings(config)["backup"]
    include_config = cfg["include_config"] if include_config is None else bool(include_config)
    level = cfg["compress_level"] if level is None else level
    encrypt = cfg["encrypt"] if encrypt is None else bool(encrypt)
    key_env = key_env or cfg["key_env"]
    secret = None
    if encrypt:
        try:
            secret = sealing.check_ready(key_env, env)
        except sealing.SealError as error:
            raise OpsError(error.code, key_env if error.code != "library_missing" else "cryptography") from None
    dest = Path(dest)
    if into_dir or dest.is_dir() or str(dest).endswith(("/", "\\")):
        dest = dest / default_name(encrypt, now)
    elif encrypt and not dest.name.endswith(".enc"):
        dest = dest.with_name(dest.name + ".enc")
    if not include_files and account is None:
        files, omitted = {"schema": 1, "included": False}, 0      # the lists and the settings file of the installation are left out (a tool that works on a folder of accounts)
    elif account is not None:
        try:
            base.check_account(account)
        except base.StorageError:
            raise OpsError("no_account", account) from None
        if account not in inst.list_accounts():
            raise OpsError("no_account", account)
        files, omitted = {"schema": 1, "included": False, "scope": "account"}, 0      # the settings of the installation belong to the whole package; the account carries its own in the dump
    else:
        files, omitted = collect_files(config or {}, folder, include_config)
    from github_actions_monitor.storage import sqlite_storage
    from github_actions_monitor.tool_version import TOOL_VERSION
    info = {"product_version": TOOL_VERSION, "schema_version": sqlite_storage.SCHEMA_VERSION, "edition": "complete", "config_included": include_config, "config_omitted": omitted}
    plain = dest.with_name(dest.name + f".{os.getpid()}.plain") if encrypt else dest
    try:
        manifest = backup.write_package(inst, plain, fmt=FORMAT, payload_filter=_filter(include_config), extra_members={FILES: (json.dumps(files, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")},
                                        level=level, info=info, only_account=account)
        if encrypt:
            sealing.seal(plain, dest, secret)
            manifest["sealed"] = True
    except base.StorageError as error:
        raise OpsError("package", str(error)) from None
    except sealing.SealError as error:
        raise OpsError(error.code) from None
    finally:
        if encrypt:
            with contextlib.suppress(OSError):
                plain.unlink()
    private_io._fix_mode(dest, private_io.FILE_MODE)
    return {"path": str(dest), "bytes": dest.stat().st_size, "sealed": bool(encrypt), "manifest": manifest}


@contextlib.contextmanager
def open_package(path, key_env=None, env=None, config=None):
    """The path of the PLAIN package behind `path`: the file itself, or, for a sealed one, a temporary copy opened with the key of the variable `key_env` (removed afterwards). Raises OpsError."""
    path = Path(path)
    if not path.is_file():
        raise OpsError("not_found")
    if not sealing.is_sealed(path):
        yield path
        return
    name = key_env or opsconf.settings(config)["backup"]["key_env"]
    try:
        secret = sealing.passphrase(name, env)
        with tempfile.TemporaryDirectory(prefix="ghamon-open-") as scratch:
            plain = Path(scratch) / "package.zip"
            sealing.unseal(path, plain, secret)
            yield plain
    except sealing.SealError as error:
        raise OpsError(error.code, name) from None


def verify(path, key_env=None, env=None, config=None):
    """The list of problems of a package (empty = good); a sealed one is opened with the key of the variable. Raises OpsError for a missing file or a key that is not there. Reads only."""
    with open_package(path, key_env, env, config) as plain:
        return backup.verify_backup(plain)


def manifest_of(path, key_env=None, env=None, config=None):
    with open_package(path, key_env, env, config) as plain:
        return backup.read_manifest(plain)


def files_of(plain):
    """files.json of a plain package as a dict ({} when it has none: a format 1 package)."""
    data = backup.read_member(plain, FILES)
    try:
        found = json.loads(data.decode("utf-8")) if data else {}
    except (ValueError, UnicodeDecodeError):
        return {}
    return found if isinstance(found, dict) else {}
