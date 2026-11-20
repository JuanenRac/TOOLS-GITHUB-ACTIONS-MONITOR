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
    "tab:now": "now.runs", "tab:al": "alerts.unresolved", "tab:rep": "decorative: the optional reports are read from GET /api/reports, not from the signals", "tab:les": "decorative: the lessons are read from GET /api/ai/lessons and travel in GET /api/ai/state as lessons", "tab:sent": "sentinel.*", "tab:charts": "decorative: trends are drawn from the same data (see sentinel.a3 and now.runs)",
    "tab:repos": "repos.errors", "tab:team": "decorative: the ranking of the repositories is drawn from the alerts and the runs (see alerts.unresolved and now.runs)", "tab:sci": "decorative: the panels of the CI sentinel are the signals sentinel.* and now.* drawn by layer", "tab:scol": "decorative: the Collab sentinel alerts travel in the feed of alerts (see alerts.unresolved)", "tab:ssec": "decorative: the Security sentinel alerts travel in the feed of alerts (see alerts.unresolved)", "tab:fleet": "decorative: the fleet view groups the same ranking of the repositories as the Team health tab", "tab:trep": "decorative: the scheduled reports are files written by the monitor, listed by GET /api/report-files", "tab:sdel": "decorative: the Delivery sentinel alerts travel in the feed of alerts (see alerts.unresolved)", "tab:ssup": "decorative: the Supply chain sentinel alerts travel in the feed of alerts (see alerts.unresolved)", "tab:syvt": "decorative: yesterday against today is drawn from the reports saved by the CI sentinel (see sentinel.a3)", "tab:strend": "trend.daily", "tab:upd": "decorative: the Updates menu reads GET /api/updates/status; it is a tool for the person, not a state of the monitor", "tab:hist": "now.fail24", "tab:cfg": "health.doctor",
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
        from github_actions_monitor.app import actions_monitor
        started = actions_monitor.parse_time(stamp)
        return max(0, int(now - started.timestamp())) if started else None
    except Exception:   # noqa: BLE001 - an unreadable time is "unknown age", not an error
        return None


SENTINEL_WITH_SIGNAL = ("security", "delivery", "supply")      # the sentinels whose alerts have no panel: they travel as the signal `sentinel.<name>` (collab has its panel; the CI one has A1-A13)
SENTINEL_NAMES = ("security", "delivery", "supply", "collab")
_ALERT_LEVEL = {"critical": "act", "error": "act", "warning": "watch"}
_RANK = {"act": 2, "watch": 1, "info": 0}
_BENIGN_UNAVAILABLE = ("off", "plan", "not_found")      # a feature that is off, not in the plan, or a repository without the file: a setting of the account, not a gap of the reading


def coverage_problems(status):
    """{cause: number} of what keeps a sentinel from having read everything, from its status: reads that failed (by cause), repositories not checked yet, a pause, and sources GitHub would not answer for a
    reason that is not a plain "off" or "not in the plan". Pure; {} when nothing is missing."""
    status = status if isinstance(status, dict) else {}
    out = {}
    for e in status.get("errors") or []:
        kind = str((e or {}).get("kind") or "error") if isinstance(e, dict) else "error"
        out["read " + kind] = out.get("read " + kind, 0) + 1
    if status.get("paused"):
        out["paused"] = 1
    if status.get("unchecked"):
        out["not checked yet"] = len(status["unchecked"])
    why = status.get("unavailable_why")
    if isinstance(why, dict):      # the security sentinel: {reason: {signal: repositories}}
        for reason, row in why.items():
            if reason not in _BENIGN_UNAVAILABLE and isinstance(row, dict):
                for signal, n in row.items():
                    out[f"{reason} {signal}"] = out.get(f"{reason} {signal}", 0) + int(n or 0)
    elif isinstance(status.get("unavailable"), dict):      # the others: {reason: repositories}
        for reason, n in status["unavailable"].items():
            if reason not in _BENIGN_UNAVAILABLE and isinstance(n, int):
                out[f"unreadable {reason}"] = out.get(f"unreadable {reason}", 0) + n
    return {k: v for k, v in out.items() if v}


def sentinel_signals(reports):
    """The signals of the sentinels that have no panel. `reports` = {name: {"status": dict, "alerts": [alerts]}} of the ones that are switched on. Per sentinel in `SENTINEL_WITH_SIGNAL`, one signal
    `sentinel.<name>` with one row per (code, repository), the worst first, each row with its `code` and `level` (act / watch / info); and, for every sentinel (collab too), `sentinel.<name>.coverage`
    (watch) ONLY when part of what it should read was not read, with the causes. A sentinel with nothing open says so at level info."""
    out = []
    for name in SENTINEL_NAMES:
        rep = (reports or {}).get(name)
        if not isinstance(rep, dict):
            continue
        alerts = [a for a in rep.get("alerts") or [] if isinstance(a, dict)]
        if name in SENTINEL_WITH_SIGNAL:
            rows = []
            for a in sorted(alerts, key=lambda x: (-_RANK[_ALERT_LEVEL.get(x.get("level"), "info")], str(x.get("code")), str(x.get("repo")))):
                level = _ALERT_LEVEL.get(a.get("level"), "info")
                row = _row(a.get("repo"), a.get("title") or a.get("code"), "", None, ("open the " + name + " sentinel and deal with it") if level != "info" else "")
                row["code"], row["level"] = str(a.get("code") or ""), level
                rows.append(row)
            level = max((r["level"] for r in rows), key=_RANK.get, default="info")
            by_code = {}
            for r in rows:
                by_code[r["code"]] = by_code.get(r["code"], 0) + 1
            repos = len({r["repo"] for r in rows})
            summary = (f"{len(rows)} alert(s) in {repos} repositor(ies): " + ", ".join(f"{c} {n}" for c, n in sorted(by_code.items(), key=lambda kv: (-kv[1], kv[0]))[:6])) if rows else "no alerts"
            sig = _signal("sentinel." + name, name, level, summary, rows)
            sig["rows_total"] = len(rows)
            out.append(sig)
        problems = coverage_problems(rep.get("status"))
        if problems:
            transient = all(k.split(" ")[0] in ("read", "not", "paused") for k in problems)
            ordered = sorted(problems.items(), key=lambda kv: (-kv[1], kv[0]))
            out.append(_signal(f"sentinel.{name}.coverage", name, "watch", f"{name}: not everything was read - " + ", ".join(f"{k} {n}" for k, n in ordered[:8]),
                               [_row("", f"{k}: {n}", "", None, "an empty list of alerts does not mean clean while this is open") for k, n in ordered[:8]], transient=transient))
    return out


def inventory(data, panels=None, health=None, now=None, daily_trend=None, sentinels=None):
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
    from github_actions_monitor.data_pipeline import alertflow
    report = alertflow.silences_report(now=now)
    if report["total"]:
        attention = report["due"] + report["expired"] + report["undated"]
        out.append(_signal("alerts.silences", "alerts", "watch" if attention else "info",
                           f"{report['total']} silence(s) by pattern: {len(report['due'])} past their review date, {len(report['expired'])} expired, {len(report['undated'])} without a review date",
                           [_row(p, "silence by pattern past its review date" if p in report["due"] else ("expired silence" if p in report["expired"] else "silence without a review date"), "", None,
                                 "decide: keep it with a new date, or remove it from alerts.silences") for p in attention]))
    out.append(_signal("now.fail24", "now", "info", f"{figures.get('fail24', 0)} failure(s) and {figures.get('ok24', 0)} success(es) in the last 24 h"))
    errors = data.get("errors") or {}
    out.append(_signal("repos.errors", "repos", "watch" if errors else "info", f"{len(errors)} repositor(ies) without data", [_row(k, v, "", None, "wait: reads are repeated by themselves") for k, v in list(errors.items())[:20]], transient=True))
    drift = data.get("drift") or {}
    if drift.get("status") or drift.get("conclusion") or drift.get("malformed"):
        names = [f"status {k} ({n})" for k, n in (drift.get("status") or {}).items()] + [f"conclusion {k} ({n})" for k, n in (drift.get("conclusion") or {}).items()]
        out.append(_signal("schema.drift", "repos", "info", "GitHub sent values the monitor does not know: " + (", ".join(names[:8]) or "no named value") + (f"; {drift.get('malformed')} run(s) without a usable number left out" if drift.get("malformed") else ""),
                           [_row("", "an unknown value is never counted as red or as green: it is shown as it came", "", None, "the rules of the monitor have to learn it; report it")], transient=False))
    listing = data.get("listing") or {}
    if listing.get("suspect"):
        out.append(_signal("repos.listing", "repos", "watch", f"the listing of the account came back {'empty' if listing.get('verdict') == 'empty' else 'with far fewer repositories'} ({listing.get('now')} instead of {listing.get('before')}): the last good listing is kept",
                           [_row("", "a listing like this is not believed: it would look like everything is green with nothing watched", "", None, "wait: it is asked again in a few minutes; check the access of the token to the account")], transient=True))
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
    gql = data.get("graphql") or {}
    if etag.get("calls") is not None or len(sources) > 1 or gql.get("calls"):
        rows = [_row(name, f"{info.get('remaining')}/{info.get('limit')} calls left, renews {info.get('reset')}", "", None, "") for name, info in sources.items()]
        out.append(_signal("quota.accounting", "now", "info", f"reads: {etag.get('calls', 0)} conditional calls, {etag.get('saved', 0)} answered 304 (no allowance spent)" + (f"; {len(sources)} sources read the repositories" if len(sources) > 1 else "") +
                           (f"; GraphQL: {gql.get('calls')} batch(es) read {gql.get('repos', 0)} repositories for {gql.get('cost', 0)} point(s), {gql.get('fallbacks', 0)} went to REST" if gql.get("calls") else ""), rows))
    if etag.get("calls"):
        out.append(etag_health_signal(etag))
    offline = (data.get("offline") or {}).get("offline")
    out.append(_signal("connection", "now", "watch" if offline else "info", "offline since " + str((data.get("offline") or {}).get("since")) if offline else "online", transient=bool(offline)))
    for panel in panels or []:
        rows = [_row(r.get("repo"), r.get("text"), r.get("url"), None, "open the panel " + panel["id"].upper() + " of the Sentinel tab and deal with it") for r in panel.get("rows") or []]
        out.append(_signal("sentinel." + panel["id"], panel["id"], _level(panel.get("level")), panel.get("summary") or panel.get("title"), rows))
    out.extend(sentinel_signals(sentinels))
    if isinstance(daily_trend, dict) and daily_trend:
        out.append(trend_signal(daily_trend))
    health = health or {}
    out.append(_signal("health.refresh", "health", "watch" if health.get("stale") else "info", f"data read {health.get('age_seconds', '?')} s ago", transient=bool(health.get("stale"))))
    low = health.get("working_mode") == "low"
    out.append(_signal("health.mode", "health", "watch" if low else "info", f"working mode {health.get('working_mode', 'normal')}" + (" (automatic)" if health.get("auto_mode") else "") +
                       (f": the allowance is low, the monitor reads less and its figures can be old (the last reading was {health.get('age_seconds', '?')} s ago)" if low else ""), transient=low))
    central = health.get("central")
    if central:
        from github_actions_monitor.sentinels import central_source
        rows = []
        if central.get("ok") and not central.get("stale"):
            rows = [_row(r.get("repo"), f"{r.get('wf') or r.get('workflow')}: red on the default branch (central panel)", "", _age(r.get("since"), now), "open the log of the run (or wait for your own reading to confirm)") for r in central["data"]["ci"]["red"]]
        out.append(_signal("health.central", "health", "watch" if (not central.get("ok") or central.get("stale")) else "info", central_source.summary(central), rows, transient=not central.get("ok") or bool(central.get("stale"))))
    out.append(_signal("health.doctor", "health", "watch" if health.get("warnings") else "info", "; ".join(health.get("warnings") or []) or "no warning",
                       [_row("", w, "", None, "run the doctor: python bin/actions_monitor.py --doctor") for w in health.get("warnings") or []]))
    return out


_TREND_LEFT_OUT = ("versions", "releases", "workflows", "thresholds", "min_repo")


def _last(values):
    for value in reversed(values or []):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def _change(values, back):
    """The change of the last day against `back` days earlier; None when either day has no figure (a gap is not a zero)."""
    if not values or len(values) <= back:
        return None
    a, b = values[-1], values[-1 - back]
    ok = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b))
    return round(a - b, 2) if ok else None


def trend_signal(trend):
    """The daily trend of the sentinel as ONE signal of level info (it asks nothing of anybody): a row per series with its last figure, the change against yesterday and seven days ago and the days
    that have no figure, the series of minutes of each repository, the days a release was published and the lines of the chart. Read from the history the sentinel already keeps."""
    rows, days = [], 0
    for key, doc in sorted(trend.items()):
        if key in _TREND_LEFT_OUT or not isinstance(doc, dict) or "values" not in doc:
            continue
        values = doc.get("values") or []
        days = max(days, len(values))
        last, d1, d7 = _last(values), _change(values, 1), _change(values, 7)
        gaps = sum(1 for v in values if v is None)
        rows.append(_row("", f"{key}: {last if last is not None else 'no figure'}; change against yesterday {d1 if d1 is not None else 'unknown'}, against 7 days ago {d7 if d7 is not None else 'unknown'}; {gaps} day(s) without figure",
                         "", None, "open the Daily trend tab or read a3.trend of GET /api/sentinel"))
    per_repo = (trend.get("min_repo") or {}).get("repos") or {}
    for repo, values in list(per_repo.items())[:8]:
        rows.append(_row(repo, f"minutes24 of this repository: {_last(values) if _last(values) is not None else 'no figure'} (last of {len(values)} day(s))", "", None, "a3.trend.min_repo"))
    releases = trend.get("releases") or {}
    workflows = trend.get("workflows") or {}
    lines = trend.get("thresholds") or {}
    summary = (f"{len(rows)} series over {days} day(s); a day without a figure is a gap, never zero; releases published on {len(releases)} day(s)" + (f"; commits that touched the workflow files on {len(workflows)} day(s)" if workflows else "") +
               (": " + ", ".join(f"{k} {v}" for k, v in sorted(lines.items())) if lines else ""))
    return _signal("trend.daily", "a3", "info", summary, rows)


def state(data, panels, edition, health=None, now=None, version="", trend=None, sentinels=None):
    """The document of `GET /api/ai/state`: versioned, read only, with the counters the page and the brief show."""
    now = time.time() if now is None else now
    signals = inventory(data, panels, health, now, trend, sentinels)
    missing = [p for p in SENTINEL_PANELS] if edition == "lite" else []
    return {"schema": SCHEMA, "edition": edition, "version": version, "generated_epoch": int(now), "signals": signals,
            "act": sum(max(1, len(s["rows"])) for s in signals if s["level"] == "act" and not s["transient"]),
            "watch": sum(1 for s in signals if s["level"] == "watch"), "panels_not_in_this_edition": missing,
            "note": "the lite edition has no sentinel: the panels listed are not missing data, they do not exist here" if missing else ""}


STREAM_MAX_ROWS = 25      # events per sentinel; the rest is one more event that says how many
EVENT_SIGNALS = ("quota", "quota.trend", "connection", "repos.errors", "health.refresh", "health.central", "health.doctor", "health.mode")


def extra_alert_rows(doc):
    """The signals that are not a red workflow or a sentinel panel (those already travel as alerts) and that say "watch" or "act", as rows for the feed: the stream, the hook and the brief then carry an event
    when the allowance is used up, the connection drops, the data go stale or the central panel is behind, and another when it is solved."""
    out = []
    for sig in doc["signals"]:
        if sig["id"] in EVENT_SIGNALS and sig["level"] in ("act", "watch"):
            out.append({"repo": "monitor", "workflow": sig["id"], "conclusion": "panel", "streak": 1, "since": None, "url": "", "panel": sig["panel"], "level": "bad" if sig["level"] == "act" else "warn",
                        "detail": sig["summary"], "title": sig["id"]})
    for sig in doc["signals"]:      # the sentinels without a panel (security, delivery, supply) and their gaps of reading: one event per (code, repository), only for what asks for attention (watch / act)
        parts = sig["id"].split(".")
        if parts[0] != "sentinel" or len(parts) < 2 or parts[1] not in SENTINEL_NAMES:
            continue
        if sig["id"].endswith(".coverage"):
            if sig["level"] in ("act", "watch"):
                out.append({"repo": "monitor", "workflow": sig["id"], "conclusion": "panel", "streak": 1, "since": None, "url": "", "panel": sig["panel"], "level": "warn", "detail": sig["summary"], "title": sig["id"]})
            continue
        asking = [r for r in sig["rows"] if r.get("level") in ("act", "watch")]
        for r in asking[:STREAM_MAX_ROWS]:
            out.append({"repo": r["repo"] or sig["panel"], "workflow": r["code"], "conclusion": "panel", "streak": 1, "since": None, "url": "", "panel": sig["panel"],
                        "level": "bad" if r["level"] == "act" else "warn", "detail": r["text"], "title": sig["id"]})
        if len(asking) > STREAM_MAX_ROWS:
            out.append({"repo": sig["panel"], "workflow": sig["id"] + ".more", "conclusion": "panel", "streak": 1, "since": None, "url": "", "panel": sig["panel"], "level": "warn",
                        "detail": f"{len(asking) - STREAM_MAX_ROWS} more alert(s) not listed; see /api/sentinel/{sig['panel']}", "title": sig["id"]})
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


def etag_health_signal(etag):
    """The health of the conditional reads in one signal: the share of calls answered 304, the full answers that came without an ETag (a proxy that strips it makes the cache do nothing), the reads made in full on purpose
    because they describe something still running, and the refusals remembered. `watch` only when the cache stores nothing and answers without an ETag keep arriving."""
    calls, saved, bare = int(etag.get("calls") or 0), int(etag.get("saved") or 0), int(etag.get("no_etag") or 0)
    broken = bare >= 10 and bare > saved
    text = (f"conditional reads: {etag.get('hit_pct', 0) or 0}% of {calls} calls answered 304; {bare} full answer(s) without ETag; {int(etag.get('skipped_active') or 0)} list(s) with running work and "
            f"{int(etag.get('skipped_stateful') or 0)} read(s) of a state in motion made in full; {int(etag.get('denied_hits') or 0)} refused read(s) not repeated")
    rows = [_row("", "answers without ETag outnumber the 304: something between this computer and GitHub strips the header, so the cache saves nothing", "", None, "check the proxy or turn the cache off")] if broken else []
    return _signal("quota.etag", "now", "watch" if broken else "info", text, rows, transient=broken)
