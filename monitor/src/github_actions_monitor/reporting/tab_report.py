# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The report of one tab of the page: ONE function builds it as a structure and everything else is made from that structure, so the text file, the data file, the PDF and the printed page can never
differ. Standard library only, both editions, read only (it reads what the monitor already holds, never GitHub).

  settings(config)                 the `report_export.*` settings with their conservative defaults
  build(tab, state, lang, ...)     the structure of the report of a tab (None for a tab that does not exist)
  render_text(report)              the same report as plain text
  pdf_route(lang, preference)      "own" (the PDF written by the monitor) or "browser" (the print of the browser) for a language and a preference
  file_name(template, tab, date)   the suggested name of a file, without extension

The structure: title, subtitle, meta [{label, value}], figures [{label, value, level}], alerts [{level, repo, text}] and sections [{title, columns, rows, empty}], plus the fixed words already in the
language asked for, so the page and the PDF draw it without knowing any language.
"""
import re
import time

from github_actions_monitor.data_pipeline import briefs

SCHEMA = 1
PRODUCT = "GitHub Actions Monitor"
PAPER = ("a4", "letter")
PDF_PATH = ("auto", "own", "browser")
BROWSER_ONLY = ("ja", "zh")      # the standard fonts of a PDF do not hold these scripts: the print of the browser (which has the fonts) makes their PDF
DEFAULTS = {"txt": True, "pdf": True, "json": False, "name": "monitor-{tab}-{date}", "paper": "a4", "pdf_path": "auto"}
NAME_RE = re.compile(r"^[A-Za-z0-9._{}-]{1,80}\Z")
MAX_ALERTS = 30
MAX_ROWS = 60


def settings(config):
    """The `report_export` block read with its defaults: a value that is not valid falls back to the default (never an error)."""
    block = (config or {}).get("report_export") if isinstance((config or {}).get("report_export"), dict) else {}
    out = dict(DEFAULTS)
    for key in ("txt", "pdf", "json"):
        if isinstance(block.get(key), bool):
            out[key] = block[key]
    if isinstance(block.get("name"), str) and NAME_RE.match(block["name"]):
        out["name"] = block["name"]
    if block.get("paper") in PAPER:
        out["paper"] = block["paper"]
    if block.get("pdf_path") in PDF_PATH:
        out["pdf_path"] = block["pdf_path"]
    return out


def pdf_route(lang, preference="auto"):
    """Which way the PDF is made: the monitor writes its own for the Latin languages; Japanese and Chinese (and a preference for the browser) use the print of the browser."""
    if lang in BROWSER_ONLY or preference == "browser":
        return "browser"
    return "own"


def file_name(template, tab, date):
    """The suggested name of a saved file, without its extension: `{tab}` and `{date}` are replaced and anything outside letters, digits, dot, dash and underscore is dropped."""
    text = (template if NAME_RE.match(str(template or "")) else DEFAULTS["name"]).replace("{tab}", str(tab)).replace("{date}", str(date))
    return re.sub(r"[^A-Za-z0-9._-]", "", text)[:100] or "monitor-report"


def _age(seconds):
    if seconds is None:
        return ""
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""
    if seconds < 3600:
        return "%d min" % (seconds // 60)
    if seconds < 86400:
        return "%d h" % (seconds // 3600)
    return "%d d" % (seconds // 86400)


def _words(lang, translate):
    def word(key):
        found = translate(lang, "ui.rx_" + key) if translate else ""
        return found if found and found != "ui.rx_" + key else key
    return word


def _generic(found, word):
    figures = [{"label": s.get("id", ""), "value": s.get("summary", ""), "level": s.get("level", "info")} for s in found]
    alerts = []
    for s in found:
        if s.get("level") not in ("act", "watch") or s.get("transient"):
            continue
        rows = s.get("rows") or []
        if not rows:
            alerts.append({"level": s["level"], "repo": "", "text": s.get("summary", "")})
        for row in rows:
            alerts.append({"level": s["level"], "repo": row.get("repo", ""), "text": row.get("text", "")})
    sections = []
    for s in found:
        rows = s.get("rows") or []
        if rows:
            sections.append({"title": s.get("summary", s.get("id", "")), "columns": [word("col_repo"), word("col_what"), word("col_age"), word("col_next")],
                             "rows": [[r.get("repo", ""), r.get("text", ""), _age(r.get("age_seconds")), r.get("next", "")] for r in rows[:MAX_ROWS]], "empty": word("none")})
    return figures, alerts, sections


def _now_tab(data, word, found):
    """Now: the running workflows and the ones that are red, with the main figures of the day."""
    data = data or {}
    figs = data.get("figures") or {}
    figures = [{"label": word("fig_active"), "value": figs.get("active", 0), "level": "info"}, {"label": word("fig_queued"), "value": figs.get("queued", 0), "level": "info"},
               {"label": word("fig_fail24"), "value": figs.get("fail24", 0), "level": "watch" if figs.get("fail24") else "info"}, {"label": word("fig_ok24"), "value": figs.get("ok24", 0), "level": "info"},
               {"label": word("fig_red"), "value": len(data.get("failing") or []), "level": "act" if data.get("failing") else "info"}]
    sections = [{"title": word("running"), "columns": [word("col_repo"), word("col_workflow"), word("col_status"), word("col_minutes")],
                 "rows": [[r.get("repo", ""), r.get("name", ""), r.get("status", ""), int((r.get("seconds") or 0) // 60)] for r in (data.get("active") or [])[:MAX_ROWS]], "empty": word("none")}]
    sections.append(_red_section(data, word))
    return figures, sections


def _red_section(data, word):
    return {"title": word("red"), "columns": [word("col_repo"), word("col_workflow"), word("col_status")],
            "rows": [[r.get("repo", ""), r.get("name", ""), r.get("conclusion", "")] for r in (data.get("failing") or [])[:MAX_ROWS]], "empty": word("none")}


def _alerts_tab(data, word):
    data = data or {}
    sections = [_red_section(data, word), {"title": word("issues"), "columns": [word("col_repo"), word("col_number"), word("col_title")],
                                           "rows": [[i.get("repo", ""), "#%s" % i.get("number", ""), i.get("title", "")] for i in (data.get("issues") or [])[:MAX_ROWS]], "empty": word("none")}]
    figures = [{"label": word("fig_red"), "value": len(data.get("failing") or []), "level": "act" if data.get("failing") else "info"},
               {"label": word("issues"), "value": len(data.get("issues") or []), "level": "act" if data.get("issues") else "info"}]
    return figures, sections


def _lessons_tab(library, word):
    rows = [[x.get("category", ""), x.get("what", ""), x.get("do", "")] for x in (library or [])[:MAX_ROWS]]
    return [{"label": word("lessons"), "value": len(library or []), "level": "info"}], [{"title": word("lessons"), "columns": [word("col_category"), word("col_lesson"), word("col_do")], "rows": rows, "empty": word("none")}]


def build(tab, state, lang="en", translate=None, data=None, library=None, now=None):
    """The report of a tab as a structure, or None when there is no such tab. `state` is the document of ai_state, `data` what the page reads, `library` the lessons of the book."""
    document = briefs.brief(tab, state, lang, translate)
    if document is None:
        return None
    word = _words(lang, translate)
    stamp = time.localtime(time.time() if now is None else now)
    found = document.get("signals") or []
    figures, alerts, sections = _generic(found, word)
    if tab == "now":
        figures, sections = _now_tab(data, word, found)
        sections += [s for s in _generic(found, word)[2] if s["title"] not in {x["title"] for x in sections}]
    elif tab == "al":
        figures, sections = _alerts_tab(data, word)
        sections += _generic(found, word)[2]
    elif tab == "les":
        figures, sections = _lessons_tab(library, word)
    if not document.get("available", True):
        sections = []
        figures = []
        alerts = []
    date = time.strftime("%Y-%m-%d", stamp)
    meta = [{"label": word("generated"), "value": time.strftime("%Y-%m-%d %H:%M", stamp)}, {"label": word("version"), "value": str(document.get("version", ""))},
            {"label": word("tab"), "value": document.get("title", tab)}]
    return {"schema": SCHEMA, "kind": "tab-report", "tab": tab, "lang": lang, "title": "%s - %s" % (PRODUCT, document.get("title", tab)), "subtitle": "" if document.get("available", True) else word("unavailable"),
            "date": date, "meta": meta, "figures_title": word("figures"), "figures": figures[:MAX_ROWS], "alerts_title": word("alerts"), "alerts": alerts[:MAX_ALERTS],
            "alerts_empty": word("none_alerts"), "sections": sections, "footer": "%s %s" % (PRODUCT, document.get("version", "")), "page_label": word("page"),
            "act": document.get("act", 0), "watch": document.get("watch", 0), "edition": document.get("edition", "complete")}


def render_text(report):
    """The report as plain text (UTF-8): the same title, figures, alerts and tables, a table row on one line with ' | ' between its cells."""
    out = [report["title"], "=" * min(len(report["title"]), 78)]
    if report.get("subtitle"):
        out.append(report["subtitle"])
    out += ["%s: %s" % (m["label"], m["value"]) for m in report.get("meta", [])]
    out += ["", report.get("figures_title", "")]
    for item in report.get("figures", []):
        out.append("  %s%s: %s" % ({"act": "[!] ", "watch": "[~] "}.get(item.get("level"), ""), item["label"], item["value"]))
    out += ["", report.get("alerts_title", "")]
    if not report.get("alerts"):
        out.append("  " + report.get("alerts_empty", ""))
    for item in report.get("alerts", []):
        out.append("  %s%s%s" % ({"act": "[!] ", "watch": "[~] "}.get(item.get("level"), "- "), (item["repo"] + ": ") if item.get("repo") else "", item["text"]))
    for section in report.get("sections", []):
        out += ["", section["title"], "-" * min(len(section["title"]), 78)]
        if not section["rows"]:
            out.append("  " + section.get("empty", ""))
            continue
        out.append("  " + " | ".join(section["columns"]))
        out += ["  " + " | ".join(str(c) for c in row) for row in section["rows"]]
    out += ["", report.get("footer", ""), ""]
    return "\n".join(out)
