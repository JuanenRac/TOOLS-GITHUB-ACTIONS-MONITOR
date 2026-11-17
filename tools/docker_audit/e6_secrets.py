#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E6 - secrets: with every secret given as a FILE (the GitHub login, the password of the first administrator, the access token, the shared secret of the webhook), none of their values may be
in `docker inspect`, in an answer of /api/*, in the log, in the history or the files of the image, or in the environment of a process of the container."""
import json
import re
import secrets
import sys
import time

import audit_lib as lib

PATHS_EXTRA = ["/api/accounts", "/api/settings", "/api/advanced", "/api/github-token", "/api/auth/users", "/api/auth/audit", "/api/auth/me", "/api/audit-log", "/api/run-log", "/api/live-status",
               "/api/github-app/status", "/api/statusbar", "/api/ai/state", "/api/paths", "/api/about", "/api/data", "/api/alerts", "/api/discovery"]

ENVIRON = r'''
import json, os, sys
secrets = json.loads(sys.stdin.read())
found = []
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        env = open("/proc/%s/environ" % pid, "rb").read().decode("utf-8", "replace")
        cmd = open("/proc/%s/cmdline" % pid, "rb").read().decode("utf-8", "replace").replace("\0", " ")
    except OSError:
        continue
    for label, value in secrets.items():
        if value in env:
            found.append({"pid": int(pid), "cmd": cmd[:80].replace(value, "<%s>" % label), "secret": label, "where": "environ"})
        if value in cmd:
            found.append({"pid": int(pid), "cmd": cmd[:80].replace(value, "<%s>" % label), "secret": label, "where": "command line"})
print("AUDIT-JSON " + json.dumps(found))
'''
SCAN = r'''
import os, re, sys
patterns = [re.compile(rb"ghp_[A-Za-z0-9]{30,}"), re.compile(rb"github_pat_[A-Za-z0-9_]{30,}"), re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")]
hits = []
for top in ("/app", "/etc", "/root", "/home", "/usr/local/bin", "/opt", "/srv", "/var/lib"):
    for folder, dirs, files in os.walk(top):
        for name in files:
            path = os.path.join(folder, name)
            try:
                if os.path.getsize(path) > 3000000 or os.path.islink(path):
                    continue
                blob = open(path, "rb").read()
            except OSError:
                continue
            for pattern in patterns:
                if pattern.search(blob):
                    hits.append(path)
unwanted = [p for p in ("/app/tests", "/app/.git", "/app/data", "/app/config", "/app/logs", "/app/ai", "/app/.env", "/app/actions_monitor.json") if os.path.exists(p)]
print("AUDIT-JSON " + __import__("json").dumps({"hits": hits[:20], "unwanted": unwanted}))
'''


def body(s):
    image = s.image()
    mounts, env, gh_token = s.login_files()
    password = s.secret("audit-pass-" + secrets.token_hex(6), "admin-password")
    access = s.secret("audit-access-" + secrets.token_hex(12), "access-token")
    webhook = s.secret("audit-hook-" + secrets.token_hex(20), "webhook-secret")
    files = {"admin_pw": s.file("secrets/admin_pw", password), "access": s.file("secrets/access_token", access), "webhook": s.file("secrets/webhook_secret", webhook)}
    config, data = s.volume("config"), s.volume("data")
    volumes = ["%s:/config" % config, "%s:/data" % data] + mounts + ["%s:/run/secrets/admin_pw:ro" % files["admin_pw"], "%s:/run/secrets/access_token:ro" % files["access"],
                                                                      "%s:/run/secrets/webhook_secret:ro" % files["webhook"]]
    env.update({"MONITOR_TEAM_MODE": "1", "MONITOR_ADMIN_USER": "ops", "MONITOR_ADMIN_PASSWORD_FILE": "/run/secrets/admin_pw", "MONITOR_ACCESS_TOKEN_FILE": "/run/secrets/access_token",
                "MONITOR_WEBHOOK_SECRET_FILE": "/run/secrets/webhook_secret"})
    name, code, out = s.service("monitor", image, volumes, env, ports=["127.0.0.1:8765:8765"])
    if not s.check("the container starts with every secret as a file", code == 0 and s.wait_healthy(name, 180), s.logs(name)[-1000:]):
        return
    values = {"github-token": gh_token, "admin-password": password, "access-token": access, "webhook-secret": webhook}

    code, out = s.docker("inspect", name, label="docker inspect (only the names of the variables are shown below)")
    s.steps[-1]["output"] = "[full inspect not copied here] variables: " + ", ".join(sorted(re.findall(r'"((?:MONITOR|GH|FAKE)_[A-Z_]+)=', out)))
    leaked = [label for label, value in values.items() if value in out]
    s.check("docker inspect of the container shows no value of a secret, only the names of the variables", code == 0 and not leaked, "found: %s" % leaked)
    s.check("the variables that carry a secret hold a path (…_FILE), not the value", all(k.endswith("_FILE") for k in env if any(w in k for w in ("PASSWORD", "TOKEN", "SECRET"))) and "MONITOR_ACCESS_TOKEN" not in env, "")

    # sign in as the administrator and read every route that could show a setting or a credential
    head = {"Host": "127.0.0.1:8765", "X-Monitor-Access": access, "Content-Type": "application/json"}
    answer = lib.http_request(8765, "POST", "/api/auth/login", head, json.dumps({"username": "ops", "password": password}))
    parsed = lib.jbody(answer) or {}
    s.check("the administrator signs in", answer["status"] == 200, "%s %s" % (answer["status"], answer["body"][:200]))
    head["Cookie"] = lib.header(answer, "Set-Cookie").split(";")[0]
    contract = json.loads((s.target / "monitor" / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
    paths = sorted({row["path"] for row in contract["endpoints"]} | set(PATHS_EXTRA))
    seen, leaks = 0, []
    for path in paths:
        reply = lib.http_request(8765, "GET", path, head)
        if reply["status"] == 200:
            seen += 1
        for label, value in values.items():
            if value in reply["body"]:
                leaks.append("%s in %s" % (label, path))
    s.check("no secret value is in the answer of any of the %d routes read (%d answered 200)" % (len(paths), seen), not leaks and seen > 10, "; ".join(leaks) or "only %d answered" % seen)
    users = lib.http_request(8765, "GET", "/api/auth/users", head)
    s.check("the list of users shows no password or hash field", users["status"] == 200 and not re.search(r'"(password|hash|salt|pw)[a-z_]*"\s*:', users["body"], re.I), users["body"][:300])
    wrong = "wrong-" + secrets.token_hex(5)
    lib.http_request(8765, "POST", "/api/auth/login", head, json.dumps({"username": "ops", "password": wrong}))
    lib.http_request(8765, "POST", "/api/access", head, json.dumps({"token": wrong + "-token"}))
    s.docker("kill", "-s", "HUP", name)
    lib.http_request(8765, "POST", "/api/webhook", {"Host": "127.0.0.1:8765", "Content-Type": "application/json", "X-Hub-Signature-256": "sha256=" + "0" * 64, "X-GitHub-Delivery": "audit-" + secrets.token_hex(8), "X-GitHub-Event": "ping"}, "{}")
    time.sleep(3)
    logs = s.logs(name)
    leaked = [label for label, value in {**values, "wrong-password": wrong, "wrong-token": wrong + "-token"}.items() if value in logs]
    s.check("the log (after the start, wrong passwords, wrong tokens, a bad webhook and SIGHUP) has no secret and no password that was typed", not leaked, "found: %s" % leaked)

    # the environment and the command line of every process
    code, out = s.run(["docker", "exec", "-i", name, "python", "-c", ENVIRON], input_text=json.dumps(values), timeout=60, label="look for the secrets in /proc/*/environ and /proc/*/cmdline (the values come on the standard input)")
    match = re.search(r"AUDIT-JSON (\[.*\])", out)
    found = json.loads(match.group(1)) if match else None
    s.check("the scan of the processes ran", found is not None, out[-300:])
    found = found or []
    hard = [f for f in found if f["secret"] in ("admin-password", "webhook-secret")]
    s.check("the password of the administrator and the secret of the webhook are in the environment or the command line of no process", not hard, json.dumps(hard))
    soft = [f for f in found if f["secret"] not in ("admin-password", "webhook-secret")]
    s.note("processes that hold the GitHub login or the access token (a process that calls `gh` needs the first one): %s" % (json.dumps(soft) if soft else "none"))

    # the image
    code, out = s.docker("history", "--no-trunc", "--format", "{{.CreatedBy}}", image, label="docker history --no-trunc")
    hist_hits = re.findall(r"(?i)(ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|(?:password|secret|token|api_key)\s*=\s*[^\s\"']{6,})", out)
    s.check("docker history of the image shows no secret", code == 0 and not hist_hits, str(hist_hits[:5]))
    code, out = s.docker("run", "--rm", "--label", lib.LABEL, "--entrypoint", "python", image, "-c", SCAN, label="scan the files of the image for tokens and private keys")
    match = re.search(r"AUDIT-JSON (\{.*\})", out)
    scan = json.loads(match.group(1)) if match else {}
    s.check("the files of the image hold no GitHub token and no private key", match is not None and not scan.get("hits"), json.dumps(scan))
    s.check("the image holds no tests, no .git, no data/config/logs/ai folder of its own and no .env", match is not None and not scan.get("unwanted"), json.dumps(scan.get("unwanted")))
    code, out = s.docker("inspect", image, "--format", "{{json .Config.Env}}")
    cleaned = out.replace("MONITOR_SECRET_DIR=/data/secrets", "")
    s.check("the variables baked into the image carry no secret value", not re.search(r"(?i)(password|secret|token)[A-Z_]*=[^\s\",]", cleaned), out[:600])


if __name__ == "__main__":
    sys.exit(lib.main_of("E6", "Secrets: not in inspect, API, logs, image or process environment", body))
