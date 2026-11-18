# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Backup and restore of a storage, the same for every backend.

A backup is ONE .zip. Format 1 has two members:

  dump.jsonl     one JSON line per account ({"account": id, "payload": <export_account>}) and a last line with the global records ({"records": ...})
  manifest.json  {"format", "backend", "created", "accounts", "events", "dump_bytes", "dump_sha256"}

Format 2 (the package of `ops/bundle.py`) adds members next to the dump (files.json: the settings and the lists of the installation, cleaned) and a `members` table in the manifest with the size and the
SHA-256 of every one of them. `verify_backup` reads both formats; a restore never needs to know which one it holds.

The dump does not depend on the backend: a copy made from files restores into SQLite and the other way round. `verify_backup` re-reads the zip and checks the size and the SHA-256 of the
dump (and of every member of a format 2 package) and the counts of the manifest; `restore_backup` verifies first, refuses to write into a storage that already holds accounts unless `force`, and writes
every account with the atomic operations of the target. Nothing here reads or sends anything outside the files.
"""
import hashlib
import json
import os
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.storage import base

FORMAT = 1
FORMATS = (1, 2)
DUMP, MANIFEST = "dump.jsonl", "manifest.json"
MEMBER_READ_MAX = 16 * 1024 * 1024      # the most that a member other than the dump may weigh once it is read


NOT_KEPT = ("sessions",)      # a backup never carries the sessions (they hold the CSRF token of each one) and restoring one never brings a revoked session back to life


def _without_sessions(records):
    return {kind: rows for kind, rows in (records or {}).items() if kind not in NOT_KEPT}


def _dump_lines(storage, payload_filter=None, only_account=None):
    for account_id in storage.list_accounts():
        if only_account is not None and account_id != only_account:
            continue
        payload = storage.export_account(account_id)
        yield json.dumps({"account": account_id, "payload": payload_filter(account_id, payload) if payload_filter else payload}, ensure_ascii=False, sort_keys=True)
    yield json.dumps({"records": {} if only_account is not None else _without_sessions(storage.export_records())}, ensure_ascii=False, sort_keys=True)      # a package of one account carries no users


def write_package(storage, dest, fmt=FORMAT, payload_filter=None, extra_members=None, level=6, info=None, only_account=None):
    """Writes the package of `storage` to the file `dest` (a .zip, replaced atomically) and returns its manifest. `payload_filter(account_id, payload)` may clean the payload of every account before
    it is written; `extra_members` ({name: bytes}) are written next to the dump (format 2) and `info` is merged into the manifest. With `only_account` the package holds that account alone
    and no global record (no user), and the manifest says `scope: account`."""
    if only_account is not None:
        base.check_account(only_account)
        if only_account not in storage.list_accounts():
            raise base.StorageError("the storage holds no such account")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest, size, accounts, events = hashlib.sha256(), 0, 0, 0
    tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
    try:
        with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=level) as bundle:
            with bundle.open(DUMP, mode="w", force_zip64=True) as member:
                for line in _dump_lines(storage, payload_filter, only_account):
                    data = (line + "\n").encode("utf-8")
                    member.write(data)
                    digest.update(data)
                    size += len(data)
                    parsed = json.loads(line)
                    if "account" in parsed:
                        accounts += 1
                        events += len(parsed["payload"].get("events") or [])
            manifest = {"format": fmt, "backend": storage.backend, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "accounts": accounts, "events": events,
                        "dump_bytes": size, "dump_sha256": digest.hexdigest()}
            if only_account is not None:
                manifest.update(scope="account", account=only_account)
            if fmt >= 2:
                members = {DUMP: {"bytes": size, "sha256": digest.hexdigest()}}
                for name, data in sorted((extra_members or {}).items()):
                    bundle.writestr(name, data)
                    members[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                manifest.update(info or {})
                manifest["members"] = members
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


def make_backup(storage, dest):
    """Writes the backup (format 1) of `storage` to the file `dest` (a .zip, replaced atomically) and returns its manifest."""
    return write_package(storage, dest)


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


def read_member(path, name):
    """The bytes of one member of a package (not the dump), or None when it is missing or too big. Reads only."""
    try:
        with zipfile.ZipFile(path) as bundle:
            if name not in bundle.namelist() or bundle.getinfo(name).file_size > MEMBER_READ_MAX:
                return None
            return bundle.read(name)
    except (OSError, zipfile.BadZipFile, EOFError, zlib.error):
        return None


def read_manifest(path):
    """The manifest of a package, or {} when it cannot be read."""
    try:
        bundle, manifest = _open(path)
    except base.StorageError:
        return {}
    bundle.close()
    return manifest if isinstance(manifest, dict) else {}


def _member_problems(bundle, manifest):
    """The problems of the members of a format 2 package: a member the manifest lists is missing, one it does not list is there, or a size or checksum differs."""
    members = manifest.get("members")
    if not isinstance(members, dict) or DUMP not in members:
        return ["members missing from the manifest"]
    problems = []
    names = set(bundle.namelist()) - {MANIFEST}
    if names - set(members):
        problems.append("a member the manifest does not list")
    for name, expected in members.items():
        if name not in names:
            problems.append("members missing: " + str(name)[:40])
            continue
        if name == DUMP or not isinstance(expected, dict):
            continue
        try:
            if bundle.getinfo(name).file_size > MEMBER_READ_MAX:
                problems.append("a member is too big: " + name[:40])
                continue
            data = bundle.read(name)
        except (OSError, zipfile.BadZipFile, EOFError, zlib.error):
            problems.append("a member cannot be read: " + name[:40])
            continue
        if len(data) != expected.get("bytes") or hashlib.sha256(data).hexdigest() != expected.get("sha256"):
            problems.append("the checksum of a member differs from the manifest: " + name[:40])
    if isinstance(members.get(DUMP), dict) and (members[DUMP].get("bytes") != manifest.get("dump_bytes") or members[DUMP].get("sha256") != manifest.get("dump_sha256")):
        problems.append("the table of members disagrees about the dump")
    return problems


def verify_backup(path):
    """A list of problems with the backup file (empty = it is complete and its checksum matches). Reads only."""
    try:
        bundle, manifest = _open(path)
    except base.StorageError as error:
        return [str(error)]
    problems = []
    with bundle:
        if not isinstance(manifest, dict) or manifest.get("format") not in FORMATS:
            return ["unknown backup format"]
        if manifest["format"] >= 2:
            problems += _member_problems(bundle, manifest)
        digest, size, accounts, events, last_records, only_seen = hashlib.sha256(), 0, 0, 0, False, None
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
                        try:      # every id and name is checked here, before anything is written by a restore
                            base.check_account(parsed["account"])
                            for part in ("sentinels", "docs"):
                                for name in parsed["payload"].get(part) or {}:
                                    base.check_name(name)
                        except base.StorageError:
                            problems.append("an account id or a name in the dump is not valid")
                        accounts += 1
                        only_seen = parsed["account"]
                        events += len(parsed["payload"].get("events") or [])
                    elif isinstance(parsed, dict) and "records" in parsed:
                        last_records = True
                    else:
                        problems.append("a line of the dump has no account")
        except (OSError, zipfile.BadZipFile, EOFError, zlib.error) as error:
            return [f"the dump cannot be read: {str(error)[:80]}"]
    if size != manifest.get("dump_bytes"):
        problems.append("the size of the dump differs from the manifest")
    if digest.hexdigest() != manifest.get("dump_sha256"):
        problems.append("the checksum of the dump differs from the manifest")
    if accounts != manifest.get("accounts") or events != manifest.get("events"):
        problems.append("the counts differ from the manifest")
    if not last_records:
        problems.append("the global records are missing")
    if manifest.get("scope") == "account" and (accounts != 1 or manifest.get("account") != only_seen):
        problems.append("a package of one account must hold that account alone")
    return problems


def restore_backup(path, storage, force=False, only_account=None, payload_filter=None):
    """Restores a backup into `storage`. Verifies the file first. A storage that already holds accounts is refused unless `force` (then the accounts of the backup are written over them).
    `only_account` restores that account alone (the global records and the other accounts are left as they are; it is refused only when that account exists); `payload_filter(account_id, payload)` may change the payload of an account before
    it is written (a restore merges the settings with those that are there). Returns {"accounts": n, "events": n, "ids": [...]}."""
    problems = verify_backup(path)
    if problems:
        raise base.StorageError("the backup does not verify: " + "; ".join(problems[:3]))
    if only_account is not None:
        base.check_account(only_account)
    holds = storage.list_accounts()
    if (only_account in holds if only_account is not None else bool(holds)) and not force:
        raise base.StorageError("the storage already holds accounts: restore into an empty one, or use force")
    restored = {"accounts": 0, "events": 0, "ids": []}
    bundle, _manifest = _open(path)
    with bundle:
        if only_account is not None:
            with bundle.open(DUMP) as member:
                found = any(json.loads(raw.decode("utf-8")).get("account") == only_account for raw in member)
            if not found:
                raise base.StorageError("the backup holds no such account")
        with bundle.open(DUMP) as member:
            for raw in member:
                parsed = json.loads(raw.decode("utf-8"))
                if "account" in parsed:
                    if only_account is not None and parsed["account"] != only_account:
                        continue
                    payload = payload_filter(parsed["account"], parsed["payload"]) if payload_filter else parsed["payload"]
                    storage.import_account(parsed["account"], payload)
                    restored["accounts"] += 1
                    restored["events"] += len(parsed["payload"].get("events") or [])
                    restored["ids"].append(parsed["account"])
                elif only_account is None:
                    storage.import_records(_without_sessions(parsed["records"]))      # also for a backup made before sessions were left out
    return restored
