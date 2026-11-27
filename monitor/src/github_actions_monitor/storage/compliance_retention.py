# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One table of every category of data the monitor keeps and how long: each with its days, and every purge written in the log of actions. Standard library only.

Events, analytics and scores keep their own settings (storage/retention.py). The categories added here are kept FOR EVER unless a number of days is set (0 = never purged by age):

  retention.audit_days     the rotated files of the log of actions, whole files only, with a signed mark of where the chain goes on
  retention.reports_days   the report files written by the monitor (the newest report of each account stays)
  retention.ai_log_days    the lines of the optional record of prompts
  retention.backups_days   the copies of the installation (the newest copy stays)

A category with no policy is never purged: the doctor and the compliance report name it. Under `retention.legal_hold` nothing at all is removed."""
import json
import os
import time
from pathlib import Path

from github_actions_monitor.storage import retention

NEW_DAYS = ("audit_days", "reports_days", "ai_log_days", "backups_days")
BOUNDS = (0, 3650)
STATE_NAME = "compliance_state.json"
#: (category, setting that limits it or "", how it ends)
CATEGORIES = (
    ("events", "retention.events_days", "age"), ("analytics", "retention.analytics_days", "age"), ("scores", "retention.analytics_days", "age"),
    ("reports", "retention.reports_days", "age_and_count"), ("audit", "retention.audit_days", "age_and_count"), ("ai_log", "retention.ai_log_days", "age_and_count"),
    ("backups", "retention.backups_days", "age_and_count"), ("proposals", "", "expire_by_themselves"), ("devices", "", "kept_until_revoked"),
    ("postmortems", "", "not_kept_by_this_version"), ("incidents", "", "not_kept_by_this_version"), ("notes", "", "not_kept_by_this_version"),
)


def days(config):
    block = config.get("retention") if isinstance(config, dict) and isinstance(config.get("retention"), dict) else {}
    out = {}
    for key in NEW_DAYS:
        value = block.get(key)
        out[key] = int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and BOUNDS[0] <= value <= BOUNDS[1] else 0
    return out


def policy(config):
    """[{"category", "days" (0 = no purge by age), "setting", "how", "mode"}] of every category."""
    base_cfg, extra = retention.settings(config), days(config)
    out = []
    for name, setting, how in CATEGORIES:
        key = setting.split(".")[-1] if setting else ""
        value = base_cfg.get(key) if key in base_cfg else extra.get(key, 0)
        if name in ("events", "analytics", "scores") and not base_cfg["enabled"]:
            value = 0
        out.append({"category": name, "days": value or 0, "setting": setting, "how": how, "mode": base_cfg["mode"] if name == "events" else "delete"})
    return out


def without_policy(config):
    """The categories that grow and are not purged by age."""
    return [row["category"] for row in policy(config) if row["setting"] and not row["days"]]


def purge_files(folder, pattern, before, group=lambda path: "all"):
    """Removes the files of `folder` that match `pattern` and are older than `before`, never the newest of each group. Returns how many."""
    folder = Path(folder)
    if not folder.is_dir():
        return 0
    groups = {}
    for path in folder.glob(pattern):
        if path.is_file():
            groups.setdefault(group(path), []).append((path.stat().st_mtime, path.name, path))
    removed = 0
    for items in groups.values():
        newest = max(item[0] for item in items)
        for stamp, _name, path in items:
            if stamp < before and stamp < newest:
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    continue
    return removed


def purge_lines(path, before):
    """Removes from a JSON-lines record (an "at" in epoch seconds in each line) the lines older than `before`. Returns how many."""
    from github_actions_monitor.security import private_io
    from github_actions_monitor.storage import locks
    path = Path(path)
    if not path.is_file():
        return 0
    with locks.os_lock(path, 5.0):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        keep = []
        for line in lines:
            try:
                at = json.loads(line).get("at")
            except (ValueError, AttributeError):
                at = None
            if not isinstance(at, (int, float)) or at >= before:      # a line with no time is never removed
                keep.append(line)
        if len(keep) == len(lines):
            return 0
        tmp = Path(str(path) + ".tmp")
        private_io.write_tmp(tmp, "".join(line + "\n" for line in keep))
        os.replace(tmp, path)
    return len(lines) - len(keep)


def _places(config):
    from github_actions_monitor.integrations import ai_prompt_log
    from github_actions_monitor.ops import opsconf
    from github_actions_monitor.reporting import report_service
    return {"reports": report_service.folder(None), "ai_log": Path(ai_prompt_log.LOG_FILE), "backups": opsconf.backup_dir(config, None)}


def run(config, now=None, places=None):
    """One pass over the categories added here. Returns {category: removed}. Each category that removed something leaves its line in the log of actions."""
    from github_actions_monitor.security import audit_log, compliance_checkpoints
    now = time.time() if now is None else now
    if retention.held(config):
        return {}
    limits = days(config)
    removed = {}
    if limits["audit_days"]:
        found = compliance_checkpoints.purge(config, now - limits["audit_days"] * 86400, now=now)
        removed["audit"] = found["entries"]
    wanted = {name: limits[name + "_days"] for name in ("reports", "ai_log", "backups") if limits[name + "_days"]}
    if wanted:
        places = places or _places(config)
        for name, kept_days in wanted.items():
            before = now - kept_days * 86400
            if name == "reports":
                from github_actions_monitor.reporting import report_service
                removed[name] = purge_files(places[name], "report_*", before, group=lambda p: (report_service.NAME_RE.match(p.name) or [p.name, p.name])[1] + p.suffix)
            elif name == "backups":
                from github_actions_monitor.ops import bundle
                removed[name] = purge_files(places[name], "*", before, group=lambda p: "copy" if bundle.NAME_RE.match(p.name) else "other:" + p.name)
            else:
                removed[name] = purge_lines(places[name], before)
    for name, count in removed.items():
        if count and name != "audit":      # the purge of the log writes its own line
            audit_log.record(config, "retention_purge", target=name, details={"removed": count, "days": limits[name + "_days"]}, now=now)
    return removed


def tick(config, now=None, state_file=None):
    """Once per `retention.interval_hours`. Returns what `run` returned, or None when nothing was due or no category here has a limit."""
    from github_actions_monitor.security import private_io
    from github_actions_monitor.util import paths
    now = time.time() if now is None else now
    if not any(days(config).values()):
        return None
    where = Path(state_file) if state_file else paths.place(STATE_NAME)
    try:
        last = float(json.loads(where.read_text(encoding="utf-8")).get("retention_at") or 0)
    except (OSError, ValueError, AttributeError, TypeError):
        last = 0
    if 0 <= now - last < retention.settings(config)["interval_hours"] * 3600:
        return None
    removed = run(config, now)
    private_io.private_dir(where.parent)
    private_io.write_private(where, json.dumps({"retention_at": now, "removed": removed}))
    return removed
