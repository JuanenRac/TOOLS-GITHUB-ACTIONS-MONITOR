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


def group_by_repo(items):
    """{repo: [item, ...]} in one pass (the items that are not dictionaries or have no repository are left out): the views then take their own list instead of filtering all of them."""
    out = {}
    for item in items or []:
        if isinstance(item, dict) and item.get("repo"):
            out.setdefault(item["repo"], []).append(item)
    return out


def summarize_runs(runs, now):
    """{repo: {"last": newest start, "runs_24h", "successes_24h", "failures_24h", "runs_7d"}} in one pass over ALL the runs the monitor holds. The page only receives the 600 newest runs of the whole account; the health of
    a repository must not depend on that cut, so it is counted here, before the cut."""
    out = {}
    for run in runs or []:
        if not isinstance(run, dict) or not run.get("repo"):
            continue
        t = _ts(run.get("started"))
        row = out.setdefault(run["repo"], {"last": None, "runs_24h": 0, "successes_24h": 0, "failures_24h": 0, "runs_7d": 0})
        if t is None:
            continue
        if row["last"] is None or t > row["last"]:
            row["last"] = t
        if t >= now - 7 * DAY:
            row["runs_7d"] += 1
        if t >= now - DAY and run.get("status") == "completed":
            row["runs_24h"] += 1
            if run.get("conclusion") == "success":
                row["successes_24h"] += 1
            elif run.get("conclusion") in ("failure", "timed_out", "startup_failure"):
                row["failures_24h"] += 1
    return out


ACTIVE_WORKFLOWS, ACTIVE_BRANCHES = 30, 10      # what the health of one repository lists of its runs that are still going (the numbers carry the rest)


def active_part(repo, active, all_runs=True):
    """The runs of the repository that are still going, BY WORKFLOW: {"runs", "running", "queued", "all", "workflows": [{"workflow", "running", "queued", "branches": [{"branch", "status", "id", "url"}]}]}.
    Two runs of the same workflow that go at once (a release in parallel, a matrix by branch) are both counted and listed, with the newest run of each branch; with `all_runs` off (`fleet.show_all_active`) a
    workflow shows only its newest run, as a list that keeps one run per workflow would. `running` is `in_progress`; everything else that waits (queued, waiting, pending) is `queued`."""
    by_workflow = {}
    for run in active or []:
        if isinstance(run, dict) and run.get("repo") == repo:
            by_workflow.setdefault(str(run.get("name") or run.get("workflow") or ""), []).append(run)
    rows = []
    for name, runs in by_workflow.items():
        runs = sorted(runs, key=lambda r: str(r.get("started") or ""), reverse=True)
        runs = runs if all_runs else runs[:1]
        newest, seen = [], set()
        for run in runs:      # the newest run of each branch (the list is already newest first)
            key = str(run.get("branch") or "")
            if key not in seen:
                seen.add(key)
                newest.append({"branch": key, "status": run.get("status"), "id": run.get("id"), "url": run.get("url")})
        running = sum(1 for r in runs if r.get("status") == "in_progress")
        rows.append({"workflow": name, "running": running, "queued": len(runs) - running, "branches": newest[:ACTIVE_BRANCHES]})
    rows.sort(key=lambda r: (-(r["running"] + r["queued"]), r["workflow"].lower()))
    running, queued = sum(r["running"] for r in rows), sum(r["queued"] for r in rows)
    return {"runs": running + queued, "running": running, "queued": queued, "all": bool(all_runs), "workflows": rows[:ACTIVE_WORKFLOWS]}


def ci_part(repo, runs, failing, active, now, summary=None, all_active=True):
    """The CI of the repository: runs of the last 24 hours and the red and stuck ones. `failing` are the red workflows ({"repo", "workflow"...}), `active` the runs in progress or waiting."""
    if summary is not None:      # counted over every run of the account, not over the cut the page receives
        recent_n, ok, bad = summary["runs_24h"], summary["successes_24h"], summary["failures_24h"]
    else:
        mine = [r for r in runs if isinstance(r, dict) and r.get("repo") == repo]
        recent = [r for r in mine if (_ts(r.get("started")) or 0) >= now - DAY and r.get("status") == "completed"]
        ok = sum(1 for r in recent if r.get("conclusion") == "success")
        bad = sum(1 for r in recent if r.get("conclusion") in ("failure", "timed_out", "startup_failure"))
        recent_n = len(recent)
    red = sorted({str(f.get("workflow") or f.get("name") or "") for f in failing if isinstance(f, dict) and f.get("repo") == repo})
    stuck = sum(1 for a in active if isinstance(a, dict) and a.get("repo") == repo and a.get("stuck"))
    judged = ok + bad
    return {"runs_24h": recent_n, "successes_24h": ok, "failures_24h": bad, "success_rate_24h": round(ok / judged, 3) if judged else None, "red_workflows": red, "stuck_runs": stuck,
            "active": active_part(repo, active, all_active)}


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


def activity_part(repo, runs, now, summary=None):
    if summary is not None:
        last = summary["last"]
        return {"last_run_at": datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if last else None, "runs_7d": summary["runs_7d"],
                "idle_days": round((now - last) / DAY, 1) if last else None}
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


def repo_view(repo, runs, failing, active, alerts, readiness, sources, ecosystem="", now=0.0, summary=None, all_active=True):
    """The whole health of one repository. `readiness` is the row of the readiness of the releases for this repository ({"entries", "next"...}) or None; `sources` {sentinel: lifecycle}."""
    ci = ci_part(repo, runs, failing, active, now, summary, all_active)
    al = alerts_part(repo, alerts)
    act = activity_part(repo, runs, now, summary)
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
