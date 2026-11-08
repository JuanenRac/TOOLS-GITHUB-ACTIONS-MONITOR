# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Analytics of the workflows: how long they take, how long they wait in the queue, how long each step takes, and which ones are flaky.

Everything is computed from data the monitor already reads (the list of runs of each repository) plus, optionally, the jobs of a few completed runs per cycle (a small, capped number
of extra reads, only for runs not seen before; each one answered with the same conditional read as the rest, so a repeat costs nothing).

  duration     p50 and p95 of the duration of the successful runs of each workflow
  queue        p50 and p95 of the time a job waited before it started (created_at -> started_at)
  steps        p50 and p95 of each step of a workflow
  flaky        a workflow that FAILED and then PASSED on the very same commit (or whose run needed a re-run): "possibly transient". It is only a LABEL: the rule that decides
               what is red is not changed by it
  slower       a workflow whose p50 today is `slow_factor` times the median p50 of the previous days

The samples are kept in `analytics_history.json` (local, never published) for `keep_days` days, at most `max_samples` per workflow, so the file cannot grow without limit.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HISTORY_FILE = HERE / "analytics_history.json"
BAD = ("failure", "timed_out", "startup_failure")
DEFAULTS = {"enabled": True, "keep_days": 30, "min_samples": 5, "max_samples": 200, "slow_factor": 1.5, "jobs_per_cycle": 3, "steps": True, "flaky": True}


def percentile(values, q):
    """Nearest-rank percentile (q in 0..100) of a list of numbers; None for an empty list."""
    data = sorted(v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool))
    if not data:
        return None
    rank = max(1, -(-len(data) * q // 100))   # ceil(n * q / 100)
    return data[int(rank) - 1]


def _key(repo, workflow):
    return f"{repo}|{workflow}"


def duration_rows(runs, min_samples=5):
    """[{"repo", "workflow", "n", "p50", "p95", "max"}] for the successful runs, workflows with fewer than min_samples runs left out. Sorted by p95, slowest first."""
    groups = {}
    for run in runs:
        if run.get("conclusion") == "success" and isinstance(run.get("seconds"), (int, float)) and run["seconds"] > 0:
            groups.setdefault((run.get("repo"), run.get("name")), []).append(run["seconds"])
    rows = [{"repo": repo, "workflow": name, "n": len(vals), "p50": percentile(vals, 50), "p95": percentile(vals, 95), "max": max(vals)}
            for (repo, name), vals in groups.items() if len(vals) >= max(1, min_samples)]
    return sorted(rows, key=lambda r: (-(r["p95"] or 0), r["repo"] or "", r["workflow"] or ""))


def flaky_rows(runs, min_runs=3):
    """Workflows with a possible transient failure: a failed run followed by a success on the same commit, or a run that needed another attempt.
    [{"repo", "workflow", "total", "flaky", "rate"}], the flakiest first. The label never changes what counts as red."""
    by_workflow, by_commit = {}, {}
    for run in runs:
        if run.get("status") != "completed":
            continue
        by_workflow.setdefault((run.get("repo"), run.get("name")), []).append(run)
        by_commit.setdefault((run.get("repo"), run.get("name"), run.get("sha")), []).append(run)
    flaky_commits = {}
    for (repo, name, sha), group in by_commit.items():
        ordered = sorted(group, key=lambda r: r.get("started") or "")
        failed_then_passed = any(r.get("conclusion") in BAD for r in ordered) and ordered[-1].get("conclusion") == "success"
        retried = any((r.get("attempt") or 1) > 1 and r.get("conclusion") == "success" for r in ordered)
        if sha and (failed_then_passed or retried):
            flaky_commits[(repo, name)] = flaky_commits.get((repo, name), 0) + 1
    rows = []
    for (repo, name), group in by_workflow.items():
        if len(group) >= min_runs and flaky_commits.get((repo, name)):
            rows.append({"repo": repo, "workflow": name, "total": len(group), "flaky": flaky_commits[(repo, name)], "rate": round(flaky_commits[(repo, name)] / len(group), 3)})
    return sorted(rows, key=lambda r: (-r["rate"], r["repo"] or "", r["workflow"] or ""))


def _ts(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def job_sample(job):
    """(queue seconds or None, {step name: seconds}) of one job of the API (created_at, started_at, completed_at, steps)."""
    created, started = _ts(job.get("created_at")), _ts(job.get("started_at"))
    queue = max(0, started - created) if created is not None and started is not None else None
    steps = {}
    for step in job.get("steps") or []:
        a, b = _ts(step.get("started_at")), _ts(step.get("completed_at"))
        if a is not None and b is not None and step.get("name"):
            steps[str(step["name"])[:80]] = max(0, b - a)
    return queue, steps


class Store:
    """The local samples: queue times, step times and the daily p50 of each workflow."""

    def __init__(self, path=HISTORY_FILE, keep_days=30, max_samples=200):
        self.path, self.keep_days, self.max_samples = Path(path), keep_days, max_samples
        self.lock = threading.Lock()
        self.data = {"seen": [], "queue": {}, "steps": {}, "daily": {}}
        self.dirty = False
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for key in self.data:
                    if isinstance(loaded.get(key), type(self.data[key])):
                        self.data[key] = loaded[key]
        except (OSError, ValueError):
            pass

    def seen(self, run_id):
        return run_id in self.data["seen"]

    def add_jobs(self, repo, workflow, run_id, jobs, with_steps=True):
        """Adds the samples of the jobs of one completed run (once per run id)."""
        key = _key(repo, workflow)
        with self.lock:
            if run_id in self.data["seen"]:
                return False
            self.data["seen"] = (self.data["seen"] + [run_id])[-2000:]
            for job in jobs or []:
                queue, steps = job_sample(job)
                if queue is not None:
                    self.data["queue"][key] = (self.data["queue"].get(key, []) + [queue])[-self.max_samples:]
                if with_steps:
                    for name, seconds in steps.items():
                        slot = self.data["steps"].setdefault(key, {})
                        slot[name] = (slot.get(name, []) + [seconds])[-self.max_samples:]
            self.dirty = True
            return True

    def queue_rows(self, min_samples=5):
        rows = []
        for key, vals in self.data["queue"].items():
            if len(vals) >= max(1, min_samples):
                repo, _, workflow = key.partition("|")
                rows.append({"repo": repo, "workflow": workflow, "n": len(vals), "p50": percentile(vals, 50), "p95": percentile(vals, 95)})
        return sorted(rows, key=lambda r: (-(r["p95"] or 0), r["repo"], r["workflow"]))

    def step_rows(self, min_samples=5):
        rows = []
        for key, steps in self.data["steps"].items():
            repo, _, workflow = key.partition("|")
            for name, vals in steps.items():
                if len(vals) >= max(1, min_samples):
                    rows.append({"repo": repo, "workflow": workflow, "step": name, "n": len(vals), "p50": percentile(vals, 50), "p95": percentile(vals, 95)})
        return sorted(rows, key=lambda r: (-(r["p95"] or 0), r["repo"], r["workflow"], r["step"]))

    def record_day(self, rows, today=None):
        """Remembers today's p50 of every workflow and forgets the days older than keep_days."""
        today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.lock:
            self.data["daily"][today] = {_key(r["repo"], r["workflow"]): r["p50"] for r in rows if r.get("p50")}
            for day in sorted(self.data["daily"])[:-max(1, self.keep_days)]:
                del self.data["daily"][day]
            self.dirty = True

    def slower(self, rows, slow_factor=1.5, today=None, min_days=3):
        """Workflows whose p50 is slow_factor times the median of the previous days (needs min_days days of history)."""
        today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        before = [self.data["daily"][d] for d in sorted(self.data["daily"]) if d < today]
        out = []
        if len(before) < min_days:
            return out
        for row in rows:
            history = [day.get(_key(row["repo"], row["workflow"])) for day in before]
            history = [h for h in history if h]
            if len(history) >= min_days and row.get("p50"):
                base = percentile(history, 50)
                if base and row["p50"] >= base * slow_factor:
                    out.append({"repo": row["repo"], "workflow": row["workflow"], "p50": row["p50"], "usual": base, "factor": round(row["p50"] / base, 2)})
        return sorted(out, key=lambda r: -r["factor"])

    def save(self):
        with self.lock:
            if not self.dirty:
                return False
            payload = json.dumps(self.data)
            self.dirty = False
        try:
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False


def settings(config):
    """`analytics` of the configuration merged over DEFAULTS (a value of the wrong type keeps the default)."""
    merged = dict(DEFAULTS)
    user = (config or {}).get("analytics")
    if isinstance(user, dict):
        for key, base in DEFAULTS.items():
            v = user.get(key)
            if isinstance(v, bool) == isinstance(base, bool) and isinstance(v, (bool, int, float)) and (isinstance(base, bool) or v > 0):
                merged[key] = type(base)(v) if not isinstance(base, bool) else v
    return merged


def pending_runs(runs, store, limit):
    """Up to `limit` completed runs (newest first) whose jobs were not sampled yet."""
    out = []
    for run in sorted(runs, key=lambda r: r.get("started") or "", reverse=True):
        if len(out) >= limit:
            break
        if run.get("status") == "completed" and run.get("conclusion") in ("success",) + BAD and not store.seen(run.get("id")):
            out.append(run)
    return out


def summary(runs, store, cfg):
    """Everything the page, /metrics and Grafana need: {"enabled", "duration": [...], "queue": [...], "steps": [...], "flaky": [...], "slower": [...]}."""
    if not cfg.get("enabled", True):
        return {"enabled": False, "duration": [], "queue": [], "steps": [], "flaky": [], "slower": []}
    duration = duration_rows(runs, cfg["min_samples"])
    if duration:
        store.record_day(duration)
    return {"enabled": True, "duration": duration, "queue": store.queue_rows(cfg["min_samples"]), "steps": store.step_rows(cfg["min_samples"]) if cfg.get("steps", True) else [],
            "flaky": flaky_rows(runs) if cfg.get("flaky", True) else [], "slower": store.slower(duration, cfg["slow_factor"])}


def clock():
    return time.time()
