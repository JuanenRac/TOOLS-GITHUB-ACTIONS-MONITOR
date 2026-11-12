# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Optional local webhook receiver (OFF by default).

It only exists when actions_monitor.json says  "webhook": {"enabled": true, "secret": "<at least 32 random characters>"}.  The monitor still listens
on 127.0.0.1 only, so GitHub can reach it only through a tunnel YOU run on purpose (the tool never opens one). Every request must carry the standard
GitHub signature header `X-Hub-Signature-256: sha256=<hmac>` made with the shared secret from the config (never a GitHub token); anything else is
refused. What an accepted event does is small: it marks the repository named in the payload for a refresh on the next cycle (nothing is written
anywhere, no payload text is stored or shown, and only repositories the monitor already watches are accepted).
"""
import collections
import hashlib
import hmac
import json
import re
import threading
import time
from datetime import datetime, timezone

import i18n
import toolconfig

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
DELIVERY_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")   # X-GitHub-Delivery: a GUID
FULL_NAME_RE = re.compile(r"^([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})$")
MIN_SECRET = 32
MAX_BODY = 262144
MAX_DELIVERIES = 2000        # the replay memory is bounded: the oldest delivery ids fall out first
EVENTS = ("workflow_run", "workflow_job", "push", "release", "check_suite", "ping")

TEXT = {key: "wh." + key for key in ("off", "bad_secret", "too_big", "bad_signature", "bad_event", "bad_payload", "unknown_repo", "on", "bad_delivery")}   # keys of the messages (locales/*.json); use text(key)


def text(key):
    return i18n.t(TEXT[key])


def settings(config):
    cfg = (config or {}).get("webhook")
    cfg = cfg if isinstance(cfg, dict) else {}
    secret = cfg.get("secret") if isinstance(cfg.get("secret"), str) else ""
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


def reset():
    """Forgets every remembered delivery and every count (tests, and a changed secret)."""
    with _guard_lock:
        _seen.clear()
        _per_repo.clear()


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
    if full is not None:   # the owner named in the payload must be one this monitor watches
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


GITHUB_URL = re.compile(r"^https://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]{1,200}$")   # a link to the run on github.com or on a GitHub Enterprise Server host


def _time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def _name(value, size=100):
    return value[:size] if isinstance(value, str) and value else ""


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
    url = obj.get("html_url") if isinstance(obj.get("html_url"), str) and GITHUB_URL.match(obj["html_url"]) else None
    record = {"event": event, "repo": repo, "run_id": obj["run_id"] if event == "workflow_job" and isinstance(obj.get("run_id"), int) else obj["id"], "status": _name(obj.get("status"), 20),
              "conclusion": _name(obj.get("conclusion"), 20) or None, "branch": _name(obj.get("head_branch")), "sha": _name(obj.get("head_sha"), 40)[:7], "url": url,
              "attempt": obj.get("run_attempt") if isinstance(obj.get("run_attempt"), int) else None}
    if event == "workflow_run":
        record["workflow"] = _name(obj.get("name"))
        record["path"] = _name(obj.get("path"), 200).split("@")[0].rsplit("/", 1)[-1]
        record["started"] = _name(obj.get("run_started_at") or obj.get("created_at"), 25)
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
    return {"repo": record["repo"], "id": record["run_id"], "name": record["workflow"], "title": "", "event": "webhook", "branch": record["branch"], "path": record["path"], "sha": record["sha"],
            "actor": "", "status": record["status"], "conclusion": record["conclusion"], "started": record["started"], "seconds": record["seconds"] or 0, "url": record["url"], "attempt": record.get("attempt")}
