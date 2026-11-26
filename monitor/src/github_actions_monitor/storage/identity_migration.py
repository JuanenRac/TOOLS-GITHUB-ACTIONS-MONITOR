# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Keeps the saved state tied to the identity of the repositories (data_pipeline/repo_identity.py): a document records which owner the data belongs to, and the migration brings older data to it.

  first time      the owner of today is recorded as the owner of every saved record that does not name one; nothing else changes (the marks of the expected red workflows already say "owner/name")
  owner changed   the silences and the alert ledger of repositories, and what the event feed last announced, are set aside (kept in `repo_identity_aside.json`), so that nothing decided about a
                  repository of one owner applies to the repository with the same name of another

`plan` only reads. `apply` first copies every file it is going to change into `identity_backup/<time>/`, so nothing is lost. Running it again changes nothing."""
import json
import time
from pathlib import Path

from github_actions_monitor.app import toolconfig
from github_actions_monitor.data_pipeline import events, repo_identity
from github_actions_monitor.security import private_io
from github_actions_monitor.sentinels import alert_center
from github_actions_monitor.storage import state_io

SCHEMA = 1
HISTORY = 20


def record_file():
    """Beside the silences, so that each account has its own."""
    return Path(alert_center.STATE_FILE).with_name("repo_identity.json")


def aside_file():
    return record_file().with_name("repo_identity_aside.json")


def _load(path):
    try:
        data = state_io.load_json(path)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def recorded():
    data = _load(record_file())
    return data if data and isinstance(data.get("owner"), str) and data["owner"] else None


def _owner(config):
    return toolconfig.github_owner(config).strip().lower()


def _repo_alerts(data):
    """The ids of the ledger rows that are about a repository."""
    seen = data.get("seen") if isinstance(data.get("seen"), dict) else {}
    return {ident for ident, row in seen.items() if isinstance(row, dict) and row.get("repo")}


def _silences_of(data, ids):
    return [e for e in data.get("active") or [] if isinstance(e, dict) and e.get("scope") == "alert" and e.get("value") in ids]


def plan(config):
    """{"ok", "reason": "" | "first" | "owner_changed" | "no_owner", "owner", "was", "items": [{"file", "kind", "action", "records"}]}. Reads only."""
    owner, before = _owner(config), recorded()
    out = {"ok": True, "reason": "", "owner": owner, "was": before["owner"] if before else "", "items": []}
    if not owner:
        out["reason"] = "no_owner"
        return out
    if before and before["owner"] == owner:
        return out
    out["reason"] = "owner_changed" if before else "first"

    def item(path, kind, action, records):
        out["items"].append({"file": str(path), "kind": kind, "action": action, "records": records})
    if before:
        data = _load(alert_center.STATE_FILE) or {}
        ids = _repo_alerts(data)
        if ids:
            item(alert_center.STATE_FILE, "alerts", "set_aside", len(ids) + len(_silences_of(data, ids)))
        if _load(events.STATE_FILE):
            item(events.STATE_FILE, "events", "set_aside", 1)
    return out


def _copy(files, now):
    """Copies the files that are about to change; returns the folder ("" when there was nothing to copy). Raises OSError, so nothing is changed without its copy."""
    found = [(Path(f), _load(f)) for f in files]
    found = [(f, data) for f, data in found if data is not None]
    if not found:
        return ""
    folder = record_file().parent / "identity_backup" / time.strftime("%Y%m%d-%H%M%S", time.gmtime(now))
    folder.mkdir(parents=True, exist_ok=True)
    for path, data in found:
        kept = path.is_file() and not state_io.routed(path)      # a file: byte for byte; kept in the database: its content
        private_io.write_private(folder / path.name, path.read_bytes() if kept else json.dumps(data, ensure_ascii=False))
    return str(folder)


def apply(config, now=None):
    """Does what `plan` says and records the owner. {"ok", "applied", "reason", "backup", "items"}."""
    now = time.time() if now is None else now
    todo = plan(config)
    if todo["reason"] in ("", "no_owner"):
        return {"ok": True, "applied": False, "reason": todo["reason"], "backup": "", "items": []}
    before = recorded()
    was = before["owner"] if before else todo["owner"]
    backup = _copy([row["file"] for row in todo["items"]], now)
    aside = {}
    for row in todo["items"]:
        if row["kind"] == "alerts":
            with alert_center.LOCK:
                data = _load(alert_center.STATE_FILE) or {}
                ids = _repo_alerts(data)
                aside["silences"] = _silences_of(data, ids)
                aside["ledger"] = {i: data["seen"].pop(i) for i in sorted(ids)}
                data["active"] = [e for e in data.get("active") or [] if e not in aside["silences"]]
                state_io.save_text(alert_center.STATE_FILE, json.dumps(data, ensure_ascii=False))
        else:
            aside["events_state"] = _load(events.STATE_FILE)
            state_io.save_text(events.STATE_FILE, "null")      # the feed takes a new first look: nothing of the other owner is announced as fixed
    if aside:
        rows = (_load(aside_file()) or {}).get("rows") or []
        rows = (rows + [dict(aside, owner=was, at=int(now))])[-HISTORY:]
        state_io.save_text(aside_file(), json.dumps({"rows": rows}, ensure_ascii=False))
    previous = (before or {}).get("previous") or []
    if before:
        previous = (previous + [{"owner": before["owner"], "since": before.get("since"), "until": int(now)}])[-HISTORY:]
    state_io.save_text(record_file(), json.dumps({"schema": SCHEMA, "source": repo_identity.GITHUB, "owner": todo["owner"], "since": int(now), "previous": previous}))
    return {"ok": True, "applied": True, "reason": todo["reason"], "backup": backup, "items": todo["items"]}


def tick(config):
    """After a cycle: applies the migration when it is due (once for each owner). A monitor that has not saved anything yet has nothing to bring along."""
    if not record_file().parent.is_dir():
        return
    owner, before = _owner(config), recorded()
    if owner and (before is None or before["owner"] != owner):
        apply(config)


def status(config):
    todo = plan(config)
    return {"ok": True, "record": recorded(), "pending": todo["reason"] in ("first", "owner_changed"), "plan": todo}
