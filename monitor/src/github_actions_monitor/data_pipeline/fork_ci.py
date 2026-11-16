# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Which forks are worth judging. A fork copies the files, the settings and the workflows of a project that somebody else owns: its hygiene (no ruleset, no release, no CHANGELOG, the licence of the
upstream), its workflow files and the nightly jobs it inherits say nothing about the work of the owner of the fork, and an account that collects forks (722 of 727 repositories in a measured one)
would show hundreds of warnings and a score made of noise.

A fork enters the hygiene (A6), the lint of workflows and the score only when it has a CI of its own: runs of `push`, `pull_request`, `workflow_dispatch` or `merge_group` that are not from a pull request
of another fork and are not made by GitHub itself, in the last `ci.fork_own_ci_days` days (90). A copied `schedule` does not count: the fork inherits it. A fork without such a run is "idle": it is left out of
those three and counted apart. Setting `ci.forks_need_own_ci` (on by default) turns the rule off; with it off every fork is judged like any other repository.

When the list of runs of a fork is as long as the sample asked for and does not reach back to the start of the window, a run of its own may hide beyond it: the fork is NOT idle then (it stays in).
Pure functions: no network; the clock is given by the caller."""
import time
from datetime import datetime

from github_actions_monitor.data_pipeline import redrule

OWN_EVENTS = ("push", "pull_request", "workflow_dispatch", "merge_group")
DEFAULT_DAYS = 90


def settings(config):
    """{"enabled", "days"}: `ci.forks_need_own_ci` (on) and `ci.fork_own_ci_days` (90, 1..365); an invalid value keeps the default."""
    block = (config or {}).get("ci")
    block = block if isinstance(block, dict) else {}
    days = block.get("fork_own_ci_days")
    days = days if isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 365 else DEFAULT_DAYS
    return {"enabled": block.get("forks_need_own_ci") is not False, "days": days}


POLICY = {"enabled": True, "days": DEFAULT_DAYS}      # replaced by configure(): the whole monitor shares one rule


def configure(config):
    POLICY.update(settings(config))


def _epoch(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def is_own_run(run):
    """A run that shows the owner of the fork works on it."""
    return run.get("event") in OWN_EVENTS and run.get("fork") is not True and not redrule.is_dynamic(run)


def has_own_ci(runs, full, now, days):
    """True / False / None (cannot be told: the list is full and does not reach back far enough)."""
    start = now - days * 86400
    oldest = None
    for run in runs or []:
        stamp = _epoch(run.get("started"))
        if stamp is None:
            continue
        oldest = stamp if oldest is None else min(oldest, stamp)
        if stamp >= start and is_own_run(run):
            return True
    if full and (oldest is None or oldest >= start):
        return None
    return False


def idle_forks(forks, runs_by_repo, full_repos, now=None, cfg=None):
    """The forks of `forks` (names) that have no CI of their own in the window, sorted. [] when the rule is off. `full_repos` = the repositories whose list of runs is as long as the sample asked for."""
    cfg = cfg or dict(POLICY)
    if not cfg["enabled"]:
        return []
    now = time.time() if now is None else now
    return sorted(repo for repo in forks if has_own_ci(runs_by_repo.get(repo), repo in (full_repos or ()), now, cfg["days"]) is False)
