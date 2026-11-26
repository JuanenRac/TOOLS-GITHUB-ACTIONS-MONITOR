# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""When the collaboration views are read, what is kept (data/actions_state.json) and the one thing that can act by itself.

Reading is GET only and a read that GitHub refuses is listed by name as not read, never as clean. Writing on GitHub goes only through integrations/ghactions.py (off by default, its allowed list, one
confirmation for each plan). The single exception is `actions.auto_rerun` (off): one re-run of a run that the infrastructure ended, through the same checks, never a second one."""
import base64
import json
import re
import threading
import time
import urllib.parse

from github_actions_monitor import families, i18n
from github_actions_monitor.families.actions import actions_views as views
from github_actions_monitor.families.posture.posture_checks import Unread
from github_actions_monitor.families.posture.posture_engine import names_of, reader
from github_actions_monitor.integrations import dispatch_inputs
from github_actions_monitor.storage import state_io
from github_actions_monitor.util import paths

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
WORKFLOW_FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\.ya?ml\Z")
CODE_AGAIN, CODE_DISMISSAL = "actions.rerun_failed_again", "actions.dismissal_not_authorized"
PULLS_DETAILED = 10      # pull requests of one repository read one by one (their state needs it)
AUTO_PER_HOUR = 5
LOCK = threading.RLock()
RUNNING = {"on": False}


def settings(config):
    return families.block(config if isinstance(config, dict) else {}, "actions")


def active(config):
    return settings(config)["enabled"] is True and (config or {}).get("airgapped") is not True


def state_file(account=""):
    name = f"actions_state_{re.sub(r'[^A-Za-z0-9_-]', '', account)}.json" if account else "actions_state.json"
    return paths.folder("data") / name


def load(account=""):
    try:
        data = state_io.load_json(state_file(account))
    except (OSError, ValueError):
        data = None
    data = data if isinstance(data, dict) else {}
    for key, empty in (("repos", {}), ("runs_view", {}), ("rerun", {}), ("hooks", [])):
        if not isinstance(data.get(key), type(empty)):
            data[key] = empty
    return data


def save(data, account=""):
    try:
        path = state_file(account)
        path.parent.mkdir(parents=True, exist_ok=True)
        state_io.save_text(path, json.dumps(data, ensure_ascii=False))
        return True
    except OSError:
        return False


def _list(answer):
    if not isinstance(answer, list):
        raise Unread("failed")
    return [a for a in answer if isinstance(a, dict)]


def read_repo(get, owner, repo, cfg, now):
    """What one repository shows: {"at", "pulls", "vulnerable", "dismissals", "workflows", "quiet_days", "unread": {part: reason}}."""
    base = f"repos/{owner}/{repo}"
    out = {"at": now, "pulls": [], "vulnerable": None, "dismissals": [], "workflows": [], "unread": {}}

    def part(name, function):
        try:
            function()
        except Unread as error:
            if error.reason == "rate_limited":
                raise
            out["unread"][name] = error.reason
        except (AttributeError, KeyError, TypeError, ValueError):
            out["unread"][name] = "failed"

    def pulls():
        found = _list(get(f"{base}/pulls?state=open&per_page=50"))
        for pull in found[:PULLS_DETAILED]:
            bot = views.bot_of(pull, cfg["bot_authors"], cfg["bot_branches"], cfg["bot_labels"])
            number = pull.get("number")
            detail = get(f"{base}/pulls/{int(number)}")
            sha = str((pull.get("head") or {}).get("sha") or "")
            checks = None
            if re.fullmatch(r"[0-9a-fA-F]{7,64}", sha):
                try:
                    checks = (get(f"{base}/commits/{sha}/check-runs?per_page=50") or {}).get("check_runs")
                except Unread as error:
                    if error.reason == "rate_limited":
                        raise
            out["pulls"].append(views.pull_row(repo, pull, detail if isinstance(detail, dict) else {}, checks, bot))

    def vulnerabilities():
        out["vulnerable"] = views.vulnerabilities(repo, _list(get(f"{base}/dependabot/alerts?state=open&per_page=100&sort=created&direction=asc")), now)

    def dismissals():
        for kind, endpoint in (("dependency", "dependabot"), ("code", "code-scanning")):
            out["dismissals"] += views.dismissals(repo, kind, _list(get(f"{base}/{endpoint}/alerts?state=dismissed&per_page=30")), cfg["dismiss_allowed"])

    def workflows():
        answer = get(f"{base}/actions/workflows?per_page=100")
        out["workflows"] = [{"repo": repo, "id": w["id"], "name": str(w.get("name") or "")[:100]} for w in answer.get("workflows") or [] if w.get("state") == "disabled_inactivity" and isinstance(w.get("id"), int)]

    part("pulls", pulls)
    part("vulnerabilities", vulnerabilities)
    if cfg["dismissed_alerts"]:
        part("dismissals", dismissals)
    if cfg["inactive_workflows"]:
        part("workflows", workflows)
    return out


def refresh(config, owner, repos, get=None, now=None, account=""):
    """At most actions.repos_per_cycle repositories whose turn has come, the longest waiting first. Returns how many were read."""
    if not active(config) or not owner or not NAME_RE.match(str(owner)):
        return 0
    cfg = settings(config)
    now = time.time() if now is None else now
    get = get or reader()
    every = cfg["refresh_hours"] * 3600
    done = 0
    with LOCK:
        known = load(account)["repos"]
    due = sorted((r for r in repos if now - known.get(r, {}).get("at", 0) >= every), key=lambda r: known.get(r, {}).get("at", 0))
    found = {}
    for repo in due[:cfg["repos_per_cycle"]]:
        try:
            found[repo] = read_repo(get, owner, repo, cfg, now)
        except Unread:
            break      # the allowance is gone: the rest waits for the next cycle
        done += 1
    with LOCK:
        data = load(account)
        data["repos"].update(found)
        if repos:
            data["repos"] = {k: v for k, v in data["repos"].items() if k in repos}
        save(data, account)
    return done


def runs_view(config, runs, now):
    """What comes out of the runs of a cycle alone (no extra read)."""
    cfg = settings(config)
    runs = views.visible(runs, cfg["hide_workflows"])
    return {"at": now, "waiting": views.waiting(runs), "lanes": views.lanes(runs)[:300], "policy": views.policy_matches(runs, cfg["cancel_policy"]),
            "queued": views.old_runs(runs, views.QUEUED, cfg["queued_hours"], now), "stuck": views.old_runs(runs, views.RUNNING, cfg["stuck_hours"], now),
            "forks": [r for r in views.waiting(runs)["person"] if r["kind"] == "fork"]}


def auto_rerun(config, owner, runs, run_gh, now=None, account=""):
    """With actions.auto_rerun: one re-run of the failed jobs of each new run that the infrastructure ended, through the plan and the confirmation of ghactions (so it stays off while the actions are
    off, `rerun_failed` is not allowed, this monitor only observes or the credential cannot). Returns the ids tried now."""
    from github_actions_monitor.integrations import ghactions
    cfg = settings(config)
    if not (active(config) and cfg["auto_rerun"] is True and run_gh):
        return []
    if not ghactions.settings(config)["enabled"] or "rerun_failed" not in ghactions.settings(config)["allowed"]:
        return []
    now = time.time() if now is None else now
    tried = []
    with LOCK:
        data = load(account)
        done = data["rerun"]
        room = AUTO_PER_HOUR - sum(1 for v in done.values() if now - v.get("at", 0) < 3600)
        for run in views.rerun_candidates(runs, done, now)[:max(0, room)]:
            item, why = ghactions.plan(config, owner, "rerun_failed", run.get("repo"), run.get("id"), reason="automatic single re-run of an infrastructure failure (actions.auto_rerun)",
                                       operator="monitor (automatic)", run_gh=run_gh)
            result = ghactions.execute(config, item["id"], run_gh) if item else {"ok": False, "status": why}
            done[str(run["id"])] = {"at": now, "repo": run.get("repo"), "workflow": run.get("name"), "status": result["status"]}      # whatever happened, this run is never tried again
            tried.append(run["id"])
        data["rerun"] = dict(sorted(done.items(), key=lambda kv: kv[1].get("at", 0))[-500:])
        save(data, account)
    return tried


def report(config, account="", now=None):
    from github_actions_monitor.data_pipeline import run_dismiss
    cfg = settings(config)
    now = time.time() if now is None else now
    data = load(account)
    view = data["runs_view"]
    repos = data["repos"]
    pulls = [p for entry in repos.values() for p in entry.get("pulls", [])]
    workflows = [w for entry in repos.values() for w in entry.get("workflows", [])]
    unread = [{"repo": name, "part": part, "reason": why} for name, entry in sorted(repos.items()) for part, why in (entry.get("unread") or {}).items()]
    vulnerable = sorted((e["vulnerable"] for e in repos.values() if e.get("vulnerable")), key=lambda v: (-v["critical"], -(v["oldest_days"] or 0), v["repo"]))
    return {"ok": True, "enabled": cfg["enabled"] is True, "waiting": view.get("waiting") or {"person": [], "machine": []}, "lanes": view.get("lanes") or [], "dismissed": run_dismiss.rows(now),
            "pulls": sorted(pulls, key=lambda p: (not p["bot"], p["group"], p["repo"], p["number"] or 0)), "vulnerable": vulnerable, "unread": unread,
            "not_read_yet": view.get("repos_waiting") or [], "dismissals": [d for e in repos.values() for d in e.get("dismissals", [])], "workflows": workflows,
            "proposals": views.proposals(view.get("all_runs") or [], pulls, view.get("policy") or [], workflows, cfg, now),
            "auto_reruns": [dict(v, run=int(k)) for k, v in data["rerun"].items() if k.isdigit()][-30:], "runner_events": data["hooks"][-50:]}


def alerts(config, account=""):
    if not active(config):
        return []
    data = load(account)
    out = []

    def alert(code, level, ident, repo, title, details, at):
        out.append({"id": f"{code}:{ident}", "code": code, "level": level, "sentinel": "ci", "account_id": account, "repo": repo, "title": title, "details": details,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(at))})
    for row in data["runs_view"].get("failed_again") or []:
        alert(CODE_AGAIN, "error", f"{row['repo']}:{row['run']}", row["repo"], i18n.t("ui.actions.alert_again", repo=row["repo"], workflow=row["workflow"]), {"url": row["url"], "workflow": row["workflow"]},
              data["runs_view"].get("at", 0))
    for entry in data["repos"].values():
        for item in entry.get("dismissals", []):
            if item.get("authorized") is False:
                alert(CODE_DISMISSAL, "warning", f"{item['repo']}:{item['kind']}:{item['number']}", item["repo"], i18n.t("ui.actions.alert_dismissal", repo=item["repo"], who=item["who"] or "?"),
                      {"url": item["url"], "reason": item["reason"], "who": item["who"]}, entry.get("at", 0))
    return out


def tick(config, data, runs, run_gh=None, account="", get=None):
    """After a cycle: the views from the runs at once, the automatic re-run when it is on, and the reads of the repositories in a thread of their own."""
    if not active(config):
        return None
    from github_actions_monitor.app import toolconfig
    owner, repos, now = toolconfig.github_owner(config), names_of(data), time.time()
    cfg = settings(config)
    runs = [r for r in runs or [] if isinstance(r, dict)]
    view = runs_view(config, runs, now)
    view["all_runs"] = [{k: r.get(k) for k in ("repo", "id", "name", "branch", "status", "started", "event", "url", "actor")} for r in runs if r.get("status") != "completed"][:600]
    auto_rerun(config, owner, views.visible(runs, cfg["hide_workflows"]), run_gh, now, account)
    with LOCK:
        state = load(account)
        view["failed_again"] = views.failed_again(runs, state["rerun"])
        view["repos_waiting"] = [r for r in repos if r not in state["repos"]][:100]
        state["runs_view"] = view
        save(state, account)
    if RUNNING["on"]:
        return None
    RUNNING["on"] = True

    def work():
        try:
            refresh(config, owner, repos, get=get, account=account)
        finally:
            RUNNING["on"] = False
    thread = threading.Thread(target=work, name="actions-views", daemon=True)
    thread.start()
    return thread


def dispatch_form(config, owner, repo, workflow, get=None):
    """The inputs of a workflow that is fired by hand, read from its file on the default branch: {"ok", "id", "ref", "inputs"} or {"ok": False, "reason"}."""
    if not (NAME_RE.match(str(repo or "")) and WORKFLOW_FILE_RE.match(str(workflow or "")) and NAME_RE.match(str(owner or ""))):
        return {"ok": False, "reason": "name"}
    get = get or reader()
    try:
        info = get(f"repos/{owner}/{repo}/actions/workflows/{urllib.parse.quote(workflow)}")
        branch = str((get(f"repos/{owner}/{repo}") or {}).get("default_branch") or "main")
        answer = get(f"repos/{owner}/{repo}/contents/.github/workflows/{urllib.parse.quote(workflow)}")
        text = base64.b64decode(str(answer.get("content") or ""), validate=False).decode("utf-8", "replace")[:500000]
        ident = int(info["id"])
    except Unread as error:
        return {"ok": False, "reason": error.reason}
    except (AttributeError, KeyError, TypeError, ValueError):
        return {"ok": False, "reason": "failed"}
    inputs = dispatch_inputs.parse(text)
    if inputs is None:
        return {"ok": False, "reason": "unreadable_inputs"}
    if "workflow_dispatch" not in text:
        return {"ok": False, "reason": "not_manual"}
    return {"ok": True, "id": ident, "ref": branch, "inputs": inputs}


def environments_of(owner, repo, run, get=None):
    """The environments a run waits for: {"ok", "environments": [{"id", "name", "can_approve"}]}."""
    if not (NAME_RE.match(str(repo or "")) and str(run).isdigit()):
        return {"ok": False, "reason": "name"}
    get = get or reader()
    try:
        rows = _list(get(f"repos/{owner}/{repo}/actions/runs/{run}/pending_deployments"))
    except Unread as error:
        return {"ok": False, "reason": error.reason}
    return {"ok": True, "environments": [{"id": r["environment"]["id"], "name": str(r["environment"].get("name") or "")[:100], "can_approve": r.get("current_user_can_approve") is True}
                                         for r in rows if isinstance(r.get("environment"), dict) and isinstance(r["environment"].get("id"), int)]}


def fork_facts(owner, repo, run, get=None):
    """Facts about the author of a run of a fork that waits for approval, to help a person decide. Facts only: no verdict is given."""
    if not (NAME_RE.match(str(repo or "")) and str(run).isdigit()):
        return {"ok": False, "reason": "name"}
    get = get or reader()
    try:
        info = get(f"repos/{owner}/{repo}/actions/runs/{run}")
        login = str((info.get("triggering_actor") or info.get("actor") or {}).get("login") or "")
        sha = str(info.get("head_sha") or "")
        if not re.fullmatch(r"[A-Za-z0-9\[\]-]{1,60}", login) or not re.fullmatch(r"[0-9a-f]{7,64}", sha):
            return {"ok": False, "reason": "failed"}
        user = get(f"users/{urllib.parse.quote(login)}")
        query = urllib.parse.quote(f"repo:{owner}/{repo} is:pr is:merged author:{login}")
        merged = get(f"search/issues?q={query}&per_page=1")
        pulls = _list(get(f"repos/{owner}/{repo}/commits/{sha}/pulls"))
        number = pulls[0]["number"] if pulls else None
        files = _list(get(f"repos/{owner}/{repo}/pulls/{int(number)}/files?per_page=100")) if number else None
    except Unread as error:
        return {"ok": False, "reason": error.reason}
    except (AttributeError, KeyError, TypeError, ValueError):
        return {"ok": False, "reason": "failed"}
    created = views.epoch(user.get("created_at"))
    return {"ok": True, "author": login, "account_age_days": int((time.time() - created) // 86400) if created else None, "public_repos": user.get("public_repos"),
            "merged_before": merged.get("total_count"), "association": str((pulls[0].get("author_association") if pulls else "") or ""), "pull": number,
            "workflow_files": None if files is None else [str(f.get("filename"))[:200] for f in files if str(f.get("filename") or "").startswith((".github/", "action.y"))][:20],
            "files": None if files is None else len(files), "sha": sha[:12]}


def record_hook(config, phase, env, now=None, account=""):
    """One event of a hook of a self-hosted runner (ACTIONS_RUNNER_HOOK_JOB_STARTED / _COMPLETED), from the variables GitHub gives the hook. True when it was kept."""
    if not (active(config) and settings(config)["runner_hooks"] is True) or phase not in ("started", "completed"):
        return False

    def clean(name, limit=120):
        return "".join(c for c in str(env.get(name) or "") if c.isprintable())[:limit]
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now)), "phase": phase, "repo": clean("GITHUB_REPOSITORY"), "run": clean("GITHUB_RUN_ID", 20),
           "job": clean("GITHUB_JOB"), "workflow": clean("GITHUB_WORKFLOW"), "runner": clean("RUNNER_NAME")}
    if not row["repo"] or not row["run"]:
        return False
    with LOCK:
        data = load(account)
        data["hooks"] = (data["hooks"] + [row])[-200:]
        return save(data, account)
