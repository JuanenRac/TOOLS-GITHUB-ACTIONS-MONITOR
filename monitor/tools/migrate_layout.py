#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tidies a folder that was a FLAT installation (every module, the page, the examples and the languages next to each other) after the new layout was unzipped over it.

  py -3 tools/migrate_layout.py [FOLDER] [--apply] [--lang CODE]

Without --apply it only SHOWS what it would do (a dry run: nothing is touched). With --apply:
  1. a copy of your configuration files (actions_monitor.json, actions_monitor_lite.json, targets.json, ecosystems.json, profiles.json, quotas.json) goes to layout_backup_<stamp>/config/;
  2. the old modules, the old page, the old examples and the old locales/ folder are MOVED (not deleted) to layout_backup_<stamp>/old_code/, because the new layout carries its own copies in src/ and assets/.
Your data is never touched: actions_monitor.json, the caches, the logs, config_backups/, accounts/, the catalogue files and quotas.json stay exactly where they are, and nothing that already exists is
overwritten. Run it again and it finds nothing to do. FOLDER defaults to the folder this script belongs to.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))            # works also under `py -3 -I`
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.util import layout  # noqa: E402

CONFIG_FILES = ("actions_monitor.json", "actions_monitor_lite.json", "targets.json", "ecosystems.json", "profiles.json", "quotas.json")


def plan(root):
    """[(relative path, kind)] of what would move; empty = nothing to do."""
    return [(p, "folder" if (Path(root) / p).is_dir() else "file") for p in layout.stale(root)]


def apply(root, stamp=None):
    """Makes the copy of the configuration and moves the old code. Returns (backup folder, [moved relative paths], [copied configuration names]). Never deletes, never overwrites."""
    root = Path(root)
    items = plan(root)
    if not items:
        return None, [], []
    backup = root / f"layout_backup_{stamp or time.strftime('%Y%m%d_%H%M%S', time.gmtime())}"
    if backup.exists():
        raise SystemExit(f"{backup} already exists: nothing was changed")
    copied, moved = [], []
    (backup / "config").mkdir(parents=True)
    (backup / "old_code").mkdir()
    for name in CONFIG_FILES:
        source = root / name
        if source.is_file():
            shutil.copy2(source, backup / "config" / name)
            copied.append(name)
    for relative, _kind in items:
        shutil.move(str(root / relative), str(backup / "old_code" / relative))
        moved.append(relative.as_posix())
    return backup, moved, copied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", nargs="?", default=str(HERE))
    parser.add_argument("--apply", action="store_true", help=i18n.t("ml.help_apply"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = parser.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    root = Path(args.folder).resolve()
    items = plan(root)
    if not items:
        print(i18n.t("ml.nothing", folder=str(root)))
        return 0
    print(i18n.t("ml.found", n=len(items), folder=str(root)))
    for relative, kind in items:
        print("  " + relative.as_posix() + ("/" if kind == "folder" else ""))
    if not args.apply:
        print(i18n.t("ml.dry_run"))
        return 0
    backup, moved, copied = apply(root)
    print(i18n.t("ml.done", moved=len(moved), copied=len(copied), backup=backup.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
