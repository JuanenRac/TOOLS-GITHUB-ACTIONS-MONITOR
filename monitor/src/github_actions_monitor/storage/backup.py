# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Backup and restore of a storage, the same for every backend.

A backup is ONE .zip with two members:

  dump.jsonl     one JSON line per account ({"account": id, "payload": <export_account>}) and a last line with the global records ({"records": ...})
  manifest.json  {"format", "backend", "created", "accounts", "events", "dump_bytes", "dump_sha256"}

The dump does not depend on the backend: a copy made from files restores into SQLite and the other way round. `verify_backup` re-reads the zip and checks the size and the SHA-256 of the
dump and the counts of the manifest; `restore_backup` verifies first, refuses to write into a storage that already holds accounts unless `force`, and writes every account with the
atomic operations of the target. Nothing here reads or sends anything outside the two files.
"""
import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.storage import base

FORMAT = 1
DUMP, MANIFEST = "dump.jsonl", "manifest.json"


def _dump_lines(storage):
    for account_id in storage.list_accounts():
        yield json.dumps({"account": account_id, "payload": storage.export_account(account_id)}, ensure_ascii=False, sort_keys=True)
    yield json.dumps({"records": storage.export_records()}, ensure_ascii=False, sort_keys=True)


def make_backup(storage, dest):
    """Writes the backup of `storage` to the file `dest` (a .zip, replaced atomically) and returns its manifest."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest, size, accounts, events = hashlib.sha256(), 0, 0, 0
    tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
    try:
        with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
            with bundle.open(DUMP, mode="w", force_zip64=True) as member:
                for line in _dump_lines(storage):
                    data = (line + "\n").encode("utf-8")
                    member.write(data)
                    digest.update(data)
                    size += len(data)
                    parsed = json.loads(line)
                    if "account" in parsed:
                        accounts += 1
                        events += len(parsed["payload"].get("events") or [])
            manifest = {"format": FORMAT, "backend": storage.backend, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "accounts": accounts, "events": events,
                        "dump_bytes": size, "dump_sha256": digest.hexdigest()}
            bundle.writestr(MANIFEST, json.dumps(manifest, indent=2) + "\n")
        problems = verify_backup(tmp)
        if problems:
            raise base.StorageError("the backup did not verify: " + "; ".join(problems[:3]))
        private_io._fix_mode(tmp, private_io.FILE_MODE)      # a backup holds everything: only its owner reads it
        os.replace(tmp, dest)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    return manifest


def _open(path):
    try:
        bundle = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise base.StorageError("not a backup: " + str(error)[:80]) from error
    names = set(bundle.namelist())
    if not {DUMP, MANIFEST} <= names:
        bundle.close()
        raise base.StorageError("not a backup: members missing")
    try:
        manifest = json.loads(bundle.read(MANIFEST).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        bundle.close()
        raise base.StorageError("not a backup: manifest") from error
    return bundle, manifest


def verify_backup(path):
    """A list of problems with the backup file (empty = it is complete and its checksum matches). Reads only."""
    try:
        bundle, manifest = _open(path)
    except base.StorageError as error:
        return [str(error)]
    problems = []
    with bundle:
        if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
            return ["unknown backup format"]
        digest, size, accounts, events, last_records = hashlib.sha256(), 0, 0, 0, False
        try:
            with bundle.open(DUMP) as member:
                for raw in member:
                    digest.update(raw)
                    size += len(raw)
                    try:
                        parsed = json.loads(raw.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        problems.append("a line of the dump is damaged")
                        continue
                    if isinstance(parsed, dict) and "account" in parsed and isinstance(parsed.get("payload"), dict):
                        accounts += 1
                        events += len(parsed["payload"].get("events") or [])
                    elif isinstance(parsed, dict) and "records" in parsed:
                        last_records = True
                    else:
                        problems.append("a line of the dump has no account")
        except (OSError, zipfile.BadZipFile, EOFError) as error:
            return [f"the dump cannot be read: {str(error)[:80]}"]
    if size != manifest.get("dump_bytes"):
        problems.append("the size of the dump differs from the manifest")
    if digest.hexdigest() != manifest.get("dump_sha256"):
        problems.append("the checksum of the dump differs from the manifest")
    if accounts != manifest.get("accounts") or events != manifest.get("events"):
        problems.append("the counts differ from the manifest")
    if not last_records:
        problems.append("the global records are missing")
    return problems


def restore_backup(path, storage, force=False):
    """Restores a backup into `storage`. Verifies the file first. A storage that already holds accounts is refused unless `force` (then the accounts of the backup are written over them).
    Returns {"accounts": n, "events": n}."""
    problems = verify_backup(path)
    if problems:
        raise base.StorageError("the backup does not verify: " + "; ".join(problems[:3]))
    if storage.list_accounts() and not force:
        raise base.StorageError("the storage already holds accounts: restore into an empty one, or use force")
    restored = {"accounts": 0, "events": 0}
    bundle, _manifest = _open(path)
    with bundle:
        with bundle.open(DUMP) as member:
            for raw in member:
                parsed = json.loads(raw.decode("utf-8"))
                if "account" in parsed:
                    storage.import_account(parsed["account"], parsed["payload"])
                    restored["accounts"] += 1
                    restored["events"] += len(parsed["payload"].get("events") or [])
                else:
                    storage.import_records(parsed["records"])
    return restored
