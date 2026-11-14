# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tidies the product folder of an installation of 1.8.1 or older: its data, configuration, logs and AI files used to sit next to the launchers; now they live in config/, data/, logs/ and ai/.

Standard library only. It MOVES, it never deletes and never overwrites, and it can be undone:

  py -3 -m github_actions_monitor.util.rootmigrate [FOLDER]          show what would move (nothing is touched)
  py -3 -m github_actions_monitor.util.rootmigrate [FOLDER] --apply  move it
  py -3 -m github_actions_monitor.util.rootmigrate [FOLDER] --undo   put every file back where it was

Before the first move the configuration files are copied to config/config_backups/pre_layout_<stamp>/; each move is written to data/.layout_moves.json, which is what --undo reads. The monitor does this by itself
when it starts (set MONITOR_NO_AUTO_MIGRATION=1 to turn that off), and the doctor tells when something is still next to the launchers. A file that already exists in its new place is left alone and reported.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.util import paths

JOURNAL = ".layout_moves.json"
LEAVE = set(paths.KINDS) | {"src", "assets", "docs", "bin", "tools", "tests", "deploy"}       # folders of the product itself and the new folders: never moved
PREFIXES = ("layout_backup_",)


def _base(root):
    return None if root is None else Path(root)


def _journal(root):
    return paths.folder("data", _base(root)) / JOURNAL


def plan(root=None):
    """[(source, destination)] of what is still next to the launchers: files and folders the monitor knows (paths.kind_of) whose place is now another folder. Destinations that exist are not listed here (see conflicts)."""
    root = Path(root) if root else paths.ROOT
    base = _base(root)
    if not root.is_dir():
        return []
    out = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.name in LEAVE or entry.name.startswith(PREFIXES):
            continue
        kind = paths.kind_of(entry.name)
        if kind is None or (entry.name == "state" and not entry.is_dir()):
            continue
        out.append((entry, paths.place(entry.name, base)))
    return out


def conflicts(root=None):
    """The part of plan() whose destination is already there as a FILE: those are not moved (the new place wins) and the doctor reports them."""
    return [(s, d) for s, d in plan(root) if d.exists() and not (s.is_dir() and d.is_dir())]


def _merge_move(source, destination, moved):
    """Moves a file, or a folder into a folder that already exists (child by child, never over an existing file)."""
    if source.is_dir() and destination.is_dir():
        for child in sorted(source.iterdir()):
            _merge_move(child, destination / child.name, moved)
        try:
            source.rmdir()
        except OSError:
            pass
        return
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    moved.append((source, destination))


def apply(root=None, stamp=None):
    """Moves what plan() lists. Returns {"moved": [(from, to)], "conflicts": [(from, to)], "backup": folder or None}; a second run finds nothing to do."""
    root = Path(root) if root else paths.ROOT
    base = _base(root)
    items = plan(root)
    todo = [(s, d) for s, d in items if not d.exists() or (s.is_dir() and d.is_dir())]
    out = {"moved": [], "conflicts": conflicts(root), "backup": None}
    if not todo:
        return out
    stamp = stamp or time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    config = [s for s, _d in todo if paths.kind_of(s.name) == "config" and s.is_file()]
    if config:
        backup = paths.folder("config", base) / "config_backups" / f"pre_layout_{stamp}"
        backup.mkdir(parents=True, exist_ok=True)
        for source in config:
            shutil.copy2(source, backup / source.name)
        out["backup"] = backup
    moved = []
    for source, destination in todo:
        try:
            _merge_move(source, destination, moved)
        except OSError as error:
            out.setdefault("problems", []).append(f"{source.name}: {str(error)[:80]}")
    if moved:
        journal = _journal(root)
        try:
            data = json.loads(journal.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {"runs": []}
        data["runs"].append({"stamp": stamp, "moves": [[str(s), str(d)] for s, d in moved]})
        journal.parent.mkdir(parents=True, exist_ok=True)
        private_io.write_private(journal, json.dumps(data, indent=1))
    out["moved"] = moved
    return out


def undo(root=None):
    """Puts back every file the journal says was moved (the last run first). Returns the list of (from, to) restored; a file that is gone or whose old place is taken stays where it is."""
    journal = _journal(root)
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    restored = []
    for run in reversed(data.get("runs", [])):
        for old, new in reversed(run.get("moves", [])):
            old, new = Path(old), Path(new)
            if new.exists() and not old.exists():
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(new), str(old))
                restored.append((new, old))
    try:
        journal.unlink()
    except OSError:
        pass
    return restored


def auto(root=None, environ=None):
    """The start-up call: moves what is still next to the launchers unless MONITOR_NO_AUTO_MIGRATION is set. Never raises (a monitor must start). Returns apply()'s answer or None."""
    import os
    environ = os.environ if environ is None else environ
    if (environ.get("MONITOR_NO_AUTO_MIGRATION") or "").strip() not in ("", "0"):
        return None
    try:
        result = apply(root)
    except OSError:
        return None
    if result["moved"]:
        sys.stderr.write(f"[layout] {len(result['moved'])} item(s) moved into config/, data/, logs/ and ai/ (undo: python -m github_actions_monitor.util.rootmigrate --undo)\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Moves the data of an installation of 1.8.1 or older into config/, data/, logs/ and ai/.")
    parser.add_argument("folder", nargs="?", default=None, help="the product folder (default: this one)")
    parser.add_argument("--apply", action="store_true", help="move the files (without it only shows)")
    parser.add_argument("--undo", action="store_true", help="put back what the last runs moved")
    args = parser.parse_args(argv)
    if args.undo:
        back = undo(args.folder)
        print(f"{len(back)} item(s) put back")
        return 0
    if not args.apply:
        items = plan(args.folder)
        for source, destination in items:
            print(f"{source.name}  ->  {destination}")
        print(f"{len(items)} item(s) would move" if items else "nothing to move")
        return 0
    result = apply(args.folder)
    print(f"{len(result['moved'])} item(s) moved; {len(result['conflicts'])} left (the new place already had a file)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
