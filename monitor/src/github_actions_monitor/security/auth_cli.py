# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Recovery of the team mode from the console of the computer that runs the monitor (the only place that can do it).

    python -m github_actions_monitor.security.auth_cli list
    python -m github_actions_monitor.security.auth_cli create-admin NAME [--password-env VAR]
    python -m github_actions_monitor.security.auth_cli reset-password NAME [--password-env VAR]
    python -m github_actions_monitor.security.auth_cli revoke NAME

A password is asked on the console (it is not shown) or read from the environment variable you NAME with --password-env; it never travels in the command line, so it never
reaches the list of processes or the history of the shell. Nothing here prints a password, a hash or a token. Use it when the only administrator forgot the password, or to add
an administrator without the page. It writes to the same storage as the server and to the same audit.
"""
import argparse
import getpass
import os
import sys

from github_actions_monitor.security import auth


def _password(args):
    if args.password_env:
        value = os.environ.get(args.password_env, "")
        if not value:
            raise SystemExit(f"the variable {args.password_env} is empty or not set")
        return value
    first = getpass.getpass("Password: ")
    if getpass.getpass("Again: ") != first:
        raise SystemExit("the two passwords differ")
    return first


def main(argv=None, storage=None):
    parser = argparse.ArgumentParser(prog="auth_cli", description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("list", "create-admin", "reset-password", "revoke"))
    parser.add_argument("name", nargs="?", default="")
    parser.add_argument("--password-env", default="", help="name of the environment variable that holds the password (never the password itself)")
    args = parser.parse_args(argv)
    from github_actions_monitor.app import toolconfig
    config = toolconfig.raw_config()
    cfg = auth.settings(config)
    storage = storage or auth.get_storage(config)
    if args.command == "list":
        for user in auth.list_users(storage):
            print(f"{user['username']}\t{user['role']}\t{'active' if user['active'] else 'inactive'}\t{','.join(user['accounts'])}")
        return 0
    if not args.name:
        parser.error("a user name is needed")
    if args.command == "revoke":
        print(f"{auth.revoke_sessions(storage, auth.clean_username(args.name))} session(s) ended")
        auth.audit(cfg, "cli_revoke", args.name, address="console")
        return 0
    password = _password(args)
    if args.command == "create-admin":
        user, code = auth.create_user(storage, args.name, password, "admin", None, cfg["min_length"])
    else:
        user, code = auth.update_user(storage, args.name, password=password, active=True, minimum=cfg["min_length"])
    auth.audit(cfg, "cli_" + args.command.replace("-", "_"), args.name, "admin" if user else "", "console", "", "ok" if user else "denied", code)
    if code:
        print(f"not done: {code}", file=sys.stderr)
        return 1
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
