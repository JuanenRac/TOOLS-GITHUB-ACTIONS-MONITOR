# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the CI costs by KIND OF CHANGE (`finops.by_change`, OFF by default), and the estimated carbon of those minutes (`finops.co2`, OFF).

Every run of the last 24 hours is put in one kind of change from what the run already says (nothing new is read from GitHub):

  dependencies  a bot of dependencies (Dependabot, Renovate, any actor that is a Bot) or a title that starts with "bump" / "update"
  scheduled     the event is `schedule`            manual   `workflow_dispatch` or `repository_dispatch`        release   the event is `release` or the title says so
  feature, fix, docs, ci, test, refactor, perf, chore   the type of a title written as a conventional commit (`feat(scope): ...`)
  other         anything else

Then minutes, runs, share of the total, average minutes per run and the estimated dollars of the private repositories (a public repository costs no minutes) are added by kind. The estimate uses the
rate of Linux per minute of the plan table; it is the same estimate as the Quota tab, not the invoice. Local reusable workflows (a file that is only called by other workflows of the repository,
`workflow_call`) are left out of the figures: their jobs already count inside the run of the caller, and counting the file again would count the same minutes twice.

CO2 (`finops.co2`): minutes x the watts of a runner x the grams per kWh of the grid. The figures are the ones YOU set (`finops.co2_watts`, `finops.co2_grams_per_kwh`): GitHub does not publish them, so the
result is an order of magnitude to compare weeks with each other, never a report of emissions.
"""
import math
import re

TYPES = ("dependencies", "scheduled", "manual", "release", "feature", "fix", "docs", "ci", "test", "refactor", "perf", "chore", "other")
CONVENTIONAL = re.compile(r"^\s*(feat|feature|fix|bugfix|hotfix|docs?|ci|build|test|tests|refactor|style|perf|chore|revert|release)(?:\([^)]{0,40}\))?!?\s*:", re.I)
CONV_MAP = {"feat": "feature", "feature": "feature", "fix": "fix", "bugfix": "fix", "hotfix": "fix", "doc": "docs", "docs": "docs", "ci": "ci", "build": "ci", "test": "test", "tests": "test",
            "refactor": "refactor", "style": "refactor", "perf": "perf", "chore": "chore", "revert": "chore", "release": "release"}
BOT_ACTORS = ("dependabot", "renovate", "github-actions", "pre-commit-ci")
DEPS_TITLE = re.compile(r"^\s*(bump|update|upgrade|pin|chore\(deps)", re.I)
DEFAULTS = {"by_change": False, "co2": False, "co2_watts": 40, "co2_grams_per_kwh": 400, "usd_per_minute": 0.008}


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def _num(value, low, high, default):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    cfg = config.get("finops") if isinstance(config, dict) and isinstance(config.get("finops"), dict) else {}
    return {"by_change": cfg.get("by_change") is True, "co2": cfg.get("co2") is True, "co2_watts": _int(cfg.get("co2_watts"), 1, 2000, DEFAULTS["co2_watts"]),
            "co2_grams_per_kwh": _int(cfg.get("co2_grams_per_kwh"), 1, 2000, DEFAULTS["co2_grams_per_kwh"])}


def classify(run):
    """The kind of change of a run (one of TYPES)."""
    actor = str(run.get("actor") or "").lower()
    title = str(run.get("title") or "")
    if run.get("actor_bot") is True or actor.endswith("[bot]") or any(actor.startswith(b) for b in BOT_ACTORS[:2]):
        return "dependencies"
    event = str(run.get("event") or "")
    if event == "schedule":
        return "scheduled"
    if event in ("workflow_dispatch", "repository_dispatch"):
        return "manual"
    if event == "release":
        return "release"
    match = CONVENTIONAL.match(title)
    if match:
        return CONV_MAP.get(match.group(1).lower(), "other")
    if DEPS_TITLE.match(title):
        return "dependencies"
    return "other"


def build(config, runs, private=None, local_reusables=None, usd_per_minute=None):
    """{"enabled", "window_hours": 24, "total_minutes", "rows": [{"type", "runs", "minutes", "share", "avg_minutes", "estimated_usd"}], "co2": {...}} over the finished runs of `runs`.
    `private` = set of private repositories (None = every repository is counted as private: the estimate then is an upper bound); `local_reusables` = {repo: {file}} to leave out."""
    cfg = settings(config)
    if not cfg["by_change"] and not cfg["co2"]:
        return {"enabled": False}
    rate = usd_per_minute if isinstance(usd_per_minute, (int, float)) else DEFAULTS["usd_per_minute"]
    skip = local_reusables or {}
    acc = {t: {"runs": 0, "seconds": 0, "usd_seconds": 0} for t in TYPES}
    for run in runs or []:
        if not isinstance(run, dict) or run.get("status") != "completed":
            continue
        if run.get("path") in (skip.get(run.get("repo")) or ()):
            continue
        slot = acc[classify(run)]
        seconds = max(0, int(run.get("seconds") or 0))
        slot["runs"] += 1
        slot["seconds"] += seconds
        if private is None or run.get("repo") in private:
            slot["usd_seconds"] += seconds
    total = sum(s["seconds"] for s in acc.values())
    rows = []
    for name in TYPES:
        s = acc[name]
        if not s["runs"]:
            continue
        minutes = math.ceil(s["seconds"] / 60) if s["seconds"] else 0
        rows.append({"type": name, "runs": s["runs"], "minutes": minutes, "share": round(100.0 * s["seconds"] / total, 1) if total else 0.0,
                     "avg_minutes": round(s["seconds"] / 60 / s["runs"], 2), "estimated_usd": round(s["usd_seconds"] / 60 * rate, 2)})
    rows.sort(key=lambda r: (-r["minutes"], r["type"]))
    out = {"enabled": True, "window_hours": 24, "total_minutes": math.ceil(total / 60) if total else 0, "rows": rows if cfg["by_change"] else []}
    if cfg["co2"]:
        out["co2"] = carbon(cfg, total / 60)
    return out


def carbon(cfg, minutes):
    """Grams of CO2 (an estimate): kWh = minutes / 60 x watts / 1000, grams = kWh x grams per kWh."""
    kwh = minutes / 60 * cfg["co2_watts"] / 1000
    return {"kwh": round(kwh, 3), "grams": round(kwh * cfg["co2_grams_per_kwh"], 1), "watts": cfg["co2_watts"], "grams_per_kwh": cfg["co2_grams_per_kwh"], "estimate": True}


def lines(prefix, report):
    """Exposition lines: minutes, runs and dollars by kind of change, and the carbon."""
    if not isinstance(report, dict) or not report.get("enabled"):
        return []
    out = []
    rows = report.get("rows") or []
    if rows:
        for metric, key, text in (("ci_change_minutes", "minutes", "Minutes of CI of the last 24 hours by kind of change."), ("ci_change_runs", "runs", "Runs of the last 24 hours by kind of change."),
                                  ("ci_change_estimated_usd", "estimated_usd", "Estimated dollars of the last 24 hours by kind of change (private repositories).")):
            out += [f"# HELP {prefix}{metric} {text}", f"# TYPE {prefix}{metric} gauge"]
            out += [f'{prefix}{metric}{{change="{r["type"]}"}} {r[key]}' for r in rows]
    co2 = report.get("co2")
    if co2:
        out += [f"# HELP {prefix}ci_co2_grams_estimate Estimated grams of CO2 of the CI minutes of the last 24 hours (an order of magnitude, never a report of emissions).", f"# TYPE {prefix}ci_co2_grams_estimate gauge",
                f"{prefix}ci_co2_grams_estimate {co2['grams']}"]
    return out
