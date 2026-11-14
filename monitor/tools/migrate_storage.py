#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Moves the state of the complete edition between the file backend and the SQLite backend.

  py -3 tools/migrate_storage.py --from file --to sqlite [--accounts-dir DIR] [--db FILE] [--account ID ...] [--flat] [--apply]

Without --apply it only SHOWS what it would copy, account by account (a dry run: nothing is written). With --apply every account is copied in one step of the target, then both sides are
read back and compared item by item (configuration, sentinel state, documents, analytics, every event, the users and sessions); the exit code is 0 only when that comparison is clean.
Your files are never changed or deleted. An interrupted run leaves each account whole or as it was: run the same command again and it resumes (accounts that are already identical are skipped).

  --accounts-dir  the folder of the accounts (default: data/accounts/ of the product folder, or MONITOR_ACCOUNTS_DIR); with --flat the product folder itself
  --db            ONE shared database (model B). Without it each account gets its own, data/accounts/<id>/storage.sqlite3 (model A, the default)
  --flat          the installation without an accounts/ folder: one account, "default", with its files in config/, data/ and logs/ of the product folder

After a clean run, set  "storage": {"backend": "sqlite"}  in the configuration of the account (or of the monitor) and restart it.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))            # works also under `py -3 -I`
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.accounts import accounts  # noqa: E402
from github_actions_monitor.storage import installation, migrate  # noqa: E402


def build(args):
    root = Path(args.accounts_dir) if args.accounts_dir else (HERE if args.flat else accounts.root_dir(HERE))
    db = Path(args.db) if args.db else None
    return installation.open_installation(args.source, root, db if args.source == "sqlite" else None, args.flat), installation.open_installation(args.target, root, db if args.target == "sqlite" else None, args.flat)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", choices=("file", "sqlite"), required=True, help=i18n.t("mst.help_from"))
    parser.add_argument("--to", dest="target", choices=("file", "sqlite"), required=True, help=i18n.t("mst.help_to"))
    parser.add_argument("--accounts-dir", help=i18n.t("mst.help_dir"))
    parser.add_argument("--db", help=i18n.t("mst.help_db"))
    parser.add_argument("--account", action="append", metavar="ID", help=i18n.t("mst.help_account"))
    parser.add_argument("--flat", action="store_true", help=i18n.t("mst.help_flat"))
    parser.add_argument("--apply", action="store_true", help=i18n.t("mst.help_apply"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = parser.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    if args.source == args.target:
        print(i18n.t("mst.same_backend"))
        return 2
    source, target = build(args)
    try:
        rows = migrate.plan(source, target, args.account)
        if not rows:
            print(i18n.t("mst.nothing", source=str(source.root)))
            return 0
        print(i18n.t("mst.found", n=len(rows), source=str(source.root)))
        for row in rows:
            print("  " + i18n.t("mst.row", account=row["account"], events=row["events"], sentinels=row["sentinels"], docs=row["docs"], status=i18n.t("mst.s_" + row["status"])))
        if not args.apply:
            print(i18n.t("mst.dry_run"))
            return 0
        result = migrate.migrate(source, target, apply=True, accounts=args.account)
        if result["verified"]:
            print(i18n.t("mst.done", n=result["copied"], skipped=result["skipped"], events=result["events"]))
            return 0
        print(i18n.t("mst.failed", n=len(result["problems"])))
        for problem in result["problems"][:10]:
            print("  " + problem)
        return 1
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    sys.exit(main())
