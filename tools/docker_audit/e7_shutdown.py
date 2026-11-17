#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E7 - stopping and crashing: SIGTERM (docker stop) ends the service in an orderly way and without losing data, a start after kill -9 finds the data whole, and the memory limits."""
import json
import re
import sys
import time

import audit_lib as lib

JSON_CHECK = r'''
import json, os
bad, total = [], 0
for top in ("/data", "/config"):
    for folder, dirs, files in os.walk(top):
        for name in files:
            if name.endswith(".json"):
                path = os.path.join(folder, name)
                total += 1
                try:
                    text = open(path, encoding="utf-8").read()
                    if text.strip():
                        json.loads(text)
                except (OSError, ValueError) as error:
                    bad.append(path + ": " + str(error)[:80])
print("AUDIT-JSON " + json.dumps({"total": total, "bad": bad}))
'''


def inspect_state(s, name):
    code, out = s.docker("inspect", "-f", "{{json .State}}", name, record=False)
    try:
        return json.loads(out)
    except ValueError:
        return {}


def facts(s, name, token):
    """What must survive: the access token, the marker, the mode of the login, and whether every JSON file of the volumes is whole."""
    marker = s.docker("exec", name, "cat", "/data/state/audit_marker")[1].strip()
    mode = s.docker("exec", name, "stat", "-c", "%a", "/data/accounts/default/credential")[1].strip()
    _c, out = s.python_in(name, JSON_CHECK, label="parse every .json file of the volumes")
    match = re.search(r"AUDIT-JSON (\{.*\})", out)
    return s.read_token(name) == token, marker, mode, json.loads(match.group(1)) if match else {"total": 0, "bad": ["no answer"]}


def body(s):
    image = s.image()
    mounts, env, good = s.login_files()
    config, data = s.volume("config"), s.volume("data")
    volumes = ["%s:/config" % config, "%s:/data" % data] + mounts
    name, code, out = s.service("monitor", image, volumes, env, ports=["127.0.0.1:8765:8765"], extra=["--memory", "256m", "--memory-swap", "256m"])
    if not s.check("the container starts with a memory limit of 256 MiB", code == 0 and s.wait_healthy(name, 180), s.logs(name)[-1000:]):
        return
    token = s.read_token(name)
    s.run(["docker", "exec", "-i", "-e", "MONITOR_ACCESS_TOKEN=" + token, name, "python", "/app/bin/monitor_cli.py", "credential", "replace", "--account", "default", "--new-token-file", "-"],
          input_text=good + "\n", timeout=120, label="credential replace")
    s.docker("exec", name, "sh", "-c", "echo audit-marker > /data/state/audit_marker")
    head = {"Host": "127.0.0.1:8765", "X-Monitor-Access": token}
    statuses = {}
    for path in ("/api/data", "/api/alerts", "/api/score", "/api/quota", "/api/help/topics", "/api/settings", "/api/health?deep=1") * 12:
        code = lib.http_request(8765, "GET", path, head)["status"]
        statuses[code] = statuses.get(code, 0) + 1
    state = inspect_state(s, name)
    s.check("a burst of %d requests leaves the container healthy and not killed for memory" % sum(statuses.values()), s.health(name) == "healthy" and not state.get("OOMKilled"), "statuses %s, state %s" % (statuses, state.get("Status")))
    s.note("memory in use after the burst: %s" % s.docker("stats", "--no-stream", "--format", "{{.MemUsage}} ({{.MemPerc}})", name)[1].strip())

    # SIGTERM
    started = time.time()
    code, out = s.docker("stop", "-t", "30", name, label="docker stop (SIGTERM, 30 s of grace)")
    took = time.time() - started
    state = inspect_state(s, name)
    s.check("docker stop ends the service within the grace period, by itself (exit code 0 or 143, not 137)", code == 0 and took < 25 and state.get("ExitCode") in (0, 143), "took %.1f s, exit code %s, OOMKilled %s" % (took, state.get("ExitCode"), state.get("OOMKilled")))
    s.note("time to stop on SIGTERM: %.1f s" % took)
    logs = s.logs(name)
    s.check("the log of the stop has no traceback", "Traceback" not in logs, logs[-800:])
    s.docker("start", name)
    s.check("after docker start the container is healthy again", s.wait_healthy(name, 180), s.logs(name)[-800:])
    same, marker, mode, parsed = facts(s, name, token)
    s.check("nothing was lost by the orderly stop: the token, the marker and the login (0600) are there and every JSON file is whole", same and marker == "audit-marker" and mode == "600" and not parsed["bad"],
            "token same %s, marker %r, mode %s, JSON %s" % (same, marker, mode, parsed))

    # kill -9
    s.docker("kill", "-s", "KILL", name)
    state = inspect_state(s, name)
    s.check("the container was killed (exit code 137)", state.get("ExitCode") == 137, "exit code %s" % state.get("ExitCode"))
    s.docker("start", name)
    s.check("after kill -9 and docker start the container is healthy again (no stale lock or pid keeps it down)", s.wait_healthy(name, 180), s.logs(name)[-1200:])
    same, marker, mode, parsed = facts(s, name, token)
    s.check("after kill -9 the token, the marker and the login are there and every JSON file is whole", same and marker == "audit-marker" and mode == "600" and not parsed["bad"],
            "token same %s, marker %r, mode %s, JSON %s" % (same, marker, mode, parsed))
    logs = s.logs(name)
    s.check("the log after the crash has no traceback", "Traceback" not in logs, logs[-800:])
    s.docker("rm", "-f", name)

    # a limit that is too small: only reported
    config2, data2 = s.volume("config2"), s.volume("data2")
    small, code, _ = s.service("small", image, ["%s:/config" % config2, "%s:/data" % data2] + mounts, env, extra=["--memory", "96m", "--memory-swap", "96m"])
    healthy = code == 0 and s.wait_healthy(small, 150)
    state = inspect_state(s, small)
    s.note("with --memory 96m: healthy=%s, OOMKilled=%s, status=%s (the smallest limit that works is information for the people who size a container)" % (healthy, state.get("OOMKilled"), state.get("Status")))


if __name__ == "__main__":
    sys.exit(lib.main_of("E7", "Shutdown on SIGTERM, restart after kill -9, memory limits", body))
