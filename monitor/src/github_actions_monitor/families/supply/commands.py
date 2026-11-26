# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The commands `keyring list|add|revoke|verify` and `verify-release` of bin/monitor_cli.py: public keys only, no network."""
import tempfile
from datetime import date
from pathlib import Path

from github_actions_monitor import families, i18n
from github_actions_monitor.app import toolconfig
from github_actions_monitor.families.supply import installed
from github_actions_monitor.security import keyring, release_verify
from github_actions_monitor.util import paths

OK, USAGE, DEGRADED = 0, 1, 4


def keyring_file():
    return paths.place("keyring.json")


def _usage(message):
    return {"ok": False, "error": message}, [message], USAGE


def _rows():
    return [dict(key, fingerprint=keyring.fingerprint(key["public"]), builtin=key["id"] in {k["id"] for k in keyring.builtin_keys()}) for key in keyring.all_keys(keyring_file())]


def keyring_command(ctx):
    args, action = ctx["args"], ctx.get("action") or "list"
    try:
        if action == "list":
            rows = _rows()
            soon = keyring.expiring(keyring.all_keys(keyring_file()), date.today())
            lines = [i18n.t("cli.supply_key_line", id=row["id"], scopes=",".join(row["scopes"]), fingerprint=row["fingerprint"],
                            state=i18n.t("cli.supply_revoked" if row["revoked"] else "cli.supply_active")) for row in rows]
            lines += [i18n.t("cli.supply_expires_soon", id=key_id, days=days) for key_id, days in soon]
            return {"keys": rows}, lines, OK
        if action == "add":
            if not (args.key_id and args.public_key and args.key_scope):
                return _usage(i18n.t("cli.supply_need_add"))
            entry = keyring.add_key(keyring_file(), args.key_id, args.public_key, [args.key_scope], expires=args.expires)
            return {"ok": True, "key": entry}, [i18n.t("cli.supply_added", id=entry["id"], fingerprint=keyring.fingerprint(entry["public"]))], OK
        if action == "revoke":
            if not args.key_id:
                return _usage(i18n.t("cli.supply_need_id"))
            entry = keyring.revoke_key(keyring_file(), args.key_id)
            return {"ok": True, "key": entry}, [i18n.t("cli.supply_revoked_done", id=entry["id"])], OK
        if action == "check-rotation":
            if not args.document:
                return _usage(i18n.t("cli.supply_need_document"))
            report = keyring.verify_rotation(args.document, keys=keyring.all_keys(keyring_file()))
            return report, [i18n.t("cli.supply_rotation", result=report["result"], key=report["new"] or "-")], OK if report["result"] == keyring.VALID else DEGRADED
        if action == "verify":
            if not args.document:
                return _usage(i18n.t("cli.supply_need_document"))
            result, key_id = keyring.verify_file(args.document, scope=args.key_scope or "release", keys=keyring.all_keys(keyring_file()))
            return {"result": result, "key": key_id}, [i18n.t("cli.supply_result", result=result, key=key_id or "-")], OK if result == keyring.VALID else DEGRADED
    except keyring.KeyringError as error:
        return _usage(i18n.t("cli.supply_error", code=error.code))
    return _usage(i18n.t("cli.supply_need_add"))


def verify_release_command(ctx):
    args = ctx["args"]
    if args.fetch:
        if families.block(toolconfig.raw_config(), "ops").get("verify_release", {}).get("fetch") is not True:
            return _usage(i18n.t("cli.supply_fetch_off"))
        with tempfile.TemporaryDirectory(prefix="verify_release_") as folder:
            try:
                installed.fetch(folder)
            except (OSError, ValueError, RuntimeError) as error:
                return {"ok": False, "error": str(error)[:100]}, [i18n.t("cli.supply_fetch_failed", why=str(error)[:100])], DEGRADED
            return _check(folder, args.installed, args.attestations)
    if not args.folder or not Path(args.folder).is_dir():
        return _usage(i18n.t("cli.supply_need_folder"))
    return _check(args.folder, args.installed, args.attestations)


def doctor_release(folder):
    """`doctor --verify-release DIR`: the folder of the release, its signature and this installation against its bill of materials."""
    if not Path(folder).is_dir():
        return _usage(i18n.t("cli.supply_need_folder"))
    return _check(folder, True, False)


def _check(folder, compare, attest):
    report = release_verify.verify_release(folder)
    lines = [i18n.t("cli.supply_signature", result=report["signature"])]
    lines += [f"  {name}: {state}" for name, state in report["files"].items()]
    ok = report["ok"]
    lines.append(i18n.t("cli.supply_release_ok" if ok else "cli.supply_release_bad"))
    if compare:
        if ok:      # a bill of materials is only believed when the signature of the project covers it
            report["installed"] = found = installed.compare_installed(folder)
            if found["ok"]:
                lines.append(i18n.t("cli.supply_installed_ok", count=found["checked"]))
            else:
                lines.append(i18n.t("cli.supply_installed_bad", changed=len(found["changed"]), missing=len(found["missing"]), why=found["reason"] or "-"))
                lines += [f"  {name}" for name in (found["changed"] + found["missing"])[:20]]
            ok = ok and found["ok"]
    if attest:
        report["attestation"] = installed.attestation(folder)
        lines.append(i18n.t("cli.supply_attestation", result=report["attestation"]))
        ok = ok and report["attestation"] != "failed"
    return report, lines, OK if ok else DEGRADED
