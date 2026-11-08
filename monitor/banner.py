# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tells at a glance which edition runs: the start-up banner, the window title and the tag of the status lines of the console, for the complete and the lite edition.

  GitHub Actions Monitor LITE 1.6.3 · port 8766 · actions_monitor_lite.json · no sentinel · http://127.0.0.1:8766/
  GitHub Actions Monitor COMPLETE 1.6.3 · port 8765 · actions_monitor.json · sentinel on · http://127.0.0.1:8765/
"""
import sys

from tool_version import TOOL_VERSION

NAMES = {False: "COMPLETE", True: "LITE"}


def tag(lite):
    """The short mark of a status line: [LITE] or [COMPLETE] (the words are the same in every language: they are product names)."""
    return f"[{NAMES[bool(lite)]}]"


def line(lite, port, config_name, translate, url=None, sentinel=None, version=TOOL_VERSION):
    """The banner line in the language of the user."""
    on = (not lite) if sentinel is None else bool(sentinel)
    parts = [f"GitHub Actions Monitor {NAMES[bool(lite)]} {version}", translate("banner.port", port=port), config_name, translate("banner.sentinel_on" if on else "banner.sentinel_off")]
    if url:
        parts.append(url)
    return " · ".join(parts)


def window_title(lite, port, translate):
    return f"GitHub Actions Monitor {NAMES[bool(lite)]} - {translate('banner.port', port=port)}"


def set_title(text, stream=None):
    """Sets the title of the window of the console / terminal with the OSC 0 sequence (Windows Terminal, macOS, Linux; the old Windows console is handled by `title` in the launcher). Only on a terminal."""
    stream = stream or sys.stdout
    try:
        if stream.isatty():
            stream.write(f"\x1b]0;{text}\x07")
            stream.flush()
    except (OSError, ValueError):
        pass
