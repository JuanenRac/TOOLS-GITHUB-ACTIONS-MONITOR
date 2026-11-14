# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Notifications for each user of the team mode (OFF by default: `notify.users.enabled`).

Each user keeps preferences of their own in their record: the channels they want (ntfy, Teams, e-mail), which sentinels (`ci`, `collab`), the lowest level they care about (`info`, `warn`,
`bad`), whether they want the events of the system itself (a lost connection, the allowance, a revoked login) and whether the messages come at once or gathered in a digest (`hourly`, `daily`).
The dispatcher decides WHO is told about an event with the preferences and the role:

  viewer       the events of CI (a red, a stuck build, a failed workflow, the collaborators) of the accounts the user may see
  maintainer   also what waits for a person to act: a build waiting for its signature, a release that is due
  admin        also the events of the system, all accounts

An event of an account is never sent to someone who may not see that account. A user caps at `notify.users.max_per_hour` messages an hour. A digest gathers the alerts the user has not seen yet
(opening the page, or POST /api/auth/me/notify/seen, marks them as seen and they are not sent again). The web address of a Teams channel and the token of a ntfy topic are kept in
security/channel_secrets.py, encrypted by the system, and never come back in any answer.
"""
import threading
import time

from github_actions_monitor.integrations import channels
from github_actions_monitor.security import auth, channel_secrets
from github_actions_monitor.storage import base as storage_base
from github_actions_monitor.storage import locks
from github_actions_monitor.util import paths

LEVELS = ("ok", "info", "warn", "bad")
MIN_LEVELS = ("info", "warn", "bad")
RANK = {"ok": 0, "info": 1, "warn": 2, "bad": 3, "critical": 3}
DIGESTS = ("off", "hourly", "daily")
DIGEST_SECONDS = {"hourly": 3600, "daily": 86400}
SENTINELS = ("ci", "collab")
FAMILIES = {"ci": ("red_new", "red_fixed", "stuck_new", "workflow_failed", "alerts_up", "ai_alert", "collab_new", "collab_fixed"),
            "release": ("pending_sign", "release_due"),
            "system": ("offline", "online", "rate_low", "credential_blind", "credential_back", "quota_warn", "quota_over", "quota_alert")}
ROLE_FAMILIES = {"viewer": ("ci",), "maintainer": ("ci", "release"), "admin": ("ci", "release", "system")}
DEFAULTS = {"users": {"enabled": False, "max_per_hour": 10}, "digest": {"max_items": 50}}
DOC = "notify_digest"
LOCK_WAIT = 10.0
_lock = threading.Lock()
ACCOUNT = {"id": ""}      # set by accounts/account_child.py: the account this process is the monitor of ("" = the single account, called "default")
_sent = {}            # user -> timestamps of the messages that left (for max_per_hour)
STATS = {"sent": 0, "failed": 0, "limited": 0, "queued": 0, "digests": 0}


def settings(config):
    """`notify.users` and `notify.digest` of the configuration; a real `true` is the only thing that turns it on."""
    notify = (config or {}).get("notify") if isinstance((config or {}).get("notify"), dict) else {}
    users = notify.get("users") if isinstance(notify.get("users"), dict) else {}
    digest = notify.get("digest") if isinstance(notify.get("digest"), dict) else {}

    def number(value, low, high, default):
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default
    return {"enabled": users.get("enabled") is True,
            "max_per_hour": number(users.get("max_per_hour"), 1, 600, DEFAULTS["users"]["max_per_hour"]),
            "max_items": number(digest.get("max_items"), 5, 200, DEFAULTS["digest"]["max_items"])}


def family_of(kind):
    for family, kinds in FAMILIES.items():
        if kind in kinds or (family == "system" and str(kind).startswith("quota_")):
            return family
    return ""


def sentinel_of(kind):
    return "collab" if str(kind).startswith("collab_") else "ci"


def secret_name(user, channel):
    return f"user.{user}.{channel}"


# --- the preferences of a user ------------------------------------------------------------------------------------------------------------------------------------------------------

def default_prefs(role="viewer"):
    return {"enabled": False, "channels": [], "sentinels": list(SENTINELS), "min_level": "warn", "system": role == "admin", "digest": "off", "destinations": {}}


def clean_prefs(raw, role="viewer"):
    """The preferences with the conservative value for anything missing or wrong (nothing is sent until the user turns it on and sets a destination)."""
    out = default_prefs(role)
    if not isinstance(raw, dict):
        return out
    out["enabled"] = raw.get("enabled") is True
    if isinstance(raw.get("channels"), list):
        out["channels"] = [c for c in channels.NAMES if c in raw["channels"]]
    if isinstance(raw.get("sentinels"), list):
        out["sentinels"] = [s for s in SENTINELS if s in raw["sentinels"]]
    if raw.get("min_level") in MIN_LEVELS:
        out["min_level"] = raw["min_level"]
    if isinstance(raw.get("system"), bool):
        out["system"] = raw["system"]
    if raw.get("digest") in DIGESTS:
        out["digest"] = raw["digest"]
    dests = raw.get("destinations") if isinstance(raw.get("destinations"), dict) else {}
    for name, plugin in channels.PLUGINS.items():
        item = dests.get(name)
        if isinstance(item, dict):
            kept = {k: item[k] for k in plugin.fields if isinstance(item.get(k), str)}
            if kept:
                out["destinations"][name] = kept
    return out


def get_prefs(storage, user, secrets_known=True):
    """The preferences of a user for the page: with which channels have a secret stored (a yes or a no), never the secret."""
    record = storage.get_record("users", user) or {}
    prefs = clean_prefs(record.get("notify"), record.get("role", "viewer"))
    if secrets_known:
        prefs["secrets"] = {n: channel_secrets.has(secret_name(user, n)) for n, p in channels.PLUGINS.items() if p.secret}
    prefs["role"] = record.get("role", "viewer")
    prefs["families"] = list(ROLE_FAMILIES.get(prefs["role"], ("ci",)))
    return prefs


def set_prefs(storage, user, body):
    """Saves the preferences a user sends. Returns (prefs, "") or (None, code). A secret goes to channel_secrets (an empty text removes it); everything else to the record of the user."""
    if not isinstance(body, dict):
        return None, "body_invalid"
    with auth._lock:
        record = storage.get_record("users", user)
        if record is None:
            return None, "user_unknown"
        role = record.get("role", "viewer")
        merged = clean_prefs({**clean_prefs(record.get("notify"), role), **{k: v for k, v in body.items() if k != "secrets"}}, role)
        for key, allowed in (("channels", channels.NAMES), ("sentinels", SENTINELS)):
            if isinstance(body.get(key), list) and any(item not in allowed for item in body[key]):
                return None, key + "_invalid"
        for key, allowed in (("min_level", MIN_LEVELS), ("digest", DIGESTS)):
            if key in body and body[key] not in allowed:
                return None, key + "_invalid"
        secrets = body.get("secrets") if isinstance(body.get("secrets"), dict) else {}
        for name, value in secrets.items():
            plugin = channels.PLUGINS.get(name)
            if plugin is None or not plugin.secret or not isinstance(value, str):
                return None, "secret_invalid"
            if value.strip() and (not channel_secrets.valid_value(value) or (plugin.secret_required and plugin.check_destination({}, value.strip()) is not None)):
                return None, "secret_invalid"
        for name in merged["channels"]:
            plugin = channels.PLUGINS[name]
            if plugin.secret_required:
                given = str(secrets.get(name) or "").strip()
                if not given and not channel_secrets.has(secret_name(user, name)):
                    return None, "secret_missing"
            elif plugin.check_destination(merged["destinations"].get(name, {})) is not None:
                return None, "destination_invalid"
        for name, value in secrets.items():
            if value.strip():
                ok, _why = channel_secrets.put(secret_name(user, name), value)
                if not ok:
                    return None, "secret_not_saved"
            else:
                channel_secrets.delete(secret_name(user, name))
        record["notify"] = merged
        storage.put_record("users", user, record)
    return get_prefs(storage, user), ""


def forget_user(user):
    """The user is gone: so are the secrets of their channels."""
    for name in channels.NAMES:
        channel_secrets.delete(secret_name(user, name))


# --- who is told ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

def wants(prefs, role, accounts, event, account_id):
    """True when this user, with these preferences and this role, is told about this event of this account."""
    family = family_of(event.get("kind"))
    if not family or not prefs["enabled"] or not prefs["channels"]:
        return False
    if family not in ROLE_FAMILIES.get(role, ("ci",)):
        return False
    if RANK.get(event.get("level", "info"), 1) < RANK[prefs["min_level"]]:
        return False
    if family == "system":
        return prefs["system"]
    return sentinel_of(event.get("kind")) in prefs["sentinels"] and auth.can_see_account(accounts, account_id)


def recipients(storage, event, account_id):
    """[(user, role, prefs)] of the users who are told about the event."""
    out = []
    for name, record in sorted(storage.list_records("users").items()):
        if record.get("active") is False:
            continue
        role = record.get("role", "viewer")
        prefs = clean_prefs(record.get("notify"), role)
        if wants(prefs, role, auth.accounts_of(storage, name, role), event, account_id):
            out.append((name, role, prefs))
    return out


def _reserve(user, limit, now=None):
    now = time.time() if now is None else now
    with _lock:
        stamps = [t for t in _sent.get(user, []) if t > now - 3600]
        ok = len(stamps) < limit
        if ok:
            stamps.append(now)
        _sent[user] = stamps
        return ok


def message_of(event):
    return {"title": str(event.get("repo") or "Monitor"), "text": str(event.get("text") or ""), "url": event.get("url"), "level": event.get("level", "info"), "repo": event.get("repo", "")}


def _send(user, prefs, message, server, allow_private, use_proxy, opener=None, smtp=None):
    results = []
    for name in prefs["channels"]:
        plugin = channels.PLUGINS[name]
        secret = channel_secrets.get(secret_name(user, name)) if plugin.secret else ""
        results.append(channels.deliver(name, server[name], prefs["destinations"].get(name, {}), secret, message, opener, allow_private, use_proxy, smtp))
    return results


def _count(results, limited=0):
    with _lock:
        STATS["sent"] += sum(1 for r in results if r["ok"])
        STATS["failed"] += sum(1 for r in results if not r["ok"])
        STATS["limited"] += limited


def dispatch(config, event, storage=None, account_id=None, opener=None, smtp=None, now=None):
    """Tells every user who wants this event (at once, or into their digest). Returns {user: [results]} for the messages sent at once. Never raises."""
    cfg = settings(config)
    if not cfg["enabled"] or event.get("owner", "main") != "main":
        return {}
    account_id = account_id or ACCOUNT["id"] or "default"
    try:
        storage = storage or auth.get_storage(config)
        found = recipients(storage, event, account_id)
        notify = (config or {}).get("notify") if isinstance((config or {}).get("notify"), dict) else {}
        allow = notify.get("allow_private_targets") is True
        proxy = ((config or {}).get("network") or {}).get("use_proxy") is True if isinstance((config or {}).get("network"), dict) else False
        server = channels.server_settings(config)
        answers = {}
        for user, _role, prefs in found:
            if prefs["digest"] != "off":
                queue(storage, account_id, user, event, cfg["max_items"], now)
                continue
            if not _reserve(user, cfg["max_per_hour"], now):
                _count([], 1)
                continue
            answers[user] = _send(user, prefs, message_of(event), server, allow, proxy, opener, smtp)
            _count(answers[user])
        return answers
    except Exception:       # noqa: BLE001 - a notification never stops the monitor
        with _lock:
            STATS["failed"] += 1
        return {}


# --- the digest ----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _lock_path(account_id):
    return paths.folder("data") / (DOC + "_" + account_id)


def queue(storage, account_id, user, event, max_items, now=None):
    """Puts an event in the digest of a user (the oldest are dropped past `max_items`)."""
    now = time.time() if now is None else now
    item = {"at": int(now), "kind": event.get("kind"), "level": event.get("level", "info"), "repo": event.get("repo", ""), "text": str(event.get("text") or "")[:300], "url": event.get("url")}
    with locks.process_lock(_lock_path(account_id), LOCK_WAIT):
        doc = storage.load_doc(account_id, DOC, {}) or {}
        mine = doc.setdefault("items", {}).setdefault(user, [])
        mine.append(item)
        del mine[:-max_items]
        storage.save_doc(account_id, DOC, doc)
    with _lock:
        STATS["queued"] += 1


def pending(storage, account_id, user):
    return list(((storage.load_doc(account_id, DOC, {}) or {}).get("items") or {}).get(user, []))


def mark_seen(storage, user, account_ids=None):
    """The user has seen their alerts: what waits in their digests is dropped. Returns how many items were dropped."""
    dropped = 0
    for account_id in (account_ids if account_ids is not None else storage.list_accounts()):
        storage_base.check_account(account_id)
        with locks.process_lock(_lock_path(account_id), LOCK_WAIT):
            doc = storage.load_doc(account_id, DOC, {}) or {}
            mine = (doc.get("items") or {}).get(user) or []
            if mine:
                dropped += len(mine)
                doc["items"][user] = []
                storage.save_doc(account_id, DOC, doc)
    return dropped


def digest_message(items, language_title):
    lines = [f"[{i['level']}] {i['repo'] or '-'}: {i['text']}" for i in items[-30:]]
    first = next((i["url"] for i in reversed(items) if i.get("url")), None)
    worst = max((RANK.get(i["level"], 1) for i in items), default=1)
    return {"title": language_title.format(n=len(items)), "text": "\n".join(lines)[:1500], "url": first, "level": next((k for k, v in RANK.items() if v == worst and k != "critical"), "info"), "repo": ""}


def run_digests(config, storage=None, account_id=None, title="{n} alerts you have not seen", opener=None, smtp=None, now=None):
    """Sends the digest of every user whose time has come and who has alerts they have not seen. Returns {user: [results]}. Never raises."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return {}
    now = time.time() if now is None else now
    account_id = account_id or ACCOUNT["id"] or "default"
    answers = {}
    try:
        storage = storage or auth.get_storage(config)
        notify = (config or {}).get("notify") if isinstance((config or {}).get("notify"), dict) else {}
        allow = notify.get("allow_private_targets") is True
        proxy = ((config or {}).get("network") or {}).get("use_proxy") is True if isinstance((config or {}).get("network"), dict) else False
        server = channels.server_settings(config)
        with locks.process_lock(_lock_path(account_id), LOCK_WAIT):
            doc = storage.load_doc(account_id, DOC, {}) or {}
            due = []
            for user, items in sorted((doc.get("items") or {}).items()):
                record = storage.get_record("users", user) or {}
                prefs = clean_prefs(record.get("notify"), record.get("role", "viewer"))
                last = (doc.get("last") or {}).get(user, 0)
                if items and prefs["enabled"] and prefs["digest"] != "off" and record.get("active") is not False and now - last >= DIGEST_SECONDS[prefs["digest"]]:
                    due.append((user, prefs, list(items)))
            for user, prefs, items in due:      # the items leave the queue before the send: a crash in between loses one digest, it never sends one twice
                doc["items"][user] = []
                doc.setdefault("last", {})[user] = int(now)
            if due:
                storage.save_doc(account_id, DOC, doc)
        for user, prefs, items in due:
            answers[user] = _send(user, prefs, digest_message(items, title), server, allow, proxy, opener, smtp)
            _count(answers[user])
            with _lock:
                STATS["digests"] += 1
    except Exception:       # noqa: BLE001
        with _lock:
            STATS["failed"] += 1
    return answers
