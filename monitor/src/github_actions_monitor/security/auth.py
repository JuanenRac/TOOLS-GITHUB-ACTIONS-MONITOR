# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Users, roles and sessions of the team mode: the rules, with no word about HTTP (security/auth_http.py puts them on the server).

OFF by default. Nothing changes for one person using the monitor alone: with `auth.enabled` off, or on while no user exists yet, every request is served as before (the individual mode).
The lite edition never has a login.

Roles, from the least to the most (each one can do what the ones before it can):

  viewer      reads: the page, the alerts, the events, the exports of the accounts it may see
  maintainer  also changes what only belongs to the monitor: silences, acknowledgements, the working mode, the groups
  admin       also changes the settings, the users and everything that can reach GitHub or the outside

Where things are kept (the `Storage` interface, global records): `users` (one per user name), `user_accounts` (the accounts a user may see; "*" = every account) and `sessions` (the
SHA-256 of the token of a session, with its expiry; the token itself is never stored). A password is never stored either: only a salted scrypt hash (PBKDF2-SHA256 where this build of
Python has no scrypt), with its parameters inside, so they can be raised later without locking anybody out.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.storage import base as storage_base

ROLES = ("viewer", "maintainer", "admin")
RANK = {role: index for index, role in enumerate(ROLES)}
ALL_ACCOUNTS = "*"
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,39}$")
TOKEN_PREFIX = "msn_"                       # a session token for a client that is not a browser; it can never be mistaken for the access token of the network mode
SESSION_COOKIE = "monitor_session"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
PBKDF2_ROUNDS = 600_000
MAX_PASSWORD_BYTES = 256
DEFAULTS = {"enabled": False, "session_hours": 12, "max_failed_logins": 5, "lockout_minutes": 15, "min_length": 10, "allow_bearer": True, "audit": True}
AUDIT_MAX_BYTES = 1_000_000
AUDIT_FILE = None                           # tests point this to a temporary file; None = auth_audit.jsonl in the product folder
_lock = threading.RLock()


# --- the settings -------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    """The `auth` section with the conservative default for anything missing or wrong (a real `true` is the only thing that turns a switch on)."""
    cfg = config.get("auth") if isinstance(config, dict) and isinstance(config.get("auth"), dict) else {}
    return {"enabled": cfg.get("enabled") is True,
            "session_hours": _int(cfg.get("session_hours"), 1, 720, DEFAULTS["session_hours"]),
            "max_failed_logins": _int(cfg.get("max_failed_logins"), 3, 20, DEFAULTS["max_failed_logins"]),
            "lockout_minutes": _int(cfg.get("lockout_minutes"), 1, 1440, DEFAULTS["lockout_minutes"]),
            "min_length": _int(cfg.get("min_length"), 8, 64, DEFAULTS["min_length"]),
            "allow_bearer": cfg.get("allow_bearer") is not False,
            "audit": cfg.get("audit") is not False}


# --- the passwords ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


def hash_password(password, salt=None):
    """`scrypt$N$r$p$salt$hash` (or `pbkdf2$rounds$salt$hash`), everything base64 but the numbers."""
    data = password.encode("utf-8")
    salt = salt or os.urandom(16)
    if hasattr(hashlib, "scrypt"):
        try:
            raw = hashlib.scrypt(data, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=64 * 1024 * 1024, dklen=32)
            return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(raw)}"
        except (ValueError, MemoryError):
            pass
    raw = hashlib.pbkdf2_hmac("sha256", data, salt, PBKDF2_ROUNDS, dklen=32)
    return f"pbkdf2${PBKDF2_ROUNDS}${_b64(salt)}${_b64(raw)}"


def verify_password(password, stored):
    """True when `password` is the one `stored` was made from. Constant-time; anything damaged is simply False."""
    try:
        data = password.encode("utf-8")
        parts = stored.split("$")
        if parts[0] == "scrypt" and len(parts) == 6:
            n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
            if not (2 ** 12 <= n <= 2 ** 20 and 1 <= r <= 16 and 1 <= p <= 4):
                return False
            raw = hashlib.scrypt(data, salt=base64.b64decode(parts[4]), n=n, r=r, p=p, maxmem=256 * 1024 * 1024, dklen=32)
            return hmac.compare_digest(raw, base64.b64decode(parts[5]))
        if parts[0] == "pbkdf2" and len(parts) == 4:
            rounds = int(parts[1])
            if not 100_000 <= rounds <= 5_000_000:
                return False
            raw = hashlib.pbkdf2_hmac("sha256", data, base64.b64decode(parts[2]), rounds, dklen=32)
            return hmac.compare_digest(raw, base64.b64decode(parts[3]))
    except (ValueError, TypeError, AttributeError, MemoryError):
        pass
    return False


_DUMMY = {}


def burn_time(password):
    """A wrong user name costs the same time as a wrong password, so the answer time does not tell whether the user exists."""
    if "hash" not in _DUMMY:
        _DUMMY["hash"] = hash_password("not-a-password")
    verify_password(password, _DUMMY["hash"])


def password_problem(password, username, minimum):
    """A short code (never the password) when the password is not acceptable, else ''."""
    if not isinstance(password, str) or not password:
        return "password_missing"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "password_too_long"
    if len(password) < minimum:
        return "password_short"
    if password.lower() == str(username).lower() or len(set(password)) < 4:
        return "password_weak"
    return ""


# --- the permissions of each route ---------------------------------------------------------------------------------------------------------------------------------------------------

#: POST routes a maintainer may use (they only change what belongs to the monitor); every other POST is for an admin, so a route added later is closed until someone lists it here on purpose
MAINTAINER_POST = ("/api/alerts/mute", "/api/alerts/unmute", "/api/ai/ack", "/api/hot-only", "/api/mode", "/api/refresh-repos", "/api/sentinel/parte/save", "/api/discovery/group", "/api/welcome",
                   "/api/session-token")
#: GET routes only an admin reads (they describe what is configured to reach the outside)
ADMIN_GET = ("/api/github-token", "/api/advanced", "/api/github-app/status", "/api/auth/users", "/api/auth/audit")
#: routes that never need a session: the login itself, the health check, the page shell, and the webhook and the network access, which have a proof of their own
PUBLIC = ("/api/auth/login", "/api/auth/me", "/api/auth/bootstrap", "/api/auth/logout", "/api/health", "/api/webhook", "/api/access", "/login")


def required_role(method, path):
    """The least role that may do `method` on `path`, or None when the route is public. Unknown writes need an admin."""
    path = path.split("?")[0]
    if path in PUBLIC:
        return None
    if method in ("GET", "HEAD"):
        return "admin" if path in ADMIN_GET else "viewer"
    if path in MAINTAINER_POST:
        return "maintainer"
    if path == "/api/auth/password":      # everybody changes their own password
        return "viewer"
    return "admin"


def allows(role, needed):
    return needed is None or (role in RANK and RANK[role] >= RANK[needed])


# --- the users and the sessions -----------------------------------------------------------------------------------------------------------------------------------------------------

_storage = {"obj": None}


def use_storage(storage):
    """Sets the storage the users live in (tests, and the first use of the server)."""
    _storage["obj"] = storage


def get_storage(config=None):
    if _storage["obj"] is None:
        from github_actions_monitor.storage import factory
        _storage["obj"] = factory.create_storage((config or {}).get("storage") if isinstance(config, dict) else None)
    return _storage["obj"]


def _now():
    return time.time()


def _stamp(now=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now or _now()))


def clean_username(value):
    text = value.strip().lower() if isinstance(value, str) else ""
    return text if USERNAME_RE.match(text) else ""


def users_exist(storage):
    return bool(storage.list_records("users"))


def public_user(name, record, accounts=None):
    """What may be shown of a user: never the hash."""
    return {"username": name, "role": record.get("role"), "active": record.get("active", True) is True, "created_at": record.get("created_at", ""),
            "accounts": accounts if accounts is not None else [ALL_ACCOUNTS]}


def accounts_of(storage, name, role):
    if role == "admin":
        return [ALL_ACCOUNTS]
    row = storage.get_record("user_accounts", name) or {}
    items = [a for a in (row.get("accounts") or []) if a == ALL_ACCOUNTS or (isinstance(a, str) and storage_base.ACCOUNT_RE.match(a))]
    return items or []


def can_see_account(accounts, account_id):
    return ALL_ACCOUNTS in accounts or account_id in accounts


def create_user(storage, username, password, role, accounts=None, minimum=10):
    """Creates a user. Returns (None, code) when it cannot, else (public user, ''). The name is unique."""
    name = clean_username(username)
    if not name:
        return None, "username_invalid"
    if role not in RANK:
        return None, "role_invalid"
    problem = password_problem(password, name, minimum)
    if problem:
        return None, problem
    clean = _clean_accounts(accounts, role)
    if clean is None:
        return None, "accounts_invalid"
    with _lock:
        if storage.get_record("users", name) is not None:
            return None, "user_exists"
        record = {"role": role, "hash": hash_password(password), "active": True, "created_at": _stamp(), "failed": 0, "locked_until": 0}
        storage.put_record("users", name, record)
        storage.put_record("user_accounts", name, {"accounts": clean})
    return public_user(name, record, clean), ""


def _clean_accounts(accounts, role):
    if role == "admin":
        return [ALL_ACCOUNTS]
    if accounts is None:
        return ["default"]      # conservative: a viewer or a maintainer sees the main account until an admin says otherwise
    if not isinstance(accounts, list) or len(accounts) > 100:
        return None
    out = []
    for item in accounts:
        if item != ALL_ACCOUNTS and not (isinstance(item, str) and storage_base.ACCOUNT_RE.match(item)):
            return None
        if item not in out:
            out.append(item)
    return out


def bootstrap_admin(storage, username, password, minimum=10):
    """The first administrator: only while no user exists (the check and the write happen under one lock, so two requests never make two). Returns (user, code)."""
    with _lock:
        if users_exist(storage):
            return None, "bootstrap_closed"
        return create_user(storage, username, password, "admin", None, minimum)


def active_admins(storage):
    return [n for n, r in storage.list_records("users").items() if r.get("role") == "admin" and r.get("active", True) is True]


def update_user(storage, username, role=None, active=None, accounts=None, password=None, minimum=10):
    """Changes a user. Never leaves the installation without an active admin. Returns (public user, code)."""
    name = clean_username(username)
    with _lock:
        record = storage.get_record("users", name) if name else None
        if record is None:
            return None, "user_unknown"
        new_role = record.get("role") if role is None else role
        if new_role not in RANK:
            return None, "role_invalid"
        new_active = record.get("active", True) is True if active is None else active
        if not isinstance(new_active, bool):
            return None, "active_invalid"
        was_admin = record.get("role") == "admin" and record.get("active", True) is True
        if was_admin and not (new_role == "admin" and new_active) and active_admins(storage) == [name]:
            return None, "last_admin"
        if password is not None:
            problem = password_problem(password, name, minimum)
            if problem:
                return None, problem
            record["hash"] = hash_password(password)
            record["failed"], record["locked_until"] = 0, 0
        clean = _clean_accounts(accounts, new_role)
        if clean is None:
            return None, "accounts_invalid"
        old_role = record.get("role")
        record["role"], record["active"] = new_role, new_active
        storage.put_record("users", name, record)
        storage.put_record("user_accounts", name, {"accounts": clean})
        if password is not None or not new_active or new_role != old_role:
            revoke_sessions(storage, name)      # a changed password, role or state ends the sessions that were opened before it
    return public_user(name, record, clean), ""


def delete_user(storage, username):
    name = clean_username(username)
    with _lock:
        record = storage.get_record("users", name) if name else None
        if record is None:
            return "user_unknown"
        if record.get("role") == "admin" and record.get("active", True) is True and active_admins(storage) == [name]:
            return "last_admin"
        storage.delete_record("users", name)
        storage.delete_record("user_accounts", name)
        revoke_sessions(storage, name)
    return ""


def list_users(storage):
    users = storage.list_records("users")
    return [public_user(n, r, accounts_of(storage, n, r.get("role"))) for n, r in sorted(users.items())]


def _session_key(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_sessions(storage, username):
    """Ends every session of a user. Returns how many."""
    count = 0
    for key, row in storage.list_records("sessions").items():
        if row.get("user") == username and storage.delete_record("sessions", key):
            count += 1
    return count


def login(storage, username, password, cfg, kind="cookie", now=None):
    """Checks a password. Returns (session info, code): on success ({"token", "csrf", "user", "role", "expires"}, ""); otherwise (None, "invalid_credentials" | "locked", retry seconds in `cfg["_retry"]` is not used:
    the second value of a lock is "locked" and `locked_for(...)` tells for how long). A wrong password counts against the USER (it locks after `max_failed_logins`) so that a guess spread over many addresses
    is stopped too; the address has its own limit in the server."""
    now = _now() if now is None else now
    name = clean_username(username)
    if not isinstance(password, str) or not password or len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        burn_time("x")
        return None, "invalid_credentials"
    with _lock:
        record = storage.get_record("users", name) if name else None
        if record is None or record.get("active", True) is not True:
            burn_time(password)
            return None, "invalid_credentials"
        if record.get("locked_until", 0) > now:
            return None, "locked"
        if not verify_password(password, record.get("hash", "")):
            record["failed"] = int(record.get("failed", 0)) + 1
            if record["failed"] >= cfg["max_failed_logins"]:
                record["locked_until"], record["failed"] = now + cfg["lockout_minutes"] * 60, 0
                storage.put_record("users", name, record)
                return None, "locked"
            storage.put_record("users", name, record)
            return None, "invalid_credentials"
        if record.get("failed") or record.get("locked_until"):
            record["failed"], record["locked_until"] = 0, 0
            storage.put_record("users", name, record)
        storage.purge_records("sessions", now)
        token = (TOKEN_PREFIX if kind == "bearer" else "") + secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        expires = now + cfg["session_hours"] * 3600
        storage.put_record("sessions", _session_key(token), {"user": name, "csrf": csrf, "kind": kind, "created": _stamp(now), "expires": expires}, expires=expires)
    return {"token": token, "csrf": csrf, "user": name, "role": record.get("role"), "expires": expires}, ""


def locked_for(storage, username, now=None):
    record = storage.get_record("users", clean_username(username)) or {}
    return max(0, int(record.get("locked_until", 0) - (_now() if now is None else now)))


def find_session(storage, token, now=None):
    """The context of a valid token: {"user", "role", "accounts", "csrf", "kind"} or None (unknown, expired, the user is gone or inactive)."""
    now = _now() if now is None else now
    if not isinstance(token, str) or not 16 <= len(token) <= 200:
        return None
    row = storage.get_record("sessions", _session_key(token))
    if not row or not isinstance(row.get("expires"), (int, float)) or row["expires"] <= now:
        return None
    record = storage.get_record("users", row.get("user", ""))
    if not record or record.get("active", True) is not True:
        return None
    role = record.get("role")
    return {"user": row["user"], "role": role, "accounts": accounts_of(storage, row["user"], role), "csrf": row.get("csrf", ""), "kind": row.get("kind", "cookie")}


def end_session(storage, token):
    if isinstance(token, str) and token:
        return storage.delete_record("sessions", _session_key(token))
    return False


def change_own_password(storage, username, current, new, cfg, keep_token=None):
    """A person changes their own password: the old one is checked first, and every other session of theirs ends."""
    name = clean_username(username)
    with _lock:
        record = storage.get_record("users", name)
        if record is None or not verify_password(current if isinstance(current, str) else "", record.get("hash", "")):
            return "invalid_credentials"
        problem = password_problem(new, name, cfg["min_length"])
        if problem:
            return problem
        record["hash"] = hash_password(new)
        storage.put_record("users", name, record)
        keep = _session_key(keep_token) if keep_token else None
        for key, row in storage.list_records("sessions").items():
            if row.get("user") == name and key != keep:
                storage.delete_record("sessions", key)
    return ""


# --- the audit of the accesses ------------------------------------------------------------------------------------------------------------------------------------------------------

def audit_path():
    if AUDIT_FILE is not None:
        return Path(AUDIT_FILE)
    from github_actions_monitor.util import paths
    chosen = os.environ.get("MONITOR_STATE_DIR", "").strip()      # a service keeps it in the volume of its data, apart from the code
    return (Path(chosen) if chosen else paths.folder("logs")) / "auth_audit.jsonl"


def audit(cfg, action, user="", role="", address="", path="", result="ok", code=""):
    """One line per event: a login (good or bad), a lock, a logout, a refused request, a change of users. Never a password, a token or a hash. The file is private (0600) and, past a megabyte,
    the old part is kept as `.1` (one generation), so it never grows without a limit."""
    if not cfg.get("audit", True):
        return
    entry = {"at": _stamp(), "action": str(action)[:40], "user": str(user)[:40], "role": str(role)[:12], "address": str(address)[:64], "path": str(path).split("?")[0][:120], "result": result, "code": str(code)[:40]}
    target = audit_path()
    try:
        with _lock:
            if target.exists() and target.stat().st_size > AUDIT_MAX_BYTES:
                os.replace(target, target.with_name(target.name + ".1"))
            private_io.private_dir(target.parent)
            with private_io.open_append(target) as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass      # the audit never stops a request


def read_audit(limit=200):
    """The last `limit` lines of the audit, newest last."""
    target = audit_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out
