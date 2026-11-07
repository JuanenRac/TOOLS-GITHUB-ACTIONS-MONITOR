# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Optional local webhook receiver (OFF by default).

It only exists when actions_monitor.json says  "webhook": {"enabled": true, "secret": "<at least 32 random characters>"}.  The monitor still listens
on 127.0.0.1 only, so GitHub can reach it only through a tunnel YOU run on purpose (the tool never opens one). Every request must carry the standard
GitHub signature header `X-Hub-Signature-256: sha256=<hmac>` made with the shared secret from the config (never a GitHub token); anything else is
refused. What an accepted event does is small: it marks the repository named in the payload for a refresh on the next cycle (nothing is written
anywhere, no payload text is stored or shown, and only repositories the monitor already watches are accepted).
"""
import hashlib
import hmac
import json
import re

import i18n

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
MIN_SECRET = 32
MAX_BODY = 262144
EVENTS = ("workflow_run", "workflow_job", "push", "release", "check_suite", "ping")

TEXT = {key: "wh." + key for key in ("off", "bad_secret", "too_big", "bad_signature", "bad_event", "bad_payload", "unknown_repo", "on")}   # keys of the messages (locales/*.json); use text(key)


def text(key):
    return i18n.t(TEXT[key])


def settings(config):
    cfg = (config or {}).get("webhook")
    cfg = cfg if isinstance(cfg, dict) else {}
    secret = cfg.get("secret") if isinstance(cfg.get("secret"), str) else ""
    return {"enabled": cfg.get("enabled") is True, "secret": secret}


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
    return hmac.compare_digest(sign(secret, body), header.strip())


def handle(config, body, headers, watched):
    """(http code, answer dict, repo or None). `headers` is any mapping with .get. Never raises."""
    if not active(config):
        return 404, {"ok": False}, None
    if len(body) > MAX_BODY:
        return 413, {"ok": False, "error": text("too_big")}, None
    if not verify(settings(config)["secret"], body, headers.get("X-Hub-Signature-256")):
        return 401, {"ok": False, "error": text("bad_signature")}, None
    event = headers.get("X-GitHub-Event")
    if event not in EVENTS:
        return 202, {"ok": True, "ignored": True}, None
    if event == "ping":
        return 200, {"ok": True}, None
    try:
        name = json.loads(body)["repository"]["name"]
    except (ValueError, KeyError, TypeError):
        return 400, {"ok": False, "error": text("bad_payload")}, None
    if not isinstance(name, str) or not NAME_RE.match(name) or name not in set(watched):
        return 202, {"ok": True, "ignored": True}, None
    return 200, {"ok": True, "refresh": name}, name
