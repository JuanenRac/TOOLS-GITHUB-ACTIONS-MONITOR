# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The compliance report: which guarantees THIS installation offers, read from the configuration and from what runs. Standard library only.

Each line is {"id", "value", "evidence"}: "checked" = the monitor looked at the thing itself (the chain of the log, the hook that enforces a restriction, the files of the copies); "declared" = it is what
the configuration says, nothing more. It is not a certification of anything and says so. It holds no secret, no path and no name of a person or a repository; with the same installation and the same
clock the answer is the same."""
import os
import time
from pathlib import Path

NOTICE = "This report describes one installation. It is not a certification and claims none."


def _on(config, dotted):
    node = config
    for part in dotted.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def _yes(value):
    return "on" if value is True else "off"


def lines(config, now=None, sources=None):
    """[{"id", "value", "evidence"}] in a fixed order. `sources` replaces what is read from the machine (tests): chain, guard, backups, latest, container, root, schema, plugins."""
    config = config if isinstance(config, dict) else {}
    now = time.time() if now is None else now
    found = dict(gather(config, now), **(sources or {}))
    from github_actions_monitor.ops import egress
    from github_actions_monitor.security import compliance_checkpoints, compliance_guard
    from github_actions_monitor.storage import compliance_retention, retention
    from github_actions_monitor.tool_version import TOOL_VERSION
    out = []

    def add(ident, value, evidence="declared"):
        out.append({"id": ident, "value": value, "evidence": evidence})

    guard = found["guard"]
    network = _on(config, "listen.network") is True
    auth = _on(config, "auth.enabled") is True
    add("version", TOOL_VERSION, "checked")
    add("support", "latest_only" if not found["latest"] or found["latest"] == TOOL_VERSION else f"newer_published:{found['latest']}", "checked" if found["latest"] else "declared")
    add("edition", found["edition"], "checked")
    add("authentication", _yes(auth))
    add("identity_provider", "local_users" if auth else "none")
    add("network_mode", "network" if network else "this_computer_only")
    add("tls", "certificate_set" if _on(config, "listen.tls_cert") else "behind_proxy" if _on(config, "listen.trusted_proxy") is True else "off")
    wanted_strict, wanted_policy, _allow, _ghe = compliance_guard.wanted(config)
    add("read_only_strict", _yes(wanted_strict), "checked" if guard["read_only_strict"] == wanted_strict else "declared")
    add("egress_policy", wanted_policy, "checked" if guard["egress_policy"] == wanted_policy else "declared")
    rows = egress.table(config)
    add("destinations", ",".join(sorted(row["id"] for row in rows if row["active"])) or "none", "declared")
    bad = compliance_guard.violations(config, rows)
    add("egress_violations", ",".join(sorted({ident for ident, _host in bad})) or "none", "checked")
    kept = retention.effective(config)
    add("retention_events_days", kept["events_days"] if kept["enabled"] else 0)
    add("retention_without_limit", ",".join(compliance_retention.without_policy(config)) or "none")
    add("legal_hold", _yes(retention.held(config)))
    add("audit_log", _yes(_on(config, "audit_log.enabled") is not False))
    chain = found["chain"]
    add("audit_chain", "no_lines" if not chain["entries"] else "verified" if chain["ok"] else "broken", "checked")
    add("audit_checkpoints", _yes(compliance_checkpoints.enabled(config)))
    add("audit_export", _on(config, "audit_export.target") or "file" if _on(config, "audit_export.enabled") is True else "off")
    add("last_backup_days", found["backups"]["age_days"] if found["backups"]["age_days"] is not None else "none", "checked")
    add("backup_encryption", _yes(_on(config, "ops.backup.encrypt") is True), "checked" if found["backups"]["sealed"] else "declared")
    add("encryption_at_rest", "none")
    add("storage_schema", found["schema"], "checked")
    add("third_party_plugins", _yes(_on(config, "plugins.third_party.enabled") is True and _on(config, "plugins.enabled") is True))
    add("federation", "not_in_this_version", "checked")
    add("deployment", "container" if found["container"] else "service" if retention.service_mode(config) else "desktop", "checked")
    add("runs_as_root", "unknown" if found["root"] is None else "yes" if found["root"] else "no", "checked" if found["root"] is not None else "declared")
    add("profile", str(_on(config, "profile") or "default")[:30])
    return out


def gather(config, now):
    """What is looked at on the machine; each part that cannot be read answers as unknown, never as good."""
    from github_actions_monitor.security import compliance_checkpoints, compliance_guard
    out = {"guard": compliance_guard.status(), "container": Path("/.dockerenv").exists(), "root": (os.geteuid() == 0) if hasattr(os, "geteuid") else None, "latest": "", "edition": "complete"}
    try:
        out["chain"] = compliance_checkpoints.verify()
    except Exception:   # noqa: BLE001
        out["chain"] = {"ok": False, "entries": -1}
    try:
        from github_actions_monitor.ops import schedule
        copies = schedule.list_backups(config, None)
        out["backups"] = {"age_days": int(max(0, now - copies[0]["epoch"]) // 86400) if copies else None, "sealed": bool(copies and copies[0]["sealed"])}
    except Exception:   # noqa: BLE001
        out["backups"] = {"age_days": None, "sealed": False}
    try:
        from github_actions_monitor.storage import runtime
        storage, _account = runtime.process_storage(None)
        out["schema"] = f"{storage.backend}:{storage.schema_version()}" if hasattr(storage, "schema_version") else "files"
    except Exception:   # noqa: BLE001
        out["schema"] = "unknown"
    try:
        from github_actions_monitor.app import updatecheck
        from github_actions_monitor.util import paths
        release = updatecheck._load(paths.place("update_check.json")).get("release")
        out["latest"] = str(release.get("tag", "")).lstrip("v") if isinstance(release, dict) else ""
    except Exception:   # noqa: BLE001
        out["latest"] = ""
    return out


def report(config, now=None, sources=None):
    now = time.time() if now is None else now
    return {"schema": 1, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "notice": NOTICE, "lines": lines(config, now, sources)}


def as_text(found, translate):
    """The report as lines of text in the language of `translate` (key -> text)."""
    out = [translate("ui.compliance.notice"), found["at"]]
    for row in found["lines"]:
        out.append(f"[{translate('ui.compliance.evidence_' + row['evidence'])}] {translate('ui.compliance.line_' + row['id'])}: {row['value']}")
    return out


LINE_IDS = ("version", "support", "edition", "authentication", "identity_provider", "network_mode", "tls", "read_only_strict", "egress_policy", "destinations", "egress_violations",
            "retention_events_days", "retention_without_limit", "legal_hold", "audit_log", "audit_chain", "audit_checkpoints", "audit_export", "last_backup_days", "backup_encryption",
            "encryption_at_rest", "storage_schema", "third_party_plugins", "federation", "deployment", "runs_as_root", "profile")
