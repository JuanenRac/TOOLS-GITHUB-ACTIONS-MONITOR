# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Actions that the sentinel's AI may PROPOSE and, only if you switch it on and confirm each one, that the monitor may RUN (levels 3 and 4 of the AI layer).

Level 3 (propose, `ai.actions.enabled`): the answer of the model may contain a command. Only a command that matches one template of the CLOSED LIST below is kept; anything else is dropped.
The command that is shown and run is rebuilt by this module from the checked pieces (repository, number), never copied from the model's text.
Level 4 (run, `ai.actions.execute`, off by default and independent of level 3): every proposal has an id; running it needs a request that carries that id AND the exact command text the
person saw (so the dialog of the page must show the whole command); the id expires; the repository and the run or issue number must be ones the monitor already watches (the model cannot invent
a target); `gh` runs with your own login (no token of its own) and no shell; each attempt is written to a local log; at most `max_per_hour` actions run in an hour; after two failures in a
row the module locks itself until you unlock it.

The closed list: `rerun_failed` (gh run rerun N --failed), `rerun` (gh run rerun N), `close_issue` (gh issue close N), `act_local` (act -W FILE -j JOB; only ever proposed, never run here).
Not in the list, on purpose: deleting a branch, closing or merging a pull request, anything about secrets or settings.
"""
import json
import os
import re
import secrets
import subprocess
import threading
import time
from pathlib import Path
import private_io

HERE = Path(__file__).resolve().parent
LOG_FILE = HERE / "ai_actions_log.jsonl"
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}\.ya?ml$")
JOB_RE = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
CLOSED_LIST = ("rerun_failed", "rerun", "close_issue", "act_local")
RUNNABLE = ("rerun_failed", "rerun", "close_issue")        # act_local is only a suggestion
DEFAULTS = {"enabled": False, "execute": False, "allowed": ["rerun_failed", "close_issue"], "max_per_hour": 5, "ttl_seconds": 600}
LOCK_AFTER = 2
# the shapes the module recognises in a text (owner/repo is optional in the text: the repository comes from the context, never from here)
_PATTERNS = [
    ("rerun_failed", re.compile(r"\bgh\s+run\s+rerun\s+(\d{1,15})\s+--failed\b")),
    ("rerun", re.compile(r"\bgh\s+run\s+rerun\s+(\d{1,15})\b(?!\s+--failed)")),
    ("close_issue", re.compile(r"\bgh\s+issue\s+close\s+(\d{1,9})\b")),
    ("act_local", re.compile(r"\bact\s+-W\s+(\S+)\s+-j\s+(\S+)")),
]


def settings(config):
    """`ai.actions` of the configuration merged over DEFAULTS."""
    out = {**DEFAULTS, "allowed": list(DEFAULTS["allowed"])}
    user = ((config or {}).get("ai") or {}).get("actions") if isinstance((config or {}).get("ai"), dict) else None
    if isinstance(user, dict):
        for key in ("enabled", "execute"):
            if isinstance(user.get(key), bool):
                out[key] = user[key]
        if isinstance(user.get("allowed"), list):
            out["allowed"] = [a for a in user["allowed"] if a in CLOSED_LIST]
        for key, low, high in (("max_per_hour", 1, 60), ("ttl_seconds", 30, 3600)):
            if isinstance(user.get(key), int) and not isinstance(user.get(key), bool) and low <= user[key] <= high:
                out[key] = user[key]
    return out


def extract(text):
    """[(action, args tuple)] for every command of the closed list found in `text`, in order, without repeats."""
    found = []
    for action, pattern in _PATTERNS:
        for match in pattern.finditer(str(text or "")):
            item = (action, match.groups())
            if item not in found:
                found.append(item)
    return found


class Actions:
    def __init__(self, log_file=LOG_FILE, clock=time.time):
        self.log_file, self.clock = Path(log_file), clock
        self.lock = threading.Lock()
        self.pending = {}       # id -> proposal
        self.recent = []        # times of the actions that ran (for max_per_hour)
        self.failures = 0
        self.locked = False

    # ---- level 3
    def propose(self, text, repo, config, watched, known_run, known_issue, owner):
        """The proposals of one answer for one repository: [{"id", "action", "command", "runnable", "argv"}] (only the ones that pass every check).
        known_run(repo, run_id) and known_issue(repo, number) say whether the monitor knows that target."""
        cfg = settings(config)
        if not cfg["enabled"] or repo not in watched or not NAME_RE.match(repo or "") or not owner or not NAME_RE.match(owner):
            return []
        out = []
        for action, args in extract(text):
            if action not in cfg["allowed"]:
                continue
            if action == "act_local":
                if not (FILE_RE.match(args[0]) and JOB_RE.match(args[1])):
                    continue
                command, argv = f"act -W .github/workflows/{args[0]} -j {args[1]}", None
            else:
                number = int(args[0])
                if action in ("rerun_failed", "rerun") and not known_run(repo, number):
                    continue
                if action == "close_issue" and not known_issue(repo, number):
                    continue
                if action == "close_issue":
                    argv = ["gh", "issue", "close", str(number), "-R", f"{owner}/{repo}"]
                else:
                    argv = ["gh", "run", "rerun", str(number), "-R", f"{owner}/{repo}"] + (["--failed"] if action == "rerun_failed" else [])
                command = " ".join(argv)
            ident = secrets.token_hex(8)
            proposal = {"id": ident, "action": action, "command": command, "runnable": action in RUNNABLE and cfg["execute"], "argv": argv, "repo": repo, "at": self.clock(), "ttl": cfg["ttl_seconds"]}
            with self.lock:
                self.pending[ident] = proposal
                for key in [k for k, v in self.pending.items() if self.clock() - v["at"] > v["ttl"]]:
                    del self.pending[key]
            out.append({k: v for k, v in proposal.items() if k not in ("argv", "at", "ttl")})
        return out

    # ---- level 4
    def run(self, ident, command, config, runner=None):
        """Runs the proposal `ident` when `command` is exactly its text. Returns {"ok", "reason", ...}; reasons: off, unknown, expired, mismatch, locked, rate, failed, ok."""
        cfg = settings(config)
        if not cfg["enabled"] or not cfg["execute"]:
            return {"ok": False, "reason": "off"}
        with self.lock:
            proposal = self.pending.get(str(ident))
            if proposal is None:
                return {"ok": False, "reason": "unknown"}
            if self.clock() - proposal["at"] > proposal["ttl"]:
                del self.pending[str(ident)]
                return {"ok": False, "reason": "expired"}
            if command != proposal["command"] or not proposal["argv"] or proposal["action"] not in RUNNABLE or proposal["action"] not in cfg["allowed"]:
                return {"ok": False, "reason": "mismatch"}
            if self.locked:
                return {"ok": False, "reason": "locked"}
            self.recent = [t for t in self.recent if self.clock() - t < 3600]
            if len(self.recent) >= cfg["max_per_hour"]:
                return {"ok": False, "reason": "rate"}
            self.recent.append(self.clock())
            del self.pending[str(ident)]
        try:
            import secretstore
            done = (runner or subprocess.run)(proposal["argv"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL, shell=False,
                                              **(secretstore.gh_kwargs() if proposal["argv"][0] == "gh" else {}))
            code, tail = done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()[-300:]
        except (OSError, subprocess.SubprocessError) as error:
            code, tail = 1, str(error)[:200]
        with self.lock:
            self.failures = 0 if code == 0 else self.failures + 1
            if self.failures >= LOCK_AFTER:
                self.locked = True
        self._log({"action": proposal["action"], "repo": proposal["repo"], "command": proposal["command"], "code": code, "output": tail})
        return {"ok": code == 0, "reason": "ok" if code == 0 else "failed", "code": code, "locked": self.locked}

    def unlock(self):
        with self.lock:
            self.locked, self.failures = False, 0

    def _log(self, record):
        record = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock())), **record}
        try:
            with private_io.open_append(self.log_file) as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            if self.log_file.stat().st_size > 256 * 1024:
                lines = self.log_file.read_text(encoding="utf-8").splitlines()
                private_io.write_private(self.log_file, "\n".join(lines[len(lines) // 2:]) + "\n")
        except OSError:
            pass

    def log(self, limit=50):
        """The newest `limit` records of the local log, newest first."""
        try:
            lines = self.log_file.read_text(encoding="utf-8").splitlines()[-limit:]
        except OSError:
            return []
        out = []
        for line in reversed(lines):
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def state(self, config):
        cfg = settings(config)
        return {"enabled": cfg["enabled"], "execute": cfg["execute"], "locked": self.locked, "pending": len(self.pending), "allowed": cfg["allowed"],
                "ran_last_hour": len([t for t in self.recent if self.clock() - t < 3600]), "max_per_hour": cfg["max_per_hour"]}


ACTIONS = Actions()
