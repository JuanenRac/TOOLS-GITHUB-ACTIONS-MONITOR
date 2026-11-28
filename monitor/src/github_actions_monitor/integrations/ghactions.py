# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Actions ON GitHub from the page (`github_actions.enabled`, OFF by default): run again a failed run or job, cancel a run, close an issue or a pull request, merge a pull request.

  * Every action needs its own confirmation: the page asks for a plan (what exactly will be sent: method, endpoint, repository, number) and then confirms THAT plan with a one-use
    token (confirmation.py). Nothing is ever done automatically, in a loop or from a notification, and the AI assistant has no way to reach this module.
  * Only the actions named in `github_actions.allowed` can be planned; by default the two that change nothing for good (`rerun_failed`, `cancel`). `close_issue`, `close_pr` and `merge_pr`
    must be added by you.
  * It needs the permission of the token: with a classic token the scopes (`X-OAuth-Scopes`) must include `workflow` for runs and jobs and `repo` for issues and pull requests; a
    fine-grained token or an app token does not list scopes, so GitHub's own answer (403) is the check and it is shown.
  * Every attempt is written to `github_actions_log.jsonl` (time, action, repository, number, operator, reason, result - never a token and never an answer body).
  * `github_actions.require_reason` (on): every action needs a reason (3 to 200 characters) and the name of the operator (`github_actions.operator`, or the signed-in person in the team mode); the server
    refuses a plan without them, whatever the page sends. With `github_actions.comment_on_target` (off) a closed issue or pull request also gets a comment with the operator and the reason, because the
    actor GitHub shows is the App or the token, not the person.
  * The server looks again at the state of the target right before acting (an issue that was closed meanwhile, a run that finished) and does not trust the screen: `stale` when it no longer fits.
  * `github_actions.preflight` (on): before a plan is made it asks, without side effects, whether the credential can (write access to the repository, no list of who may push that leaves it out): `doctor()`.
  * `github_actions.writer_lock` (on): only one monitor of this computer writes; a second one, and any monitor started with `--profile qa`, is an observer and refuses every action (`observer`).
"""
import json
import os
import re
import time
from pathlib import Path

from github_actions_monitor.security import audit_log
from github_actions_monitor.security import confirmation
from github_actions_monitor.security import secretstore
from github_actions_monitor.security import private_io

from github_actions_monitor.util import paths
LOG_FILE = paths.place("github_actions_log.jsonl")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
NUMBER_RE = re.compile(r"^[0-9]{1,12}\Z")
METHODS = ("merge", "squash", "rebase")
# action -> (HTTP method, endpoint, scope the token needs, what the number is)
ACTIONS = {
    "rerun_failed": ("POST", "repos/{owner}/{repo}/actions/runs/{id}/rerun-failed-jobs", "workflow", "run"),
    "rerun_run": ("POST", "repos/{owner}/{repo}/actions/runs/{id}/rerun", "workflow", "run"),
    "rerun_job": ("POST", "repos/{owner}/{repo}/actions/jobs/{id}/rerun", "workflow", "job"),
    "cancel": ("POST", "repos/{owner}/{repo}/actions/runs/{id}/cancel", "workflow", "run"),
    "close_issue": ("PATCH", "repos/{owner}/{repo}/issues/{id}", "repo", "issue"),
    "close_pr": ("PATCH", "repos/{owner}/{repo}/pulls/{id}", "repo", "pr"),
    "merge_pr": ("PUT", "repos/{owner}/{repo}/pulls/{id}/merge", "repo", "pr"),
    "update_branch": ("PUT", "repos/{owner}/{repo}/pulls/{id}/update-branch", "repo", "pr"),
    "approve_fork": ("POST", "repos/{owner}/{repo}/actions/runs/{id}/approve", "workflow", "run"),
    "approve_deployment": ("POST", "repos/{owner}/{repo}/actions/runs/{id}/pending_deployments", "repo", "run"),
    "force_cancel": ("POST", "repos/{owner}/{repo}/actions/runs/{id}/force-cancel", "workflow", "run"),
    "enable_workflow": ("PUT", "repos/{owner}/{repo}/actions/workflows/{id}/enable", "workflow", "workflow"),
    "dispatch": ("POST", "repos/{owner}/{repo}/actions/workflows/{id}/dispatches", "workflow", "workflow"),
}
#: actions that mean nothing without the fields the monitor builds for them (families/actions/): never planned from a number alone
NEEDS_FIELDS = ("approve_deployment", "dispatch")
DEFAULT_ALLOWED = ("rerun_failed", "cancel")
PENDING = confirmation.Pending()
REASON_RANGE = (3, 200)
OPERATOR_MAX = 60
LOCK_NAME = "github_actions_writer.lock"
WRITER = {"owner": False}      # this process holds the writer lock
CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(value, limit):
    """A reason or a name as one line of at most `limit` characters, with no control character."""
    return " ".join(CTRL_RE.sub(" ", str(value or "")).split())[:limit]


def settings(config):
    cfg = config.get("github_actions") if isinstance(config, dict) and isinstance(config.get("github_actions"), dict) else {}
    allowed = cfg.get("allowed")
    allowed = [a for a in allowed if a in ACTIONS] if isinstance(allowed, list) else list(DEFAULT_ALLOWED)
    flag = lambda key, default: cfg.get(key) if isinstance(cfg.get(key), bool) else default  # noqa: E731
    return {"enabled": cfg.get("enabled") is True, "allowed": allowed, "merge_method": cfg.get("merge_method") if cfg.get("merge_method") in METHODS else "squash",
            "require_reason": flag("require_reason", True), "operator": clean_text(cfg.get("operator"), OPERATOR_MAX), "comment_on_target": flag("comment_on_target", False),
            "preflight": flag("preflight", True), "writer_lock": flag("writer_lock", True)}


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def process_started(pid):
    """A text that says WHEN the process `pid` started ("" when it cannot be told): a pid that Windows or Linux gave to another program later has another one."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.windll.kernel32
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1000, False, pid)      # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return ""
            try:
                created, other = wintypes.FILETIME(), wintypes.FILETIME()
                if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(other), ctypes.byref(other), ctypes.byref(other)):
                    return ""
                return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
            finally:
                kernel.CloseHandle(handle)
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists():
            return stat.read_text(encoding="ascii", errors="replace").rsplit(")", 1)[1].split()[19]      # field 22: the start in clock ticks after the boot
        import subprocess
        done = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return " ".join(done.stdout.split()) if done.returncode == 0 else ""
    except Exception:   # noqa: BLE001 - not knowing is allowed
        return ""


def _read_lock(path):
    """(pid, started) written in the lock file: the old files hold the pid only."""
    try:
        parts = Path(path).read_text(encoding="ascii", errors="replace").split(None, 1)
        return (int(parts[0]) if parts else 0), (parts[1].strip() if len(parts) > 1 else "")
    except (OSError, ValueError):
        return 0, ""


def release_writer(lock_path=None):
    """Deletes the lock file when it is this process's: it runs when the monitor ends, so the pid it wrote is not left behind for another program to inherit."""
    path = Path(lock_path) if lock_path else paths.place(LOCK_NAME)
    if _read_lock(path)[0] == os.getpid():
        try:
            os.remove(str(path))
        except OSError:
            pass
    WRITER["owner"] = False


def writer_state(config, env=None, lock_path=None):
    """("writer" | "observer", why). A monitor started with MONITOR_PROFILE=qa (`--profile qa`) is always an observer; otherwise, with `github_actions.writer_lock` on, the first monitor of this computer
    that asks takes the lock (a file with its PID) and the others are observers until it ends. Two monitors on one account would do every action twice."""
    env = os.environ if env is None else env
    if (env.get("MONITOR_PROFILE") or "").strip().lower() == "qa":
        return "observer", "qa"
    if not settings(config).get("writer_lock", True):
        return "writer", ""
    path = Path(lock_path) if lock_path else paths.place(LOCK_NAME)
    for _attempt in range(2):
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                started = process_started(os.getpid())
                os.write(fd, (f"{os.getpid()} {started}" if started else str(os.getpid())).encode("ascii", errors="replace"))
            finally:
                os.close(fd)
            WRITER["owner"] = True
            if not WRITER.get("exit_registered"):
                import atexit
                atexit.register(release_writer, lock_path)
                WRITER["exit_registered"] = True
            return "writer", ""
        except FileExistsError:
            other, started = _read_lock(path)
            if other == os.getpid() and not (started and process_started(other) not in ("", started)):      # a lock of this very process (not one a dead monitor left with the same pid)
                return "writer", ""
            if other != os.getpid() and pid_alive(other):
                now_started = process_started(other) if started else ""
                if not (started and now_started and now_started != started):      # the same process still lives; if its start differs the pid was given to another program and the lock is old
                    return "observer", "lock"
            try:
                os.remove(str(path))      # the monitor that held it is gone
            except OSError:
                return "observer", "lock"
        except OSError:
            return "writer", ""      # a folder that cannot be written must not make the monitor refuse for ever
    return "observer", "lock"


def doctor(run_gh, owner, repo, login=""):
    """What the credential can do on one repository, asked without side effects: {"repo", "push", "restricted", "actions": {action: "" | why}}. `push` = write access (None when GitHub does not say),
    `restricted` = the default branch lists who may push and the credential is not among them (None when it cannot be told). An action with a reason is offered disabled, with that reason."""
    out = {"repo": repo, "push": None, "restricted": None, "actions": {}}
    code, text, _err = run_gh(["api", f"repos/{owner}/{repo}"], 25)
    branch = "main"
    if code == 0:
        try:
            body = json.loads(text)
            perms = body.get("permissions") if isinstance(body, dict) else None
            if isinstance(perms, dict) and isinstance(perms.get("push"), bool):
                out["push"] = perms["push"]
            branch = body.get("default_branch") if isinstance(body.get("default_branch"), str) and NAME_RE.match(body["default_branch"]) else "main"
        except ValueError:
            pass
    code, text, _err = run_gh(["api", f"repos/{owner}/{repo}/branches/{branch}/protection/restrictions"], 25)
    if code == 0:
        try:
            body = json.loads(text)
            names = {str(x.get("login") or x.get("slug") or "").lower() for key in ("users", "apps") for x in (body.get(key) or []) if isinstance(x, dict)}
            out["restricted"] = bool(login) and login.lower() not in names if (body.get("users") or body.get("apps") or body.get("teams")) else False
        except (ValueError, AttributeError):
            pass
    elif "404" in (_err or ""):
        out["restricted"] = False      # no list of who may push
    for action, (_m, _e, scope, _s) in ACTIONS.items():
        why = ""
        if out["push"] is False:
            why = "no_push"
        elif action in ("merge_pr", "close_pr") and out["restricted"]:
            why = "restricted_push"
        out["actions"][action] = why
    return out


def preflight_reason(run_gh, owner, repo, action, login=""):
    """"" when the credential can do the action on that repository (or when that cannot be told), else the reason."""
    try:
        return doctor(run_gh, owner, repo, login)["actions"].get(action, "")
    except Exception:   # noqa: BLE001 - a question that cannot be asked blocks nothing
        return ""


def plan(config, owner, action, repo, number, reason="", operator="", run_gh=None, fields=None):
    """({plan dict} | None, reason). Reasons: off, action, not_allowed, repo, number, reason_required, operator_required, observer, preflight. The plan is what will be sent; it is kept for the confirmation."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return None, "off"
    if action not in ACTIONS:
        return None, "action"
    if action not in cfg["allowed"]:
        return None, "not_allowed"
    if not isinstance(repo, str) or not NAME_RE.match(repo) or not isinstance(owner, str) or not NAME_RE.match(owner or ""):
        return None, "repo"
    number = str(number)
    if not NUMBER_RE.match(number):
        return None, "number"
    if action in NEEDS_FIELDS and not fields:
        return None, "fields"
    why = clean_text(reason, REASON_RANGE[1])
    who = clean_text(operator, OPERATOR_MAX) or cfg.get("operator", "")
    if cfg.get("require_reason", True):
        if len(why) < REASON_RANGE[0]:
            return None, "reason_required"
        if not who:
            return None, "operator_required"
    state, _why = writer_state(config)
    if state != "writer":
        return None, "observer"
    if cfg.get("preflight", True) and run_gh is not None and preflight_reason(run_gh, owner, repo, action):
        return None, "preflight"
    method, endpoint, scope, subject = ACTIONS[action]
    if action not in NEEDS_FIELDS:      # the fields of these two are the only ones a caller may give
        fields = {"state": "closed"} if action in ("close_issue", "close_pr") else ({"merge_method": cfg["merge_method"]} if action == "merge_pr" else {})
    item = {"action": action, "method": method, "endpoint": endpoint.format(owner=owner, repo=repo, id=number), "scope": scope, "subject": subject, "repo": repo, "number": number,
            "fields": fields, "reason": why, "operator": who, "owner": owner}
    item["id"] = PENDING.add("ghaction", item)
    return {k: v for k, v in item.items()}, "ok"


def scopes(run_gh):
    """The scopes of the token: a set, or None when the token does not list them (fine-grained, app, Actions token)."""
    code, out, _err = run_gh(["api", "-i", "rate_limit"], 20)
    if code != 0:
        return None
    for line in out.splitlines():
        if line.lower().startswith("x-oauth-scopes:"):
            return {part.strip() for part in line.split(":", 1)[1].split(",") if part.strip()}
    return None


def permission(scope, have):
    """True when the scopes allow the action, or when they are not listed (GitHub decides)."""
    if have is None:
        return True
    return scope in have or (scope == "workflow" and "repo" in have and "workflow" in have) or (scope == "repo" and "repo" in have)


REASONS = {"403": "forbidden", "404": "not_found", "405": "method", "409": "conflict", "422": "invalid"}


def reason_of(err):
    """Why GitHub refused, in words the page can explain: forbidden (the token has no Actions write permission), not_found (a private repository the token cannot see, or no such item: GitHub answers 404 for both),
    method, conflict, invalid (the inputs did not validate). "" when the answer carries none of those codes."""
    found = re.search(r"\b(403|404|405|409|422)\b", err or "")
    return REASONS[found.group(1)] if found else ""


def still_fits(item, run_gh):
    """The server looks at the target again right before it acts: an issue or pull request still open, a run still going (cancel) or finished and red (rerun). What cannot be read, or is not understood,
    does not block (GitHub decides then). False only when the answer is clear and the state no longer fits."""
    owner = item.get("owner") or ""
    action, repo, number = item.get("action"), item.get("repo"), item.get("number")
    if not (action and repo and number):
        return True
    if not owner:
        return True
    kind = {"close_issue": f"issues/{number}", "close_pr": f"pulls/{number}", "merge_pr": f"pulls/{number}", "cancel": f"actions/runs/{number}", "rerun_failed": f"actions/runs/{number}", "rerun_run": f"actions/runs/{number}",
            "update_branch": f"pulls/{number}", "force_cancel": f"actions/runs/{number}", "approve_fork": f"actions/runs/{number}", "approve_deployment": f"actions/runs/{number}"}.get(action)
    if not kind:
        return True
    code, text, _err = run_gh(["api", f"repos/{owner}/{repo}/{kind}"], 25)
    if code != 0:
        return True
    try:
        body = json.loads(text)
    except ValueError:
        return True
    if not isinstance(body, dict):
        return True
    if action in ("close_issue", "close_pr", "merge_pr", "update_branch"):
        return body.get("state") in (None, "open") and not body.get("merged")
    status, conclusion = body.get("status"), body.get("conclusion")
    if action == "approve_fork":
        return conclusion in (None, "action_required")
    if action == "approve_deployment":
        return status in (None, "waiting")
    if action == "force_cancel":
        return status != "completed"
    if action == "cancel":
        return status in (None, "in_progress", "queued", "waiting", "pending", "requested")
    return status in (None, "completed") and conclusion not in ("success",)      # a run that passed is not run again behind someone's back


def log(entry, path=None):
    line = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **{k: entry[k] for k in ("action", "repo", "number", "ok", "status") if k in entry}}
    for key, limit in (("operator", OPERATOR_MAX), ("reason", REASON_RANGE[1])):
        if entry.get(key):
            line[key] = clean_text(entry[key], limit)
    try:
        with private_io.open_append(path or LOG_FILE) as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass


def execute(config, plan_id, run_gh, log_file=None):
    """Runs a confirmed plan. {"ok", "status"} - status: done | off | unknown_plan | permission | refused | error. The plan is consumed even when it fails."""
    if not settings(config)["enabled"]:
        return {"ok": False, "status": "off"}
    item = PENDING.take(plan_id, "ghaction")
    if item is None:
        return {"ok": False, "status": "unknown_plan"}
    audit_log.note(f"{item.get('action')} {item.get('repo')}#{item.get('number')}", {"operator": clean_text(item.get("operator"), OPERATOR_MAX), "reason": clean_text(item.get("reason"), REASON_RANGE[1])})      # the line of the log of actions says what was confirmed, by whom and why
    have = scopes(run_gh)
    if writer_state(config)[0] != "writer":
        result = {"ok": False, "status": "observer"}
    elif not permission(item["scope"], have):
        result = {"ok": False, "status": "permission"}
    elif not still_fits(item, run_gh):
        result = {"ok": False, "status": "stale"}
    else:
        args = ["api", "-X", item["method"], item["endpoint"]]
        for key, value in item["fields"].items():
            for one in value if isinstance(value, list) else [value]:      # a list repeats the key; the numbers of it are sent as numbers
                args += ["-F" if isinstance(one, int) else "-f", f"{key}={one}"]
        code, _out, err = run_gh(args, 40)
        if code == 0:
            result = {"ok": True, "status": "done"}
            if settings(config).get("comment_on_target", False) and item["action"] in ("close_issue", "close_pr", "merge_pr"):
                note = f"Done through GitHub Actions Monitor by {item.get('operator') or 'an operator'}: {item.get('reason') or 'no reason given'}"
                run_gh(["api", "-X", "POST", f"repos/{item['owner']}/{item['repo']}/issues/{item['number']}/comments", "-f", f"body={note}"], 40)
        else:
            why = reason_of(err)
            result = {"ok": False, "status": "refused" if why else "error", "detail": secretstore.redact((err or "").strip()[:200], secretstore.APPLIED["token"])}
            if why:
                result["reason"] = why
    log({**item, **result}, log_file)
    return result
