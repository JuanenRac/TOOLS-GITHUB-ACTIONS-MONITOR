#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Compares an extracted release (a folder, or the zip itself) with the files a git ref versions, by CONTENT: line endings are made alike and two JSON files that hold the same data count as equal
whatever their spacing or key order. For whoever audits a package: "is what I downloaded what the tag says?" without being fooled by the CRLF that the build puts on launchers or by a re-indented JSON.

    py -3 tools/compare_tree.py PATH [--ref v2.1.4] [--root monitor] [--strip github_actions_monitor] [--ignore GLOB ...] [--repo DIR]

Exit 0 when nothing differs, 1 when something does, 2 when the input cannot be read. Files only in the package, only in the ref and different ones are listed by name; nothing is written."""
import argparse
import fnmatch
import json
import subprocess
import sys
import zipfile
from pathlib import Path

NOWIN = 0x08000000 if sys.platform == "win32" else 0


def normal(name, data):
    """The bytes of a file in a form that is the same for the same content."""
    data = bytes(data).replace(b"\r\n", b"\n")
    if name.lower().endswith(".json"):
        try:
            return json.dumps(json.loads(data.decode("utf-8-sig")), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return data
    return data


def read_package(path, strip=""):
    """name -> bytes of an extracted folder or of a zip, with the leading folder `strip` removed."""
    out = {}
    path = Path(path)
    prefix = strip.strip("/") + "/" if strip else ""
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if prefix and name.startswith(prefix):
                    name = name[len(prefix):]
                out[name] = z.read(info)
    elif path.is_dir():
        base = path / strip if strip and (path / strip).is_dir() else path
        for f in sorted(base.rglob("*")):
            if f.is_file() and not f.is_symlink():
                out[f.relative_to(base).as_posix()] = f.read_bytes()
    else:
        raise OSError("not a folder or a zip: " + str(path))
    return out


def read_ref(repo, ref, root):
    """name -> bytes of the files of `root` in the git ref (names relative to root)."""
    run = lambda *a, **k: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, creationflags=NOWIN, **k)  # noqa: E731
    listed = run("ls-tree", "-r", "-z", ref, "--", root)
    if listed.returncode != 0:
        raise OSError("git does not know " + ref + ": " + listed.stderr.decode("utf-8", "replace")[:200])
    names = {}
    for record in listed.stdout.decode("utf-8", "replace").split(chr(0)):
        meta, _, name = record.partition(chr(9))
        parts = meta.split()
        if name and len(parts) == 3 and parts[1] == "blob":
            names[name[len(root) + 1:] if root and name.startswith(root + "/") else name] = parts[2]
    shas = "".join(sha + "\n" for sha in names.values()).encode("ascii")
    done = run("cat-file", "--batch", input=shas)
    if done.returncode != 0:
        raise OSError("git cat-file failed")
    out, at = {}, 0
    for name in names:
        end = done.stdout.index(b"\n", at)
        size = int(done.stdout[at:end].split()[2])
        out[name] = done.stdout[end + 1:end + 1 + size]
        at = end + 1 + size + 1
    return out


def compare(package, reference, ignore=()):
    """(only_in_package, only_in_ref, different) as sorted lists of names."""
    def skipped(name):
        return any(fnmatch.fnmatch(name, pattern) for pattern in ignore)
    a = {k: v for k, v in package.items() if not skipped(k)}
    b = {k: v for k, v in reference.items() if not skipped(k)}
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    different = sorted(k for k in set(a) & set(b) if normal(k, a[k]) != normal(k, b[k]))
    return only_a, only_b, different


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--root", default="monitor")
    ap.add_argument("--strip", default="github_actions_monitor")
    ap.add_argument("--ignore", action="append", default=[])
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)
    try:
        package = read_package(args.path, args.strip)
        reference = read_ref(args.repo, args.ref, args.root)
    except (OSError, zipfile.BadZipFile) as exc:
        print("COMPARE=ERROR " + str(exc))
        return 2
    only_a, only_b, different = compare(package, reference, args.ignore)
    for label, names in (("only in the package", only_a), ("only in the ref", only_b), ("different", different)):
        for name in names:
            print(label + ": " + name)
    ok = not (only_a or only_b or different)
    print("COMPARE=" + ("SAME" if ok else "DIFFERENT") + " files=%d" % len(package))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
