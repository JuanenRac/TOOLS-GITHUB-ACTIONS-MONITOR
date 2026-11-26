# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command `plugin` of bin/monitor_cli.py: list, validate, pack, verify, init (a template), install, enable, disable, uninstall, audit. No network; the monitor never signs."""
import shutil
from pathlib import Path

from github_actions_monitor import i18n
from github_actions_monitor.app import toolconfig
from github_actions_monitor.plugins import plugin_host as host
from github_actions_monitor.plugins import plugin_package as packages
from github_actions_monitor.security import audit_log, keyring
from github_actions_monitor.util import paths

OK, USAGE, DEGRADED = 0, 1, 4
TEMPLATE = ("assets", "plugin_template")


def _usage(message):
    return {"ok": False, "error": message}, [message], USAGE


def _keys(args):
    chosen = getattr(args, "keyring", "")
    return keyring.all_keys(chosen) if chosen else host.user_keys()


def _record(config, action, target):
    try:
        audit_log.record(config, action, user="cli", target=target)
    except Exception:      # noqa: BLE001 - the log of actions never stops the command
        pass


def _declares(found):
    m = found["manifest"]
    head = i18n.t("cli.plugins.declares", name=m["name"], version=m["version"], author=m["author"], permissions=", ".join(m["permissions"]) or "-")
    return [head, *[f"  {p}" for p in m["get_paths"]], i18n.t("cli.plugins.signed_by", key=found["key_id"], fingerprint=found["fingerprint"]), i18n.t("ui.plugins.signed_not_safe")]


def _line(row):
    return i18n.t("cli.plugins.line", name=row["name"], version=row["version"], trust=row["trust"], state=row["state"], isolation=i18n.t("ui.plugins.isolation_" + row["isolation"]))


def init(folder):
    """A copy of the template of a plugin with its test, in a new folder."""
    target = Path(folder)
    if target.exists() and any(target.iterdir()):
        return _usage(i18n.t("cli.plugins.not_empty"))
    shutil.copytree(paths.ROOT.joinpath(*TEMPLATE), target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    return {"ok": True, "folder": str(target)}, [i18n.t("cli.plugins.made", folder=str(target))], OK


def run(ctx):
    args, action = ctx["args"], ctx.get("action") or "list"
    path, name = getattr(args, "path", ""), getattr(args, "name", "")
    config = toolconfig.raw_config()
    try:
        if action == "list":
            out = host.catalogue(config)
            lines = [_line(row) for row in out["plugins"]] or [i18n.t("cli.plugins.none")]
            lines += [f"pip: {c['distribution']} {c['name']} {c['package']}".rstrip() for c in out["candidates"]]
            return out, lines, OK
        if action == "audit":
            rows = packages.audit(_keys(args))
            lines = [f"{r['name']} {r['version']} {r['fingerprint']} {r['state']}" for r in rows] or [i18n.t("cli.plugins.none")]
            good = all(r["state"] == "ok" for r in rows)
            return {"ok": good, "plugins": rows}, lines, OK if good else DEGRADED
        if action in ("enable", "disable", "uninstall") and not name:
            return _usage(i18n.t("cli.plugins.need_name"))
        if action in ("enable", "disable"):
            if name in host.official():
                if action == "disable":
                    return _usage(i18n.t("cli.plugins.official_setting", name=name))
            else:
                packages.set_enabled(name, action == "enable")
            if action == "enable":
                host.resume(name)
            _record(config, "plugin_enable", f"{name} {action}")
            return {"ok": True, "name": name}, [i18n.t("cli.plugins.done", name=name)], OK
        if action == "uninstall":
            done = packages.uninstall(name)
            host.save_state(name, None)
            _record(config, "plugin_uninstall", name)
            return done, [i18n.t("cli.plugins.done", name=name)], OK if done["removed"] else DEGRADED
        if not path:
            return _usage(i18n.t("cli.plugins.need_path"))
        if action == "init":
            return init(path)
        if action == "validate":
            report = packages.validate(path)
            lines = [i18n.t("cli.plugins.valid" if report["ok"] else "cli.plugins.invalid")] + report["errors"] + report["warnings"]
            return report, lines, OK if report["ok"] else DEGRADED
        if action == "pack":
            out = getattr(args, "out", "")
            if not out:
                report = packages.validate(path)
                if not report["ok"]:
                    return report, report["errors"], DEGRADED
                out = f"{report['manifest']['name']}-{report['manifest']['version']}.zip"
            digest = packages.pack(path, out)
            return {"ok": True, "package": out, "sha256": digest}, [i18n.t("cli.plugins.packed", package=out, sha=digest)], OK
        if action == "verify":
            found = packages.inspect(path, _keys(args))
            return dict(found, ok=True), _declares(found), OK
        if action == "install":
            fingerprint = getattr(args, "fingerprint", "")
            if not fingerprint:      # the first step shows what would be installed; the second one repeats the fingerprint of the key
                found = packages.inspect(path, _keys(args))
                return dict(found, ok=False, confirm=found["fingerprint"]), _declares(found) + [i18n.t("cli.plugins.confirm", fingerprint=found["fingerprint"])], DEGRADED
            done = packages.install(path, _keys(args), fingerprint)
            _record(config, "plugin_install", f"{done['name']} {done['version']}")
            return dict(done, ok=True), [i18n.t("cli.plugins.installed", name=done["name"])], OK
    except packages.PackageError as error:
        return {"ok": False, "reason": error.code}, [i18n.t("cli.plugins.refused", code=error.code, why=str(error)[:160])], DEGRADED
    except (OSError, keyring.KeyringError) as error:
        return _usage(str(error)[:160])
    return _usage(i18n.t("cli.plugins.need_path"))
