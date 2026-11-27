# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Compliance: the strict read-only mode and the network policy, the compliance report, retention by category and legal hold, signed checkpoints and export of the log of actions.

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder. Everything is off by default."""
import re
import time

from github_actions_monitor.families.declare import Check, Command, Egress, Family, Option, Route, Setting
from github_actions_monitor.security import envguard

HOST_RE = re.compile(r"^(program:[a-z0-9_.-]{1,40}|(\*\.)?[a-z0-9.-]{1,200}|[0-9a-f:.]{2,45})\Z")
TEXT_RE = re.compile(r"^[^\x00-\x1f]{0,400}\Z")
URL_RE = re.compile(r"^(https?://[^\s@]{1,400})?\Z")
SERVER_RE = re.compile(r"^[A-Za-z0-9.:-]{0,200}\Z")


def _report(request):
    from github_actions_monitor.reporting import compliance_report
    return compliance_report.report(request.config)


def _state(request):
    from github_actions_monitor.integrations import compliance_audit_export as export
    from github_actions_monitor.security import compliance_guard
    from github_actions_monitor.storage import compliance_retention
    state = export.load_state()
    state.pop("cursor", None)
    return {"restrictions": compliance_guard.status(), "retention": compliance_retention.policy(request.config),
            "export": dict(state, enabled=export.active(request.config), lag=export.lagging(request.config, state))}


def _compliance_cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.reporting import compliance_report
    found = compliance_report.report(toolconfig.raw_config())
    return found, compliance_report.as_text(found, i18n.t), 0


def _audit_cli(ctx):
    from github_actions_monitor import i18n
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.integrations import compliance_audit_export as export
    from github_actions_monitor.security import audit_log, compliance_checkpoints as marks
    config = toolconfig.raw_config()
    action = ctx["action"] or "verify"
    args = ctx["args"]
    if action == "checkpoint":
        entries = marks.entries(audit_log.path())
        made = marks.mark(audit_log.path(), entries[-1].get("hash") if entries else "")
        return {"ok": bool(made)}, [i18n.t("cli.compliance.marked" if made else "cli.compliance.not_marked")], 0 if made else 1
    if action == "purge":
        if args.older_than_days < 1:
            return {"ok": False, "reason": "days"}, [i18n.t("cli.compliance.need_days")], 2
        out = marks.purge(config, time.time() - args.older_than_days * 86400, dry_run=ctx["dry_run"])
        text = i18n.t("cli.compliance.purge_refused", reason=out["reason"]) if out["reason"] else i18n.t("cli.compliance.would_purge" if ctx["dry_run"] else "cli.compliance.purged", files=out["files"], entries=out["entries"])
        return dict(out, ok=not out["reason"]), [text], 1 if out["reason"] else 0
    if action == "export":
        state = export.run(config)
        state.pop("cursor", None)
        bad = bool(state["last_error"]) or not export.active(config)
        return dict(state, ok=not bad), [i18n.t("cli.compliance.export", sent=state["sent"], waiting=state["backlog_bytes"], error=state["last_error"] or "-")], 1 if bad else 0
    found = marks.verify(from_entry=max(1, args.audit_from))
    key = "cli.compliance.chain_ok" if found["ok"] else "cli.compliance.chain_broken"
    return found, [i18n.t(key, entries=found["entries"], checkpoints=found["checkpoints"], gaps=found["gaps"], bad=len(found["bad_checkpoints"]))], 0 if found["ok"] else 1


def _alerts(config, account):
    from github_actions_monitor import i18n
    from github_actions_monitor.integrations import compliance_audit_export as export
    state = export.load_state()
    if not export.active(config) or not export.lagging(config, state):
        return []
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(state["at"] or 0))
    return [{"id": export.ALERT_CODE, "code": export.ALERT_CODE, "level": "warning", "sentinel": "ci", "account_id": account, "repo": "", "title": i18n.t("ui.compliance.alert_lag", waiting=state["backlog_bytes"], lost=state["lost"]),
             "details": {"backlog_bytes": state["backlog_bytes"], "lost": state["lost"]}, "created_at": stamp}]


def _tick(config, data):
    from github_actions_monitor.integrations import compliance_audit_export
    from github_actions_monitor.security import compliance_guard
    from github_actions_monitor.storage import compliance_retention
    compliance_guard.arm(config)      # a restriction that was switched on while the monitor runs holds from the next cycle; relaxing one needs a restart
    compliance_audit_export.tick(config, data)
    compliance_retention.tick(config)


def _check_strict(config):
    from github_actions_monitor.security import compliance_guard
    strict = compliance_guard.wanted(config)[0]
    return ("ok", "enforced" if compliance_guard.status()["read_only_strict"] else "set, applies when the process starts") if strict else ("ok", "off")


def _check_egress(config):
    from github_actions_monitor.ops import egress
    from github_actions_monitor.security import compliance_guard
    policy = compliance_guard.wanted(config)[1]
    bad = compliance_guard.violations(config, egress.table(config))
    return ("fail", "; ".join(f"{ident} {host}" for ident, host in bad[:6])) if bad else ("ok", policy)


def _check_support(config):
    from github_actions_monitor.app import updatecheck
    from github_actions_monitor.tool_version import TOOL_VERSION
    from github_actions_monitor.util import paths
    release = updatecheck._load(paths.place("update_check.json")).get("release")
    latest = str(release.get("tag", "")).lstrip("v") if isinstance(release, dict) else ""
    if latest and updatecheck.is_newer(latest, TOOL_VERSION):
        return ("warn", f"{TOOL_VERSION} is not supported any more: {latest} is out")
    return ("ok", "latest" if latest else "no release read")


def _check_retention(config):
    from github_actions_monitor.storage import compliance_retention, retention
    if retention.held(config):
        return ("ok", "legal hold: nothing is removed")
    names = compliance_retention.without_policy(config)
    return ("ok", "no age limit: " + ", ".join(names) if names else "every category has a limit")


def _check_chain(config):
    from github_actions_monitor.security import compliance_checkpoints
    found = compliance_checkpoints.verify()
    return ("ok", f"{found['entries']} lines") if found["ok"] else ("fail", f"broken (line {found['broken_at']}, gaps {found['gaps']}, checkpoints {len(found['bad_checkpoints'])})")


def _check_export(config):
    from github_actions_monitor.integrations import compliance_audit_export as export
    if not export.settings(config)["enabled"]:
        return ("ok", "off")
    if not export.active(config):
        return ("warn", "on but without a destination")
    state = export.load_state()
    if export.lagging(config, state):
        return ("warn", f"{export.ALERT_CODE}: {state['backlog_bytes']} bytes waiting, lost {state['lost']}")
    return ("warn", state["last_error"]) if state["last_error"] else ("ok", f"{state['sent']} lines sent")


def _hosts(config):
    from github_actions_monitor.integrations import compliance_audit_export
    return compliance_audit_export.hosts(config)


def _s(block, key, kind, bounds=None, secure=True, unit=None, restart=False):
    return Setting("compliance", block, key, kind, bounds=bounds, restart=restart, secure=secure, unit=unit)


_LIMITS, _KEEP, _EXPORT = "compliance_limits", "compliance_retention", "audit_export"

FAMILY = Family(
    "compliance",
    defaults={"security": {"read_only_strict": False, "egress_policy": "default", "egress_allow": []},
              "retention": {"legal_hold": False, "audit_days": 0, "reports_days": 0, "ai_log_days": 0, "backups_days": 0},
              "audit_checkpoints": {"enabled": False},
              "audit_export": {"enabled": False, "target": "file", "path": "", "host": "", "port": 6514, "tls": True, "ca_file": "", "url": "", "token_env": "", "batch": 100, "spool_mb": 50,
                               "max_mb": 50, "allow_private_targets": False}},
    settings=(_s(_LIMITS, "security.read_only_strict", "bool", restart=True), _s(_LIMITS, "security.egress_policy", "enum", ("default", "github_only", "none"), restart=True),
              _s(_LIMITS, "security.egress_allow", "names", HOST_RE, restart=True), _s(_LIMITS, "audit_checkpoints.enabled", "bool"),
              _s(_KEEP, "retention.legal_hold", "bool"), _s(_KEEP, "retention.audit_days", "int", (0, 3650), unit="d"), _s(_KEEP, "retention.reports_days", "int", (0, 3650), unit="d"),
              _s(_KEEP, "retention.ai_log_days", "int", (0, 3650), unit="d"), _s(_KEEP, "retention.backups_days", "int", (0, 3650), unit="d"),
              _s(_EXPORT, "audit_export.enabled", "bool"), _s(_EXPORT, "audit_export.target", "enum", ("file", "syslog", "http")), _s(_EXPORT, "audit_export.path", "text", TEXT_RE),
              _s(_EXPORT, "audit_export.host", "text", SERVER_RE), _s(_EXPORT, "audit_export.port", "int", (1, 65535)), _s(_EXPORT, "audit_export.tls", "bool"),
              _s(_EXPORT, "audit_export.ca_file", "text", TEXT_RE), _s(_EXPORT, "audit_export.url", "text", URL_RE), _s(_EXPORT, "audit_export.token_env", "text", re.compile(r"^(?!(?:" + "|".join(envguard.SYSTEM_NAMES + envguard.SECRET_NAMES) + r")\Z)(?:[A-Z_][A-Z0-9_]{0,63})?\Z")),
              _s(_EXPORT, "audit_export.batch", "int", (1, 1000)), _s(_EXPORT, "audit_export.spool_mb", "int", (1, 10000), unit="MB"),
              _s(_EXPORT, "audit_export.max_mb", "int", (1, 1000), unit="MB"), _s(_EXPORT, "audit_export.allow_private_targets", "bool")),
    settings_tabs=(("compliance", "extci"),),
    routes=(Route("GET", "/api/compliance/report", _report, "which guarantees this installation offers, each line checked or only declared; not a certification, no secret and no path", role="admin"),
            Route("GET", "/api/compliance/state", _state, "the restrictions in force (strict read-only, network policy), the retention of each category and the state of the export of the log of actions", role="admin")),
    commands=(Command("compliance", _compliance_cli, "cli.compliance.help", words=("report",)),
              Command("audit", _audit_cli, "cli.compliance.help_audit", words=("verify", "checkpoint", "purge", "export"),
                      options=(Option("--audit-from", "cli.compliance.help_from", {"type": int, "default": 1, "metavar": "N"}),
                               Option("--older-than-days", "cli.compliance.help_older", {"type": int, "default": 0, "metavar": "DAYS"})))),
    ticks=(_tick,),
    alerts=_alerts,
    egress=(Egress("audit_export", (), "audit_export.enabled", hosts_from=_hosts),),
    checks=(Check("compliance_strict", _check_strict, "python bin/monitor_cli.py compliance report"), Check("compliance_egress", _check_egress, "python bin/monitor_cli.py doctor --egress"),
            Check("compliance_support", _check_support, "python bin/monitor_cli.py update check"), Check("compliance_retention", _check_retention, "python bin/monitor_cli.py compliance report"),
            Check("compliance_chain", _check_chain, "python bin/monitor_cli.py audit verify"), Check("compliance_export", _check_export, "python bin/monitor_cli.py audit export")),
)
