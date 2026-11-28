# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The routes of the assistant extras (families/assistant): what is on, the report of a repository and one turn of the free chat. The server has already checked the session, the origin and the token."""
from github_actions_monitor import families, i18n
from github_actions_monitor.app import actions_monitor, toolconfig
from github_actions_monitor.integrations import ai_actions, ai_chat, ai_report
from github_actions_monitor.security import audit_log

REPO_MAX = 140


def _on(config, dotted, key="enabled"):
    return families.block(config, dotted).get(key) is True


def extras(request):
    config = request.config
    return {"ok": True, "chat": _on(config, "ai.chat"), "copy_report": _on(config, "ui.copy_report"), "can_propose": _on(config, "ai.assistant", "can_propose"), "rag": _on(config, "ai.rag"),
            "people": actions_monitor.ai_people(config), "user": request.user, "actions": ai_actions.settings(config)["enabled"]}


def repo_report(request):
    if not _on(request.config, "ui.copy_report"):
        return 404, {"ok": False, "error": "off"}
    repo = str(request.query.get("repo") or "")[:REPO_MAX]
    language = str(request.query.get("lang") or "en")[:2]
    view = ai_report.view_of(actions_monitor.health_views(), repo)
    if view is None:
        return 404, {"ok": False, "error": "repo"}
    with i18n.use_language(language if language in i18n.LANGS else "en"):
        return dict(ai_report.report(view), ok=True, repo=repo)


def _watched():
    return [r for r in ((actions_monitor.STATE["data"] or {}).get("repos") or []) if isinstance(r, str)]


def _propose(config, message, answer, user):
    """With ai.assistant.can_propose (and ai.actions.enabled): a command of the closed list in the answer, about the one repository the question names, becomes a proposal people must approve."""
    repo = ai_chat.named_repo(message, _watched())
    if not repo:
        return []
    data = actions_monitor.STATE["data"] or {}
    runs = lambda r: (actions_monitor.RUN_CACHE.get(r) or {}).get("runs", [])      # noqa: E731
    return ai_actions.ACTIONS.propose(answer, repo, config, _watched(), lambda r, n: any(x.get("id") == n for x in runs(r)),
                                      lambda r, n: any(i.get("repo") == r and i.get("number") == n for i in data.get("issues", [])), toolconfig.github_owner(config), creator=user or "")


def chat(request):
    config = request.config
    if not _on(config, "ai.chat"):
        return 404, {"ok": False, "error": "off"}
    from github_actions_monitor.sentinels import sentinel_ai
    cfg = sentinel_ai.ai_config(config)
    store = actions_monitor.ai_store()
    message = request.body.get("message")
    out = ai_chat.ask(message, request.body.get("history"), cfg, actions_monitor.assistant_reader(), lambda text: sentinel_ai.explain("assistant", text, cfg, store))
    audit_log.note("chat", {"tool_calls": out["tool_calls"], "ok": out["ok"]})      # never the question nor the answer
    out["proposals"] = []
    if out["ok"] and _on(config, "ai.assistant", "can_propose"):
        out["proposals"] = _propose(config, message, out["text"], request.user)
    out["used_today"], out["daily_limit"] = store.used_today(), cfg["daily_limit"]
    return (400 if out["error"] == "argument" else 200), out
