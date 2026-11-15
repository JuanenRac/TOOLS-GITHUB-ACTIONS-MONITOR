# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Action proposals: observe, propose, and (full edition only) execute, with no silent write.

  Proposal         a request to do one thing on GitHub (rerun, label, comment, close, dispatch, merge). States: pending, approved, rejected, executed, failed, expired.
  content_hash     SHA-256 of the canonical content (account, repository, action, parameters). An approval is bound to that hash: a proposal that changes after it was approved cannot run.
  PolicyEngine     who may do what, where and when: roles, accounts, repositories, action types, a time window (UTC) and a maximum per day. Merge is off unless the person switches it on.
  ProposalStore    the proposals and the audit chain, in memory or in a file. `create` is idempotent for the same content; `expire_due` closes the old ones.
  Executor         the only object that can call a runner. It exists only in the full edition AND with `execute_enabled`; it re-checks state, hash, time to live and policy right before running, runs a
                   proposal once (the second call answers with the first result) and records who approved and who executed.
  Audit            an append-only chain of hashed lines (who proposed, approved, rejected, executed, with what result); `verify()` says where a line was changed or removed.

The complete edition creates and lists proposals and can show a dry run (`simulate`); it has no executor, so no code path of it calls the runner. The runner, the clock and the storage are given by the
caller. Parameters never carry secrets: a key that looks like one is refused."""
import copy
import fnmatch
import hashlib
import json
import re
import threading
from pathlib import Path

from github_actions_monitor.phase4 import msgs

STATES = ("pending", "approved", "rejected", "executed", "failed", "expired")
TERMINAL = ("rejected", "executed", "failed", "expired")
ACTION_TYPES = ("rerun", "rerun_failed", "label", "comment", "close", "dispatch", "merge")
ROLES = ("viewer", "maintainer", "admin")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,100}\Z")
ACCOUNT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}\Z")
ACTOR_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,64}\Z")
SECRET_KEY = re.compile(r"(?i)(token|passw|secret|key|cookie|authorization|credential|bearer|salt|csrf|session)")
HOURS_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)\Z")
MAX_PARAM_BYTES = 4000
SIMULATED_CALLS = {
    "rerun": "POST /repos/{repo}/actions/runs/{run_id}/rerun", "rerun_failed": "POST /repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs",
    "label": "POST /repos/{repo}/issues/{number}/labels", "comment": "POST /repos/{repo}/issues/{number}/comments", "close": "PATCH /repos/{repo}/issues/{number}",
    "dispatch": "POST /repos/{repo}/actions/workflows/{workflow}/dispatches", "merge": "PUT /repos/{repo}/pulls/{number}/merge",
}


class ProposalError(Exception):
    """`code` is a key of msgs ("act.expired"); `reason` is a stable word for logs and tests."""

    def __init__(self, code, reason="", **values):
        super().__init__(code + ":" + reason)
        self.code, self.reason, self.values = code, reason, values

    def text(self, lang="en"):
        return msgs.t(lang, self.code, reason=self.reason, **self.values)


def canonical(account_id, repo, action_type, params):
    return json.dumps({"account": account_id, "repo": repo, "action": action_type, "params": params}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(account_id, repo, action_type, params):
    return hashlib.sha256(canonical(account_id, repo, action_type, params).encode("utf-8")).hexdigest()


def _clean_params(value, depth=0):
    """The parameters as plain JSON-able data, or ProposalError: no secret-looking key, no deep or huge structures."""
    if depth > 4:
        raise ProposalError("api.bad_request", "params_too_deep", detail="params")
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str) or not re.match(r"^[A-Za-z0-9_.-]{1,40}\Z", key) or SECRET_KEY.search(key):
                raise ProposalError("api.bad_request", "bad_param_key", detail="params")
            out[key] = _clean_params(item, depth + 1)
        return out
    if isinstance(value, list):
        return [_clean_params(i, depth + 1) for i in value[:50]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:1000] if isinstance(value, str) else value
    raise ProposalError("api.bad_request", "bad_param_type", detail="params")


def _safe_result(value, depth=0):
    """What a runner answered, kept for the record: only plain data, secret-looking keys dropped, texts cut. It never raises (the action already happened)."""
    if isinstance(value, dict) and depth < 4:
        return {str(k)[:40]: _safe_result(v, depth + 1) for k, v in list(value.items())[:30] if not SECRET_KEY.search(str(k))}
    if isinstance(value, list) and depth < 4:
        return [_safe_result(v, depth + 1) for v in value[:30]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:300]


def _result_of(outcome):
    """The record of what a runner answered: a dict is kept (cleaned); anything else becomes {"ok", "detail"}."""
    return _safe_result(outcome) if isinstance(outcome, dict) else {"ok": bool(outcome), "detail": str(outcome)[:300]}


def _minutes(text):
    return int(text[:2]) * 60 + int(text[3:5])


def in_window(hours, now):
    """Whether `now` (epoch seconds, read as UTC) is inside "HH:MM-HH:MM" (it may wrap midnight). An empty text means always."""
    if not hours:
        return True
    match = HOURS_RE.match(hours)
    if not match:
        return False             # an unreadable window blocks rather than opens
    start, end = _minutes(hours[:5]), _minutes(hours[6:])
    current = int(now % 86400) // 60
    return start <= current < end if start <= end else (current >= start or current < end)


class PolicyEngine:
    """The rules, from the `proposals` settings plus an optional list of `rules`: {"account", "repo" (glob), "actions", "roles", "hours"}. When there are rules, a proposal must match one of them."""

    def __init__(self, settings, rules=None):
        self.settings, self.rules = settings, list(rules or [])

    def _rule_for(self, proposal):
        if not self.rules:
            return {}
        for rule in self.rules:
            if rule.get("account", proposal["account_id"]) == proposal["account_id"] and fnmatch.fnmatchcase(proposal["repo"], rule.get("repo", "*")):
                if proposal["action_type"] in rule.get("actions", ACTION_TYPES):
                    return rule
        return None

    def check(self, proposal, role, now, executed_today=0):
        """(True, "") or (False, reason). Reasons: action_type, merge_off, role, no_rule, rule_role, hours, rate."""
        action = proposal["action_type"]
        if action not in ACTION_TYPES or (action != "merge" and action not in self.settings.get("allowed_actions", [])):
            return False, "action_type"
        if action == "merge" and not self.settings.get("merge_allowed"):
            return False, "merge_off"
        if role not in self.settings.get("allowed_roles", ["admin"]):
            return False, "role"
        rule = self._rule_for(proposal)
        if rule is None:
            return False, "no_rule"
        if rule.get("roles") and role not in rule["roles"]:
            return False, "rule_role"
        hours = rule.get("hours", self.settings.get("hours", ""))
        if not in_window(hours, now):
            return False, "hours"
        if executed_today >= self.settings.get("max_per_day", 20):
            return False, "rate"
        return True, ""


class MemoryBackend:
    def __init__(self):
        self.proposals, self.audit = {}, []

    def save_proposal(self, proposal):
        self.proposals[proposal["id"]] = copy.deepcopy(proposal)

    def load_proposals(self):
        return copy.deepcopy(self.proposals)

    def append_audit(self, line):
        self.audit.append(dict(line))

    def load_audit(self):
        return [dict(x) for x in self.audit]


class FileBackend:
    """Two files in one folder: `proposals.json` (rewritten atomically) and `proposals_audit.jsonl` (only appended)."""

    def __init__(self, folder):
        self.folder = Path(folder)

    def _p(self, name):
        return self.folder / name

    def load_proposals(self):
        try:
            data = json.loads(self._p("proposals.json").read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_proposal(self, proposal):
        data = self.load_proposals()
        data[proposal["id"]] = proposal
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self._p("proposals.json.tmp")
        tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        tmp.replace(self._p("proposals.json"))

    def append_audit(self, line):
        self.folder.mkdir(parents=True, exist_ok=True)
        with open(self._p("proposals_audit.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")

    def load_audit(self):
        out = []
        try:
            for line in self._p("proposals_audit.jsonl").read_text(encoding="utf-8").splitlines():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({"corrupt": True})
        except OSError:
            pass
        return out


def _line_hash(line):
    body = {k: v for k, v in line.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


class ProposalStore:
    def __init__(self, settings, backend=None, clock=None, new_id=None, policy=None):
        self.settings = settings
        self.backend = backend or MemoryBackend()
        self.clock = clock or (lambda: 0)
        self._counter = 0
        self._new_id = new_id or self._default_id
        self.policy = policy or PolicyEngine(settings)
        self.lock = threading.RLock()
        self.proposals = self.backend.load_proposals()
        self._audit = self.backend.load_audit()

    def _default_id(self):
        self._counter += 1
        return "p%06d" % (len(self.proposals) + self._counter)

    # ---- audit ----
    def _log(self, event, proposal_id, actor, role, detail=None):
        prev = self._audit[-1].get("hash", "") if self._audit else ""
        line = {"seq": len(self._audit) + 1, "at": int(self.clock()), "event": event, "proposal": proposal_id, "actor": actor, "role": role, "detail": detail or {}, "prev": prev}
        line["hash"] = _line_hash(line)
        self._audit.append(line)
        self.backend.append_audit(line)

    def audit(self):
        return [dict(x) for x in self._audit]

    def verify_audit(self):
        """(True, 0) or (False, seq of the first bad line): a line changed, cut out or put in breaks the chain."""
        prev = ""
        for number, line in enumerate(self._audit, 1):
            if line.get("seq") != number or line.get("prev") != prev or line.get("hash") != _line_hash(line):
                return False, number
            prev = line["hash"]
        return True, 0

    # ---- helpers ----
    def _get(self, proposal_id):
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            raise ProposalError("api.not_found", "no_such_proposal")
        return proposal

    def _save(self, proposal):
        self.proposals[proposal["id"]] = proposal
        self.backend.save_proposal(proposal)

    def _fresh_hash(self, proposal):
        return content_hash(proposal["account_id"], proposal["repo"], proposal["action_type"], proposal["params"])

    def _expire_if_old(self, proposal):
        if proposal["state"] in ("pending", "approved") and self.clock() >= proposal["expires_at"]:
            proposal["state"] = "expired"
            self._save(proposal)
            self._log("expired", proposal["id"], "system:clock", "", {})
        return proposal

    def get(self, proposal_id):
        with self.lock:
            return copy.deepcopy(self._expire_if_old(self._get(proposal_id)))

    def list(self, state=None, account_id=None):
        with self.lock:
            self.expire_due()
            return [copy.deepcopy(p) for p in sorted(self.proposals.values(), key=lambda p: p["created_at"]) if (state is None or p["state"] == state) and (account_id is None or p["account_id"] == account_id)]

    def expire_due(self):
        """Closes every pending or approved proposal whose time ran out; returns their ids."""
        with self.lock:
            out = []
            for proposal in list(self.proposals.values()):
                before = proposal["state"]
                self._expire_if_old(proposal)
                if proposal["state"] != before:
                    out.append(proposal["id"])
            return out

    # ---- the life of a proposal ----
    def create(self, account_id, repo, action_type, params, reason, actor, role="maintainer"):
        """A new pending proposal; the same content already pending returns that one (so a sentinel that proposes every cycle does not pile them up)."""
        with self.lock:
            if not ACCOUNT_RE.match(str(account_id)) or not REPO_RE.match(str(repo)) or action_type not in ACTION_TYPES or not ACTOR_RE.match(str(actor)):
                raise ProposalError("api.bad_request", "bad_field", detail="proposal")
            if not (str(actor).startswith("system:") or role in ("maintainer", "admin")):
                raise ProposalError("api.forbidden", "role")
            cleaned = _clean_params(params if params is not None else {})
            if len(json.dumps(cleaned)) > MAX_PARAM_BYTES:
                raise ProposalError("api.bad_request", "params_too_big", detail="params")
            digest = content_hash(account_id, repo, action_type, cleaned)
            for existing in self.proposals.values():
                if existing["content_hash"] == digest and self._expire_if_old(existing)["state"] in ("pending", "approved"):
                    return copy.deepcopy(existing)
            now = int(self.clock())
            proposal = {"id": self._new_id(), "account_id": account_id, "repo": repo, "action_type": action_type, "params": cleaned, "reason": str(reason)[:300], "created_by": actor,
                        "created_at": now, "expires_at": now + self.settings.get("ttl_seconds", 86400), "state": "pending", "content_hash": digest,
                        "approved_by": "", "approved_hash": "", "approved_at": 0, "executed_by": "", "executed_at": 0, "result": None}
            self._save(proposal)
            self._log("created", proposal["id"], actor, role, {"action": action_type, "repo": repo, "hash": digest})
            return copy.deepcopy(proposal)

    def approve(self, proposal_id, actor, role, expected_hash, now=None):
        """pending -> approved, bound to `expected_hash` (what the person was shown). The hash is recomputed from the stored content, so a changed record cannot be approved with the old hash."""
        with self.lock:
            proposal = self._expire_if_old(self._get(proposal_id))
            if proposal["state"] == "expired":
                raise ProposalError("act.expired", "expired")
            if proposal["state"] != "pending":
                raise ProposalError("act.bad_state", "state", state=proposal["state"])
            if expected_hash != self._fresh_hash(proposal) or expected_hash != proposal["content_hash"]:
                raise ProposalError("act.hash_mismatch", "hash")
            if proposal["created_by"] == actor and self.settings.get("four_eyes", True):
                raise ProposalError("act.not_allowed", "four_eyes")
            ok, why = self.policy.check(proposal, role, self.clock() if now is None else now, self.executed_today(proposal["account_id"]))
            if not ok:
                self._log("approve_denied", proposal_id, actor, role, {"reason": why})
                raise ProposalError("act.not_allowed", why)
            proposal.update(state="approved", approved_by=actor, approved_hash=expected_hash, approved_at=int(self.clock()))
            self._save(proposal)
            self._log("approved", proposal_id, actor, role, {"hash": expected_hash})
            return copy.deepcopy(proposal)

    def reject(self, proposal_id, actor, role, note=""):
        with self.lock:
            proposal = self._expire_if_old(self._get(proposal_id))
            if proposal["state"] not in ("pending", "approved"):
                raise ProposalError("act.bad_state", "state", state=proposal["state"])
            if role not in self.settings.get("allowed_roles", ["admin"]):
                raise ProposalError("act.not_allowed", "role")
            proposal["state"] = "rejected"
            self._save(proposal)
            self._log("rejected", proposal_id, actor, role, {"note": str(note)[:200]})
            return copy.deepcopy(proposal)

    def executed_today(self, account_id):
        since = self.clock() - 86400
        return sum(1 for p in self.proposals.values() if p["account_id"] == account_id and p["state"] in ("executed", "failed") and p["executed_at"] >= since)

    def simulate(self, proposal_id):
        """A dry run for the complete edition: what would be called, with what, and whether the policy would allow it now. It runs nothing and writes nothing but a line of audit-free memory."""
        with self.lock:
            proposal = self.get(proposal_id)
            call = SIMULATED_CALLS[proposal["action_type"]].format(repo=proposal["repo"], **{k: proposal["params"].get(k, "{" + k + "}") for k in ("run_id", "number", "workflow")})
            roles = self.settings.get("allowed_roles") or ["admin"]
            ok, why = self.policy.check(proposal, roles[0], self.clock(), self.executed_today(proposal["account_id"]))
            return {"proposal": proposal["id"], "would_call": call, "policy_ok": ok, "policy_reason": why, "executes": False}


class Executor:
    """Runs approved proposals. It refuses to exist unless the edition is `full` and `execute_enabled` is on (the capability check is here, not in the caller)."""

    def __init__(self, store, runner, edition, settings):
        if edition != "full" or not settings.get("execute_enabled"):
            raise ProposalError("act.exec_disabled", "capability")
        self.store, self.runner = store, runner

    def execute(self, proposal_id, actor, role):
        store = self.store
        with store.lock:
            proposal = store._expire_if_old(store._get(proposal_id))
            if proposal["state"] in ("executed", "failed"):
                return {"idempotent": True, "state": proposal["state"], "result": copy.deepcopy(proposal["result"])}       # the second call answers with the first result, runs nothing
            if proposal["state"] == "expired":
                raise ProposalError("act.expired", "expired")
            if proposal["state"] != "approved":
                raise ProposalError("act.bad_state", "state", state=proposal["state"])
            fresh = store._fresh_hash(proposal)
            if fresh != proposal["approved_hash"] or fresh != proposal["content_hash"]:
                store._log("execute_denied", proposal_id, actor, role, {"reason": "hash"})
                raise ProposalError("act.hash_mismatch", "hash")
            ok, why = store.policy.check(proposal, role, store.clock(), store.executed_today(proposal["account_id"]))
            if not ok:
                store._log("execute_denied", proposal_id, actor, role, {"reason": why})
                raise ProposalError("act.not_allowed", why)
            proposal["state"], proposal["executed_by"], proposal["executed_at"] = "failed", actor, int(store.clock())      # failed until the runner says otherwise: a crash cannot leave it re-runnable
            store._save(proposal)
            try:
                outcome = self.runner(proposal["action_type"], proposal["account_id"], proposal["repo"], copy.deepcopy(proposal["params"]), proposal["id"])
                proposal["state"], proposal["result"] = "executed", _result_of(outcome)
            except Exception as exc:   # noqa: BLE001 - the failure is the result
                proposal["result"] = {"error": type(exc).__name__, "message": str(exc)[:200]}
            store._save(proposal)
            store._log(proposal["state"], proposal_id, actor, role, {"approved_by": proposal["approved_by"], "result": proposal["result"]})
            return {"idempotent": False, "state": proposal["state"], "result": copy.deepcopy(proposal["result"])}
