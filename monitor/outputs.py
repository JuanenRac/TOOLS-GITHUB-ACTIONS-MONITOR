# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Optional outputs of the monitor for other tools. All of them are OFF unless switched on in actions_monitor.json (outputs.*, or in the settings menu),
are served only on 127.0.0.1 by the same web server (the same Host/Origin checks as every other endpoint) and need no new token.

  GET /metrics                      Prometheus text format (version 0.0.4)             outputs.prometheus.enabled   (outputs.prometheus.per_repo adds the per-repository series)
  GET /api/outputs/grafana.json     JSON for the Grafana "Infinity" / JSON data source   outputs.json.enabled
  GET /api/outputs/dashboard.json   the document of ci_red.py (schema 2) for the status dashboard   outputs.dashboard.enabled

Nothing is read from GitHub here: the figures come from the snapshot of the sentinel and the state the monitor already holds, so a scrape costs no API quota.
Every metric name starts with ghamon_; a value that is not known is left out, never written as 0. The names follow the Prometheus conventions (gauges, base units,
the status of a repository as a number plus its labels), an idea shared with the existing exporters of GitHub Actions; no code of them is used.
"""
import calendar
import time

import ci_red
from tool_version import TOOL_VERSION

PREFIX = "ghamon_"
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _esc(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _num(value):
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return repr(round(value, 3))
    return str(int(value))


class _Out:
    def __init__(self):
        self.lines, self.seen = [], set()

    def add(self, name, help_text, value, labels=None, kind="gauge"):
        if value is None:
            return
        full = PREFIX + name
        if full not in self.seen:
            self.seen.add(full)
            self.lines.append(f"# HELP {full} {help_text}")
            self.lines.append(f"# TYPE {full} {kind}")
        tag = "{" + ",".join(f'{k}="{_esc(v)}"' for k, v in sorted((labels or {}).items())) + "}" if labels else ""
        self.lines.append(f"{full}{tag} {_num(value)}")


def _hours_since(since, now):
    try:
        t = calendar.timegm(time.strptime(str(since)[:19], "%Y-%m-%dT%H:%M:%S"))
        return max(0.0, (now - t) / 3600)
    except (ValueError, TypeError):
        return None


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def metrics_text(snapshot, data, per_repo=True, now=None, extra=None):
    """The Prometheus exposition of the current state. `snapshot` = sentinel snapshot (may be None), `data` = the monitor state (may be None)."""
    now = time.time() if now is None else now
    extra = extra if isinstance(extra, dict) else {}
    snap = snapshot if isinstance(snapshot, dict) and snapshot.get("enabled", True) else {}
    data = data if isinstance(data, dict) else {}
    out = _Out()
    out.add("info", "Version of the monitor (always 1).", 1, {"version": TOOL_VERSION})
    out.add("snapshot_complete", "1 when the sentinel snapshot is complete, 0 while it is loading or reduced.", 0 if (not snap or snap.get("loading")) else 1)
    eco = snap.get("ecosystems") or {}
    red = [r for r in (snap.get("a2") or {}).get("red") or [] if isinstance(r, dict) and r.get("repo")]
    if snap:
        out.add("red_workflows", "Workflows whose last completed run on the default branch is red.", len(red))
        out.add("red_repos", "Repositories with at least one red workflow.", len({r["repo"] for r in red}))
        for key in sorted(set(eco.values())):
            out.add("ecosystem_red_workflows", "Red workflows by ecosystem.", sum(1 for r in red if eco.get(r["repo"], "other") == key), {"ecosystem": key})
        if per_repo:
            for repo in sorted({r["repo"] for r in red}):
                out.add("repo_red_workflows", "Red workflows of a repository.", sum(1 for r in red if r["repo"] == repo), {"repo": repo, "ecosystem": eco.get(repo, "other")})
            for r in sorted(red, key=lambda x: (x["repo"], str(x.get("workflow")))):
                labels = {"repo": r["repo"], "workflow": r.get("workflow") or "", "ecosystem": eco.get(r["repo"], "other")}
                out.add("workflow_red_streak", "Consecutive red runs of a workflow on the default branch.", _int(r.get("streak")), labels)
                out.add("workflow_red_hours", "Hours since the workflow turned red.", _hours_since(r.get("since"), now), labels)
        pending = [g for g in (snap.get("a5") or {}).get("pending_sign") or [] if isinstance(g, dict) and g.get("repo")]
        out.add("pending_sign", "Builds waiting for the local signature or publication, over the threshold.", len(pending))
        out.add("pending_sign_repos", "Repositories with a build waiting to be signed.", len({g["repo"] for g in pending}))
        out.add("pending_sign_hours_max", "The longest wait for a signature, in hours.", max((g.get("hours") or 0 for g in pending), default=0))
        if per_repo:
            for repo in sorted({g["repo"] for g in pending}):
                out.add("repo_pending_sign_hours", "The longest signature wait of a repository, in hours.",
                        max(g.get("hours") or 0 for g in pending if g["repo"] == repo), {"repo": repo, "ecosystem": eco.get(repo, "other")})
        paused = (snap.get("a10") or {}).get("paused")
        out.add("surface_paused", "1 while the surface checks (A10) wait for GitHub quota.", 1 if paused else 0)
        if isinstance(paused, dict):
            out.add("surface_paused_remaining", "Quota left when A10 paused.", _int(paused.get("remaining")))
            out.add("surface_paused_needed", "Quota A10 needs to resume.", _int(paused.get("needed")))
        api = snap.get("api") or {}
        out.add("sentinel_calls_last_hour", "API calls made by the sentinel in the last hour.", _int(api.get("calls_last_hour")))
        out.add("sentinel_budget_per_hour", "Hourly API budget of the sentinel.", _int(api.get("budget_per_hour")))
    rate = data.get("rate") if isinstance(data.get("rate"), dict) else None
    if rate:
        out.add("api_rate_remaining", "GitHub API allowance left.", _int(rate.get("remaining")))
        out.add("api_rate_limit", "GitHub API allowance per hour.", _int(rate.get("limit")))
    if data:
        out.add("repos_watched", "Repositories the monitor watches.", len(data.get("repos") or []))
        active = data.get("active") or []
        out.add("runs_active", "Runs in progress or waiting.", len(active))
        out.add("runs_stuck", "Runs over the stuck threshold.", sum(1 for a in active if isinstance(a, dict) and a.get("stuck")))
        out.add("runs_failing", "Workflows whose latest run failed and was not fixed since.", len(data.get("failing") or []))
        out.add("issues_open", "Open issues opened by the CI bots.", len(data.get("issues") or []))
        out.add("quota_paused", "1 while the monitor is paused to protect the quota.", 1 if data.get("paused_quota") else 0)
    _extra_metrics(out, extra, eco, per_repo)
    return "\n".join(out.lines) + "\n"


def _extra_metrics(out, extra, eco, per_repo):
    """The metrics of 1.6.0: conditional reads, connection, durations (p50 / p95), queue times, steps, flaky rate, live events and notifications."""
    etag = extra.get("etag") if isinstance(extra.get("etag"), dict) else None
    if etag:
        out.add("etag_saved_total", "Reads answered with 304 Not Modified (no quota used) since the cache was created.", _int(etag.get("saved")), kind="counter")
        out.add("etag_entries", "Endpoints held in the conditional-read cache.", _int(etag.get("entries")))
    if "offline" in extra:
        out.add("offline", "1 while the monitor has no connection to GitHub and shows the last picture.", 1 if extra["offline"] else 0)
    if "live_events" in extra:
        out.add("live_events", "Events of the incoming webhook kept in memory.", _int(extra["live_events"]))
    if "disconnects" in extra:
        out.add("client_disconnects_total", "Requests whose browser or scraper closed the connection before the answer was sent.", _int(extra["disconnects"]), kind="counter")
    notify = extra.get("notify") if isinstance(extra.get("notify"), dict) else None
    if notify:
        out.add("notifications_sent_total", "Notifications that left the computer.", _int(notify.get("sent")), kind="counter")
        out.add("notifications_failed_total", "Notifications that could not be sent.", _int(notify.get("failed")), kind="counter")
    summary = extra.get("analytics") if isinstance(extra.get("analytics"), dict) else None
    if not summary or not summary.get("enabled", True):
        return
    out.add("workflows_slower", "Workflows whose p50 duration is well above their usual one.", len(summary.get("slower") or []))
    out.add("workflows_flaky", "Workflows with a possibly transient failure (failed, then passed on the same commit).", len(summary.get("flaky") or []))
    if not per_repo:
        return
    for row in (summary.get("duration") or [])[:200]:
        for q, key in (("0.5", "p50"), ("0.95", "p95")):
            out.add("workflow_duration_seconds", "Duration of the successful runs of a workflow (quantiles).", _int(row.get(key)),
                    {"repo": row["repo"], "workflow": row["workflow"], "ecosystem": eco.get(row["repo"], "other"), "quantile": q})
    for row in (summary.get("queue") or [])[:200]:
        for q, key in (("0.5", "p50"), ("0.95", "p95")):
            out.add("job_queue_seconds", "Time a job waited before it started (quantiles).", _int(row.get(key)),
                    {"repo": row["repo"], "workflow": row["workflow"], "ecosystem": eco.get(row["repo"], "other"), "quantile": q})
    for row in (summary.get("steps") or [])[:200]:
        for q, key in (("0.5", "p50"), ("0.95", "p95")):
            out.add("step_duration_seconds", "Duration of one step of a workflow (quantiles).", _int(row.get(key)),
                    {"repo": row["repo"], "workflow": row["workflow"], "step": row["step"], "quantile": q})
    for row in (summary.get("flaky") or [])[:200]:
        out.add("workflow_flaky_rate", "Share of the runs of a workflow that failed and then passed on the same commit (a label, not a verdict).", row.get("rate"),
                {"repo": row["repo"], "workflow": row["workflow"], "ecosystem": eco.get(row["repo"], "other")})


def grafana_json(snapshot, data, extra=None):
    """The same figures as tables for the JSON/Infinity data source: {"summary": {...}, "red": [rows], "pending_sign": [rows], "ecosystems": [rows]}."""
    snap = snapshot if isinstance(snapshot, dict) and snapshot.get("enabled", True) else {}
    data = data if isinstance(data, dict) else {}
    eco = snap.get("ecosystems") or {}
    red = [{"repo": r["repo"], "ecosystem": eco.get(r["repo"], "other"), "workflow": r.get("workflow"), "conclusion": r.get("conclusion"), "since": r.get("since"),
            "streak": r.get("streak"), "url": r.get("url")} for r in (snap.get("a2") or {}).get("red") or [] if isinstance(r, dict) and r.get("repo")]
    pending = [{"repo": g["repo"], "ecosystem": eco.get(g["repo"], "other"), "workflow": g.get("workflow"), "hours": g.get("hours"), "state": g.get("state"),
                "signature_kind": g.get("signature_kind"), "signature_verified": g.get("signature_verified"), "url": g.get("url")}
               for g in (snap.get("a5") or {}).get("pending_sign") or [] if isinstance(g, dict) and g.get("repo")]
    rate = data.get("rate") if isinstance(data.get("rate"), dict) else {}
    paused = (snap.get("a10") or {}).get("paused")
    summary = {"version": TOOL_VERSION, "generated": snap.get("generated"), "complete": bool(snap) and not snap.get("loading"),
               "red_workflows": len(red), "red_repos": len({r["repo"] for r in red}), "pending_sign": len(pending),
               "api_rate_remaining": rate.get("remaining"), "api_rate_limit": rate.get("limit"), "surface_paused": bool(paused),
               "runs_active": len(data.get("active") or []), "runs_failing": len(data.get("failing") or []), "repos_watched": len(data.get("repos") or [])}
    ecos = [{"ecosystem": key, "red_workflows": sum(1 for r in red if r["ecosystem"] == key), "pending_sign": sum(1 for g in pending if g["ecosystem"] == key)}
            for key in sorted(set(eco.values()))]
    analytics_part = (extra or {}).get("analytics") if isinstance((extra or {}).get("analytics"), dict) else {}
    return {"schema": 1, "summary": summary, "red": red, "pending_sign": pending, "ecosystems": ecos, "durations": analytics_part.get("duration") or [],
            "queue": analytics_part.get("queue") or [], "flaky": analytics_part.get("flaky") or [], "slower": analytics_part.get("slower") or []}


def dashboard_json(snapshot):
    """The document of ci_red.py for the status dashboard (None while there is no snapshot)."""
    if not isinstance(snapshot, dict) or snapshot.get("enabled") is False:
        return None
    return ci_red.build(snapshot)
