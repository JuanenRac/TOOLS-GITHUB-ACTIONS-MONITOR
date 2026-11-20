# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The assistant of the credentials: one question, "does what I gave the monitor work, and what can it do?".

`probe()` asks GitHub a few small read-only questions and answers in one place:

  * the login the monitor reads with (the stored token or the own login of `gh`): who it is, whether it is a classic token (and its scopes) or a fine-grained token or a GitHub App (which do not
    send scopes), what it lacks for the account of the monitor, how many repositories that account has, and whether the list is complete (single sign-on) and the allowance left (limit, remaining, reset);
  * the GitHub App, when one is configured: its name, the installation it reads with, the permissions it lacks and its own allowance;
  * the installations of the App when it has no `github_app.installation_id` yet: the monitor finds the one of its own account by itself, and when there are several and none is it, it lists them so
    that one can be written.

Nothing is written to GitHub, no token or key is read, printed or kept, and the answer carries no secret. A second ask within `MIN_GAP` seconds returns the last answer, so a button cannot spend the
allowance. Pure code: the questions are given by the caller (`runner`, and the App functions), so the tests need no network."""
import json
import threading
import time

from github_actions_monitor.integrations import access_diag, github_app

MIN_GAP = 10.0
NEEDED = ("repo", "read:org")
_LOCK = threading.Lock()
_LAST = {"at": 0.0, "answer": None}


def kind_of(scopes):
    """"classic" when the answer carried the header of scopes (even an empty one), else "fine_grained_or_app" (a fine-grained token and a GitHub App never send it), or "unknown" without an answer."""
    if scopes is None:
        return "fine_grained_or_app"
    return "classic"


def missing(scopes, owner_kind):
    """The scopes a classic token lacks for this account: `repo` always (private repositories; the doctor says when only public ones are used), `read:org` for an organization. [] for a token without scopes."""
    if scopes is None:
        return []
    have = set(scopes)
    wanted = [s for s in NEEDED if s != "read:org" or owner_kind == "organization"]
    return [s for s in wanted if s not in have and not (s == "read:org" and "admin:org" in have)]


def rate_of(runner):
    """{"limit", "remaining", "reset"} of the core allowance of the login, or None. One small read that costs no allowance."""
    code, out, _err = runner(["gh", "api", "rate_limit"])
    if code != 0:
        return None
    try:
        core = ((json.loads(out) or {}).get("resources") or {}).get("core") or {}
    except ValueError:
        return None
    if not all(isinstance(core.get(k), int) and not isinstance(core.get(k), bool) for k in ("limit", "remaining", "reset")):
        return None
    return {"limit": core["limit"], "remaining": core["remaining"], "reset": core["reset"]}


def user_side(runner, owner=""):
    """What the login of the monitor can do. `runner(args)` = (code, stdout, stderr) with args starting with "gh" (the same one access_diag.probe takes)."""
    found = access_diag.probe(runner, owner)
    out = {"ok": not found["cause"], "login": found["login"], "kind": kind_of(found["scopes"]) if found["login"] else "unknown", "scopes": found["scopes"],
           "missing": missing(found["scopes"], found["owner_kind"]), "owner_kind": found["owner_kind"], "repos": found["repos"], "partial": found["partial"], "cause": found["cause"], "stage": found["stage"],
           "rate": None}
    if found["cause"] not in ("auth", "network"):      # a login that is refused or a network that is down cannot tell its allowance
        out["rate"] = rate_of(runner)
    return out


def app_side(config, status=None, discover=None):
    """What the GitHub App can do, or None when none is configured. `status` and `discover` are github_app.status / github_app.discover (the tests give fakes)."""
    cfg = github_app.settings(config)
    if not cfg["enabled"]:
        return None
    info = (status or github_app.status)(config)
    found = (discover or github_app.discover)(config)
    perms = info.get("permissions") or {}
    return {"enabled": True, "ok": bool(info.get("ok")), "app": info.get("app") or "", "installation_id": str(info.get("installation_id") or found.get("chosen") or ""),
            "missing": sorted(name for name, level in perms.items() if level in ("missing", None)), "rate": info.get("rate") if isinstance(info.get("rate"), dict) else None,
            "error": str(info.get("error") or "")[:160], "code": str(info.get("code") or ""), "installations": found.get("installations", []), "chosen": found.get("chosen", ""),
            "choose_reason": found.get("reason", "")}


def probe(config, runner, owner="", status=None, discover=None, now=None, force=False):
    """The whole answer: {"user": ..., "app": ... | None, "at": epoch, "cached": bool}. The last answer is returned again for MIN_GAP seconds unless `force`."""
    now = time.time() if now is None else now
    with _LOCK:
        if not force and _LAST["answer"] is not None and now - _LAST["at"] < MIN_GAP:
            return {**_LAST["answer"], "cached": True}
    answer = {"user": user_side(runner, owner), "app": app_side(config, status, discover), "at": int(now), "cached": False}
    with _LOCK:
        _LAST.update(at=now, answer=answer)
    return answer


def reset():
    with _LOCK:
        _LAST.update(at=0.0, answer=None)
