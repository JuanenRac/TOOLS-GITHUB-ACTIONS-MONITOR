# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The webhook without a public address: GitHub's own forwarder over a WebSocket.

A monitor at home, behind a router, cannot be reached by GitHub. The GitHub CLI can do the reverse: `gh webhook forward` makes a temporary webhook that points to GitHub's forwarder, keeps a WebSocket
open from this computer, and hands every delivery to a local address, so nothing is exposed. This module runs and watches those `gh webhook forward` processes, one for each repository or organization
that you list, and hands them the local address of the receiver of the monitor. OFF by default and it WRITES to GitHub (the temporary hooks), so it needs a token with the permission to manage webhooks
(`admin:repo_hook`, `admin:org_hook`).

  webhook.transport      http (the default: GitHub reaches you through a tunnel you run) | websocket (this module)
  webhook.ws_targets     what to forward: `owner/repo` (one repository) or `owner` (a whole organization); empty by default, so switching the transport alone starts nothing
  webhook.ws_max_targets the most processes at once (10 by default; a personal account needs one hook for each repository)
  webhook.ws_cleanup     off by default: when on, the temporary hooks of the forwarder that a crash left behind in the listed targets are deleted at start

The deliveries are signed with a secret that is made at every start, kept in memory, handed to `gh` on its command line (so a process of the same user on this computer could read it: it only lets
that user send events to a receiver that is on this computer) and accepted by the receiver next to the shared secret. The shared secret itself never leaves the environment. A process that ends is
started again with a longer wait each time (5 seconds up to 5 minutes). Standard library only; the processes are started by a function the caller can replace, so the tests start none.
"""
import os
import re
import secrets
import subprocess
import threading
import time

from github_actions_monitor.security.redactor import redact

TRANSPORTS = ("http", "websocket")
DEFAULTS = {"transport": "http", "ws_targets": [], "ws_max_targets": 10, "ws_cleanup": False}
EVENTS = "workflow_run,workflow_job,check_run,push,release,check_suite"
FORWARDER = "webhook-forwarder.github.com"      # the address the temporary hooks of `gh webhook forward` point to
TARGET_RE = re.compile(r"^([A-Za-z0-9-]{1,39})(?:/([A-Za-z0-9._-]{1,100}))?\Z")
BACKOFF = (5, 10, 20, 40, 80, 160, 300)
NO_WINDOW = 0x08000000
STATES = ("starting", "forwarding", "forbidden", "restarting", "stopped")


def settings(config):
    block = (config or {}).get("webhook")
    block = block if isinstance(block, dict) else {}
    cap = block.get("ws_max_targets")
    cap = cap if isinstance(cap, int) and not isinstance(cap, bool) and 1 <= cap <= 50 else DEFAULTS["ws_max_targets"]
    seen = []
    for item in block.get("ws_targets") if isinstance(block.get("ws_targets"), list) else []:
        if isinstance(item, str) and TARGET_RE.match(item.strip()) and item.strip() not in seen:
            seen.append(item.strip())
    return {"transport": block.get("transport") if block.get("transport") in TRANSPORTS else "http", "targets": seen[:cap], "max_targets": cap, "cleanup": block.get("ws_cleanup") is True}


def command(target, url, secret, gh="gh"):
    """The command line of one forwarder (no shell): `owner/repo` forwards a repository, `owner` an organization."""
    owner, _, repo = target.partition("/")
    scope = ["--repo", target] if repo else ["--org", owner]
    return [gh, "webhook", "forward", *scope, "--events", EVENTS, "--url", url, "--secret", secret]


def classify(line):
    """The state a line of output of `gh webhook forward` shows: forwarding, forbidden (a token without the permission) or "" (nothing to conclude)."""
    low = line.lower()
    if "forwarding webhook events" in low:
        return "forwarding"
    if "admin:repo_hook" in low or "admin:org_hook" in low or "http 403" in low or "http 404" in low or "must have admin rights" in low or "resource not accessible" in low:
        return "forbidden"
    return ""


def short(line):
    """One short, clean line of output: no control characters, no secret."""
    return redact(re.sub(r"[\x00-\x1f\x7f]+", " ", line).strip())[:160]


def orphans(run, target):
    """The ids of the hooks of the forwarder in a target: [(id, active)]. Reads only. `run(args)` runs `gh` and returns (code, stdout, stderr)."""
    import json
    owner, _, repo = target.partition("/")
    endpoint = f"repos/{owner}/{repo}/hooks" if repo else f"orgs/{owner}/hooks"
    code, out, _err = run(["api", endpoint + "?per_page=100"])
    if code != 0:
        return []
    try:
        hooks = json.loads(out)
    except ValueError:
        return []
    found = []
    for hook in hooks if isinstance(hooks, list) else []:
        if isinstance(hook, dict) and isinstance(hook.get("id"), int) and FORWARDER in str((hook.get("config") or {}).get("url", "")):
            found.append((hook["id"], bool(hook.get("active"))))
    return found


def cleanup(run, targets):
    """Deletes the hooks of the forwarder that no process of ours holds (call it before starting): returns how many were deleted. WRITES to GitHub; the caller only calls it when `webhook.ws_cleanup` is on."""
    removed = 0
    for target in targets:
        owner, _, repo = target.partition("/")
        base = f"repos/{owner}/{repo}/hooks" if repo else f"orgs/{owner}/hooks"
        for ident, _active in orphans(run, target):
            code, _out, _err = run(["api", "-X", "DELETE", f"{base}/{ident}"])
            removed += 1 if code == 0 else 0
    return removed


class Forwarders:
    def __init__(self):
        self.lock = threading.Lock()
        self.secret = ""
        self.rows = {}      # target -> {"state", "restarts", "last", "since"}
        self.stopping = False
        self.procs = {}

    def reset(self):
        self.stop()
        with self.lock:
            self.secret, self.rows, self.stopping, self.procs = "", {}, False, {}

    def start(self, config, port, spawn=None, gh="gh", sleep=time.sleep, clock=time.time, threaded=True):
        """Starts one watcher for each target. Returns the targets started ([] when the transport is `http` or nothing is listed). `spawn(command)` returns a process with `.stdout` (lines) and `.wait()`,
        `.terminate()`; the default starts the real one without a window."""
        cfg = settings(config)
        if cfg["transport"] != "websocket" or not cfg["targets"]:
            return []
        with self.lock:
            if self.rows:
                return []
            self.secret = secrets.token_hex(32)
            self.stopping = False
            for target in cfg["targets"]:
                self.rows[target] = {"state": "starting", "restarts": 0, "last": "", "since": clock()}
        url = f"http://127.0.0.1:{int(port)}/api/webhook"
        for target in cfg["targets"]:
            work = lambda t=target: self.watch(t, url, spawn or self._spawn, gh, sleep, clock)      # noqa: E731
            if threaded:
                threading.Thread(target=work, name=f"ws-forward-{target}", daemon=True).start()
            else:
                work()
        return cfg["targets"]

    @staticmethod
    def _spawn(cmd):
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW if os.name == "nt" else 0)

    def watch(self, target, url, spawn, gh, sleep, clock):
        """Runs the forwarder of one target again and again, with a longer wait each time it ends, until `stop()`."""
        attempt = 0
        while True:
            with self.lock:
                if self.stopping:
                    self.rows[target]["state"] = "stopped"
                    return
                secret = self.secret
            try:
                proc = spawn(command(target, url, secret, gh))
            except OSError as error:
                self._note(target, "restarting", short(str(error)), clock)
                proc = None
            if proc is not None:
                with self.lock:
                    self.procs[target] = proc
                for line in proc.stdout or ():
                    state = classify(line)
                    self._note(target, state or None, short(line) if line.strip() else None, clock)
                try:
                    proc.wait()
                except OSError:
                    pass
            with self.lock:
                self.procs.pop(target, None)
                if self.stopping:
                    self.rows[target]["state"] = "stopped"
                    return
                if self.rows[target]["state"] != "forbidden":
                    self.rows[target]["state"] = "restarting"
                self.rows[target]["restarts"] += 1
                state = self.rows[target]["state"]
            wait = BACKOFF[min(attempt, len(BACKOFF) - 1)] * (6 if state == "forbidden" else 1)      # a token that may not manage hooks is not asked every few seconds
            attempt += 1
            sleep(wait)

    def _note(self, target, state, line, clock):
        with self.lock:
            row = self.rows.get(target)
            if row is None:
                return
            if state:
                row["state"], row["since"] = state, clock()
            if line:
                row["last"] = line

    def stop(self):
        """Ends every forwarder (they delete their temporary hook when they end normally)."""
        with self.lock:
            self.stopping = True
            procs = list(self.procs.values())
        for proc in procs:
            try:
                proc.terminate()
            except OSError:
                pass

    def local_secret(self):
        with self.lock:
            return self.secret

    def snapshot(self, config=None):
        cfg = settings(config)
        with self.lock:
            return {"transport": cfg["transport"], "targets": [{"target": t, **{k: v for k, v in row.items() if k != "since"}} for t, row in self.rows.items()], "listed": len(cfg["targets"])}


FORWARDERS = Forwarders()
