# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the collaboration views make of the runs and of the answers of GitHub. Pure functions: nothing is read and nothing is written here.

Every "proposal" is only a line that says which action of integrations/ghactions.py a person could confirm; nothing here runs it."""
import calendar
import fnmatch
import time

QUEUED = ("queued", "pending", "requested")
RUNNING = ("in_progress",)
BAD = ("failure", "timed_out", "startup_failure")
INFRASTRUCTURE = ("startup_failure", "timed_out")      # what a re-run once may cure by itself
INACTIVITY_DAYS = 60      # after this quiet time GitHub switches off the scheduled workflows of a public repository


def epoch(text):
    try:
        return calendar.timegm(time.strptime(str(text)[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return 0


def _dicts(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _matches_any(value, patterns):
    value = str(value or "").lower()
    return any(fnmatch.fnmatchcase(value, str(p).lower()) for p in patterns or ())


def visible(runs, hide):
    """The runs whose workflow name is not hidden (`teamwork.hide_workflows`, patterns)."""
    return [r for r in _dicts(runs) if not _matches_any(r.get("name"), hide)]


def _brief(run):
    return {"repo": run.get("repo"), "run": run.get("id"), "workflow": run.get("name"), "branch": run.get("branch"), "event": run.get("event"), "actor": run.get("actor"), "since": run.get("started"), "url": run.get("url")}


def waiting(runs):
    """The two ways of waiting. "person": a person has to act - "environment" (a deployment held by the protection of an environment), "fork" (a workflow of a fork nobody approved) or "check"
    (another run that asks for an action). "machine": nobody has to act, a runner has not taken it yet."""
    out = {"person": [], "machine": []}
    for run in _dicts(runs):
        if run.get("status") == "waiting":
            out["person"].append(dict(_brief(run), kind="environment"))
        elif run.get("conclusion") == "action_required":
            out["person"].append(dict(_brief(run), kind="fork" if run.get("fork") is True else "check"))
        elif run.get("status") in QUEUED:
            out["machine"].append(dict(_brief(run), kind="queued"))
    return out


def lanes(runs):
    """The newest finished run of each lane (repository, workflow file, branch), the failing ones first."""
    newest = {}
    for run in _dicts(runs):
        if run.get("status") != "completed" or run.get("conclusion") in (None, "action_required", "skipped", "cancelled", "neutral"):
            continue
        key = (run.get("repo"), run.get("path") or run.get("name"), run.get("branch"))
        if key not in newest or str(run.get("started")) > str(newest[key].get("started")):
            newest[key] = run
    rows = [dict(_brief(r), conclusion=r["conclusion"], red=r["conclusion"] in BAD) for r in newest.values()]
    return sorted(rows, key=lambda r: (not r["red"], str(r["repo"]), str(r["workflow"]), str(r["branch"])))


def bot_of(pull, authors, branches, labels):
    """Why a pull request is a dependency update: "author", "branch", "label" or ""."""
    login = str((pull.get("user") or {}).get("login") or "")
    if login.lower() in {str(a).lower() for a in authors or ()}:
        return "author"
    if _matches_any((pull.get("head") or {}).get("ref"), branches):
        return "branch"
    if {str(x.get("name") or "").lower() for x in _dicts(pull.get("labels"))} & {str(x).lower() for x in labels or ()}:
        return "label"
    return ""


def pull_row(repo, pull, detail, checks, bot):
    """One open pull request. `detail` is its full answer (for mergeable_state), `checks` the check runs of its head (None when not read)."""
    state = str((detail or {}).get("mergeable_state") or "unknown")
    failing = None if checks is None else sum(1 for c in _dicts(checks) if c.get("conclusion") in BAD)
    if state == "behind":
        group = "pending_rebase"
    elif state == "dirty" or state == "blocked" or failing:
        group = "needs_action"
    elif state in ("clean", "has_hooks") and failing == 0:
        group = "mergeable"
    else:
        group = "unknown"      # not known is not mergeable
    return {"repo": repo, "number": pull.get("number"), "title": str(pull.get("title") or "")[:120], "author": str((pull.get("user") or {}).get("login") or ""), "url": pull.get("html_url"),
            "draft": pull.get("draft") is True, "bot": bot, "state": state, "failing": failing, "behind": state == "behind", "group": group}


def vulnerabilities(repo, alerts, now):
    """The critical and high Dependabot alerts open in one repository: how many of each and the age of the oldest. None when there are none."""
    found = []
    for alert in _dicts(alerts):
        level = str(((alert.get("security_advisory") or {}).get("severity") or (alert.get("security_vulnerability") or {}).get("severity") or "")).lower()
        if level in ("critical", "high"):
            found.append((epoch(alert.get("created_at")), level, alert.get("html_url")))
    if not found:
        return None
    oldest = min(found)
    return {"repo": repo, "critical": sum(1 for f in found if f[1] == "critical"), "high": sum(1 for f in found if f[1] == "high"), "oldest_days": int((now - oldest[0]) // 86400) if oldest[0] else None, "url": oldest[2]}


def dismissals(repo, kind, alerts, allowed):
    """Security alerts somebody dismissed: who, why and when. `authorized` is False when the person is not in `teamwork.dismiss_allowed` (None when that list is empty: nothing to compare)."""
    out = []
    names = {str(a).lower() for a in allowed or ()}
    for alert in _dicts(alerts):
        who = str((alert.get("dismissed_by") or {}).get("login") or "")
        if not alert.get("dismissed_at"):
            continue
        out.append({"repo": repo, "kind": kind, "number": alert.get("number"), "who": who, "reason": str(alert.get("dismissed_reason") or "")[:60], "at": alert.get("dismissed_at"),
                    "url": alert.get("html_url"), "authorized": (who.lower() in names) if names else None})
    return out


def policy_matches(runs, patterns):
    """The runs still going that match a line `repository:workflow:branch` (patterns) of `teamwork.cancel_policy`."""
    out = []
    for run in _dicts(runs):
        if run.get("status") not in RUNNING + QUEUED + ("waiting",):
            continue
        for line in patterns or ():
            parts = str(line).split(":")
            if len(parts) == 3 and all(_matches_any(value, [part]) for value, part in zip((run.get("repo"), run.get("name"), run.get("branch")), parts)):
                out.append(dict(_brief(run), rule=line))
                break
    return out


def old_runs(runs, status, hours, now):
    return [_brief(r) for r in _dicts(runs) if r.get("status") in status and epoch(r.get("started")) and now - epoch(r.get("started")) > hours * 3600]


def proposal(action, repo, number, why, detail=""):
    return {"action": action, "repo": repo, "number": number, "why": why, "detail": str(detail)[:160]}


def proposals(runs, pulls, policy, workflows, cfg, now, ageing=()):
    """What a person could confirm: close the update of a bot whose checks fail, cancel what waits too long or breaks the policy, force the cancel of what runs for too long, update a branch that is
    behind, enable a workflow GitHub switched off for inactivity and enable again, before that happens, a scheduled workflow of a repository that has been quiet for a long time."""
    out = []
    for row in pulls:
        if row["bot"] and row["failing"]:
            out.append(proposal("close_pr", row["repo"], row["number"], "bot_red", row["title"]))
        elif row["behind"] and not row["draft"]:
            out.append(proposal("update_branch", row["repo"], row["number"], "behind", row["title"]))
    out += [proposal("cancel", r["repo"], r["run"], "queued_long", r["workflow"]) for r in old_runs(runs, QUEUED, cfg["queued_hours"], now)]
    out += [proposal("force_cancel", r["repo"], r["run"], "stuck", r["workflow"]) for r in old_runs(runs, RUNNING, cfg["stuck_hours"], now)]
    out += [proposal("cancel", r["repo"], r["run"], "policy", f"{r['workflow']} ({r['rule']})") for r in policy]
    out += [proposal("enable_workflow", w["repo"], w["id"], "inactive_workflow", w["name"]) for w in workflows]
    out += [proposal("enable_workflow", w["repo"], w["id"], "keep_alive", f"{w['days_left']} - {w['name']}") for w in sorted(ageing, key=lambda w: (w["days_left"], w["repo"]))]
    seen, unique = set(), []
    for item in out:
        key = (item["action"], item["repo"], item["number"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:100]


def rerun_candidates(runs, done, now, max_age_hours=24):
    """The runs a single automatic re-run may cure: first attempt, ended by the infrastructure (did not start or hit the time limit), recent, not of a fork and never tried before."""
    out = []
    for run in _dicts(runs):
        if run.get("status") == "completed" and run.get("conclusion") in INFRASTRUCTURE and run.get("attempt") == 1 and run.get("fork") is not True and str(run.get("id")) not in done \
                and epoch(run.get("started")) and now - epoch(run.get("started")) <= max_age_hours * 3600:
            out.append(run)
    return out


def failed_again(runs, done):
    """The runs that were re-run automatically and failed once more."""
    return [_brief(r) for r in _dicts(runs) if str(r.get("id")) in done and r.get("status") == "completed" and r.get("conclusion") in BAD and isinstance(r.get("attempt"), int) and r["attempt"] >= 2]


def dispatch_values(inputs, given):
    """({name: text}, "") or ({}, "name: reason") for the values typed in the form against the inputs the workflow declares."""
    given = given if isinstance(given, dict) else {}
    names = {i["name"] for i in inputs}
    unknown = [k for k in given if k not in names]
    if unknown:
        return {}, f"{str(unknown[0])[:40]}: unknown"
    out = {}
    for item in inputs:
        name, value = item["name"], given.get(item["name"])
        if value is None or value == "":
            if item.get("required") and item.get("default") in (None, ""):
                return {}, f"{name}: required"
            continue
        value = str(value).strip().lower() if item.get("type") == "boolean" else str(value)
        if len(value) > 1000 or any(ord(c) < 32 for c in value):
            return {}, f"{name}: text"
        if item.get("type") == "boolean" and value not in ("true", "false"):
            return {}, f"{name}: boolean"
        if item.get("type") == "choice" and value not in (item.get("options") or []):
            return {}, f"{name}: choice"
        if item.get("type") == "number":
            try:
                float(value)
            except ValueError:
                return {}, f"{name}: number"
        out[name] = value
    return out, ""
