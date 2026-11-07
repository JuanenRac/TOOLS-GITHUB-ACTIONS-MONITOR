# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Prints a message of the launchers (.bat / .sh / .command) in the language of the user.  Usage:  launcher_msg.py gh_missing|stopped|menu|choose"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # works also under `py -3 -I`
import i18n  # noqa: E402
import platform_compat  # noqa: E402


def main(argv=None):
    platform_compat.console_utf8()
    i18n.cli_language(argv)
    what = (argv or sys.argv[1:] or [""])[0]
    if what == "gh_missing":
        print(platform_compat.gh_install_hint())
    elif what == "stopped":
        print(i18n.t("launch.stopped"))
    elif what == "choose":
        print(i18n.t("launch.choose"), end=" ")
    elif what == "menu":
        print("\n " + i18n.t("launch.menu_title"))
        for n in range(1, 7):
            print(f"  {n}) " + i18n.t(f"launch.m{n}"))
    else:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
