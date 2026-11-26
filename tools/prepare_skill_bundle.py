#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Makes the folder of the external skill ready to be published in a skill registry (ClawHub uses the same SKILL.md format). It publishes NOTHING: the upload is done by hand by the maintainer.

    python tools/prepare_skill_bundle.py --out DIR

DIR (which must not exist or be empty) receives SKILL.md and references/ with LF line endings, bundle.json (name, version of the monitor, licence) and SHA256SUMS. The same sources give the same bytes."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "monitor" / "skills" / "external"
sys.path.insert(0, str(ROOT / "monitor" / "src"))
from github_actions_monitor.tool_version import TOOL_VERSION  # noqa: E402

LICENSE_ID = "GPL-3.0-or-later"
CHECKLIST = ("1. Read the terms of the registry and sign in with the account of the maintainer.",
             "2. Check that bundle.json has the version of the release that is published.",
             "3. Read SKILL.md and the references once more: no private path, name or key.",
             "4. Upload the folder by hand and write down the date in the private release notes.")


def front_matter(text):
    found = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not found:
        raise SystemExit("SKILL=FAIL SKILL.md has no front matter")
    return dict(line.split(": ", 1) for line in found.group(1).splitlines() if ": " in line)


def files(skill=SKILL):
    """{relative name: bytes with LF endings} of the skill."""
    out = {}
    for path in sorted(p for p in skill.rglob("*") if p.is_file() and p.suffix == ".md"):
        out[path.relative_to(skill).as_posix()] = path.read_bytes().replace(b"\r\n", b"\n")
    return out


def bundle(out, skill=SKILL, version=TOOL_VERSION):
    """Writes the bundle in `out` and returns {name: SHA-256}."""
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit("SKILL=FAIL the folder is not empty")
    content = files(skill)
    meta = front_matter(content["SKILL.md"].decode("utf-8"))
    info = {"name": meta["name"], "version": version, "license": LICENSE_ID, "description": meta["description"], "homepage": "https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR"}
    content["bundle.json"] = (json.dumps(info, indent=2) + "\n").encode("utf-8")
    sums = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(content.items())}
    content["SHA256SUMS"] = "".join(f"{sha}  {name}\n" for name, sha in sums.items()).encode("ascii")
    for name, data in content.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return sums


def main(argv=None):
    parser = argparse.ArgumentParser(prog="prepare_skill_bundle.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    sums = bundle(args.out)
    print(f"SKILL=OK {len(sums)} files, version {TOOL_VERSION}. Nothing was published. Before publishing by hand:")
    print("\n".join(CHECKLIST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
