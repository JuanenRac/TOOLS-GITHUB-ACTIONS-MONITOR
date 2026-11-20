# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Paired devices: a phone or a tablet joins the monitor in the network mode with a ONE-USE code (shown as a QR code on this computer) and gets a token of its own, so it never learns the access
token of the monitor and can be taken away alone.

  start(cfg, now)               a one-use code that lives `pairing.code_minutes` minutes; the new code replaces the previous one (only one is open at a time)
  redeem(cfg, code, name, now)  the code is spent whatever the answer; on success a device token `dev_...` is made, only its SHA-256 is kept (data folder, devices.json, mode 0600)
  valid(token, cfg, now)        True for the token of a device that is not revoked and not older than `pairing.device_days` (0 = it does not expire); marks the last use at most once a minute
  list_devices() / revoke(id)   what the page shows and the way a device is taken away (its token stops working at once)

Everything is opt-in (`pairing.enabled`, off by default) and refuses without the network mode. The file never holds a token, an address or a name typed by the visitor beyond a short label made from the
browser (kind of device), and the order of the keys is stable. Standard library only."""
import hashlib
import hmac
import json
import re
import secrets
import threading
import time

from github_actions_monitor.storage import file_storage
from github_actions_monitor.util import paths

FILE = "devices.json"
TOKEN_PREFIX = "dev_"
DEFAULTS = {"enabled": False, "code_minutes": 5, "max_devices": 10, "device_days": 90}
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # nothing that looks like another character
CODE_LENGTH = 12
NAME_RE = re.compile(r"[^A-Za-z0-9 ._()/+-]")
_LOCK = threading.RLock()
_OPEN = {"hash": "", "until": 0.0}      # the open code: the SHA-256 of the code and the moment it stops working (kept only in memory)
_TOUCH = {}      # device id -> the moment of the last write of its "last_seen"


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(raw):
    block = (raw or {}).get("pairing") if isinstance(raw, dict) else None
    block = block if isinstance(block, dict) else {}
    return {"enabled": block.get("enabled") is True, "code_minutes": _int(block.get("code_minutes"), 1, 30, DEFAULTS["code_minutes"]),
            "max_devices": _int(block.get("max_devices"), 1, 50, DEFAULTS["max_devices"]), "device_days": _int(block.get("device_days"), 0, 365, DEFAULTS["device_days"])}


def _path():
    return paths.place(FILE)


def _read():
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"devices": []}
    rows = data.get("devices") if isinstance(data, dict) else None
    return {"devices": [r for r in rows if isinstance(r, dict) and isinstance(r.get("hash"), str)] if isinstance(rows, list) else []}


def _write(data):
    file_storage.atomic_write(_path(), json.dumps(data, indent=1, sort_keys=True) + "\n")


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def label_from(user_agent):
    """A short, harmless name of the kind of device from the browser: "Android phone", "iPhone", "Windows computer"... never the full text of the browser."""
    agent = str(user_agent or "")
    for needle, name in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android device"), ("Windows", "Windows computer"), ("Macintosh", "Mac"), ("Linux", "Linux computer")):
        if needle in agent:
            return name
    return "Device"


def start(cfg, now=None):
    """Opens a code. Returns {"code", "expires_in"}; the code is shown once and only its hash stays in memory."""
    now = time.time() if now is None else now
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    with _LOCK:
        _OPEN["hash"], _OPEN["until"] = _hash(code), now + cfg["code_minutes"] * 60
    return {"code": code, "expires_in": cfg["code_minutes"] * 60}


def is_open(now=None):
    now = time.time() if now is None else now
    with _LOCK:
        return bool(_OPEN["hash"]) and now < _OPEN["until"]


def close():
    with _LOCK:
        _OPEN["hash"], _OPEN["until"] = "", 0.0


def redeem(cfg, code, user_agent="", now=None):
    """Spends the open code. Returns (token, device) or (None, reason) with reason in: closed, wrong, full. A wrong code does not spend the open one (a stranger must not be able to cancel a pairing by
    guessing), but the caller counts it against the address (localguard.note_failure) so the guesses stop."""
    now = time.time() if now is None else now
    code = str(code or "").strip().upper()
    with _LOCK:
        if not _OPEN["hash"] or now >= _OPEN["until"]:
            close()
            return None, "closed"
        if not re.fullmatch(r"[A-Z0-9]{%d}" % CODE_LENGTH, code) or not hmac.compare_digest(_hash(code), _OPEN["hash"]):
            return None, "wrong"
        close()      # one use: the code is gone whatever happens next
        data = _read()
        if len(data["devices"]) >= cfg["max_devices"]:
            return None, "full"
        token = TOKEN_PREFIX + secrets.token_urlsafe(32)
        device = {"id": _hash(token)[:10], "hash": _hash(token), "name": NAME_RE.sub("", label_from(user_agent))[:40], "created": int(now), "last_seen": int(now)}
        data["devices"].append(device)
        _write(data)
        return token, public(device)


def public(device, now=None):
    """What the page may see of a device: never the hash."""
    return {"id": device.get("id", ""), "name": device.get("name", ""), "created": device.get("created", 0), "last_seen": device.get("last_seen", 0)}


def list_devices():
    return [public(d) for d in sorted(_read()["devices"], key=lambda d: d.get("created", 0), reverse=True)]


def revoke(device_id):
    """True when a device with that id existed and is gone."""
    with _LOCK:
        data = _read()
        keep = [d for d in data["devices"] if d.get("id") != str(device_id)]
        if len(keep) == len(data["devices"]):
            return False
        _write({"devices": keep})
        return True


def valid(token, cfg=None, now=None):
    """True when `token` is the token of a device that is still allowed. Never raises."""
    if not isinstance(token, str) or not token.startswith(TOKEN_PREFIX) or len(token) > 120:
        return False
    now = time.time() if now is None else now
    wanted = _hash(token)
    try:
        with _LOCK:
            data = _read()
            for device in data["devices"]:
                if hmac.compare_digest(device["hash"], wanted):
                    days = (cfg or DEFAULTS)["device_days"]
                    if days and now - device.get("created", 0) > days * 86400:
                        return False
                    if now - _TOUCH.get(device["id"], 0) > 60:      # the last use is written at most once a minute: a page that asks every few seconds must not rewrite a file each time
                        _TOUCH[device["id"]] = now
                        device["last_seen"] = int(now)
                        _write(data)
                    return True
    except OSError:
        return False
    return False
