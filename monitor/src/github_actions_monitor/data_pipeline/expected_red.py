# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Expected red: a workflow that is KNOWN to be red for a while (a pipeline under construction, a workflow that waits for a fix) is marked with a reason, an owner and an end date.

While the mark lasts, the red of that workflow is neither counted as red nor alerted: it is listed apart as "expected red", with who put it there, why and until when. When the date passes the
workflow is red again at once and one alert says that the mark ran out, until a person removes it or marks it again. This is not a silence by pattern: it names ONE workflow (or all the workflows of one
repository with `*`), it has a reason and an owner, and it can never last longer than `expected_red.max_days` days.

It is a note of this monitor (data/expected_red.json); nothing is written to GitHub. Off by default (`expected_red.enabled`).

  settings(config)                                  enabled (off), max_days (30)
  lookup(repo, workflow, now)                       the entry that covers a red workflow now, or None (the hook that redrule.classify calls)
  add(...), remove(id), entries(now), alerts(...)   the store, the list with each state (active, expired) and the alert of a mark that ran out
"""
import hashlib
import json
import re
import threading
import time

from github_actions_monitor import i18n
from github_actions_monitor.storage import file_storage
from github_actions_monitor.util import paths

FILE = "expected_red.json"
DEFAULTS = {"enabled": False, "max_days": 30}
MAX_ENTRIES = 100
CODE = "ci.expected_red_expired"
_LOCK = threading.RLock()
_SEEN = {"mtime": None, "entries": []}
_CONFIG = {"enabled": False, "max_days": 30}


def settings(config):
    block = (config or {}).get("expected_red") if isinstance(config, dict) else None
    block = block if isinstance(block, dict) else {}
    days = block.get("max_days")
    return {"enabled": block.get("enabled") is True, "max_days": days if isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 365 else DEFAULTS["max_days"]}


def configure(config):
    """Called with the configuration at every cycle (redrule.configure): the hook of redrule only looks at entries while the switch is on."""
    _CONFIG.update(settings(config))


def _path():
    return paths.place(FILE)


def _load():
    path = _path()
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        _SEEN.update(mtime=None, entries=[])
        return _SEEN["entries"]
    if _SEEN["mtime"] != stamp:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data.get("entries") if isinstance(data, dict) else None
            _SEEN["entries"] = [r for r in rows if isinstance(r, dict) and isinstance(r.get("repo"), str) and isinstance(r.get("workflow"), str) and isinstance(r.get("until"), (int, float))] if isinstance(rows, list) else []
        except (OSError, ValueError):
            _SEEN["entries"] = []
        _SEEN["mtime"] = stamp
    return _SEEN["entries"]


def _save(rows):
    file_storage.atomic_write(_path(), json.dumps({"entries": rows}, indent=1, sort_keys=True) + "\n")
    _SEEN["mtime"] = None


def _clean(text, limit):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(text or "")).strip()[:limit]


def entry_id(repo, workflow):
    return hashlib.sha256(f"{repo}\n{workflow}".encode("utf-8")).hexdigest()[:10]


def _matches(entry, repo, workflow):
    if entry["repo"].lower() != str(repo or "").lower():
        return False
    wanted = entry["workflow"].lower()
    return wanted == "*" or wanted == str(workflow or "").lower() or wanted == str(workflow or "").lower().rsplit("/", 1)[-1]


def lookup(repo, workflow, now=None):
    """The entry that covers the red workflow `workflow` (file name or name) of `repo` now, or None: only while the switch is on and the mark has not run out."""
    if not _CONFIG["enabled"]:
        return None
    now = time.time() if now is None else now
    for entry in _load():
        if entry["until"] > now and _matches(entry, repo, workflow):
            return entry
    return None


def entries(now=None):
    """Every mark, each with `id` and `state` (`active` or `expired`), newest end first."""
    now = time.time() if now is None else now
    rows = [{**e, "id": entry_id(e["repo"], e["workflow"]), "state": "active" if e["until"] > now else "expired"} for e in _load()]
    return sorted(rows, key=lambda r: (-r["until"], r["repo"], r["workflow"]))


def add(repo, workflow, reason, owner, days, max_days, now=None):
    """Marks a workflow. Returns (entry, "") or (None, reason of the refusal): bad_repo, bad_workflow, no_reason, no_owner, full. The days are brought into 1..max_days."""
    now = time.time() if now is None else now
    repo, workflow, reason, owner = _clean(repo, 140), _clean(workflow, 120), _clean(reason, 200), _clean(owner, 40)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", repo):
        return None, "bad_repo"
    if not (workflow == "*" or (re.fullmatch(r"[A-Za-z0-9_. /()-]{1,120}", workflow) and ".." not in workflow)):
        return None, "bad_workflow"
    if not reason:
        return None, "no_reason"
    if not owner:
        return None, "no_owner"
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = max_days
    days = max(1, min(max_days, days))
    with _LOCK:
        rows = [e for e in _load() if not (e["repo"].lower() == repo.lower() and e["workflow"].lower() == workflow.lower())]
        if len(rows) >= MAX_ENTRIES:
            return None, "full"
        entry = {"repo": repo, "workflow": workflow, "reason": reason, "owner": owner, "created": int(now), "until": int(now + days * 86400)}
        rows.append(entry)
        _save(rows)
    return {**entry, "id": entry_id(repo, workflow), "state": "active"}, ""


def remove(identifier):
    with _LOCK:
        rows = _load()
        keep = [e for e in rows if entry_id(e["repo"], e["workflow"]) != str(identifier)]
        if len(keep) == len(rows):
            return False
        _save(keep)
        return True


def alerts(account="", now=None):
    """One alert for each mark that ran out and was neither removed nor renewed (`sentinel: "system"`, level warning); [] while the switch is off."""
    if not _CONFIG["enabled"]:
        return []
    now = time.time() if now is None else now
    out = []
    for row in entries(now):
        if row["state"] != "expired":
            continue
        out.append({"id": f"{CODE}:{row['id']}", "code": CODE, "level": "warning", "sentinel": "system", "account_id": account, "repo": row["repo"],
                    "title": i18n.t("expected_red.alert_expired", repo=row["repo"], workflow=row["workflow"], owner=row["owner"], reason=row["reason"]),
                    "details": {"workflow": row["workflow"], "owner": row["owner"], "reason": row["reason"], "until": row["until"]},
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(row["until"]))})
    return out
