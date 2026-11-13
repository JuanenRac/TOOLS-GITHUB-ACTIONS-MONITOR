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
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SRC = PACKAGE.parent
ROOT = SRC.parent
ASSETS = ROOT / "assets"
EXAMPLES = ASSETS / "examples"
STATIC = ASSETS / "static"
LOCALES = ASSETS / "locales"
DOCS = ROOT / "docs"
