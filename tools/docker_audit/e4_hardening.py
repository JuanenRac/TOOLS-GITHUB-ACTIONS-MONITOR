#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E4 - the hardening the guide asks for, measured inside the running container: a user that is not root, a read-only file system with the two volumes and /tmp as the only places that can
be written, every capability removed, no new privileges, and the image/compose declarations that say the same."""
import json
import re
import sys

import audit_lib as lib

INSIDE = r'''
import json, os, sys
out = {"uid": os.getuid(), "gid": os.getgid()}
def can_write(path):
    try:
        probe = os.path.join(path, ".audit-probe")
        with open(probe, "w") as handle:
            handle.write("x")
        os.remove(probe)
        return True
    except OSError as error:
        return False
out["write"] = {p: can_write(p) for p in ("/app", "/app/src", "/etc", "/usr/local/bin", "/", "/tmp", "/data", "/config", "/data/state", "/var")}
status = {}
for line in open("/proc/1/status"):
    key, _, value = line.partition(":")
    status[key] = value.strip()
out["pid1"] = {k: status.get(k) for k in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs", "Uid", "Seccomp")}
out["pid1_name"] = open("/proc/1/comm").read().strip()
procs = []
for pid in os.listdir("/proc"):
    if pid.isdigit():
        try:
            uids = [l for l in open("/proc/%s/status" % pid) if l.startswith("Uid:")][0].split()[1:3]
            caps = [l for l in open("/proc/%s/status" % pid) if l.startswith("CapEff:")][0].split()[1]
            procs.append({"pid": int(pid), "cmd": open("/proc/%s/comm" % pid).read().strip(), "uid": uids, "capeff": caps})
        except (OSError, IndexError):
            pass
out["procs"] = procs
def attempt(label, call):
    try:
        call()
        return label + ": ALLOWED"
    except OSError as error:
        return label + ": " + type(error).__name__
out["attempts"] = [
    attempt("chown /tmp to root", lambda: os.chown("/tmp", 0, 0)),
    attempt("set the user to 0", lambda: os.setuid(0)),
    attempt("write /proc/sys/kernel/hostname", lambda: open("/proc/sys/kernel/hostname", "w").write("x")),
    attempt("mkdir /root/x", lambda: os.mkdir("/root/x")),
]
sys.stdout.write("AUDIT-JSON " + json.dumps(out) + "\n")
'''


def body(s):
    image = s.image()
    mounts, env, _t = s.login_files()
    config, data = s.volume("config"), s.volume("data")
    name, code, out = s.service("monitor", image, ["%s:/config" % config, "%s:/data" % data] + mounts, env, extra=["--memory", "512m", "--pids-limit", "256"])
    if not s.check("the container starts with the flags of the guide (--read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true)", code == 0 and s.wait_healthy(name, 180), s.logs(name)[-1000:]):
        return
    code, out = s.docker("exec", name, "python", "-c", INSIDE, label="measure from inside the container")
    match = re.search(r"AUDIT-JSON (\{.*\})", out)
    if not s.check("the measurement ran inside the container", bool(match), out[-600:]):
        return
    info = json.loads(match.group(1))
    s.check("the program runs as the user 10001, not root (id -u != 0)", info["uid"] == 10001 and info["gid"] == 10001, "uid %s gid %s" % (info["uid"], info["gid"]))
    ids = [p for p in info["procs"] if p["uid"] != ["10001", "10001"]]
    s.check("every process of the container runs as 10001 (tini included)", not ids, "others: %s" % ids[:5])
    s.check("PID 1 is tini (the init of the image)", info["pid1_name"] == "tini", info["pid1_name"])
    write = info["write"]
    s.check("the code and the system are read-only (/app, /etc, /usr/local/bin, /, /var cannot be written)", not any(write[p] for p in ("/app", "/app/src", "/etc", "/usr/local/bin", "/", "/var")), json.dumps(write))
    s.check("the only places that can be written are /tmp and the two volumes", write["/tmp"] and write["/data"] and write["/config"] and write["/data/state"], json.dumps(write))
    pid1 = info["pid1"]
    zero = "0000000000000000"
    s.check("no capability at all (CapEff, CapPrm, CapBnd are zero)", pid1["CapEff"] == zero and pid1["CapPrm"] == zero and pid1["CapBnd"] == zero, json.dumps(pid1))
    s.check("no-new-privileges is on (NoNewPrivs 1)", pid1["NoNewPrivs"] == "1", json.dumps(pid1))
    s.check("what a root-only call tries inside is refused (chown, setuid, /proc/sys, /root)", not any("ALLOWED" in a for a in info["attempts"]), "; ".join(info["attempts"]))
    s.note("seccomp mode of PID 1: %s (2 = the default profile of Docker is on)" % pid1.get("Seccomp"))

    code, out = s.docker("inspect", name, "--format", "{{json .HostConfig}}")
    host = json.loads(out) if code == 0 else {}
    s.check("docker inspect: ReadonlyRootfs, CapDrop ALL, no-new-privileges, not privileged, no extra capability, no host network or PID",
            host.get("ReadonlyRootfs") is True and "ALL" in (host.get("CapDrop") or []) and any("no-new-privileges" in o for o in (host.get("SecurityOpt") or [])) and not host.get("Privileged")
            and not host.get("CapAdd") and host.get("NetworkMode") != "host" and not host.get("PidMode") and not host.get("Devices"), json.dumps({k: host.get(k) for k in ("ReadonlyRootfs", "CapDrop", "CapAdd", "SecurityOpt", "Privileged", "NetworkMode", "PidMode", "Devices")}))
    s.check("/tmp is a tmpfs", "/tmp" in (host.get("Tmpfs") or {}), json.dumps(host.get("Tmpfs")))
    code, out = s.docker("inspect", image, "--format", "{{json .Config}}")
    cfg = json.loads(out) if code == 0 else {}
    s.check("the image itself declares User 10001:10001, a health check, the volumes and the exposed port", cfg.get("User") == "10001:10001" and cfg.get("Healthcheck") and set(cfg.get("Volumes") or {}) == {"/config", "/data"}
            and "8765/tcp" in (cfg.get("ExposedPorts") or {}), json.dumps({k: cfg.get(k) for k in ("User", "Volumes", "ExposedPorts")}))
    s.check("the entry point is tini then the service", (cfg.get("Entrypoint") or [])[:2] == ["/usr/bin/tini", "--"] and "github_actions_monitor.service" in " ".join(cfg.get("Entrypoint") or []), json.dumps(cfg.get("Entrypoint")))

    # the compose file of the version says the same as the docker run
    text = (s.target / "deploy" / "compose.yaml").read_text(encoding="utf-8")
    for needle in ("read_only: true", "cap_drop:", "- ALL", "no-new-privileges:true", "- /tmp", '"127.0.0.1:${MONITOR_PORT:-8765}:8765"'):
        s.check("deploy/compose.yaml has `%s`" % needle, needle in text, "")
    stats = s.docker("stats", "--no-stream", "--format", "{{.MemUsage}} / {{.PIDs}} processes", name)[1].strip()
    s.note("resources of the idle monitor: %s" % stats)
    s.check("the monitor is still healthy after the measurements", s.health(name) == "healthy", s.health(name))


if __name__ == "__main__":
    sys.exit(lib.main_of("E4", "Hardening: no root, read-only file system, no capabilities, no new privileges", body))
