# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The report "what changed": from the finished runs of the ledger, which repositories got worse or better and which workflows started or stopped failing between the two windows. Pure functions.
The ledger keeps no code or repository for the alerts of the collaboration sentinel, so they appear as counts (opened and closed in the window), never by name."""
from github_actions_monitor.compare import metrics


def _per_repo(runs):
    out = {}
    for _, conclusion, _, repo, _ in runs:
        row = out.setdefault(repo, {"good": 0, "bad": 0})
        row["good" if conclusion == "success" else "bad"] += 1
    return out


def _per_workflow(runs):
    out = {}
    for _, conclusion, _, repo, workflow in runs:
        row = out.setdefault((repo, workflow), {"good": 0, "bad": 0})
        row["good" if conclusion == "success" else "bad"] += 1
    return out


def build(ledger, wins, days, cfg, zone=None):
    """{"worse": [...], "better": [...], "new_failures": [...], "resolved_failures": [...], "reason": str or None} with at most `top_changes` rows each, in a stable order."""
    top = cfg["top_changes"]
    now_runs = metrics.window_runs(ledger, wins["now"], days, cfg["workdays"], zone)
    base_runs = metrics.window_runs(ledger, wins["base"], days, cfg["workdays"], zone)
    if not now_runs and not base_runs:
        return {"worse": [], "better": [], "new_failures": [], "resolved_failures": [], "reason": "no_data"}
    now_repo, base_repo = _per_repo(now_runs), _per_repo(base_runs)
    moved = []
    for repo in sorted(set(now_repo) & set(base_repo)):
        a, b = now_repo[repo], base_repo[repo]
        if a["good"] + a["bad"] < cfg["min_repo_runs"] or b["good"] + b["bad"] < cfg["min_repo_runs"]:
            continue
        rate_now, rate_base = a["bad"] / (a["good"] + a["bad"]), b["bad"] / (b["good"] + b["bad"])
        if abs(rate_now - rate_base) >= 1e-9:
            moved.append({"repo": repo, "red_rate_now": round(rate_now, 4), "red_rate_base": round(rate_base, 4), "delta": round(rate_now - rate_base, 4), "runs_now": a["good"] + a["bad"], "runs_base": b["good"] + b["bad"]})
    worse = sorted((m for m in moved if m["delta"] > 0), key=lambda m: (-m["delta"], m["repo"]))[:top]
    better = sorted((m for m in moved if m["delta"] < 0), key=lambda m: (m["delta"], m["repo"]))[:top]
    now_wf, base_wf = _per_workflow(now_runs), _per_workflow(base_runs)
    new = [{"repo": k[0], "workflow": k[1], "failures": v["bad"]} for k, v in now_wf.items() if v["bad"] and not base_wf.get(k, {"bad": 0})["bad"]]
    resolved = [{"repo": k[0], "workflow": k[1], "failures_before": v["bad"]} for k, v in base_wf.items() if v["bad"] and k in now_wf and not now_wf[k]["bad"]]
    new.sort(key=lambda r: (-r["failures"], r["repo"], r["workflow"]))
    resolved.sort(key=lambda r: (-r["failures_before"], r["repo"], r["workflow"]))
    return {"worse": worse, "better": better, "new_failures": new[:top], "resolved_failures": resolved[:top], "reason": None}

