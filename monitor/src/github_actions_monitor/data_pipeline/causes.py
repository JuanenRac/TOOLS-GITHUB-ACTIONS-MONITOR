# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One root cause, one alert; and which jobs of a big workflow fail.

  * `ci.group.reusable` (off): the red workflows that call the SAME reusable workflow (`uses: owner/shared/.github/workflows/x.yml`) have most likely one cause. The red list gets a group row
    (the shared workflow, how many workflows and repositories it touches) and the notification of the new reds says it once, with the number affected, instead of once for each.
    A group needs `ci.group.min` workflows (default 2). The red rows themselves are never hidden.
  * `ci.failed_jobs` (off): for a red run of an umbrella workflow with many jobs (a matrix of platforms) the monitor reads the jobs of that run once (one call, a few runs per cycle, kept
    while the run does not change) and the red row says WHICH jobs failed, grouped by platform (the system in the name of the job, else the first parameter of the matrix, else the
    part before " / " of a job of a reusable workflow).
Pure functions: no network, no clock.
"""
import re

from github_actions_monitor.security.redactor import redact

DEFAULTS = {"group": {"reusable": False, "min": 2}, "failed_jobs": {"enabled": False, "max_per_cycle": 4, "group_by": "auto"}}
GROUP_BY = ("auto", "platform", "matrix", "prefix")
PLATFORM_RE = re.compile(r"(ubuntu|windows|macos|linux|android|ios|osx|web|wasm|freebsd|arm64|x64|x86)[\w.\-]*", re.IGNORECASE)
POLICY = {"group": dict(DEFAULTS["group"]), "failed_jobs": dict(DEFAULTS["failed_jobs"])}
BAD = ("failure", "timed_out", "startup_failure", "cancelled")


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    ci = (config or {}).get("ci")
    ci = ci if isinstance(ci, dict) else {}
    group = ci.get("group") if isinstance(ci.get("group"), dict) else {}
    jobs = ci.get("failed_jobs") if isinstance(ci.get("failed_jobs"), dict) else {}
    return {"group": {"reusable": group.get("reusable") is True, "min": _int(group.get("min"), 2, 50, 2)},
            "failed_jobs": {"enabled": jobs.get("enabled") is True, "max_per_cycle": _int(jobs.get("max_per_cycle"), 1, 50, 4), "group_by": jobs.get("group_by") if jobs.get("group_by") in GROUP_BY else "auto"}}


def configure(config):
    POLICY.clear()
    POLICY.update(settings(config))


def reusable_paths(run_body):
    """The reusable workflows a run of the API calls, as `owner/repo/.github/workflows/file.yml` (no ref), at most three. [] when none."""
    out = []
    for item in (run_body or {}).get("referenced_workflows") or []:
        path = str((item or {}).get("path") or "").split("@")[0]
        if path and path not in out:
            out.append(path)
    return out[:3]


def groups(rows, policy=None):
    """[{"workflow": shared path, "count", "repos": [...], "items": [{"repo", "workflow"}]}] for the red rows that share a reusable workflow; biggest first. [] when the setting is off."""
    cfg = (policy or POLICY)["group"]
    if not cfg["reusable"]:
        return []
    by = {}
    for row in rows:
        for path in row.get("reusable") or []:
            by.setdefault(path, []).append(row)
    out = []
    for path, items in by.items():
        if len(items) >= cfg["min"]:
            out.append({"workflow": path, "count": len(items), "repos": sorted({r["repo"] for r in items}), "items": [{"repo": r["repo"], "workflow": r.get("workflow")} for r in items]})
    return sorted(out, key=lambda g: (-g["count"], g["workflow"]))


def group_events(events, policy=None):
    """Replaces the new-red events that share a reusable workflow by ONE event that says how many are affected. The others pass untouched."""
    cfg = (policy or POLICY)["group"]
    if not cfg["reusable"]:
        return events
    by = {}
    for event in events:
        if event.get("kind") == "red_new":
            for path in event.get("reusable") or []:
                by.setdefault(path, []).append(event)
                break      # an event belongs to the first shared workflow it names
    chosen = {path: items for path, items in by.items() if len(items) >= cfg["min"]}
    if not chosen:
        return events
    from github_actions_monitor import i18n
    out, done = [], set()
    for event in events:
        path = next((p for p in event.get("reusable") or [] if p in chosen), None) if event.get("kind") == "red_new" else None
        if path is None:
            out.append(event)
        elif path not in done:
            done.add(path)
            members = chosen[path]
            repos = sorted({m.get("repo") for m in members})
            made = dict(members[0])
            made.update({"repo": members[0].get("repo") if len(repos) == 1 else "", "level": "bad", "grouped": len(members), "text": i18n.t("evt.red_cause", shared=path.rsplit("/", 1)[-1], count=len(members), repos=len(repos)),
                         "args": {"shared": path, "count": len(members), "repos": repos, "workflows": [(m.get("args") or {}).get("workflow") for m in members]}})
            out.append(made)
    return out


def platform_of(name, mode="auto"):
    """The group a job belongs to, from its name: `build (ubuntu-latest, 3.11)` -> ubuntu-latest; `deploy / test` of a reusable workflow -> deploy."""
    name = str(name or "")
    inner = re.search(r"\(([^)]*)\)", name)
    first = inner.group(1).split(",")[0].strip() if inner else ""
    prefix = name.split(" / ")[0].strip() if " / " in name else ""
    found = PLATFORM_RE.search(name)
    if mode == "platform":
        return found.group(0) if found else name
    if mode == "matrix":
        return first or name
    if mode == "prefix":
        return prefix or name
    return (found.group(0) if found else (first or prefix or name)).strip() or name


def summarize_jobs(body, mode="auto"):
    """{"total", "failed", "groups": [{"group", "failed", "total", "jobs": [names of the failed ones]}]} from the answer of `actions/runs/{id}/jobs`; only the groups with a failure."""
    jobs = [j for j in (body or {}).get("jobs") or [] if isinstance(j, dict)]
    seen = {}
    for job in jobs:
        key = " ".join(redact(platform_of(job.get("name"), mode)).split())[:80]      # the key of a group is the name of a job when it has no platform: cut and cleaned like the names of the jobs
        slot = seen.setdefault(key, {"group": key, "failed": 0, "total": 0, "jobs": []})
        slot["total"] += 1
        if job.get("conclusion") in BAD:
            slot["failed"] += 1
            slot["jobs"].append(" ".join(redact(str(job.get("name"))).split())[:80])
    shown = sorted((g for g in seen.values() if g["failed"]), key=lambda g: (-g["failed"], g["group"]))
    return {"total": len(jobs), "failed": sum(g["failed"] for g in shown), "groups": [{**g, "jobs": g["jobs"][:8]} for g in shown[:12]]}
