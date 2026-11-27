# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""History of the downloads of the release files and of the visits and clones of the repositories the user chooses, kept on this computer (traffic_engine.py does the work). Off by default.

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder."""
import re

from github_actions_monitor.families.declare import Command, Family, Raw, Route, Setting

REPO_RE = re.compile(r"^(?:[A-Za-z0-9-]{1,39}/)?[A-Za-z0-9._-]{1,100}\Z")


def _engine():
    from github_actions_monitor.families.traffic import traffic_engine as engine
    return engine


def _account():
    from github_actions_monitor.app import actions_monitor
    return actions_monitor.CHILD["account"] or ""


def _owner(config):
    from github_actions_monitor.app import toolconfig
    return toolconfig.github_owner(config)


def _report(request):
    return _engine().report(request.config, _owner(request.config), _account())


def _export(request):
    what = "assets" if request.query.get("what") == "assets" else "days"
    return Raw("text/csv; charset=utf-8", _engine().csv_text(what, _account()).encode("utf-8"))


def _cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    engine = _engine()
    config = toolconfig.raw_config()
    if ctx["action"] == "export":
        lines = engine.csv_text("days", _account()).splitlines()
        return {"ok": True, "csv": lines}, lines, 0
    out = engine.report(config, _owner(config), _account())
    lines = engine.text_lines(out) or [i18n.t("cli.traffic.none")]
    return out, lines, 0


def _tick(config, data):
    _engine().tick(config, _account())


def _s(key, kind, bounds=None, secure=False, unit=None):
    return Setting("traffic", "traffic", "traffic." + key, kind, bounds=bounds, restart=False, secure=secure, unit=unit)


FAMILY = Family(
    "traffic",
    defaults={"traffic": {"enabled": False, "repos": [], "views_clones": True, "repos_per_cycle": 2, "keep_days": 400}},
    settings=(_s("enabled", "bool", secure=True), _s("repos", "names", REPO_RE), _s("views_clones", "bool"), _s("repos_per_cycle", "int", (1, 10)), _s("keep_days", "int", (30, 3650), unit="d")),
    settings_tabs=(("traffic", "posture"),),
    routes=(Route("GET", "/api/traffic", _report, "history kept on this computer of the downloads of release files and of the visits and clones of the chosen repositories, with what could not be read"),
            Route("GET", "/api/traffic/export", _export, "that history as CSV (?what=days, one line per repository and day; ?what=assets, one line per release file and day on which its count changed)")),
    commands=(Command("traffic", _cli, "cli.traffic.help", words=("status", "export")),),
    ticks=(_tick,),
)
