# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One catalogued brief for every tab of the page, and the master index that lists them: how an AI tool reads EVERYTHING the monitor shows, tab by tab, in a form a machine can walk. Standard library only,
both editions. Read only: the brief of a tab is the part of the signals (signals.py) that the tab draws, plus the routes where its raw data live; it carries no key, no token and no secret (the caller
cleans the document with the same redactor as the rest of the feed).

  CATALOG                   tab -> {"prefixes": ids of signals, "sources": routes with the data, "kind": what the tab is}
  index(state, lang, ...)   the master index: one entry per tab, the routes of the AI channels, the edition
  brief(tab, state, lang)   the document of one tab (None for a tab that does not exist)
  note_access(...)          the optional record of who read which brief (no secret, no text of the signals)
"""
import json
import time

from github_actions_monitor.security import private_io, redactor

SCHEMA = 1
LITE_TABS = ("now", "charts", "repos", "hist", "cfg")
ACCESS_FILE = "ai_access.jsonl"
ACCESS_MAX_BYTES = 256 * 1024

# Every tab of the page. `prefixes`: the signals the tab draws (an id equal to the prefix or starting with it + "."); `sources`: where the raw data of the tab live; `kind`: how to read it.
CATALOG = {
    "now": {"prefixes": ["now", "quota", "connection", "health.refresh"], "sources": ["/api/data", "/api/quota"], "kind": "live"},
    "al": {"prefixes": ["alerts"], "sources": ["/api/ai/alerts"], "kind": "live"},
    "charts": {"prefixes": ["now", "sentinel.a3"], "sources": ["/api/data"], "kind": "trend"},
    "sent": {"prefixes": ["sentinel"], "sources": ["/api/sentinel"], "kind": "panel"},
    "sci": {"prefixes": ["sentinel", "now"], "sources": ["/api/sentinel"], "kind": "panel"},
    "scol": {"prefixes": ["sentinel.collab", "alerts"], "sources": ["/api/sentinel"], "kind": "panel"},
    "ssec": {"prefixes": ["alerts"], "sources": ["/api/sentinel"], "kind": "panel"},
    "sdel": {"prefixes": ["alerts"], "sources": ["/api/sentinel/delivery"], "kind": "panel"},
    "ssup": {"prefixes": ["alerts"], "sources": ["/api/sentinel/supply"], "kind": "panel"},
    "strend": {"prefixes": ["sentinel.a3"], "sources": ["/api/sentinel"], "kind": "trend"},
    "syvt": {"prefixes": ["sentinel.a3"], "sources": ["/api/compare"], "kind": "trend"},
    "team": {"prefixes": ["alerts", "now.runs"], "sources": ["/api/team"], "kind": "ranking"},
    "fleet": {"prefixes": ["alerts", "now.runs"], "sources": ["/api/team"], "kind": "ranking"},
    "repos": {"prefixes": ["repos"], "sources": ["/api/repos"], "kind": "inventory"},
    "rep": {"prefixes": [], "sources": ["/api/reports"], "kind": "report"},
    "trep": {"prefixes": [], "sources": ["/api/report-files"], "kind": "report"},
    "les": {"prefixes": [], "sources": ["/api/ai/lessons", "/api/ai/failures"], "kind": "library"},
    "hist": {"prefixes": ["now.fail24"], "sources": ["/api/data"], "kind": "history"},
    "upd": {"prefixes": [], "sources": ["/api/updates/status"], "kind": "tool"},
    "cfg": {"prefixes": ["health"], "sources": ["/api/settings"], "kind": "settings"},
}
CHANNELS = ("/api/ai/index", "/api/ai/briefs", "/api/ai/state", "/api/ai/brief", "/api/ai/alerts", "/api/ai/lessons", "/api/skills")


def _matches(signal_id, prefixes):
    return any(signal_id == p or signal_id.startswith(p + ".") for p in prefixes)


def tabs():
    return tuple(CATALOG)


def _title(tab, lang, translate):
    text = translate(lang, "ui.tab_" + tab) if translate else ""
    return text if text and text != "ui.tab_" + tab else tab


def index(state, lang="en", translate=None):
    """The master index: machine readable, one entry per tab, the same in both editions (a tab the lite edition does not have says so)."""
    lite = (state or {}).get("edition") == "lite"
    entries = []
    for tab, info in CATALOG.items():
        available = (tab in LITE_TABS) if lite else True
        entries.append({"tab": tab, "title": _title(tab, lang, translate), "kind": info["kind"], "available": available, "brief": f"/api/ai/briefs?tab={tab}",
                        "signals": list(info["prefixes"]), "sources": list(info["sources"])})
    return {"schema": SCHEMA, "kind": "ai-index", "edition": (state or {}).get("edition", "complete"), "version": (state or {}).get("version", ""), "generated_epoch": int(time.time()),
            "briefs": entries, "channels": list(CHANNELS), "read_only": True,
            "note": "every brief is read only and carries no secret; a tab with available=false does not exist in this edition"}


def brief(tab, state, lang="en", translate=None):
    """The brief of one tab, or None when there is no such tab."""
    info = CATALOG.get(tab)
    if info is None:
        return None
    lite = (state or {}).get("edition") == "lite"
    available = (tab in LITE_TABS) if lite else True
    found = [s for s in (state or {}).get("signals", []) if _matches(str(s.get("id", "")), info["prefixes"])] if available else []
    return {"schema": SCHEMA, "kind": "ai-brief", "tab": tab, "title": _title(tab, lang, translate), "tab_kind": info["kind"], "available": available,
            "edition": (state or {}).get("edition", "complete"), "version": (state or {}).get("version", ""), "generated_epoch": int(time.time()),
            "act": sum(max(1, len(s.get("rows") or [])) for s in found if s.get("level") == "act" and not s.get("transient")), "watch": sum(1 for s in found if s.get("level") == "watch"),
            "signals": found, "sources": list(info["sources"]), "index": "/api/ai/index",
            "note": "" if available else "this tab does not exist in this edition: that is not missing data"}


def note_access(folder, tab, client="", now=None):
    """One line per read: when, which brief, who asks (the User-Agent, cut). Never a signal, never a text of the page. The file stays under ACCESS_MAX_BYTES (the oldest half goes). True when written."""
    now = time.time() if now is None else now
    try:
        from pathlib import Path
        path = Path(folder) / ACCESS_FILE
        private_io.private_dir(path.parent)
        line = json.dumps({"at": int(now), "tab": str(tab)[:12], "client": redactor.redact("".join(c for c in str(client or "") if c.isprintable()), 60)}, ensure_ascii=True)
        if path.is_file() and path.stat().st_size > ACCESS_MAX_BYTES:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            private_io.write_private(path, "\n".join(lines[len(lines) // 2:]) + "\n")
        with private_io.open_append(path) as handle:
            handle.write(line + "\n")
        return True
    except OSError:
        return False


def read_access(folder, limit=200):
    """The last `limit` lines of the record, newest last; [] when there is none."""
    try:
        from pathlib import Path
        out = []
        for line in (Path(folder) / ACCESS_FILE).read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out
    except OSError:
        return []
