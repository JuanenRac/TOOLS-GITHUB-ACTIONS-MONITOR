# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""THE rule of "red on main", small enough for the lite edition (which does not load the sentinel) and used by the sentinel too, so that both editions count the same.

A workflow is red when the LAST COMPLETED run of its file on the DEFAULT branch failed; cancelled, skipped, neutral and stale runs say nothing and are ignored (an older failure is not
hidden by them). The sentinel knows the default branch of each repository; the lite edition does not read it, so it guesses (`main`, then `master`, then the branch with most runs) and says
the figure is approximate (`approx`). It is also approximate when the list of runs of a repository is as long as the sample asked for: an older workflow may be hidden beyond it.

Which runs may decide (the block `ci` of the configuration):
  * only runs of an event in `ci.red_events` (push, schedule, workflow_dispatch, merge_group by default): a pull request, a comment or an issue never makes a branch red;
  * runs of a pull request that comes from a FORK do not count, even when the fork's branch is called `main` (the head repository differs from the repository of the run) unless `ci.count_fork_runs`;
  * a run that waits for an approval (`action_required`, or a job `waiting` for an environment) is neither red nor queued: it is "awaiting approval";
  * a workflow whose last run is older than `ci.inactive_days` is "inactive", not red for ever;
  * a red nobody has attended to (its failing run is older than `ci.red_age_days`, 30 by default, and nothing newer of the events that decide has run) AGES: it becomes "inactive" too (`ci.red_ages`);
  * the merge queue of the default branch (branches `gh-readonly-queue/<branch>/...`, event merge_group) is its own lane, shown as "merge queue";
  * `ci.extra_branches` (patterns) adds maintenance branches to the watched ones; by default only the default branch is.
"""
import fnmatch
import time
from datetime import datetime

from github_actions_monitor import i18n

BAD = ("failure", "timed_out", "startup_failure")      # `action_required` is not a failure: it is a run that waits for a person to approve it (see is_awaiting)
IGNORED = ("cancelled", "skipped", "neutral", "stale")
RED_EVENTS = ("push", "schedule", "workflow_dispatch", "merge_group")      # the events whose failure on the branch is a red of the repository itself (setting ci.red_events)
AUTOMATION_EVENTS = ("issues", "issue_comment", "pull_request_target", "pull_request_review", "pull_request_review_comment", "discussion", "discussion_comment", "label", "watch", "fork", "create", "delete")
SERVICE_EVENTS = ("schedule", "workflow_dispatch", "repository_dispatch", "dynamic")
RELEASE_EVENTS = ("release", "registry_package")
QUEUE_PREFIX = "gh-readonly-queue/"
AWAITING_DAYS = 14
DEFAULT_INACTIVE_DAYS = 90
DEFAULT_RED_AGE_DAYS = 30
POLICY = {"events": RED_EVENTS, "fork_runs": False, "automation": False, "inactive_days": DEFAULT_INACTIVE_DAYS, "red_age_days": DEFAULT_RED_AGE_DAYS, "branches": (), "disabled_apart": True}      # replaced by configure(): the whole monitor shares one rule


def configure(config):
    """Reads the block `ci` of the configuration; a missing or invalid value keeps the conservative default."""
    block = (config or {}).get("ci")
    block = block if isinstance(block, dict) else {}
    events = block.get("red_events")
    POLICY["events"] = tuple(e for e in events if isinstance(e, str) and e) if isinstance(events, (list, tuple)) and events else RED_EVENTS
    POLICY["fork_runs"] = block.get("count_fork_runs") is True
    POLICY["automation"] = block.get("automation_counts") is True
    days = block.get("inactive_days")
    POLICY["inactive_days"] = days if isinstance(days, int) and not isinstance(days, bool) and 0 <= days <= 3650 else DEFAULT_INACTIVE_DAYS
    age = block.get("red_age_days")
    age = age if isinstance(age, int) and not isinstance(age, bool) and 1 <= age <= 3650 else DEFAULT_RED_AGE_DAYS
    POLICY["red_age_days"] = age if block.get("red_ages") is not False else 0      # 0 = a red never ages
    POLICY["disabled_apart"] = block.get("disabled_apart") is not False
    extra = block.get("extra_branches")
    POLICY["branches"] = tuple(b for b in extra if isinstance(b, str) and b) if isinstance(extra, (list, tuple)) else ()


def workflow_key(run):
    return run.get("path") or run.get("name") or ""


def is_dynamic(run):
    """A run that GitHub creates for itself (event `dynamic`, a `dynamic/...` path: Dependabot updates, the dependency graph, the default CodeQL, the review and the agent of Copilot): it is not a
    build of the repository and never decides. The monitor keeps only the name of the file of a run, so `dynamic` is also a flag written when the run is read, from the whole path."""
    return run.get("event") == "dynamic" or run.get("dynamic") is True or str(run.get("path") or "").startswith("dynamic/")


def service_name(path, name=""):
    """Which service of GitHub a `dynamic/...` workflow is: dependabot (the updates), graph (the dependency graph and its submissions), copilot (review and agent), codeql (the default setup) or other."""
    text = (str(path or "") + " " + str(name or "")).lower()
    if "graph" in text or "dependency submission" in text:
        return "graph"
    if "dependabot" in text:
        return "dependabot"
    if "copilot" in text:
        return "copilot"
    if "codeql" in text or "code-scanning" in text:
        return "codeql"
    return "other"


def service_rows(runs, now=None, policy=None):
    """The services of GitHub whose last finished run failed, one row each: they are not a red of the repository (nothing in it can be fixed by a push) but they are not silent either.
    A failing Dependabot update is a warning (the dependencies are not being updated); the others are information. A service that has not run for ci.inactive_days is left out."""
    policy = policy or POLICY
    now = time.time() if now is None else now
    last = {}
    finished = (r for r in runs if is_dynamic(r) and r.get("status") == "completed" and r.get("conclusion") and r.get("conclusion") not in IGNORED and not is_awaiting(r))
    for run in sorted(finished, key=lambda r: r.get("started") or ""):
        last[(run.get("repo"), run.get("service") or service_name(run.get("path"), run.get("name")), workflow_key(run))] = run
    out = []
    for (repo, service, _key), run in last.items():
        stamp = _epoch(run.get("started"))
        if run.get("conclusion") not in BAD or (policy["inactive_days"] and stamp is not None and now - stamp > policy["inactive_days"] * 86400):
            continue
        out.append({"repo": repo, "service": service, "workflow": run.get("name") or workflow_key(run), "conclusion": run.get("conclusion"), "since": run.get("started"), "url": run.get("url"),
                    "level": "warning" if service == "dependabot" else "info"})
    return sorted(out, key=lambda r: (r["level"] != "warning", str(r["repo"]), r["service"]))


def is_awaiting(run):
    """A run that waits for a person: a pull request of a fork or a first contribution that nobody approved yet (`action_required`), or a job held by the protection of an environment (`waiting`).
    It is neither red nor in the queue of runners."""
    return run.get("conclusion") == "action_required" or run.get("status") == "waiting"


def is_fork_run(run):
    return run.get("fork") is True


def origin_counts(run, policy=None):
    """True when the run may decide the colour of its branch: it did not come from a fork (unless ci.count_fork_runs) and its event is one of ci.red_events (an unknown event counts, as before)."""
    policy = policy or POLICY
    if is_fork_run(run) and not policy["fork_runs"]:
        return False
    event = run.get("event")
    return not event or event in policy["events"]


def lane(run, default, policy=None):
    """Where a run belongs: "" = the default branch, "queue" = the merge queue of the default branch, the branch name = a maintenance branch (ci.extra_branches), None = not watched."""
    policy = policy or POLICY
    branch = run.get("branch")
    if branch == default:
        return ""
    if run.get("event") == "merge_group" and isinstance(branch, str) and branch.startswith(QUEUE_PREFIX + str(default) + "/"):
        return "queue"
    if isinstance(branch, str) and any(fnmatch.fnmatchcase(branch, pattern) for pattern in policy["branches"]):
        return branch
    return None


def workflow_kind(events):
    """build | release | automation | service, from the events a workflow was seen to run on: only issue / comment / label events = automation (triage, bots); only schedule, manual or
    dispatch = service; a release event without push or pull requests = release; anything else (push, pull_request, merge_group...) = build."""
    events = {e for e in events if e}
    if not events:
        return "build"
    if events <= set(AUTOMATION_EVENTS):
        return "automation"
    if events & set(RELEASE_EVENTS) and not events & {"push", "pull_request", "merge_group"}:
        return "release"
    if events <= set(SERVICE_EVENTS):
        return "service"
    return "build"


def completed_runs(runs, branch="main"):
    """The runs that count: completed, on the branch, not dynamic, not from a fork, of an event that decides, with a conclusion that is not cancelled / skipped / neutral / stale / action_required
    (the same definition as signstate.completed_runs)."""
    return [r for r in runs if r.get("status") == "completed" and r.get("branch") == branch and r.get("conclusion") and r.get("conclusion") not in IGNORED and not is_awaiting(r)
            and not is_dynamic(r) and origin_counts(r)]


def guess_default_branch(runs):
    """main, else master, else the branch that has most runs (None without runs). Runs of forks do not vote: their branch names are not the repository's."""
    counts = {}
    for run in runs:
        if is_dynamic(run) or is_fork_run(run):
            continue
        counts[run.get("branch")] = counts.get(run.get("branch"), 0) + 1
    for name in ("main", "master"):
        if name in counts:
            return name
    return max(counts, key=lambda b: (counts[b], str(b)), default=None)


def _epoch(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def classify(runs, branch, now=None, policy=None):
    """{"red": [...], "inactive": [...]} for the runs of ONE repository. red = the last counted run of a workflow (per lane: the branch, its merge queue, a maintenance branch)
    failed; inactive = it failed but the workflow has not run for ci.inactive_days (an abandoned workflow is not red for ever). Each item is {"run", "streak", "lane", "kind"}."""
    policy = policy or POLICY
    now = time.time() if now is None else now
    events_of, newest_of = {}, {}
    for run in runs:
        if is_dynamic(run):
            continue
        key = workflow_key(run)
        events_of.setdefault(key, set()).add(run.get("event"))
        newest_of[key] = max(newest_of.get(key, 0), _epoch(run.get("started")) or 0)
    series = {}
    for run in sorted(runs, key=lambda r: r.get("started") or ""):
        where = lane(run, branch, policy)
        if where is None or is_dynamic(run) or not origin_counts(run, policy):
            continue
        if is_awaiting(run) or run.get("status") != "completed" or not run.get("conclusion") or run.get("conclusion") in IGNORED:
            continue
        series.setdefault((where, workflow_key(run)), []).append(run)
    out = {"red": [], "inactive": []}
    for (where, key), items in series.items():
        last = items[-1]
        if last.get("conclusion") not in BAD:
            continue
        kind = workflow_kind(events_of.get(key, ()))
        if kind == "automation" and not policy["automation"]:
            continue
        streak = 0
        for run in reversed(items):
            if run.get("conclusion") in BAD:
                streak += 1
            else:
                break
        recent = [r.get("conclusion") in BAD for r in items[-10:]]
        item = {"run": last, "streak": streak, "lane": where, "kind": kind, "recent": (sum(recent), len(recent))}
        quiet_since = newest_of.get(key) or 0
        failed_at = _epoch(last.get("started")) or 0
        if policy.get("red_age_days") and failed_at and now - failed_at > policy["red_age_days"] * 86400:
            out["inactive"].append({**item, "aged": True})      # a failure nobody attended to for weeks is history, not an alarm that never ends
        elif policy["inactive_days"] and quiet_since and now - quiet_since > policy["inactive_days"] * 86400:
            out["inactive"].append(item)
        else:
            out["red"].append(item)
    return out


def awaiting_runs(runs, now=None, days=AWAITING_DAYS):
    """The runs that wait for an approval right now: any branch, any origin (a pull request of a fork is the typical case), one per run id, started in the last `days` days (an old run nobody approved is
    dropped, not a pending task)."""
    now = time.time() if now is None else now
    seen, out = set(), []
    for run in runs:
        stamp = _epoch(run.get("started"))
        if not is_awaiting(run) or is_dynamic(run) or run.get("id") in seen or (stamp is not None and now - stamp > days * 86400):
            continue
        seen.add(run.get("id"))
        out.append({"repo": run.get("repo"), "workflow": run.get("name") or workflow_key(run), "branch": run.get("branch"), "event": run.get("event"), "fork": is_fork_run(run), "since": run.get("started"), "url": run.get("url"), "id": run.get("id")})
    return out


def split_disabled(red, perms):
    """(kept, apart): the red rows whose workflow the owner switched off by hand (state `disabled_manually`, read with the permissions of each repository) go apart: switching a workflow off is the answer
    to its failure, and its last run stays red for ever. A workflow GitHub switched off for inactivity is not here: that one is not a decision of the owner. Rows are matched by the name of the file."""
    if not POLICY["disabled_apart"]:
        return list(red), []
    off = {(repo, name) for repo, p in (perms or {}).items() for name in (p or {}).get("wf_manual_files") or []}
    kept, apart = [], []
    for row in red:
        (apart if (row.get("repo"), str(row.get("file") or "").rsplit("/", 1)[-1]) in off else kept).append(row)
    return kept, apart


def red_runs(runs, branch, now=None):
    """The last run of every workflow that is red now (the runs themselves, for the callers that need the whole record)."""
    return [item["run"] for item in classify(runs, branch, now)["red"]]


def lane_label(where):
    """The words that tell a row that is not the default branch apart: "(merge queue)" or "(branch release-1)" after the workflow; nothing for the default branch."""
    if not where:
        return ""
    return " (" + (i18n.t("ci.lane_queue") if where == "queue" else i18n.t("ci.lane_branch", branch=where)) + ")"


def row_of(repo, item):
    last = item["run"]
    where = item["lane"]
    return {"repo": repo, "workflow": (last.get("name") or workflow_key(last)) + lane_label(where), "conclusion": last.get("conclusion"), "since": last.get("started"), "url": last.get("url"), "streak": item["streak"],
            "sha": last.get("sha", ""), "origin": "merge_queue" if where == "queue" else ("maintenance" if where else "branch"), "branch": last.get("branch"), "kind": item["kind"],
            "run_id": last.get("id"), "reusable": list(last.get("reusable") or []), "aged": bool(item.get("aged")),
            "file": workflow_key(last), "recent_runs": item["recent"][1], "fail_rate": round(100 * item["recent"][0] / item["recent"][1]) if item["recent"][1] else 0}


def branch_of(repo, runs, default_branches=None, guess=False):
    """(branch, guessed): the default branch of the repository as known, else a guess (main, master, most runs) when asked, else main."""
    branch = (default_branches or {}).get(repo)
    if branch:
        return branch, False
    return (guess_default_branch(runs) if guess else None) or "main", bool(guess)


def red_workflows(runs_by_repo, default_branches=None, guess=False, sample=None, now=None):
    """(rows, approx): rows = [{"repo", "workflow", "conclusion", "since", "url", "streak", "sha", "origin", "branch", "kind"}] sorted by repo and workflow; approx = True when a branch was guessed or a sample is full.
    With guess=False a repository without a known default branch uses "main" (the rule of the sentinel before the branches are read)."""
    out, approx = [], False
    for repo, runs in runs_by_repo.items():
        branch, guessed = branch_of(repo, runs, default_branches, guess)
        approx = approx or guessed
        if sample and len(runs) >= sample:
            approx = True
        out.extend(row_of(repo, item) for item in classify(runs, branch, now)["red"])
    return sorted(out, key=lambda r: (r["repo"], r["workflow"], r["origin"], str(r["branch"]))), approx


def states(runs_by_repo, default_branches=None, guess=False, now=None):
    """{"inactive": [rows], "awaiting": [rows], "services": [rows]} for all repositories: the workflows not red because they were abandoned, the runs that wait for an approval and the
    services of GitHub (dynamic workflows) whose last run failed."""
    out = {"inactive": [], "awaiting": [], "services": []}
    for repo, runs in runs_by_repo.items():
        branch, _guessed = branch_of(repo, runs, default_branches, guess)
        out["inactive"].extend(row_of(repo, item) for item in classify(runs, branch, now)["inactive"])
        out["awaiting"].extend(awaiting_runs(runs, now))
        out["services"].extend(service_rows(runs, now))
    return out
