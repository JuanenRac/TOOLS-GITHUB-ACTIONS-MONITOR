# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The copy on a schedule, its rotation and the state the doctor and the page read.

`tick` is the maintenance tick (the same pattern as the retention): with `ops.backup.enabled` OFF (the default) it does nothing; ON, it makes a package every `ops.backup.interval_hours`, keeps the
newest `ops.backup.keep` of them and leaves the result in `data/ops/backup_status.json`. Only one process makes the copy at a time (a lock file), and a failure (a full disk, a missing key) is written
to the state and counted; it NEVER stops the monitor. A copy made by hand (`monitor_cli.py backup create`, the page) goes through `run` as well, so the state is the same.
"""
import json
import threading
import time
from datetime import datetime, timezone

from github_actions_monitor.ops import bundle, opsconf
from github_actions_monitor.ops.bundle import OpsError
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import locks

STATUS = "backup_status.json"
RUNS_KEPT = 10
RUNNING = threading.Lock()      # one copy at a time inside this process; the lock file of `tick` and `run_locked` does the same between processes


def _iso(moment):
    return datetime.fromtimestamp(moment, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_status(folder=None):
    try:
        data = json.loads((opsconf.ops_dir(folder) / STATUS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data = data if isinstance(data, dict) else {}
    return {"ok": data.get("ok"), "last_ok": str(data.get("last_ok") or ""), "last_ok_epoch": float(data.get("last_ok_epoch") or 0), "last_attempt": str(data.get("last_attempt") or ""),
            "last_attempt_epoch": float(data.get("last_attempt_epoch") or 0), "error": str(data.get("error") or ""), "file": str(data.get("file") or ""), "bytes": int(data.get("bytes") or 0),
            "sealed": data.get("sealed") is True, "accounts": int(data.get("accounts") or 0), "events": int(data.get("events") or 0), "failures": int(data.get("failures") or 0),
            "runs": data.get("runs") if isinstance(data.get("runs"), list) else []}


def _save(folder, status):
    target = opsconf.ops_dir(folder)
    target.mkdir(parents=True, exist_ok=True)
    private_io.write_private(target / STATUS, json.dumps(status, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def list_backups(config=None, folder=None):
    """The copies in the folder of the copies, newest first: [{"name", "bytes", "at", "epoch", "sealed"}]. Only files with the name of a copy are listed."""
    out = []
    try:
        for item in opsconf.backup_dir(config, folder).iterdir():
            if bundle.NAME_RE.match(item.name) and item.is_file():
                info = item.stat()
                out.append({"name": item.name, "bytes": info.st_size, "at": _iso(info.st_mtime), "epoch": info.st_mtime, "sealed": item.name.endswith(".enc")})
    except OSError:
        return []
    return sorted(out, key=lambda row: (row["epoch"], row["name"]), reverse=True)


def rotate(config=None, folder=None):
    """Removes the oldest copies beyond `ops.backup.keep` (only files with the name of a copy). Returns the names removed."""
    keep = opsconf.settings(config)["backup"]["keep"]
    removed = []
    for row in list_backups(config, folder)[keep:]:
        try:
            (opsconf.backup_dir(config, folder) / row["name"]).unlink()
            removed.append(row["name"])
        except OSError:
            continue
    return removed


def run(config=None, folder=None, inst=None, now=None, env=None, dest=None, **options):      # options: encrypt, key_env, include_config, level, account
    """Makes one copy now and records the result. Returns the state. Never raises: an error is in the state (`error` is the stable code)."""
    now = time.time() if now is None else now
    status = read_status(folder)
    status["last_attempt"], status["last_attempt_epoch"] = _iso(now), now
    owned = inst is None
    try:
        inst = inst or bundle.open_installation(config, folder)
        target = dest or opsconf.backup_dir(config, folder)
        made = bundle.create(inst, target, config=config, folder=folder, env=env, now=now, into_dir=dest is None, **options)
        manifest = made["manifest"]
        status.update(ok=True, last_ok=_iso(now), last_ok_epoch=now, error="", file=made["path"].replace("\\", "/").rsplit("/", 1)[-1], bytes=made["bytes"], sealed=made["sealed"],
                      accounts=manifest.get("accounts", 0), events=manifest.get("events", 0))
        if dest is None:
            rotate(config, folder)
    except OpsError as error:
        status.update(ok=False, error=error.code, failures=status["failures"] + 1)
    except Exception as error:   # noqa: BLE001 - a copy that cannot be made is said in the state; the monitor goes on
        status.update(ok=False, error="failed", failures=status["failures"] + 1)
        status["detail"] = f"{type(error).__name__}: {str(error)[:120]}"
    finally:
        if owned and inst is not None:
            try:
                inst.close()
            except Exception:   # noqa: BLE001
                pass
    status["runs"] = (status["runs"] + [{"at": _iso(now), "ok": status["ok"], "error": status["error"]}])[-RUNS_KEPT:]
    try:
        _save(folder, status)
    except OSError:
        status["saved"] = False
    return status


def due(config, folder=None, now=None):
    cfg = opsconf.settings(config)["backup"]
    if not cfg["enabled"]:
        return False
    now = time.time() if now is None else now
    last = read_status(folder)["last_attempt_epoch"]
    return last > now or now - last >= cfg["interval_hours"] * 3600      # a last attempt in the future (the clock set back) is due now


def tick(config, folder=None, now=None, env=None):
    """The tick of maintenance. Returns the state after a copy, or None when nothing was due (the usual case, and always while the schedule is off)."""
    if not due(config, folder, now) or not RUNNING.acquire(blocking=False):
        return None
    try:
        with locks.os_lock(opsconf.ops_dir(folder) / "backup", timeout=1.0):
            if not due(config, folder, now):      # another process of the installation did it while this one waited
                return None
            return run(config, folder, now=now, env=env)
    except (TimeoutError, OSError):
        return None
    finally:
        RUNNING.release()


def run_locked(config, folder=None, **options):
    """A copy asked for by a person (the page, the API): the same as `run`, but refused ({"ok": False, "error": "busy"}) while another copy is being made in this process or another."""
    if not RUNNING.acquire(blocking=False):
        return {**read_status(folder), "ok": False, "error": "busy"}
    try:
        with locks.os_lock(opsconf.ops_dir(folder) / "backup", timeout=1.0):
            return run(config, folder, **options)
    except (TimeoutError, OSError):
        return {**read_status(folder), "ok": False, "error": "busy"}
    finally:
        RUNNING.release()


def overview(config, folder=None, now=None):
    """What the page and `GET /api/ops/status` show: the mode, the last copy, the schedule, the purge switch, the retention policy in force and the report of the last restore. No path, no secret."""
    from github_actions_monitor.ops import restore, sealing
    from github_actions_monitor.storage import retention
    cfg = opsconf.settings(config)
    state = read_status(folder)
    age = age_days(folder, now)
    policy = retention.settings(config)
    last = restore.last_report(folder)
    return {"schema": 1, "mode": "service" if retention.service_mode(config) else "local",
            "backup": {"enabled": cfg["backup"]["enabled"], "interval_hours": cfg["backup"]["interval_hours"], "keep": cfg["backup"]["keep"], "encrypt": cfg["backup"]["encrypt"], "sealing_available": sealing.available(),
                       "ok": state["ok"], "last_ok": state["last_ok"], "age_days": None if age is None else round(age, 2), "last_attempt": state["last_attempt"], "error": state["error"], "file": state["file"],
                       "bytes": state["bytes"], "sealed": state["sealed"], "failures": state["failures"], "count": len(list_backups(config, folder))},
            "purge": {"enabled": cfg["purge"]["enabled"], "require_backup_hours": cfg["purge"]["require_backup_hours"]},
            "retention": {"enabled": policy["enabled"], "events_days": policy["events_days"], "analytics_days": policy["analytics_days"], "mode": policy["mode"]},
            "restore": {"at": last.get("at", ""), "accounts": last.get("accounts", 0)}}


def age_days(folder=None, now=None):
    """Days since the last good copy, or None when there never was one."""
    last = read_status(folder)["last_ok_epoch"]
    return None if not last else max(0.0, ((time.time() if now is None else now) - last) / 86400.0)
