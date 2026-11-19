# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The figures of one day that feed the series of the daily trend and that the daily history did not have: how long the runs last (mean and p95), how long they wait in the queue, the workflows
that failed and then passed on the same commit, the Actions minutes of each repository, the size of the artifacts, the alerts of every severity and the days a release was published.

Everything is computed from what the cycle already holds in memory (the list of runs of each repository, the artifacts read by the surface checks, the releases of the repositories): there is
no call to GitHub here. A figure that cannot be told (no run in the last day, the artifacts were not read) is None: a day without data is a gap in the chart, never a zero.
"""
from datetime import datetime, timezone

from github_actions_monitor.data_pipeline import analytics

DAY = 86400
SEVERITIES = ("critical", "high", "medium", "low")
MAX_REPOS = 8      # the repositories drawn as series of minutes per day
MAX_RELEASES_PER_DAY = 5


def _time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if text else None
    except ValueError:
        return None


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def runs_of_the_day(runs_by_repo, now):
    """The runs that started in the last 24 hours, with the repository name in every run."""
    out = []
    for repo, runs in (runs_by_repo or {}).items():
        for run in runs or []:
            started = _time(run.get("started"))
            if started and 0 <= (now - started).total_seconds() <= DAY:
                out.append({**run, "repo": run.get("repo") or repo})
    return out


def run_figures(runs):
    """{"dur_avg", "dur_p95" (minutes), "queue_avg" (seconds), "flaky"} of the runs of the day. Each one is None when the runs cannot tell."""
    done = [r for r in runs if r.get("status") == "completed"]
    seconds = [r["seconds"] for r in done if r.get("conclusion") == "success" and _positive(r.get("seconds"))]
    queued = [r["queued"] for r in runs if isinstance(r.get("queued"), (int, float)) and not isinstance(r.get("queued"), bool) and r["queued"] >= 0]
    flaky = sum(row["flaky"] for row in analytics.flaky_rows(done, min_runs=1)) if done else None
    return {"dur_avg": round(sum(seconds) / len(seconds) / 60.0, 1) if seconds else None,
            "dur_p95": round(analytics.percentile(seconds, 95) / 60.0, 1) if seconds else None,
            "queue_avg": round(sum(queued) / len(queued), 1) if queued else None,
            "flaky": flaky}


def artifact_megabytes(raw):
    """The megabytes of the live artifacts of all the repositories, or None when the surface checks have not read any."""
    sizes = [(v.get("artifacts") or {}).get("bytes") for v in (raw or {}).values() if isinstance(v, dict)]
    sizes = [s for s in sizes if isinstance(s, (int, float)) and not isinstance(s, bool)]
    return round(sum(sizes) / 1048576.0, 1) if sizes else None


def severities(totals):
    """The open alerts of every severity from the per-repository counters ('moderate' is what GitHub calls the middle one of the dependency alerts)."""
    out = {k: 0 for k in SEVERITIES}
    for t in (totals or {}).values():
        sev = (t or {}).get("sev") or {}
        for k in SEVERITIES:
            out[k] += int(sev.get(k, 0) or 0) + (int(sev.get("moderate", 0) or 0) if k == "medium" else 0)
    return out


def release_days(releases):
    """{day: ["repo tag", ...]} of the days the latest release of each repository was published (at most MAX_RELEASES_PER_DAY names a day)."""
    out = {}
    for repo, rel in sorted((releases or {}).items()):
        day = str((rel or {}).get("publishedAt") or "")[:10]
        if len(day) == 10:
            names = out.setdefault(day, [])
            if len(names) < MAX_RELEASES_PER_DAY:
                names.append(f"{repo} {rel.get('tagName') or ''}".strip())
    return out


def build(runs_by_repo, now, raw, totals, minutes):
    """The block the sentinel puts in a7['day']: what the history keeps of this cycle."""
    figures = run_figures(runs_of_the_day(runs_by_repo, now))
    figures["artifact_mb"] = artifact_megabytes(raw)
    figures["min_repo"] = {r: v["min24"] for r, v in (minutes or {}).items() if _positive(v.get("min24"))} if any((runs_by_repo or {}).values()) else None      # no run read yet: no figure, not a day of zeros
    figures["severity"] = severities(totals)
    return figures


def merge_marks(days, found, key="releases"):
    """Writes the marks of a kind (`releases`, `workflows`) into the days of the history that exist (a mark of a day the monitor was off is not invented a day): the names already there are kept."""
    for day, names in (found or {}).items():
        if day in days and isinstance(days[day], dict):
            old = [n for n in (days[day].get(key) or []) if isinstance(n, str)]
            days[day][key] = (old + [n for n in names if n not in old])[:MAX_RELEASES_PER_DAY]


def merge_releases(days, found):
    """The release days into the days of the history (see merge_marks)."""
    merge_marks(days, found, "releases")


def commit_days(repo, commits, since_day=""):
    """{day: ["repo abc1234", ...]} of the days a commit touched the workflow files, from the answer of `commits?path=.github/workflows` (the date of the committer, the first 7 letters of the SHA).
    A commit without a date or with a SHA that is not hexadecimal is left out; a day before `since_day` is left out; the names of a day are at most MAX_RELEASES_PER_DAY."""
    out = {}
    for item in commits if isinstance(commits, list) else []:
        if not isinstance(item, dict):
            continue
        sha = str(item.get("sha") or "")
        when = str((((item.get("commit") or {}).get("committer") or {}).get("date")) or "")[:10]
        if len(when) != 10 or not (7 <= len(sha) <= 40) or any(c not in "0123456789abcdef" for c in sha) or (since_day and when < since_day):
            continue
        names = out.setdefault(when, [])
        name = f"{repo} {sha[:7]}"
        if name not in names and len(names) < MAX_RELEASES_PER_DAY:
            names.append(name)
    return out


def workflow_marks(history):
    """{day: [names]} of the days of the history in which a commit touched the workflow files."""
    out = {}
    for d, row in sorted((history.get("days") or {}).items()):
        names = [n for n in ((row or {}).get("workflows") or []) if isinstance(n, str)]
        if names:
            out[d] = names
    return out


def repo_series(history, top=MAX_REPOS):
    """{"dates", "repos": {repo: [minutes or None per day]}} for the repositories with most minutes in the history (the days before the figure existed are gaps)."""
    days = sorted((history.get("days") or {}))
    per_day = [(history["days"][d].get("min_repo") if isinstance(history["days"][d].get("min_repo"), dict) else None) for d in days]
    total = {}
    for row in per_day:
        for repo, value in (row or {}).items():
            if _positive(value):
                total[repo] = total.get(repo, 0) + value
    best = sorted(total, key=lambda r: (-total[r], r))[:top]
    return {"dates": days, "repos": {r: [None if row is None else (row.get(r) if _positive(row.get(r)) else 0) for row in per_day] for r in best}}


def release_marks(history):
    """{day: [names]} of the days of the history in which a release was published."""
    out = {}
    for d, row in sorted((history.get("days") or {}).items()):
        names = [n for n in ((row or {}).get("releases") or []) if isinstance(n, str)]
        if names:
            out[d] = names
    return out
