# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The assistant: proposals that people approve, light retrieval, a free chat with read only tools and the report of a repository to copy (integrations/ai_*.py do the work).

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder."""
import re

from github_actions_monitor.families.declare import Family, Route, Setting


def _api():
    from github_actions_monitor.integrations import ai_surface
    return ai_surface


def _extras(request):
    return _api().extras(request)


def _report(request):
    return _api().repo_report(request)


def _chat(request):
    return _api().chat(request)


def _s(block, key, kind, bounds=None, secure=False, unit=None):
    return Setting("ai", block, key, kind, bounds=bounds, restart=False, secure=secure, unit=unit)


FAMILY = Family(
    "assistant",
    defaults={"ai": {"assistant": {"can_propose": False}, "chat": {"enabled": False}, "rag": {"enabled": False, "model": "", "url": "http://127.0.0.1:11434", "max_mb": 200}},
              "ui": {"copy_report": {"enabled": True}}},
    settings=(_s("ai_extras", "ai.assistant.can_propose", "bool", secure=True), _s("ai_extras", "ai.chat.enabled", "bool", secure=True), _s("ai_extras", "ai.rag.enabled", "bool", secure=True),
              _s("ai_extras", "ai.rag.model", "text", bounds=re.compile(r"^[A-Za-z0-9._:/-]{0,100}\Z")), _s("ai_extras", "ai.rag.url", "text", bounds=re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\]):\d{2,5}\Z"), secure=True),
              _s("ai_extras", "ai.rag.max_mb", "int", (10, 100000), unit="MB"), _s("ai_extras", "ui.copy_report.enabled", "bool")),
    routes=(
        Route("GET", "/api/assistant/extras", _extras, "whether the chat, the repository report and the proposals of the assistant are on, and how many people decide on a proposal"),
        Route("GET", "/api/assistant/repo-report", _report, "the report of one repository in Markdown and a draft of a triage comment, to copy by hand (ui.copy_report.enabled); ?repo=; no request to GitHub"),
        Route("POST", "/api/assistant/chat", _chat, "one turn of the free chat with read only tools (ai.chat.enabled); body {message, history}; spends from the budget of the AI; nothing is run", role="viewer",
              audit="assistant_chat", max_body=20000),
    ),
)
