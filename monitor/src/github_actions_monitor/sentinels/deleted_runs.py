# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Runs that were deleted after the monitor saw them (the `security.runs_deleted` signal of the Security sentinel).

After a leak of secrets, deleting the run that printed them is the usual way to remove the trace, and GitHub leaves no visible record of it for the owner. The monitor already looks at the runs of every
repository, so it keeps a short, private list of the runs it saw that matter (a push to the default branch, a manual run, a run of a `pull_request_target`) and, when one of them is no longer in the list,
asks for that single run: an explicit 404 means it was deleted. Anything else (403, a network error, a 5xx) is NOT a deletion and is not counted. A run older than the check window is not asked for at
all: it may have been purged by the retention of the account, which is not a trace removed by somebody.

Pure functions over plain data: the sentinel reads GitHub and stores the result. A run is kept as [id, workflow, actor, branch, event, created (epoch seconds)].
"""
from datetime import datetime, timezone

SENSITIVE_EVENTS = ("workflow_dispatch", "pull_request_target")
KEEP = 40                                  # runs remembered per repository (the newest sensitive ones)
DELETED_KEEP = 20                          # deletions remembered per repository
WINDOW_DAYS, MAX_CHECKS = 14, 50           # defaults of `check_window_days` and `max_checks`


def created_epoch(run):
    try:
        return datetime.strptime(str(run.get("created_at") or ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def is_sensitive(run, default_branch):
    """A manual run, a run of `pull_request_target`, or a push to the default branch."""
    event = str(run.get("event") or "")
    return event in SENSITIVE_EVENTS or (event == "push" and bool(default_branch) and run.get("head_branch") == default_branch)


def _row(run):
    who = run.get("triggering_actor") or run.get("actor")
    actor = who.get("login") if isinstance(who, dict) else ""
    return [int(run["id"]), str(run.get("name") or run.get("path") or "")[:80], str(actor or "")[:40], str(run.get("head_branch") or "")[:80], str(run.get("event") or "")[:30], created_epoch(run)]


def observe(seen, runs, default_branch, now, window_s):
    """(new seen list, ids of the runs of this list): the sensitive runs of the list are added, what is older than the window is dropped, and at most KEEP of the newest stay."""
    listed = {int(r["id"]) for r in runs if isinstance(r, dict) and isinstance(r.get("id"), int)}
    known = {row[0]: row for row in seen if isinstance(row, list) and len(row) == 6}
    for run in runs:
        if isinstance(run, dict) and isinstance(run.get("id"), int) and is_sensitive(run, default_branch) and created_epoch(run) >= now - window_s:
            known.setdefault(run["id"], _row(run))
    rows = [row for row in known.values() if row[5] >= now - window_s]
    rows.sort(key=lambda row: row[5], reverse=True)
    return rows[:KEEP], listed


def to_check(seen, listed, max_checks):
    """The remembered runs that are no longer in the list, the newest first, at most `max_checks`: the ones to ask for one by one."""
    return [row for row in seen if row[0] not in listed][:max(0, max_checks)]


def stamp(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def deleted_record(row, now):
    return {"id": row[0], "workflow": row[1], "actor": row[2], "branch": row[3], "event": row[4], "created": stamp(row[5]), "noticed": stamp(now), "at": now}


def update(seen, deleted_before, runs, default_branch, now, window_days, max_checks, ask):
    """One pass over one repository. `ask(run_id)` answers the HTTP status of the single run (200, 404, ...) and may raise. Returns (seen, deleted, checks made).
    A run that answers 200 is alive (it only left the list) and is forgotten; a 404 is a deletion and is recorded; anything else keeps the run for the next pass."""
    window = max(1, int(window_days)) * 86400
    seen, listed = observe(seen, runs, default_branch, now, window)
    deleted = [d for d in (deleted_before or []) if isinstance(d, dict) and now - float(d.get("at") or 0) < window]
    checks, gone, alive = 0, set(), set()
    for row in to_check(seen, listed, max_checks):
        try:
            status = ask(row[0])
        except Exception:      # noqa: BLE001 - a read that fails is not a deletion
            continue
        checks += 1
        if status == 404:
            gone.add(row[0])
            deleted.append(deleted_record(row, now))
        elif status == 200:
            alive.add(row[0])
    seen = [row for row in seen if row[0] not in gone and row[0] not in alive]
    return seen, deleted[-DELETED_KEEP:], checks


def detail(deleted):
    """What the alert says: how many, and the last one (workflow, who triggered it, branch)."""
    last = deleted[-1]
    return {"n": len(deleted), "workflow": last.get("workflow", ""), "actor": last.get("actor", ""), "branch": last.get("branch", ""), "noticed": last.get("noticed", "")}
