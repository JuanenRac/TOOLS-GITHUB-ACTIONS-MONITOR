#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E9 - files shared by several processes inside the container: the lock of the operating system (os_lock) and the lock file (process_lock) on the data volume, with the user of the image, read-only
root and no capabilities. Four processes add to one counter 40 times each: not one increment may be lost, a process killed while it holds the lock must not stop the others, and the monitor of the
container must still be healthy at the end. (Two visitors behind the proxy, one locked and the other not, are checked in E3.)"""
import json
import sys

import audit_lib as lib

WORKER = r"""
import json, os, sys
from pathlib import Path
from github_actions_monitor.storage import locks
target, kind, rounds = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
guard = locks.os_lock if kind == "os" else locks.process_lock
for _ in range(rounds):
    with guard(target, 60.0):
        value = int(target.read_text() or "0") if target.exists() else 0
        target.write_text(str(value + 1))
"""

DRIVER = r"""
import subprocess, sys, json
from pathlib import Path
kind, workers, rounds = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
target = Path("/data/e9_counter_" + kind)
target.write_text("0")
procs = [subprocess.Popen([sys.executable, "-c", open("/tmp/e9_worker.py").read(), str(target), kind, str(rounds)]) for _ in range(workers)]
codes = [p.wait(timeout=300) for p in procs]
print(json.dumps({"codes": codes, "count": int(target.read_text())}))
"""

KILLER = r"""
import subprocess, sys, time, os, signal, json
from pathlib import Path
from github_actions_monitor.storage import locks
target = Path("/data/e9_killed")
holder = subprocess.Popen([sys.executable, "-c", "import sys,time\nfrom pathlib import Path\nfrom github_actions_monitor.storage import locks\nwith locks.os_lock(Path(sys.argv[1]), 60.0):\n print('held', flush=True)\n time.sleep(120)", str(target)], stdout=subprocess.PIPE, text=True)
assert holder.stdout.readline().strip() == "held"
holder.kill(); holder.wait()
started = time.monotonic()
with locks.os_lock(target, 10.0):
    pass
print(json.dumps({"waited": round(time.monotonic() - started, 2)}))
"""


def body(s):
    image = s.image()
    s.base_digests("python:3.13-slim")
    mounts, env, _token = s.login_files()
    config, data = s.volume("config"), s.volume("data")
    volumes = ["%s:/config" % config, "%s:/data" % data] + mounts
    name, code, out = s.service("monitor", image, volumes, env)
    if not s.check("the container starts", code == 0, out):
        return
    s.check("it becomes healthy", s.wait_healthy(name, 180), s.logs(name)[-1500:])
    s.run(["docker", "exec", name, "python", "-c", "open('/tmp/e9_worker.py','w').write(%r)" % WORKER], timeout=30, record=False)
    for kind, label in (("os", "os_lock (lock of the operating system)"), ("proc", "process_lock (lock file)")):
        code, out = s.run(["docker", "exec", name, "python", "-c", DRIVER, kind, "4", "40"], timeout=400, label="four processes add to one counter with %s" % label)
        line = out.strip().splitlines()[-1] if out.strip() else ""
        try:
            result = json.loads(line)
        except ValueError:
            result = {}
        s.check("4 processes x 40 increments with %s inside the container lose none (160)" % label, code == 0 and result.get("count") == 160 and result.get("codes") == [0, 0, 0, 0], "%s | %s" % (line, out[-600:]))
    code, out = s.python_in(name, KILLER, timeout=120, label="a process killed while it holds the os_lock")
    s.check("a process killed while it holds the lock lets go of it at once (the next one gets it in under 5 s)", code == 0 and '"waited"' in out and float(out.strip().splitlines()[-1].split(":")[1].strip("} ")) < 5.0, out[-600:])
    logs = s.logs(name)
    s.check("the log has no traceback", "Traceback" not in logs, logs[-1500:])
    s.check("the container is still healthy at the end", s.health(name) == "healthy", s.health(name))


if __name__ == "__main__":
    sys.exit(lib.main_of("E9", "Files shared by several processes inside the container (os_lock, process_lock)", body))
