# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Checks a downloaded release of the monitor (or the folder of a build) without any network: the signature of SHA256SUMS against the release key of the keyring and every file that SHA256SUMS names.

    report = verify_release(folder)
    report["ok"]          True only when the signature is valid and every listed file is present with its SHA-256
    report["signature"]   "valid" | "invalid" | "absent" | "expired" | "revoked" | "unknown_key"
    report["files"]       {name: "ok" | "mismatch" | "missing"}
"""
import hashlib
import re
from pathlib import Path

from github_actions_monitor.security import keyring

SUMS_NAME = "SHA256SUMS"
LINE_RE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]{0,120})\Z")
MAX_SUMS = 64 * 1024


def parse_sums(text):
    """({name: sha256}, [bad line]): only plain file names are taken (never a path), and a name listed twice with two sums is a bad line."""
    found, bad = {}, []
    for line in str(text or "").splitlines():
        if not line.strip():
            continue
        match = LINE_RE.match(line.rstrip())
        if not match or found.get(match.group(2), match.group(1)) != match.group(1):
            bad.append(line[:100])
            continue
        found[match.group(2)] = match.group(1)
    return found, bad


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_release(folder, keys=None, today=None):
    """The report of the folder (see the top of the file). It never raises on what the folder holds."""
    folder = Path(folder)
    report = {"ok": False, "signature": keyring.ABSENT, "key": None, "files": {}, "bad_lines": []}
    sums = folder / SUMS_NAME
    try:
        if not sums.is_file() or sums.stat().st_size > MAX_SUMS:
            return report
        data = sums.read_bytes()
    except OSError:
        return report
    report["signature"], report["key"] = keyring.verify_file(sums, scope="release", keys=keys, today=today)
    listed, report["bad_lines"] = parse_sums(data.decode("ascii", "replace"))
    for name, expected in sorted(listed.items()):
        target = folder / name
        try:
            report["files"][name] = "missing" if not target.is_file() else ("ok" if sha256_of(target) == expected else "mismatch")
        except OSError:
            report["files"][name] = "missing"
    report["ok"] = bool(listed) and report["signature"] == keyring.VALID and not report["bad_lines"] and all(state == "ok" for state in report["files"].values())
    return report
