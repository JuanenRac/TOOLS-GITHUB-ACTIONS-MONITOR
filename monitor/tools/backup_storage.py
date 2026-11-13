#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Backup, check and restore of the state of the complete edition, for the file backend and for SQLite.

  py -3 tools/backup_storage.py backup  FILE.zip --backend file|sqlite [--accounts-dir DIR] [--db FILE] [--flat]
  py -3 tools/backup_storage.py verify  FILE.zip
  py -3 tools/backup_storage.py restore FILE.zip --backend file|sqlite [--accounts-dir DIR] [--db FILE] [--flat] [--force]

A backup is one .zip (a dump of every account and of the users and sessions, and a manifest with the counts, the size and the SHA-256 of the dump). It does not depend on the backend: a copy
made from files restores into SQLite and the other way round. `backup` verifies the file it wrote before it says it is done; `restore` verifies first and refuses to write into a storage that
already holds accounts unless --force. Stop the monitor of the account before restoring into it.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))            # works also under `py -3 -I`
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.accounts import accounts  # noqa: E402
from github_actions_monitor.storage import backup, base, installation  # noqa: E402


def open_target(args):
    root = Path(args.accounts_dir) if args.accounts_dir else (HERE if args.flat else accounts.root_dir(HERE))
    return installation.open_installation(args.backend, root, Path(args.db) if args.db and args.backend == "sqlite" else None, args.flat)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("backup", "verify", "restore"))
    parser.add_argument("file")
    parser.add_argument("--backend", choices=("file", "sqlite"), help=i18n.t("bst.help_backend"))
    parser.add_argument("--accounts-dir", help=i18n.t("mst.help_dir"))
    parser.add_argument("--db", help=i18n.t("mst.help_db"))
    parser.add_argument("--flat", action="store_true", help=i18n.t("mst.help_flat"))
    parser.add_argument("--force", action="store_true", help=i18n.t("bst.help_force"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = parser.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    if args.action == "verify":
        problems = backup.verify_backup(args.file)
        if problems:
            print(i18n.t("bst.bad", why="; ".join(problems[:3])))
            return 1
        print(i18n.t("bst.ok"))
        return 0
    if not args.backend:
        print(i18n.t("bst.need_backend"))
        return 2
    store = open_target(args)
    try:
        if args.action == "backup":
            manifest = backup.make_backup(store, args.file)
            print(i18n.t("bst.made", file=args.file, accounts=manifest["accounts"], events=manifest["events"], sha=manifest["dump_sha256"][:16]))
            return 0
        try:
            done = backup.restore_backup(args.file, store, force=args.force)
        except base.StorageError as error:
            print(i18n.t("bst.refused", why=str(error)[:200]))
            return 1
        problems = store.verify()
        if problems:
            print(i18n.t("bst.bad", why="; ".join(problems[:3])))
            return 1
        print(i18n.t("bst.restored", accounts=done["accounts"], events=done["events"]))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
