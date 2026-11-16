# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The health of one repository (`GET /api/repos/<owner>/<repo>/health`) and the ranking of the team (`GET /api/team/health`). Pure functions: the data go in, plain data come out; nothing is read here.

What a repository's health is made of, all of it from what the monitor already holds:
  ci         the runs of the last 24 hours (successes, failures), the workflows that are red now, the runs that are stuck
  alerts     every open alert of every sentinel about the repository (CI, Collab, Security), counted by sentinel and by level
  readiness  the row of the release readiness (entries under [Unreleased], what is next), when the repository has one
  activity   when the last run started and how many runs the monitor holds for the last 7 days
  sources    which sentinels looked (their lifecycle): a repository with no alerts from a sentinel that is off or degraded is NOT healthy, only not seen
The state is `bad` (a red workflow, or an alert of level critical or error), `warn` (a warning, or a run that is stuck), `ok`, or `unknown` (nothing to judge by: no run and no alert, or no sentinel
that could look at it, because they are all in error, paused or degraded, or off with no run in the last seven days: a quiet repository is only `ok` when something really looked at it). `risk` is the number the ranking sorts
by: every red workflow, stuck run and open alert adds points by its severity (the same weights for every repository, shown in `RISK`), so the repositories that need a person come first.
"""
from datetime import datetime, timezone

DAY = 86400.0
STATES = ("unknown", "ok", "warn", "bad")        # from the best known to the worst: a filter by severity keeps this one and everything after it
RISK = {"red": 30, "stuck": 10, "critical": 25, "error": 10, "warning": 3, "info": 1}
LEVELS = ("critical", "error", "warning", "info")


def _ts(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def ci_part(repo, runs, failing, active, now):
    """The CI of the repository: runs of the last 24 hours and the red and stuck ones. `failing` are the red workflows ({"repo", "workflow"...}), `active` the runs in progress or waiting."""
    mine = [r for r in runs if isinstance(r, dict) and r.get("repo") == repo]
    recent = [r for r in mine if (_ts(r.get("started")) or 0) >= now - DAY and r.get("status") == "completed"]
    ok = sum(1 for r in recent if r.get("conclusion") == "success")
    bad = sum(1 for r in recent if r.get("conclusion") in ("failure", "timed_out", "startup_failure"))
    red = sorted({str(f.get("workflow") or f.get("name") or "") for f in failing if isinstance(f, dict) and f.get("repo") == repo})
    stuck = sum(1 for a in active if isinstance(a, dict) and a.get("repo") == repo and a.get("stuck"))
    judged = ok + bad
    return {"runs_24h": len(recent), "successes_24h": ok, "failures_24h": bad, "success_rate_24h": round(ok / judged, 3) if judged else None, "red_workflows": red, "stuck_runs": stuck}


def alerts_part(repo, alerts):
    """The open alerts about the repository, with the counts by sentinel and by level and the list (without the long details)."""
    mine = [a for a in alerts if isinstance(a, dict) and a.get("repo") == repo and not a.get("muted_until")]
    by_sentinel, by_level = {}, {}
    for a in mine:
        by_sentinel[a.get("sentinel", "")] = by_sentinel.get(a.get("sentinel", ""), 0) + 1
        by_level[a.get("level", "")] = by_level.get(a.get("level", ""), 0) + 1
    items = [{"id": a.get("id"), "code": a.get("code"), "level": a.get("level"), "sentinel": a.get("sentinel"), "title": str(a.get("title") or "")[:200], "created_at": a.get("created_at")}
             for a in sorted(mine, key=lambda x: (LEVELS.index(x["level"]) if x.get("level") in LEVELS else 9, str(x.get("id"))))][:50]
    return {"total": len(mine), "by_sentinel": by_sentinel, "by_level": by_level, "items": items}


def activity_part(repo, runs, now):
    stamps = [t for t in (_ts(r.get("started")) for r in runs if isinstance(r, dict) and r.get("repo") == repo) if t is not None]
    last = max(stamps) if stamps else None
    return {"last_run_at": datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if last else None, "runs_7d": sum(1 for t in stamps if t >= now - 7 * DAY),
            "idle_days": round((now - last) / DAY, 1) if last else None}


def state_of(ci, alerts, seen):
    """bad / warn / ok / unknown. `seen` says whether anything could be judged (the monitor holds runs of the repository, a sentinel looked at it, and some sentinel is able to look)."""
    levels = alerts["by_level"]
    if ci["red_workflows"] or levels.get("critical") or levels.get("error"):
        return "bad"
    if levels.get("warning") or ci["stuck_runs"]:
        return "warn"
    return "ok" if seen else "unknown"


def risk_of(ci, alerts):
    points = RISK["red"] * len(ci["red_workflows"]) + RISK["stuck"] * ci["stuck_runs"]
    for level in LEVELS:
        points += RISK[level] * alerts["by_level"].get(level, 0)
    return points


def repo_view(repo, runs, failing, active, alerts, readiness, sources, ecosystem="", now=0.0):
    """The whole health of one repository. `readiness` is the row of the readiness of the releases for this repository ({"entries", "next"...}) or None; `sources` {sentinel: lifecycle}."""
    ci = ci_part(repo, runs, failing, active, now)
    al = alerts_part(repo, alerts)
    act = activity_part(repo, runs, now)
    blind = sorted(name for name, life in (sources or {}).items() if life not in ("healthy", "off"))
    looked = any(life == "healthy" for life in (sources or {}).values())
    nobody = bool(sources) and not looked and (bool(blind) or not act["runs_7d"])      # every sentinel is in error, paused or degraded, or all are off and nothing ran this week
    seen = bool(ci["runs_24h"] or act["last_run_at"] or al["total"]) and not nobody
    return {"repo": repo, "ecosystem": ecosystem, "state": state_of(ci, al, seen), "risk": risk_of(ci, al), "ci": ci, "alerts": al, "readiness": readiness or None, "activity": act,
            "sources": dict(sources or {}), "not_fully_seen": blind}


def matches(view, ecosystem="", severity="", text="", label=""):
    """The filters of the team view: an ecosystem (key or label), a least severity (the state asked for or a worse one) and a piece of the name."""
    if ecosystem and view["ecosystem"] != ecosystem:
        return False
    if label and label.lower() not in (view.get("ecosystem_label") or view["ecosystem"] or "").lower():
        return False
    if severity in STATES and STATES.index(view["state"]) < STATES.index(severity):
        return False
    return not text or text.lower() in view["repo"].lower()


def team_view(views, ecosystem="", severity="", text="", label="", limit=200):
    """The ranking and the totals. `views` are the results of `repo_view`; the filters narrow the list AND the totals (what you see is what is counted); `all` says how many there were before them."""
    chosen = [v for v in views if matches(v, ecosystem, severity, text, label)]
    ranking = sorted(chosen, key=lambda v: (-v["risk"], -STATES.index(v["state"]), v["repo"]))
    totals = {s: sum(1 for v in chosen if v["state"] == s) for s in STATES}
    totals["not_fully_seen"] = sum(1 for v in chosen if v["not_fully_seen"])      # on top of the states: the repositories that some sentinel could not read
    by_eco = {}
    for v in chosen:
        row = by_eco.setdefault(v["ecosystem"] or "", {"repos": 0, "bad": 0, "warn": 0, "ok": 0, "unknown": 0, "risk": 0})
        row["repos"] += 1
        row[v["state"]] += 1
        row["risk"] += v["risk"]
    by_sentinel, by_level = {}, {}
    for v in chosen:
        for name, n in v["alerts"]["by_sentinel"].items():
            by_sentinel[name] = by_sentinel.get(name, 0) + n
        for level, n in v["alerts"]["by_level"].items():
            by_level[level] = by_level.get(level, 0) + n
    slim = [{k: v[k] for k in ("repo", "ecosystem", "state", "risk")} | {"red_workflows": len(v["ci"]["red_workflows"]), "alerts": v["alerts"]["total"], "failures_24h": v["ci"]["failures_24h"],
            "last_run_at": v["activity"]["last_run_at"], "release_next": (v["readiness"] or {}).get("next"), "not_fully_seen": v["not_fully_seen"]} for v in ranking[:limit]]
    return {"schema": 1, "all": len(views), "shown": len(chosen), "truncated": len(chosen) > limit, "totals": totals, "by_ecosystem": dict(sorted(by_eco.items())), "alerts": {"by_sentinel": by_sentinel, "by_level": by_level},
            "ranking": slim, "filters": {"ecosystem": ecosystem, "severity": severity, "q": text, "label": label}}
