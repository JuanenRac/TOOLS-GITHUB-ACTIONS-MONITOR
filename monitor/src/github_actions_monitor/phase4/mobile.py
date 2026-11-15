# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The server side of the native app (read only to begin with): what the app is told, never what it must compute.

  views          the app's screens are the same `?view=` of the phone web app: now, alerts, live (and score/health where they exist); each one is a list of reads of the API v1
  push           the server decides which alerts are critical enough, once each, outside quiet hours, and sends a MINIMAL message (an id, a level, a short cleaned title and the view to open);
                 the app does not recompute rules and the message holds no repository secret, no log and no token
  device tokens  registered by the app with its Bearer token; the registry keeps them private and never logs them
  deep links     `ghamon://proposal/<id>?hash=<hex>` for the full edition: it only OPENS the proposal on the device, where a person confirms; a link never approves or executes by itself

The sender is given by the caller (`send(message) -> bool`); nothing here uses the network, a clock or a file."""
import hashlib
import re

from github_actions_monitor.phase4 import pwa
from github_actions_monitor.phase4.assistant import redact_text

LEVELS = ("info", "warning", "error", "critical")
DEVICE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_:.-]{20,4096}\Z")
PLATFORMS = ("android", "ios")
DEEP_LINK_RE = re.compile(r"^ghamon://proposal/([a-z0-9]{3,32})\?hash=([0-9a-f]{64})\Z")
PUSH_DEFAULTS = {"enabled": False, "min_level": "critical", "quiet_hours": "", "max_per_device_per_hour": 6, "dedupe_seconds": 3600, "include_title": True}
SCREENS = dict(pwa.VIEW_ENDPOINTS, score=["/api/v1/score"], health=["/api/v1/team/health"])


def screens(available=("now", "alerts", "live")):
    """The reads each screen of the app makes (a screen whose endpoint does not exist on this server is left out by the caller through `available`)."""
    return {name: list(SCREENS[name]) for name in available if name in SCREENS}


def push_settings(raw):
    out = dict(PUSH_DEFAULTS)
    raw = raw if isinstance(raw, dict) else {}
    if isinstance(raw.get("enabled"), bool):
        out["enabled"] = raw["enabled"]
    if raw.get("min_level") in LEVELS:
        out["min_level"] = raw["min_level"]
    if isinstance(raw.get("include_title"), bool):
        out["include_title"] = raw["include_title"]
    if isinstance(raw.get("quiet_hours"), str) and (raw["quiet_hours"] == "" or re.match(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d\Z", raw["quiet_hours"])):
        out["quiet_hours"] = raw["quiet_hours"]
    for key, low, high in (("max_per_device_per_hour", 1, 120), ("dedupe_seconds", 60, 86400 * 7)):
        if isinstance(raw.get(key), int) and not isinstance(raw.get(key), bool) and low <= raw[key] <= high:
            out[key] = raw[key]
    return out


class DeviceRegistry:
    """Device tokens by user. The token is kept as given (the push service needs it) but is only ever shown as a short fingerprint."""

    def __init__(self):
        self._devices = {}          # fingerprint -> {"token", "user", "platform"}

    @staticmethod
    def fingerprint(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]

    def register(self, user, token, platform):
        if not isinstance(token, str) or not DEVICE_TOKEN_RE.match(token) or platform not in PLATFORMS or not isinstance(user, str) or not user:
            return None
        fp = self.fingerprint(token)
        self._devices[fp] = {"token": token, "user": user, "platform": platform}
        return fp

    def unregister(self, user, fp):
        device = self._devices.get(fp)
        if device and device["user"] == user:
            del self._devices[fp]
            return True
        return False

    def for_users(self, users=None):
        return [(fp, dict(d)) for fp, d in sorted(self._devices.items()) if users is None or d["user"] in users]

    def listing(self, user):
        return [{"id": fp, "platform": d["platform"]} for fp, d in sorted(self._devices.items()) if d["user"] == user]


class PushPlanner:
    def __init__(self, settings, registry, send):
        self.settings, self.registry, self.send = push_settings(settings), registry, send
        self._sent_alert = {}              # alert id -> when
        self._per_device = {}              # fingerprint -> list of times

    def _quiet(self, now):
        from github_actions_monitor.phase4.proposals import in_window
        hours = self.settings["quiet_hours"]
        return bool(hours) and in_window(hours, now)

    def message(self, alert):
        """The minimal payload of one alert (what the phone gets and nothing more)."""
        data = {"alert_id": str(alert.get("id", ""))[:120], "level": alert.get("level"), "code": str(alert.get("code", ""))[:60], "view": "alerts"}
        if self.settings["include_title"]:
            data["title"] = redact_text(str(alert.get("title", "")))[:100]
        return data

    def notify(self, alerts, now, users=None, accounts_of=None):
        """Sends each new alert at or above `min_level` to the devices of `users` (all when None) that may see its account. Returns the number of messages sent."""
        s = self.settings
        if not s["enabled"] or self._quiet(now):
            return 0
        floor = LEVELS.index(s["min_level"])
        sent = 0
        for alert in alerts:
            level = alert.get("level")
            if level not in LEVELS or LEVELS.index(level) < floor:
                continue
            key = str(alert.get("id", ""))
            if not key or now - self._sent_alert.get(key, -10 ** 12) < s["dedupe_seconds"]:
                continue
            delivered = False
            for fp, device in self.registry.for_users(users):
                if accounts_of is not None and alert.get("account_id") not in (accounts_of.get(device["user"]) or []):
                    continue          # a device only hears about the accounts its user may see
                times = [t for t in self._per_device.get(fp, []) if now - t < 3600]
                if len(times) >= s["max_per_device_per_hour"]:
                    self._per_device[fp] = times
                    continue
                if self.send(dict(self.message(alert), device=device["token"], platform=device["platform"])):
                    times.append(now)
                    sent += 1
                    delivered = True
                self._per_device[fp] = times
            if delivered:
                self._sent_alert[key] = now
        return sent


def deep_link(proposal_id, content_hash):
    return "ghamon://proposal/{}?hash={}".format(proposal_id, content_hash)


def parse_deep_link(url):
    """(proposal_id, hash) or None. The link only names what to open; the app shows it and asks for confirmation (with biometrics when the person enabled it) before any call."""
    match = DEEP_LINK_RE.match(str(url or ""))
    return (match.group(1), match.group(2)) if match else None
