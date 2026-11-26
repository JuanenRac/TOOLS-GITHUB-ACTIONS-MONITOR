# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Posture of repositories and organizations, read only (posture_engine.py does the work, posture_catalogue.py lists the checks).

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder."""
import re

from github_actions_monitor.families.declare import Command, Family, Option, Route, Setting

TYPE_RE = re.compile(r"^[A-Za-z0-9._*?-]{1,100}=(standard|library|internal|sandbox)\Z")
CHECK_RE = re.compile(r"^(webhook|actions|scan|repo|branch|deploy|stored|org|runner|release|original)\.[a-z_]{2,30}\Z")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/*?-]{1,100}\Z")
WINDOW_RE = re.compile(r"^(?:[1-7]-[1-7] (?:[01]\d|2[0-4])-(?:[01]\d|2[0-4]))?\Z")


def _engine():
    from github_actions_monitor.families.posture import posture_engine as engine
    return engine


def _account():
    from github_actions_monitor.app import actions_monitor
    return actions_monitor.CHILD["account"] or ""


def _report(request):
    return _engine().report(request.config, _account())


def _cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    engine = _engine()
    config = toolconfig.raw_config()
    if ctx["action"] == "matrix":
        from github_actions_monitor.families.posture import posture_catalogue as catalogue
        rows = catalogue.matrix()
        return {"ok": True, "permissions": rows}, [f"{r['permission']}: {', '.join(r['checks'])}" for r in rows], 0
    if ctx["action"] == "check":      # one read of one repository, now
        repo = ctx["args"].repo_name
        if repo:
            engine.refresh(dict(config, posture=dict(engine.settings(config), enabled=True, refresh_hours=0, org_checks=False)), toolconfig.github_owner(config), [repo])
    out = engine.report(config, _account())
    if ctx["action"] == "report":
        return {"ok": True, "compliance": out["compliance"], "trend": out["trend"]}, engine.markdown(out), 0
    if ctx["action"] == "check" and ctx["args"].repo_name:
        out["repos"] = [r for r in out["repos"] if r["repo"] == ctx["args"].repo_name]
    lines = engine.text_lines(out) or [i18n.t("cli.posture.none")]
    worst = 1 if any(f["level"] == "error" for r in out["repos"] for f in r["findings"]) or any(f["level"] == "error" for f in out["org"]["findings"]) else 0
    return out, lines, worst


def _tick(config, data):
    _engine().tick(config, data, _account())


def _s(key, kind, bounds=None, secure=False, unit=None):
    return Setting("posture", "posture", "posture." + key, kind, bounds=bounds, restart=False, secure=secure, unit=unit)


FAMILY = Family(
    "posture",
    defaults={"posture": {"enabled": False, "alerts": True, "profile": "basic", "types": [], "skip": [], "repos_per_cycle": 3, "refresh_hours": 24, "org_checks": True, "audit_log": False,
                          "review_sample": 0, "runner_runs": 0, "releases": True, "release_window": "", "release_branches": ["release/*", "release-*", "hotfix/*"], "deploy_max_days": 365,
                          "stored_max_days": 365, "upstream": False}},
    settings=(_s("enabled", "bool", secure=True), _s("alerts", "bool"), _s("profile", "enum", ("basic", "strict")), _s("types", "names", TYPE_RE), _s("skip", "names", CHECK_RE),
              _s("repos_per_cycle", "int", (1, 50)), _s("refresh_hours", "int", (1, 720), unit="h"), _s("org_checks", "bool"), _s("audit_log", "bool"), _s("review_sample", "int", (0, 30)),
              _s("runner_runs", "int", (0, 20)), _s("releases", "bool"), _s("release_window", "text", WINDOW_RE), _s("release_branches", "names", BRANCH_RE), _s("deploy_max_days", "int", (30, 3650), unit="d"),
              _s("stored_max_days", "int", (30, 3650), unit="d"), _s("upstream", "bool")),
    settings_tabs=(("posture", "extci"),),
    routes=(Route("GET", "/api/posture", _report, "posture of the repositories and the organization: findings, what could not be checked, OWASP and CIS references, permissions needed, history"),),
    commands=(Command("posture", _cli, "cli.posture.help", words=("status", "matrix", "check", "report"), options=(Option("--repo-name", "cli.posture.help_repo", {"default": ""}),)),),
    ticks=(_tick,),
)
