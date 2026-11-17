# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The model of the runners (`runners.model`, OFF by default): what kind of machine each job asked for, how long jobs wait for each kind, what the minutes of each kind cost, which workflow fires itself
again and again, and whether a self-hosted runner is down. Pure functions; the labels (`runs-on`) are the ones the jobs API of GitHub gives, read by the monitor with the calls it already makes.

Kinds (the order of the tests is the order of this list):
  selfhosted   the job asks for `self-hosted` (or a label of `runners.self_labels`): it costs no minutes of GitHub
  thirdparty   a paid runner of another company, told by the start of a label (`runners.thirdparty_labels`; the default list names the usual services): GitHub does not bill it
  large        a larger runner of GitHub: a label with `-N-cores`, `large`/`xlarge` of macOS, or a pattern of `runners.large_labels` (names of your own runner groups)
  hosted       a standard runner of GitHub (an ubuntu, windows or macos label)
  unknown      no label, or none the model knows

Read only: nothing here writes to GitHub, and the warnings are alerts of this monitor (`runners.alerts`), never actions.
"""
import fnmatch
import math
import re
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n

KINDS = ("hosted", "large", "thirdparty", "selfhosted", "unknown")
DEFAULT_THIRDPARTY = ["blacksmith", "buildjet", "namespace-profile", "depot", "warpbuild", "ubicloud", "runs-on", "actuated", "cirrus-runners", "codspeed"]
LABEL_RE = re.compile(r"^[A-Za-z0-9._*?=/-]{1,60}\Z")
CORES_RE = re.compile(r"-\d{1,3}-cores?\b")
OS_RE = re.compile(r"^(ubuntu|windows|macos|linux)")
CODE_QUEUE, CODE_RUNAWAY, CODE_DOWN = "runner.queue", "runner.runaway", "runner.selfhosted_down"
LEVELS = ("info", "warning", "error")
DEFAULTS = {"enabled": False, "jobs_per_cycle": 10, "thirdparty_labels": DEFAULT_THIRDPARTY, "large_labels": [], "self_labels": [], "queue_warn_minutes": 20, "runaway_runs_per_hour": 20,
            "runaway_ignore_events": ["pull_request", "pull_request_target"], "thirdparty_usd_per_minute": 0.0, "alerts": True, "alert_level": "warning"}


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def _labels(value, default):
    return [x.lower() for x in value if isinstance(x, str) and LABEL_RE.match(x)][:100] if isinstance(value, list) else list(default)


def settings(config):
    """The `runners.model` settings with every value checked; a wrong one falls back to the conservative default."""
    runners = config.get("runners") if isinstance(config, dict) and isinstance(config.get("runners"), dict) else {}
    cfg = runners.get("model") if isinstance(runners.get("model"), dict) else {}
    rate = cfg.get("thirdparty_usd_per_minute")
    return {"enabled": cfg.get("enabled") is True, "jobs_per_cycle": _int(cfg.get("jobs_per_cycle"), 0, 100, DEFAULTS["jobs_per_cycle"]),
            "thirdparty_labels": _labels(cfg.get("thirdparty_labels"), DEFAULT_THIRDPARTY), "large_labels": _labels(cfg.get("large_labels"), []), "self_labels": _labels(cfg.get("self_labels"), []),
            "queue_warn_minutes": _int(cfg.get("queue_warn_minutes"), 1, 10080, DEFAULTS["queue_warn_minutes"]),
            "runaway_runs_per_hour": _int(cfg.get("runaway_runs_per_hour"), 0, 1000, DEFAULTS["runaway_runs_per_hour"]),
            "runaway_ignore_events": [x for x in cfg.get("runaway_ignore_events", DEFAULTS["runaway_ignore_events"]) if isinstance(x, str) and re.match(r"^[a-z_]{1,40}\Z", x)] if isinstance(cfg.get("runaway_ignore_events", []), list) else list(DEFAULTS["runaway_ignore_events"]),
            "thirdparty_usd_per_minute": float(rate) if isinstance(rate, (int, float)) and not isinstance(rate, bool) and 0 <= rate <= 10 else 0.0,
            "alerts": cfg.get("alerts") is not False, "alert_level": cfg.get("alert_level") if cfg.get("alert_level") in LEVELS else DEFAULTS["alert_level"]}


def kind_of(labels, cfg):
    """The kind of runner a job asked for, from its labels (case does not matter)."""
    names = [str(x).lower() for x in labels or [] if isinstance(x, (str, int))]
    if not names:
        return "unknown"
    if "self-hosted" in names or any(n in cfg["self_labels"] for n in names):
        return "selfhosted"
    if any(n.startswith(tuple(cfg["thirdparty_labels"])) for n in names if cfg["thirdparty_labels"]):
        return "thirdparty"
    if any(CORES_RE.search(n) or (n.startswith("macos") and ("large" in n or "xlarge" in n)) or any(fnmatch.fnmatchcase(n, p) for p in cfg["large_labels"]) for n in names):
        return "large"
    return "hosted" if any(OS_RE.match(n) for n in names) else "unknown"


def _ts(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def compact(repo, run_id, body):
    """The jobs of one run reduced to what the model needs: [{"repo", "run", "name", "status", "labels", "created", "started", "runner"}]."""
    rows = []
    for job in (body or {}).get("jobs") or []:
        if isinstance(job, dict):
            rows.append({"repo": repo, "run": run_id, "name": str(job.get("name") or "")[:80], "status": job.get("status"), "labels": [str(x)[:40] for x in (job.get("labels") or [])][:12],
                         "created": job.get("created_at"), "started": job.get("started_at"), "runner": str(job.get("runner_name") or "")[:60]})
    return rows


def queue_by_kind(rows, now, cfg):
    """{kind: {"jobs": n, "oldest_wait_seconds": s}} for the jobs that have not started (status queued or waiting); a kind with no waiting job is left out."""
    out = {}
    for row in rows:
        if row.get("status") not in ("queued", "waiting"):
            continue
        created = _ts(row.get("created"))
        wait = max(0.0, now - created) if created is not None else 0.0
        entry = out.setdefault(kind_of(row.get("labels"), cfg), {"jobs": 0, "oldest_wait_seconds": 0})
        entry["jobs"] += 1
        entry["oldest_wait_seconds"] = max(entry["oldest_wait_seconds"], int(wait))
    return out


def tally(jobs, rates, default_runner, cfg):
    """The minutes of finished jobs by kind: {"minutes": {kind: n}, "billable": x}. `jobs` carry `seconds` and `labels`; `rates` is the table of quota.py. Each job is rounded up to the minute, as GitHub bills.
    `billable` counts only what GitHub bills (hosted and large, in minutes of Linux): a third-party or a self-hosted job is never billed by GitHub."""
    from github_actions_monitor.data_pipeline import quota
    minutes, billable = {}, 0.0
    for job in jobs or []:
        seconds = job.get("seconds") or 0
        count = math.ceil(seconds / 60) if seconds > 0 else 0
        kind = kind_of(job.get("labels"), cfg)
        minutes[kind] = minutes.get(kind, 0) + count
        if kind in ("hosted", "large", "unknown"):
            billable += count * quota.multiplier(quota.runner_system(job.get("labels")) or default_runner, rates)
    return {"minutes": minutes, "billable": round(billable, 2)}


def usage(tallies, rates, cfg):
    """The cost by kind over the runs that were sampled: {kind: {"minutes", "usd"}}; `usd` is None for a third-party kind with no price set (`runners.model.thirdparty_usd_per_minute`)."""
    minutes, billable = {}, 0.0
    for item in tallies:
        for kind, n in (item.get("minutes") or {}).items():
            minutes[kind] = minutes.get(kind, 0) + n
        billable += item.get("billable") or 0
    base = (rates.get("rates_usd_per_minute") or {}).get("linux") or 0.006
    paid = sum(minutes.get(k, 0) for k in ("hosted", "large", "unknown"))
    out = {}
    for kind, n in sorted(minutes.items()):
        if kind in ("hosted", "large", "unknown"):
            usd = round(billable * base * (n / paid), 2) if paid else 0.0      # the billable minutes are shared out in proportion to the minutes of each kind
        elif kind == "thirdparty":
            usd = round(n * cfg["thirdparty_usd_per_minute"], 2) if cfg["thirdparty_usd_per_minute"] > 0 else None
        else:
            usd = 0.0
        out[kind] = {"minutes": n, "usd": usd}
    return out


def runaway(runs, now, cfg, sample_cap=0):
    """The workflows that fire again and again: those with at least `runaway_runs_per_hour` runs started in the last hour (pull requests do not count by default). The list of runs the monitor holds
    is a sample (`runs_per_repo` per repository), so a limit above the sample cannot be reached: `limited` says so instead of looking quiet."""
    limit = cfg["runaway_runs_per_hour"]
    if not limit:
        return {"rows": [], "limited": False}
    groups = {}
    for run in runs or []:
        when = _ts(run.get("started"))
        if when is None or when < now - 3600 or when > now + 300 or run.get("event") in cfg["runaway_ignore_events"]:
            continue
        g = groups.setdefault((run.get("repo"), run.get("name") or run.get("path") or ""), {"runs": 0, "events": {}, "branches": set()})
        g["runs"] += 1
        g["events"][run.get("event") or ""] = g["events"].get(run.get("event") or "", 0) + 1
        g["branches"].add(str(run.get("branch") or ""))
    rows = [{"repo": k[0], "workflow": k[1], "runs_last_hour": g["runs"], "events": g["events"], "branches": sorted(g["branches"])[:5]} for k, g in groups.items() if g["runs"] >= limit]
    rows.sort(key=lambda r: (-r["runs_last_hour"], r["repo"], r["workflow"]))
    return {"rows": rows[:50], "limited": bool(sample_cap) and sample_cap < limit}


def selfhosted_down(rows, runners, now, cfg):
    """The jobs that wait for a self-hosted runner for at least `queue_warn_minutes`, and why nothing picks them up: `no_online_runner` (no runner that is online has all the labels of the job),
    `all_busy` (there is one and it is busy: a queue, not a failure) or `unknown` (the list of runners is not read: `runners.enabled` is off)."""
    known = runners is not None
    found = {}
    for row in rows:
        if row.get("status") not in ("queued", "waiting") or kind_of(row.get("labels"), cfg) != "selfhosted":
            continue
        created = _ts(row.get("created"))
        if created is None or now - created < cfg["queue_warn_minutes"] * 60:
            continue
        need = {str(x).lower() for x in row.get("labels") or []}
        fits = [r for r in runners or [] if r.get("state") != "offline" and need <= {str(x).lower() for x in r.get("labels") or []}]
        reason = "unknown" if not known else ("no_online_runner" if not fits else ("all_busy" if all(r.get("state") == "busy" for r in fits) else "idle_not_picking"))
        key = (row["repo"], tuple(sorted(need)))
        e = found.setdefault(key, {"repo": row["repo"], "labels": sorted(need), "jobs": 0, "oldest_wait_minutes": 0, "reason": reason})
        e["jobs"] += 1
        e["oldest_wait_minutes"] = max(e["oldest_wait_minutes"], int((now - created) // 60))
    return sorted(found.values(), key=lambda e: (-e["oldest_wait_minutes"], e["repo"]))


def build(config, job_rows, runs, tallies, rates, runners, now, sample_cap=0):
    """The whole model in one answer: settings, the queue by kind, the cost by kind, the workflows that fire again and again and the self-hosted queues."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return {"schema": 1, "enabled": False}
    return {"schema": 1, "enabled": True, "queue": queue_by_kind(job_rows, now, cfg), "usage": usage(tallies, rates, cfg), "runaway": runaway(runs, now, cfg, sample_cap),
            "selfhosted": selfhosted_down(job_rows, runners, now, cfg), "jobs_seen": len(job_rows), "runners_known": runners is not None,
            "limits": {"queue_warn_minutes": cfg["queue_warn_minutes"], "runaway_runs_per_hour": cfg["runaway_runs_per_hour"]}}


def alerts(model, config, account="", now=None):
    """The model as alerts of the Alerts tab (`sentinel: "system"`), only when `runners.model.alerts` is on: a self-hosted queue with no runner to pick it up, and a workflow that fires itself."""
    cfg = settings(config)
    if not model.get("enabled") or not cfg["alerts"]:
        return []
    level, out = cfg["alert_level"], []
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now))
    for row in model.get("selfhosted") or []:
        if row["reason"] in ("no_online_runner", "idle_not_picking"):
            out.append({"id": f"{CODE_DOWN}:{row['repo']}:{','.join(row['labels'])}", "code": CODE_DOWN, "level": level, "sentinel": "system", "account_id": account, "repo": row["repo"],
                        "title": i18n.t("runner.alert_down", jobs=row["jobs"], minutes=row["oldest_wait_minutes"], labels=", ".join(row["labels"]), reason=i18n.t("runner.reason_" + row["reason"])),
                        "details": {"reason": row["reason"], "labels": row["labels"], "jobs": row["jobs"], "oldest_wait_minutes": row["oldest_wait_minutes"]}, "created_at": stamp})
    for row in (model.get("runaway") or {}).get("rows") or []:
        out.append({"id": f"{CODE_RUNAWAY}:{row['repo']}:{row['workflow']}", "code": CODE_RUNAWAY, "level": level, "sentinel": "system", "account_id": account, "repo": row["repo"],
                    "title": i18n.t("runner.alert_runaway", workflow=row["workflow"], runs=row["runs_last_hour"]),
                    "details": {"runs_last_hour": row["runs_last_hour"], "events": row["events"], "branches": row["branches"]}, "created_at": stamp})
    return out
