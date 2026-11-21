# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""How many commits the original repository has that a fork does not (`fleet.fork_behind`, OFF by default): a column of the Repositories table for the repositories that are forks.

  * One read of the fork (`repos/OWNER/NAME`: its parent and the default branch of both) and one read of the compare endpoint (`compare/FORKBRANCH...PARENT:PARENTBRANCH`: `ahead_by` is the number
    of commits the original has and the fork lacks). A round reads at most `fleet.fork_behind_per_call` forks, two rounds are at least 30 seconds apart, and an answer is kept `fleet.meta_ttl_hours`
    (the same time to live as the metadata columns). Read only.
  * A fork that could not be read (no access, the original was deleted, the branch is gone, no network) is `unknown`: it is marked neither green nor red, it says "not evaluable" and it is asked
    again after an hour at most. A repository that is not a fork has no value at all.
  * States: `behind` (the original has `behind` more commits), `current` (nothing to catch up), `unknown`.
"""
import threading
import time
from urllib.parse import quote

DEFAULTS = {"enabled": False, "per_call": 5}
MIN_GAP_SECONDS = 30
RETRY_SECONDS = 3600
MAX_BEHIND = 100000


def settings(config):
    """The fork_behind part of the `fleet` block, each value checked (a wrong one keeps the conservative default), plus the shared `fleet.meta_ttl_hours`."""
    from github_actions_monitor.data_pipeline import meta_columns
    fleet = (config or {}).get("fleet") if isinstance((config or {}).get("fleet"), dict) else {}
    per_call = fleet.get("fork_behind_per_call")
    per_call = per_call if isinstance(per_call, int) and not isinstance(per_call, bool) and 1 <= per_call <= 50 else DEFAULTS["per_call"]
    return {"enabled": fleet.get("fork_behind") is True, "per_call": per_call, "ttl_hours": meta_columns.settings(config)["ttl_hours"]}


def behind_of(answer):
    """The number of commits the original has that the fork lacks, from the answer of the compare endpoint (`ahead_by` of fork...parent); None when the answer does not say."""
    value = (answer or {}).get("ahead_by") if isinstance(answer, dict) else None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return min(value, MAX_BEHIND)


def parent_of(answer):
    """(fork default branch, parent full name, parent default branch) from the read of the fork, or None when it has no parent (a fork whose original was deleted or detached)."""
    if not isinstance(answer, dict) or not isinstance(answer.get("parent"), dict):
        return None
    parent = answer["parent"]
    values = (answer.get("default_branch"), parent.get("full_name"), parent.get("default_branch"))
    if not all(isinstance(v, str) and v for v in values):
        return None
    return values


def read_one(repo, read):
    """{"state", "behind", "parent"} for one fork. Any failure is `unknown`."""
    try:
        found = parent_of(read(f"repos/{repo}"))
        if found is None:
            return {"state": "unknown", "behind": None, "parent": "", "why": "no_parent"}
        branch, parent, parent_branch = found
        number = behind_of(read(f"repos/{repo}/compare/{quote(branch, safe='/')}...{quote(parent.split('/')[0], safe='')}:{quote(parent_branch, safe='/')}"))
        if number is None:
            return {"state": "unknown", "behind": None, "parent": parent, "why": "no_answer"}
        return {"state": "behind" if number > 0 else "current", "behind": number, "parent": parent, "why": ""}
    except Exception:   # noqa: BLE001 - no access, no network, a branch that is gone: not evaluable, never a mark
        return {"state": "unknown", "behind": None, "parent": "", "why": "unreadable"}


class Reader:
    def __init__(self):
        self.cache = {}
        self.lock = threading.RLock()
        self.last_round = 0.0

    def due(self, repo, ttl_hours, now):
        row = self.cache.get(repo)
        if row is None:
            return True
        return now - row["at"] >= (min(ttl_hours * 3600, RETRY_SECONDS) if row["state"] == "unknown" else ttl_hours * 3600)

    def pending(self, forks, ttl_hours, now=None):
        now = time.time() if now is None else now
        return sum(1 for r in forks if self.due(r, ttl_hours, now))

    def fill(self, forks, read, per_call, ttl_hours, owner="", now=None):
        """Reads at most `per_call` forks that are due (the oldest answer first) unless the last round was less than MIN_GAP_SECONDS ago; `owner` completes a bare repository name.
        Returns how many forks are still waiting."""
        now = time.time() if now is None else now
        with self.lock:
            todo = sorted((r for r in forks if self.due(r, ttl_hours, now)), key=lambda r: ((self.cache.get(r) or {}).get("at", 0), r))
            if todo and now - self.last_round >= MIN_GAP_SECONDS:
                self.last_round = now
                for repo in todo[:per_call]:
                    self.cache[repo] = dict(read_one(repo if "/" in repo or not owner else f"{owner}/{repo}", read), at=now)
                return max(0, len(todo) - per_call)
            return len(todo)

    def rows(self, forks):
        """{fork: {"state", "behind"}} for the forks asked for; a fork not read yet is `unknown` (not evaluable) and carries `pending`."""
        out = {}
        for repo in forks:
            row = self.cache.get(repo)
            out[repo] = {"state": row["state"], "behind": row["behind"]} if row else {"state": "unknown", "behind": None, "pending": True}
        return out

    def forget(self):
        with self.lock:
            self.cache.clear()
