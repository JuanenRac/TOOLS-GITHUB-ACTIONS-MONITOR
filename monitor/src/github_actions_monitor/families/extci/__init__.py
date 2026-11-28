# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""External sources of CI results, read only (integrations/external_ci/ does the work).

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder."""
import os
import re

from github_actions_monitor.families.declare import Check, Command, Egress, Family, Option, Route, Setting

LINE_RE = re.compile(r"^(buildbot|gitlab|jenkins|azure)(;[a-z_]{2,12}=[^;\s,]{1,200}){2,7}\Z")


def _engine():
    from github_actions_monitor.integrations.external_ci import extci_engine as engine
    return engine


def _status(request):
    return _engine().status(request.config)


def _log(request):
    found = _engine().log_of(request.config, request.query.get("source", ""), request.query.get("build", ""))
    return dict(found, ok=True) if found else (404, {"ok": False, "error": "no_log"})


def _probe(request):
    from github_actions_monitor.security import audit_log
    line = request.body.get("source")
    if not isinstance(line, str) or len(line) > 1500:
        return 400, {"ok": False, "reason": "format"}
    audit_log.note(line.split(";")[0][:20])
    return _engine().probe(request.config, line)


def _cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.cli import monitor_cli
    engine = _engine()
    config = toolconfig.raw_config()
    if ctx["action"] == "probe":
        line = ctx["args"].source
        if not line:
            raise monitor_cli.CliError(i18n.t("cli.extci.need_source"))
        out = engine.probe(config, line)
        text = i18n.t("cli.extci.seen", workflows=out["workflows"], builds=out["builds"], red=out["red"]) if out["ok"] else i18n.t("cli.extci.failed", reason=out["reason"])
        return out, [text], 0 if out["ok"] else 1
    if ctx["action"] == "status":      # the command line is not the running monitor: it makes one read of its own
        engine.refresh(config)
    out = engine.status(config)
    lines = [f"{row['state']:<10} {row['id']} {row['reason']}".rstrip() for row in out["sources"]] + [f"invalid    {row['line']} {row['reason']}" for row in out["invalid"]]
    worst = 1 if ctx["action"] == "status" and any(row["state"] in ("red", "degraded") for row in out["sources"]) else 0
    return out, lines or [i18n.t("cli.extci.none")], worst


def _tick(config, data):
    _engine().tick(config, data)


def _migration():
    from github_actions_monitor.storage import identity_migration
    return identity_migration


def _identity_tick(config, data):
    _migration().tick(config)


def _identity_cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    migration = _migration()
    config = toolconfig.raw_config()
    if ctx["action"] == "apply":
        out = migration.apply(config)
        return out, [i18n.t("cli.extci.identity_done", backup=out["backup"] or "-") if out["applied"] else i18n.t("cli.extci.identity_nothing")], 0
    out = migration.status(config)
    plan = out["plan"]
    lines = [i18n.t("cli.extci.identity_owner", owner=plan["owner"] or "-", was=plan["was"] or "-")]
    lines += [f"{row['action']:<10} {row['records']:>4}  {row['file']}" for row in plan["items"]] or ([] if out["pending"] else [i18n.t("cli.extci.identity_nothing")])
    return out, lines, 0


def _doctor_sources(config):
    """The external CI sources, with one read of each: off, what cannot be understood, what could not be read."""
    engine = _engine()
    if engine.settings(config)["enabled"] is not True:
        return ("ok", "off")
    engine.refresh(config)
    now = engine.status(config)
    bad = [f"{row['line']} {row['reason']}" for row in now["invalid"]] + [f"{row['id']} {row['reason']}" for row in now["sources"] if row["state"] == "degraded"]
    missing = sorted({s["token_env"] for s in engine.configured(config) if s.get("token_env") and not os.environ.get(s["token_env"])})
    bad += [f"{name} not set" for name in missing]
    return ("warn", "; ".join(bad[:4])) if bad else ("ok", f"{len(now['sources'])} sources")


def _doctor_identity(config):
    """A second owner among the accounts while sources.multi_owner is off, or saved data not yet brought to the identity of today."""
    from github_actions_monitor.accounts import accounts
    names = set(accounts.owners().values())
    if len(names) > 1 and not accounts.multi_owner_allowed():
        return ("warn", f"{len(names)} owners, sources.multi_owner off")
    todo = _migration().plan(config) if config.get("github_owner") else {"reason": ""}
    return ("warn", todo["reason"]) if todo["reason"] == "owner_changed" else ("ok", "")


def _hosts(config):
    return _engine().hosts(config)


def _active(config):
    return _engine().active(config)


def _s(key, kind, bounds=None, secure=False, unit=None):
    return Setting("extci", "external_ci", "external_ci." + key, kind, bounds=bounds, restart=False, secure=secure, unit=unit)


FAMILY = Family(
    "extci",
    defaults={"sources": {"multi_owner": False}, "external_ci": {"enabled": False, "sources": [], "refresh_seconds": 600, "timeout_s": 15, "max_bytes": 2000000, "allow_private_targets": False, "experimental": True,
                              "breaker": {"failures": 3}, "buildbot": {"max_builders": 50}, "gitlab": {"max_pipelines": 30}, "jenkins": {"enabled": False}, "azure": {"enabled": False},
                              "alert": {"enabled": True, "level": "error"}, "logs": {"enabled": False, "max_kb": 64, "tail_lines": 200, "keep_hours": 72}}},
    settings=(_s("enabled", "bool", secure=True), _s("sources", "names", LINE_RE, secure=True), _s("refresh_seconds", "int", (300, 86400), unit="s"), _s("timeout_s", "int", (2, 120), unit="s"),
              _s("max_bytes", "int", (10000, 50000000)), _s("allow_private_targets", "bool", secure=True), _s("experimental", "bool"), _s("breaker.failures", "int", (1, 20)),
              _s("buildbot.max_builders", "int", (1, 500)), _s("gitlab.max_pipelines", "int", (1, 200)), _s("jenkins.enabled", "bool", secure=True), _s("azure.enabled", "bool", secure=True),
              _s("alert.enabled", "bool"), _s("alert.level", "enum", ("error", "warning")), _s("logs.enabled", "bool", secure=True), _s("logs.max_kb", "int", (4, 1024)),
              _s("logs.tail_lines", "int", (10, 5000)), _s("logs.keep_hours", "int", (1, 720)),
              Setting("extci", "sources", "sources.multi_owner", "bool", restart=False, secure=True)),
    settings_tabs=(("extci", "outputs"),),
    routes=(Route("GET", "/api/external-ci/status", _status, "state of the external CI sources, what each says and why one could not be read"),
            Route("GET", "/api/external-ci/log", _log, "the bounded and redacted end of the log of a failed external build (external_ci.logs.enabled); ?source=&build=", role="maintainer"),
            Route("POST", "/api/external-ci/probe", _probe, "one read of a source line, nothing is saved", this_computer=True, audit="extci_probe", max_body=2048)),
    commands=(Command("external-ci", _cli, "cli.extci.help", words=("list", "status", "probe"), options=(Option("--source", "cli.extci.help_source", {"default": ""}),)),
              Command("identity", _identity_cli, "cli.extci.help_identity", words=("status", "plan", "apply"))),
    ticks=(_tick, _identity_tick),
    checks=(Check("extci", _doctor_sources, "python bin/monitor_cli.py external-ci status"), Check("extci_identity", _doctor_identity, "python bin/monitor_cli.py identity plan")),
    egress=(Egress("extci", (), "external_ci.enabled", hosts_from=_hosts, active=_active),),
)
