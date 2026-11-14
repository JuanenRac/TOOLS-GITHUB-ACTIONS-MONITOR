# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""ci_red.json: a small snapshot (repository -> workflows in red + hours waiting for the signature) for whoever wants the CI state
without asking the monitor. Written atomically; it never raises and never needs the workspace.

sentinel.ci_red_file in actions_monitor.json:  ""  = ci_red.json next to the monitor (default)
                                               "off" = not written
                                               a path = there (relative paths are relative to the monitor folder; never on D:)
sentinel.ci_red_audit_copy: true also copies it into the audits folder when that folder exists.

FORMAT (schema 2, stable; read it with .get(): fields are only ever added)
  {"schema": 2, "generated": "<UTC time>", "generated_local": "<same moment for people: local date, time, zone and UTC>", "tool_version": "...", "complete": bool,   complete = false while the sentinel is still loading
   "red_repos": N,                                  repositories with at least one workflow in red
   "pending_sign_repos": N,                         repositories with a green build waiting for the local signature / publication (over the threshold)
   "pending_sign_hours_threshold": H,
   "repos": {"<REPO>": {"ecosystem": "armor|urtc|hydra|eh3d|other",
                        "red": [{"workflow", "conclusion", "since", "streak", "url", "ai_hint"}],      A2: last completed run of the workflow on the default branch;
                                                                                                    ai_hint (optional, added in 1.6.4): {"class": "real|transient", "cause", "action"}, for an AI or a script
                        "pending_sign_hours": float|null,                                    the longest wait of the repository (kept from schema 1)
                        "pending_sign": [{"workflow", "hours", "state", "signature_kind": "none|dev|release",
                                          "signature_verified": true|false|"unknown", "last_build_at", "url"}]}}}
The contract for consumers is documented in docs/CI_RED_SCHEMA.md.
"Red" and "green" use ONE definition (signstate.completed_runs): completed, on the default branch, not cancelled/skipped/neutral/stale.
"""
import json
import os
import re
from pathlib import Path

from github_actions_monitor.integrations import ai_alerts
from github_actions_monitor.util import tzdisplay
from github_actions_monitor.tool_version import TOOL_VERSION
from github_actions_monitor.security import private_io

from github_actions_monitor.util import paths
DEFAULT_NAME = "ci_red.json"


SCHEMA = 2
_FOREIGN_DRIVE = re.compile(r"^(?:[A-Za-z]:|/mnt/[A-Za-z](?:/|$)|/[dD](?:/|$))")   # a Windows drive (C:/x, D:\x), WSL (/mnt/d) or Git Bash (/d) path


def build(snapshot):
    repos = {}
    eco = snapshot.get("ecosystems") or {}
    for r in (snapshot.get("a2") or {}).get("red") or []:
        row = repos.setdefault(r["repo"], {"ecosystem": eco.get(r["repo"], "other"), "red": [], "pending_sign_hours": None})
        row["red"].append({"workflow": r.get("workflow"), "conclusion": r.get("conclusion"), "since": r.get("since"), "streak": r.get("streak"), "url": r.get("url"),
                           "ai_hint": ai_alerts.hint({"repo": r["repo"], "workflow": r.get("workflow"), "conclusion": r.get("conclusion"), "streak": r.get("streak"), "since": r.get("since"), "url": r.get("url")})})
    for g in (snapshot.get("a5") or {}).get("pending_sign") or []:
        row = repos.setdefault(g["repo"], {"ecosystem": eco.get(g["repo"], "other"), "red": [], "pending_sign_hours": None})
        row["pending_sign_hours"] = max(row["pending_sign_hours"] or 0, g.get("hours") or 0)
        row.setdefault("pending_sign", []).append({"workflow": g.get("workflow"), "hours": g.get("hours"), "state": g.get("state", "built_on_gha"),
                                                   "signature_kind": g.get("signature_kind", "none"), "signature_verified": g.get("signature_verified", "unknown"),
                                                   "last_build_at": g.get("last_build_at"), "url": g.get("url")})
    for row in repos.values():
        row.setdefault("pending_sign", [])
    return {"schema": SCHEMA, "generated": snapshot.get("generated"), "generated_local": tzdisplay.stamp(snapshot.get("generated")) if snapshot.get("generated") else None, "tool_version": TOOL_VERSION, "complete": not snapshot.get("loading"),
            "red_repos": sum(1 for v in repos.values() if v["red"]), "pending_sign_repos": sum(1 for v in repos.values() if v["pending_sign"]),
            "pending_sign_hours_threshold": (snapshot.get("a5") or {}).get("pending_sign_hours"), "repos": dict(sorted(repos.items()))}


def target_path(setting, base=None, windows=None):
    """None when disabled or when the destination is not allowed. `windows` = None means "this system" (the tests pass True/False)."""
    text = str(setting or "").strip()
    if text.lower() == "off":
        return None
    if text and (text.startswith(("\\\\", "//")) or (_FOREIGN_DRIVE.match(text) and not _own_drive_path(text, os.name == "nt" if windows is None else windows))):
        return None   # a D: drive (a removable drive) on any system, and a drive/UNC path that this system cannot use
    if not text or text == DEFAULT_NAME:
        path = paths.place(DEFAULT_NAME, base)      # ai/ci_red.json: with the rest of what an AI reads
    else:
        path = Path(text)
    if not path.is_absolute():
        path = Path(base or paths.ROOT) / path
    return None if str(path).upper().startswith("D:") else path


def _own_drive_path(text, windows):
    """True when `text` is a drive path that THIS system understands and that is not D: (Windows only)."""
    return windows and re.match(r"^[A-Za-z]:[\\/]", text) is not None and text[0].upper() != "D"


def _write_atomic(path, payload):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    private_io.write_tmp(tmp, json.dumps(payload, ensure_ascii=False, indent=1))
    os.replace(tmp, path)


def export(snapshot, cfg, audit_dir=None, base=None):
    """Writes the file(s); returns the list of paths written ([] when disabled, loading or on any problem)."""
    if not snapshot or snapshot.get("loading") or snapshot.get("enabled") is False:
        return []
    path = target_path((cfg or {}).get("ci_red_file"), base)
    if path is not None and path == paths.place(DEFAULT_NAME, base):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)      # ai/ of a fresh install; any other folder must exist already
        except OSError:
            return []
    written = []
    payload = build(snapshot)
    targets = [path] if path else []
    if path and (cfg or {}).get("ci_red_audit_copy") and audit_dir:
        try:
            if Path(audit_dir).is_dir():
                targets.append(Path(audit_dir) / DEFAULT_NAME)
        except OSError:
            pass
    for target in targets:
        try:
            _write_atomic(target, payload)
            written.append(target)
        except OSError:
            continue
    return written
