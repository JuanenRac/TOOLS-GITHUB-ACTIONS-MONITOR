# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The assistant of the monitor: fixed questions ("explain this alert", "summarise the week", "why is it slow") answered by the AI the owner already configured, from the data the monitor holds.

What it is NOT: a chat, an agent or a way to act. It has no tool that writes, none that reaches GitHub and none that is not in the closed list below; the answer is text. It is OFF by default
(`ai.assistant.enabled`) and, like every other use of the AI, it needs `ai.provider` (none by default), spends from the one daily budget (`ai.daily_limit`, the budget per model) and goes through the one cleaner
of the product (security/redactor.py) before anything leaves the computer.

Everything a repository wrote (the name of a workflow, the title of an alert) is DATA, never an instruction: every such text is cleaned, cut to `ai.untrusted_text_max` and put between marks that carry a
random word of this request, so a text cannot close the mark from inside it. The context shows its sources (the ids of the alerts, the repositories, the tools called) and the size sent, always.
Standard library only; the data comes in through `Reader` (the monitor builds it from what it holds, so a test needs no server)."""
import hashlib
import hmac
import re
import secrets
import unicodedata

from github_actions_monitor.security import redactor

ACTIONS = ("explain_alert", "summarize_week", "why_slow")
TOOLS = ("status", "alerts", "runs", "score")      # the closed list: nothing else can be called, whatever the settings or the model say
DEFAULT_TOOLS = ["status", "alerts", "runs", "score"]
DEFAULTS = {"enabled": False, "max_context": 6000, "tools": list(DEFAULT_TOOLS), "max_tool_calls": 4}
REPO_RE = re.compile(r"^[A-Za-z0-9._/-]{1,140}\Z")
ALERT_RE = re.compile(r"^[A-Za-z0-9._:/#@+=,-]{1,200}\Z")
ROLE_RANK = {"viewer": 1, "maintainer": 2, "admin": 3}
TOOL_ROLE = {"status": "viewer", "alerts": "viewer", "runs": "viewer", "score": "viewer"}      # the least role that may use each tool (all of them read what a viewer already sees)
AUTOMATION_RE = re.compile(r"(?i)(\[bot\]$|-bot$|^bot-|^dependabot|^renovate|^github-actions|^copilot|^claude|^codex|^cursor|^devin|^sweep-ai|^coderabbit)")
MAX_ALERTS = 20
PROCESS_KEY = secrets.token_bytes(16)      # the marks of a question carry a word only this process can work out: a text written in a repository cannot guess it


class AssistantError(Exception):
    """A refusal with a stable code (`off`, `tool`, `calls`, `action`, `argument`, `role`)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def settings(ai_cfg):
    """The settings of the assistant from the (already merged) configuration of the AI: every value inside its range, everything else back to the default."""
    raw = ai_cfg.get("assistant") if isinstance(ai_cfg, dict) and isinstance(ai_cfg.get("assistant"), dict) else {}
    out = dict(DEFAULTS, tools=list(DEFAULT_TOOLS))
    out["enabled"] = raw.get("enabled") is True
    for key, low, high in (("max_context", 500, 200000), ("max_tool_calls", 0, 20)):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    tools = raw.get("tools")
    if isinstance(tools, list):
        out["tools"] = [t for t in dict.fromkeys(tools) if t in TOOLS]
    out["untrusted_text_max"] = untrusted_max(ai_cfg)
    return out


def untrusted_max(ai_cfg):
    value = ai_cfg.get("untrusted_text_max") if isinstance(ai_cfg, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and 200 <= value <= 20000 else 2000


def actor_kind(login):
    """`automation` for a bot or an agent of AI that works in a repository (they count as automation, never as a person), else `person`."""
    return "automation" if AUTOMATION_RE.search(str(login or "").strip()) else "person"


def plain(text, limit):
    """A text from outside as one safe line of data: compatibility form (look-alike letters become the letters), no control, no invisible or direction character, no mark of ours, cut to `limit`."""
    text = unicodedata.normalize("NFKC", str(text if text is not None else ""))
    text = "".join(" " if ch in "\r\n\t  " else ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf", "Co", "Cs", "Cn") or ch in "\r\n\t")
    text = re.sub(r"\s+", " ", text.replace("[[", "( (").replace("]]", ") )")).strip()
    return text if len(text) <= limit else text[:limit] + "..."


def untrusted(text, limit, nonce):
    """The text of a third party between marks that carry the random `nonce` of this request: the text is cleaned, cut and cleaned again by the redactor, and cannot contain the mark (it never saw the nonce)."""
    return f"[[DATA-{nonce}]]{redactor.redact(plain(text, limit))}[[/DATA-{nonce}]]"


class Toolbox:
    """The tools of the assistant over a `reader` ({"views": callable -> list of repository views, "score": callable -> dict}): only the names in `allowed`, at most `max_calls` calls, only for a role that
    may. Every call is written in `sources` (what was read, never the text). Nothing here writes."""

    def __init__(self, reader, allowed, max_calls, role="viewer"):
        self.reader, self.allowed, self.max_calls = reader, [t for t in allowed if t in TOOLS], max_calls
        self.role = role if role in ROLE_RANK else "viewer"
        self.calls = 0
        self.sources = []

    def call(self, name, **args):
        if name not in TOOLS or name not in self.allowed:
            raise AssistantError("tool")
        if ROLE_RANK[self.role] < ROLE_RANK[TOOL_ROLE[name]]:
            raise AssistantError("role")
        if self.calls >= self.max_calls:
            raise AssistantError("calls")
        repo = args.get("repo")
        if repo is not None and not (isinstance(repo, str) and REPO_RE.match(repo)):
            raise AssistantError("argument")
        self.calls += 1
        result = getattr(self, "_" + name)(repo)
        self.sources.append({"tool": name, "repo": repo or "", "items": result.pop("_ids", [])})
        return result

    def _views(self):
        views = self.reader["views"]()
        return [v for v in views if isinstance(v, dict)]

    def _status(self, repo):
        views = self._views()
        totals = {s: sum(1 for v in views if v.get("state") == s) for s in ("bad", "warn", "ok", "unknown")}
        worst = sorted(views, key=lambda v: -int(v.get("risk") or 0))[:5]
        return {"repos": len(views), "totals": totals, "worst": [{"repo": v.get("repo"), "state": v.get("state"), "risk": v.get("risk")} for v in worst if v.get("risk")],
                "_ids": [v.get("repo") for v in worst if v.get("risk")]}

    def _alerts(self, repo):
        out = []
        for view in self._views():
            if repo and view.get("repo") != repo:
                continue
            for item in ((view.get("alerts") or {}).get("items") or []):
                out.append({"id": item.get("id"), "repo": view.get("repo"), "level": item.get("level"), "sentinel": item.get("sentinel"), "code": item.get("code"), "title": item.get("title"),
                            "since": item.get("created_at")})
        order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        out.sort(key=lambda a: (order.get(a["level"], 4), str(a["id"])))
        return {"alerts": out[:MAX_ALERTS], "total": len(out), "_ids": [a["id"] for a in out[:MAX_ALERTS]]}

    def _runs(self, repo):
        for view in self._views():
            if view.get("repo") == repo:
                ci, act = view.get("ci") or {}, view.get("activity") or {}
                return {"repo": repo, "runs_24h": ci.get("runs_24h"), "failures_24h": ci.get("failures_24h"), "success_rate_24h": ci.get("success_rate_24h"), "red_workflows": ci.get("red_workflows") or [],
                        "stuck_runs": ci.get("stuck_runs"), "runs_7d": act.get("runs_7d"), "last_run_at": act.get("last_run_at"), "idle_days": act.get("idle_days"), "_ids": [repo]}
        return {"repo": repo, "found": False, "_ids": []}

    def _score(self, repo):
        data = self.reader["score"]() if "score" in self.reader else {}
        data = data if isinstance(data, dict) else {}
        return {k: data.get(k) for k in ("state", "score", "letter", "coverage") if k in data} | {"_ids": ["score"]}


def _lines(value, nonce, limit, indent=""):
    """A tool answer as lines of text: the numbers and the fixed words as they are, every text a repository wrote as data between marks."""
    free = {"title", "red_workflows", "repo", "reason"}
    rows = []
    for key, item in value.items():
        if isinstance(item, list):
            if not item:
                continue
            rows.append(f"{indent}{key}:")
            for sub in item[:MAX_ALERTS]:
                if isinstance(sub, dict):
                    rows.append(indent + "  - " + ", ".join(f"{k}={untrusted(v, limit, nonce) if k in free else plain(v, 80)}" for k, v in sub.items() if v not in (None, "")))
                else:
                    rows.append(f"{indent}  - {untrusted(sub, limit, nonce) if key in free else plain(sub, 80)}")
        elif isinstance(item, dict):
            rows.append(f"{indent}{key}: " + ", ".join(f"{k}={plain(v, 40)}" for k, v in item.items()))
        elif item is not None and item != "":
            rows.append(f"{indent}{key}: " + (untrusted(item, limit, nonce) if key in free else plain(item, 80)))
    return rows


def build_context(action, args, toolbox, nonce, limit):
    """(text, sources) for one fixed action: the question, then what the tools read. Raises AssistantError for a wrong argument or a refused tool."""
    if action not in ACTIONS:
        raise AssistantError("action")
    repo, alert = args.get("repo"), args.get("alert")
    if alert is not None and not (isinstance(alert, str) and ALERT_RE.match(alert)):
        raise AssistantError("argument")
    parts = []
    if action == "explain_alert":
        if not alert:
            raise AssistantError("argument")
        found = next((a for a in toolbox.call("alerts", repo=repo)["alerts"] if a["id"] == alert), None)
        parts.append("QUESTION: explain why this alert is open, what it most likely means and what to look at first.")
        if found is None:
            parts.append("The alert is not among the open alerts the monitor holds.")
        else:
            parts += ["ALERT:"] + _lines(found, nonce, limit, "  ")
            if found.get("repo") and "runs" in toolbox.allowed:
                try:
                    parts += ["CI OF ITS REPOSITORY:"] + _lines(toolbox.call("runs", repo=found["repo"]), nonce, limit, "  ")
                except AssistantError as error:
                    if error.code != "calls":
                        raise
    elif action == "summarize_week":
        parts.append("QUESTION: summarise the state of the CI in a few lines: what is red, what is waiting, what to do first.")
        if "status" in toolbox.allowed:
            parts += ["STATUS:"] + _lines(toolbox.call("status"), nonce, limit, "  ")
        if "alerts" in toolbox.allowed:
            parts += ["OPEN ALERTS:"] + _lines(toolbox.call("alerts", repo=repo), nonce, limit, "  ")
        if "score" in toolbox.allowed:
            try:
                parts += ["SCORE:"] + _lines(toolbox.call("score"), nonce, limit, "  ")
            except AssistantError as error:
                if error.code != "calls":
                    raise
    else:
        parts.append("QUESTION: why is the CI slow or stuck here? Use only the numbers below; say plainly when they do not show it.")
        if not repo:
            raise AssistantError("argument")
        parts += ["CI OF THE REPOSITORY:"] + _lines(toolbox.call("runs", repo=repo), nonce, limit, "  ")
        if "alerts" in toolbox.allowed:
            try:
                parts += ["OPEN ALERTS:"] + _lines(toolbox.call("alerts", repo=repo), nonce, limit, "  ")
            except AssistantError as error:
                if error.code != "calls":
                    raise
    return "\n".join(parts), toolbox.sources


def ask(action, args, ai_cfg, reader, explain, role="viewer", nonce=None):
    """The answer to one fixed question: {ok, text, action, sources, tool_calls, sent_chars, sent_tokens, provider, model, error}. Never raises. `explain(text)` is the call to the AI (sentinel_ai.explain with the
    shared budget, cache and chain); it is not called when the assistant is off or the question is refused."""
    cfg = settings(ai_cfg)
    base = {"ok": False, "action": action, "text": "", "sources": [], "tool_calls": 0, "sent_chars": 0, "sent_tokens": 0, "error": ""}
    if not cfg["enabled"]:
        return {**base, "error": "off"}
    if ai_cfg.get("provider", "none") == "none":
        return {**base, "error": "no_provider"}
    args = args if isinstance(args, dict) else {}
    nonce = nonce or hmac.new(PROCESS_KEY, repr((action, args.get("repo"), args.get("alert"))).encode("utf-8", "replace"), hashlib.sha256).hexdigest()[:12]      # the same question gives the same words, so the cache of the AI still answers it
    toolbox = Toolbox(reader, cfg["tools"], cfg["max_tool_calls"], role)
    try:
        text, sources = build_context(action, args, toolbox, nonce, cfg["untrusted_text_max"])
    except AssistantError as error:
        return {**base, "error": error.code, "sources": toolbox.sources, "tool_calls": toolbox.calls}
    text = redactor.redact(text)
    cap = cfg["max_context"] * 4
    if len(text) > cap:
        text = text[:cap] + "\n[cut]"
    base.update({"sources": sources, "tool_calls": toolbox.calls, "sent_chars": len(text), "sent_tokens": len(text) // 4})
    answer = explain(text)
    if not answer.get("ok"):
        return {**base, "error": str(answer.get("error") or "no_answer")[:300], "provider": answer.get("provider", ""), "model": answer.get("model", "")}
    return {**base, "ok": True, "text": answer.get("text", ""), "cached": bool(answer.get("cached")), "provider": answer.get("provider", ""), "model": answer.get("model", "")}


def describe(ai_cfg):
    """What GET /api/assistant says (it spends nothing): the switch, the actions, the tools, the limits and the fixed rules the page shows next to the answer."""
    cfg = settings(ai_cfg)
    return {"schema": "monitor_assistant/1", "enabled": cfg["enabled"], "provider": ai_cfg.get("provider", "none"), "actions": list(ACTIONS), "tools": cfg["tools"], "all_tools": list(TOOLS),
            "max_context": cfg["max_context"], "max_tool_calls": cfg["max_tool_calls"], "untrusted_text_max": cfg["untrusted_text_max"], "read_only": True, "shows_sources": True,
            "free_chat": False}
