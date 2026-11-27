# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of actions copied elsewhere as it grows (`audit_export.enabled`, off by default). Standard library only.

  target "file"    a JSON-lines file of your own, rotated at `audit_export.max_mb`
  target "syslog"  RFC 5424 messages over TCP with TLS (RFC 5425 framing; `audit_export.tls` off only for a receiver on your own network)
  target "http"    POST of batches of JSON lines to `audit_export.url` (the token, when asked, is read from the environment variable named in `audit_export.token_env`)

The log itself is the queue: a cursor (the hash of the last line the destination took) moves only after a send succeeds, so a destination that is down loses nothing and stops nothing. When what
waits passes `audit_export.spool_mb` the monitor says `system.audit_export_lag`; if the log rotated past the cursor before it could be sent, the lines that are gone are counted as lost.
The lines are sent as they are in the log, which never holds a secret."""
import json
import os
import socket
import ssl
import threading
import time
import urllib.request
from pathlib import Path

from github_actions_monitor.security import envguard, netguard, private_io
from github_actions_monitor.storage import locks

TARGETS = ("file", "syslog", "http")
ALERT_CODE = "system.audit_export_lag"
STATE_NAME = "audit_export_state.json"
DEFAULTS = {"enabled": False, "target": "file", "path": "", "host": "", "port": 6514, "tls": True, "ca_file": "", "url": "", "token_env": "", "batch": 100, "spool_mb": 50, "max_mb": 50,
            "allow_private_targets": False}
MAX_BATCHES = 20      # per pass: a long backlog goes out over several cycles
_RUNNING = threading.Lock()


def settings(config):
    block = config.get("audit_export") if isinstance(config, dict) and isinstance(config.get("audit_export"), dict) else {}
    out = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = block.get(key)
        if isinstance(default, bool):
            out[key] = value if isinstance(value, bool) else default
        elif isinstance(default, int):
            out[key] = value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 100000 else default
        elif isinstance(value, str) and len(value) <= 500:
            out[key] = value.strip()
    if out["target"] not in TARGETS:
        out["target"] = "file"
    out["batch"], out["port"] = min(out["batch"], 1000), min(out["port"], 65535)
    return out


def active(config):
    cfg = settings(config)
    needs = {"file": cfg["path"], "syslog": cfg["host"], "http": cfg["url"]}
    return cfg["enabled"] and bool(needs[cfg["target"]]) and not (config.get("airgapped") is True and cfg["target"] != "file")


def hosts(config):
    cfg = settings(config)
    if not cfg["enabled"] or cfg["target"] == "file":
        return []
    from urllib.parse import urlsplit
    found = cfg["host"] if cfg["target"] == "syslog" else (urlsplit(cfg["url"]).hostname or "")
    return [found.lower()] if found else []


def state_path():
    from github_actions_monitor.util import paths
    return paths.place(STATE_NAME)


def load_state(where=None):
    try:
        data = json.loads(Path(where or state_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data = data if isinstance(data, dict) else {}

    def number(key):      # a damaged file is read as far as it can be, never raised
        value = data.get(key)
        return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < 2 ** 53 else 0
    return {"cursor": str(data.get("cursor") or ""), "sent": number("sent"), "lost": number("lost"), "backlog_bytes": number("backlog_bytes"), "last_error": str(data.get("last_error") or "")[:200],
            "at": number("at")}


def pending(cursor, target=None):
    """(lines after the line whose hash is `cursor`, whether the cursor is gone) from the log and its rotated files, the oldest first."""
    from github_actions_monitor.security import audit_log, compliance_checkpoints
    rows = [e for e in compliance_checkpoints.entries(target or audit_log.path()) if isinstance(e.get("hash"), str)]
    if not cursor:
        return rows, False
    for index in range(len(rows) - 1, -1, -1):
        if rows[index]["hash"] == cursor:
            return rows[index + 1:], False
    return rows, bool(rows)


def line_of(entry):
    return json.dumps(entry, ensure_ascii=False, separators=(",", ":"))


def syslog_frame(entry, hostname=None):
    """One RFC 5424 message with the octet count of RFC 5425 in front. Facility 13 (log audit), severity 6 (informational) or 4 (a refusal or an error)."""
    severity = 6 if entry.get("result") == "ok" else 4
    host = "".join(c for c in (hostname or socket.gethostname()) if 33 <= ord(c) <= 126)[:255] or "-"
    message = f"<{13 * 8 + severity}>1 {entry.get('at') or '-'} {host} github-actions-monitor - audit - {line_of(entry)}".encode("utf-8")
    return str(len(message)).encode("ascii") + b" " + message


def send_file(cfg, rows, env=None):
    where = Path(cfg["path"])
    with locks.os_lock(where, 5.0):
        if where.is_file() and where.stat().st_size > cfg["max_mb"] * 1_000_000:
            os.replace(where, where.with_name(where.name + ".1"))
        with private_io.open_append(where) as handle:
            handle.write("".join(line_of(row) + "\n" for row in rows))


def send_syslog(cfg, rows, env=None):
    address = netguard.check_host(cfg["host"], cfg["port"], cfg["allow_private_targets"])
    with socket.create_connection((address, cfg["port"]), timeout=10) as raw:
        if cfg["tls"]:
            context = ssl.create_default_context(cafile=cfg["ca_file"] or None)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            with context.wrap_socket(raw, server_hostname=cfg["host"]) as secure:
                secure.sendall(b"".join(syslog_frame(row) for row in rows))
        else:
            raw.sendall(b"".join(syslog_frame(row) for row in rows))


def send_http(cfg, rows, env=None):
    env = os.environ if env is None else env
    if not cfg["url"].startswith(("https://", "http://")):
        raise ValueError("url")
    headers = {"Content-Type": "application/x-ndjson", "User-Agent": "github-actions-monitor"}
    secret = env.get(cfg["token_env"], "") if envguard.NamePattern().match(cfg["token_env"]) else ""
    if secret:
        if cfg["url"].startswith("http://") and not (cfg["allow_private_targets"] and netguard.only_private(cfg["url"])):
            raise ValueError("a token is not sent without TLS")
        headers["Authorization"] = "Bearer " + secret
    request = urllib.request.Request(cfg["url"], data=("\n".join(line_of(r) for r in rows) + "\n").encode("utf-8"), headers=headers, method="POST")
    with netguard.open_url(request, timeout=10, allow_private=cfg["allow_private_targets"], follow_redirects=False) as answer:
        answer.read(100)


SENDERS = {"file": send_file, "syslog": send_syslog, "http": send_http}


def run(config, where=None, log=None, now=None, sender=None):
    """One pass: sends what waits, in batches, and moves the cursor after each batch that arrived. Returns the state. Never raises."""
    now = time.time() if now is None else now
    state = load_state(where)
    if not active(config):
        return state
    cfg = settings(config)
    send = sender or SENDERS[cfg["target"]]
    try:
        rows, gone = pending(state["cursor"], log)
        if gone:      # the log rotated past the cursor: what was in between cannot be sent any more
            state["lost"] += 1
        state["last_error"] = ""
        for _batch in range(MAX_BATCHES):
            if not rows:
                break
            part, rows = rows[:cfg["batch"]], rows[cfg["batch"]:]
            try:
                send(cfg, part)
            except Exception as error:      # noqa: BLE001 - a destination that is down never stops the monitor
                secret = os.environ.get(cfg["token_env"], "") if cfg["token_env"] else ""
                text = f"{type(error).__name__}: {str(error)[:120]}"
                state["last_error"] = text.replace(secret, "***") if secret else text
                rows = part + rows
                break
            state["cursor"], state["sent"] = part[-1]["hash"], state["sent"] + len(part)
        state["backlog_bytes"] = sum(len(line_of(r).encode("utf-8")) + 1 for r in rows)
        state["at"] = int(now)
        target = Path(where or state_path())
        private_io.private_dir(target.parent)
        private_io.write_private(target, json.dumps(state))
    except Exception as error:      # noqa: BLE001
        state["last_error"] = f"{type(error).__name__}: {str(error)[:120]}"
    return state


def lagging(config, state):
    """True when more waits than `audit_export.spool_mb`, or lines were lost."""
    return settings(config)["enabled"] and (state["backlog_bytes"] > settings(config)["spool_mb"] * 1_000_000 or state["lost"] > 0)


def tick(config, data=None):
    """After a cycle: one pass in a thread of its own (never two at once), so a slow destination does not delay the next cycle."""
    if not active(config) or not _RUNNING.acquire(blocking=False):
        return None

    def work():
        try:
            run(config)
        finally:
            _RUNNING.release()
    thread = threading.Thread(target=work, name="audit-export", daemon=True)
    thread.start()
    return thread
