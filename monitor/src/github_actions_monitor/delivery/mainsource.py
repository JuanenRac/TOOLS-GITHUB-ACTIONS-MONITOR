# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Where the monitor reads the CHANGELOG (and the version files) of a local clone: the default branch of the remote, not the working tree.

A clone can sit on an old branch of an agent (20 entries under [Unreleased] where main has 3). The panels A5 and A11 and the delivery signals must say what main says, so the text is read with
`git show origin/<default>:<file>` after checking that the reference exists (no fetch: the monitor never changes a clone). When it cannot be done (no origin, no remote branch, no git) the
working tree is read and a visible note says so: "clone on branch X, not on main" or "no remote branch, counted from the working tree". ONE function counts the entries for the whole monitor.

Rule of the count (unchanged): every list line ("- " or "* ") under `## [Unreleased]`, indented or not, counts as one entry; CRLF and LF are the same.
"""
import os
import re
import subprocess
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
UNRELEASED_RE = re.compile(r"^## \[Unreleased\]\s*\n(.*?)(?=^## \[|\Z)", re.S | re.M)
ENTRY_RE = re.compile(r"^\s*[-*] ", re.M)


def unreleased_count(text):
    """Number of list entries under `## [Unreleased]` of a CHANGELOG text (nested ones count too)."""
    text = str(text or "").replace("\r\n", "\n")
    m = UNRELEASED_RE.search(text)
    return len(ENTRY_RE.findall(m.group(1) if m else ""))


def _git(clone, *args):
    """(ok, output) of one git command in `clone`."""
    try:
        done = subprocess.run(["git", "-C", str(clone), *args], capture_output=True, timeout=20, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return False, ""
    return done.returncode == 0, done.stdout.decode("utf-8", errors="replace")


def current_branch(clone):
    """The branch the clone is on ("" when detached or unknown)."""
    name = _git(clone, "rev-parse", "--abbrev-ref", "HEAD")[1].strip()
    return "" if name == "HEAD" else name


def default_ref(clone):
    """(ref, branch) of the default branch of the remote that the clone knows, e.g. ("origin/main", "main"); ("", "") when it has none."""
    head = _git(clone, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")[1].strip()
    candidates = [head[len("refs/remotes/origin/"):]] if head.startswith("refs/remotes/origin/") else []
    for branch in candidates + ["main", "master"]:
        if _git(clone, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}^{{commit}}")[0]:
            return f"origin/{branch}", branch
    return "", ""


def read_file(clone, name):
    """(text | None, note) of `name` in `clone`, taken from the default branch of the remote. `note` is "" when that was possible; otherwise it says why the working tree was read
    ("clone on branch X, not on main" or "no remote branch known"). text is None when the file does not exist where it was looked for."""
    clone = Path(clone)
    ref, branch = default_ref(clone)
    if ref:
        ok, text = _git(clone, "show", f"{ref}:{name}")
        return (text, "") if ok else (None, "")
    here = current_branch(clone)
    try:
        text = (clone / name).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, ""
    if here and here not in ("main", "master"):
        return text, f"clone on branch {here}, not on main; counted from the working tree"
    return text, "no remote branch known; counted from the working tree"


MAX_WORKFLOWS = 60
MAX_WORKFLOW_BYTES = 1_048_576


def workflow_texts(clone):
    """({file name: text}, note) of the workflow files (`.github/workflows/*.yml|yaml`) of a clone, taken from the default branch of the remote like the CHANGELOG: a clone on an old branch of an agent
    must not make the linter and the scanners judge a workflow that main no longer has. `note` is "" when that was possible, otherwise it says why the working tree was read (same words as
    `read_file`). At most 60 files of 1 MiB; a file that cannot be read is left out."""
    clone = Path(clone)
    ref, _branch = default_ref(clone)
    texts = {}
    if ref:
        ok, listing = _git(clone, "ls-tree", "--name-only", ref, ".github/workflows/")
        for path in sorted(p.strip() for p in listing.split("\n") if p.strip().endswith((".yml", ".yaml")))[:MAX_WORKFLOWS] if ok else ():
            good, text = _git(clone, "show", f"{ref}:{path}")
            if good:
                texts[path.rsplit("/", 1)[-1]] = text[:MAX_WORKFLOW_BYTES]
        return texts, ""
    folder = clone / ".github" / "workflows"
    try:
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml"))[:MAX_WORKFLOWS]
    except OSError:
        return {}, ""
    for path in files:
        try:
            texts[path.name] = path.read_text(encoding="utf-8", errors="replace")[:MAX_WORKFLOW_BYTES]
        except OSError:
            continue
    here = current_branch(clone)
    if here and here not in ("main", "master"):
        return texts, f"clone on branch {here}, not on main; read from the working tree"
    return texts, "no remote branch known; read from the working tree"


def read_changelog(clone):
    """(text | None, note) of the CHANGELOG of a clone; see `read_file`."""
    return read_file(clone, "CHANGELOG.md")


def root_names(clone):
    """Names of the files at the top of the default branch of the remote (of the working tree when that branch is not known)."""
    ref, _ = default_ref(clone)
    if ref:
        ok, out = _git(clone, "ls-tree", "--name-only", ref)
        if ok:
            return out.split("\n")
    try:
        return [p.name for p in Path(clone).iterdir()]
    except OSError:
        return []


def behind_note(clone, remote_oid):
    """A note when the remote branch known by the clone is not the commit GitHub has now (the clone was not fetched), "" when it is the same or when it cannot be told."""
    ref, _ = default_ref(clone)
    if not ref or not remote_oid:
        return ""
    ok, out = _git(clone, "rev-parse", ref)
    if ok and out.strip() and out.strip() != remote_oid:
        return "clone not fetched: counted from the last fetched main"
    return ""
