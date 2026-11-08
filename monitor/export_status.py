# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Explicit, optional exports of what the monitor knows. Nothing here runs by itself and nothing is ever committed or pushed.

  read_report.py --export-status DIR        writes ci_status_public.json (+ .md) into a folder YOU name: ONLY the list of red workflows
                                           (repository, workflow, conclusion, since, streak, run link). No signing state, no key names,
                                           no local paths, no commands. What happens to the folder afterwards is up to you.
  read_report.py --export-sign-queue FILE   writes the global signing queue (.json or .csv by the extension) INCLUDING the exact local
                                           commands: it is for this PC only and says so inside the file.

The public dashboard does not need these files: it recomputes the same red rule itself.
"""
import csv
import io
import json
import os
import re
from pathlib import Path

import ci_red
import i18n
import signstate
from tool_version import TOOL_VERSION

class _Text(dict):
    """TEXT[key] -> the message in the current language (keys are the texts "exp.<key>" of locales/*.json)."""

    def __getitem__(self, key):
        return i18n.t("exp." + key)


TEXT = _Text.fromkeys(("refused", "no_data", "wrote", "md_title", "md_none"), "")
FIELDS = ("name", "repo", "ecosystem", "hours", "step", "signature_kind", "signature_verified", "trust", "attestation", "last_build_at", "run_id", "url", "command")


def public_status(snapshot):
    """The non-sensitive part of the snapshot: red workflows only."""
    eco = snapshot.get("ecosystems") or {}
    rows = [{"repo": r.get("repo"), "ecosystem": eco.get(r.get("repo"), "other"), "workflow": r.get("workflow"), "conclusion": r.get("conclusion"),
             "since": r.get("since"), "streak": r.get("streak"), "url": r.get("url")} for r in (snapshot.get("a2") or {}).get("red") or []]
    return {"schema": 1, "generated": snapshot.get("generated"), "tool_version": TOOL_VERSION, "complete": not snapshot.get("loading"),
            "red_repos": len({r["repo"] for r in rows}), "red": rows}


def public_markdown(status):
    lines = [TEXT["md_title"], ""]
    lines += [f"- {r['repo']} · {r['workflow']} ({r['conclusion']}, {i18n.t('exp.streak')} {r['streak']})" for r in status["red"]] or [TEXT["md_none"]]
    return "\n".join(lines) + "\n"


def allowed_directory(text):
    """None when the destination is refused (D:, UNC, a foreign drive form); the Path otherwise."""
    target = ci_red.target_path(str(text) if text else "off", base=Path.cwd())
    return target


def write_public_status(snapshot, directory):
    """Returns the list of files written, or [] when refused / no data. Never raises for a path problem."""
    if not snapshot or snapshot.get("loading") or snapshot.get("enabled") is False:
        return []
    folder = allowed_directory(directory)
    if folder is None:
        return []
    status = public_status(snapshot)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        out = []
        for name, text in (("ci_status_public.json", json.dumps(status, ensure_ascii=False, indent=1) + "\n"), ("ci_status_public.md", public_markdown(status))):
            tmp = folder / (name + ".tmp")
            tmp.write_text(text, encoding="utf-8", newline="\n")
            os.replace(tmp, folder / name)
            out.append(folder / name)
        return out
    except OSError:
        return []


def sign_queue_rows(snapshot, trust="all"):
    """The signing queue (optionally only the rows whose signature is verified | unknown | failed)."""
    rows = []
    for q in signstate.filter_queue((snapshot.get("a5") or {}).get("sign_queue") or [], trust):
        row = {k: q.get(k) for k in FIELDS}
        row["trust"] = signstate.trust_of(q)
        rows.append(row)
    return rows


def write_sign_queue(snapshot, path, trust="all"):
    """JSON (default) or CSV (.csv). Returns (Path | None, reason): reason is "ok", "no_data" (nothing to say yet), "path" (a drive or network location that is refused), "is_dir" (the
    destination is a folder) or "write: <what the system said>". The caller shows `reason_text(reason)`."""
    if not snapshot or snapshot.get("loading"):
        return None, "no_data"
    target = allowed_directory(path)
    if target is None:
        return None, "path"
    if target.is_dir():
        return None, "is_dir"
    rows = sign_queue_rows(snapshot, trust)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".csv":
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            text = buffer.getvalue()
        else:
            text = json.dumps({"schema": 1, "generated": snapshot.get("generated"), "local_only": True, "queue": rows}, ensure_ascii=False, indent=1) + "\n"
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, target)
        return target, "ok"
    except OSError as error:
        return None, "write: " + (error.strerror or type(error).__name__)[:120]


def reason_text(reason):
    """The sentence (current language) for a reason returned by write_sign_queue."""
    if reason.startswith("write:"):
        return i18n.t("exp.reason_write", error=reason[6:].strip())
    return i18n.t({"no_data": "exp.no_data", "path": "exp.reason_path", "is_dir": "exp.reason_dir"}.get(reason, "exp.refused"))


def contains_sensitive(text):
    """Self-check used by the tests: does an exported text carry anything of the signing side?"""
    return re.search(r"pending_sign|signature_|sign_queue|finalize|[\/~]\.[A-Za-z0-9_-]*(?:keys|armor)", text) is not None
