# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The checks of the doctor that look at an installation that lives for months: the volumes (a real write and read), the supervisor, the limits (webhook secret LENGTH, retention policy), the integrity
of the SQLite databases (read only, with a time limit), the age of the last copy, the free disk and /metrics. Each one is `(status, detail)` with status ok | warn | fail, read only (the only thing
written is a probe file that is removed at once), and never shows a secret or a path of a person. The complete edition runs them from `cli/doctor.py`; the lite edition never imports this module."""
import os
import shutil
import uuid
from pathlib import Path

from github_actions_monitor.ops import opsconf, schedule
from github_actions_monitor.util import paths


def probe(folder):
    """None when a file can be written, read back and removed in `folder`, else a short reason. The probe file is always removed."""
    name = folder / f".ghamon-probe-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    try:
        with open(name, "wb") as handle:
            handle.write(b"probe")
        if name.read_bytes() != b"probe":
            return "read-back"
        return None
    except PermissionError:
        return "read-only"
    except OSError as error:
        return (error.strerror or "error")[:40]
    finally:
        try:
            name.unlink()
        except OSError:
            pass


def volumes(config, folder=None):
    """The folders the monitor writes to (data, logs and the folder of the copies): each must accept a real file. Docker volumes mounted as root or read only fail here."""
    places = {"data": paths.folder("data", folder), "logs": paths.folder("logs", folder), "backups": opsconf.backup_dir(config, folder)}
    bad, good = [], []
    for label, where in places.items():
        if where.is_dir():
            reason = probe(where)
        elif label == "backups" or (where.parent.is_dir() and probe(where.parent) is None):
            good.append(label + " (new)")      # made by the first start, or by the first copy
            continue
        else:
            reason = "missing"
        (bad if reason else good).append(f"{label}: {reason}" if reason else label)
    return ("fail", "; ".join(bad)) if bad else ("ok", ", ".join(good))


def supervisor(config, folder=None, alive=None, ask=None):
    """The deep health of a monitor that is running (the supervisor and the refresh cycle of every account); nothing is started. No monitor running is not a problem: the doctor also runs before the start."""
    from github_actions_monitor.util import exclusive, ports
    port = ports.resolve("complete")
    if not (alive or exclusive.monitor_on)(port):
        return "ok", "not running"
    from github_actions_monitor.cli import healthcheck
    status, document = (ask or healthcheck.ask)(f"http://127.0.0.1:{port}", 4.0, healthcheck.token())
    code, _text = healthcheck.judge(status, document)
    if code == healthcheck.EXIT_OK:
        return "ok", "healthy"
    if code == healthcheck.EXIT_REFUSED:
        return "warn", "access refused"
    if code == healthcheck.EXIT_DOWN:
        return "warn", "no answer"
    return "fail", "unhealthy"


def limits(config, folder=None, secret_reader=None):
    """The webhook secret (only whether it is set and how LONG it is, against `ops.doctor.webhook_min_length`; never its value) and the retention policy in force."""
    from github_actions_monitor.security import webhook
    from github_actions_monitor.storage import retention
    cfg = opsconf.settings(config)["doctor"]
    notes, status = [], "ok"
    hook = (config or {}).get("webhook") if isinstance((config or {}).get("webhook"), dict) else {}
    if hook.get("enabled") is True:
        value = (secret_reader or webhook.read_secret)(webhook.secret_env_name(config))
        if not value and secret_reader is None:
            value = webhook.settings(config)["secret"]      # a secret kept in the file, where webhook.allow_config_secret still allows it
        if not value:
            status = "fail"      # the receiver is on and has no secret: it refuses every delivery, so nothing GitHub sends is ever read
            notes.append("webhook secret not set")
        elif len(value) < cfg["webhook_min_length"]:
            status = "warn"
            notes.append(f"webhook secret {len(value)} < {cfg['webhook_min_length']} characters")
    policy = retention.effective(config)
    notes.append(f"retention {policy['events_days']} d {policy['mode']}" if policy["enabled"] else "retention off")
    for key, info in (policy.get("raised") or {}).items():
        notes.append(f"{key} raised from {info['asked']} to {info['now']} to cover the longest window that reads it")
        if status == "ok":
            status = "warn"
    if not policy["enabled"] and retention.service_mode(config):
        status = "warn"
    return status, "; ".join(notes)


def sqlite_hot(config, folder=None, inspect=None, clock=None):
    """The integrity of every SQLite database, read only and with a time limit: quick_check by default (fast), integrity_check with `ops.doctor.sqlite_check` = deep, nothing with off. Corruption after a
    power cut shows here. A check that ran out of time is a warning, not a failure."""
    from github_actions_monitor.accounts import accounts
    from github_actions_monitor.cli import doctor
    from github_actions_monitor.storage import factory, sqlite_storage
    cfg = opsconf.settings(config)["doctor"]
    if cfg["sqlite_check"] == "off":
        return "ok", "off"
    mode = "quick" if cfg["sqlite_check"] == "quick" else "integrity"
    seen, problems, slow = 0, [], []
    for account_id, account_cfg in doctor._account_configs(config, folder):
        settings = factory.settings(account_cfg.get("storage"))
        if settings["backend"] != "sqlite":
            continue
        path = Path(settings["path"]) if settings["path"] else (accounts.account_dir(account_id, folder) / factory.DB_NAME if account_id else paths.place(factory.DB_NAME, folder))
        if not path.is_file():
            continue
        extra = {"clock": clock} if clock else {}
        info = (inspect or sqlite_storage.inspect)(path, mode=mode, timeout_s=cfg["sqlite_timeout_s"], **extra)
        seen += 1
        label = account_id or "default"
        problems += [f"{label}: {p}" for p in info["problems"]]
        if info.get("timed_out"):
            slow.append(label)
    if problems:
        return "fail", "; ".join(problems[:3])
    if slow:
        return "warn", f"{mode} check stopped at {cfg['sqlite_timeout_s']} s: " + ", ".join(slow[:3])
    return "ok", f"{mode}: {seen} database(s)" if seen else "no SQLite database"


def backup_age(config, folder=None, now=None):
    """The last good copy against `ops.doctor.backup_max_age_days`: a warning when the schedule is on and there is none or it is too old, or when the last attempt failed, or when a copy exists but is old."""
    cfg = opsconf.settings(config)
    state = schedule.read_status(folder)
    age = schedule.age_days(folder, now)
    limit = cfg["doctor"]["backup_max_age_days"]
    on = cfg["backup"]["enabled"]
    if on and state["ok"] is False:
        return "warn", "last attempt failed: " + (state["error"] or "failed")
    if age is None:
        return ("warn", "none yet") if on else ("ok", "none (schedule off)")
    return ("warn", f"{age:.1f} d old (> {limit})") if age > limit else ("ok", f"{age:.1f} d old")


def disk(config, folder=None, usage=None):
    """Free space of the volume of the data against `ops.doctor.min_free_mb` (a warning below it, a failure below a tenth of it)."""
    floor = opsconf.settings(config)["doctor"]["min_free_mb"]
    target = paths.folder("data", folder)
    try:
        free = (usage or shutil.disk_usage)(target if target.exists() else target.parent).free // 1048576
    except OSError:
        return "warn", "unknown"
    if free < max(1, floor // 10):
        return "fail", f"{free} MB free"
    return ("warn", f"{free} MB free < {floor} MB") if free < floor else ("ok", f"{free} MB free")


def metrics(config, folder=None, alive=None, fetch=None):
    """/metrics answers when the Prometheus output is on and a monitor is running; off or not running is fine."""
    from github_actions_monitor.app import settings_api
    if not settings_api.output_enabled(config or {}, "prometheus"):
        return "ok", "off"
    from github_actions_monitor.util import exclusive, ports
    port = ports.resolve("complete")
    if not (alive or exclusive.monitor_on)(port):
        return "ok", "not running"
    try:
        status = (fetch or _fetch_metrics)(f"http://127.0.0.1:{port}/metrics")
    except OSError:
        return "warn", "no answer"
    return ("ok", "answering") if status == 200 else ("warn", f"HTTP {status}")


def _fetch_metrics(url):
    import urllib.error
    import urllib.request
    from github_actions_monitor.security import netguard
    try:
        with netguard.local_open(urllib.request.Request(url), timeout=4, follow_redirects=False) as answer:
            return answer.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code


def capacity(config, folder=None, repos=-1):
    """The setup against its ceilings (data_pipeline/limits.py): reads an hour against the allowance, memory of the held runs, repositories against `discover_limit`. The number of repositories is the one of
    the last picture of the monitor (`repos` gives it in a test); with no picture yet there is nothing to judge and it says so."""
    from github_actions_monitor.data_pipeline import limits
    if repos == -1:
        try:
            from github_actions_monitor.app import lastpicture
            picture = lastpicture.load(paths.folder("data", folder), {"startup": {"resume_max_age_hours": 168}})
            repos = len((picture or {}).get("repos") or []) if picture else None
        except Exception:   # noqa: BLE001 - no picture to read is not a failure of the doctor
            repos = None
    if repos is None:
        return "ok", "no picture yet"
    status, detail = limits.verdict(limits.planned(config, repos))
    return status, f"{repos} repositories: {detail}"


def run_all(config, folder=None):
    """{id: (status, detail)} for the checks of ORDER_OPS. A check that cannot run answers warn, never raises: the doctor must always answer."""
    out = {}
    for name, function in (("volumes", volumes), ("supervisor", supervisor), ("limits", limits), ("capacity", capacity), ("sqlite_hot", sqlite_hot), ("backup_age", backup_age), ("disk", disk), ("metrics", metrics)):
        try:
            out[name] = function(config, folder)
        except Exception as error:   # noqa: BLE001 - one check that breaks must not hide the others
            out[name] = ("warn", f"could not run ({type(error).__name__})")
    return out
