# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""This installation against the bill of materials of a release, and the attestations GitHub keeps of it (the last one needs the `gh` client and the network: without them it is "not_checked", never "invalid")."""
import json
import shutil
import subprocess
import os
from pathlib import Path

from github_actions_monitor.security import release_verify
from github_actions_monitor.tool_version import TOOL_VERSION
from github_actions_monitor.util import paths

SPDX_NAME = "github_actions_monitor.spdx.json"
ZIP_NAME = "github_actions_monitor.zip"
REPO = "JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR"
PREFIX = "./github_actions_monitor/"
NO_NETWORK = ("dial tcp", "could not resolve", "no such host", "connection refused", "timeout", "gh auth login", "network")


def compare_installed(folder, root=None, version=TOOL_VERSION):
    """{"ok", "reason", "checked", "changed": [...], "missing": [...]}: every file of the bill of materials of `folder` against the file of this installation. The folder must already be a verified release
    (the caller checks the signature); a bill of materials of another version is refused."""
    result = {"ok": False, "reason": "", "checked": 0, "changed": [], "missing": []}
    root = Path(root or paths.ROOT)
    try:
        document = json.loads((Path(folder) / SPDX_NAME).read_text(encoding="utf-8"))
        product = next(p for p in document["packages"] if p.get("SPDXID") == "SPDXRef-Product")
        files = document["files"]
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return dict(result, reason="no_sbom")
    if product.get("versionInfo") != version:
        return dict(result, reason="other_version")
    for item in files:
        name = str(item.get("fileName") or "")
        if not name.startswith(PREFIX) or ".." in name[len(PREFIX):].split("/"):
            return dict(result, reason="no_sbom")
        relative = name[len(PREFIX):]
        expected = next((c.get("checksumValue") for c in item.get("checksums") or [] if c.get("algorithm") == "SHA256"), "")
        target = root / relative
        result["checked"] += 1
        if not target.is_file():
            result["missing"].append(relative)
        elif release_verify.sha256_of(target) != expected:
            result["changed"].append(relative)
    result["ok"] = bool(result["checked"]) and not result["changed"] and not result["missing"]
    return result


def attestation(folder, runner=None):
    """"verified" | "failed" | "not_checked" for the zip of `folder`."""
    target = Path(folder) / ZIP_NAME
    if not target.is_file() or (runner is None and not shutil.which("gh")):
        return "not_checked"
    runner = runner or (lambda command: subprocess.run(command, capture_output=True, text=True, timeout=120, creationflags=0x08000000 if os.name == "nt" else 0))
    try:
        done = runner(["gh", "attestation", "verify", str(target), "--repo", REPO])
    except (OSError, subprocess.SubprocessError):
        return "not_checked"
    if done.returncode == 0:
        return "verified"
    said = (str(done.stderr or "") + str(done.stdout or "")).lower()
    return "not_checked" if any(word in said for word in NO_NETWORK) else "failed"


def fetch(folder, source=None, version=TOOL_VERSION):
    """Downloads the files of the release of this version into `folder` (only when the person asked and ops.verify_release.fetch is on). Returns the number of files; OSError or ValueError when it cannot."""
    from github_actions_monitor.ops import updates
    updater = updates.module()
    if updater is None:
        raise ValueError("no_updater")
    source = source or updater.GitHubSource()
    release = next((r for r in source.releases() if r["version"] == version), None)
    if release is None:
        raise ValueError("no_release")
    assets, count = release.get("assets") or {}, 0
    for name in ("SHA256SUMS", "SHA256SUMS.ed25519.sig", ZIP_NAME, SPDX_NAME, "github_actions_monitor.cdx.json", "monitor_updater.py"):
        if name in assets:
            source._download(assets[name]["url"], Path(folder) / name, 300 * 1024 * 1024)      # noqa: SLF001 - the checked downloader of the updater (hosts, redirects, size)
            count += 1
    if not count:
        raise ValueError("no_release")
    return count
