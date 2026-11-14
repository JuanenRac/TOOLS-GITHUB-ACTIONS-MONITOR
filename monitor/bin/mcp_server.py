#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Entry point of the command line: `py -3 bin/mcp_server.py ...`. It only puts src/ on the path and runs github_actions_monitor.integrations.mcp_server (the code lives there)."""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":      # importing this file by its old flat name must not start anything
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    runpy.run_module("github_actions_monitor.integrations.mcp_server", run_name="__main__", alter_sys=True)
