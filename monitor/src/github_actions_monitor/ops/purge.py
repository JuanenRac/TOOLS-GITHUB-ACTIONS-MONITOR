# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The purge on demand: the retention purge (`storage/retention.py`) run NOW by an administrator, behind two doors.

  * `ops.purge.enabled` (off by default): while it is off the route does not exist and this module refuses.
  * a good copy newer than `ops.purge.require_backup_hours` (24 by default; 0 = not asked): a purge that removes data is refused without one.

A request is a DRY RUN unless it says otherwise: it returns the policy in force and how many events would be removed or archived, and changes nothing. Under `retention.legal_hold` it is refused (legal_hold). A real purge writes the same line in the audit
document of the retention (`retention_audit`) as the scheduled one, and the route leaves its line in the log of actions.
"""
import time

from github_actions_monitor.ops import opsconf, schedule
from github_actions_monitor.ops.bundle import OpsError
from github_actions_monitor.storage import base, retention

LOAD_MAX = 500000      # more events than this are not counted for the plan (the real purge does not need the count)


def plan(config, storage, account_id, folder=None, now=None):
    """What a purge would do now: the policy, the cutoff, how many events would go and whether the copy that is asked for exists."""
    now = time.time() if now is None else now
    policy = retention.effective(config)
    before, analytics_before = retention.cutoffs(policy, now)
    stats = storage.event_stats(account_id)
    would = None
    if stats["count"] <= LOAD_MAX:
        would = sum(1 for event in storage.load_events(account_id, limit=None) if base.event_ts(event) and base.event_ts(event) < before)
    age = schedule.age_days(folder, now)
    need = opsconf.settings(config)["purge"]["require_backup_hours"]
    return {"policy": {"events_days": policy["events_days"], "analytics_days": policy["analytics_days"], "mode": policy["mode"]}, "events_before": before, "analytics_before": analytics_before,
            "events": stats["count"], "would_remove": would, "backup_required_hours": need, "backup_age_hours": None if age is None else round(age * 24, 1),
            "backup_ok": need == 0 or (age is not None and age * 24 <= need)}


def run(config, storage, account_id, folder=None, now=None, dry_run=True):
    """The plan (dry run) or the purge itself. Raises OpsError: purge_off, purge_no_backup."""
    if not opsconf.settings(config)["purge"]["enabled"]:
        raise OpsError("purge_off")
    now = time.time() if now is None else now
    found = plan(config, storage, account_id, folder, now)
    if dry_run:
        return {"dry_run": True, **found}
    if retention.held(config):
        raise OpsError("legal_hold")
    if not found["backup_ok"]:
        raise OpsError("purge_no_backup")
    line = retention.run(storage, account_id, retention.effective(config), now, config=config)
    return {"dry_run": False, **found, "line": line}
