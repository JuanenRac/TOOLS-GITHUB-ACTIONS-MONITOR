# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The panels of the Sentinel tab (A1..A13 and the second sentinel) as DATA, for whoever is not looking at the page: an AI tool, the brief, the feed, the command line.

The level of each panel is the one the sentinel already computes (`snapshot["aN"]["level"]`, the page shows the same word); this module adds the short summary line and the rows somebody has
to act on, each with its repository and a link, so that the page, the endpoint `GET /api/sentinel/panels`, the brief and the feed all say the same thing.

  panels(snapshot, t, analytics=None, collab=None, owner="")   [{"id", "title", "level", "summary", "rows": [{"repo", "text", "url", "level", "key"}]}]
  alert_rows(panels)                                           the rows that become alerts of the feed: level "bad" -> real, level "warn" -> watch
  brief_section(panels)                                        the Markdown block "Sentinel panels"

A panel at level "bad" is "act now", "warn" is "keep an eye on it", "ok" / "info" / "unknown" need nothing from a person.
"""
import re

ORDER = ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a11", "a12", "a13", "collab")
MAX_ROWS = 40
_HIGH = ("critical", "high")


def _text(value, limit=200):
    text = re.sub(r"\s+", " ", str(value if value is not None else "")).strip()
    return text[:limit]


def _row(repo, text, url="", level="warn", key=""):
    return {"repo": _text(repo, 120), "text": _text(text), "url": _text(url, 300), "level": level, "key": _text(key or text, 160)}


def _gh(owner, repo, tail=""):
    return f"https://github.com/{owner}/{repo}{tail}" if owner and repo else ""


def _a1(s, owner, t):
    rows = [_row(r.get("repo"), f"{r.get('name')} {r.get('status')} {int(r.get('seconds') or 0) // 60} min", r.get("url"), "bad", f"stuck:{r.get('name')}") for r in s.get("stuck") or []]
    rows += [_row(i.get("repo"), f"#{i.get('number')} {i.get('title')}", i.get("url"), "bad", f"issue:{i.get('number')}") for i in s.get("issues") or []]
    return rows, t("ui.sc_findings", n=len(rows)) if rows else t("ui.sc_none")


def _a2(s, owner, t):
    rows = [_row(r.get("repo"), f"{r.get('workflow')}: {r.get('conclusion')} x{r.get('streak')}", r.get("url"), "bad", f"red:{r.get('workflow')}") for r in s.get("red") or []]
    return rows, t("ui.a2_count", n=len(rows), w=s.get("workflows_checked", 0))


def _a3(s, owner, t):
    rows = []
    for r in s.get("rows") or []:
        sev = r.get("sev") or {}
        high = sum(int(sev.get(k, 0) or 0) for k in _HIGH)
        secrets = r.get("secret") or 0
        if not (r.get("codeql") or r.get("dependabot") or secrets):
            continue
        detail = f"CodeQL {r.get('codeql') if r.get('codeql') is not None else '-'} · Dependabot {r.get('dependabot') or 0} · " + t("ui.th_secrets") + f" {secrets}"
        if high:
            detail += " · " + ", ".join(f"{k} {sev[k]}" for k in _HIGH if sev.get(k))
        rows.append(_row(r.get("repo"), detail, _gh(owner, r.get("repo"), "/security"), "bad" if (high or secrets) else "warn", "security"))
    for a in (s.get("codeql") or [])[:MAX_ROWS]:
        if str(a.get("severity") or "").lower() in _HIGH:
            rows.append(_row(a.get("repo"), f"CodeQL {a.get('severity')}: {a.get('rule') or a.get('rule_id') or ''} {a.get('file') or a.get('path') or ''}", a.get("url"), "bad", f"codeql:{a.get('rule') or a.get('rule_id')}:{a.get('file') or a.get('path')}"))
    return rows, t("ui.a3_summary", c=s.get("codeql_total", 0), d=s.get("dependabot_total", 0), s=s.get("secret_total", 0))


def _a4(s, owner, t):
    rows = [_row(p.get("repo"), f"#{p.get('number', p.get('num'))} {p.get('title')}" + (" (major)" if p.get("major") else "") + (" (conflict)" if p.get("conflict") else ""), p.get("url"), "warn", f"pr:{p.get('number', p.get('num'))}")
            for p in s.get("dependabot") or [] if p.get("major") or p.get("conflict")]
    return rows, t("ui.sc_open", n=len(s.get("dependabot") or []))


def _a5(s, owner, t):
    rows = [_row(c.get("repo"), f"{c.get('entries')} entries since the last release", "", "warn", "candidate") for c in s.get("candidates") or []]
    rows += [_row(g.get("repo"), f"signature pending for {int(g.get('hours') or 0)} h", g.get("url"), "warn", "pending_sign") for g in s.get("pending_sign") or []]
    return rows, t("ui.sc_a5", c=len(s.get("candidates") or []), g=len(s.get("green_unreleased") or []))


def _a6(s, owner, t):
    rows = [_row(r.get("repo"), "; ".join(p.get("text", "") for p in r.get("problems") or []), "", "warn", "hygiene") for r in s.get("rows") or [] if r.get("problems")]
    return rows, t("ui.sc_violations", n=len(rows))


def _a7(s, owner, t):
    rows = [_row(b.get("ecosystem"), f"{b.get('used')} / {b.get('limit')} min ({b.get('period')})", "", "bad" if b.get("level") == "over" else "warn", "budget") for b in s.get("budget") or [] if b.get("level") != "ok"]
    return rows, t("ui.sc_a7", n=s.get("total24", 0))


def _a8(s, owner, t):
    return [], " · ".join(sorted((s.get("audits") or {}).keys()))


def _a9(s, owner, t):
    boards = s.get("boards") or []
    rows = [_row(b.get("name") or b.get("title") or b.get("repo") or "", "; ".join(str(p) for p in b.get("problems") or []), b.get("url"), "warn", "board") for b in boards if b.get("problems")]
    return rows, t("ui.sc_a9", n=len(rows), m=len(boards))


def _a10(s, owner, t):
    rows = []
    sections = s.get("sections") or []
    for sec in sections:
        if sec.get("level") in ("bad", "warn") and sec.get("count"):
            cells = [" ".join(str(c) for c in r if c not in (None, "")) if isinstance(r, (list, tuple)) else str(r) for r in (sec.get("rows") or [])[:5]]
            rows.append(_row(sec.get("title") or sec.get("key"), f"{sec.get('count')}: " + " | ".join(cells), "", sec.get("level"), f"a10:{sec.get('key')}"))
    return rows, t("ui.sc_a10", n=len([x for x in sections if x.get("count") and x.get("level") in ("bad", "warn")]), m=len(sections))


def _a11(s, owner, t):
    rows = [_row(h.get("ecosystem"), f"health {h.get('score')}", "", "warn", "health") for h in s.get("low_health") or []]
    return rows, t("ui.sc_a11", n=s.get("ready", 0), m=s.get("behind", 0))


def _a12(s, owner, t):
    rows = [_row(r.get("repo"), f"{r.get('workflow') or r.get('name')} is slower than usual", "", "warn", f"slow:{r.get('workflow') or r.get('name')}") for r in (s or {}).get("slower") or []]
    return rows, t("ui.sc_a12", n=len((s or {}).get("duration") or []), m=len((s or {}).get("flaky") or []))


def _a13(s, owner, t):
    rows = [_row(r.get("repo"), f"{r.get('file')}:{r.get('line')} {r.get('rule')}", "", "bad" if r.get("severity") == "bad" else "warn", f"lint:{r.get('rule')}:{r.get('file')}") for r in (s or {}).get("rows") or []][:MAX_ROWS]
    summary = (s or {}).get("summary") or {}
    return rows, t("ui.sc_a13", n=summary.get("findings", 0), m=summary.get("repos", 0)) if (s or {}).get("enabled") else ""


def _collab(alerts, owner, t):
    rows = [_row(a.get("repo"), a.get("title") or a.get("code"), (a.get("details") or {}).get("url"), "bad" if a.get("level") in ("bad", "error") else "warn", f"collab:{a.get('id')}") for a in alerts or []][:MAX_ROWS]
    return rows, t("ui.collab_count", n=len(alerts or []), m=0)


def _level_a12(analytics):
    if not analytics or analytics.get("enabled") is False:
        return "unknown"
    return "warn" if analytics.get("slower") else ("ok" if analytics.get("duration") else "unknown")


def _level_a13(lint):
    if not lint or not lint.get("enabled"):
        return "unknown"
    summary = lint.get("summary") or {}
    return "bad" if summary.get("bad") else ("warn" if summary.get("warn") else "ok")


def panels(snapshot, t, analytics=None, collab=None, owner=""):
    """The panels of one snapshot of the sentinel, in the order of the page. `t` translates ("ui.a3_title"...); `analytics` is the summary of A12, `collab` the list of alerts of the second sentinel."""
    s = snapshot or {}
    if s.get("enabled") is False or not s:
        return []
    builders = {"a1": (_a1, s.get("a1")), "a2": (_a2, s.get("a2")), "a3": (_a3, s.get("a3")), "a4": (_a4, s.get("a4")), "a5": (_a5, s.get("a5")), "a6": (_a6, s.get("a6")), "a7": (_a7, s.get("a7")),
                "a8": (_a8, s.get("a8")), "a9": (_a9, s.get("a9")), "a10": (_a10, s.get("a10")), "a11": (_a11, s.get("a11")), "a12": (_a12, analytics), "a13": (_a13, s.get("lint"))}
    out = []
    for key in ORDER:
        if key == "collab":
            rows, summary = _collab(collab, owner, t)
            level = "bad" if any(r["level"] == "bad" for r in rows) else ("warn" if rows else ("ok" if collab is not None else "unknown"))
            out.append({"id": key, "title": t("ui.collab_title"), "level": level, "summary": _text(summary), "rows": rows[:MAX_ROWS]})
            continue
        build, data = builders[key]
        rows, summary = build(data or {}, owner, t) if key not in ("a12", "a13") else build(data, owner, t)
        if key == "a12":
            level = _level_a12(analytics)
        elif key == "a13":
            level = _level_a13(s.get("lint"))
        else:
            level = (data or {}).get("level") or "unknown"
        out.append({"id": key, "title": t(f"ui.{key}_title"), "level": level, "summary": _text(summary), "rows": rows[:MAX_ROWS]})
    return out


def alert_rows(panel_list):
    """The rows that have to reach the feed as alerts: those of a panel at level "bad" (real) or "warn" (watch); the row keeps its own level when it is lower than the panel's."""
    out = []
    for panel in panel_list:
        if panel["level"] not in ("bad", "warn") or panel["id"] == "a2":      # A2 is the red workflows: they are already alerts of their own
            continue
        for row in panel["rows"]:
            level = "bad" if (panel["level"] == "bad" and row["level"] == "bad") else "warn"
            out.append({"repo": row["repo"] or panel["id"].upper(), "workflow": f"{panel['title']} [{row['key']}]", "conclusion": "panel", "streak": 1, "since": None,
                        "url": row["url"], "panel": panel["id"], "level": level, "detail": row["text"], "title": panel["title"]})
    return out


def brief_section(panel_list):
    """Markdown for the brief: one line per panel (id, title, level, summary) and, under each panel that needs something, its rows."""
    lines = ["## Sentinel panels", ""]
    for panel in panel_list:
        lines.append(f"- {panel['id'].upper()} {panel['title']}: {panel['level']}" + (f" - {panel['summary']}" if panel["summary"] else ""))
        if panel["level"] in ("bad", "warn"):
            for row in panel["rows"][:12]:
                lines.append(f"  - [{row['level']}] {row['repo']}: {row['text']}" + (f" {row['url']}" if row["url"] else ""))
    return "\n".join(lines) + "\n"
