# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The short summary of a release in the eight languages: `assets/release_summaries/<version>.json` with one text per language. It is written into the notes of the release as marked blocks, so that the
notice of an update can show it in the language of the interface with the same request that finds the update.

  python tools/release_summary.py check VERSION      is the summary there, complete and short enough
  python tools/release_summary.py blocks VERSION     the blocks to add at the end of the notes of the release
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
MAX_CHARS = 900                   # of one language: the whole of the eight stays small in the notes
FIRST_REQUIRED = (2, 2, 0)        # from this version on a release has a summary


def path_of(version, here=HERE):
    return Path(here) / "assets" / "release_summaries" / f"{version}.json"


def required(version):
    return tuple(int(part) for part in str(version).split(".")[:3]) >= FIRST_REQUIRED


def problems(version, here=HERE):
    """[problem] of the summary of `version`; empty list = complete (or not needed for that version)."""
    path = path_of(version, here)
    if not path.is_file():
        return [f"assets/release_summaries/{version}.json is missing"] if required(version) else []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"assets/release_summaries/{version}.json cannot be read: {error}"]
    found = []
    for lang in LANGS:
        text = data.get(lang) if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            found.append(f"the summary of {version} has no text in {lang}")
        elif len(text) > MAX_CHARS:
            found.append(f"the summary of {version} in {lang} is longer than {MAX_CHARS} characters")
        elif "<!--" in text or "-->" in text:
            found.append(f"the summary of {version} in {lang} holds a comment mark")
    return found


def blocks(version, here=HERE):
    """The text to put at the end of the notes of the release ("" when there is no summary)."""
    path = path_of(version, here)
    if not path.is_file():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    return "\n".join(f"<!-- whats-new:{lang}\n{data[lang].strip()}\n-->" for lang in LANGS) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="release_summary.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("check", "blocks"))
    parser.add_argument("version")
    args = parser.parse_args(argv)
    found = problems(args.version)
    if found:
        print("\n".join(found))
        return 1
    if args.action == "blocks":
        sys.stdout.buffer.write(blocks(args.version).encode("utf-8"))
    else:
        print("RELEASE_SUMMARY=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
