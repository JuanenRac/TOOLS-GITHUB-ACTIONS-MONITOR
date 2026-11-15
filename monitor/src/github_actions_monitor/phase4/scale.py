# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Scale and operation of the server, as pure, deterministic parts the supervisor can drive:

  WorkQueues      one bounded queue per (account, sentinel) with back-pressure: the same job queued twice is coalesced, a full queue refuses the new job (and counts it) instead of growing, an
                  account never runs more than `per_account_parallel` jobs at once, and the accounts are served in turn so a busy one cannot starve the others
  TickMetrics     the monitor's own measurements: latency of each tick (p50, p95, max over the last N), errors, size of the state, rate limit remaining per account
  render_metrics  those numbers (and the queue's) in the Prometheus text format, with a cap on the number of series
  limits_report   the documented limits of one installation (accounts, repositories) and how close an installation is to them

Nothing here starts a thread, sleeps or reads a clock: the caller passes `now` and runs the jobs, so every rule is tested without time."""
import re
from collections import deque

PREFIX = "ghamon_"
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}\Z")
MAX_SERIES = 2000
MAX_BACKOFF = 600
DOCUMENTED_LIMITS = {"accounts_per_install": 20, "repos_per_install": 500, "queue_depth": 8, "per_account_parallel": 2}      # what the installation guide states; the settings may lower or raise them
WARN_AT = 0.8


def _label(value):
    return value if isinstance(value, str) and LABEL_RE.match(value) else None


def _esc(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class WorkQueues:
    def __init__(self, depth=8, per_account_parallel=2):
        self.depth, self.parallel = depth, per_account_parallel
        self.queues = {}                # (account, sentinel) -> deque of job ids
        self.running = {}               # account -> set of (sentinel, job)
        self.dropped = {}               # key -> number refused
        self.coalesced = {}
        self.accepted = {}
        self.rejects_in_a_row = {}
        self._order = deque()           # accounts in turn

    def submit(self, account, sentinel, job):
        """"accepted", "coalesced" (already waiting) or "rejected" (the queue is full: back-pressure). A bad name is rejected too."""
        if _label(account) is None or _label(sentinel) is None:
            return "rejected"
        key = (account, sentinel)
        queue = self.queues.setdefault(key, deque())
        if account not in self._order:
            self._order.append(account)
        if job in queue or (sentinel, job) in self.running.get(account, set()):
            self.coalesced[key] = self.coalesced.get(key, 0) + 1
            return "coalesced"
        if len(queue) >= self.depth:
            self.dropped[key] = self.dropped.get(key, 0) + 1
            self.rejects_in_a_row[key] = self.rejects_in_a_row.get(key, 0) + 1
            return "rejected"
        queue.append(job)
        self.accepted[key] = self.accepted.get(key, 0) + 1
        self.rejects_in_a_row[key] = 0
        return "accepted"

    def next(self):
        """(account, sentinel, job) to run now, or None. Accounts in turn; an account at its parallel limit is skipped."""
        for _ in range(len(self._order)):
            account = self._order[0]
            self._order.rotate(-1)
            if len(self.running.get(account, ())) >= self.parallel:
                continue
            for (acc, sentinel), queue in sorted(self.queues.items()):
                if acc == account and queue:
                    job = queue.popleft()
                    self.running.setdefault(account, set()).add((sentinel, job))
                    return account, sentinel, job
        return None

    def done(self, account, sentinel, job):
        self.running.get(account, set()).discard((sentinel, job))

    def depth_of(self, account, sentinel):
        return len(self.queues.get((account, sentinel), ()))

    def backoff(self, account, sentinel, base=5):
        """Seconds a producer should wait before offering this sentinel again: 0 until it was refused, then doubling up to MAX_BACKOFF."""
        rejects = self.rejects_in_a_row.get((account, sentinel), 0)
        return 0 if rejects == 0 else min(MAX_BACKOFF, base * 2 ** (rejects - 1))

    def snapshot(self):
        return {"depth": {f"{a}/{s}": len(q) for (a, s), q in self.queues.items() if q}, "running": {a: len(r) for a, r in self.running.items() if r},
                "dropped": {f"{a}/{s}": n for (a, s), n in self.dropped.items()}, "coalesced": {f"{a}/{s}": n for (a, s), n in self.coalesced.items()}}


def percentile(values, p):
    """Nearest-rank percentile of a list (0 for an empty one)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, -(-int(p * len(ordered)) // 100))
    return float(ordered[min(rank, len(ordered)) - 1])


class TickMetrics:
    def __init__(self, history=50):
        self.history = history
        self.ticks = {}          # (account, sentinel) -> deque of seconds
        self.errors = {}
        self.count = {}
        self.state_bytes = {}
        self.rate_remaining = {}

    def record_tick(self, account, sentinel, seconds, ok=True, state_bytes=None):
        key = (account, sentinel)
        if _label(account) is None or _label(sentinel) is None or not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0:
            return False
        self.ticks.setdefault(key, deque(maxlen=self.history)).append(float(seconds))
        self.count[key] = self.count.get(key, 0) + 1
        if not ok:
            self.errors[key] = self.errors.get(key, 0) + 1
        if isinstance(state_bytes, int) and not isinstance(state_bytes, bool) and state_bytes >= 0:
            self.state_bytes[key] = state_bytes
        return True

    def record_rate(self, account, remaining):
        if _label(account) is not None and isinstance(remaining, int) and not isinstance(remaining, bool) and remaining >= 0:
            self.rate_remaining[account] = remaining

    def summary(self):
        out = {}
        for key, values in self.ticks.items():
            out[key] = {"count": self.count.get(key, 0), "errors": self.errors.get(key, 0), "p50": percentile(values, 50), "p95": percentile(values, 95), "max": max(values),
                        "state_bytes": self.state_bytes.get(key)}
        return out


def render_metrics(metrics, queues=None):
    """Prometheus text (version 0.0.4). The series are capped at MAX_SERIES so a bug in the labels cannot grow the answer without end."""
    lines, seen, series = [], set(), [0]

    def add(name, help_text, kind, value, labels):
        if value is None or series[0] >= MAX_SERIES:
            return
        full = PREFIX + name
        if full not in seen:
            seen.add(full)
            lines.append(f"# HELP {full} {help_text}")
            lines.append(f"# TYPE {full} {kind}")
        tag = "{" + ",".join(f'{k}="{_esc(v)}"' for k, v in sorted(labels.items())) + "}" if labels else ""
        lines.append(f"{full}{tag} {repr(round(value, 6)) if isinstance(value, float) else int(value)}")
        series[0] += 1

    for (account, sentinel), s in sorted(metrics.summary().items()):
        base = {"account": account, "sentinel": sentinel}
        add("tick_seconds", "Duration of the last ticks of a sentinel, by quantile.", "gauge", s["p50"], dict(base, quantile="0.5"))
        add("tick_seconds", "Duration of the last ticks of a sentinel, by quantile.", "gauge", s["p95"], dict(base, quantile="0.95"))
        add("tick_seconds", "Duration of the last ticks of a sentinel, by quantile.", "gauge", s["max"], dict(base, quantile="1"))
        add("ticks_total", "Ticks run by a sentinel.", "counter", s["count"], base)
        add("tick_errors_total", "Ticks of a sentinel that ended in an error.", "counter", s["errors"], base)
        add("state_bytes", "Size in bytes of the state a sentinel keeps.", "gauge", s["state_bytes"], base)
    for account, remaining in sorted(metrics.rate_remaining.items()):
        add("rate_limit_remaining", "Requests left in the GitHub allowance of an account.", "gauge", remaining, {"account": account})
    if queues is not None:
        snap = queues.snapshot()
        for key, n in sorted(snap["depth"].items()):
            account, sentinel = key.split("/", 1)
            add("queue_depth", "Jobs waiting for a sentinel of an account.", "gauge", n, {"account": account, "sentinel": sentinel})
        for key, n in sorted(snap["dropped"].items()):
            account, sentinel = key.split("/", 1)
            add("queue_dropped_total", "Jobs refused because the queue was full (back-pressure).", "counter", n, {"account": account, "sentinel": sentinel})
        for account, n in sorted(snap["running"].items()):
            add("jobs_running", "Jobs running for an account.", "gauge", n, {"account": account})
    return "\n".join(lines) + ("\n" if lines else "")


def limits_report(accounts, repos, settings=None):
    """[{"code", "level", "value", "limit"}]: "accounts_near|accounts_over" and "repos_near|repos_over" against the settings (or the documented defaults). Empty = comfortably inside."""
    settings = settings or {}
    out = []
    for name, value, limit in (("accounts", accounts, settings.get("max_accounts", DOCUMENTED_LIMITS["accounts_per_install"])),
                               ("repos", repos, settings.get("max_repos_per_install", DOCUMENTED_LIMITS["repos_per_install"]))):
        if value > limit:
            out.append({"code": name + "_over", "level": "warning", "value": value, "limit": limit})
        elif value >= limit * WARN_AT:
            out.append({"code": name + "_near", "level": "info", "value": value, "limit": limit})
    return out
