# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`python -m github_actions_monitor` starts the complete monitor (the same as MONITOR_GITHUB_ACTIONS); `python -m github_actions_monitor.lite` the lite edition."""
import sys

from github_actions_monitor.app import actions_monitor

if __name__ == "__main__":
    sys.exit(actions_monitor.main())
