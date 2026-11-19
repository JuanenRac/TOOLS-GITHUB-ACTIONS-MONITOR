# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Retention and rotation of the event feed and the analytics, so a monitor that runs for months as a service does not grow without a ceiling.

Settings (the `retention` block of the configuration; every one is read through `settings`, which clamps it, so a hand-edited value can never switch the safeguards off by accident):

    retention.enabled         true   the purge runs; false = nothing is ever removed by age
    retention.events_days     90     events older than this are removed (or archived)
    retention.analytics_days  180    days of the analytics history older than this are removed
    retention.mode            archive | delete   (default archive)  archive = the old events are first written to a .gz outside the hot path (events/archive/ of the account), then removed
    retention.events_max_kb   512    the ceiling in bytes of the feed FILE (the file backend): the feed is cut to its newest half beyond it, as it always was
    retention.interval_hours  24     how often the purge runs (a tick of maintenance checks the clock; the purge itself is one short pass)
    retention.warn_events_mb  20     `--doctor` warns when the events of an account are bigger than this

A retention shorter than the longest window that reads it (the comparison of periods for the events, `analytics.keep_days` for the analytics) is raised to that window when the purge runs
(`effective`) and the doctor says so: nothing is purged that a window still needs.

What a purge touches: ONLY events older than the limit and days of the analytics older than its limit. It never touches the configuration, the state of the sentinels or the small
documents (the silences, what the feed announced, the update notice) and it never removes an event that has no time. Each pass leaves a line in the audit document `retention_audit`
(when, how many events removed and kept, the archive file, how many days of analytics, the mode, an error if there was one); the last AUDIT_KEEP are kept.
"""
import os
import time

from github_actions_monitor.util import clock
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULTS = {"enabled": True, "events_days": 90, "analytics_days": 180, "mode": "archive", "events_max_kb": 512, "interval_hours": 24, "warn_events_mb": 20}
BOUNDS = {"events_days": (1, 3650), "analytics_days": (1, 3650), "events_max_kb": (64, 1048576), "interval_hours": (1, 168), "warn_events_mb": (1, 100000)}
MODES = ("delete", "archive")
AUDIT_KEEP = 50
AUDIT_DOC = "retention_audit"


def settings(config):
    """The `retention` block as clean values: anything missing, of the wrong type or out of range reads as the default (a bool is not a number)."""
    block = config.get("retention") if isinstance(config, dict) and isinstance(config.get("retention"), dict) else {}
    out = dict(DEFAULTS)
    if isinstance(block.get("enabled"), bool):
        out["enabled"] = block["enabled"]
    if block.get("mode") in MODES:
        out["mode"] = block["mode"]
    for key, (low, high) in BOUNDS.items():
        value = block.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high:
            out[key] = int(value)
    return out


def floors(config):
    """{setting: days} the retention may not go below: the feed of events must reach back as far as the window of the comparison needs (two of its windows and a day, while it is on) and the days of
    the analytics must reach as far as `analytics.keep_days`. Purging earlier than a window reads would make that window quietly show less than it says."""
    out = {"events_days": 0, "analytics_days": 0}
    try:
        from github_actions_monitor.compare import config as compare_config
        cfg = compare_config.settings(config)
        out["events_days"] = 2 * max(cfg["default_window_days"], 7) + 1 if cfg["enabled"] else 0
    except Exception:   # noqa: BLE001 - a floor that cannot be worked out is no floor
        pass
    try:
        from github_actions_monitor.data_pipeline import analytics
        out["analytics_days"] = int(analytics.settings(config)["keep_days"])
    except Exception:   # noqa: BLE001
        pass
    return out


def effective(config):
    """`settings` with the retention raised to the longest window that reads it (see `floors`): what the purge really uses. `raised` = {setting: {"asked", "now"}} of what was raised."""
    out = settings(config)
    out["raised"] = {}
    for key, floor in floors(config).items():
        if out[key] < floor:
            out["raised"][key] = {"asked": out[key], "now": floor}
            out[key] = floor
    return out


def configured(config):
    """True when the configuration carries a `retention` block of its own (the doctor asks this of a monitor that runs as a service)."""
    return isinstance(config, dict) and isinstance(config.get("retention"), dict) and bool(config["retention"])


def service_mode(config, env=None):
    """True for a monitor that is left running without a person at the page: it listens on the network, does not open a browser, runs in a container or says so (MONITOR_SERVICE)."""
    env = os.environ if env is None else env
    config = config if isinstance(config, dict) else {}
    listen = config.get("listen") if isinstance(config.get("listen"), dict) else {}
    return bool(listen.get("network") is True or config.get("open_browser") is False or str(env.get("MONITOR_SERVICE", "")).strip() not in ("", "0")
                or Path("/.dockerenv").exists())


def _stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def cutoffs(cfg, now=None):
    """(events cutoff as the text of `at`, analytics cutoff as 'YYYY-MM-DD') for the settings `cfg` at the moment `now` (epoch seconds)."""
    moment = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc)
    return _stamp(moment - timedelta(days=cfg["events_days"])), (moment - timedelta(days=cfg["analytics_days"])).strftime("%Y-%m-%d")


def audit(storage, account_id):
    """The audit document ({"last_run", "last_run_epoch", "runs": [...]}); empty values when there was no pass yet."""
    doc = storage.load_doc(account_id, AUDIT_DOC, None)
    return doc if isinstance(doc, dict) and isinstance(doc.get("runs"), list) else {"last_run": "", "last_run_epoch": 0, "runs": []}


def run(storage, account_id, cfg, now=None):
    """One pass for one account with the settings `cfg` (from `settings`). Returns the audit line it wrote. A failure is recorded in the line (`error`) and never raised."""
    now = time.time() if now is None else now
    events_before, analytics_before = cutoffs(cfg, now)
    line = {"at": _stamp(datetime.fromtimestamp(now, timezone.utc)), "mode": cfg["mode"], "events_removed": 0, "events_kept": 0, "archived": "", "analytics_removed": 0, "scores_removed": 0, "error": ""}
    try:
        archive_dir = storage.archive_dir(account_id) if cfg["mode"] == "archive" else None
        result = storage.purge_events(account_id, events_before, archive_dir=archive_dir)
        line.update(events_removed=result["removed"], events_kept=result["kept"], archived=Path(result["archived"]).name if result["archived"] else "")
        line["analytics_removed"] = storage.purge_analytics(account_id, analytics_before)["removed"]
        line["scores_removed"] = storage.purge_score_snapshots(account_id, analytics_before + "T00")["removed"]
    except Exception as error:      # noqa: BLE001 - a purge that cannot run is said in the audit; the monitor goes on
        line["error"] = f"{type(error).__name__}: {str(error)[:120]}"
    doc = audit(storage, account_id)
    doc.update(last_run=line["at"], last_run_epoch=now, runs=(doc["runs"] + [line])[-AUDIT_KEEP:])
    try:
        storage.save_doc(account_id, AUDIT_DOC, doc)
    except Exception as error:      # noqa: BLE001
        line["error"] = line["error"] or f"audit: {type(error).__name__}"
    return line


def due(storage, account_id, cfg, now=None):
    now = time.time() if now is None else now
    last = float(audit(storage, account_id).get("last_run_epoch") or 0)
    return cfg["enabled"] and (clock.in_future(last, now) or now - last >= cfg["interval_hours"] * 3600)      # a last run in the future (clock set back) is due now: the pass writes a good moment


def tick(storage, account_id, config, now=None):
    """The tick of maintenance: runs a pass when retention is on and the interval has passed. Returns the audit line, or None when nothing was due. Cheap when nothing is due."""
    cfg = effective(config)
    if not due(storage, account_id, cfg, now):
        return None
    return run(storage, account_id, cfg, now)


def report(storage, account_id, config):
    """What the doctor and the page show: the settings, the size of the feed and the last pass."""
    cfg = settings(config)
    stats = storage.event_stats(account_id)
    last = (audit(storage, account_id)["runs"] or [{}])[-1]
    return {"settings": cfg, "configured": configured(config), "events": stats, "last": last}
