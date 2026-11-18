# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Restoring a backup package (format 1 or 2) and the deep check that proves one can be restored.

A restore verifies the package first; it is refused while a monitor answers on its port (stop the service), into a storage that already holds accounts (unless `force`; with `account` only when THAT
account exists) and into a folder that is not empty (`to_dir`). The settings it brings back are MERGED over the ones that are there: a key that the package does not carry (it left the secrets out) is
never removed. It writes `ops/restore_report.json` in the data folder: what came back and what is left for the person to do (the credentials are never restored).
"""
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from github_actions_monitor.ops import bundle, opsconf
from github_actions_monitor.ops.bundle import OpsError
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import backup, base, installation
from github_actions_monitor.util import paths

REPORT = "restore_report.json"


def merge(existing, restored):
    """`restored` written over `existing`, key by key and level by level; what only `existing` holds stays."""
    if not isinstance(existing, dict) or not isinstance(restored, dict):
        return restored
    out = dict(existing)
    for key, value in restored.items():
        out[key] = merge(existing.get(key), value) if isinstance(value, dict) else value
    return out


def service_alive(config=None):
    """True when a monitor answers on the port of either edition of this computer."""
    from github_actions_monitor.util import exclusive, ports
    return any(exclusive.monitor_on(port) for port in set(ports.both().values()))


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    private_io.write_private(path, json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def _checklist(done, files, omitted, to_dir):
    todo = ["credentials"]
    if omitted:
        todo.append("settings_left_out")
    if len(done["ids"]) > 1 and not to_dir:
        todo.append("children")
    if files.get("skipped"):
        todo.append("files_skipped")
    todo += ["doctor", "start"]
    return todo


def restore(path, config=None, folder=None, account=None, to_dir=None, force=False, key_env=None, env=None, alive=None, inst=None, now=None):
    """Restores the package `path`. Returns the report (also saved). Raises OpsError: not_found, library_missing / key_missing / key_weak / bad_key / damaged (a sealed package), verify (the package does
    not verify), service_running, dir_not_empty, exists (accounts there, no force), no_account, package."""
    alive = alive if alive is not None else service_alive
    with bundle.open_package(path, key_env, env, config) as plain:
        problems = backup.verify_backup(plain)
        if problems:
            raise OpsError("verify", "; ".join(problems[:3]))
        manifest = backup.read_manifest(plain)
        files = bundle.files_of(plain)
        if manifest.get("scope") == "account":      # a package of one account restores that account and nothing else
            if account is not None and account != manifest.get("account"):
                raise OpsError("no_account", account)
            account = manifest.get("account")
        target_folder = folder
        if to_dir:
            root = Path(to_dir)
            try:
                busy = root.exists() and any(root.iterdir())
            except OSError:
                busy = True
            if busy and not force:
                raise OpsError("dir_not_empty", str(root))
            target = inst or installation.open_installation("file", root / "accounts")
            target_folder = root
        else:
            if alive():
                raise OpsError("service_running")
            target = inst or bundle.open_installation(config, folder)
        try:
            def keep_existing_keys(account_id, payload):
                if not payload.get("config"):
                    return payload
                held = {}
                try:
                    held = target.account_storage(account_id).load_config(account_id)
                except (OSError, base.StorageError):
                    held = {}
                return {**payload, "config": merge(held, payload["config"])}
            try:
                done = backup.restore_backup(plain, target, force=force, only_account=account, payload_filter=keep_existing_keys)
            except base.StorageError as error:
                text = str(error)
                code = "exists" if "already holds" in text else ("no_account" if "no such account" in text or "account id" in text else "package")
                raise OpsError(code, account or text) from None
            written, skipped = [], []
            if account is None and files.get("included"):
                written, skipped = _write_files(files, config, target_folder, force, to_dir)
            after = target.verify()
        finally:
            if inst is None:
                target.close()
    moment = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    omitted = int(manifest.get("config_omitted") or 0)
    report = {"at": moment, "package_created": manifest.get("created", ""), "package_version": manifest.get("product_version", ""), "format": manifest.get("format"), "accounts": done["accounts"], "ids": done["ids"],
              "events": done["events"], "to_dir": bool(to_dir), "only_account": account or "", "files": {"written": written, "skipped": skipped}, "verify": after[:5], "config_omitted": omitted}
    report["todo"] = _checklist(done, report["files"], omitted, bool(to_dir))
    try:
        _write_json(opsconf.ops_dir(target_folder) / REPORT, report)
    except OSError:
        report["report_saved"] = False
    return report


def _write_files(files, config, folder, force, to_dir):
    """The settings and the lists of the package that are not in the dump. A file that is already there is kept unless `force`; the settings are merged. Returns (written, skipped) as lists of names."""
    written, skipped = [], []
    target = paths.place("actions_monitor.json", folder) if to_dir else paths.config_file()
    clean = files.get("config")
    if isinstance(clean, dict) and clean:
        if target.is_file() and not force:
            skipped.append("actions_monitor.json")
        else:
            held = {}
            try:
                held = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
            except (OSError, ValueError):
                held = {}
            _write_json(target, merge(held if isinstance(held, dict) else {}, clean))
            written.append("actions_monitor.json")
    for name, data in {**(files.get("lists") or {}), **(files.get("files") or {})}.items():
        if name not in bundle.LISTS + bundle.GLOBAL_FILES + bundle.OPTIONAL_FILES:
            continue
        path = paths.place(name, folder)
        if path.is_file() and not force:
            skipped.append(name)
            continue
        _write_json(path, data)
        written.append(name)
    return written, skipped


def deep_verify(path, config=None, key_env=None, env=None):
    """The deep check of a package: it verifies, restores into a temporary folder (files backend) and checks the restored storage. Returns the list of problems (empty = it can be restored)."""
    with bundle.open_package(path, key_env, env, config) as plain:
        problems = backup.verify_backup(plain)
        if problems:
            return problems
        manifest = backup.read_manifest(plain)
        with tempfile.TemporaryDirectory(prefix="ghamon-deep-") as scratch:
            target = installation.open_installation("file", Path(scratch) / "accounts")
            try:
                done = backup.restore_backup(plain, target)
                problems = list(target.verify())
                if done["accounts"] != manifest.get("accounts") or done["events"] != manifest.get("events"):
                    problems.append("the restored counts differ from the manifest")
            except base.StorageError as error:
                problems.append(str(error)[:120])
            finally:
                target.close()
    return problems


def last_report(folder=None):
    try:
        data = json.loads((opsconf.ops_dir(folder) / REPORT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
