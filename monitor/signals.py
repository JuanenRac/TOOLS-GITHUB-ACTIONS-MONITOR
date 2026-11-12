# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The inventory of SIGNALS: everything the monitor says on its page, as data, for an AI tool (and for anybody who is not looking at the page). Standard library only, both editions.

A signal is {"id", "panel", "level", "summary", "rows", "transient"}; level "act" = somebody has to do something, "watch" = keep an eye on it, "info" = nothing to do. A row is
{"repo", "text", "url", "age_seconds", "next"}: where, what, a link, how old it is and the next step that makes sense. The same inventory feeds `GET /api/ai/state`, the brief ("What to do now",
"Pending", "Monitor health"), the MCP tools and the counter "N signals to act on".

  inventory(data, panels, edition, health)  the list of signals
  state(...)                                the document of /api/ai/state (versioned: "schema")
  brief_sections(state)                     the Markdown blocks for ALERTS_BRIEF.md
  COVERAGE                                  every tile / tab / panel of the page -> the signal that says it (or "decorative"): a test walks the page and fails for an element not listed

The lite edition has no sentinel: its state says `"edition": "lite"` and lists the panels that do not exist there, so nobody takes a missing panel for missing data.
"""
import time

SCHEMA = 1
LEVELS = ("info", "watch", "act")
SENTINEL_PANELS = ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a11", "a12", "a13", "collab")
_MAP = {"bad": "act", "warn": "watch"}

# element of the page -> id of the signal that carries it ("decorative" = it shows nothing to act on, with the reason)
COVERAGE = {
    "tab:now": "now.runs", "tab:al": "alerts.unresolved", "tab:sent": "sentinel.*", "tab:charts": "decorative: trends are drawn from the same data (see sentinel.a3 and now.runs)",
    "tab:repos": "repos.errors", "tab:hist": "now.fail24", "tab:cfg": "health.doctor",
    "tile:kt-active": "now.runs", "tile:kt-queued": "now.runs", "tile:kp-fail": "now.fail24", "tile:kt-ok": "decorative: successes need nothing",
    "tile:kt-min": "decorative: compute minutes are in sentinel.a7", "tile:kt-issues": "alerts.issues", "tile:kp-red": "alerts.unresolved", "tile:kp-sign": "sentinel.a5",
    "tile:kt-repos": "decorative: a count of repositories", "tile:kt-hot": "decorative: a count of hot repositories", "tile:kt-mode": "health.mode",
    "tile:kt-etag": "decorative: reads saved by the cache", "tile:kt-quota": "quota", "tile:kt-conn": "connection", "tile:kt-upd": "health.refresh", "tile:kt-loading": "health.refresh",
}


def _level(word):
    return _MAP.get(word, "info")


def _signal(sid, panel, level, summary, rows=None, transient=False):
    return {"id": sid, "panel": panel, "level": level, "summary": str(summary)[:240], "rows": list(rows or [])[:40], "transient": bool(transient)}


def _row(repo, text, url="", age=None, nxt=""):
    return {"repo": str(repo or "")[:120], "text": str(text or "")[:200], "url": str(url or "")[:300], "age_seconds": age, "next": nxt}


def _age(stamp, now):
    try:
        import actions_monitor
        started = actions_monitor.parse_time(stamp)
        return max(0, int(now - started.timestamp())) if started else None
    except Exception:   # noqa: BLE001 - an unreadable time is "unknown age", not an error
        return None


def inventory(data, panels=None, health=None, now=None):
    """The signals of one cycle. `data` is what the page reads (/api/data), `panels` the output of sentinel_panels.panels (complete edition), `health` a dict of the health of the monitor."""
    now = time.time() if now is None else now
    data = data or {}
    out = []
    figures = data.get("figures") or {}
    active = data.get("active") or []
    stuck = [r for r in active if r.get("stuck")]
    out.append(_signal("now.runs", "now", "act" if stuck else "info", f"{figures.get('active', 0)} running, {figures.get('queued', 0)} queued" + (f", {len(stuck)} stuck" if stuck else ""),
                       [_row(r.get("repo"), f"{r.get('name')} {r.get('status')} {int((r.get('seconds') or 0) // 60)} min", r.get("url"), r.get("seconds"), "look at the run; cancel or re-run it") for r in stuck]))
    failing = data.get("failing") or []
    out.append(_signal("alerts.unresolved", "alerts", "act" if failing else "info", f"{len(failing)} workflow(s) red on the default branch",
                       [_row(r.get("repo"), f"{r.get('name')}: {r.get('conclusion')}", r.get("url"), _age(r.get("started"), now), "open the log of the run, find the first failing step and fix it") for r in failing]))
    issues = data.get("issues") or []
    out.append(_signal("alerts.issues", "alerts", "act" if issues else "info", f"{len(issues)} open issue(s) of failed builds",
                       [_row(i.get("repo"), f"#{i.get('number')} {i.get('title')}", i.get("url"), _age(i.get("created"), now), "read the issue and the run it names") for i in issues]))
    out.append(_signal("now.fail24", "now", "info", f"{figures.get('fail24', 0)} failure(s) and {figures.get('ok24', 0)} success(es) in the last 24 h"))
    errors = data.get("errors") or {}
    out.append(_signal("repos.errors", "repos", "watch" if errors else "info", f"{len(errors)} repositor(ies) without data", [_row(k, v, "", None, "wait: reads are repeated by themselves") for k, v in list(errors.items())[:20]], transient=True))
    block = data.get("quota_block") or {}
    rate = data.get("rate") or {}
    if block.get("blocked"):
        out.append(_signal("quota", "now", "watch", f"GitHub allowance used up until {block.get('until')}: reads wait, {block.get('unread', 0)} repositories not refreshed",
                           [_row("", "the allowance is shared by every tool of the account", "", None, "do not call the API until the renewal; work locally")], transient=True))
    else:
        low = rate.get("remaining") is not None and data.get("paused_quota")
        out.append(_signal("quota", "now", "watch" if low else "info", f"allowance {rate.get('remaining')}/{rate.get('limit')}, renews {rate.get('reset')}" if rate else "allowance unknown",
                           [_row("", "below the floor: the loop slows down", "", None, "keep other tools from spending the allowance")] if low else [], transient=bool(low)))
    etag = data.get("etag") or {}
    sources = data.get("rate_sources") or {}
    trend = data.get("quota_trend") or {}
    if trend:
        out.append(_signal("quota.trend", "now", "watch" if trend.get("others_warn") else "info",
                           f"over {trend.get('minutes')} min the account spent {trend.get('all_per_hour')} calls an hour, this monitor {trend.get('own_per_hour')} and other tools about {trend.get('others_per_hour')}" +
                           ("; other tools are spending most of the allowance" if trend.get("others_warn") else ""), transient=bool(trend.get("others_warn"))))
    if etag.get("calls") is not None or len(sources) > 1:
        rows = [_row(name, f"{info.get('remaining')}/{info.get('limit')} calls left, renews {info.get('reset')}", "", None, "") for name, info in sources.items()]
        out.append(_signal("quota.accounting", "now", "info", f"reads: {etag.get('calls', 0)} conditional calls, {etag.get('saved', 0)} answered 304 (no allowance spent)" + (f"; {len(sources)} sources read the repositories" if len(sources) > 1 else ""), rows))
    offline = (data.get("offline") or {}).get("offline")
    out.append(_signal("connection", "now", "watch" if offline else "info", "offline since " + str((data.get("offline") or {}).get("since")) if offline else "online", transient=bool(offline)))
    for panel in panels or []:
        rows = [_row(r.get("repo"), r.get("text"), r.get("url"), None, "open the panel " + panel["id"].upper() + " of the Sentinel tab and deal with it") for r in panel.get("rows") or []]
        out.append(_signal("sentinel." + panel["id"], panel["id"], _level(panel.get("level")), panel.get("summary") or panel.get("title"), rows))
    health = health or {}
    out.append(_signal("health.refresh", "health", "watch" if health.get("stale") else "info", f"data read {health.get('age_seconds', '?')} s ago", transient=bool(health.get("stale"))))
    low = health.get("working_mode") == "low"
    out.append(_signal("health.mode", "health", "watch" if low else "info", f"working mode {health.get('working_mode', 'normal')}" + (" (automatic)" if health.get("auto_mode") else "") +
                       (f": the allowance is low, the monitor reads less and its figures can be old (the last reading was {health.get('age_seconds', '?')} s ago)" if low else ""), transient=low))
    central = health.get("central")
    if central:
        import central_source
        rows = []
        if central.get("ok") and not central.get("stale"):
            rows = [_row(r.get("repo"), f"{r.get('wf') or r.get('workflow')}: red on the default branch (central panel)", "", _age(r.get("since"), now), "open the log of the run (or wait for your own reading to confirm)") for r in central["data"]["ci"]["red"]]
        out.append(_signal("health.central", "health", "watch" if (not central.get("ok") or central.get("stale")) else "info", central_source.summary(central), rows, transient=not central.get("ok") or bool(central.get("stale"))))
    out.append(_signal("health.doctor", "health", "watch" if health.get("warnings") else "info", "; ".join(health.get("warnings") or []) or "no warning",
                       [_row("", w, "", None, "run the doctor: python actions_monitor.py --doctor") for w in health.get("warnings") or []]))
    return out


def state(data, panels, edition, health=None, now=None, version=""):
    """The document of `GET /api/ai/state`: versioned, read only, with the counters the page and the brief show."""
    now = time.time() if now is None else now
    signals = inventory(data, panels, health, now)
    missing = [p for p in SENTINEL_PANELS] if edition == "lite" else []
    return {"schema": SCHEMA, "edition": edition, "version": version, "generated_epoch": int(now), "signals": signals,
            "act": sum(max(1, len(s["rows"])) for s in signals if s["level"] == "act" and not s["transient"]),
            "watch": sum(1 for s in signals if s["level"] == "watch"), "panels_not_in_this_edition": missing,
            "note": "the lite edition has no sentinel: the panels listed are not missing data, they do not exist here" if missing else ""}


EVENT_SIGNALS = ("quota", "quota.trend", "connection", "repos.errors", "health.refresh", "health.central", "health.doctor", "health.mode")


def extra_alert_rows(doc):
    """The signals that are not a red workflow or a sentinel panel (those already travel as alerts) and that say "watch" or "act", as rows for the feed: the stream, the hook and the brief then carry an event
    when the allowance is used up, the connection drops, the data go stale or the central panel is behind, and another when it is solved."""
    out = []
    for sig in doc["signals"]:
        if sig["id"] in EVENT_SIGNALS and sig["level"] in ("act", "watch"):
            out.append({"repo": "monitor", "workflow": sig["id"], "conclusion": "panel", "streak": 1, "since": None, "url": "", "panel": sig["panel"], "level": "bad" if sig["level"] == "act" else "warn",
                        "detail": sig["summary"], "title": sig["id"]})
    return out


def brief_sections(doc):
    """Markdown for the brief: what to do now (act, with the next step), pending things (watch) and the health of the monitor."""
    lines = ["## What to do now", ""]
    acts = [s for s in doc["signals"] if s["level"] == "act" and s["rows"]]
    if not acts:
        lines.append("- Nothing needs a person right now.")
    for s in acts:
        lines.append(f"- {s['id']}: {s['summary']}")
        for r in s["rows"][:6]:
            lines.append(f"  - {r['repo']}: {r['text']}" + (f" ({r['age_seconds'] // 60} min old)" if isinstance(r.get("age_seconds"), int) else "") + (f" -> {r['next']}" if r.get("next") else "") + (f" {r['url']}" if r.get("url") else ""))
    lines += ["", "## Pending", ""]
    watch = [s for s in doc["signals"] if s["level"] == "watch" and not s["id"].startswith("health.")]
    lines += [f"- {s['id']}: {s['summary']}" + (" (passing: it usually clears by itself)" if s["transient"] else "") for s in watch] or ["- Nothing pending."]
    lines += ["", "## Monitor health", ""]
    lines += [f"- {s['id']}: {s['summary']}" for s in doc["signals"] if s["id"].startswith(("health.", "connection", "quota"))]
    lines.append(f"- edition: {doc['edition']}" + (" (panels not in this edition: " + ", ".join(doc["panels_not_in_this_edition"]) + ")" if doc["panels_not_in_this_edition"] else "") + f"; signals to act on: {doc['act']}")
    return "\n".join(lines) + "\n"
