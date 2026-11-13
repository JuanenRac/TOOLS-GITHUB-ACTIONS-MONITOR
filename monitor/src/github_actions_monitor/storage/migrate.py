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
            "config": bool(payload.get("config")), "analytics": bool(payload.get("analytics"))}


def _same(source_payload, target_payload):
    """True when everything in the source payload is in the target one, equal (the target may hold more documents: nothing is removed from it)."""
    if canonical(source_payload.get("config") or {}) != canonical(target_payload.get("config") or {}):
        return False
    if canonical(source_payload.get("analytics") or {}) != canonical(target_payload.get("analytics") or {}):
        return False
    if canonical(source_payload.get("events") or []) != canonical(target_payload.get("events") or []):
        return False
    for part in ("sentinels", "docs"):
        have = target_payload.get(part) or {}
        for name, data in (source_payload.get(part) or {}).items():
            if canonical(data) != canonical(have.get(name)):
                return False
    return True


def plan(source, target, accounts=None):
    """[{"account", "status", **counts}] for each account of the source (or the ones asked for); status is "new" (not in the target), "differs" or "same"."""
    known = set(target.list_accounts())
    rows = []
    for account in source.list_accounts():
        if accounts and account not in accounts:
            continue
        payload = source.export_account(account)
        if account not in known:
            status = "new"
        else:
            status = "same" if _same(payload, target.export_account(account)) else "differs"
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


def migrate(source, target, apply=False, accounts=None):
    """Copies every account (and the global records) of `source` to `target`. Without `apply` it only returns the plan. Returns
    {"applied", "rows", "copied", "skipped", "events", "problems": [..], "verified"}; `problems` holds what failed to copy or to verify."""
    rows = plan(source, target, accounts)
    out = {"applied": bool(apply), "rows": rows, "copied": 0, "skipped": 0, "events": 0, "problems": [], "verified": False}
    if not apply:
        return out
    for row in rows:
        if row["status"] == "same":
            out["skipped"] += 1
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
    out["problems"] += verify(source, target, accounts)
    out["verified"] = not out["problems"]
    return out
