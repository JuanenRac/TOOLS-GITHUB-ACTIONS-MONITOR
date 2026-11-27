# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A red run set aside by a person for a while (30 days at most by default): it is listed with the expected reds, neither red nor alerted. It covers that run only: the next run of the workflow
counts again, whatever it gives. Kept in a small file of the monitor; nothing is written on GitHub. Standard library only."""
import json
import re
import threading
import time

from github_actions_monitor.util import paths

FILE = "dismissed_runs.json"
MAX_ROWS = 200
DAY = 86400
_LOCK = threading.RLock()
_SEEN = {"mtime": None, "rows": []}


def _path():
    return paths.place(FILE)


def rows(now=None):
    """The marks that have not run out."""
    now = time.time() if now is None else now
    path = _path()
    with _LOCK:
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            _SEEN.update(mtime=None, rows=[])
            return []
        if _SEEN["mtime"] != stamp:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                found = data.get("rows") if isinstance(data, dict) else []
            except (OSError, ValueError):
                found = []
            _SEEN.update(mtime=stamp, rows=[r for r in found or [] if isinstance(r, dict) and isinstance(r.get("repo"), str) and isinstance(r.get("run"), int) and isinstance(r.get("until"), (int, float))])
        return [dict(r) for r in _SEEN["rows"] if r["until"] > now]


def _save(found):
    from github_actions_monitor.storage import file_storage
    file_storage.atomic_write(_path(), json.dumps({"rows": found[-MAX_ROWS:]}, indent=1) + "\n")
    _SEEN["mtime"] = None


def _clean(text, limit):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(text or "")).strip()[:limit]


def dismiss(repo, run_id, who, reason, days, now=None):
    """(mark, "") or (None, "bad_run" | "no_reason" | "no_owner")."""
    now = time.time() if now is None else now
    repo, who, reason = _clean(repo, 140), _clean(who, 60), _clean(reason, 200)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", repo) or not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        return None, "bad_run"
    if not reason:
        return None, "no_reason"
    if not who:
        return None, "no_owner"
    mark = {"repo": repo, "run": run_id, "owner": who, "reason": reason, "at": int(now), "until": int(now + max(1, min(365, int(days))) * DAY)}
    with _LOCK:
        _save([r for r in rows(now) if (r["repo"], r["run"]) != (repo, run_id)] + [mark])
    return mark, ""


def restore(repo, run_id):
    """True when there was a mark for that run."""
    with _LOCK:
        have = rows()
        keep = [r for r in have if (r["repo"], r["run"]) != (repo, run_id)]
        if len(keep) == len(have):
            return False
        _save(keep)
    return True


def lookup(run, now=None):
    """The mark that covers this run, or None."""
    if not isinstance(run, dict):
        return None
    return next((r for r in rows(now) if r["repo"] == run.get("repo") and r["run"] == run.get("id")), None)
