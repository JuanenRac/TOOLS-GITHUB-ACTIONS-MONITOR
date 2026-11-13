# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Finds what a flat installation (versions up to 1.7.9: every module, the page, the examples and the languages in ONE folder) leaves behind when the new layout is unzipped over it.

Standard library only. Nothing here changes a file: `stale()` only LISTS (the doctor shows it, tools/migrate_layout.py moves it). The data of the person who runs the monitor (actions_monitor.json, the
caches, the logs, accounts/, config_backups/, targets.json, ecosystems.json, profiles.json, quotas.json) is never listed.
"""
from pathlib import Path

from github_actions_monitor.util import paths

SHIM_MARK = "runpy.run_module"                     # the tiny entry points of the new layout (read_report.py, actions_monitor.py ...) carry this call; an old module does not
MOVED_ASSETS = ("actions_monitor.html", "actions_monitor.example.json", "ecosystems.example.json", "profiles.example.json", "targets.example.json")
MOVED_DIRS = ("locales",)
EXTRA_MODULES = ("make_release",)                    # now in tools/


def module_names():
    """The stems of the modules that live in the package now (the ones an old flat folder holds as <stem>.py)."""
    names = set(EXTRA_MODULES)
    for path in paths.PACKAGE.rglob("*.py"):
        if "__pycache__" in path.parts or path.stem in ("__init__", "__main__"):
            continue
        names.add(path.stem)
    names.add("i18n")                                 # i18n.py became the package i18n/
    return names


def is_entry_point(path):
    try:
        return SHIM_MARK in path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return False


def stale(root=None):
    """[Path] (relative to `root`) of the code, the page, the examples and the languages of an old flat layout that are still there: old modules (not the new entry points), the old page, the old
    examples and the old locales/ folder. Only listed when the new layout is present next to them (src/ and assets/)."""
    root = Path(root) if root else paths.ROOT
    if not (root / "src" / "github_actions_monitor").is_dir():
        return []
    found = []
    modules = module_names()
    for path in sorted(root.glob("*.py")):
        if path.stem in modules and not is_entry_point(path):
            found.append(Path(path.name))
    for name in MOVED_ASSETS:
        if (root / name).is_file() and (root / "assets").is_dir():
            found.append(Path(name))
    for name in MOVED_DIRS:
        if (root / name).is_dir() and (root / "assets" / name).is_dir():
            found.append(Path(name))
    return found
