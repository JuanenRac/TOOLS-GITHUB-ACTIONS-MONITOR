# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Moves the state of an installation from one storage backend to the other (files <-> SQLite). Used by tools/migrate_storage.py.

  * a DRY RUN by default: `plan` only reads and says what would be copied, account by account;
  * the SOURCE IS NEVER CHANGED OR DELETED: the person removes it after checking;
  * every account is copied in ONE step of the target (a SQLite transaction; for files every item is replaced atomically), so an interrupted run leaves each account either whole or as it
    was, and running the same command again resumes: an account that is already identical is skipped, the others are written again;
  * after the copy `verify` reads both sides back and compares them item by item (configuration, every sentinel state, every document, the analytics, EVERY event, the global records) and
    the target's own integrity check; any difference is reported and the run ends with a failure, so nobody switches the backend over a bad copy.
"""
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _count(payload):
    return {"events": len(payload.get("events") or []), "sentinels": len(payload.get("sentinels") or {}), "docs": len(payload.get("docs") or {}),
            "config": bool(payload.get("config")), "analytics": bool(payload.get("analytics")), "scores": len(payload.get("scores") or []),
            "damaged": int(payload.get("damaged_events") or 0)}


def _same(source_payload, target_payload):
    """True when everything in the source payload is in the target one, equal (the target may hold more documents: nothing is removed from it)."""
    if canonical(source_payload.get("config") or {}) != canonical(target_payload.get("config") or {}):
        return False
    if canonical(source_payload.get("analytics") or {}) != canonical(target_payload.get("analytics") or {}):
        return False
    if canonical(source_payload.get("scores") or []) != canonical(target_payload.get("scores") or []):
        return False
    if canonical(source_payload.get("events") or []) != canonical(target_payload.get("events") or []):
        return False
    for part in ("sentinels", "docs"):
        have = target_payload.get(part) or {}
        for name, data in (source_payload.get(part) or {}).items():
            if canonical(data) != canonical(have.get(name)):
                return False
    return True


def _newest(payload):
    """(newest event time, newest score hour) of a payload, as text ('' when there is none)."""
    events = [e.get("at") for e in payload.get("events") or [] if isinstance(e, dict) and isinstance(e.get("at"), str)]
    hours = [s.get("hour") for s in payload.get("scores") or [] if isinstance(s, dict) and isinstance(s.get("hour"), str)]
    return (max(events) if events else "", max(hours) if hours else "")


def _target_is_newer(source_payload, target_payload):
    """True when the target holds an event or a score snapshot that is newer than anything in the source: the account was used after the first copy and a new copy would erase that."""
    have, got = _newest(source_payload), _newest(target_payload)
    return got[0] > have[0] or got[1] > have[1]


def plan(source, target, accounts=None):
    """[{"account", "status", **counts}] for each account of the source (or the ones asked for); status is "new" (not in the target), "differs", "same" or "target_newer"
    (it differs and the target has newer events or snapshots than the source: copying again would replace them)."""
    known = set(target.list_accounts())
    rows = []
    for account in source.list_accounts():
        if accounts and account not in accounts:
            continue
        payload = source.export_account(account)
        if account not in known:
            status = "new"
        else:
            there = target.export_account(account)
            status = "same" if _same(payload, there) else ("target_newer" if _target_is_newer(payload, there) else "differs")
        rows.append({"account": account, "status": status, **_count(payload)})
    return rows


def verify(source, target, accounts=None, records=True):
    """A list of differences between the source and the target (empty = the copy is faithful), plus the integrity problems of the target."""
    problems = []
    target_accounts = set(target.list_accounts())
    for account in source.list_accounts():
        if accounts and account not in accounts:
            continue
        if account not in target_accounts:
            problems.append(f"{account}: missing in the target")
        elif not _same(source.export_account(account), target.export_account(account)):
            problems.append(f"{account}: the target differs from the source")
    if records:
        have = target.export_records()
        for kind, rows in source.export_records().items():
            if canonical(rows) != canonical(have.get(kind, {})):
                problems.append(f"records {kind}: the target differs from the source")
    problems += [f"target: {p}" for p in target.verify()]
    return problems


class _Without:
    """The source seen without some accounts (the refused ones), so the verification does not report them as differences."""

    def __init__(self, source, skip):
        self._source, self._skip = source, set(skip)

    def list_accounts(self):
        return [a for a in self._source.list_accounts() if a not in self._skip]

    def __getattr__(self, name):
        return getattr(self._source, name)


def migrate(source, target, apply=False, accounts=None, force=False):
    """Copies every account (and the global records) of `source` to `target`. Without `apply` it only returns the plan. Returns
    {"applied", "rows", "copied", "skipped", "events", "refused": [accounts], "problems": [..], "verified"}; `problems` holds what failed to copy or to verify. An account whose target is newer
    than the source (`target_newer`) is NOT written unless `force`: it is listed in `refused` and the run does not verify, so nobody loses the data made after the first copy."""
    rows = plan(source, target, accounts)
    out = {"applied": bool(apply), "rows": rows, "copied": 0, "skipped": 0, "events": 0, "refused": [], "problems": [], "verified": False}
    if not apply:
        return out
    for row in rows:
        if row["status"] == "same":
            out["skipped"] += 1
            continue
        if row["status"] == "target_newer" and not force:
            out["refused"].append(row["account"])
            continue
        try:
            target.import_account(row["account"], source.export_account(row["account"]))
            out["copied"] += 1
            out["events"] += row["events"]
        except Exception as error:      # noqa: BLE001 - one account that fails does not stop the others; the run ends as a failure and can be repeated
            out["problems"].append(f"{row['account']}: {type(error).__name__}: {str(error)[:120]}")
    try:
        target.import_records(source.export_records())
    except Exception as error:      # noqa: BLE001
        out["problems"].append(f"records: {type(error).__name__}: {str(error)[:120]}")
    out["problems"] += verify([a for a in out["refused"]] and _Without(source, out["refused"]) or source, target, accounts)
    out["verified"] = not out["problems"] and not out["refused"]
    return out
