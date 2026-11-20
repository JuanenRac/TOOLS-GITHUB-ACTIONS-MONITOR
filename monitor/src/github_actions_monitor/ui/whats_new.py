# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What is new after an update: the entries of the CHANGELOG of the versions that a person skipped, in the language of the page.

The page remembers (in the browser, never on the server) the version it showed last; when the monitor is a newer one it offers a small notice with the entries of every version in between, without
interrupting anything (it opens only when asked and is dismissed with the first click). The text is the real CHANGELOG of the installed version, in its eight translations, so there is nothing to keep in
sync and nothing is read from the network.

  versions(text)                 [(version, [entry, ...])] from the text of a changelog, newest first (`[Unreleased]` is left out)
  since(text, seen, current)     the same, only the versions after `seen` up to `current`; at most 5 versions of 12 entries each
  payload(language, seen, current, enabled)   what GET /api/whats-new answers
"""
import re

from github_actions_monitor.util import paths

TAIL = {"en": "", "es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}
HEADING = re.compile(r"^## \[(\d+(?:\.\d+){1,3})\]", re.M)
MAX_VERSIONS = 5
MAX_ENTRIES = 12
MAX_CHARS = 420
VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}\Z")


def vkey(text):
    return tuple(int(p) for p in re.findall(r"\d+", str(text))[:4])


def clean(entry):
    """One entry as plain text: the bold title and the rest, without the marks of the format, cut to a size a notice can hold."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", entry)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS - 1].rstrip() + "…"


def versions(text):
    """[(version, [entries])] newest first; an entry is a line that starts with "- " (a long entry may continue on the next lines, which are joined)."""
    text = str(text or "").replace("\r\n", "\n")
    marks = list(HEADING.finditer(text))
    out = []
    for i, mark in enumerate(marks):
        body = text[mark.end():marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        entries, current = [], None
        for line in body.split("\n"):
            if line.startswith("- "):
                if current is not None:
                    entries.append(current)
                current = line[2:]
            elif current is not None and line.strip() and not line.startswith("#"):
                current += " " + line.strip()
            elif current is not None and (not line.strip() or line.startswith("#")):
                entries.append(current)
                current = None
        if current is not None:
            entries.append(current)
        out.append((mark.group(1), [clean(e) for e in entries if e.strip()]))
    return out


def since(text, seen, current):
    """The versions after `seen` and up to `current` (both inclusive of `current`); with no `seen` only `current`."""
    cur = vkey(current)
    low = vkey(seen) if seen else (0,)
    rows = [(v, items) for v, items in versions(text) if vkey(v) <= cur and (vkey(v) > low if seen else vkey(v) == cur)]
    return [{"version": v, "items": items[:MAX_ENTRIES], "more": max(0, len(items) - MAX_ENTRIES)} for v, items in rows[:MAX_VERSIONS]]


def changelog_text(language):
    """The changelog of the installed version in this language, else the English one; '' when the files are not there (a copy without the docs)."""
    for path in ([paths.DOCS / f"CHANGELOG{TAIL[language]}.md"] if language in TAIL and language != "en" else []) + [paths.ROOT / "CHANGELOG.md"]:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


def payload(language, seen, current, enabled):
    seen = seen if isinstance(seen, str) and VERSION_RE.match(seen) else ""
    if not enabled:
        return {"enabled": False, "current": current, "seen": seen, "versions": []}
    return {"enabled": True, "current": current, "seen": seen, "versions": since(changelog_text(language), seen, current)}
