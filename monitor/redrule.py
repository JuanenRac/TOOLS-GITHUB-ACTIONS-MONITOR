# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""THE rule of "red on main", small enough for the lite edition (which does not load the sentinel) and used by the sentinel too, so that both editions count the same.

A workflow is red when the LAST COMPLETED run of its file on the DEFAULT branch failed; cancelled, skipped, neutral and stale runs say nothing and are ignored (an older failure is not
hidden by them). The sentinel knows the default branch of each repository; the lite edition does not read it, so it guesses (`main`, then `master`, then the branch with most runs) and says
the figure is approximate (`approx`). It is also approximate when the list of runs of a repository is as long as the sample asked for: an older workflow may be hidden beyond it.
"""
BAD = ("failure", "timed_out", "startup_failure", "action_required")
IGNORED = ("cancelled", "skipped", "neutral", "stale")


def workflow_key(run):
    return run.get("path") or run.get("name") or ""


def completed_runs(runs, branch="main"):
    """The runs that count: completed, on the branch, not cancelled / skipped / neutral / stale (the same definition as signstate.completed_runs)."""
    return [r for r in runs if r.get("status") == "completed" and r.get("branch") == branch and r.get("conclusion") not in IGNORED]


def guess_default_branch(runs):
    """main, else master, else the branch that has most runs (None without runs)."""
    counts = {}
    for run in runs:
        counts[run.get("branch")] = counts.get(run.get("branch"), 0) + 1
    for name in ("main", "master"):
        if name in counts:
            return name
    return max(counts, key=lambda b: (counts[b], str(b)), default=None)


def red_workflows(runs_by_repo, default_branches=None, guess=False, sample=None):
    """(rows, approx): rows = [{"repo", "workflow", "conclusion", "since", "url", "streak", "sha"}] sorted by repo and workflow; approx = True when a branch was guessed or a sample is full.
    With guess=False a repository without a known default branch uses "main" (the rule of the sentinel before the branches are read)."""
    out, approx = [], False
    for repo, runs in runs_by_repo.items():
        branch = (default_branches or {}).get(repo)
        if not branch:
            branch = (guess_default_branch(runs) if guess else None) or "main"
            approx = approx or guess
        if sample and len(runs) >= sample:
            approx = True
        series = {}
        for run in sorted(completed_runs(runs, branch), key=lambda r: r.get("started") or ""):
            series.setdefault(workflow_key(run), []).append(run)
        for key, items in series.items():
            last = items[-1]
            if last.get("conclusion") not in BAD:
                continue
            streak = 0
            for run in reversed(items):
                if run.get("conclusion") in BAD:
                    streak += 1
                else:
                    break
            out.append({"repo": repo, "workflow": last.get("name") or key, "conclusion": last["conclusion"], "since": last.get("started"), "url": last.get("url"), "streak": streak, "sha": last.get("sha", "")})
    return sorted(out, key=lambda r: (r["repo"], r["workflow"])), approx
