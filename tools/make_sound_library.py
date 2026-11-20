#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/make_sound_library.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Writes the library of sounds (monitor/src/github_actions_monitor/integrations/soundlib.py) into the page and into the wall screens, between /*SND-LIBRARY-BEGIN*/ and /*SND-LIBRARY-END*/.

    python tools/make_sound_library.py           rewrite both files
    python tools/make_sound_library.py --check   exit 1 when a copy is out of date (a test runs it)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "monitor" / "src"))
from github_actions_monitor.integrations import soundlib  # noqa: E402

FILES = [ROOT / "monitor" / "assets" / "static" / "actions_monitor.html", ROOT / "monitor" / "assets" / "static" / "screens.html"]
BLOCK = re.compile(r"/\*SND-LIBRARY-BEGIN\*/.*?/\*SND-LIBRARY-END\*/", re.S)


def render(text):
    block = soundlib.js_block()
    if not BLOCK.search(text):
        raise SystemExit("markers not found")
    return BLOCK.sub(lambda m: block, text, count=1)


def main(argv):
    check = "--check" in argv
    stale = []
    for path in FILES:
        old = path.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in old else "\n"
        new = render(old.replace("\r\n", "\n")).replace("\n", eol)
        if new != old:
            stale.append(path.name)
            if not check:
                path.write_bytes(new.encode("utf-8"))
    if stale:
        print(("out of date: " if check else "rewritten: ") + ", ".join(stale))
    return 1 if (stale and check) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
