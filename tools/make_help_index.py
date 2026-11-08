#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Builds the index of the Help panel from the real documentation files, so no text is written twice.

    python tools/make_help_index.py            write monitor/docs/help_index.json
    python tools/make_help_index.py --check    fail when the file differs from what the documents give (the CI runs it)

Sources (every language that exists; English is the fallback when a document is not translated):
  README*.md of the repository, monitor/QUICKSTART_<xx>.txt, monitor/README_<xx>.txt, every guide monitor/docs/NAME.md with its NAME_<xxx>.md translations,
  docs/ROADMAP.md, monitor/CHANGELOG.md, CONTRIBUTING.md, SECURITY.md and SUPPORT.md.
The result is one JSON file that travels in the package: the local server answers the Help panel and the console help from it, without Internet.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MON = ROOT / "monitor"
TARGET = MON / "docs" / "help_index.json"
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
SUFFIX = {"en": "", "es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}      # README_spa.md, SETTINGS_spa.md
SHORT = {lang: "_" + lang for lang in LANGS}                                                                            # QUICKSTART_es.txt, README_es.txt
ORDER = ("readme", "first_steps", "quickstart", "lite", "sentinel", "quotas", "modes", "settings", "ai", "analytics", "notifications", "outputs", "webhook", "console_tools", "deployment", "ci_red_bridge", "ci_red_schema",
         "migrating", "roadmap", "changelog", "contributing", "security", "support", "package")


def clean(text, plain):
    """Without the copyright comment and the decorative HTML / language switchers."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\A(?:<!--.*?-->\s*)+", "", text, flags=re.S)
    if plain:
        text = re.sub(r"\A(?:Copyright[^\n]*\n)?(?:GPL-3\.0[^\n]*\n)?\s*", "", text)
    lines = []
    fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and not plain and (re.match(r"^\s*</?[A-Za-z!]", line) or line.count(" | ") >= 5 or line.strip() in ("</p>",)):
            continue
        lines.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def slug(title):
    base = re.sub(r"[^\w぀-ヿ一-鿿]+", "-", title.lower()).strip("-")
    return base or "section"


def split(text, plain):
    """[(slug, title, body)]: a first section for what comes before the first '## ' and one for each '## '. A plain text file is split at lines underlined with ===/---."""
    sections, title, body, fence = [], "", [], False
    lines = text.split("\n")
    heading = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
        match = None
        if not fence:
            match = re.match(r"^##\s+(.+?)\s*#*$", line) if not plain else None
        if match:
            if body or title:
                sections.append((title, "\n".join(body).strip()))
            title, body = match.group(1).strip(), []
        else:
            body.append(line)
    sections.append((title, "\n".join(body).strip()))
    out, seen = [], {}
    for title, content in sections:
        if not title and not content:
            continue
        name = slug(title) if title else "top"
        seen[name] = seen.get(name, 0) + 1
        out.append([name if seen[name] == 1 else f"{name}-{seen[name]}", title, content])
    return out


def first_title(text, fallback):
    for line in text.split("\n"):
        match = re.match(r"^#\s+(.+?)\s*#*$", line)
        if match:
            return re.sub(r"[*_`]", "", match.group(1)).strip()
    for line in text.split("\n"):
        if line.strip() and not line.startswith(("=", "-")):
            return line.strip()[:80]
    return fallback


def sources():
    """[(topic id, group, {lang: Path}, plain)]"""
    out = [("readme", "start", {l: ROOT / f"README{SUFFIX[l]}.md" for l in LANGS}, False),
           ("quickstart", "start", {l: MON / f"QUICKSTART{SHORT[l]}.txt" for l in LANGS}, True),
           ("package", "start", {l: MON / f"README{SHORT[l]}.txt" for l in LANGS}, True)]
    names = sorted({p.stem for p in (MON / "docs").glob("*.md") if not re.search(r"_(spa|deu|fra|ita|jpn|zho|por)$", p.stem)})
    for name in names:
        out.append((name.lower(), "guides", {l: MON / "docs" / f"{name}{SUFFIX[l]}.md" for l in LANGS}, False))
    out += [("roadmap", "project", {"en": ROOT / "docs" / "ROADMAP.md"}, False), ("changelog", "project", {"en": MON / "CHANGELOG.md"}, False),
            ("contributing", "project", {"en": ROOT / "CONTRIBUTING.md"}, False), ("security", "project", {"en": ROOT / "SECURITY.md"}, False),
            ("support", "project", {"en": ROOT / "SUPPORT.md"}, False)]
    return out


def build():
    topics, files = [], {}
    for topic_id, group, paths, plain in sources():
        titles, sections = {}, {}
        for lang, path in paths.items():
            if not path.is_file():
                continue
            files[path.name] = topic_id
            text = clean(path.read_text(encoding="utf-8"), plain)
            titles[lang] = first_title(text, topic_id)
            sections[lang] = split(text, plain)
        if "en" in sections:
            topics.append({"id": topic_id, "group": group, "plain": plain, "title": titles, "sections": sections})
    topics.sort(key=lambda t: (ORDER.index(t["id"]) if t["id"] in ORDER else len(ORDER), t["id"]))
    return {"_author": "Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>", "_license": "GPL-3.0-or-later - see LICENSE", "format": 1, "langs": list(LANGS), "files": dict(sorted(files.items())), "topics": topics}


def render():
    return json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"


def main(argv):
    want = render()
    have = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
    if "--check" in argv:
        ok = have == want
        print("HELP_INDEX=" + ("PASS the index agrees with the documents" if ok else "FAIL monitor/docs/help_index.json is out of date (run tools/make_help_index.py)"))
        return 0 if ok else 1
    TARGET.write_text(want, encoding="utf-8", newline="\n")
    print("HELP_INDEX=WRITTEN %s (%d KB)" % (TARGET, len(want.encode("utf-8")) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
