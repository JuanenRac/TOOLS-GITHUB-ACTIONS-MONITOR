# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""GitHub quotas for every kind of user: the plan, the billable minutes, the allowance of the API, the concurrency and the long jobs. Standard library only; nothing is sent anywhere.

The figures are NOT in the code: they are read from `quotas.json` (next to the monitor; edit it to follow the changes of GitHub without a new version). The plan is chosen in Settings > Basic
(`account.plan`, unknown by default).
  * public repositories cost no minutes; private ones count the minutes of a job with the multiplier of its system (rate of the system / rate of Linux);
  * what the monitor computes is an ESTIMATE (the duration of the runs it holds, rounded up to the minute, with `quota.default_runner` as the system); the real figures come only from the
    optional, read-only billing report (`quota.billing_api`, off by default; it needs a token with permission and degrades silently on 403 / 404);
  * a warning at `quota.warn_percent` and `quota.alert_percent` of the included minutes, once per level and month, through the same notifications as everything else.
"""
import json
import math
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUOTAS_FILE = HERE / "quotas.json"
PLANS = ("unknown", "free", "pro", "team", "enterprise")
SYSTEMS = ("linux", "windows", "macos")
DEFAULT_SETTINGS = {"plan": "unknown", "billing_api": False, "warn_percent": 75, "alert_percent": 90, "default_runner": "linux"}
FALLBACK = {"plans": {}, "rates_usd_per_minute": {"linux": 0.006, "windows": 0.01, "macos": 0.062}, "limits": {"job_hours": 6, "run_days": 35, "matrix_jobs": 256},
            "api": {"unauthenticated": 60, "token": 5000, "actions_token": 1000, "enterprise_cloud": 15000, "app_max": 12500, "concurrent_requests": 100}, "public_repositories_free": True}


def load(path=None):
    try:
        data = json.loads(Path(path or QUOTAS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in FALLBACK.items()}
    for key, value in (data.items() if isinstance(data, dict) else ()):
        if key in ("plans", "rates_usd_per_minute", "limits", "api") and isinstance(value, dict):
            out[key] = {**out.get(key, {}), **value}
        elif key in ("schema", "source", "public_repositories_free"):
            out[key] = value
    return out


def settings(config):
    cfg = config if isinstance(config, dict) else {}
    account = cfg.get("account") if isinstance(cfg.get("account"), dict) else {}
    quota = cfg.get("quota") if isinstance(cfg.get("quota"), dict) else {}
    out = dict(DEFAULT_SETTINGS)
    out["plan"] = account.get("plan") if account.get("plan") in PLANS else "unknown"
    out["billing_api"] = quota.get("billing_api") is True
    for key in ("warn_percent", "alert_percent"):
        value = quota.get(key)
        out[key] = value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 100 else DEFAULT_SETTINGS[key]
    out["default_runner"] = quota.get("default_runner") if quota.get("default_runner") in SYSTEMS else "linux"
    return out


def multiplier(system, data):
    rates = data["rates_usd_per_minute"]
    base = rates.get("linux") or 0.006
    return round((rates.get(system) or base) / base, 3)


def runner_system(labels):
    """'linux' | 'windows' | 'macos' | 'self' from the labels of a job; None when there are none. Self-hosted runners cost no minutes."""
    labels = [str(x).lower() for x in labels or []]
    if not labels:
        return None
    if "self-hosted" in labels:
        return "self"
    for label in labels:
        if label.startswith("windows"):
            return "windows"
        if label.startswith("macos"):
            return "macos"
    return "linux"


def included_minutes(plan, data):
    """Standard Linux minutes included each month in a plan, or None when the plan is unknown (included dollars divided by the Linux rate)."""
    info = data["plans"].get(plan)
    if not info:
        return None
    return round(info["included_usd"] / data["rates_usd_per_minute"]["linux"])


def billable(runs, private, data, default_runner="linux", systems=None):
    """{"clock": minutes of every run, "billable": multiplied minutes of the private repositories, "by_system": {...}, "estimate": True} for the completed runs given."""
    clock = bill = 0
    by = {s: 0 for s in SYSTEMS}
    for run in runs:
        seconds = run.get("seconds") or 0
        minutes = math.ceil(seconds / 60) if seconds > 0 else 0
        clock += minutes
        if run.get("repo") not in private:
            continue
        system = (systems or {}).get(run.get("id")) or default_runner
        if system == "self":
            continue
        bill += minutes * multiplier(system, data)
        by[system] += minutes
    return {"clock": clock, "billable": round(bill), "by_system": by, "estimate": True}


def projection(billable_24h, days_in_month=30):
    """The month at this pace: the minutes of one day times the days of the month. An estimate, and the panel says so."""
    return round(billable_24h * days_in_month)


def level(used, included, cfg):
    if not included:
        return "unknown"
    pct = 100.0 * used / included
    return "alert" if pct >= cfg["alert_percent"] else ("warn" if pct >= cfg["warn_percent"] else "ok")


def api_mode(limit):
    """What kind of token the allowance of the API says it is; GitHub's own header is the truth, 5,000 is never assumed: unauthenticated | actions_token | token | enterprise | custom | unknown."""
    if not isinstance(limit, int) or isinstance(limit, bool):
        return "unknown"
    return {60: "unauthenticated", 1000: "actions_token", 5000: "token", 12500: "token", 15000: "enterprise"}.get(limit, "custom")


def concurrency(active, plan, data):
    """Running and queued against the concurrent-job limit of the plan. Jobs are approximated by runs (one job each) unless a run lists its jobs."""
    info = data["plans"].get(plan)
    running = sum(max(1, len(r.get("jobs") or [])) for r in active if r.get("status") == "in_progress")
    queued = sum(1 for r in active if r.get("status") != "in_progress")
    limit = info["concurrent_jobs"] if info else None
    state = "unknown" if not limit else ("alert" if running >= limit and queued else ("warn" if running >= 0.9 * limit else "ok"))
    return {"running": running, "queued": queued, "limit": limit, "macos_limit": info["concurrent_macos"] if info else None, "level": state}


def long_jobs(active, data, share=0.8):
    """Runs in progress for more than `share` of the 6-hour limit of a job: [{"repo", "name", "hours"}]."""
    limit = data["limits"]["job_hours"] * 3600 * share
    return [{"repo": r.get("repo"), "name": r.get("name"), "hours": round((r.get("seconds") or 0) / 3600, 1)} for r in active if r.get("status") == "in_progress" and (r.get("seconds") or 0) >= limit]


def billing_usage(owner, reader):
    """The real minutes of Actions this month from the billing report of GitHub (read only): {"minutes", "by_sku"} or None on any error (403, 404, offline). `reader(endpoint)` returns the JSON."""
    for endpoint in (f"users/{owner}/settings/billing/usage", f"organizations/{owner}/settings/billing/usage"):
        try:
            body = reader(endpoint)
        except Exception:   # noqa: BLE001 - no permission, not that kind of account, offline: the estimate stays
            continue
        items = body.get("usageItems") if isinstance(body, dict) else None
        if isinstance(items, list):
            by = {}
            for item in items:
                if isinstance(item, dict) and str(item.get("product", "")).lower() == "actions" and isinstance(item.get("quantity"), (int, float)) and "minute" in str(item.get("unitType", "minutes")).lower():
                    sku = str(item.get("sku") or "actions")[:40]
                    by[sku] = by.get(sku, 0) + item["quantity"]
            return {"minutes": round(sum(by.values()), 1), "by_sku": {k: round(v, 1) for k, v in by.items()}}
    return None


class Alerts:
    """Each warning level is said once per month."""

    def __init__(self, clock=time.time):
        self.clock, self.said = clock, set()

    def due(self, state):
        if state not in ("warn", "alert"):
            return False
        key = (time.strftime("%Y-%m", time.gmtime(self.clock())), state)
        if key in self.said:
            return False
        self.said.add(key)
        return True


def summary(config, runs, active, private, reader=None, owner="", rate_limit=None, systems=None, data=None):
    """Everything the panel shows, in one dictionary."""
    cfg = settings(config)
    data = data or load()
    sums = billable(runs, private, data, cfg["default_runner"], systems)
    included = included_minutes(cfg["plan"], data)
    real = billing_usage(owner, reader) if (cfg["billing_api"] and reader and owner) else None
    month = projection(sums["billable"])
    used = real["minutes"] if real else month
    return {"plan": cfg["plan"], "included_minutes": included, "billable": sums, "month_estimate": month, "billing": real, "billing_requested": cfg["billing_api"], "level": level(used, included, cfg),
            "warn_percent": cfg["warn_percent"], "alert_percent": cfg["alert_percent"], "api_mode": api_mode(rate_limit), "concurrency": concurrency(active, cfg["plan"], data),
            "long_jobs": long_jobs(active, data), "limits": data["limits"], "multipliers": {s: multiplier(s, data) for s in SYSTEMS}, "source": data.get("source", ""),
            "public_free": data.get("public_repositories_free", True)}
