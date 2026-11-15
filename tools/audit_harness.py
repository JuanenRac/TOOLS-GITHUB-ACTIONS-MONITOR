#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/audit_harness.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A supervisor in team mode with several accounts, ready in a few seconds, for whoever reviews the product (and for the tests that need the same).

    python tools/audit_harness.py [--check] [--keep]

It starts, in a temporary folder that is removed at the end, the supervisor with THREE accounts (`alpha`, `beta` and `default`, each one a stand-in monitor that answers the same routes and says
which account it is), the team mode with FOUR users (`admin`: administrator of everything; `maintainer`: maintainer of `alpha` only; `viewer`: viewer of `beta` only; `inactive`: a viewer of `beta` whose user
is switched off) and a fake `gh` that answers nothing, so that nothing leaves this computer and no token is needed. All the passwords are the same disposable one, printed on screen.

Without options it prints the address and the users and waits for Enter (or Ctrl-C). With `--check` it asks the routes that decide the isolation of the accounts, prints what each user gets
(`ok` or `WRONG`) and exits with 0 when every answer is the expected one and 1 otherwise: the table of the reproductions of the independent review, in one minute.

The stand-in monitors and the harness are the ones of `monitor/tests/test_170.py` and `monitor/tests/test_auth.py`; nothing here reaches GitHub, a real account or the installation of the person who runs it.
"""
import argparse
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "monitor" / "src"))
sys.path.insert(0, str(ROOT / "monitor" / "tests"))

PASSWORD = "audit-only password 1"
USERS = (("admin", "admin", None), ("maintainer", "maintainer", ["alpha"]), ("viewer", "viewer", ["beta"]), ("inactive", "viewer", ["beta"]))


def request(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as answer:      # noqa: S310 - 127.0.0.1 only
            return answer.status, json.loads(answer.read().decode("utf-8") or "{}"), dict(answer.headers)
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8") or "{}")
        except ValueError:
            body = {}
        return error.code, body, dict(error.headers)


def sign_in(base, name):
    status, body, head = request(base + "/api/auth/login", {"Content-Type": "application/json"}, json.dumps({"username": name, "password": PASSWORD}).encode())
    if status != 200:
        return None
    return {"Cookie": head["Set-Cookie"].split(";")[0], "X-CSRF-Token": body["csrf"]}


def expected_table():
    """(user, path, the statuses that are right)."""
    return (("admin", "/api/echo?account=alpha", (200,)), ("admin", "/api/echo?account=beta", (200,)),
            ("maintainer", "/api/echo?account=alpha", (200,)), ("maintainer", "/api/echo?account=beta", (403,)),
            ("maintainer", "/api/echo?account=alpha&account=beta", (400, 403)), ("viewer", "/api/echo?account=beta", (200,)),
            ("viewer", "/api/echo?account=alpha", (403,)), ("viewer", "/api/echo?account=beta&account=alpha", (400, 403)),
            ("maintainer", "/api/accounts/beta/status", (403,)), ("viewer", "/api/accounts/beta/status", (200,)),
            ("inactive", "/api/echo?account=beta", (401,)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Supervisor with three accounts, four users and no GitHub, for review.")
    ap.add_argument("--check", action="store_true", help="ask the routes of the isolation of the accounts, print the table and exit 0 or 1")
    args = ap.parse_args(argv)
    import test_170 as t170
    from github_actions_monitor.accounts import accounts, accounts_supervisor as sup
    from github_actions_monitor.security import auth, auth_http, localguard
    from github_actions_monitor.storage import factory
    tmp = tempfile.TemporaryDirectory()
    base_dir = Path(tmp.name)
    fake_bin = base_dir / "bin"
    fake_bin.mkdir()
    gh = fake_bin / ("gh.cmd" if os.name == "nt" else "gh")
    gh.write_text("@echo off\r\necho [] \r\n" if os.name == "nt" else "#!/bin/sh\necho '[]'\n")
    gh.chmod(0o755)
    patches = [mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(base_dir / "accounts"), "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")}),
               mock.patch.object(sup.Handler, "team_config", staticmethod(lambda: {"auth": {"enabled": True}, "session_guard": False}))]
    for patcher in patches:
        patcher.start()
    supervisor = server = None
    storage = None
    try:
        for name in ("alpha", "beta", "default"):
            accounts.create_account(name, name + "-owner")
        supervisor = sup.Supervisor(command_for=t170.stub_command(base_dir, "ok"), port_start=t170.unused_stretch())
        supervisor.sync()
        for _ in range(40):
            supervisor.check()
            if all(c.health is not None for c in supervisor.children.values()):
                break
            time.sleep(0.25)
        sup.SUPERVISOR["obj"] = supervisor
        storage = factory.create_storage({"backend": "file", "path": str(base_dir / "data")})
        auth.use_storage(storage)
        auth.AUDIT_FILE = base_dir / "audit.jsonl"
        for name, role, assigned in USERS:
            auth.create_user(storage, name, PASSWORD, role, assigned)
        auth.update_user(storage, "inactive", active=False)      # the fourth user is switched off: it must not get in at all
        auth_http.forget_cache()
        localguard.reset_limits()
        server = ThreadingHTTPServer(("127.0.0.1", 0), sup.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        print(f"supervisor: {base}\naccounts: alpha, beta, default\nusers (password {PASSWORD!r}): " + ", ".join(f"{n} ({r}{', ' + '/'.join(a) if a else ''})" for n, r, a in USERS))
        if not args.check:
            input("Enter to stop... ")
            return 0
        wrong = 0
        sessions = {name: sign_in(base, name) for name, _, _ in USERS}
        for user, path, good in expected_table():
            status = request(base + path, sessions[user] or {})[0] if sessions[user] else 401
            mark = "ok" if status in good else "WRONG"
            wrong += mark != "ok"
            print(f"  {mark:5} {user:11} GET {path:46} -> {status} (expected {'/'.join(map(str, good))})")
        print("AUDIT_HARNESS=" + ("PASS" if not wrong else f"FAIL {wrong}"))
        return 1 if wrong else 0
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if supervisor:
            supervisor.stop()
        sup.SUPERVISOR.update(obj=None)
        if storage:
            auth.use_storage(None)
            auth.AUDIT_FILE = None
            storage.close()
        localguard.configure(False)
        for patcher in patches:
            patcher.stop()
        tmp.cleanup()


if __name__ == "__main__":
    sys.exit(main())
