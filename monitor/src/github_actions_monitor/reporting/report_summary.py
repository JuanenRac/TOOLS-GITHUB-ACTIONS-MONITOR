# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The summary of a report, written by a person: a short text at the top of the next report that the person reads, edits and approves before it is printed. Two drafts are offered, neither is ever
written by itself:

  template   always: a few plain sentences made from the figures of the report (score, what changed, open alerts, the repositories that need a person), in the language of the person. No model.
  AI         only with `ai.report_summary.enabled` (off by default) and an AI that is configured: the same figures, cleaned, go to the AI of the monitor through the one way every question takes
             (`sentinel_ai.explain`, kind `report`: the same cleaner, budget, cache and chain as every other question).

What the person approves (the text as edited, an origin of `template`, `ai` or `edited`) is kept in the state file of the reports and goes into the NEXT report that is written, once: it says something about
that period, so it is not repeated in the following ones. Nothing here reaches GitHub and nothing is sent anywhere but to the AI the person already configured. The text is plain: it is cut, cleaned of control
characters, of secrets (the one redactor of the product) and of markup, and the report prints it escaped."""
import re

from github_actions_monitor.reporting import report_render as render
from github_actions_monitor.security.redactor import redact

MAX_CHARS = 1200
ORIGINS = ("template", "ai", "edited")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP = re.compile(r"</?[A-Za-z][^>\n]{0,200}>")


def enabled(config):
    """`ai.report_summary.enabled`: only a real true switches the AI draft on."""
    ai = (config or {}).get("ai") if isinstance((config or {}).get("ai"), dict) else {}
    block = ai.get("report_summary") if isinstance(ai.get("report_summary"), dict) else {}
    return block.get("enabled") is True


def clean(text, limit=MAX_CHARS):
    """The text as it may be kept and printed: no control characters, no tags, no secrets, blank lines kept as paragraphs, at most `limit` characters."""
    text = CONTROL.sub("", str(text if text is not None else "").replace("\r\n", "\n").replace("\r", "\n"))
    text = redact(MARKUP.sub("", text))
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
    return "\n\n".join(p for p in paragraphs if p)[:limit].strip()


def template(doc, lang="en"):
    """The deterministic draft: the sentences of the report itself, in the language asked for."""
    t = render._texts(lang)
    tot = doc["team"]["totals"]
    lines = [render.score_line(doc, t)] + render.changes_lines(doc, t)
    lines.append(t("alerts_total", n=doc["alerts"]["total"]))
    lines.append(t("team_totals", bad=tot.get("bad", 0), warn=tot.get("warn", 0), ok=tot.get("ok", 0), unknown=tot.get("unknown", 0), all=doc["team"]["all"]))
    worst = [r["repo"] for r in doc["team"]["ranking"][:3] if r.get("state") in ("bad", "warn")]
    if worst:
        lines.append(", ".join(worst))
    return clean("\n".join(lines))


def ai_data(doc, lang="en"):
    """What the model is shown: the figures of the draft and the worst alerts (titles already cleaned by the report builder). The AI's own cleaner runs over it again."""
    items = [f"[{a.get('level')}] {a.get('repo')}: {a.get('title')}" for a in doc["alerts"]["items"][:8]]
    return template(doc, lang) + "\n" + "\n".join(items)


def ai_draft(config, doc, lang, explain):
    """{"status": "off"|"no_ai"|"failed"|"ok", "text", "provider", "model"}. `explain(text)` asks the AI of the monitor (kind `report`); it is only called when the switch is on."""
    if not enabled(config):
        return {"status": "off", "text": "", "provider": "", "model": ""}
    try:
        answer = explain(ai_data(doc, lang))
    except Exception:   # noqa: BLE001 - an AI that fails never stops the draft of the template
        return {"status": "failed", "text": "", "provider": "", "model": ""}
    if not isinstance(answer, dict) or not answer.get("ok"):
        return {"status": "no_ai" if "off" in str((answer or {}).get("error", "")).lower() else "failed", "text": "", "provider": "", "model": ""}
    return {"status": "ok", "text": clean(answer.get("text")), "provider": str(answer.get("provider") or "")[:40], "model": str(answer.get("model") or "")[:80]}


def drafts(config, doc, lang, explain, with_ai=True):
    """Both drafts for the page and the route: {"template": text, "ai": {...}}; the AI draft is only asked for when `with_ai`."""
    return {"template": template(doc, lang), "ai": ai_draft(config, doc, lang, explain) if with_ai else {"status": "not_asked", "text": "", "provider": "", "model": ""}}

