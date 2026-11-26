# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The commands `keyring list|add|revoke|verify` and `verify-release` of bin/monitor_cli.py: public keys only, no network."""
from pathlib import Path

from github_actions_monitor import i18n
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
            lines = [i18n.t("cli.supply_key_line", id=row["id"], scopes=",".join(row["scopes"]), fingerprint=row["fingerprint"],
                            state=i18n.t("cli.supply_revoked" if row["revoked"] else "cli.supply_active")) for row in rows]
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
        if action == "verify":
            if not args.document:
                return _usage(i18n.t("cli.supply_need_document"))
            result, key_id = keyring.verify_file(args.document, scope=args.key_scope or "release", keys=keyring.all_keys(keyring_file()))
            return {"result": result, "key": key_id}, [i18n.t("cli.supply_result", result=result, key=key_id or "-")], OK if result == keyring.VALID else DEGRADED
    except keyring.KeyringError as error:
        return _usage(i18n.t("cli.supply_error", code=error.code))
    return _usage(i18n.t("cli.supply_need_add"))


def verify_release_command(ctx):
    folder = ctx["args"].folder
    if not folder or not Path(folder).is_dir():
        return _usage(i18n.t("cli.supply_need_folder"))
    report = release_verify.verify_release(folder)
    lines = [i18n.t("cli.supply_signature", result=report["signature"])]
    lines += [f"  {name}: {state}" for name, state in report["files"].items()]
    lines.append(i18n.t("cli.supply_release_ok" if report["ok"] else "cli.supply_release_bad"))
    return report, lines, OK if report["ok"] else DEGRADED
