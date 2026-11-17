#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E2 - the team mode in a container: the first administrator comes from the environment (name) and a secret file (password), a second start needs neither, a start without any
administrator stops and says how to make one, wrong passwords lock the account, and the session cookie is HttpOnly and SameSite=Strict."""
import secrets
import sys

import audit_lib as lib

JSON = {"Content-Type": "application/json", "Host": "127.0.0.1:8765"}


def login(token, user, password, headers=None):
    import json
    head = dict(JSON, **{"X-Monitor-Access": token}, **(headers or {}))
    return lib.http_request(8765, "POST", "/api/auth/login", head, json.dumps({"username": user, "password": password}))


def body(s):
    image = s.image()
    mounts, env, _gh = s.login_files()
    password = s.secret("audit-pass-" + secrets.token_hex(6), "admin-password")
    pw_file = s.file("secrets/admin_pw", password)
    config, data = s.volume("config"), s.volume("data")
    base = ["%s:/config" % config, "%s:/data" % data] + mounts
    team = dict(env, MONITOR_TEAM_MODE="1")

    # 1. the first start with MONITOR_ADMIN_USER and a password FILE (the way the guide says for a container)
    first = dict(team, MONITOR_ADMIN_USER="ops", MONITOR_ADMIN_PASSWORD_FILE="/run/secrets/admin_pw")
    name, code, out = s.service("first", image, base + ["%s:/run/secrets/admin_pw:ro" % pw_file], first, ports=["127.0.0.1:8765:8765"])
    if not s.check("the team mode starts with the first administrator from the environment", code == 0 and s.wait_healthy(name, 180), s.logs(name)[-1500:]):
        return
    logs = s.logs(name)
    s.check("the password is not in the log", password not in logs, "")
    token = s.read_token(name)
    answer = login(token, "ops", password)
    parsed = lib.jbody(answer) or {}
    s.check("the administrator signs in with that password", answer["status"] == 200 and parsed.get("ok") is True and parsed.get("role") == "admin", "%s %s" % (answer["status"], answer["body"][:300]))
    cookie = lib.header(answer, "Set-Cookie")
    s.check("the session cookie is HttpOnly and SameSite=Strict", "HttpOnly" in cookie and "SameSite=Strict" in cookie, cookie)
    s.note("Secure flag on the cookie over plain HTTP without a proxy: %s (it is set when the session is HTTPS, see the proxy check)" % ("present" if "Secure" in cookie else "absent"))
    session = cookie.split(";")[0]
    me = lib.http_request(8765, "GET", "/api/auth/me", dict(JSON, **{"Cookie": session, "X-Monitor-Access": token}))
    s.check("the cookie identifies the administrator", me["status"] == 200 and "ops" in me["body"], "%s %s" % (me["status"], me["body"][:200]))
    without = lib.http_request(8765, "POST", "/api/alerts/unmute", dict(JSON, **{"Cookie": session, "X-Monitor-Access": token}), "{}")
    s.check("a write with the cookie and no CSRF token is refused as a CSRF failure (403 csrf)", without["status"] == 403 and "csrf" in without["body"], "%s %s" % (without["status"], without["body"][:200]))
    csrf = parsed.get("csrf") or ""
    withit = lib.http_request(8765, "POST", "/api/alerts/unmute", dict(JSON, **{"Cookie": session, "X-Monitor-Access": token, "X-CSRF-Token": csrf}), "{}")
    s.check("the same write with the CSRF token is not refused as a CSRF failure", "csrf" not in withit["body"], "%s %s" % (withit["status"], withit["body"][:200]))
    anonymous = lib.http_request(8765, "GET", "/api/alerts", dict(JSON, **{"X-Monitor-Access": token}))
    s.check("a route that is not public needs a session even with the access token (401)", anonymous["status"] == 401, "%s %s" % (anonymous["status"], anonymous["body"][:200]))
    s.docker("rm", "-f", name)

    # 2. the second start, on the same volumes, with neither the name nor the password file: the administrator is already there
    name2, code, out = s.service("second", image, base, team, ports=["127.0.0.1:8765:8765"])
    ok = code == 0 and s.wait_healthy(name2, 180)
    s.check("the second start needs no administrator variable and is healthy", ok, s.logs(name2)[-1500:])
    token = s.read_token(name2) or token
    again = login(token, "ops", password)
    s.check("the administrator of the first start still signs in", again["status"] == 200, "%s %s" % (again["status"], again["body"][:200]))
    s.check("the password is not in the log of the second start", password not in s.logs(name2), "")

    # 3. wrong passwords lock the account (and the right one is refused while it is locked)
    statuses = []
    for _ in range(8):
        statuses.append(login(token, "ops", "wrong-" + secrets.token_hex(4))["status"])
    s.check("wrong passwords end in 401 and then a lock (429)", 401 in statuses and 429 in statuses, "statuses %s" % statuses)
    locked = login(token, "ops", password)
    s.check("while it is locked the right password is refused too (429, Retry-After)", locked["status"] == 429 and lib.header(locked, "Retry-After") != "", "%s %s" % (locked["status"], lib.header(locked, "Retry-After")))
    ghost = [login(token, "ghost-%d" % i, "x" * 12)["status"] for i in range(3)]
    s.check("a name that does not exist gets the same 401 as a wrong password (no way to tell them apart)", set(ghost) == {401}, "statuses %s" % ghost)
    s.docker("rm", "-f", name2)

    # 4. a start of the team mode with no administrator at all stops, and says the command that makes one
    cfg3, data3 = s.volume("config3"), s.volume("data3")
    name3, code, _ = s.service("none", image, ["%s:/config" % cfg3, "%s:/data" % data3] + mounts, team)
    done, waited = s.run(["docker", "wait", name3], timeout=120, label="wait for the container without administrator to stop")
    exit_code = waited.strip().splitlines()[-1] if waited.strip() else "?"
    logs3 = s.logs(name3)
    s.check("with no administrator the first start stops (exit code not 0)", done == 0 and exit_code not in ("0", "?"), "exit %s" % exit_code)
    s.check("and the log says the exact command that creates the first one", "auth_cli" in logs3 and "create-admin" in logs3, logs3[-600:])


if __name__ == "__main__":
    sys.exit(lib.main_of("E2", "Team mode in a container: first administrator, second start, lock-out, cookies", body))
