#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Entry point kept in the product folder so that `py -3 release_notes.py ...`, the scripts and the hooks that already call it keep working: it only puts src/ on the path and runs github_actions_monitor.cli.release_notes (the code lives there)."""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":      # importing this file by its old flat name must not start anything
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    runpy.run_module("github_actions_monitor.cli.release_notes", run_name="__main__", alter_sys=True)
