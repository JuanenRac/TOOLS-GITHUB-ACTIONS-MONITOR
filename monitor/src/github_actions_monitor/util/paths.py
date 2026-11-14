# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Where things are, in one place (standard library only).

  ROOT      the product folder: the one that holds the launchers, README, docs/, tests/ and src/. The data of the person who runs the monitor (actions_monitor.json, the caches,
            the logs, config_backups/, accounts/<id>/) is written HERE, exactly where it was before the code moved into src/: never inside src/ and never under assets/.
  SRC       ROOT/src, the folder that holds the importable package.
  PACKAGE   the package itself.
  ASSETS    ROOT/assets: what travels with the product and is not code: examples/ (the neutral *.example.json and quotas.json), static/ (the page) and locales/ (the 8 languages).
  DOCS      ROOT/docs.
"""
import os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SRC = PACKAGE.parent
ROOT = SRC.parent
ASSETS = ROOT / "assets"
EXAMPLES = ASSETS / "examples"
STATIC = ASSETS / "static"
LOCALES = ASSETS / "locales"
DOCS = ROOT / "docs"


def config_file():
    """The configuration file of the monitor: `MONITOR_CONFIG` when it is set (a container keeps it in a volume of its own, apart from the code), else `actions_monitor.json` in the product folder."""
    chosen = os.environ.get("MONITOR_CONFIG", "").strip()
    return Path(chosen) if chosen else ROOT / "actions_monitor.json"
