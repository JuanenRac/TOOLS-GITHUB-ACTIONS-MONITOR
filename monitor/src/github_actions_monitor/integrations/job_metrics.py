# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Histograms and gauges built from the signed `workflow_job` / `workflow_run` events (outputs.prometheus.histograms, OFF by default).

What it keeps, all in memory and bounded (nothing of a payload but short validated words is ever stored, and nothing is written to disk):
  * time in the queue of a job (`ghamon_job_wait_seconds`, a histogram) by runner group and label, counted ONCE per job: the event that says the job started counts it and the later
    `completed` event of the same job does not;
  * duration of jobs and of workflow runs (`ghamon_job_run_seconds`, `ghamon_workflow_run_seconds`);
  * jobs by conclusion (`ghamon_jobs_total`), jobs waiting now by label (`ghamon_runner_jobs_waiting`, the demand for runners) and the oldest wait;
  * per runner (outputs.prometheus.per_runner, OFF): jobs and busy seconds of each self-hosted runner by name, I-173.

Cardinality is controlled: a series that would be number `histogram_max_series` + 1 is written under the label value `other`, so a wild matrix cannot grow the exposition without end.
"""
import collections
import re
import threading
import time

BUCKETS = (1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1200, 1800, 3600, 7200, 14400)
LABEL_RE = re.compile(r"^[A-Za-z0-9._*?=/-]{1,60}\Z")
NAME_RE = re.compile(r"^[A-Za-z0-9._ -]{1,80}\Z")
MAX_LABELS = 8
MAX_WAITING = 5000
SEEN_JOBS = 5000
DEFAULTS = {"histograms": False, "per_runner": False, "histogram_max_series": 200}
OTHER = "other"
GITHUB_HOSTED = ("ubuntu", "windows", "macos")


def settings(config):
    """The `outputs.prometheus` settings of this module, each one checked (a wrong value falls back to the conservative default)."""
    out = config.get("outputs") if isinstance(config, dict) and isinstance(config.get("outputs"), dict) else {}
    cfg = out.get("prometheus") if isinstance(out.get("prometheus"), dict) else {}
    size = cfg.get("histogram_max_series")
    return {"histograms": cfg.get("histograms") is True, "per_runner": cfg.get("per_runner") is True,
            "histogram_max_series": size if isinstance(size, int) and not isinstance(size, bool) and 10 <= size <= 2000 else DEFAULTS["histogram_max_series"]}


def clean_labels(labels):
    """The labels of a job (`runs-on`) as a short list of safe words; anything else is dropped."""
    if not isinstance(labels, list):
        return []
    return [x.lower() for x in labels if isinstance(x, str) and LABEL_RE.match(x)][:MAX_LABELS]


def clean_name(value):
    return value if isinstance(value, str) and NAME_RE.match(value) else ""


def label_of(labels):
    """The one word a job is counted under: `self-hosted` when it asks for it, else the first label that names the machine (not an operating system word alone), else the first, else `none`."""
    names = clean_labels(labels)
    if not names:
        return "none"
    if "self-hosted" in names:
        rest = [x for x in names if x not in ("self-hosted", "linux", "windows", "macos", "x64", "arm64", "arm")]
        return "self-hosted:" + rest[0] if rest else "self-hosted"
    return names[0]


class Histogram:
    """Cumulative buckets by label set, with a bounded number of series."""

    def __init__(self, name, help_text, buckets=BUCKETS):
        self.name, self.help, self.buckets = name, help_text, tuple(buckets)
        self.series = collections.OrderedDict()

    def observe(self, labels, value, max_series):
        key = tuple(sorted(labels.items()))
        if key not in self.series and len(self.series) >= max_series:
            key = tuple(sorted((k, OTHER) for k in labels))
        slot = self.series.get(key)
        if slot is None:
            slot = self.series[key] = {"counts": [0] * len(self.buckets), "sum": 0.0, "count": 0}
        for i, bound in enumerate(self.buckets):
            if value <= bound:
                slot["counts"][i] += 1
        slot["sum"] += value
        slot["count"] += 1

    def lines(self, prefix, esc):
        if not self.series:
            return []
        full = prefix + self.name
        out = [f"# HELP {full} {self.help}", f"# TYPE {full} histogram"]
        for key, slot in self.series.items():
            tag = ",".join(f'{k}="{esc(v)}"' for k, v in key)
            sep = "," if tag else ""
            for bound, n in zip(self.buckets, slot["counts"]):
                out.append(f'{full}_bucket{{{tag}{sep}le="{bound}"}} {n}')
            out.append(f'{full}_bucket{{{tag}{sep}le="+Inf"}} {slot["count"]}')
            suffix = "{" + tag + "}" if tag else ""
            out.append(f"{full}_sum{suffix} {round(slot['sum'], 3)}")
            out.append(f"{full}_count{suffix} {slot['count']}")
        return out


class Collector:
    """The state of the histograms. One instance lives in the process; the tests make their own."""

    def __init__(self, clock=time.time):
        self.clock, self.lock = clock, threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.queue = Histogram("job_wait_seconds", "Time a job waited in the queue before a runner took it, by runner group and label (one count per job).")
            self.job_secs = Histogram("job_run_seconds", "Duration of the jobs that finished, by runner group, label and conclusion.")
            self.run_secs = Histogram("workflow_run_seconds", "Duration of the workflow runs that finished, by conclusion.")
            self.jobs = collections.Counter()
            self.runners = collections.OrderedDict()
            self.waiting = collections.OrderedDict()
            self.seen = collections.OrderedDict()
            self.observed = 0

    def _first_time(self, job_id):
        if job_id is None:
            return True
        if job_id in self.seen:
            return False
        self.seen[job_id] = True
        while len(self.seen) > SEEN_JOBS:
            self.seen.popitem(last=False)
        return True

    def feed(self, record, config=None):
        """One parsed event of the webhook. Returns True when something was counted."""
        cfg = settings(config or {})
        if not cfg["histograms"] and not cfg["per_runner"]:
            return False
        cap = cfg["histogram_max_series"]
        with self.lock:
            if record.get("event") == "workflow_run":
                if record.get("status") == "completed" and isinstance(record.get("seconds"), int):
                    self.run_secs.observe({"conclusion": record.get("conclusion") or "unknown"}, record["seconds"], cap)
                    self.observed += 1
                    return True
                return False
            if record.get("event") != "workflow_job":
                return False
            job_id, status = record.get("job_id"), record.get("status")
            group, label = clean_name(record.get("runner_group")) or "none", label_of(record.get("labels"))
            if status == "queued" and job_id is not None:
                self.waiting[job_id] = (label, self.clock())
                while len(self.waiting) > MAX_WAITING:
                    self.waiting.popitem(last=False)
                return True
            if status in ("in_progress", "completed"):
                self.waiting.pop(job_id, None)
            queue = record.get("queue")
            counted = False
            if isinstance(queue, int) and status in ("in_progress", "completed") and self._first_time(job_id):
                self.queue.observe({"runner_group": group, "label": label}, queue, cap)
                counted = True
            if status == "completed":
                conclusion = record.get("conclusion") or "unknown"
                self.jobs[(label, conclusion)] += 1
                if isinstance(record.get("seconds"), int):
                    self.job_secs.observe({"runner_group": group, "label": label, "conclusion": conclusion}, record["seconds"], cap)
                if cfg["per_runner"]:
                    name = clean_name(record.get("runner_name"))
                    if name and label.startswith("self-hosted"):
                        slot = self.runners.get(name)
                        if slot is None:
                            if len(self.runners) >= cap:
                                name = OTHER
                            slot = self.runners.setdefault(name, {"jobs": 0, "failed": 0, "busy": 0, "queue": 0})
                        slot["jobs"] += 1
                        slot["failed"] += 1 if conclusion in ("failure", "timed_out") else 0
                        slot["busy"] += record.get("seconds") or 0
                        slot["queue"] += queue if isinstance(queue, int) else 0
                counted = True
            self.observed += 1 if counted else 0
            return counted

    def demand(self):
        """{label: {"waiting": n, "oldest_seconds": s}}: the jobs that were queued and have not started."""
        now = self.clock()
        with self.lock:
            out = {}
            for label, since in self.waiting.values():
                slot = out.setdefault(label, {"waiting": 0, "oldest_seconds": 0})
                slot["waiting"] += 1
                slot["oldest_seconds"] = max(slot["oldest_seconds"], int(now - since))
            return out

    def runner_stats(self):
        """[{"runner", "jobs", "failed", "busy_seconds", "avg_queue_seconds"}], busiest first (I-173)."""
        with self.lock:
            rows = [{"runner": n, "jobs": s["jobs"], "failed": s["failed"], "busy_seconds": s["busy"], "avg_queue_seconds": round(s["queue"] / s["jobs"], 1) if s["jobs"] else 0}
                    for n, s in self.runners.items()]
        return sorted(rows, key=lambda r: (-r["busy_seconds"], r["runner"]))

    def render(self, prefix, esc, config=None):
        """The lines of the exposition for what was counted (empty while the setting is off)."""
        cfg = settings(config or {})
        lines = []
        if cfg["histograms"]:
            with self.lock:
                for hist in (self.queue, self.job_secs, self.run_secs):
                    lines += hist.lines(prefix, esc)
                if self.jobs:
                    lines += [f"# HELP {prefix}jobs_total Jobs that finished, by label and conclusion.", f"# TYPE {prefix}jobs_total counter"]
                    lines += [f'{prefix}jobs_total{{label="{esc(l)}",conclusion="{esc(c)}"}} {n}' for (l, c), n in sorted(self.jobs.items())]
            demand = self.demand()
            if demand:
                lines += [f"# HELP {prefix}runner_jobs_waiting Jobs queued and not started yet, by label (the demand for runners).", f"# TYPE {prefix}runner_jobs_waiting gauge"]
                lines += [f'{prefix}runner_jobs_waiting{{label="{esc(l)}"}} {d["waiting"]}' for l, d in sorted(demand.items())]
                lines += [f"# HELP {prefix}runner_oldest_wait_seconds Wait of the oldest job not started yet, by label.", f"# TYPE {prefix}runner_oldest_wait_seconds gauge"]
                lines += [f'{prefix}runner_oldest_wait_seconds{{label="{esc(l)}"}} {d["oldest_seconds"]}' for l, d in sorted(demand.items())]
        if cfg["per_runner"]:
            rows = self.runner_stats()
            for metric, key, kind, text in (("runner_jobs_total", "jobs", "counter", "Jobs a self-hosted runner finished."), ("runner_jobs_failed_total", "failed", "counter", "Jobs of a self-hosted runner that failed."),
                                            ("runner_busy_seconds_total", "busy_seconds", "counter", "Seconds a self-hosted runner spent running jobs.")):
                if rows:
                    lines += [f"# HELP {prefix}{metric} {text}", f"# TYPE {prefix}{metric} {kind}"]
                    lines += [f'{prefix}{metric}{{runner="{esc(r["runner"])}"}} {r[key]}' for r in rows]
        return lines


COLLECTOR = Collector()
