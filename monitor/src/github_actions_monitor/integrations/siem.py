# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Events towards a SIEM (OFF; optional). `siem.sinks` is a list, empty by default; each sink says where the events of the monitor go in the format that destination takes:

  elasticsearch  `POST <url>/_bulk` (one NDJSON action per event; `index` names the index)
  splunk_hec     `POST <url>/services/collector/event`, `Authorization: Splunk <token>`
  loki           `POST <url>/loki/api/v1/push` (a stream with the labels `job` and `level`)
  sentinel       Microsoft Sentinel / Log Analytics, Data Collector API (`POST https://<workspace>.ods.opinsights.azure.com/api/logs`, signed with the shared key)
  bigquery       `POST <url>` of the `tabledata.insertAll` of a table (`Authorization: Bearer <token>`)
  http           `POST <url>` of the JSON lines, for any other receiver

A sink: {"type", "enabled" (false), "url", "token_env" (NAME of the environment variable that holds the token or key: never the secret itself, never written to the file), "workspace_id" and "log_type"
(sentinel), "index" (elasticsearch), "from_minutes" (5: events older than that are not sent), "repos_filter" ([] = all; patterns with *), "levels" ([] = all),
"allow_private" (false: a receiver on a private address is refused unless this is on)}. The event has a closed list of fields (see `shape`): no token, no log text, no path. Every send goes through
`netguard` (no private address, no redirect that carries a secret); a failure is noted and the events wait in a bounded queue (`siem.queue_max`, 500) and are dropped oldest first. Nothing leaves
the computer unless a sink is enabled, and not at all in the offline mode (`airgapped`)."""
import base64
import datetime
import fnmatch
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.request

TYPES = ("elasticsearch", "splunk_hec", "loki", "sentinel", "bigquery", "http")
FIELDS = ("at", "kind", "code", "level", "repo", "text", "url", "owner")
DEFAULT_SINK = {"type": "http", "enabled": False, "url": "", "token_env": "", "workspace_id": "", "log_type": "GhaMonitor", "index": "gha-monitor", "from_minutes": 5,
                "repos_filter": [], "levels": [], "allow_private": False}
QUEUE = []
LOCK = threading.Lock()
STATUS = {"sent": 0, "failed": 0, "dropped": 0, "last_error": ""}


def settings(config):
    """{"queue_max", "sinks": [clean sinks]}; a sink that is not well formed is left out."""
    block = config.get("siem") if isinstance(config, dict) and isinstance(config.get("siem"), dict) else {}
    qmax = block.get("queue_max")
    out = {"queue_max": qmax if isinstance(qmax, int) and not isinstance(qmax, bool) and 10 <= qmax <= 10000 else 500, "sinks": []}
    for raw in block.get("sinks") if isinstance(block.get("sinks"), list) else []:
        if not isinstance(raw, dict) or raw.get("type") not in TYPES:
            continue
        sink = dict(DEFAULT_SINK)
        sink["type"] = raw["type"]
        sink["enabled"] = raw.get("enabled") is True
        for key in ("url", "workspace_id", "log_type", "index"):
            if isinstance(raw.get(key), str) and 0 < len(raw[key]) <= 300:
                sink[key] = raw[key].strip()
        if isinstance(raw.get("token_env"), str) and 0 < len(raw["token_env"]) <= 64 and raw["token_env"].replace("_", "").isalnum():
            sink["token_env"] = raw["token_env"]
        minutes = raw.get("from_minutes")
        if isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 1440:
            sink["from_minutes"] = minutes
        sink["allow_private"] = raw.get("allow_private") is True
        for key in ("repos_filter", "levels"):
            if isinstance(raw.get(key), list):
                sink[key] = [str(x)[:100] for x in raw[key] if isinstance(x, str)][:50]
        if sink["url"].startswith(("https://", "http://")):
            out["sinks"].append(sink)
    return out


def shape(event):
    """The event as the SIEM gets it: a closed list of fields, text cut, nothing else."""
    row = {k: (str(event.get(k))[:500] if event.get(k) is not None else "") for k in FIELDS if k in event}
    row.setdefault("at", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    row["source"] = "github-actions-monitor"
    return row


def wanted(sink, event, now=None):
    """Whether this sink takes this event: not older than `from_minutes`, one of its levels, a repository that matches its filter."""
    now = now or time.time()
    if sink["levels"] and event.get("level") not in sink["levels"]:
        return False
    repo = str(event.get("repo") or "")
    if sink["repos_filter"] and not any(fnmatch.fnmatchcase(repo, p) for p in sink["repos_filter"]):
        return False
    stamp = event.get("at")
    if isinstance(stamp, str):
        try:
            when = datetime.datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()
            if now - when > sink["from_minutes"] * 60:
                return False
        except ValueError:
            pass
    return True


def request_for(sink, rows, secret="", now=None):
    """(url, headers, body bytes) of one send. Pure: the tests check each format without a network."""
    url = sink["url"].rstrip("/")
    ndjson = lambda items: ("\n".join(json.dumps(i, ensure_ascii=False, separators=(",", ":")) for i in items) + "\n").encode("utf-8")  # noqa: E731
    if sink["type"] == "elasticsearch":
        body = ndjson([x for row in rows for x in ({"index": {"_index": sink["index"]}}, row)])
        headers = {"Content-Type": "application/x-ndjson"}
        if secret:
            headers["Authorization"] = "ApiKey " + secret
        return url + "/_bulk", headers, body
    if sink["type"] == "splunk_hec":
        body = "".join(json.dumps({"time": time.time() if now is None else now, "source": "github-actions-monitor", "sourcetype": "_json", "event": row}) for row in rows).encode("utf-8")
        return url + "/services/collector/event", {"Content-Type": "application/json", "Authorization": "Splunk " + secret}, body
    if sink["type"] == "loki":
        values = [[str(int((time.time() if now is None else now) * 1e9) + i), json.dumps(row, ensure_ascii=False)] for i, row in enumerate(rows)]
        body = json.dumps({"streams": [{"stream": {"job": "github-actions-monitor", "level": str(rows[0].get("level") or "info") if rows else "info"}, "values": values}]}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if secret:
            headers["Authorization"] = "Bearer " + secret
        return url + "/loki/api/v1/push", headers, body
    if sink["type"] == "sentinel":
        body = json.dumps(rows, ensure_ascii=False).encode("utf-8")
        stamp = datetime.datetime.fromtimestamp(time.time() if now is None else now, datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        to_sign = f"POST\n{len(body)}\napplication/json\nx-ms-date:{stamp}\n/api/logs"
        try:
            key = base64.b64decode(secret)
        except ValueError:
            key = b""
        signature = base64.b64encode(hmac.new(key, to_sign.encode("utf-8"), hashlib.sha256).digest()).decode("ascii")
        headers = {"Content-Type": "application/json", "Log-Type": sink["log_type"], "x-ms-date": stamp, "Authorization": f"SharedKey {sink['workspace_id']}:{signature}"}
        return url + "/api/logs?api-version=2016-04-01", headers, body
    if sink["type"] == "bigquery":
        body = json.dumps({"rows": [{"json": row} for row in rows]}).encode("utf-8")
        return url, {"Content-Type": "application/json", "Authorization": "Bearer " + secret}, body
    return url, {"Content-Type": "application/x-ndjson", **({"Authorization": "Bearer " + secret} if secret else {})}, ndjson(rows)


def _post(request, allow_private):
    from github_actions_monitor.security import netguard
    with netguard.open_url(request, timeout=10, allow_private=allow_private, follow_redirects=False) as answer:
        return answer.status


def enqueue(config, events):
    """Puts the events a sink may take in the queue (bounded: the oldest are dropped). Returns how many were queued. Nothing when no sink is enabled or in the offline mode."""
    if isinstance(config, dict) and config.get("airgapped") is True:
        return 0
    cfg = settings(config)
    active = [s for s in cfg["sinks"] if s["enabled"]]
    if not active:
        return 0
    queued = 0
    with LOCK:
        for event in events if isinstance(events, list) else []:
            if isinstance(event, dict) and event.get("kind") and any(wanted(s, event) for s in active):
                QUEUE.append(shape(event))
                queued += 1
        while len(QUEUE) > cfg["queue_max"]:
            QUEUE.pop(0)
            STATUS["dropped"] += 1
    return queued


def flush(config, post=_post, env=None):
    """Sends the queue to every enabled sink (each one gets the events it wants). A failed send is noted in STATUS and the events stay queued for the next flush. Returns the number of sends made."""
    env = os.environ if env is None else env
    cfg = settings(config)
    sends = 0
    with LOCK:
        rows = list(QUEUE)
    if not rows:
        return 0
    delivered_all = True
    for sink in (s for s in cfg["sinks"] if s["enabled"]):
        mine = [r for r in rows if wanted(sink, {"level": r.get("level"), "repo": r.get("repo"), "at": r.get("at")})]
        if not mine:
            continue
        secret = (env.get(sink["token_env"]) or "") if sink["token_env"] else ""
        url, headers, body = request_for(sink, mine, secret)
        try:
            post(urllib.request.Request(url, data=body, headers=headers, method="POST"), sink["allow_private"])
            STATUS["sent"] += len(mine)
            sends += 1
        except Exception as error:   # noqa: BLE001 - a receiver that is down never stops the monitor
            delivered_all = False
            STATUS["failed"] += 1
            message = type(error).__name__ + ": " + str(error)[:120]
            STATUS["last_error"] = message.replace(secret, "***") if secret else message
    if delivered_all:
        with LOCK:
            del QUEUE[:len(rows)]
    return sends


def make_listener(config_reader):
    """A listener for the feed of events of a sentinel: queues what the sinks want and sends it. It never raises."""
    def listener(events):
        try:
            config = config_reader()
            if enqueue(config, events):
                flush(config)
        except Exception:   # noqa: BLE001
            pass
    return listener
