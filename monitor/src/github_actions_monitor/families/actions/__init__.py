# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Collaboration views and the optional actions on GitHub (actions_engine.py does the work, actions_views.py is the pure part).

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder. Reading is off by default; writing goes through integrations/ghactions.py, off by default and confirmed one plan at a time."""
import re

from github_actions_monitor.families.declare import Command, Family, Option, Route, Setting

PATTERN_RE = re.compile(r"^[A-Za-z0-9 ._/*?\[\]()-]{1,100}\Z")
POLICY_RE = re.compile(r"^[A-Za-z0-9._*?-]{1,100}:[^:]{1,100}:[A-Za-z0-9._/*?-]{1,100}\Z")
LOGIN_RE = re.compile(r"^[A-Za-z0-9\[\]-]{1,60}\Z")


def _engine():
    from github_actions_monitor.families.actions import actions_engine as engine
    return engine


def _monitor():
    from github_actions_monitor.app import actions_monitor
    return actions_monitor


def _account():
    return _monitor().CHILD["account"] or ""


def _owner(config):
    from github_actions_monitor.app import toolconfig
    return toolconfig.github_owner(config)


def _off():
    return 409, {"ok": False, "error": "off"}


def _state(request):
    return _engine().report(request.config, _account())


def _form(request):
    if not _engine().active(request.config):
        return _off()
    return _engine().dispatch_form(request.config, _owner(request.config), request.query.get("repo", ""), request.query.get("workflow", ""))


def _environments(request):
    if not _engine().active(request.config):
        return _off()
    return _engine().environments_of(_owner(request.config), request.query.get("repo", ""), request.query.get("run", ""))


def _facts(request):
    engine = _engine()
    if not (engine.active(request.config) and engine.settings(request.config)["forks_help"] is True):
        return _off()
    return engine.fork_facts(_owner(request.config), request.query.get("repo", ""), request.query.get("run", ""))


def _plan(request):
    """The plan of an action that carries more than a number (a workflow dispatch with its inputs, the approval of a deployment) or comes from a view. It is confirmed with /api/gh-action/confirm."""
    from github_actions_monitor.integrations import ghactions
    from github_actions_monitor.security import audit_log
    body, config = request.body, request.config
    action, repo, number = body.get("action"), body.get("repo"), body.get("number")
    fields, owner = None, _owner(config)
    audit_log.note(f"{str(action)[:30]} {str(repo)[:100]}")
    if action == "dispatch":
        form = _engine().dispatch_form(config, owner, repo, body.get("workflow"))
        if not form["ok"]:
            return 400, {"ok": False, "status": form["reason"]}
        from github_actions_monitor.families.actions import actions_views
        values, why = actions_views.dispatch_values(form["inputs"], body.get("inputs"))
        if why:
            return 400, {"ok": False, "status": "inputs", "detail": why}
        number, ref = form["id"], str(body.get("ref") or form["ref"])
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", ref) or ".." in ref:
            return 400, {"ok": False, "status": "ref"}
        fields = {"ref": ref, **{f"inputs[{k}]": v for k, v in values.items()}}
    elif action == "approve_deployment":
        found = _engine().environments_of(owner, repo, number)
        allowed = [e["id"] for e in found.get("environments", []) if e["can_approve"]]
        if not allowed:
            return 400, {"ok": False, "status": "nothing_to_approve"}
        fields = {"environment_ids[]": allowed, "state": "approved", "comment": ghactions.clean_text(body.get("reason"), 200) or "approved from the monitor"}
    item, why = ghactions.plan(config, owner, action, repo, number, reason=body.get("reason"), operator=request.user or body.get("operator"), run_gh=_monitor().run_gh_checked, fields=fields)
    return {"ok": item is not None, "status": why, "plan": item}


def _dismiss(request):
    from github_actions_monitor.data_pipeline import run_dismiss
    from github_actions_monitor.security import audit_log
    body = request.body
    audit_log.note(f"{str(body.get('repo'))[:100]} {str(body.get('run'))[:20]}")
    if body.get("restore") is True:
        return {"ok": run_dismiss.restore(body.get("repo"), body.get("run"))}
    mark, why = run_dismiss.dismiss(body.get("repo"), body.get("run"), request.user or body.get("operator"), body.get("reason"), _engine().settings(request.config)["dismiss_days"])
    return {"ok": True, "mark": mark} if mark else (400, {"ok": False, "status": why})


def _cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    engine = _engine()
    config = toolconfig.raw_config()
    out = engine.report(config, _account())
    if ctx["action"] == "proposals":
        lines = [f"{p['action']:<16} {p['repo']:<30} {p['number']:<12} {p['why']} {p['detail']}".rstrip() for p in out["proposals"]]
        return {"ok": True, "proposals": out["proposals"]}, lines or [i18n.t("cli.actions.none")], 0
    lines = [i18n.t("cli.actions.summary", person=len(out["waiting"]["person"]), red=sum(1 for x in out["lanes"] if x["red"]), behind=sum(1 for p in out["pulls"] if p["behind"]),
                    vulnerable=len(out["vulnerable"]), unread=len(out["unread"]), proposals=len(out["proposals"]))]
    lines += [f"unread     {u['repo']:<30} {u['part']} ({u['reason']})" for u in out["unread"]]
    return out, lines, 0


def _hook_cli(ctx):
    import os

    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    kept = _engine().record_hook(toolconfig.raw_config(), ctx["action"], os.environ, account=_account())
    return {"ok": True, "recorded": kept}, [i18n.t("cli.actions.hook_kept" if kept else "cli.actions.hook_off")], 0      # a hook never fails the job of the runner


def _tick(config, data):
    engine = _engine()
    if not engine.active(config):
        return
    monitor = _monitor()
    engine.tick(config, data, monitor.source_runs(config, data), monitor.run_gh_checked, _account())


def _alerts(config, account):
    return _engine().alerts(config, account) if ((config.get("teamwork") or {}).get("enabled") is True) else []


def _s(key, kind, bounds=None, secure=False, unit=None):
    return Setting("teamwork", "teamwork", "teamwork." + key, kind, bounds=bounds, restart=False, secure=secure, unit=unit)


FAMILY = Family(
    "actions",
    defaults={"teamwork": {"enabled": False, "repos_per_cycle": 3, "refresh_hours": 6, "dismiss_days": 30, "hide_workflows": ["Dependabot Updates"], "bot_authors": ["dependabot[bot]", "renovate[bot]"],
                          "bot_branches": ["dependabot/*", "renovate/*"], "bot_labels": ["dependencies"], "dismissed_alerts": False, "dismiss_allowed": [], "auto_rerun": False, "cancel_policy": [],
                          "queued_hours": 6, "stuck_hours": 6, "forks_help": False, "inactive_workflows": False, "runner_hooks": False}},
    settings=(_s("enabled", "bool", secure=True), _s("repos_per_cycle", "int", (1, 50)), _s("refresh_hours", "int", (1, 720), unit="h"), _s("dismiss_days", "int", (1, 365), unit="d"),
              _s("hide_workflows", "names", PATTERN_RE), _s("bot_authors", "names", LOGIN_RE), _s("bot_branches", "names", PATTERN_RE), _s("bot_labels", "names", PATTERN_RE),
              _s("dismissed_alerts", "bool"), _s("dismiss_allowed", "names", LOGIN_RE, secure=True), _s("auto_rerun", "bool", secure=True), _s("cancel_policy", "names", POLICY_RE, secure=True),
              _s("queued_hours", "int", (1, 720), unit="h"), _s("stuck_hours", "int", (1, 720), unit="h"), _s("forks_help", "bool"), _s("inactive_workflows", "bool"), _s("runner_hooks", "bool", secure=True)),
    settings_tabs=(("teamwork", "extci"),),
    routes=(Route("GET", "/api/actions/state", _state, "collaboration views: what waits for a person or a runner, last run of each lane, set aside runs, dependency pull requests, vulnerable repositories (and the ones not read), proposals"),
            Route("GET", "/api/actions/dispatch-form", _form, "the inputs of a workflow fired by hand; ?repo=&workflow=file.yml", role="maintainer"),
            Route("GET", "/api/actions/environments", _environments, "the environments a run waits for; ?repo=&run=", role="maintainer"),
            Route("GET", "/api/actions/fork-facts", _facts, "facts about the author of a fork run that waits for approval (teamwork.forks_help); ?repo=&run=", role="maintainer"),
            Route("POST", "/api/actions/plan", _plan, "the plan of an action on GitHub (nothing is sent); confirmed with /api/gh-action/confirm", this_computer=True, audit="actions_plan", max_body=16384),
            Route("POST", "/api/actions/dismiss", _dismiss, "set a red run aside for a while or restore it (kept by the monitor, nothing on GitHub)", role="maintainer", audit="actions_dismiss", max_body=2048)),
    commands=(Command("actions", _cli, "cli.actions.help", words=("status", "proposals")),
              Command("runner-hook", _hook_cli, "cli.actions.help_hook", words=("started", "completed"))),
    ticks=(_tick,),
    alerts=_alerts,
)
