# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A9: the GitHub Roadmap boards of the four ecosystems, and whether they are ALIVE.

Three sources, none of them writes anything:
  * the definitions committed in the profile repository (tools/roadmap_defs.py and tools/seed_ecosystem_roadmap.py): cards per status that the repository says;
  * GitHub itself (`gh api graphql`), only if `gh` has the read:project scope: cards per status that the board really has, and whether they differ from the definitions;
  * the Actions runs of the seeding workflow: when each board was last reconciled, and whether the definitions changed after that.
Without the read:project scope the tab still works from the definitions and the runs, and says what is missing.
"""
import json
import re
import subprocess
import sys
import threading
import time

import i18n
import toolconfig
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BOARDS = [("hydra-umc", "HYDRA-UMC Roadmap"), ("urtc", "URTC Roadmap"), ("armor", "A.R.M.O.R. Roadmap"), ("eh3d", "EH3D Fabrication Suite Roadmap")]


def profile_repo():
    """The profile repository (named after the account, as GitHub requires for a profile README); A9 only works when its tools/ folder is cloned next to the others."""
    return toolconfig.github_owner()


WORKFLOW = "seed-ecosystem-roadmap.yml"
STALE_DAYS = 8
SCOPE_HELP = "@scope_help"   # token: rendered in the current language by render_error() (text "a9.scope_help")

DEFS_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import roadmap_defs as r
import seed_ecosystem_roadmap as s
out = {}
hydra = [i.get("status", "Backlog") for i in s.SEED_ITEMS]
out["hydra-umc"] = {"title": "HYDRA-UMC Roadmap", "cards": len(hydra), "status": {k: hydra.count(k) for k in set(hydra)}}
for name, board in r.ROADMAPS.items():
    updates = board.get("status_updates") or {}
    states = []
    for item in board["items"]:
        decision = updates.get(item["title"])
        states.append(decision["status"] if decision else item.get("status", "Backlog"))
    out[name] = {"title": board["title"], "cards": len(states), "status": {k: states.count(k) for k in set(states)}}
print(json.dumps(out))
"""


def defs_summary(profile_dir):
    """Cards per status according to the definitions in the profile repository (run in a child process: nothing is imported here)."""
    tools = Path(profile_dir) / "tools"
    if not (tools / "roadmap_defs.py").is_file():
        return {}, i18n.t("a9.no_defs_file")
    try:
        done = subprocess.run([sys.executable, "-I", "-c", DEFS_SCRIPT, str(tools)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {}, str(error)[:200]
    if done.returncode != 0:
        return {}, (done.stderr.strip().splitlines() or [i18n.t("a9.defs_failed")])[-1][:200]
    try:
        return json.loads(done.stdout.strip().splitlines()[-1]), None
    except (ValueError, IndexError):
        return {}, i18n.t("a9.defs_not_json")


def defs_age_days(profile_dir, now):
    """Days since the definitions were last changed in git (None when it cannot be read)."""
    try:
        done = subprocess.run(["git", "-C", str(profile_dir), "log", "-1", "--format=%ct", "--", "tools/roadmap_defs.py", "tools/seed_ecosystem_roadmap.py"],
                              capture_output=True, text=True, timeout=30)
        stamp = int(done.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return round((now.timestamp() - stamp) / 86400, 1)


def parse_time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def last_runs(gh, now):
    """For each board: age in days and conclusion of the last COMPLETED run of the seeding workflow whose job is named after the board.
    Returns (per_board, last_any, error). A run with no job named after a board counts for all (the manual workflow seeds one board per run)."""
    try:
        data = gh("api", f"repos/{profile_repo()}/{profile_repo()}/actions/workflows/{WORKFLOW}/runs?per_page=12&status=completed")
    except Exception as error:   # noqa: BLE001 - a missing workflow or no access must not break the tab
        return {}, None, str(error)[:200]
    runs = (data or {}).get("workflow_runs", [])
    per_board, last_any = {}, None
    for run in runs:
        when = parse_time(run.get("created_at"))
        age = round((now - when).total_seconds() / 86400, 1) if when else None
        entry = {"age_days": age, "conclusion": run.get("conclusion"), "event": run.get("event"), "url": run.get("html_url")}
        if last_any is None:
            last_any = entry
        try:
            jobs = (gh("api", f"repos/{profile_repo()}/{profile_repo()}/actions/runs/{run['id']}/jobs?per_page=10") or {}).get("jobs", [])
        except Exception:   # noqa: BLE001
            jobs = []
        for job in jobs:
            match = re.search(r"\b(hydra-umc|urtc|armor|eh3d)\b", job.get("name", ""), re.I)
            if match and match.group(1).lower() not in per_board:
                per_board[match.group(1).lower()] = {**entry, "conclusion": job.get("conclusion") or entry["conclusion"]}
    return per_board, last_any, None


STATUS_QUERY = ("query($id:ID!,$after:String){node(id:$id){... on ProjectV2{items(first:100,after:$after){pageInfo{hasNextPage endCursor} "
                "nodes{fieldValueByName(name:\"Status\"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}}}")
LIST_QUERY = "query{user(login:\"%s\"){projectsV2(first:20){nodes{id title number url}}}}"


def live_boards(gh):
    """Cards per status as GitHub shows them, by project title. Returns (boards, error)."""
    try:
        listing = gh("api", "graphql", "-f", "query=" + LIST_QUERY % profile_repo())
    except Exception as error:   # noqa: BLE001
        text = str(error)
        return {}, (i18n.t("a9.scope_help") if ("scope" in text.lower() or "read:project" in text) else text[:200])
    nodes = (((listing or {}).get("data") or {}).get("user") or {}).get("projectsV2", {}).get("nodes") or []
    out = {}
    for project in nodes:
        counts, after = Counter(), None
        for _ in range(8):
            args = ["api", "graphql", "-f", f"query={STATUS_QUERY}", "-f", f"id={project['id']}"]
            if after:
                args += ["-f", f"after={after}"]
            try:
                page = (((gh(*args) or {}).get("data") or {}).get("node") or {}).get("items") or {}
            except Exception as error:   # noqa: BLE001
                return out, str(error)[:200]
            for node in page.get("nodes") or []:
                value = node.get("fieldValueByName") or {}
                counts[value.get("name") or i18n.t("a9.no_status")] += 1
            if not (page.get("pageInfo") or {}).get("hasNextPage"):
                break
            after = page["pageInfo"]["endCursor"]
        out[project["title"]] = {"cards": sum(counts.values()), "status": dict(counts), "url": project.get("url")}
    return out, None


def build(defs, defs_error, live, live_error, runs, last_any, runs_error, defs_age, now_ts=None):
    """One row per board plus a level: warn when a board was never reconciled or not within STALE_DAYS, or the definitions changed after the last good run."""
    rows, warn = [], False
    for key, title in BOARDS:
        d = defs.get(key) or {}
        board_live = (live or {}).get(d.get("title") or title)
        run = runs.get(key) or last_any
        problems = []   # (code, values): rendered in the language of whoever asks (render_problems), so a language switch needs no new call
        if not d:
            problems.append(("no_defs", {}))
        if run is None:
            problems.append(("never_ran", {}))
        else:
            if run.get("conclusion") != "success":
                problems.append(("last_failed", {"conclusion": run.get("conclusion")}))
            if run.get("age_days") is not None and run["age_days"] > STALE_DAYS:
                problems.append(("stale", {"days": run["age_days"], "limit": STALE_DAYS}))
            if defs_age is not None and run.get("age_days") is not None and defs_age < run["age_days"] - 0.05:
                problems.append(("defs_newer", {}))
        drift = None
        if board_live is not None and d:
            drift = dict(board_live["status"]) != dict(d["status"])
            if drift:
                problems.append(("drift", {}))
        warn = warn or bool(problems)
        rows.append({"key": key, "title": d.get("title") or title, "defs": d or None, "live": board_live, "drift": drift, "run": run, "problems_raw": problems, "problems": render_problems(problems),
                     "url": (board_live or {}).get("url")})
    return {"boards": rows, "defs_error": defs_error, "live_error": live_error, "runs_error": runs_error, "defs_age_days": defs_age,
            "level": "warn" if warn else "info", "stale_days": STALE_DAYS}


def render_problems(raw):
    return [i18n.t("a9.p." + code, **values) for code, values in raw]


def render_error(text):
    return i18n.t("a9.scope_help") if text == SCOPE_HELP else text


def localized(value):
    """A copy of a built value with the problems and the known error tokens in the language of the caller."""
    if not isinstance(value, dict):
        return value
    out = dict(value)
    out["boards"] = [{**b, "problems": render_problems(b.get("problems_raw") or [])} if "problems_raw" in b else b for b in value.get("boards") or []]
    for key in ("defs_error", "live_error", "runs_error"):
        if out.get(key):
            out[key] = render_error(out[key])
    return out


class Watcher:
    """Refreshes the A9 data in a thread (the GitHub calls are slow) and serves the last result."""

    def __init__(self, gh, profile_dir, ttl=900):
        self.gh, self.profile_dir, self.ttl = gh, Path(profile_dir), ttl
        self.at, self.value, self.busy = 0.0, None, False
        self.lock = threading.Lock()

    def refresh(self):
        now = datetime.now(timezone.utc)
        if not (self.profile_dir / "tools" / "roadmap_defs.py").is_file():   # optional layer: without the profile clone there is nothing to compare, and no call is made
            with self.lock:
                self.value, self.at, self.busy = {"boards": [], "level": "unknown", "not_configured": True, "stale_days": STALE_DAYS}, time.time(), False
            return
        defs, defs_error = defs_summary(self.profile_dir)
        live, live_error = live_boards(self.gh)
        runs, last_any, runs_error = last_runs(self.gh, now)
        value = build(defs, defs_error, live, live_error, runs, last_any, runs_error, defs_age_days(self.profile_dir, now))
        with self.lock:
            self.value, self.at, self.busy = value, time.time(), False

    def get(self):
        with self.lock:
            fresh = self.value is not None and time.time() - self.at < self.ttl
            start = not fresh and not self.busy
            if start:
                self.busy = True
            value = self.value
        if start:
            threading.Thread(target=self._safe, daemon=True, name="roadmap-a9").start()
        return localized(value) or {"boards": [], "loading": True, "level": "unknown", "stale_days": STALE_DAYS}

    def _safe(self):
        try:
            self.refresh()
        except Exception as error:   # noqa: BLE001 - the tab must never take the sentinel down
            with self.lock:
                self.value = {"boards": [], "defs_error": i18n.t("a9.read_failed", error=error)[:200], "level": "unknown", "stale_days": STALE_DAYS}
                self.at, self.busy = time.time(), False
