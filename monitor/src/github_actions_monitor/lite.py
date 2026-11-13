# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`python -m github_actions_monitor.lite`: the lite edition (the same as MONITOR_LITE_GITHUB_ACTIONS): no sentinel, no collaboration, no several accounts, its own files and port."""
import sys

from github_actions_monitor.app import actions_monitor


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if "--lite" not in args:
        args.insert(0, "--lite")
    sys.argv = [sys.argv[0], *args]
    return actions_monitor.main()


if __name__ == "__main__":
    sys.exit(main())
