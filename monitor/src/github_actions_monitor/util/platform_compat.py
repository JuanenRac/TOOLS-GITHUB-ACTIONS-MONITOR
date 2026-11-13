# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Small helpers so the monitor and the batch tools behave the same on Windows, macOS and Linux.

Nothing here touches the network or the disk: it only decides how a command is written, which Python starts a child tool,
how the console is set up and what to tell the user when GitHub CLI is missing.
"""
import os
import shlex
import shutil
import subprocess
import sys

from github_actions_monitor import i18n


def is_windows(windows=None):
    """True on Windows. `windows` lets the tests ask for the other answer."""
    return (os.name == "nt") if windows is None else bool(windows)


def python_argv(windows=None):
    """The command that starts this very Python: `py -3` on Windows when the launcher exists, otherwise the running interpreter."""
    if is_windows(windows) and shutil.which("py"):
        return ["py", "-3"]
    return [sys.executable or "python3"]


def python_hint(windows=None):
    """How to write 'run Python' in text for the user: py -3 on Windows, python3 elsewhere."""
    return "py -3" if is_windows(windows) else "python3"


def command_text(argv, windows=None):
    """One command line the user can paste into the shell of their system (cmd/PowerShell quoting on Windows, POSIX quoting elsewhere)."""
    items = [str(x) for x in argv]
    return subprocess.list2cmdline(items) if is_windows(windows) else shlex.join(items)


def console_utf8():
    """Make the console print UTF-8 without failing on characters it cannot show (old Windows consoles use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def gh_install_hint(system=None):
    """Where to get GitHub CLI on this system, with the login step."""
    name = (system or sys.platform).lower()
    if name.startswith("win"):
        how = "winget install --id GitHub.cli"
    elif name.startswith("darwin"):
        how = "brew install gh"
    else:
        how = i18n.t("cli.gh_how_linux")
    return i18n.t("cli.gh_missing", how=how)


def gh_available():
    return shutil.which("gh") is not None
