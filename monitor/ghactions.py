# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Actions ON GitHub from the page (`github_actions.enabled`, OFF by default): run again a failed run or job, cancel a run, close an issue or a pull request, merge a pull request.

  * Every action needs its own confirmation: the page asks for a plan (what exactly will be sent: method, endpoint, repository, number) and then confirms THAT plan with a one-use
    token (confirmation.py). Nothing is ever done automatically, in a loop or from a notification, and the AI assistant has no way to reach this module.
  * Only the actions named in `github_actions.allowed` can be planned; by default the two that change nothing for good (`rerun_failed`, `cancel`). `close_issue`, `close_pr` and `merge_pr`
    must be added by you.
  * It needs the permission of the token: with a classic token the scopes (`X-OAuth-Scopes`) must include `workflow` for runs and jobs and `repo` for issues and pull requests; a
    fine-grained token or an app token does not list scopes, so GitHub's own answer (403) is the check and it is shown.
  * Every attempt is written to `github_actions_log.jsonl` (time, action, repository, number, result - never a token and never an answer body).
"""
import json
import re
import time
from pathlib import Path

import confirmation
import secretstore
import private_io

HERE = Path(__file__).resolve().parent
LOG_FILE = HERE / "github_actions_log.jsonl"
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
NUMBER_RE = re.compile(r"^[0-9]{1,12}$")
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
}
DEFAULT_ALLOWED = ("rerun_failed", "cancel")
PENDING = confirmation.Pending()


def settings(config):
    cfg = config.get("github_actions") if isinstance(config, dict) and isinstance(config.get("github_actions"), dict) else {}
    allowed = cfg.get("allowed")
    allowed = [a for a in allowed if a in ACTIONS] if isinstance(allowed, list) else list(DEFAULT_ALLOWED)
    return {"enabled": cfg.get("enabled") is True, "allowed": allowed, "merge_method": cfg.get("merge_method") if cfg.get("merge_method") in METHODS else "squash"}


def plan(config, owner, action, repo, number):
    """({plan dict} | None, reason). Reasons: off, action, not_allowed, repo, number. The plan is what will be sent; it is kept for the confirmation."""
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
    method, endpoint, scope, subject = ACTIONS[action]
    fields = {"state": "closed"} if action in ("close_issue", "close_pr") else ({"merge_method": cfg["merge_method"]} if action == "merge_pr" else {})
    item = {"action": action, "method": method, "endpoint": endpoint.format(owner=owner, repo=repo, id=number), "scope": scope, "subject": subject, "repo": repo, "number": number,
            "fields": fields}
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


def log(entry, path=None):
    line = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **{k: entry[k] for k in ("action", "repo", "number", "ok", "status") if k in entry}}
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
    have = scopes(run_gh)
    if not permission(item["scope"], have):
        result = {"ok": False, "status": "permission"}
    else:
        args = ["api", "-X", item["method"], item["endpoint"]] + [x for k, v in item["fields"].items() for x in ("-f", f"{k}={v}")]
        code, _out, err = run_gh(args, 40)
        if code == 0:
            result = {"ok": True, "status": "done"}
        else:
            result = {"ok": False, "status": "refused" if re.search(r"\b(403|404|405|409|422)\b", err or "") else "error", "detail": secretstore.redact((err or "").strip()[:200], secretstore.APPLIED["token"])}
    log({**item, **result}, log_file)
    return result
