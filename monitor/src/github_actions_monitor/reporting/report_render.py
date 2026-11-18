# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A report document (`builder.build`) as one self-contained HTML page and as Markdown, in a language of the product. The page has no script, no font, no image and no outside address: it opens from a file, and its print style makes the browser's "print to PDF" a clean A4. Every text that comes from the data is escaped (HTML) or stripped of what Markdown would read as formatting."""
import html
import re

from github_actions_monitor import i18n
from github_actions_monitor.compare import metrics as compare_metrics

CSS = ("body{font:14px/1.5 system-ui,Segoe UI,sans-serif;margin:24px auto;max-width:860px;padding:0 16px;color:#1b1f24;background:#fff}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:22px 0 6px;border-bottom:1px solid #d0d7de}"
       "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:4px 8px;border-bottom:1px solid #e5e8eb;vertical-align:top}.mut{color:#57606a}.big{font-size:34px;font-weight:700}"
       ".bad{color:#b42318}.warn{color:#b54708}.ok{color:#1a7f37}@media(prefers-color-scheme:dark){body{background:#0d1117;color:#e6edf3}th,td,h2{border-color:#30363d}.mut{color:#9198a1}}"
       "@media print{body{margin:0;max-width:none;background:#fff;color:#000}h2{break-after:avoid}tr{break-inside:avoid}}")
MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#|~!])")


AUTOLINK = re.compile(r"(?i)\b(https?|ftp):(?=//)|\bwww(?=\.)")


def _md(text):
    """Markdown-safe text: the marks are escaped and an address is broken (a zero-width space after the scheme) so that a visor of Markdown does not turn a stranger's text into a link."""
    text = MD_SPECIAL.sub(r"\\\1", str(text if text is not None else "")).replace("\r", " ").replace("\n", " ")
    return AUTOLINK.sub(lambda m: m.group(0) + "\u200b", text)


def _num(value):
    return "-" if value is None else (f"{value:g}" if isinstance(value, (int, float)) else str(value))


def _texts(lang):
    t = lambda key, **kw: i18n.tl(lang, "report." + key, **kw)      # noqa: E731
    return t


def score_line(doc, t):
    s = doc["score"]
    if s["state"] == "scored":
        trend = s.get("trend") or {}
        words = t("trend_" + str(trend.get("direction") or "flat"), delta=_num(abs(trend["delta"]) if isinstance(trend.get("delta"), (int, float)) else ""))
        return t("score_line", score=_num(s["score"]), letter=s.get("letter") or "-", trend=words)
    return t("score_none", state=t("state_" + s["state"]) if s["state"] in ("calibrating", "insufficient_data", "off") else s["state"])


def changes_lines(doc, t):
    c = doc["changes"]
    if c["first"]:
        return [t("changes_first")]
    lines = [t("changes_score", delta=("%+g" % c["score_delta"]) if c["score_delta"] is not None else "-"), t("changes_alerts", new=len(c["new_alerts"]), gone=c["gone_alerts"])]
    return lines


def compare_lines(doc, t, lang):
    """The lines of the section "comparison with the period before": one per figure, or the reason there is none."""
    part = doc.get("compare")
    if not part:
        return []
    lines = []
    if part["state"] in ("calibrating", "baseline_unavailable", "off"):
        reason = part.get("reason") or part["state"]
        lines.append(t("compare_none", reason=i18n.tl(lang, "ui.cmp_reason_" + reason) if reason in ("no_history", "watched_briefly", "history_too_short", "before_history") else reason))
    for row in part["rows"]:
        name = i18n.tl(lang, "ui.cmp_m_" + row["metric"]) if row["metric"] in ("red_rate", "duration_p50", "resolution", "score_mean", "score_coverage") else row["metric"]
        if row["state"] == "ok":
            lines.append(t("compare_line", metric=name, now=compare_metrics.humanize(row["metric"], row["now"]), base=compare_metrics.humanize(row["metric"], row["base"]),
                           direction=i18n.tl(lang, "ui.cmp_dir_" + str(row["direction"]))))
        else:
            lines.append(f"{name}: " + i18n.tl(lang, "ui.cmp_insufficient" if row["state"] == "insufficient_data" else "ui.cmp_unavailable"))
    return lines


def markdown(doc, lang="en"):
    t = _texts(lang)
    out = [f"# {_md(t('title', account=doc['account']))}", "", f"{_md(t('generated', when=doc['generated_at']))}", "", f"## {t('h_score')}", "", _md(score_line(doc, t))]
    if doc["score"]["missing_parts"]:
        out += ["", _md(t("missing", parts=", ".join(doc["score"]["missing_parts"])))]
    out += ["", f"## {t('h_changes')}", ""] + [f"- {_md(x)}" for x in changes_lines(doc, t)]
    if doc.get("compare"):
        out += ["", f"## {t('h_compare')}", ""] + [f"- {_md(x)}" for x in compare_lines(doc, t, lang)]
    team = doc["team"]
    tot = team["totals"]
    out += ["", f"## {t('h_team')}", "", _md(t("team_totals", bad=tot.get("bad", 0), warn=tot.get("warn", 0), ok=tot.get("ok", 0), unknown=tot.get("unknown", 0), all=team["all"])), ""]
    if team["ranking"]:
        out += [f"| {t('c_repo')} | {t('c_state')} | {t('c_risk')} | {t('c_alerts')} |", "|---|---|---|---|"]
        out += [f"| {_md(r['repo'])} | {_md(t('sev_' + str(r['state'])))} | {_md(r['risk'])} | {_md(r['alerts'])} |" for r in team["ranking"]]
    else:
        out.append(_md(t("none")))
    al = doc["alerts"]
    out += ["", f"## {t('h_alerts')}", "", _md(t("alerts_total", n=al["total"])), ""]
    out += [f"- **{_md(a['level'])}** {_md(a['sentinel'])} {_md(a['repo'])}: {_md(a['title'])}" for a in al["items"]] or [_md(t("none"))]
    out += ["", "---", _md(t("footer"))]
    return "\n".join(out) + "\n"


def page(doc, lang="en"):
    t = _texts(lang)
    e = html.escape
    s, team, al = doc["score"], doc["team"], doc["alerts"]
    tot = team["totals"]
    body = [f"<h1>{e(t('title', account=doc['account']))}</h1>", f"<div class=\"mut\">{e(t('generated', when=doc['generated_at']))}</div>",
            f"<h2>{e(t('h_score'))}</h2>", f"<div class=\"big\">{e(_num(s['score']) if s['state'] == 'scored' else '-')}</div>", f"<div>{e(score_line(doc, t))}</div>"]
    if s["missing_parts"]:
        body.append(f"<div class=\"mut\">{e(t('missing', parts=', '.join(s['missing_parts'])))}</div>")
    body += [f"<h2>{e(t('h_changes'))}</h2>", "<ul>" + "".join(f"<li>{e(x)}</li>" for x in changes_lines(doc, t)) + "</ul>"]
    if doc.get("compare"):
        body += [f"<h2>{e(t('h_compare'))}</h2>", "<ul>" + "".join(f"<li>{e(x)}</li>" for x in compare_lines(doc, t, lang)) + "</ul>"]
    body += [
             f"<h2>{e(t('h_team'))}</h2>", f"<div>{e(t('team_totals', bad=tot.get('bad', 0), warn=tot.get('warn', 0), ok=tot.get('ok', 0), unknown=tot.get('unknown', 0), all=team['all']))}</div>"]
    if team["ranking"]:
        body.append(f"<table><thead><tr><th>{e(t('c_repo'))}</th><th>{e(t('c_state'))}</th><th>{e(t('c_risk'))}</th><th>{e(t('c_alerts'))}</th></tr></thead><tbody>" + "".join(
            f"<tr><td>{e(r['repo'])}</td><td class=\"{'bad' if r['state'] == 'bad' else 'warn' if r['state'] == 'warn' else 'ok' if r['state'] == 'ok' else 'mut'}\">{e(t('sev_' + str(r['state'])))}</td>"
            f"<td>{e(str(r['risk']))}</td><td>{e(str(r['alerts']))}</td></tr>" for r in team["ranking"]) + "</tbody></table>")
    else:
        body.append(f"<div class=\"mut\">{e(t('none'))}</div>")
    body += [f"<h2>{e(t('h_alerts'))}</h2>", f"<div>{e(t('alerts_total', n=al['total']))}</div>"]
    body.append("<ul>" + "".join(f"<li><b>{e(str(a['level']))}</b> {e(str(a['sentinel']))} {e(a['repo'])}: {e(a['title'])}</li>" for a in al["items"]) + "</ul>" if al["items"] else f"<div class=\"mut\">{e(t('none'))}</div>")
    body.append(f"<p class=\"mut\">{e(t('footer'))}</p>")
    return (f"<!doctype html><html lang=\"{e(lang)}\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{e(t('title', account=doc['account']))}</title><style>{CSS}</style></head><body>{''.join(body)}</body></html>")
