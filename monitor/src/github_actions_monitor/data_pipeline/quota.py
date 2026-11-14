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
import re
import time
from pathlib import Path

from github_actions_monitor.util import paths


def _default_file():
    """Your own config/quotas.json when it exists, else the one that travels in assets/examples."""
    own = paths.place("quotas.json")
    return own if own.is_file() else paths.EXAMPLES / "quotas.json"


QUOTAS_FILE = _default_file()
PLANS = ("unknown", "free", "pro", "team", "enterprise")
SYSTEMS = ("linux", "windows", "macos")
DEFAULT_SETTINGS = {"plan": "unknown", "billing_api": False, "warn_percent": 75, "alert_percent": 90, "default_runner": "linux"}
FALLBACK = {"plans": {}, "rates_usd_per_minute": {"linux": 0.006, "windows": 0.01, "macos": 0.062}, "limits": {"job_hours": 6, "run_days": 35, "matrix_jobs": 256},
            "api": {"unauthenticated": 60, "token": 5000, "actions_token": 1000, "enterprise_cloud": 15000, "app_max": 12500, "concurrent_requests": 100}, "public_repositories_free": True}


def load(path=None):
    try:
        data = json.loads(Path(path or (_default_file() if QUOTAS_FILE.parent == paths.EXAMPLES else QUOTAS_FILE)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in FALLBACK.items()}
    for key, value in (data.items() if isinstance(data, dict) else ()):
        if key in ("plans", "rates_usd_per_minute", "larger_rates_usd_per_minute", "limits", "api") and isinstance(value, dict):
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
    """Rate of a system divided by the rate of Linux. `system` is linux | windows | macos or a finer key of the larger runners (linux_8, windows_16, macos_xlarge...): its price comes from
    `larger_rates_usd_per_minute` in quotas.json; an unknown key is priced as its base system."""
    rates = data["rates_usd_per_minute"]
    base = rates.get("linux") or 0.006
    price = (data.get("larger_rates_usd_per_minute") or {}).get(system) or rates.get(system) or rates.get(str(system).split("_")[0]) or base
    return round(price / base, 3)


CORES_RE = re.compile(r"-(\d{1,3})-cores?$")


def runner_system(labels):
    """The system of a job from its labels: 'linux' | 'windows' | 'macos' | 'self', or a larger-runner key ('linux_8', 'windows_16', 'macos_large', 'macos_xlarge', 'linux_arm_4').
    None when there are no labels. Self-hosted runners cost no minutes."""
    labels = [str(x).lower() for x in labels or []]
    if not labels:
        return None
    if "self-hosted" in labels:
        return "self"
    for label in labels:
        kind = "windows" if label.startswith("windows") else ("macos" if label.startswith("macos") else ("linux" if label.startswith(("ubuntu", "linux")) else ""))
        if not kind:
            continue
        cores = CORES_RE.search(label)
        if kind == "macos":
            return "macos_xlarge" if "xlarge" in label else ("macos_large" if "large" in label else "macos")
        if cores:
            return f"{kind}{'_arm' if 'arm' in label else ''}_{int(cores.group(1))}"
        return kind
    return "linux"


def base_system(key):
    return "macos" if str(key).startswith("macos") else ("windows" if str(key).startswith("windows") else "linux")


def job_costs(jobs, data, default_runner="linux"):
    """The cost of ONE run from the jobs it ran: each job is rounded up to the minute (as GitHub bills) and multiplied by the rate of ITS runner. `jobs` carry `labels`, `started`/`completed`
    as seconds (`seconds`). Returns {"clock", "billable", "by_system"} - the exact figure the estimate cannot give when it assumes one system for every run."""
    clock = bill = 0
    by = {}
    for job in jobs or []:
        seconds = job.get("seconds") or 0
        minutes = math.ceil(seconds / 60) if seconds > 0 else 0
        clock += minutes
        system = runner_system(job.get("labels")) or default_runner
        if system == "self":
            continue
        bill += minutes * multiplier(system, data)
        by[system] = by.get(system, 0) + minutes
    return {"clock": clock, "billable": round(bill, 2), "by_system": by}


def included_minutes(plan, data):
    """Standard Linux minutes included each month in a plan, or None when the plan is unknown (included dollars divided by the Linux rate)."""
    info = data["plans"].get(plan)
    if not info:
        return None
    return round(info["included_usd"] / data["rates_usd_per_minute"]["linux"])


def billable(runs, private, data, default_runner="linux", systems=None, costs=None):
    """{"clock": minutes of every run, "billable": multiplied minutes of the private repositories, "by_system": {...}, "estimate": bool} for the completed runs given.
    A run whose jobs were read (`costs[run id]`, from job_costs) is counted exactly; the others with one assumed system (`systems[id]` or `default_runner`) and the result says how many were exact."""
    clock = bill = exact = 0
    by = {s: 0 for s in SYSTEMS}
    for run in runs:
        seconds = run.get("seconds") or 0
        minutes = math.ceil(seconds / 60) if seconds > 0 else 0
        known = (costs or {}).get(run.get("id"))
        clock += known["clock"] if known else minutes
        if run.get("repo") not in private:
            continue
        if known:
            exact += 1
            bill += known["billable"]
            for key, value in known["by_system"].items():
                by[key] = by.get(key, 0) + value
            continue
        system = (systems or {}).get(run.get("id")) or default_runner
        if system == "self":
            continue
        bill += minutes * multiplier(system, data)
        by[system] = by.get(system, 0) + minutes
    return {"clock": clock, "billable": round(bill), "by_system": by, "estimate": exact < len(runs) or not runs, "exact_runs": exact}


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
    """The real usage of this month from the billing report of GitHub (read only): {"minutes", "by_sku", "usd": {product: net dollars}, "storage_gb_hours"} or None on any error (403, 404, offline).
    `reader(endpoint)` returns the JSON. Actions minutes are summed as before; Codespaces, Packages and every other product are summed in dollars (netAmount) so they can be shown too."""
    for endpoint in (f"users/{owner}/settings/billing/usage", f"organizations/{owner}/settings/billing/usage"):
        try:
            body = reader(endpoint)
        except Exception:   # noqa: BLE001 - no permission, not that kind of account, offline: the estimate stays
            continue
        items = body.get("usageItems") if isinstance(body, dict) else None
        if isinstance(items, list):
            by, usd, storage = {}, {}, 0.0
            for item in items:
                if not isinstance(item, dict):
                    continue
                product = str(item.get("product", "")).lower()[:30]
                amount = item.get("netAmount")
                if isinstance(amount, (int, float)) and not isinstance(amount, bool):
                    usd[product] = round(usd.get(product, 0) + amount, 4)
                quantity, unit = item.get("quantity"), str(item.get("unitType", "minutes")).lower()
                if product == "actions" and isinstance(quantity, (int, float)):
                    if "minute" in unit:
                        sku = str(item.get("sku") or "actions")[:40]
                        by[sku] = by.get(sku, 0) + quantity
                    elif "gigabyte" in unit or "gb" in unit:
                        storage += quantity
            return {"minutes": round(sum(by.values()), 1), "by_sku": {k: round(v, 1) for k, v in by.items()}, "usd": usd, "storage_gb_hours": round(storage, 2)}
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


def extra_cost(used_minutes, included, data):
    """What the minutes above the included ones cost, in dollars, at the rate of Linux (the billable minutes are already multiplied by the rate of each system). 0 under the ceiling; None
    when the plan is unknown."""
    if included is None:
        return None
    return round(max(0.0, used_minutes - included) * data["rates_usd_per_minute"]["linux"], 2)


def summary(config, runs, active, private, reader=None, owner="", rate_limit=None, systems=None, data=None, costs=None):
    """Everything the panel shows, in one dictionary."""
    cfg = settings(config)
    data = data or load()
    sums = billable(runs, private, data, cfg["default_runner"], systems, costs)
    included = included_minutes(cfg["plan"], data)
    real = billing_usage(owner, reader) if (cfg["billing_api"] and reader and owner) else None
    month = projection(sums["billable"])
    used = real["minutes"] if real else month
    return {"plan": cfg["plan"], "included_minutes": included, "billable": sums, "month_estimate": month, "billing": real, "billing_requested": cfg["billing_api"], "level": level(used, included, cfg),
            "warn_percent": cfg["warn_percent"], "alert_percent": cfg["alert_percent"], "api_mode": api_mode(rate_limit), "concurrency": concurrency(active, cfg["plan"], data),
            "long_jobs": long_jobs(active, data), "extra_cost_usd": extra_cost(used, included, data), "limits": data["limits"], "multipliers": {s: multiplier(s, data) for s in SYSTEMS}, "source": data.get("source", ""),
            "public_free": data.get("public_repositories_free", True)}
