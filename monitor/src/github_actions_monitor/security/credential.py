# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The login of GitHub of ONE account: when GitHub revokes it or lets it expire, and how to put another one in its place without restarting anything.

Every account of the complete edition is a process of its own, so everything here is per account by construction: the state below belongs to the process that read the refusal, and the
other accounts never hear of it.

  * A refusal that says the credential itself is no good (a 401, "Bad credentials", an expired or revoked token, a suspended account) counts. After `CONFIRM` of them in a row, with no good
    cycle in between, the account is BLIND: the page, the health check, the summary of the accounts and the Alerts tab say so, a critical system alert opens and the notification channels are told
    once. A refusal of one single permission (a 403 for one repository) does not make an account blind: it is a gap in the permissions, not a lost login.
  * The first good cycle ends it (the alert closes by itself and one notice says the account is back).
  * The credential can be replaced while everything runs: `replace()` checks the new token against GitHub BEFORE it keeps it (a token GitHub refuses changes nothing), then stores it in a file
    of the folder of the account (mode 600) and uses it from the next call. The same file, or the file named by `GH_TOKEN_FILE`, is read again on `reload()` (the administrator endpoint and the
    signal SIGHUP of the supervisor do it), so a secret rotated by the platform needs no restart either.

Where the token of an account comes from, first match wins: `credential` in the folder of the account (written by `replace`), the file named by `GH_TOKEN_FILE`, then what `gh` already uses (the
variable GH_TOKEN or its own login). The token is never written to the configuration, a log, an answer or the page, and every text that may carry it goes through `redact()`.
"""
import os
import threading
import time
from pathlib import Path

from github_actions_monitor.security import private_io, secretstore

FILE_NAME = "credential"
CONFIRM = 2                     # refusals in a row before the account is blind (one stray 401 is not a lost login)
REASONS = ("expired", "revoked", "missing")
LOCK = threading.RLock()
STATE = {"state": "ok", "reason": "", "since": 0.0, "strikes": 0, "last_error": "", "replaced_at": 0.0, "source": ""}

#: texts of a refusal that mean "this login is no good" (as opposed to "this login lacks one permission")
_DEAD = ("401", "bad credentials", "token expired", "expired token", "token has expired", "has expired", "token revoked", "revoked", "requires authentication", "account has been suspended",
         "has been suspended", "not logged in", "invalid token", "authentication failed", "gh auth login", "gh_token environment")


def reset():
    with LOCK:
        STATE.update({"state": "ok", "reason": "", "since": 0.0, "strikes": 0, "last_error": "", "replaced_at": 0.0, "source": ""})


def redact(text):
    return secretstore.redact(text)


def is_dead_login(message):
    """True when a refusal of GitHub says the login itself is no good (and not just that it lacks a permission)."""
    text = str(message or "").lower()
    return any(mark in text for mark in _DEAD)


def classify(message):
    """'expired' when the refusal says the token ran out, 'missing' when there is no login at all (`gh` asks to log in), else 'revoked' (GitHub answers the same "Bad credentials" for a token it
    revoked and for one that no longer exists)."""
    text = str(message or "").lower()
    if "gh auth login" in text or "gh_token environment" in text or "not logged in" in text:
        return "missing"
    return "expired" if "expired" in text else "revoked"


def note_refusal(message, now=None):
    """One cycle ended with a refusal of the login. Returns 'blind' on the refusal that makes the account blind (the caller raises the alert once), 'strike' while it is counting, '' for a refusal that is
    not about the login itself."""
    if not is_dead_login(message):
        return ""
    now = time.time() if now is None else now
    with LOCK:
        STATE["last_error"] = redact(message)[:160]
        if STATE["state"] == "blind":
            return ""
        STATE["strikes"] += 1
        if STATE["strikes"] < CONFIRM:
            return "strike"
        STATE.update({"state": "blind", "reason": classify(message), "since": now})
        return "blind"


def mark_blind(message, now=None):
    """The account is blind from the start (the check of the login at start failed with a refusal): True when this is news, False when the refusal is not about the login itself."""
    if not is_dead_login(message):
        return False
    now = time.time() if now is None else now
    with LOCK:
        STATE.update({"state": "blind", "reason": classify(message), "since": now, "strikes": CONFIRM, "last_error": redact(message)[:160]})
    return True


def note_success(now=None):
    """A cycle ended well. Returns 'back' when that closes a blind period, else ''."""
    with LOCK:
        was = STATE["state"] == "blind"
        STATE.update({"state": "ok", "reason": "", "since": 0.0, "strikes": 0, "last_error": ""})
        return "back" if was else ""


def is_blind():
    with LOCK:
        return STATE["state"] == "blind"


def snapshot(now=None):
    """What the health check, the summary of the accounts and the page may know: never a token, nor a part of one."""
    now = time.time() if now is None else now
    with LOCK:
        blind = STATE["state"] == "blind"
        return {"state": STATE["state"], "reason": STATE["reason"] if blind else "", "since": int(STATE["since"]) if blind else None, "seconds": int(now - STATE["since"]) if blind else 0,
                "replaced_at": int(STATE["replaced_at"]) or None, "source": STATE["source"] or None}


def system_alerts(account_id="", title="", now=None):
    """The critical alert of a blind account, in the shape of the alerts of the sentinels (`sentinel: "system"`), or []."""
    info = snapshot(now)
    if info["state"] != "blind":
        return []
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(info["since"] or 0))
    return [{"id": f"system.credential:{account_id or 'main'}", "code": "system.credential_blind", "level": "critical", "sentinel": "system", "account_id": account_id or "", "repo": None,
             "title": title, "details": {"reason": info["reason"], "since": created, "updated": created}, "created_at": created}]


# --- where the token comes from and where a replacement is kept ---------------------------------------------------------------------------------------------------------------------------

def path_in(folder):
    return Path(folder) / FILE_NAME


def read_file(path):
    """The token in a file of one line, or '' (missing, empty, unreadable or not shaped like a token of GitHub)."""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            token = handle.readline().strip()
    except (OSError, UnicodeError):
        return ""
    return token if secretstore.valid(token) else ""


def stored(folder, env=None):
    """(token, source) of the credential this account should use: its own file, else the file of GH_TOKEN_FILE, else ('', '')."""
    env = os.environ if env is None else env
    token = read_file(path_in(folder)) if folder else ""
    if token:
        return token, "account"
    named = (env.get("GH_TOKEN_FILE") or "").strip()
    token = read_file(named) if named else ""
    return (token, "file") if token else ("", "")


def apply_stored(folder, env=None):
    """Makes the process use the token of `stored()`. Returns its source ('' when there is none: `gh` keeps using what it used)."""
    token, source = stored(folder, env)
    with LOCK:
        if token:
            secretstore.APPLIED["token"] = token
            STATE["source"] = source
        elif STATE["source"]:      # the file was removed: back to what gh uses by itself
            secretstore.APPLIED["token"] = ""
            STATE["source"] = ""
    return source


def replace(folder, token, verify, now=None):
    """Puts a new token in the place of the current one. `verify()` makes one call to GitHub with the process as it is now and returns (True, '') or (False, 'rejected' | 'unreachable'). Returns (ok, status):
    'saved' | 'format' | 'rejected' | 'unreachable' | 'write'. A token that does not pass leaves the old one in place and nothing written."""
    token = str(token or "").strip()
    if not secretstore.valid(token):
        return False, "format"
    now = time.time() if now is None else now
    with LOCK:
        before = secretstore.APPLIED["token"]
        secretstore.APPLIED["token"] = token
    try:
        ok, why = verify()
    except Exception:       # noqa: BLE001 - a check that cannot run keeps the old token
        ok, why = False, "unreachable"
    if not ok:
        with LOCK:
            secretstore.APPLIED["token"] = before
        return False, why or "rejected"
    try:
        private_io.write_private(path_in(folder), token + "\n")
    except OSError:
        with LOCK:
            secretstore.APPLIED["token"] = before
        return False, "write"
    with LOCK:
        STATE.update({"state": "ok", "reason": "", "since": 0.0, "strikes": 0, "last_error": "", "replaced_at": now, "source": "account"})
    return True, "saved"


def reload(folder, verify=None, env=None, now=None):
    """Reads the files again (after the platform rotated a secret, or on SIGHUP). With `verify` a token that GitHub refuses is not kept. Returns 'reloaded' | 'unchanged' | 'rejected' | 'none'."""
    token, source = stored(folder, env)
    if not token:
        apply_stored(folder, env)
        return "none"
    with LOCK:
        if secretstore.APPLIED["token"] == token:
            return "unchanged"
        before, before_source = secretstore.APPLIED["token"], STATE["source"]
        secretstore.APPLIED["token"] = token
    if verify is not None:
        try:
            ok, _ = verify()
        except Exception:       # noqa: BLE001
            ok = False
        if not ok:
            with LOCK:
                secretstore.APPLIED["token"], STATE["source"] = before, before_source
            return "rejected"
    now = time.time() if now is None else now
    with LOCK:
        STATE.update({"state": "ok", "reason": "", "since": 0.0, "strikes": 0, "last_error": "", "replaced_at": now, "source": source})
    return "reloaded"
