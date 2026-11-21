# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""OpenTelemetry export (`otlp.enabled`, OFF by default): the finished runs as TRACES and the header figures as METRICS, sent as OTLP/HTTP with JSON to a collector YOU name (`otlp.endpoint`).

  * Plain HTTP only to this computer; anywhere else HTTPS (the setting refuses anything else). Standard library only: no OpenTelemetry package.
  * Only what an operator of a dashboard needs: repository, workflow name, branch, event, conclusion, duration. No title, no author, no commit message, no log, no token.
  * Each run is sent once (the ids sent are remembered); a failed send is tried again in the next interval and its text is kept for the page (cleaned of anything like a token).
  * One span per run (`gha.run`): trace and span ids come from a hash of the repository and the run id, so a run keeps the same identifier. Metrics: gauges of the figures of the header.
  * `otlp.cicd_conventions` (off): the spans also carry the attributes of the OpenTelemetry semantic conventions for CI/CD (`cicd.pipeline.*`, `vcs.repository.*`) and the attempt of the run, and the name
    of the span follows them (`RUN <workflow>`), so a backend that understands them draws the pipelines without any mapping. The `gha.*` attributes stay.
  * `otlp.job_spans` (off; it needs the webhook): one span per finished job (`TASK <job>`), child of the span of its run (same trace, parent = the span of the run), with the runner, the labels, the queue time and
    the result. The jobs come from the signed `workflow_job` events; a job that the webhook never saw has no span.
"""
from github_actions_monitor.app import degraded
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from github_actions_monitor.security import netguard, secretstore

SCOPE = {"name": "github-actions-monitor"}
STATE = {"sent": set(), "total": 0, "last_ok": None, "last_error": "", "next": 0.0}
BAD = ("failure", "timed_out", "startup_failure")      # the same family as redrule.BAD: a run that waits for an approval is not a failure


def settings(config):
    cfg = config.get("otlp") if isinstance(config, dict) and isinstance(config.get("otlp"), dict) else {}
    interval = cfg.get("interval_seconds")
    endpoint = cfg.get("endpoint") if isinstance(cfg.get("endpoint"), str) else ""
    return {"cicd_conventions": cfg.get("cicd_conventions") is True, "job_spans": cfg.get("job_spans") is True, "enabled": cfg.get("enabled") is True and endpoint_ok(endpoint), "endpoint": endpoint.rstrip("/"), "interval_seconds": interval if isinstance(interval, int) and not isinstance(interval, bool) and 15 <= interval <= 3600 else 60}


def endpoint_ok(url):
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if parts.username or parts.password or not parts.hostname:
        return False
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost", "::1"))


def ids(repo, run_id, attempt=None):
    """(trace id, span id): the trace belongs to the run; the span to the attempt (the first attempt keeps the id it always had, a re-run has its own span in the same trace)."""
    digest = hashlib.sha256(f"{repo}/{run_id}".encode()).hexdigest()
    if isinstance(attempt, int) and not isinstance(attempt, bool) and attempt > 1:
        return digest[:32], hashlib.sha256(f"{repo}/{run_id}/{attempt}".encode()).hexdigest()[:16]
    return digest[:32], digest[32:48]


def _attempt(item):
    value = item.get("attempt") or item.get("run_attempt")
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 1


def run_key(run):
    """What the memory of the exported runs holds: the run and its attempt, because a re-run is another execution."""
    return (run.get("repo"), run.get("id"), _attempt(run))


def remember(keys, keep=5000):
    """Adds `keys` to the memory of what was sent, oldest first, and forgets only the oldest ones beyond `keep` (never half of the memory at random)."""
    sent = STATE["sent"]
    if not isinstance(sent, dict):
        sent = STATE["sent"] = dict.fromkeys(sent)
    for key in keys:
        sent.pop(key, None)
        sent[key] = None
    while len(sent) > keep:
        del sent[next(iter(sent))]


def _nano(text):
    try:
        return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    except (TypeError, ValueError):
        return 0


def attr(key, value):
    return {"key": key, "value": {"stringValue": str(value)}}


RESULTS = {"success": "success", "failure": "failure", "cancelled": "cancellation", "timed_out": "timeout", "startup_failure": "error", "skipped": "skip", "action_required": "error", "neutral": "success"}
JOBS = []      # the finished jobs the webhook saw, newest last (otlp.job_spans); memory only, bounded
MAX_JOBS = 2000


def note_job(record):
    """Keeps a finished job of a signed `workflow_job` event for the spans (only short validated fields)."""
    if not isinstance(record, dict) or record.get("event") != "workflow_job" or record.get("status") != "completed" or not record.get("job_started") or not record.get("job_completed"):
        return False
    JOBS[:] = [j for j in JOBS if (j.get("repo"), j.get("job_id")) != (record.get("repo"), record.get("job_id"))]      # the same job twice (a re-delivered event) is one span
    JOBS.append({k: record.get(k) for k in ("repo", "run_id", "job_id", "job", "workflow", "conclusion", "attempt", "labels", "runner_name", "runner_group", "queue", "job_started", "job_completed", "url")})
    del JOBS[:-MAX_JOBS]
    return True


def _cicd_attrs(run):
    """The attributes of the semantic conventions of CI/CD for a run (a value that is not known is left out)."""
    out = [attr("cicd.pipeline.name", run.get("name", "")), attr("cicd.pipeline.run.id", run.get("id")), attr("vcs.repository.name", run.get("repo", "")), attr("vcs.repository.ref.type", "branch")]
    if run.get("branch"):
        out.append(attr("vcs.repository.ref.name", run["branch"]))
    if run.get("url"):
        out.append(attr("cicd.pipeline.run.url.full", run["url"]))
    result = RESULTS.get(run.get("conclusion") or "")
    if result:
        out.append(attr("cicd.pipeline.result", result))
    if run.get("attempt"):
        out.append(attr("cicd.pipeline.run.attempt", run["attempt"]))
    return out


def span(run, cicd=False):
    trace, sid = ids(run.get("repo", ""), run.get("id"), _attempt(run))
    start = _nano(run.get("started"))
    end = start + int(max(0, run.get("seconds") or 0) * 1_000_000_000)
    failed = run.get("conclusion") in BAD
    attributes = [attr("gha.repo", run.get("repo", "")), attr("gha.workflow", run.get("name", "")), attr("gha.branch", run.get("branch") or ""), attr("gha.event", run.get("event") or ""),
                  attr("gha.conclusion", run.get("conclusion") or "")]
    if cicd:
        attributes += _cicd_attrs(run)
    return {"traceId": trace, "spanId": sid, "name": ("RUN " + str(run.get("name") or "")).strip() if cicd else "gha.run", "kind": 1, "startTimeUnixNano": str(start), "endTimeUnixNano": str(end),
            "attributes": attributes, "status": {"code": 2 if failed else 1}}


def job_span(job, cicd=False):
    """The span of a finished job: same trace as its run, child of the span of the run, with a stable id of its own."""
    trace, parent = ids(job.get("repo", ""), job.get("run_id"), _attempt(job))
    sid = hashlib.sha256(f"{job.get('repo')}/{job.get('run_id')}/{job.get('job_id')}".encode()).hexdigest()[:16]
    start, end = _nano(job.get("job_started")), _nano(job.get("job_completed"))
    failed = job.get("conclusion") in BAD
    attributes = [attr("gha.repo", job.get("repo", "")), attr("gha.workflow", job.get("workflow", "")), attr("gha.job", job.get("job", "")), attr("gha.conclusion", job.get("conclusion") or ""),
                  attr("gha.runner", job.get("runner_name") or ""), attr("gha.runner_group", job.get("runner_group") or ""), attr("gha.labels", ",".join(job.get("labels") or []))]
    if isinstance(job.get("queue"), int):
        attributes.append({"key": "gha.queue_seconds", "value": {"intValue": str(job["queue"])}})
    if cicd:
        attributes += [attr("cicd.pipeline.task.name", job.get("job", "")), attr("cicd.pipeline.task.run.id", job.get("job_id")), attr("cicd.pipeline.name", job.get("workflow", "")),
                       attr("cicd.pipeline.run.id", job.get("run_id")), attr("vcs.repository.name", job.get("repo", ""))]
        if job.get("url"):
            attributes.append(attr("cicd.pipeline.task.run.url.full", job["url"]))
        result = RESULTS.get(job.get("conclusion") or "")
        if result:
            attributes.append(attr("cicd.pipeline.task.run.result", result))
        if job.get("attempt"):
            attributes.append(attr("cicd.pipeline.run.attempt", job["attempt"]))
    return {"traceId": trace, "spanId": sid, "parentSpanId": parent, "name": ("TASK " + str(job.get("job") or "")).strip() if cicd else "gha.job", "kind": 1, "startTimeUnixNano": str(start),
            "endTimeUnixNano": str(max(start, end)), "attributes": attributes, "status": {"code": 2 if failed else 1}}


def traces(runs, resource, cicd=False, jobs=()):
    spans = [span(r, cicd) for r in runs] + [job_span(j, cicd) for j in jobs]
    return {"resourceSpans": [{"resource": {"attributes": resource}, "scopeSpans": [{"scope": SCOPE, "spans": spans}]}]}


def metrics(figures, resource, now=None):
    stamp = str(int((time.time() if now is None else now) * 1_000_000_000))
    names = {"active": "gha.runs.active", "queued": "gha.runs.queued", "fail24": "gha.runs.failed_24h", "ok24": "gha.runs.succeeded_24h", "issues": "gha.issues.open", "min24": "gha.minutes_24h", "red": "gha.workflows.red"}
    gauges = [{"name": name, "gauge": {"dataPoints": [{"asInt": str(int(figures[key])), "timeUnixNano": stamp}]}} for key, name in names.items() if isinstance(figures.get(key), (int, float))]
    return {"resourceMetrics": [{"resource": {"attributes": resource}, "scopeMetrics": [{"scope": SCOPE, "metrics": gauges}]}]}


def _send(request, config=None):
    """The request through the rule of netguard: a collector on this computer is called directly and its redirects are not followed; any other collector is refused when its name, or a redirect, leads
    to a private address (loopback, private, link-local, metadata) unless `notify.allow_private_targets` is on; no proxy of the environment is used."""
    notify = config.get("notify") if isinstance(config, dict) and isinstance(config.get("notify"), dict) else {}
    if urllib.parse.urlsplit(request.full_url).hostname in ("127.0.0.1", "localhost", "::1"):
        return netguard.local_open(request, timeout=10, follow_redirects=False).read()
    return netguard.open_url(request, timeout=10, allow_private=notify.get("allow_private_targets") is True).read()


def _post(url, document, opener=None, config=None):
    body = json.dumps(document).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    (opener or (lambda r: _send(r, config)))(request)


def export(config, data, version, now=None, post=None):
    """One export if it is due. Returns {"sent_spans", "sent_metrics", "error"}. Never raises."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not cfg["enabled"] or now < STATE["next"] or not data:
        return {"sent_spans": 0, "sent_metrics": 0, "error": ""}
    STATE["next"] = now + cfg["interval_seconds"]
    resource = [attr("service.name", "github-actions-monitor"), attr("service.version", version)]
    fresh = [r for r in data.get("runs") or [] if r.get("status") == "completed" and run_key(r) not in STATE["sent"]][:200]
    jobs = [j for j in JOBS if cfg["job_spans"] and ("job", j.get("repo"), j.get("job_id")) not in STATE["sent"]][:400]
    try:
        if fresh or jobs:
            _post(cfg["endpoint"] + "/v1/traces", traces(fresh, resource, cfg["cicd_conventions"], jobs), post, config)
        _post(cfg["endpoint"] + "/v1/metrics", metrics(data.get("figures") or {}, resource, now), post, config)
    except Exception as error:   # noqa: BLE001 - a collector that is down is not the monitor's problem
        degraded.note("otlp.send", error)
        STATE["last_error"] = secretstore.redact(str(error))[:160]
        return {"sent_spans": 0, "sent_metrics": 0, "error": STATE["last_error"]}
    remember([run_key(r) for r in fresh] + [("job", j.get("repo"), j.get("job_id")) for j in jobs])
    STATE.update({"total": STATE["total"] + len(fresh) + len(jobs), "last_ok": int(now), "last_error": ""})
    return {"sent_spans": len(fresh) + len(jobs), "sent_metrics": 1, "error": ""}


def status(config):
    cfg = settings(config)
    host = ""
    if cfg["endpoint"]:
        parts = urllib.parse.urlsplit(cfg["endpoint"])
        host = f"{parts.scheme}://{parts.hostname}" + (f":{parts.port}" if parts.port else "")
    return {"enabled": cfg["enabled"], "endpoint_host": host, "interval_seconds": cfg["interval_seconds"], "spans_sent": STATE["total"], "last_ok": STATE["last_ok"], "last_error": STATE["last_error"]}
