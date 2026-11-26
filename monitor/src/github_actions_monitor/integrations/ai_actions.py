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

Every proposal comes from an AI (origin "ia"), carries the SHA-256 of what would run and is kept on disk (ai_proposals.json next to the log) until it expires. When the monitor answers a person (the page,
the command line) an approval is a decision of PEOPLE: with two or more users two persons are needed (the one who asked the AI counts as one and cannot approve; a proposal nobody asked for needs two
approvals); with one person the approval needs the first eight characters of the hash typed back. Such an approval is needed whatever `ai.actions.require_approval` says.
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time
from pathlib import Path
from github_actions_monitor.security import private_io

from github_actions_monitor.util import paths
LOG_FILE = paths.place("ai_actions_log.jsonl")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}\.ya?ml\Z")
JOB_RE = re.compile(r"^[A-Za-z0-9_-]{1,60}\Z")
CLOSED_LIST = ("rerun_failed", "rerun", "close_issue", "act_local")
RUNNABLE = ("rerun_failed", "rerun", "close_issue")        # act_local is only a suggestion
DEFAULTS = {"enabled": False, "execute": False, "require_approval": True, "allowed": ["rerun_failed", "close_issue"], "max_per_hour": 5, "ttl_seconds": 600}
LOCK_AFTER = 2
STORE_NAME = "ai_proposals.json"
CODE_CHARS = 8                     # how many characters of the hash a person types to approve when there is nobody else to approve
# the shapes the module recognises in a text (owner/repo is optional in the text: the repository comes from the context, never from here)
_PATTERNS = [
    ("rerun_failed", re.compile(r"\bgh\s+run\s+rerun\s+(\d{1,15})\s+--failed\b")),
    ("rerun", re.compile(r"\bgh\s+run\s+rerun\s+(\d{1,15})\b(?!\s+--failed)")),
    ("close_issue", re.compile(r"\bgh\s+issue\s+close\s+(\d{1,9})\b")),
    ("act_local", re.compile(r"\bact\s+-W\s+(\S+)\s+-j\s+(\S+)")),
]


def argv_of(action, number, owner, repo):
    """The argument list of an action of the closed list that may run, built from checked pieces only; None for anything else."""
    if action not in RUNNABLE or not NAME_RE.match(repo or "") or not NAME_RE.match(owner or "") or isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        return None
    if action == "close_issue":
        return ["gh", "issue", "close", str(number), "-R", f"{owner}/{repo}"]
    return ["gh", "run", "rerun", str(number), "-R", f"{owner}/{repo}"] + (["--failed"] if action == "rerun_failed" else [])


def digest_of(command, repo):
    return hashlib.sha256(f"{repo}\n{command}".encode("utf-8")).hexdigest()


def settings(config):
    """`ai.actions` of the configuration merged over DEFAULTS."""
    out = {**DEFAULTS, "allowed": list(DEFAULTS["allowed"])}
    user = ((config or {}).get("ai") or {}).get("actions") if isinstance((config or {}).get("ai"), dict) else None
    if isinstance(user, dict):
        for key in ("enabled", "execute", "require_approval"):
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
    def __init__(self, log_file=LOG_FILE, clock=time.time, persist=False):
        self.log_file, self.clock = Path(log_file), clock
        self.lock = threading.Lock()
        self.pending = {}       # id -> proposal
        self.recent = []        # times of the actions that ran (for max_per_hour)
        self.failures = 0
        self.locked = False
        self.persist, self._read = persist, False

    def _store(self):
        return self.log_file.with_name(STORE_NAME)

    def _load(self):
        """Once, with the lock held: the proposals of the file that have not expired. The argument list is built again from the checked pieces, never taken from the file."""
        if not self.persist or self._read:
            return
        self._read = True
        try:
            rows = json.loads(self._store().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for row in rows if isinstance(rows, list) else []:
            try:
                argv = argv_of(row["action"], row.get("number"), row.get("owner"), row["repo"])
                command = " ".join(argv) if argv else str(row["command"])[:200]
                if row["action"] not in CLOSED_LIST or self.clock() - row["at"] > row["ttl"] or command != row["command"]:
                    continue
                kept = {key: str(row.get(key) or "")[:60] for key in ("creator", "by", "owner")}
                self.pending.setdefault(str(row["id"]), dict(kept, id=str(row["id"]), action=row["action"], command=command, runnable=row.get("runnable") is True and argv is not None, argv=argv,
                                                             repo=row["repo"], at=float(row["at"]), ttl=int(row["ttl"]), number=row.get("number"), origin="ia", hash=digest_of(command, row["repo"]),
                                                             status=row.get("status") if row.get("status") in ("pending", "approved", "rejected") else "pending",
                                                             approvers=[str(a)[:60] for a in row.get("approvers") or []][:5]))
            except (KeyError, TypeError, ValueError):
                continue

    def _save(self):
        """With the lock held."""
        if not self.persist:
            return
        rows = [{k: v for k, v in p.items() if k != "argv"} for p in self.pending.values()]
        try:
            self._store().parent.mkdir(parents=True, exist_ok=True)
            private_io.write_private(self._store(), json.dumps(rows, ensure_ascii=False) + "\n")
        except OSError:
            pass      # kept in memory

    # ---- level 3
    def propose(self, text, repo, config, watched, known_run, known_issue, owner, creator=""):
        """The proposals of one answer for one repository: [{"id", "action", "command", "runnable", "argv"}] (only the ones that pass every check).
        known_run(repo, run_id) and known_issue(repo, number) say whether the monitor knows that target."""
        cfg = settings(config)
        if not cfg["enabled"] or repo not in watched or not NAME_RE.match(repo or "") or not owner or not NAME_RE.match(owner):
            return []
        out = []
        for action, args in extract(text):
            if action not in cfg["allowed"]:
                continue
            number = None
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
                argv = argv_of(action, number, owner, repo)
                if argv is None:
                    continue
                command = " ".join(argv)
            ident = secrets.token_hex(8)
            proposal = {"id": ident, "action": action, "command": command, "runnable": action in RUNNABLE and cfg["execute"], "argv": argv, "repo": repo, "at": self.clock(), "ttl": cfg["ttl_seconds"], "status": "pending", "by": "",
                        "number": number, "owner": owner, "origin": "ia", "creator": str(creator or "")[:60], "hash": digest_of(command, repo), "approvers": []}
            with self.lock:
                self._load()
                self.pending[ident] = proposal
                for key in [k for k, v in self.pending.items() if self.clock() - v["at"] > v["ttl"]]:
                    del self.pending[key]
                self._save()
            out.append({k: v for k, v in proposal.items() if k not in ("argv", "at", "ttl", "number", "owner", "approvers")})
        return out

    # ---- level 4
    def run(self, ident, command, config, runner=None, people=None):
        """Runs the proposal `ident` when `command` is exactly its text. Returns {"ok", "reason", ...}; reasons: off, unknown, expired, mismatch, rejected, not_approved, locked, rate, failed, ok."""
        cfg = settings(config)
        if not cfg["enabled"] or not cfg["execute"]:
            return {"ok": False, "reason": "off"}
        with self.lock:
            self._load()
            proposal = self.pending.get(str(ident))
            if proposal is None:
                return {"ok": False, "reason": "unknown"}
            if self.clock() - proposal["at"] > proposal["ttl"]:
                del self.pending[str(ident)]
                return {"ok": False, "reason": "expired"}
            if command != proposal["command"] or not proposal["argv"] or proposal["action"] not in RUNNABLE or proposal["action"] not in cfg["allowed"]:
                return {"ok": False, "reason": "mismatch"}
            if proposal.get("status") == "rejected":
                return {"ok": False, "reason": "rejected"}
            if (cfg.get("require_approval") or people is not None) and proposal.get("status") != "approved":      # asked by a person: an approval of people, always
                return {"ok": False, "reason": "not_approved"}
            if self.locked:
                return {"ok": False, "reason": "locked"}
            self.recent = [t for t in self.recent if self.clock() - t < 3600]
            if len(self.recent) >= cfg["max_per_hour"]:
                return {"ok": False, "reason": "rate"}
            self.recent.append(self.clock())
            del self.pending[str(ident)]
            self._save()
        try:
            from github_actions_monitor.security import secretstore
            done = (runner or subprocess.run)(proposal["argv"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL, shell=False,
                                              **(secretstore.gh_kwargs() if proposal["argv"][0] == "gh" else {}))
            code, tail = done.returncode, secretstore.redact(((done.stdout or "") + (done.stderr or "")).strip(), secretstore.APPLIED["token"])[-300:]
        except (OSError, subprocess.SubprocessError) as error:
            from github_actions_monitor.security import secretstore
            code, tail = 1, secretstore.redact(str(error), secretstore.APPLIED["token"])[:200]
        with self.lock:
            self.failures = 0 if code == 0 else self.failures + 1
            if self.failures >= LOCK_AFTER:
                self.locked = True
        self._log({"action": proposal["action"], "repo": proposal["repo"], "command": proposal["command"], "code": code, "output": tail})
        return {"ok": code == 0, "reason": "ok" if code == 0 else "failed", "code": code, "locked": self.locked}

    # ---- review (approve or reject a proposal before it is run)
    def listing(self, config):
        """The proposals that wait (not expired), oldest first, WITHOUT the argument list: {"id", "action", "command", "repo", "runnable", "status", "by", "age_s", "expires_in_s"}.
        `status` is pending, approved or rejected; with `ai.actions.require_approval` a proposal runs only when it is approved."""
        now, out = self.clock(), []
        with self.lock:
            self._load()
            for key in [k for k, v in self.pending.items() if now - v["at"] > v["ttl"]]:
                del self.pending[key]
            for proposal in sorted(self.pending.values(), key=lambda v: v["at"]):
                out.append({"id": proposal["id"], "action": proposal["action"], "command": proposal["command"], "repo": proposal["repo"], "runnable": proposal["runnable"],
                            "origin": "ia", "creator": proposal.get("creator", ""), "hash": proposal.get("hash", ""), "approvals": len(proposal.get("approvers") or []),
                            "status": proposal.get("status", "pending"), "by": proposal.get("by", ""), "age_s": int(now - proposal["at"]), "expires_in_s": max(0, int(proposal["ttl"] - (now - proposal["at"])))})
        return out

    def review(self, ident, decision, who="", confirm="", people=None):
        """Approves or rejects the proposal `ident` (decision "approve" or "reject"), recording who did it. Returns {"ok", "reason", "status"}; reasons: bad_decision, unknown, expired, decided, ok.
        A decision is final: a proposal that was approved or rejected is not changed again. Nothing is run here.
        `people` is the number of users who can decide, when a person answers: with two or more, reasons also `who` (no name), `creator` (the one who asked cannot approve), `twice` (that person already
        approved) and the status stays pending (reason `needs_second`) until two persons are in; with one, `confirm` must be the first eight characters of the hash (reason `confirm`). One may reject."""
        if decision not in ("approve", "reject"):
            return {"ok": False, "reason": "bad_decision"}
        who = str(who or "")[:60]
        with self.lock:
            self._load()
            proposal = self.pending.get(str(ident))
            if proposal is None:
                return {"ok": False, "reason": "unknown"}
            if self.clock() - proposal["at"] > proposal["ttl"]:
                del self.pending[str(ident)]
                return {"ok": False, "reason": "expired"}
            if proposal.get("status", "pending") != "pending":
                return {"ok": False, "reason": "decided", "status": proposal["status"]}
            status, reason = ("approved" if decision == "approve" else "rejected"), "ok"
            if decision == "approve" and people is not None:
                if people >= 2:
                    approvers = proposal.setdefault("approvers", [])
                    why = "who" if not who else "creator" if who == proposal.get("creator") else "twice" if who in approvers else ""
                    if why:
                        return {"ok": False, "reason": why, "status": "pending"}
                    approvers.append(who)
                    if len(approvers) < (1 if proposal.get("creator") else 2):
                        status, reason = "pending", "needs_second"
                elif not proposal.get("hash") or str(confirm or "").strip().lower() != proposal["hash"][:CODE_CHARS]:
                    return {"ok": False, "reason": "confirm", "status": "pending"}
            proposal["status"], proposal["by"] = status, who
            self._save()
        self._log({"action": proposal["action"], "repo": proposal["repo"], "command": proposal["command"], "review": decision if reason == "needs_second" else status, "by": who, "hash": proposal.get("hash", "")[:16]})
        return {"ok": True, "reason": reason, "status": status}

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
        return {"enabled": cfg["enabled"], "execute": cfg["execute"], "locked": self.locked, "pending": len(self.pending), "require_approval": cfg["require_approval"], "allowed": cfg["allowed"],
                "ran_last_hour": len([t for t in self.recent if self.clock() - t < 3600]), "max_per_hour": cfg["max_per_hour"]}


ACTIONS = Actions(persist=True)
