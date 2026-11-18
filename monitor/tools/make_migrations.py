#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Builds the REGISTRY OF MIGRATIONS (assets/migrations/*.json) that the updater reads to know what changes between two versions.

  py -3 tools/make_migrations.py [--out assets/migrations] [--work DIR] [--first 1.8.1] [--include-tree] [--keep] [--check]

For every published release from --first on, the zip is downloaded with `gh release download` into a TEMPORARY folder (--work), only src/ is unpacked (names checked), and a throw-away `python -I`
process reads the settings schema and the defaults of THAT release. Two neighbouring releases are compared and one file per version is written:

  <version>.json   {"format": 1, "version", "previous", "settings": {"added", "removed", "changed"}, "digest", "data_schema", "manual": {...}}   (the first one also carries the whole "snapshot")
  launchers.json   the text of every launcher (*.bat, *.sh, *.command) each release shipped, once, so the updater can tell what a person changed in theirs

`manual` comes from assets/migrations/manual.json (the part a person REVIEWS and writes: renamed settings, files that moved, notices about changes of behaviour, steps that need another one first). The
file is the ONLY place where those are written by hand; running the tool again never loses them. A removed setting that has an added setting of the same kind with a similar name is listed in
`rename_candidates` of the report so that it can be reviewed and, if it is a rename, written in manual.json.

  --include-tree  also adds the version of THIS working tree when it is not published yet (the release that will carry the registry)
  --check         writes nothing: exits 1 when the files on disk differ from what the tree and the published releases give (the release gate uses it with --include-tree)

The downloads respect the limits of the API (one release per call, a pause between them) and of the disk (it refuses to start with less than 1 GB free); the temporary folder is deleted at the end unless --keep.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = "JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR"
ZIP_NAME = "github_actions_monitor.zip"
FORMAT = 1
MIN_FREE = 1 << 30
AUTHOR = {"_author": "Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>", "_license": "GPL-3.0-or-later - see LICENSE"}
HEADER_KEYS = ("format", "version", "previous", "settings", "digest", "manual")

PROBE = r'''
import json, re, sys
sys.path.insert(0, sys.argv[1])
from github_actions_monitor.app import settings_api, actions_monitor
def flat(tree, prefix=""):
    out = {}
    for key, value in tree.items():
        path = prefix + key
        if isinstance(value, dict) and value:
            out.update(flat(value, path + "."))
        else:
            out[path] = value
    return out
def bounds(b):
    if b is None:
        return None
    if hasattr(b, "pattern"):
        return {"re": b.pattern}
    if isinstance(b, (tuple, list)):
        return list(b)
    return str(b)
schema = {}
for row in settings_api.SCHEMA:
    tab, key, kind, bnd, restart = row[:5]
    schema[key] = {"kind": kind, "bounds": bounds(bnd)}
defaults = flat(actions_monitor.DEFAULTS)
print(json.dumps({"schema": schema, "defaults": defaults}, sort_keys=True, default=str))
'''


def version_key(text):
    return tuple(int(p) for p in re.findall(r"\d+", text)[:4])


def fail(message):
    raise SystemExit("make_migrations: " + message)


CRLF = chr(13) + chr(10)
LF = chr(10)
LAUNCHER = re.compile(r"^[^/]+/[^/]+\.(bat|sh|command)$")


def safe_unpack(zf, target):
    """Unpacks only src/** and the launchers of the root after checking every name (no absolute path, no .., no drive); returns the product folder."""
    root = None
    for info in zf.infolist():
        name = info.filename
        if name.startswith("/") or ".." in name.split("/") or ":" in name.split("/")[0]:
            fail("unsafe name in the zip: " + name)
        if ("/src/" in "/" + name or LAUNCHER.match(name)) and not name.endswith("/"):
            data = zf.read(info)
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            top = name.split("/")[0]
            root = target / top
    return root


def probe(product):
    """{schema, defaults} of a product folder read by a separate interpreter (the code is our own releases; nothing of it runs in this process)."""
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "probe.py"
        script.write_text(PROBE, encoding="utf-8")
        done = subprocess.run([sys.executable, "-I", str(script), str(product / "src")], capture_output=True, text=True, timeout=180, cwd=tmp)
    if done.returncode != 0:
        return None, done.stderr.strip()[-400:]
    return json.loads(done.stdout), ""


def entry_view(schema, defaults):
    """{key: {"kind", "bounds", "default"}} for every key known by the schema or by the defaults."""
    view = {}
    for key in sorted(set(schema) | set(defaults)):
        item = {}
        if key in schema:
            item["kind"] = schema[key]["kind"]
            if schema[key]["bounds"] is not None:
                item["bounds"] = schema[key]["bounds"]
        if key in defaults:
            item["default"] = defaults[key]
        view[key] = item
    return view


def digest_of(view):
    """Same function as `_digest` of monitor_updater.py (a test keeps them equal): the end anchor of a pattern written one way."""
    flat = {}
    for key, entry in view.items():
        entry = dict(entry)
        bounds = entry.get("bounds")
        if isinstance(bounds, dict) and "re" in bounds:
            entry["bounds"] = {"re": bounds["re"].replace(chr(92) + "Z", "$")}
        flat[key] = entry
    return hashlib.sha256(json.dumps(flat, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _same(a, b):
    """Two entries are the same setting when only the way a pattern ends differs (the end anchor `$` against a backslash Z: one rule written two ways)."""
    def norm(item):
        item = dict(item)
        bounds = item.get("bounds")
        if isinstance(bounds, dict) and "re" in bounds:
            text = bounds["re"]
            text = text.replace(ANCHOR_NEW, ANCHOR_OLD)
            item["bounds"] = {"re": text}
        return item
    return norm(a) == norm(b)


ANCHOR_OLD = "$"
ANCHOR_NEW = chr(92) + "Z"


def diff(old, new):
    added = [{"key": k, **new[k]} for k in sorted(new) if k not in old]
    removed = [{"key": k, **old[k]} for k in sorted(old) if k not in new]
    changed = []
    for k in sorted(set(old) & set(new)):
        if not _same(old[k], new[k]):
            before = {f: old[k].get(f) for f in ("kind", "bounds", "default") if old[k].get(f) != new[k].get(f) and f in old[k]}
            after = {f: new[k].get(f) for f in ("kind", "bounds", "default") if old[k].get(f) != new[k].get(f) and f in new[k]}
            changed.append({"key": k, "old": before, "new": after})
    return {"added": added, "removed": removed, "changed": changed}


def rename_candidates(delta):
    out = []
    for gone in delta["removed"]:
        for came in delta["added"]:
            if gone.get("kind") == came.get("kind") and gone["key"].split(".")[-1] == came["key"].split(".")[-1]:
                out.append((gone["key"], came["key"]))
    return out


def releases(first):
    done = subprocess.run(["gh", "release", "list", "-R", REPO, "--limit", "200", "--json", "tagName"], capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        fail("gh release list failed: " + done.stderr.strip()[-200:])
    tags = [item["tagName"] for item in json.loads(done.stdout)]
    wanted = [t for t in tags if re.fullmatch(r"v\d+(\.\d+){2,3}", t) and version_key(t) >= version_key(first)]
    return sorted(wanted, key=version_key)


def extras_of(product):
    """What is not a setting but the updater needs: the schema number of the database and the text of the launchers (line ends as LF)."""
    text = ""
    path = product / "src" / "github_actions_monitor" / "storage" / "sqlite_storage.py"
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="replace")
    found = re.search(r"^SCHEMA_VERSION\s*=\s*(\d+)", text, re.M)
    launchers = {}
    for item in sorted(product.glob("*")):
        if item.is_file() and item.suffix in (".bat", ".sh", ".command"):
            launchers[item.name] = item.read_bytes().decode("utf-8", "replace").replace(CRLF, LF)
    return {"data_schema": int(found.group(1)) if found else None, "launchers": launchers}


def view_of_release(tag, work, pause):
    folder = work / tag
    zip_path = folder / ZIP_NAME
    if not zip_path.is_file():
        folder.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(["gh", "release", "download", tag, "-R", REPO, "-p", ZIP_NAME, "-D", str(folder), "--clobber"], capture_output=True, text=True, timeout=300)
        if done.returncode != 0:
            fail(f"download of {tag} failed: " + done.stderr.strip()[-200:])
        time.sleep(pause)
    shutil.rmtree(folder / "x", ignore_errors=True)       # our own temporary folder: unpacked again every time
    with zipfile.ZipFile(zip_path) as zf:
        product = safe_unpack(zf, folder / "x")
    if product is None:
        fail(f"{tag}: no src/ in the zip")
    data, error = probe(product)
    if data is None:
        fail(f"{tag}: the schema could not be read: {error}")
    return entry_view(data["schema"], data["defaults"]), extras_of(product)


def view_of_tree():
    data, error = probe(HERE)
    if data is None:
        fail("the schema of this tree could not be read: " + error)
    return entry_view(data["schema"], data["defaults"]), extras_of(HERE)


def tree_version():
    text = (HERE / "src" / "github_actions_monitor" / "tool_version.py").read_text(encoding="utf-8")
    return re.search(r'TOOL_VERSION\s*=\s*"([^"]+)"', text).group(1)


def build(views, manual):
    """views: ordered [(version, view)] -> {version: document}."""
    docs = {}
    previous = None
    previous_view = None
    for version, view, extras in views:
        doc = {**AUTHOR, "format": FORMAT, "version": version, "previous": previous, "digest": digest_of(view), "data_schema": extras["data_schema"]}
        if previous is None:
            doc["snapshot"] = view
            doc["settings"] = {"added": [], "removed": [], "changed": []}
        else:
            doc["settings"] = diff(previous_view, view)
        doc["manual"] = manual.get(version, {})
        docs[version] = doc
        previous, previous_view = version, view
    return docs


def launchers_doc(views):
    """{"files": {sha256: text}, "versions": {version: {name: sha256}}}: every distinct launcher text once, and which text each version shipped."""
    files, versions = {}, {}
    for version, _view, extras in views:
        versions[version] = {}
        for name, text in extras["launchers"].items():
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            files[sha] = text
            versions[version][name] = sha
    return {**AUTHOR, "format": FORMAT, "files": dict(sorted(files.items())), "versions": versions}


def dump(doc):
    return json.dumps(doc, indent=1, sort_keys=False, ensure_ascii=False) + "\n"


def load_manual(out):
    path = out / "manual.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(HERE / "assets" / "migrations"))
    parser.add_argument("--work", default="")
    parser.add_argument("--first", default="1.8.1")
    parser.add_argument("--include-tree", action="store_true")
    parser.add_argument("--tree-version", default="", help="name the working tree with this version (the release that will carry it) instead of TOOL_VERSION")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--pause", type=float, default=1.0)
    args = parser.parse_args(argv)
    out = Path(args.out)
    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="mon_migr_"))
    work.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(work).free < MIN_FREE:
        fail("less than 1 GB free in " + str(work))
    try:
        views = []
        for tag in releases(args.first):
            view, extras = view_of_release(tag, work, args.pause)
            views.append((tag[1:], view, extras))
            print("read", tag, len(view), "settings")
        if args.include_tree:
            version = args.tree_version or tree_version()
            if version not in [v for v, _, _ in views]:
                view, extras = view_of_tree()
                views.append((version, view, extras))
                print("read tree", version, len(view), "settings")
        manual = load_manual(out)
        docs = build(views, manual)
        names = {f"{v}.json" for v in docs}
        launchers = launchers_doc(views)
        if args.check:
            bad = [n for n in sorted(names) if not (out / n).is_file() or (out / n).read_text(encoding="utf-8").replace(CRLF, LF) != dump(docs[n[:-5]])]
            if not (out / "launchers.json").is_file() or (out / "launchers.json").read_text(encoding="utf-8").replace(CRLF, LF) != dump(launchers):
                bad.append("launchers.json")
            if bad:
                print("registry out of date:", ", ".join(bad))
                return 1
            print("registry up to date:", len(names), "files")
            return 0
        out.mkdir(parents=True, exist_ok=True)
        for version, doc in docs.items():
            (out / f"{version}.json").write_text(dump(doc), encoding="utf-8", newline="\n")
        (out / "launchers.json").write_text(dump(launchers), encoding="utf-8", newline="\n")
        previous = None
        for version, doc in docs.items():
            for pair in rename_candidates(doc["settings"]):
                print(f"  rename candidate in {version}: {pair[0]} -> {pair[1]}")
            previous = version
        print("written", len(docs), "files in", out)
        return 0
    finally:
        if not args.keep and not args.work:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
