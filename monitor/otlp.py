# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""OpenTelemetry export (`otlp.enabled`, OFF by default): the finished runs as TRACES and the header figures as METRICS, sent as OTLP/HTTP with JSON to a collector YOU name (`otlp.endpoint`).

  * Plain HTTP only to this computer; anywhere else HTTPS (the setting refuses anything else). Standard library only: no OpenTelemetry package.
  * Only what an operator of a dashboard needs: repository, workflow name, branch, event, conclusion, duration. No title, no author, no commit message, no log, no token.
  * Each run is sent once (the ids sent are remembered); a failed send is tried again in the next interval and its text is kept for the page (cleaned of anything like a token).
  * One span per run (`gha.run`): trace and span ids come from a hash of the repository and the run id, so a run keeps the same identifier. Metrics: gauges of the figures of the header.
"""
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import secretstore

SCOPE = {"name": "github-actions-monitor"}
STATE = {"sent": set(), "total": 0, "last_ok": None, "last_error": "", "next": 0.0}
BAD = ("failure", "timed_out", "startup_failure", "action_required")


def settings(config):
    cfg = config.get("otlp") if isinstance(config, dict) and isinstance(config.get("otlp"), dict) else {}
    interval = cfg.get("interval_seconds")
    endpoint = cfg.get("endpoint") if isinstance(cfg.get("endpoint"), str) else ""
    return {"enabled": cfg.get("enabled") is True and endpoint_ok(endpoint), "endpoint": endpoint.rstrip("/"), "interval_seconds": interval if isinstance(interval, int) and not isinstance(interval, bool) and 15 <= interval <= 3600 else 60}


def endpoint_ok(url):
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if parts.username or parts.password or not parts.hostname:
        return False
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost", "::1"))


def ids(repo, run_id):
    digest = hashlib.sha256(f"{repo}/{run_id}".encode()).hexdigest()
    return digest[:32], digest[32:48]


def _nano(text):
    try:
        return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    except (TypeError, ValueError):
        return 0


def attr(key, value):
    return {"key": key, "value": {"stringValue": str(value)}}


def span(run):
    trace, sid = ids(run.get("repo", ""), run.get("id"))
    start = _nano(run.get("started"))
    end = start + int(max(0, run.get("seconds") or 0) * 1_000_000_000)
    failed = run.get("conclusion") in BAD
    return {"traceId": trace, "spanId": sid, "name": "gha.run", "kind": 1, "startTimeUnixNano": str(start), "endTimeUnixNano": str(end),
            "attributes": [attr("gha.repo", run.get("repo", "")), attr("gha.workflow", run.get("name", "")), attr("gha.branch", run.get("branch") or ""), attr("gha.event", run.get("event") or ""),
                           attr("gha.conclusion", run.get("conclusion") or "")],
            "status": {"code": 2 if failed else 1}}


def traces(runs, resource):
    return {"resourceSpans": [{"resource": {"attributes": resource}, "scopeSpans": [{"scope": SCOPE, "spans": [span(r) for r in runs]}]}]}


def metrics(figures, resource, now=None):
    stamp = str(int((time.time() if now is None else now) * 1_000_000_000))
    names = {"active": "gha.runs.active", "queued": "gha.runs.queued", "fail24": "gha.runs.failed_24h", "ok24": "gha.runs.succeeded_24h", "issues": "gha.issues.open", "min24": "gha.minutes_24h", "red": "gha.workflows.red"}
    gauges = [{"name": name, "gauge": {"dataPoints": [{"asInt": str(int(figures[key])), "timeUnixNano": stamp}]}} for key, name in names.items() if isinstance(figures.get(key), (int, float))]
    return {"resourceMetrics": [{"resource": {"attributes": resource}, "scopeMetrics": [{"scope": SCOPE, "metrics": gauges}]}]}


def _post(url, document, opener=None):
    body = json.dumps(document).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    (opener or (lambda r: urllib.request.urlopen(r, timeout=10).read()))(request)


def export(config, data, version, now=None, post=None):
    """One export if it is due. Returns {"sent_spans", "sent_metrics", "error"}. Never raises."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not cfg["enabled"] or now < STATE["next"] or not data:
        return {"sent_spans": 0, "sent_metrics": 0, "error": ""}
    STATE["next"] = now + cfg["interval_seconds"]
    resource = [attr("service.name", "github-actions-monitor"), attr("service.version", version)]
    fresh = [r for r in data.get("runs") or [] if r.get("status") == "completed" and (r.get("repo"), r.get("id")) not in STATE["sent"]][:200]
    try:
        if fresh:
            _post(cfg["endpoint"] + "/v1/traces", traces(fresh, resource), post)
        _post(cfg["endpoint"] + "/v1/metrics", metrics(data.get("figures") or {}, resource, now), post)
    except Exception as error:   # noqa: BLE001 - a collector that is down is not the monitor's problem
        STATE["last_error"] = secretstore.redact(str(error))[:160]
        return {"sent_spans": 0, "sent_metrics": 0, "error": STATE["last_error"]}
    STATE["sent"].update((r.get("repo"), r.get("id")) for r in fresh)
    if len(STATE["sent"]) > 5000:
        STATE["sent"] = set(list(STATE["sent"])[-2500:])
    STATE.update({"total": STATE["total"] + len(fresh), "last_ok": int(now), "last_error": ""})
    return {"sent_spans": len(fresh), "sent_metrics": 1, "error": ""}


def status(config):
    cfg = settings(config)
    host = ""
    if cfg["endpoint"]:
        parts = urllib.parse.urlsplit(cfg["endpoint"])
        host = f"{parts.scheme}://{parts.hostname}" + (f":{parts.port}" if parts.port else "")
    return {"enabled": cfg["enabled"], "endpoint_host": host, "interval_seconds": cfg["interval_seconds"], "spans_sent": STATE["total"], "last_ok": STATE["last_ok"], "last_error": STATE["last_error"]}
