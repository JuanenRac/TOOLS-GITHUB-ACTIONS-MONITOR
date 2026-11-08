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
import signal
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
    return {"enabled": cfg.get("enabled") is True, "allowed": allowed, "timeout_seconds": seconds if isinstance(seconds, int) and not isinstance(seconds, bool) and 30 <= seconds <= 7200 else 900,
            "allow_symlinks": cfg.get("allow_symlinks") is True}


def minimal_env():
    """The environment `act` gets: no GH_TOKEN, no variable of the user. Only what a program needs to find its way (and Docker)."""
    keep = ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP", "DOCKER_HOST", "LANG")
    return {k: os.environ[k] for k in keep if k in os.environ}


def command(binary, repo_dir, workflow, event, job=None):
    null = os.devnull
    args = [binary, event, "-W", str(Path(".github") / "workflows" / workflow), "-C", str(repo_dir), "--secret-file", null, "--var-file", null, "--env-file", null, "--input-file", null]
    return args + (["-j", job] if job else [])


def inside(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def clone_dir(workspace_root, repo, workflow, allow_symlinks=False):
    """(resolved clone folder | None, reason). The clone must be a real folder INSIDE the workspace and the workflow file must be inside the clone, once every link is resolved:
    a folder that is a symbolic link, a name such as `..`, or a `.github` that points elsewhere gives `outside` (or `symlink`). `allow_symlinks` (act.allow_symlinks, OFF) lets a
    clone be a link to another folder; the workflow file must still sit inside the clone it names."""
    if not workspace_root or repo in (".", ".."):
        return None, "no_clone"
    try:
        root = Path(workspace_root).resolve()
        repo_dir = root / repo
        if repo_dir.is_symlink() and not allow_symlinks:
            return None, "symlink"
        real = repo_dir.resolve()
        if not allow_symlinks and (real.parent != root):
            return None, "outside"
        flow = (repo_dir / ".github" / "workflows" / workflow)
        if not flow.is_file():
            return None, "no_clone"
        if not inside(flow.resolve(), real):
            return None, "outside"
    except (OSError, RuntimeError, ValueError):
        return None, "no_clone"
    return real, "ok"


def plan(config, workspace_root, repo, workflow, event, job=None, which=shutil.which):
    """(plan | None, reason). Reasons: off, not_allowed, job, no_act, no_clone, symlink, outside."""
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
    repo_dir, why = clone_dir(workspace_root, repo, workflow, cfg["allow_symlinks"])
    if repo_dir is None:
        return None, why
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


def docker_names(run=subprocess.run):
    """The ids of the containers whose name starts with `act-` (what `act` creates), or None when Docker cannot be asked. Read only, with a time limit."""
    binary = shutil.which("docker")
    if not binary:
        return None
    try:
        done = run([binary, "ps", "-a", "-q", "--filter", "name=act-"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return set(done.stdout.split()) if done.returncode == 0 else None


def clean_containers(before, run=subprocess.run, names=docker_names):
    """Stops and removes ONLY the `act-` containers that appeared after `before` (the ones this run created). Returns the ids it handled. Nothing when Docker is not there."""
    if before is None:
        return []
    now = names()
    fresh = sorted((now or set()) - before)
    binary = shutil.which("docker")
    for ident in fresh:
        if binary and re.match(r"^[0-9a-f]{6,64}$", ident):
            try:
                run([binary, "rm", "-f", ident], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
            except (OSError, subprocess.SubprocessError):
                pass
    return fresh


def spawn_options():
    """Popen options that give the child its OWN process group / session, so that the whole tree can be ended without touching anything else."""
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}


def kill_tree(proc, grace=3.0, run=subprocess.run):
    """Ends the process this module started AND everything it started (act, its helpers). POSIX: SIGTERM to its process group, SIGKILL if it is still there after `grace` seconds.
    Windows: `taskkill /T /F` on its own PID (the tree below it only). Falls back to terminate()/kill() of the process itself. Never touches a process this module did not start."""
    pid = getattr(proc, "pid", None)
    if isinstance(pid, int) and pid > 0:
        if os.name == "nt":
            try:
                run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            except (OSError, subprocess.SubprocessError):
                pass
        else:
            try:
                group = os.getpgid(pid)
                if group != os.getpgid(0):
                    os.killpg(group, signal.SIGTERM)
                    deadline = time.time() + grace
                    while time.time() < deadline and proc.poll() is None:
                        time.sleep(0.05)
                    os.killpg(group, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
    for method in ("terminate", "kill"):
        try:
            getattr(proc, method)()
        except (OSError, AttributeError):
            pass


def _worker(item, popen, clock):
    started = clock()
    before = None
    try:
        before = docker_snapshot()
        proc = popen(item["argv"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=minimal_env(), text=True, encoding="utf-8", errors="replace", cwd=None, **spawn_options())
        with RUN["lock"]:
            RUN["proc"] = proc
        stopped = threading.Event()

        def expire():
            stopped.set()
            _stop(proc)
        timer = threading.Timer(item["timeout_seconds"], expire)
        timer.daemon = True
        timer.start()
        for line in proc.stdout:
            _push(line)
        code = proc.wait()
        timer.cancel()
        if stopped.is_set() or RUN.get("stopping"):
            clean_containers(before)
    except OSError as error:
        _push(f"({secretstore.redact(str(error))[:120]})")
        code = 127
    with RUN["lock"]:
        RUN.update({"running": False, "exit": code, "proc": None, "stopping": False, "finished": clock() - started})


docker_snapshot = docker_names   # replaced by the tests


def _stop(proc):
    kill_tree(proc)


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
    with RUN["lock"]:
        RUN["stopping"] = True
    _stop(proc)
    return {"ok": True, "status": "stopping"}


def status(since=0):
    with RUN["lock"]:
        return {"running": RUN["running"], "exit": RUN["exit"], "plan": RUN["plan"], "lines": RUN["lines"][since:since + 500], "total": len(RUN["lines"])}
