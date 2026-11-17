# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Optional local webhook receiver (OFF by default).

It only exists when actions_monitor.json says  "webhook": {"enabled": true}  AND the shared secret (at least 32 random characters) is in the environment variable named by
`webhook.secret_env` (MONITOR_WEBHOOK_SECRET by default) or in the file named by that variable plus `_FILE`: the secret is never written in the configuration, shown or logged (a secret in the
configuration file is read only when `webhook.allow_config_secret` is true, a way to migrate that is off by default). The monitor still listens
on 127.0.0.1 only, so GitHub can reach it only through a tunnel YOU run on purpose (the tool never opens one). Every request must carry the standard
GitHub signature header `X-Hub-Signature-256: sha256=<hmac>` made with the shared secret from the config (never a GitHub token); anything else is
refused. What an accepted event does is small: it marks the repository named in the payload for a refresh on the next cycle (nothing is written
anywhere, no payload text is stored or shown, and only repositories the monitor already watches are accepted).
"""
import collections
import hashlib
import hmac
import json
import os
import re
import threading
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n
from github_actions_monitor.app import toolconfig
from github_actions_monitor.security import envguard
from github_actions_monitor.security.redactor import redact

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
DELIVERY_RE = re.compile(r"^[A-Za-z0-9-]{8,64}\Z")   # X-GitHub-Delivery: a GUID
FULL_NAME_RE = re.compile(r"^([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})\Z")
MIN_SECRET = 32
SECRET_ENV = "MONITOR_WEBHOOK_SECRET"      # the default name of the variable that holds the shared secret
ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}\Z")
MAX_BODY = 262144
MAX_DELIVERIES = 2000        # the replay memory is bounded: the oldest delivery ids fall out first
EVENTS = ("workflow_run", "workflow_job", "check_run", "push", "release", "check_suite", "ping")      # the closed list: any other event is answered 202 and dropped

TEXT = {key: "wh." + key for key in ("off", "bad_secret", "too_big", "bad_signature", "bad_event", "bad_payload", "unknown_repo", "on", "bad_delivery")}   # keys of the messages (locales/*.json); use text(key)


def text(key):
    return i18n.t(TEXT[key])


def secret_env_name(config):
    """The NAME of the environment variable that holds the shared secret (`webhook.secret_env`); a name that is not a plain variable name falls back to MONITOR_WEBHOOK_SECRET."""
    cfg = (config or {}).get("webhook")
    name = cfg.get("secret_env") if isinstance(cfg, dict) else None
    return name if isinstance(name, str) and ENV_NAME_RE.match(name) else SECRET_ENV


def read_secret(name):
    """The value of the environment variable `name` (held by envguard once the process started), else the first line of the file named by `name + "_FILE"`, else ''. Never printed."""
    value = envguard.get(name).strip()
    if value:
        return value
    path = os.environ.get(name + "_FILE", "").strip()
    if path:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                return handle.readline().strip()
        except (OSError, UnicodeError):
            return ""
    return ""


def secret_source(config):
    """"env" | "config" | "none": where the shared secret comes from, never the secret. "config" only when `webhook.allow_config_secret` is true and the variable is empty."""
    cfg = (config or {}).get("webhook")
    cfg = cfg if isinstance(cfg, dict) else {}
    if read_secret(secret_env_name(config)):
        return "env"
    return "config" if cfg.get("allow_config_secret") is True and isinstance(cfg.get("secret"), str) and cfg["secret"] else "none"


def settings(config):
    cfg = (config or {}).get("webhook")
    cfg = cfg if isinstance(cfg, dict) else {}
    source = secret_source(config)
    secret = read_secret(secret_env_name(config)) if source == "env" else cfg["secret"] if source == "config" else ""
    return {"enabled": cfg.get("enabled") is True, "secret": secret}


def live_settings(config):
    """What an accepted event is used for: {"record_events": bool, "live_events_keep": int}. Kept apart from settings() so the secret never travels with them."""
    cfg = (config or {}).get("webhook")
    cfg = cfg if isinstance(cfg, dict) else {}
    keep = cfg.get("live_events_keep")
    return {"record_events": cfg.get("record_events", True) is True, "live_events_keep": keep if isinstance(keep, int) and not isinstance(keep, bool) and 10 <= keep <= 1000 else 100}


def guard_settings(config):
    """{"replay_seconds", "max_per_minute", "allowed_owners"}: how long a delivery id is remembered, how many accepted events one repository may cause per minute, and the owners
    (besides github_owner) whose repositories may be named in a payload."""
    cfg = (config or {}).get("webhook")
    cfg = cfg if isinstance(cfg, dict) else {}

    def number(key, default, low, high):
        value = cfg.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default
    owners = [o for o in (cfg.get("allowed_owners") or []) if isinstance(o, str) and re.match(r"^[A-Za-z0-9-]{1,39}$", o)] if isinstance(cfg.get("allowed_owners"), list) else []
    return {"replay_seconds": number("replay_seconds", 3600, 60, 86400), "max_per_minute": number("max_per_minute", 30, 1, 600), "allowed_owners": owners}


_guard_lock = threading.Lock()
_seen = collections.OrderedDict()     # delivery id -> time it was accepted (signature already verified)
_per_repo = {}                        # repository -> times of the events accepted in the last minute


_accepted = collections.deque(maxlen=5000)     # when each event that named a watched repository was accepted (bounded)
_started = [time.time()]


def reset():
    """Forgets every remembered delivery and every count (tests, and a changed secret)."""
    with _guard_lock:
        _seen.clear()
        _per_repo.clear()
        _accepted.clear()
        _started[0] = time.time()


def note_accepted(now=None):
    """One event for a watched repository was accepted: the coverage indicator counts it."""
    with _guard_lock:
        _accepted.append(time.time() if now is None else now)


def coverage(config, now=None):
    """How much of the time the events cover the state, as a small read-only record: {"state": "off" | "waiting" | "live" | "quiet", "last_age_seconds", "last_hour", "window_minutes", "watching_seconds",
    "fallback": "poll"}. `live` = the last event is newer than `savings.webhook_window_minutes`; `quiet` = it is older (nothing arrived for a while, which is also what a lost tunnel looks like); `waiting` =
    switched on and nothing yet. The polling is always the fallback: it reads whatever the events did not tell, so a missed delivery never leaves the state wrong for longer than one slow turn."""
    from github_actions_monitor.data_pipeline import savings
    now = time.time() if now is None else now
    window = savings.settings(config or {})["webhook_window_minutes"]
    with _guard_lock:
        times = list(_accepted)
        since = _started[0]
    out = {"state": "off", "last_age_seconds": None, "last_hour": sum(1 for t in times if t > now - 3600), "window_minutes": window, "watching_seconds": max(0, int(now - since)), "fallback": "poll"}
    if not active(config):
        return out
    if not times:
        out["state"] = "waiting"
        return out
    age = max(0, int(now - times[-1]))
    out["last_age_seconds"] = age
    out["state"] = "live" if age <= window * 60 else "quiet"
    return out


def replay(delivery, window, now=None):
    """True when this delivery id was already accepted within `window` seconds; otherwise remembers it (bounded memory) and returns False."""
    now = time.time() if now is None else now
    with _guard_lock:
        while _seen and (len(_seen) > MAX_DELIVERIES or next(iter(_seen.values())) < now - window):
            _seen.popitem(last=False)
        if delivery in _seen and _seen[delivery] >= now - window:
            return True
        _seen[delivery] = now
        _seen.move_to_end(delivery)
        return False


def throttled(repo, limit, now=None):
    """True when `repo` already caused `limit` accepted events in the last minute; otherwise counts this one."""
    now = time.time() if now is None else now
    with _guard_lock:
        recent = [x for x in _per_repo.get(repo, []) if x > now - 60]
        if len(recent) >= limit:
            _per_repo[repo] = recent
            return True
        _per_repo[repo] = recent + [now]
        if len(_per_repo) > 5000:
            for key in [k for k, v in _per_repo.items() if not v or v[-1] < now - 60]:
                _per_repo.pop(key, None)
        return False


def active(config):
    """True only when switched on AND the secret is long enough. A short secret keeps the endpoint closed (fail closed)."""
    cfg = settings(config)
    return cfg["enabled"] and len(cfg["secret"]) >= MIN_SECRET


def status_text(config):
    cfg = settings(config)
    if not cfg["enabled"]:
        return text("off")
    return text("on") if len(cfg["secret"]) >= MIN_SECRET else text("bad_secret")


def sign(secret, body):
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify(secret, body, header):
    """Constant-time comparison of the GitHub signature header with the one we compute."""
    if not secret or not isinstance(header, str) or not header.startswith("sha256="):
        return False
    try:
        return hmac.compare_digest(sign(secret, body).encode("ascii"), header.strip().encode("ascii"))   # bytes: a header with other characters is a plain "no", not an exception
    except UnicodeError:
        return False


def handle(config, body, headers, watched):
    """(http code, answer dict, repo or None). `headers` is any mapping with .get. Never raises."""
    if not active(config):
        return 404, {"ok": False}, None
    if len(body) > MAX_BODY:
        return 413, {"ok": False, "error": text("too_big")}, None
    if not verify(settings(config)["secret"], body, headers.get("X-Hub-Signature-256")):
        return 401, {"ok": False, "error": text("bad_signature")}, None
    guard = guard_settings(config)
    delivery = headers.get("X-GitHub-Delivery")
    if not isinstance(delivery, str) or not DELIVERY_RE.match(delivery):
        return 400, {"ok": False, "error": text("bad_delivery")}, None
    if replay(delivery, guard["replay_seconds"]):     # a valid request captured and sent again: answered, never acted on
        return 202, {"ok": True, "ignored": True, "duplicate": True}, None
    event = headers.get("X-GitHub-Event")
    if event not in EVENTS:
        return 202, {"ok": True, "ignored": True}, None
    if event == "ping":
        return 200, {"ok": True}, None
    try:
        payload = json.loads(body)
        name = payload["repository"]["name"]
        full = payload["repository"].get("full_name")
    except (ValueError, KeyError, TypeError, AttributeError):
        return 400, {"ok": False, "error": text("bad_payload")}, None
    if not isinstance(name, str) or not NAME_RE.match(name) or name not in set(watched):
        return 202, {"ok": True, "ignored": True}, None
    if True:   # the owner named in the payload must be one this monitor watches; GitHub always names it, so a payload without it is not believed
        found = FULL_NAME_RE.match(full) if isinstance(full, str) else None
        owners = {o.lower() for o in guard["allowed_owners"]} | {toolconfig.github_owner(config).lower()}
        owners.discard("")
        if not found or found.group(2) != name or (owners and found.group(1).lower() not in owners):
            return 202, {"ok": True, "ignored": True}, None
    if throttled(name, guard["max_per_minute"]):
        return 202, {"ok": True, "ignored": True, "throttled": True}, None
    return 200, {"ok": True, "refresh": name}, name


#: the only fields of a parsed event that may reach the live list, the feed or a notification (everything else of a payload is dropped by `parse_event`, and this list guards the way out)
LIVE_FIELDS = ("event", "repo", "run_id", "status", "conclusion", "branch", "sha", "url", "attempt", "workflow", "path", "started", "seconds", "job", "queue")


RUN_EVENT_RE = re.compile(r"^[a-z_]{1,30}\Z")
GITHUB_URL = re.compile(r"^https://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]{1,200}\Z")   # a link to the run on github.com or on a GitHub Enterprise Server host


def _time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


CONTROL = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029]+")
STATUSES = ("queued", "in_progress", "completed", "waiting", "requested", "pending")
CONCLUSIONS = ("success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "startup_failure", "stale")


def _name(value, size=100):
    """A free text of the payload (a workflow, a branch, a job, a step): one line, no control characters, no secret, cut. It reaches the live list, the stream and the notices."""
    if not isinstance(value, str) or not value:
        return ""
    return redact(CONTROL.sub(" ", value).strip())[:size]


def _word(value, allowed):
    """The status or the conclusion only when it is one of the closed list of GitHub, else nothing."""
    return value if isinstance(value, str) and value in allowed else ""


def _stamp(text):
    """The date of the payload in the one shape the monitor reads, or nothing."""
    return text if isinstance(text, str) and _time(text) is not None else ""


def parse_event(event, body):
    """A small, validated record of a `workflow_run` or `workflow_job` event, or None for any other event or a payload that does not look right.

    {"event", "repo", "workflow", "run_id", "status", "conclusion", "branch", "sha", "attempt", "url", "seconds", "queue", "job", "steps": {name: seconds}}
    Only these short fields are kept (never the commit message, the actor's e-mail or any free text of the payload)."""
    if event not in ("workflow_run", "workflow_job"):
        return None
    try:
        payload = json.loads(body)
        repo = payload["repository"]["name"]
        obj = payload["workflow_run" if event == "workflow_run" else "workflow_job"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(repo, str) or not NAME_RE.match(repo) or not isinstance(obj, dict) or not isinstance(obj.get("id"), int):
        return None
    full = payload["repository"].get("full_name") if isinstance(payload.get("repository"), dict) else None
    url = obj.get("html_url") if isinstance(obj.get("html_url"), str) and GITHUB_URL.match(obj["html_url"]) else None
    if url is not None:      # the link goes to the notices and the live list: it must point to the repository the payload names (owner and name), not to any address
        path = "/" + url.split("/", 3)[3] if url.count("/") >= 3 else ""
        if not (isinstance(full, str) and FULL_NAME_RE.match(full) and path.lower().startswith(f"/{full}/".lower())):
            url = None
    record = {"event": event, "repo": repo, "run_id": obj["run_id"] if event == "workflow_job" and isinstance(obj.get("run_id"), int) else obj["id"], "status": _word(obj.get("status"), STATUSES),
              "conclusion": _word(obj.get("conclusion"), CONCLUSIONS) or None, "branch": _name(obj.get("head_branch")), "sha": _name(obj.get("head_sha"), 40)[:7], "url": url,
              "attempt": obj.get("run_attempt") if isinstance(obj.get("run_attempt"), int) else None}
    if event == "workflow_run":
        kind = obj.get("event")      # push, schedule, pull_request...: the rule of the red counts a run by it, so it is kept (a short word, never free text)
        record["run_event"] = kind if isinstance(kind, str) and RUN_EVENT_RE.match(kind) else ""
        record["workflow"] = _name(obj.get("name"))
        record["path"] = _name(obj.get("path"), 200).split("@")[0].rsplit("/", 1)[-1]
        record["started"] = _stamp(obj.get("run_started_at")) or _stamp(obj.get("created_at"))
        a, b = _time(obj.get("run_started_at") or obj.get("created_at")), _time(obj.get("updated_at"))
        record["seconds"] = max(0, int(b - a)) if a is not None and b is not None and obj.get("status") == "completed" else None
    else:
        record["workflow"] = _name(obj.get("workflow_name"))
        record["job"] = _name(obj.get("name"))
        created, started, done = _time(obj.get("created_at")), _time(obj.get("started_at")), _time(obj.get("completed_at"))
        record["queue"] = max(0, int(started - created)) if created is not None and started is not None else None
        record["seconds"] = max(0, int(done - started)) if started is not None and done is not None else None
        record["steps"] = {}
        for step in obj.get("steps") or []:
            if isinstance(step, dict) and step.get("name"):
                a, b = _time(step.get("started_at")), _time(step.get("completed_at"))
                if a is not None and b is not None:
                    record["steps"][_name(step["name"], 80)] = max(0, int(b - a))
    return record


def as_run(record):
    """The record of a `workflow_run` in the shape of the run list of the monitor (so a webhook can update a repository without reading it again)."""
    if not record or record.get("event") != "workflow_run":
        return None
    return {"repo": record["repo"], "id": record["run_id"], "name": record["workflow"], "title": "", "event": record.get("run_event") or "webhook", "branch": record["branch"], "path": record["path"], "sha": record["sha"],
            "actor": "", "status": record["status"], "conclusion": record["conclusion"], "started": record["started"], "seconds": record["seconds"] or 0, "url": record["url"], "attempt": record.get("attempt")}


# --- the live events as a read-only stream (server-sent events), OFF by default -------------------------------------------------------------------------------------------------
SSE_STREAMS = [0]
SSE_LOCK = threading.Lock()


def sse_settings(config):
    """{"enabled", "max_seconds", "max_clients"} of `live.sse`: the stream of the live events is OFF until you turn it on; anything out of range falls back to the default."""
    cfg = (config or {}).get("live")
    cfg = cfg.get("sse") if isinstance(cfg, dict) else None
    cfg = cfg if isinstance(cfg, dict) else {}

    def number(key, low, high, default):
        value = cfg.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default
    return {"enabled": cfg.get("enabled") is True, "max_seconds": number("max_seconds", 60, 86400, 3600), "max_clients": number("max_clients", 1, 10, 3)}


def sse_acquire(config):
    """True when one more listener may start (`live.sse.max_clients`); call sse_release() when it ends."""
    with SSE_LOCK:
        if SSE_STREAMS[0] >= sse_settings(config)["max_clients"]:
            return False
        SSE_STREAMS[0] += 1
        return True


def sse_release():
    with SSE_LOCK:
        SSE_STREAMS[0] = max(0, SSE_STREAMS[0] - 1)


def _sse_frame(name, data, ident=None):
    return (f"id: {ident}\n" if ident is not None else "") + f"event: {name}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


def sse_frames(config, snapshot, stop=lambda: False, sleep=time.sleep, clock=time.time, since=None, keepalive=15, poll=1.0):
    """The frames of the live stream. `snapshot()` returns (total, events): how many events were accepted since the monitor started and the newest ones, newest last. `hello` comes first
    (how many are held), then one `live` frame per new event (its `id` is the running number, to resume with Last-Event-ID; what is no longer held cannot be sent again), a comment every
    `keepalive` seconds, and `bye` when `live.sse.max_seconds` is over or `stop()` says so. Only the closed list LIVE_FIELDS (plus the time) is ever sent."""
    cfg = sse_settings(config)
    started = clock()
    total, events = snapshot()
    seen = total if since is None else max(0, min(int(since), total))
    yield _sse_frame("hello", {"held": len(events), "total": total})
    last_beat = started
    while not stop() and clock() - started < cfg["max_seconds"]:
        total, events = snapshot()
        if total > seen:
            fresh = events[-min(total - seen, len(events)):] if events else []
            first = total - len(fresh)
            for number, event in enumerate(fresh, start=first + 1):
                yield _sse_frame("live", {k: event.get(k) for k in LIVE_FIELDS + ("at",) if k in event}, number)
            seen = total
            last_beat = clock()
        if clock() - last_beat >= keepalive:
            last_beat = clock()
            yield ": keepalive\n\n"
        sleep(poll)
    yield _sse_frame("bye", {"reason": "stopped" if stop() else "time"})
