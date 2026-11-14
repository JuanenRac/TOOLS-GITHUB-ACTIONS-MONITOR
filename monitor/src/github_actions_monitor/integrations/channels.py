# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Channels of the notifications of each user, as small plugins (OFF by default).

A plugin is a class with a `name`, the `fields` a user may set (`destination`), a `secret` (what is kept encrypted, never in the file), and three functions: `check_server(cfg)` for the part
the administrator sets (`notify.channels.<name>`), `check_destination(dest)` for the part each user sets, and `send(...)`. The registry is `PLUGINS`; adding a channel is adding a class here.

  ntfy    a message to a topic of a ntfy server (https, or a server of this computer); the topic is the destination; an access token is the optional secret
  teams   a message to the incoming webhook of a Microsoft Teams channel (hosts of Microsoft only); the address of the webhook is the secret
  email   an e-mail through a RELAY ON THIS COMPUTER (127.0.0.1) that has no login of its own; the address of the user is the destination

Rules, all tested: every channel has its own switch and is off by default; a secret is read at the moment of sending and never written to the configuration, to a log or to the page;
a message only informs (a link) and never acts on GitHub; the destination of a message passes the rule of netguard (no private address, no redirect) unless `notify.allow_private_targets`
is turned on; a failed send is counted and ignored, it never stops the monitor.
"""
import json
import re
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from urllib.parse import urlparse

from github_actions_monitor.security import netguard

TIMEOUT = 8
LOOPBACK = ("127.0.0.1", "localhost", "::1", "[::1]")
LEVEL_PRIORITY = {"bad": "5", "critical": "5", "warn": "4", "info": "3", "ok": "2"}
TEAMS_HOSTS = ("webhook.office.com", "outlook.office.com", "logic.azure.com", "powerplatform.com", "api.powerplatform.com")
ADDRESS_RE = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,200}\.[A-Za-z]{2,24}\Z")
TOPIC_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}\Z")
HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,200}\Z")


def _loopback(host):
    return str(host).strip().lower() in LOOPBACK


def _clean_line(text, limit):
    """One line, no control characters (a header of a mail or of a request can never be split)."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(text or "")).strip()[:limit]


def _body(message):
    text = _clean_line(message.get("text"), 1500)
    return text + (f"\n{message['url']}" if message.get("url") else "")


class Channel:
    name = ""
    fields = ()                  # the destination keys a user may set
    secret = ""                  # "" when the channel keeps none; else the destination key that is encrypted ("webhook", "token")
    secret_required = False
    defaults = {"enabled": False}

    def check_server(self, cfg, allow_private=False):
        return None if cfg.get("enabled") else "off"

    def check_destination(self, dest, secret=""):
        return "bad_value"

    def send(self, cfg, dest, secret, message, opener=None, allow_private=False, use_proxy=False, smtp=None):
        raise NotImplementedError


class Ntfy(Channel):
    name = "ntfy"
    fields = ("topic",)
    secret = "token"
    defaults = {"enabled": False, "server": "https://ntfy.sh"}

    def check_server(self, cfg, allow_private=False):
        if not cfg.get("enabled"):
            return "off"
        url = urlparse(str(cfg.get("server")))
        if url.scheme == "https" and url.hostname and not url.username and not url.password:
            return None
        return None if url.scheme == "http" and _loopback(url.hostname or "") else "bad_host"

    def check_destination(self, dest, secret=""):
        return None if TOPIC_RE.match(str((dest or {}).get("topic", ""))) else "bad_value"

    def send(self, cfg, dest, secret, message, opener=None, allow_private=False, use_proxy=False, smtp=None):
        url = str(cfg["server"]).rstrip("/") + "/" + dest["topic"]
        headers = {"Title": _clean_line(message.get("title"), 120) or "Monitor", "Priority": LEVEL_PRIORITY.get(message.get("level"), "3")}
        if message.get("url"):
            headers["Click"] = _clean_line(message["url"], 300)
        if secret:
            headers["Authorization"] = "Bearer " + _clean_line(secret, 300)
        request = urllib.request.Request(url, data=_body(message).encode("utf-8"), headers=headers, method="POST")
        local = _loopback(urlparse(url).hostname or "")
        send = (lambda r, timeout: netguard.local_open(r, timeout=timeout, follow_redirects=False)) if local else (opener or netguard.opener_for(allow_private, use_proxy=use_proxy))
        with send(request, timeout=TIMEOUT):
            pass


class Teams(Channel):
    name = "teams"
    fields = ()
    secret = "webhook"
    secret_required = True

    def check_destination(self, dest, secret=""):
        url = urlparse(str(secret))
        host = (url.hostname or "").lower()
        ok = url.scheme == "https" and not url.username and any(host == h or host.endswith("." + h) for h in TEAMS_HOSTS)
        return None if ok else ("no_secret" if not secret else "bad_host")

    def send(self, cfg, dest, secret, message, opener=None, allow_private=False, use_proxy=False, smtp=None):
        payload = {"text": _body(message)}
        request = urllib.request.Request(secret, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with (opener or netguard.opener_for(allow_private, use_proxy=use_proxy))(request, timeout=TIMEOUT):
            pass


class Email(Channel):
    name = "email"
    fields = ("address",)
    defaults = {"enabled": False, "host": "127.0.0.1", "port": 25, "sender": "monitor@localhost"}

    def check_server(self, cfg, allow_private=False):
        if not cfg.get("enabled"):
            return "off"
        host = str(cfg.get("host"))
        port = cfg.get("port")
        if not (isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535) or not HOST_RE.match(host):
            return "bad_host"
        if not (_loopback(host) or (allow_private and host.replace(".", "").isdigit() and netguard.blocked_ip(host))):
            return "bad_host"       # a relay of THIS computer; another address of the local network only with notify.allow_private_targets
        return None if ADDRESS_RE.match(str(cfg.get("sender"))) else "bad_value"

    def check_destination(self, dest, secret=""):
        return None if ADDRESS_RE.match(str((dest or {}).get("address", ""))) else "bad_value"

    def send(self, cfg, dest, secret, message, opener=None, allow_private=False, use_proxy=False, smtp=None):
        mail = EmailMessage()
        mail["From"], mail["To"] = cfg["sender"], dest["address"]
        mail["Subject"] = _clean_line(message.get("title"), 120) or "Monitor"
        mail.set_content(_body(message))
        with (smtp or smtplib.SMTP)(cfg["host"], int(cfg["port"]), timeout=TIMEOUT) as relay:      # no login: the relay of this computer accepts mail from this computer
            relay.send_message(mail)


PLUGINS = {c.name: c for c in (Ntfy(), Teams(), Email())}
NAMES = tuple(PLUGINS)


def server_defaults():
    return {name: dict(plugin.defaults) for name, plugin in PLUGINS.items()}


def server_settings(config):
    """`notify.channels.<plugin>` merged over the defaults; a value of the wrong type keeps the default."""
    saved = ((config or {}).get("notify") or {}).get("channels") if isinstance((config or {}).get("notify"), dict) else None
    out = server_defaults()
    if not isinstance(saved, dict):
        return out
    for name, base in out.items():
        item = saved.get(name)
        if isinstance(item, dict):
            for key, default in base.items():
                v = item.get(key)
                if isinstance(v, type(default)) and (isinstance(v, bool) == isinstance(default, bool)):
                    out[name][key] = v
    return out


def deliver(name, cfg, dest, secret, message, opener=None, allow_private=False, use_proxy=False, smtp=None):
    """Sends one message. Returns {"channel", "ok", "reason"}; never raises, never puts a secret in the answer."""
    plugin = PLUGINS.get(name)
    if plugin is None:
        return {"channel": name, "ok": False, "reason": "bad_value"}
    problem = plugin.check_server(cfg, allow_private) or plugin.check_destination(dest, secret)
    if not problem and plugin.secret_required and not secret:
        problem = "no_secret"
    if problem:
        return {"channel": name, "ok": False, "reason": problem}
    try:
        plugin.send(cfg, dest, secret, message, opener, allow_private, use_proxy, smtp)
        return {"channel": name, "ok": True, "reason": ""}
    except (OSError, urllib.error.URLError, ValueError, smtplib.SMTPException) as error:
        return {"channel": name, "ok": False, "reason": netguard.reason_of(error)}
