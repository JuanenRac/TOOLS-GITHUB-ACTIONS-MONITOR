# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two skills that travel with the monitor (monitor/skills/): `internal` for the AI built into the monitor, `external` for the AIs that talk to it from outside. Standard library only.

  names()                    ("internal", "external")
  files(name)                the files of a skill (SKILL.md and references/*.md), relative paths
  read(name, file)           the text of one of them, or None for anything that is not one of them
  core(name, max_chars)      SKILL.md without its front matter, cut to a size: what is put in the prompt of the AI of the monitor
  install(name, dest)        copies the skill to <dest>/github-actions-monitor-<name>/. It NEVER overwrites a file that differs: those are reported as kept, so that a copy that
                             somebody edited is not lost. Refuses a destination on the D: drive or a network path.

Nothing here reads a secret or writes outside the destination that was asked for."""
import re
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.util import paths

NAMES = ("internal", "external")
FILE_RE = re.compile(r"^(?:SKILL\.md|references/[a-z-]+\.md)\Z")
FOREIGN = re.compile(r"^(?:[Dd]:|/mnt/[dD](?:/|$)|\\\\|//)")


def root():
    return paths.ROOT / "skills"


def names():
    return NAMES


def files(name):
    if name not in NAMES:
        return []
    base = root() / name
    found = [p.relative_to(base).as_posix() for p in base.rglob("*.md")] if base.is_dir() else []
    return sorted(f for f in found if FILE_RE.match(f))


def read(name, file="SKILL.md"):
    """The text of a file of a skill, or None (an unknown skill, a path that is not in the closed list, a missing file)."""
    if name not in NAMES or not FILE_RE.match(str(file)):
        return None
    try:
        return (root() / name / file).read_text(encoding="utf-8")
    except OSError:
        return None


def core(name, max_chars=3000):
    """SKILL.md of a skill without its front matter, cut at a line break to `max_chars` (at least 300)."""
    text = read(name)
    if text is None:
        return ""
    text = re.sub(r"\A---\n.*?\n---\n", "", text.replace("\r\n", "\n"), flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()      # the authorship comment is not for the prompt
    limit = max(300, int(max_chars))
    if len(text) <= limit:
        return text
    cut = text[:limit]
    return cut[:cut.rfind("\n")] if "\n" in cut else cut


def install(name, dest):
    """{"ok", "dest", "written": [...], "same": [...], "kept": [...], "error"}: copies the skill into <dest>/github-actions-monitor-<name>/ without overwriting a different file."""
    if name not in NAMES:
        return {"ok": False, "error": "name"}
    text = str(dest or "").strip()
    if not text or len(text) > 260 or any(ord(c) < 32 for c in text) or FOREIGN.match(text):
        return {"ok": False, "error": "dest"}
    target = Path(text).expanduser() / f"github-actions-monitor-{name}"
    out = {"ok": True, "dest": str(target), "written": [], "same": [], "kept": [], "error": ""}
    try:
        for file in files(name):
            body = read(name, file)
            path = target / file
            if path.is_file():
                (out["same"] if path.read_text(encoding="utf-8").replace("\r\n", "\n") == body.replace("\r\n", "\n") else out["kept"]).append(file)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            private_io.write_private(path, body.replace("\r\n", "\n"))
            out["written"].append(file)
    except OSError:
        out["ok"], out["error"] = False, "write"
    out["ok"] = out["ok"] and not out["kept"]
    return out
