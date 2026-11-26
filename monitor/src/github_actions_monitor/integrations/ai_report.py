# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The report of one repository in Markdown and a DRAFT of a triage comment, both to copy by hand (`ui.copy_report.enabled`). No AI, no request to GitHub, nothing published: only what the monitor already
holds, through the cleaner of the product."""
import re

from github_actions_monitor import i18n
from github_actions_monitor.security import redactor

MAX_ALERTS = 20
ORDER = {"critical": 0, "error": 1, "warning": 2, "info": 3}
MENTION_RE = re.compile(r"(@[A-Za-z0-9][A-Za-z0-9_/-]*)")


def view_of(views, repo):
    return next((v for v in views if isinstance(v, dict) and v.get("repo") == repo), None)


def _line(text):
    """One line of Markdown from a text a repository may have written: no line break, no mention that would notify somebody, no markup of its own."""
    one = " ".join(str(text if text is not None else "").split())[:200].replace("`", "'").replace("|", "\\|").replace("<", "&lt;")
    return MENTION_RE.sub(r"`\1`", one)      # inside code a name notifies nobody


def facts(view):
    ci = view.get("ci") or {}
    alerts = sorted(((view.get("alerts") or {}).get("items") or []), key=lambda a: ORDER.get(a.get("level"), 4))[:MAX_ALERTS]
    return ci, alerts


def report(view):
    """{"markdown", "triage"} for the health view of one repository."""
    t = i18n.t
    repo = view["repo"]
    ci, alerts = facts(view)
    red = [_line(w.get("workflow") or w.get("name") if isinstance(w, dict) else w) for w in ci.get("red_workflows") or []]
    lines = [f"## {_line(repo)}", "", f"- {t('ui.assistant.report_state')}: {_line(view.get('state'))}"]
    lines.append(f"- {t('ui.assistant.report_reliability')}: {t('ui.assistant.report_runs', runs=ci.get('runs_24h', '-'), failures=ci.get('failures_24h', '-'), rate=ci.get('success_rate_24h', '-'))}")
    lines.append(f"- {t('ui.assistant.report_red')}: {', '.join(red) or t('ui.assistant.report_none')}")
    lines += ["", f"### {t('ui.assistant.report_alerts')}"]
    lines += [f"- [{_line(a.get('level'))}] {_line(a.get('title'))}" for a in alerts] or [f"- {t('ui.assistant.report_none')}"]
    triage = [t("ui.assistant.triage_head", repo=_line(repo)), ""]
    triage += [t("ui.assistant.triage_red", workflows=", ".join(red))] if red else [t("ui.assistant.triage_green")]
    if alerts:
        triage.append(t("ui.assistant.triage_first", alert=_line(alerts[0].get("title"))))
    triage += ["", t("ui.assistant.triage_next")]
    return {"markdown": redactor.redact("\n".join(lines)), "triage": redactor.redact("\n".join(triage))}
