# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Is an action that a workflow uses still looked after? An information rule of the workflow linter (`archived_action`, off by default).

For each `owner/repo` named by a `uses:` line it asks GitHub for the repository of the action once (`GET repos/OWNER/REPO`) and keeps the answer in memory:

  archived   the repository of the action is archived (its owner closed it: no more fixes, no security patches)
  inactive   only when asked (`lint.maintenance.inactive`): the last push to the repository is older than N years (`lint.maintenance.inactive_years`, 2 by default)

The rule only INFORMS: its severity is always `info` and a finding of it never makes the linter fail. Reading costs calls of the shared allowance, so the number of calls of one pass is capped by the caller
(`begin(budget)`), an answer is reused for `refresh_seconds` (a week by default), a failed read is not asked again for a few minutes, and an action that is not read in this pass is simply not judged
(never reported as healthy or as archived). Without a network nothing is reported and `summary()` says how many actions could not be read. Read only; standard library only."""
import re
import threading
import time
from datetime import datetime, timezone

NAME_RE = re.compile(r"^(?!\.+\Z)[A-Za-z0-9._-]{1,100}\Z")
YEAR = 365.25 * 86400
FAILURE_PAUSE = 600      # seconds before an action whose read failed is asked again
DEFAULTS = {"inactive": False, "inactive_years": 2, "refresh_seconds": 604800, "max_calls_per_tick": 10}
RANGES = {"inactive_years": (1, 10), "refresh_seconds": (3600, 2592000), "max_calls_per_tick": (1, 100)}


def settings(block):
    """`lint.maintenance` merged over the defaults; a value out of range or of another type is ignored."""
    out = dict(DEFAULTS)
    if isinstance(block, dict):
        if isinstance(block.get("inactive"), bool):
            out["inactive"] = block["inactive"]
        for key, (low, high) in RANGES.items():
            value = block.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
                out[key] = value
    return out


def owner_repo(spec):
    """(owner, repo) of the `uses:` value of an action or of a reusable workflow of GitHub; None for a local action (`./x`), an image (`docker://`) or a value that is not `owner/repo[/path]@ref`."""
    spec = str(spec or "").strip()
    if not spec or spec.startswith(("./", "docker://")) or "@" not in spec:
        return None
    parts = spec.split("@", 1)[0].split("/")
    if len(parts) < 2 or not NAME_RE.match(parts[0]) or not NAME_RE.match(parts[1]):
        return None
    return parts[0], parts[1]


def _years_since(stamp, now):
    try:
        then = datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None
    return max(0.0, (now - then) / YEAR)


class Health:
    """The state of the actions named by the workflows. `read(endpoint)` answers the JSON of a read of the API or raises."""

    def __init__(self, read, clock=time.time, inactive=False, inactive_years=2, refresh_seconds=604800):
        self.read, self.clock = read, clock
        self.inactive, self.inactive_years, self.refresh_seconds = inactive, inactive_years, refresh_seconds
        self.cache = {}      # "owner/repo" (lower case) -> (time of the read, {"state": ok|archived|inactive|absent|failed, "years": float|None})
        self.lock = threading.RLock()
        self.begin(0)

    def configure(self, inactive, inactive_years, refresh_seconds):
        with self.lock:
            changed = (inactive, inactive_years) != (self.inactive, self.inactive_years)
            self.inactive, self.inactive_years, self.refresh_seconds = inactive, inactive_years, refresh_seconds
            if changed:
                self.cache.clear()      # the verdicts depend on the question

    def begin(self, budget):
        """Starts a pass of the linter with `budget` calls to spend (0 = only what is already known)."""
        with self.lock:
            self.left = max(0, int(budget))
            self.seen = {}      # "owner/repo" -> state, for summary()

    def _fresh(self, key):
        item = self.cache.get(key)
        if not item:
            return None
        age = self.clock() - item[0]
        limit = FAILURE_PAUSE if item[1]["state"] == "failed" else self.refresh_seconds
        return item[1] if age <= limit else None

    def lookup(self, owner, repo):
        """The state of one action: {"state", "years"}, or None when it was not read in this pass (no budget left)."""
        key = f"{owner}/{repo}".lower()
        with self.lock:
            state = self._fresh(key)
            if state is None:
                if self.left < 1:
                    self.seen.setdefault(key, {"state": "skipped"})
                    return None
                self.left -= 1
                state = self._ask(owner, repo)
                self.cache[key] = (self.clock(), state)
            self.seen[key] = state
            return state

    def _ask(self, owner, repo):
        try:
            answer = self.read(f"repos/{owner}/{repo}")
        except Exception as error:      # noqa: BLE001 - no network, no access, allowance spent: the action is not judged
            from github_actions_monitor.integrations import remote_workflows
            return {"state": "absent" if remote_workflows.reason_of(error) == "not_found" else "failed", "years": None}
        if not isinstance(answer, dict):
            return {"state": "failed", "years": None}
        years = _years_since(answer.get("pushed_at"), self.clock())
        if answer.get("archived") is True:
            return {"state": "archived", "years": years}
        if self.inactive and years is not None and years >= self.inactive_years:
            return {"state": "inactive", "years": years}
        return {"state": "ok", "years": years}

    def verdict(self, spec):
        """("archived" | "inactive", "owner/repo") for a `uses:` value whose action is archived or without activity, else None (healthy, not judged or not a GitHub action)."""
        name = owner_repo(spec)
        if not name:
            return None
        state = self.lookup(*name)
        if state and state["state"] in ("archived", "inactive"):
            return state["state"], f"{name[0]}/{name[1]}"
        return None

    def summary(self):
        """What the last pass could say: {"checked", "archived", "inactive", "unread", "skipped"}. `unread` = the read failed (no network...): those actions were not judged."""
        with self.lock:
            states = [s["state"] for s in self.seen.values()]
        return {"checked": sum(1 for s in states if s in ("ok", "archived", "inactive")), "archived": states.count("archived"), "inactive": states.count("inactive"),
                "unread": states.count("failed"), "skipped": states.count("skipped")}
