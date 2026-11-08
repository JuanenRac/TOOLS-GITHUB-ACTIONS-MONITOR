# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Run a workflow on THIS computer with `act` (`act.enabled`, OFF by default). Until 1.6.3 the monitor only SHOWED the `act -W FILE -j JOB` command; now it can run it, but only like this:

  * Every run is confirmed on its own (confirmation.py): the page asks for a plan, shows the exact command line, and only a second request naming that plan - with the one-use token of the
    page - starts it. Nothing is started by a timer, a notification, the AI assistant or a webhook.
  * Only what you listed in `act.allowed` can run: entries `repository:workflow-file:event` (all three exact, no wildcard). The repository must be a clone inside your workspace folder.
  * No real secrets: the command is given empty secret, variable, environment and input files (the null device) and a minimal environment (no token of GitHub, none of your variables); `act`
    is told not to read `.secrets` or `.env`. The output is shown in the page as it comes (limited in size, cleaned of anything that looks like a token). One run at a time; a time limit
    (`act.timeout_seconds`); the person can stop it.
"""
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import confirmation
import secretstore

ENTRY_RE = re.compile(r"^([A-Za-z0-9._-]{1,100}):([A-Za-z0-9._-]{1,80}\.ya?ml):([a-z_]{1,30})$")
JOB_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
EVENTS = ("push", "pull_request", "workflow_dispatch", "schedule", "release", "pull_request_target")
MAX_LINES = 2000
MAX_BYTES = 200_000
PENDING = confirmation.Pending()
RUN = {"lock": threading.Lock(), "proc": None, "lines": [], "bytes": 0, "running": False, "exit": None, "plan": None, "started": 0.0}


def settings(config):
    cfg = config.get("act") if isinstance(config, dict) and isinstance(config.get("act"), dict) else {}
    allowed = [e for e in (cfg.get("allowed") or []) if isinstance(e, str) and ENTRY_RE.match(e) and e.split(":")[2] in EVENTS] if isinstance(cfg.get("allowed"), list) else []
    seconds = cfg.get("timeout_seconds")
    return {"enabled": cfg.get("enabled") is True, "allowed": allowed, "timeout_seconds": seconds if isinstance(seconds, int) and not isinstance(seconds, bool) and 30 <= seconds <= 7200 else 900}


def minimal_env():
    """The environment `act` gets: no GH_TOKEN, no variable of the user. Only what a program needs to find its way (and Docker)."""
    keep = ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP", "DOCKER_HOST", "LANG")
    return {k: os.environ[k] for k in keep if k in os.environ}


def command(binary, repo_dir, workflow, event, job=None):
    null = os.devnull
    args = [binary, event, "-W", str(Path(".github") / "workflows" / workflow), "-C", str(repo_dir), "--secret-file", null, "--var-file", null, "--env-file", null, "--input-file", null]
    return args + (["-j", job] if job else [])


def plan(config, workspace_root, repo, workflow, event, job=None, which=shutil.which):
    """(plan | None, reason). Reasons: off, not_allowed, job, no_act, no_clone."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return None, "off"
    if f"{repo}:{workflow}:{event}" not in cfg["allowed"]:
        return None, "not_allowed"
    if job is not None and not (isinstance(job, str) and JOB_RE.match(job)):
        return None, "job"
    binary = which("act")
    if not binary:
        return None, "no_act"
    root = Path(workspace_root) if workspace_root else None
    repo_dir = (root / repo) if root else None
    if repo_dir is None or not (repo_dir / ".github" / "workflows" / workflow).is_file():
        return None, "no_clone"
    item = {"repo": repo, "workflow": workflow, "event": event, "job": job or "", "argv": command(binary, repo_dir, workflow, event, job), "timeout_seconds": cfg["timeout_seconds"]}
    item["command"] = " ".join(item["argv"])
    item["id"] = PENDING.add("act", item)
    return dict(item), "ok"


def _push(line):
    text = secretstore.redact(line.rstrip("\r\n"))[:400]
    with RUN["lock"]:
        if RUN["bytes"] + len(text) > MAX_BYTES or len(RUN["lines"]) >= MAX_LINES:
            if RUN["lines"] and RUN["lines"][-1] != "...":
                RUN["lines"].append("...")
            return
        RUN["lines"].append(text)
        RUN["bytes"] += len(text)


def _worker(item, popen, clock):
    started = clock()
    try:
        proc = popen(item["argv"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=minimal_env(), text=True, encoding="utf-8", errors="replace", cwd=None)
        with RUN["lock"]:
            RUN["proc"] = proc
        timer = threading.Timer(item["timeout_seconds"], lambda: _stop(proc))
        timer.daemon = True
        timer.start()
        for line in proc.stdout:
            _push(line)
        code = proc.wait()
        timer.cancel()
    except OSError as error:
        _push(f"({secretstore.redact(str(error))[:120]})")
        code = 127
    with RUN["lock"]:
        RUN.update({"running": False, "exit": code, "proc": None, "finished": clock() - started})


def _stop(proc):
    try:
        proc.terminate()
    except OSError:
        pass


def start(config, plan_id, popen=subprocess.Popen, clock=time.time, threaded=True):
    """Starts a confirmed plan. {"ok", "status"}: started | off | unknown_plan | busy."""
    if not settings(config)["enabled"]:
        return {"ok": False, "status": "off"}
    item = PENDING.take(plan_id, "act")
    if item is None:
        return {"ok": False, "status": "unknown_plan"}
    with RUN["lock"]:
        if RUN["running"]:
            return {"ok": False, "status": "busy"}
        RUN.update({"running": True, "lines": [], "bytes": 0, "exit": None, "plan": {k: item[k] for k in ("repo", "workflow", "event", "job", "command")}, "started": clock()})
    if threaded:
        threading.Thread(target=_worker, args=(item, popen, clock), daemon=True).start()
    else:
        _worker(item, popen, clock)
    return {"ok": True, "status": "started"}


def stop():
    """Stops the run this module started (and only that one)."""
    with RUN["lock"]:
        proc = RUN["proc"]
    if proc is None:
        return {"ok": False, "status": "idle"}
    _stop(proc)
    return {"ok": True, "status": "stopping"}


def status(since=0):
    with RUN["lock"]:
        return {"running": RUN["running"], "exit": RUN["exit"], "plan": RUN["plan"], "lines": RUN["lines"][since:since + 500], "total": len(RUN["lines"])}
