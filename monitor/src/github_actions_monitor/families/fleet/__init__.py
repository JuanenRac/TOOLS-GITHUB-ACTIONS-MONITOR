# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The fleet by role and by group, read APIs for other tools and the switch of repositories and groups (fleet_views.py does the work).

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder."""
import re

from github_actions_monitor.families.declare import Family, Raw, Route, Setting

ROLE_RE = re.compile(r"^[a-z][a-z0-9_-]{0,19}=[A-Za-z0-9 ._/*?|()-]{1,150}\Z")
OFF_RE = re.compile(r"^(?:group:[a-z0-9_-]{1,40}|[A-Za-z0-9._*?\[\]-]{1,100})\Z")
ROLES = ["release=*release*|*publish*", "nightly=*nightly*|*schedule*", "benchmark=*bench*", "docs=*doc*|*pages*", "build=*build*|*firmware*|*package*", "test=*test*|*ci*|*check*"]


def _views():
    from github_actions_monitor.families.fleet import fleet_views
    return fleet_views


def _monitor():
    from github_actions_monitor.app import actions_monitor
    return actions_monitor


def _table(request):
    views = _views()
    found = views.snapshot()
    return views.columns(found["runs"], found["repos"], views.roles(views.settings(request.config)["roles"])), found["at"]


def _columns(request):
    view, at = _table(request)
    return {"ok": True, "at": int(at), "roles": view["roles"], "rows": view["rows"], "groups": [{k: g[k] for k in ("key", "state", "repos", "red")} for g in _views().groups(view)]}


def _group(request):
    view, at = _table(request)
    wanted = request.query.get("slug", "")
    found = next((g for g in _views().groups(view) if g["key"] == wanted), None)
    return dict(found, ok=True, at=int(at), roles=view["roles"]) if found else (404, {"ok": False, "error": "unknown_group"})


def _cctray_on(request):
    return _views().settings(request.config)["cctray"] is True


def _cctray_json(request):
    if not _cctray_on(request):
        return 404, {"ok": False, "error": "off"}
    return {"ok": True, "projects": _views().projects(_views().snapshot()["runs"])}


def _cctray_xml(request):
    if not _cctray_on(request):
        return 404, {"ok": False, "error": "off"}
    views = _views()
    return Raw("application/xml; charset=utf-8", views.cctray_xml(views.projects(views.snapshot()["runs"])).encode("utf-8"))


def _security(kind):
    def handler(request):
        if _views().settings(request.config)["security_api"] is not True:
            return 404, {"ok": False, "error": "off"}
        return _views().security_alerts(_monitor().SENTINEL["registry"], kind)
    return handler


def _tick(config, data):
    if not isinstance(data, dict):
        return
    monitor = _monitor()
    _views().remember(monitor.source_runs(config, data), data.get("repos"))


def _s(key, kind, bounds=None, secure=False):
    return Setting("fleetapi", "fleet_apis", "fleet." + key, kind, bounds=bounds, restart=False, secure=secure)


FAMILY = Family(
    "fleet",
    defaults={"fleet": {"disabled": [], "roles": ROLES, "cctray": False, "security_api": False}},
    settings=(_s("disabled", "names", OFF_RE), _s("roles", "names", ROLE_RE), _s("cctray", "bool", secure=True), _s("security_api", "bool", secure=True)),
    settings_tabs=(("fleetapi", "teamwork"),),
    routes=(Route("GET", "/api/fleet/columns", _columns, "the fleet with one column per role of workflow and the worst state of each group"),
            Route("GET", "/api/fleet/group", _group, "the repositories of one group, worst first (the screen /g/<slug> shows it); ?slug="),
            Route("GET", "/api/cctray.json", _cctray_json, "CCTray projects as JSON, read only (fleet.cctray)"),
            Route("GET", "/api/cctray.xml", _cctray_xml, "CCTray feed (XML) for CCMenu and similar tools, read only (fleet.cctray)"),
            Route("GET", "/api/security/secrets", _security("secrets"), "open secret scanning alerts per repository, counts only (fleet.security_api)"),
            Route("GET", "/api/security/code-scanning", _security("code-scanning"), "open code scanning alerts per repository (fleet.security_api)")),
    ticks=(_tick,),
)
