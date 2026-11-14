# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Optional notifications (OFF by default): the events of the feed (a new red, a stuck build, a build waiting for its signature, a lost connection...) sent to a chat or to a device.

  telegram    a bot message           token in the environment variable named by `token_env`, `chat_id` in the file
  discord     a channel webhook       the full URL is in the environment variable named by `url_env` (discord.com only)
  slack       an incoming webhook     the full URL is in the environment variable named by `url_env` (hooks.slack.com only)
  matrix      a room message          `homeserver` (https), `room`, token in the variable named by `token_env`
  mqtt        a message to a broker ON THIS COMPUTER (127.0.0.1 / localhost) for lights and beacons in a workshop
  http_local  a POST of the same JSON to an address ON THIS COMPUTER (127.0.0.1 / localhost)

Rules, all tested: a secret (token, webhook URL) is read from the environment at the moment of sending and is never written to the configuration, to a log or to the page (only the NAME of
the variable is configured); a notification is only a message with a link: it never re-runs, cancels or writes anything on GitHub; every channel has its own switch; the whole thing is
off until `notify.enabled` is true; a send that fails is ignored (and counted) so it can never stop the monitor; at most `max_per_hour` messages leave the computer.
"""
import json
import os
import re
import socket
import struct
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlparse

from github_actions_monitor.security import netguard
from github_actions_monitor.util import tzdisplay

CHANNELS = ("telegram", "discord", "slack", "matrix", "mqtt", "http_local")
KNOWN_EVENTS = ("red_new", "red_fixed", "stuck_new", "pending_sign", "release_due", "rate_low", "offline", "online", "alerts_up", "workflow_failed", "collab_new", "collab_fixed", "credential_blind", "credential_back")
DEFAULT_EVENTS = ["red_new", "stuck_new", "pending_sign", "offline", "credential_blind"]
LOOPBACK = ("127.0.0.1", "localhost", "::1", "[::1]")
ENV_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}\Z")
TIMEOUT = 8
DEFAULTS = {"enabled": False, "allow_private_targets": False, "use_proxy": False, "events": list(DEFAULT_EVENTS), "max_per_hour": 20,
            "channels": {
                "telegram": {"enabled": False, "token_env": "", "chat_id": ""},
                "discord": {"enabled": False, "url_env": ""},
                "slack": {"enabled": False, "url_env": ""},
                "matrix": {"enabled": False, "homeserver": "", "room": "", "token_env": ""},
                "mqtt": {"enabled": False, "host": "127.0.0.1", "port": 1883, "topic": "ghamon/events"},
                "http_local": {"enabled": False, "url": ""},
            }}
_lock = threading.Lock()
_sent = []          # timestamps of the messages that left (for max_per_hour)
STATS = {"sent": 0, "failed": 0, "limited": 0}


def settings(config):
    """`notify` of the configuration merged over DEFAULTS; a value of the wrong type keeps the default."""
    out = json.loads(json.dumps(DEFAULTS))
    network = (config or {}).get("network")
    if isinstance(network, dict) and isinstance(network.get("use_proxy"), bool):
        out["use_proxy"] = network["use_proxy"]      # network.use_proxy: the proxies of the environment, with the destination judged first (netguard)
    user = (config or {}).get("notify")
    if not isinstance(user, dict):
        return out
    if isinstance(user.get("enabled"), bool):
        out["enabled"] = user["enabled"]
    if isinstance(user.get("allow_private_targets"), bool):
        out["allow_private_targets"] = user["allow_private_targets"]
    if isinstance(user.get("events"), list):
        out["events"] = [e for e in user["events"] if isinstance(e, str) and e in KNOWN_EVENTS]
    if isinstance(user.get("max_per_hour"), int) and not isinstance(user.get("max_per_hour"), bool) and 1 <= user["max_per_hour"] <= 600:
        out["max_per_hour"] = user["max_per_hour"]
    for name, base in DEFAULTS["channels"].items():
        item = (user.get("channels") or {}).get(name) if isinstance(user.get("channels"), dict) else None
        if isinstance(item, dict):
            for key, default in base.items():
                v = item.get(key)
                if isinstance(v, type(default)) and (isinstance(v, bool) == isinstance(default, bool)):
                    out["channels"][name][key] = v
    return out


def is_loopback(host):
    return str(host).strip().lower() in LOOPBACK


def secret(env_name):
    """The value of the environment variable NAMED in the configuration, or "" (the name must look like a variable name)."""
    return os.environ.get(env_name, "") if isinstance(env_name, str) and ENV_RE.match(env_name) else ""


def check_channel(name, cfg, allow_private=False):
    """None when the channel can send, else a short stable reason: off, no_secret, bad_host, bad_value, private_target (an address of the local network while `notify.allow_private_targets` is off)."""
    if not cfg.get("enabled"):
        return "off"
    if name == "telegram":
        return None if secret(cfg.get("token_env")) and re.match(r"^-?[0-9]{1,20}$", str(cfg.get("chat_id"))) else "no_secret"
    if name in ("discord", "slack"):
        url = secret(cfg.get("url_env"))
        if not url:
            return "no_secret"
        host = urlparse(url)
        allowed = ("discord.com", "discordapp.com") if name == "discord" else ("hooks.slack.com",)
        return None if host.scheme == "https" and host.hostname in allowed else "bad_host"
    if name == "matrix":
        home = urlparse(str(cfg.get("homeserver")))
        if not secret(cfg.get("token_env")):
            return "no_secret"
        if not (home.scheme == "https" and home.hostname and re.match(r"^![A-Za-z0-9:._-]{3,120}$", str(cfg.get("room")))):
            return "bad_value"
        return "private_target" if not allow_private and _private_literal(home.hostname) else None
    if name == "mqtt":
        topic = str(cfg.get("topic"))
        return None if is_loopback(cfg.get("host")) and 1 <= int(cfg.get("port", 0)) <= 65535 and re.match(r"^[A-Za-z0-9/_.-]{1,100}$", topic) else "bad_host"
    if name == "http_local":
        url = urlparse(str(cfg.get("url")))
        return None if url.scheme == "http" and is_loopback(url.hostname or "") else "bad_host"
    return "bad_value"


def _private_literal(host):
    """True for `localhost` or an address written as a number that points into this computer or the local network; names are judged when the connection opens."""
    host = str(host).strip("[]").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    if host.replace(".", "").isdigit() or ":" in host:
        return netguard.blocked_ip(host)
    return False


def _post(url, payload, headers=None, opener=None):
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    with (opener or netguard.local_open)(request, timeout=TIMEOUT) as answer:
        return answer.status


def mqtt_packet(topic, payload):
    """A MQTT 3.1.1 CONNECT followed by a QoS 0 PUBLISH, as bytes (stdlib only; enough for a broker on this computer)."""
    def text(value):
        raw = value.encode("utf-8")
        return struct.pack(">H", len(raw)) + raw

    def length(n):
        out = b""
        while True:
            digit, n = n % 128, n // 128
            out += bytes([digit | (128 if n else 0)])
            if not n:
                return out
    connect_body = text("MQTT") + b"\x04\x02" + struct.pack(">H", 30) + text("ghamon")
    publish_body = text(topic) + payload.encode("utf-8")
    return b"\x10" + length(len(connect_body)) + connect_body + b"\x30" + length(len(publish_body)) + publish_body + b"\xe0\x00"


def send_channel(name, cfg, event, opener=None, connect=None, allow_private=False, use_proxy=False):
    """Sends one event through one channel. Returns {"channel", "ok", "reason"}; never raises, never puts a secret in the answer."""
    problem = check_channel(name, cfg, allow_private)
    if problem:
        return {"channel": name, "ok": False, "reason": problem}
    if opener is None and name != "http_local":      # http_local is loopback by definition; every other channel goes through the rule of netguard (resolved address, redirects)
        opener = netguard.opener_for(allow_private, use_proxy=use_proxy)
    text = tzdisplay.localize(f"{event.get('text', '')}") + (f"\n{event['url']}" if event.get("url") else "")
    record = {"kind": event.get("kind"), "repo": event.get("repo"), "text": event.get("text"), "url": event.get("url")}
    try:
        if name == "telegram":
            _post(f"https://api.telegram.org/bot{secret(cfg['token_env'])}/sendMessage", {"chat_id": cfg["chat_id"], "text": text, "disable_web_page_preview": True}, opener=opener)
        elif name == "discord":
            _post(secret(cfg["url_env"]), {"content": text[:1900]}, opener=opener)
        elif name == "slack":
            _post(secret(cfg["url_env"]), {"text": text[:3000]}, opener=opener)
        elif name == "matrix":
            home = str(cfg["homeserver"]).rstrip("/")
            txn = f"ghamon{int(time.time() * 1000)}"
            url = f"{home}/_matrix/client/v3/rooms/{quote(cfg['room'], safe='')}/send/m.room.message/{txn}"
            request = urllib.request.Request(url, data=json.dumps({"msgtype": "m.text", "body": text}).encode("utf-8"), method="PUT",
                                             headers={"Content-Type": "application/json", "Authorization": "Bearer " + secret(cfg["token_env"])})
            with (opener or netguard.local_open)(request, timeout=TIMEOUT):
                pass
        elif name == "mqtt":
            sock = (connect or socket.create_connection)((cfg["host"], int(cfg["port"])), TIMEOUT)
            try:
                sock.sendall(mqtt_packet(cfg["topic"], json.dumps(record, ensure_ascii=False)))
            finally:
                sock.close()
        elif name == "http_local":
            _post(cfg["url"], record, opener=opener)
        return {"channel": name, "ok": True, "reason": ""}
    except (OSError, urllib.error.URLError, ValueError) as error:
        return {"channel": name, "ok": False, "reason": netguard.reason_of(error)}


def reserve(limit, count, now=None):
    """Books up to `count` MESSAGES (one per channel) of the `limit` allowed in the last hour, atomically (one lock for the whole booking, so several threads can never go over).
    Returns how many were granted, 0..count."""
    now = time.time() if now is None else now
    with _lock:
        while _sent and _sent[0] < now - 3600:
            _sent.pop(0)
        granted = max(0, min(count, limit - len(_sent)))
        _sent.extend([now] * granted)
        return granted


def allowed_now(limit, now=None):
    """True while fewer than `limit` messages left in the last hour (and registers one)."""
    return reserve(limit, 1, now) == 1


def notify(config, event, opener=None, connect=None, now=None):
    """Sends `event` through every enabled channel when notifications are on and the event kind is one the user asked for. Returns the list of results ([] when nothing was sent)."""
    from github_actions_monitor.integrations import dispatcher      # the users of the team mode who asked for this event (OFF by default, its own switch)
    dispatcher.dispatch(config, event)
    cfg = settings(config)
    if not cfg["enabled"] or event.get("kind") not in cfg["events"] or event.get("owner", "main") != "main":
        return []
    live = [(n, c) for n, c in cfg["channels"].items() if c.get("enabled")]
    if not live:
        return []
    allow = cfg["allow_private_targets"]
    broken = [{"channel": n, "ok": False, "reason": check_channel(n, c, allow)} for n, c in live if check_channel(n, c, allow)]   # a channel that cannot send books nothing
    ready = [(n, c) for n, c in live if not check_channel(n, c, allow)]
    granted = reserve(cfg["max_per_hour"], len(ready), now)      # max_per_hour counts MESSAGES: one unit for each channel that gets the event
    results = [send_channel(n, c, event, opener, connect, allow, cfg["use_proxy"]) for n, c in ready[:granted]]
    with _lock:
        STATS["sent"] += sum(1 for r in results if r["ok"])
        STATS["failed"] += sum(1 for r in results if not r["ok"]) + len(broken)
        STATS["limited"] += len(ready) - granted
    return results + broken if (results or broken) else []


def make_listener(config_fn):
    """A function to hang on the event feed (`feed.listeners`): it notifies every event, in its own thread, so a slow chat never delays the monitor."""
    def listener(events):
        for event in events:
            threading.Thread(target=notify, args=(config_fn(), event), daemon=True).start()
    return listener


def test_event(text="test"):
    return {"kind": "red_new", "owner": "main", "repo": "demo-repo", "text": text, "url": None}
