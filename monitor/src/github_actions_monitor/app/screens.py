# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The wall screens: /screen/overview (the whole fleet in one view), /screen/now (what is happening this minute) and /screen/sentinels (one card per sentinel). They are pages for a monitor or a TV that
nobody touches, with no menu and no buttons that change anything. This module is the server side of them and holds no state:

  settings(config)            the block `screens` of the configuration, every value clamped to its range
  params(query, cfg)          what the address may change for one window (?monitor ?theme ?density ?refresh ?scale ?rotate ?blink ?sound): it can only make a window quieter or smaller than the settings
                              allow, never switch on what the settings keep off
  page_data(kind, ...)        what is embedded in the page (language, texts, settings, parameters)
  build(kind, ...)            the payload of /api/screens/data: a closed list of fields made only from what the monitor already holds (the last cycle, the sentinel snapshot, the alerts, the score).
                              Nothing here reads GitHub, runs a command, opens a link or returns a title, a commit message, a URL, a job name or a user name.

Names of repositories follow `screens.show_repo_names`: `all`, `public` (a private repository is called private-N) or `none` (every repository is repo-N). Standard library only."""
import re
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n
from github_actions_monitor.tool_version import TOOL_VERSION

SCHEMA = 1
KINDS = ("overview", "now", "sentinels")
PATH_RE = re.compile(r"^/screen/(overview|now|sentinels)/?\Z")
THEMES = ("dark", "light", "contrast")
DENSITIES = ("compact", "normal", "large")
NAMES = ("all", "public", "none")
DEFAULTS = {"enabled": True, "blink": True, "blink_calm_minutes": 30, "rotate_seconds": 0, "default_theme": "dark", "default_density": "normal", "refresh_seconds": 10, "burn_in_protection": True,
            "night_dim": False, "night_dim_from_hour": 22, "night_dim_to_hour": 7, "show_repo_names": "public", "sound": False}
SENTINEL_KEY = re.compile(r"^ui\.a(1[0-2]|[1-9])\Z")
SENTINELS = tuple("a%d" % n for n in range(1, 13))
LEVELS = ("ok", "warn", "bad", "info", "unknown")
RED_CONCLUSIONS = ("failure", "timed_out", "startup_failure")
HEAT_ROWS, HEAT_BUCKETS = 12, 24
TOP_RED, EVENTS, ACTIVE_ROWS, FAILURES, TIMELINE, MERGES = 8, 10, 12, 8, 24, 6


def _int(value, low, high, default):
    if isinstance(value, bool):
        return default
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _flag(value, default):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "on", "yes"):
        return True
    if text in ("0", "false", "off", "no"):
        return False
    return default


def _choice(value, allowed, default):
    text = str(value).strip().lower() if value is not None else ""
    return text if text in allowed else default


def settings(config):
    """The settings of the wall screens from the configuration, each one inside its range (a value that is not valid is the default)."""
    block = (config or {}).get("screens")
    block = block if isinstance(block, dict) else {}
    d = DEFAULTS
    return {"enabled": _flag(block.get("enabled"), d["enabled"]), "blink": _flag(block.get("blink"), d["blink"]), "blink_calm_minutes": _int(block.get("blink_calm_minutes"), 0, 1440, d["blink_calm_minutes"]),
            "rotate_seconds": _int(block.get("rotate_seconds"), 0, 3600, d["rotate_seconds"]), "default_theme": _choice(block.get("default_theme"), THEMES, d["default_theme"]),
            "default_density": _choice(block.get("default_density"), DENSITIES, d["default_density"]), "refresh_seconds": _int(block.get("refresh_seconds"), 5, 120, d["refresh_seconds"]),
            "burn_in_protection": _flag(block.get("burn_in_protection"), d["burn_in_protection"]), "night_dim": _flag(block.get("night_dim"), d["night_dim"]),
            "night_dim_from_hour": _int(block.get("night_dim_from_hour"), 0, 23, d["night_dim_from_hour"]), "night_dim_to_hour": _int(block.get("night_dim_to_hour"), 0, 23, d["night_dim_to_hour"]),
            "show_repo_names": _choice(block.get("show_repo_names"), NAMES, d["show_repo_names"]), "sound": _flag(block.get("sound"), d["sound"])}


def enabled(config):
    return settings(config)["enabled"]


def kind_of(path):
    """'overview', 'now' or 'sentinels' for the address of a screen, else None."""
    found = PATH_RE.match(path or "")
    return found.group(1) if found else None


def params(query, cfg):
    """What the address of one window asks for, checked. `query` is {name: first value}. A window may blink less, sound less and rotate on its own; it can never turn on blinking or sound that the
    settings turned off, and the refresh stays between 5 and 120 seconds."""
    monitor = _int(query.get("monitor"), 1, 9, 1)
    rotate = _int(query.get("rotate"), 0, 3600, cfg["rotate_seconds"])
    rotate = 0 if rotate < 5 else rotate      # a turn every second would be a strobe: below 5 seconds is no rotation
    scale = 1.0
    try:
        scale = max(0.5, min(3.0, float(str(query.get("scale", "1")).replace(",", "."))))
    except ValueError:
        pass
    return {"monitor": monitor, "theme": _choice(query.get("theme"), THEMES, cfg["default_theme"]), "density": _choice(query.get("density"), DENSITIES, cfg["default_density"]),
            "refresh": _int(query.get("refresh"), 5, 120, cfg["refresh_seconds"]), "scale": scale, "rotate": rotate,
            "blink": cfg["blink"] and _flag(query.get("blink"), True), "sound": cfg["sound"] and _flag(query.get("sound"), False)}


def page_keys():
    """The catalogue keys the page needs: the texts of the screens, the names of the sentinels and the words of the levels."""
    return sorted({k for k in i18n.catalogue_keys() if k.startswith(("ui.scr_", "ui.lv_")) or SENTINEL_KEY.match(k)})


def page_data(kind, cfg, prm, lang=None):
    """The object embedded in the page: language, texts of this language, the settings that matter to the page and the parameters of the window."""
    return {"screen": kind, "kinds": list(KINDS), "lang": lang or i18n.language(), "html_lang": i18n.HTML_LANG.get(lang or i18n.language(), "en"), "locale": i18n.BROWSER_LOCALE.get(lang or i18n.language(), "en-GB"),
            "texts": {k: i18n.t(k) for k in page_keys()}, "version": TOOL_VERSION,
            "settings": {k: cfg[k] for k in ("blink", "blink_calm_minutes", "burn_in_protection", "night_dim", "night_dim_from_hour", "night_dim_to_hour")}, "params": prm}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# names
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Names:
    """What a repository is called on a screen. `meta` is the repo_meta of the cycle ({repo: {"private": bool}})."""

    def __init__(self, repos, meta, mode):
        self.mode = mode if mode in NAMES else "public"
        self.meta = meta or {}
        order = sorted(set(repos or []) | set(self.meta))
        self.index = {repo: i + 1 for i, repo in enumerate(order)}

    def hidden(self, repo):
        if self.mode == "all":
            return False
        if self.mode == "none":
            return True
        return bool((self.meta.get(repo) or {}).get("private", True))      # unknown = treated as private

    def name(self, repo):
        if not self.hidden(repo):
            return repo
        return ("repo-%d" if self.mode == "none" else "private-%d") % self.index.get(repo, 0)


def _parse(stamp):
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _number(value, default=0):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _d(value):
    return value if isinstance(value, dict) else {}


def _l(value):
    return value if isinstance(value, list) else []


def _level(value):
    return value if value in LEVELS else "unknown"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# the common part
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _meta(state, now, refresh, edition):
    data = state or {}
    updated = _parse(data.get("updated"))
    rate = data.get("rate") if isinstance(data.get("rate"), dict) else {}
    reset = _parse(rate.get("reset"))
    remaining, limit = rate.get("remaining"), rate.get("limit")
    low = isinstance(remaining, (int, float)) and isinstance(limit, (int, float)) and limit > 0 and remaining / limit < 0.1
    return {"edition": edition, "have_data": bool(state), "age_seconds": None if updated is None else max(0, int(now - updated)), "refresh_seconds": _int(data.get("refresh_seconds"), 1, 3600, refresh),
            "loading": bool(data.get("loading")), "repos": len(data.get("repos") or []), "paused": bool(data.get("paused_quota")), "offline": bool((data.get("offline") or {}).get("offline")) if isinstance(data.get("offline"), dict) else False,
            "api": {"remaining": remaining if isinstance(remaining, (int, float)) else None, "limit": limit if isinstance(limit, (int, float)) else None,
                    "reset_seconds": None if reset is None else max(0, int(reset - now)), "low": bool(low)}}


def _default_branches(state):
    return {repo: (m or {}).get("branch") for repo, m in (state.get("repo_meta") or {}).items() if isinstance(m, dict)}


def _is_red(run):
    return run.get("status") == "completed" and run.get("conclusion") in RED_CONCLUSIONS


def _red_repos(state, snapshot):
    """Repository -> list of red workflow rows: the sentinel's red list when there is one, else the failures the cycle found."""
    rows = _d(_d(snapshot).get("a2")).get("red")
    if not isinstance(rows, list):
        rows = [{"repo": r.get("repo"), "workflow": r.get("name"), "since": r.get("started"), "streak": 1} for r in (state.get("failing") or []) if isinstance(r, dict)]
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get("repo"):
            out.setdefault(row["repo"], []).append(row)
    return out


def _stuck_repos(state, snapshot):
    found = {r.get("repo") for r in _l(_d(_d(snapshot).get("a1")).get("stuck")) if isinstance(r, dict)}
    found |= {r.get("repo") for r in (state.get("active") or []) if isinstance(r, dict) and r.get("stuck")}
    found.discard(None)
    return found


def _waiting_repos(state):
    found = {r.get("repo") for r in (state.get("active") or []) if isinstance(r, dict) and r.get("status") in ("queued", "waiting", "pending")}
    found |= {r.get("repo") for r in (state.get("runs") or []) if isinstance(r, dict) and r.get("conclusion") == "action_required"}
    found.discard(None)
    return found


def _progress(run):
    """0..1 from the steps of the jobs of a running run (a finished job counts as done); None when the jobs are not known."""
    jobs = [j for j in (run.get("jobs") or []) if isinstance(j, dict)]
    total = sum(_number(j.get("steps_total")) for j in jobs)
    if not jobs or total <= 0:
        return None
    done = sum(_number(j.get("steps_total")) if j.get("status") == "completed" else _number(j.get("steps_done")) for j in jobs)
    return round(max(0.0, min(1.0, done / total)), 3)


def _kind_of_run(run):
    if run.get("status") != "completed":
        return "run" if run.get("status") == "in_progress" else "wait"
    conclusion = run.get("conclusion")
    if conclusion in RED_CONCLUSIONS:
        return "bad"
    if conclusion == "success":
        return "ok"
    return "skip"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# overview
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _fleet(state, snapshot):
    repos = list(state.get("repos") or [])
    red, stuck, waiting = set(_red_repos(state, snapshot)), _stuck_repos(state, snapshot), _waiting_repos(state)
    seen = {r.get("repo") for r in (state.get("runs") or []) if isinstance(r, dict)}
    counts = {"total": len(repos), "red": 0, "stuck": 0, "waiting": 0, "green": 0, "idle": 0}
    for repo in repos:
        if repo in red:
            counts["red"] += 1
        elif repo in stuck:
            counts["stuck"] += 1
        elif repo in waiting:
            counts["waiting"] += 1
        elif repo in seen:
            counts["green"] += 1
        else:
            counts["idle"] += 1
    return counts


def _series(runs, now, buckets, width):
    """[{"ago": n, "ok": n, "bad": n}] oldest first: the completed runs of the last `buckets` periods of `width` seconds."""
    rows = [{"ago": buckets - 1 - i, "ok": 0, "bad": 0} for i in range(buckets)]
    for run in runs:
        when = _parse(run.get("started"))
        if when is None or run.get("status") != "completed":
            continue
        ago = int((now - when) // width)
        if 0 <= ago < buckets:
            row = rows[buckets - 1 - ago]
            if run.get("conclusion") == "success":
                row["ok"] += 1
            elif run.get("conclusion") in RED_CONCLUSIONS:
                row["bad"] += 1
    return rows


def _heat(runs, now, names, red_repos):
    """The map of heat: a row for each of the busiest repositories (the red ones first), a cell for each hour of the last day: 0 nothing, 1 green, 2 mixed, 3 red."""
    cells = {}
    for run in runs:
        when = _parse(run.get("started"))
        if when is None or run.get("status") != "completed":
            continue
        ago = int((now - when) // 3600)
        if not 0 <= ago < HEAT_BUCKETS:
            continue
        row = cells.setdefault(run.get("repo"), [[0, 0] for _ in range(HEAT_BUCKETS)])[HEAT_BUCKETS - 1 - ago]
        if run.get("conclusion") == "success":
            row[0] += 1
        elif run.get("conclusion") in RED_CONCLUSIONS:
            row[1] += 1
    ranked = sorted(cells, key=lambda r: (r not in red_repos, -sum(a + b for a, b in cells[r]), str(r)))[:HEAT_ROWS]
    out = []
    for repo in ranked:
        out.append({"repo": names.name(repo), "red": repo in red_repos, "cells": [0 if not (a or b) else (3 if b and not a else 2 if b else 1) for a, b in cells[repo]]})
    return out


def _top_red(state, snapshot, names, now):
    rows = []
    for repo, found in _red_repos(state, snapshot).items():
        for row in found:
            since = _parse(row.get("since"))
            rows.append({"repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(row.get("workflow") or "")[:60], "seconds": None if since is None else max(0, int(now - since)),
                         "streak": _int(row.get("streak"), 0, 9999, 1)})
    rows.sort(key=lambda r: (-(r["seconds"] if r["seconds"] is not None else -1), r["repo"]))
    return rows[:TOP_RED]


def _events(state, names, now, limit=EVENTS):
    runs = [r for r in (state.get("runs") or []) if isinstance(r, dict) and _parse(r.get("started")) is not None]
    runs.sort(key=lambda r: _parse(r["started"]), reverse=True)
    out = []
    for run in runs[:limit]:
        repo = run.get("repo")
        out.append({"ago": max(0, int(now - _parse(run["started"]))), "kind": _kind_of_run(run), "repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(run.get("name") or "")[:60],
                    "seconds": _int(run.get("seconds"), 0, 10 ** 7, 0)})
    return out


def _queue(state, snapshot):
    active = [r for r in (state.get("active") or []) if isinstance(r, dict)]
    minutes = sum(_number(r.get("min24")) for r in _l(_d(_d(snapshot).get("a7")).get("rows")) if isinstance(r, dict))
    minutes7 = sum(_number(r.get("min7d")) for r in _l(_d(_d(snapshot).get("a7")).get("rows")) if isinstance(r, dict))
    approval = sum(1 for r in (state.get("runs") or []) if isinstance(r, dict) and r.get("conclusion") == "action_required")
    return {"running": sum(1 for r in active if r.get("status") == "in_progress"), "queued": sum(1 for r in active if r.get("status") in ("queued", "waiting", "pending")), "approval": approval,
            "minutes24": round(minutes), "minutes7d": round(minutes7)}


def _score(score):
    if not isinstance(score, dict) or not score.get("enabled", True):
        return {"state": "off", "value": None, "letter": None, "trend": None}
    value = score.get("score")
    return {"state": str(score.get("state") or "calibrating")[:20], "value": value if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
            "letter": score.get("letter") if isinstance(score.get("letter"), str) else None, "trend": score.get("trend") if isinstance(score.get("trend"), (int, float)) and not isinstance(score.get("trend"), bool) else None}


def _alert_summary(alerts):
    summary = (alerts or {}).get("summary") if isinstance(alerts, dict) else None
    summary = summary if isinstance(summary, dict) else {}
    by_level = summary.get("by_level") if isinstance(summary.get("by_level"), dict) else {}
    return {"total": _int(summary.get("total"), 0, 10 ** 6, 0), "by_level": {k: _int(by_level.get(k), 0, 10 ** 6, 0) for k in ("critical", "error", "warning", "info")}}


def build_overview(state, snapshot, alerts, score, names, now):
    runs = [r for r in (state.get("runs") or []) if isinstance(r, dict)]
    red = _red_repos(state, snapshot)
    return {"score": _score(score), "fleet": _fleet(state, snapshot), "trend24": _series(runs, now, 24, 3600), "trend7d": _series(runs, now, 7, 86400), "heat": _heat(runs, now, names, set(red)),
            "top_red": _top_red(state, snapshot, names, now), "queue": _queue(state, snapshot), "events": _events(state, names, now), "alerts": _alert_summary(alerts)}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# now
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def build_now(state, snapshot, alerts, score, names, now):
    active = [r for r in (state.get("active") or []) if isinstance(r, dict)]
    runs = [r for r in (state.get("runs") or []) if isinstance(r, dict)]
    branches = _default_branches(state)

    def row(run):
        repo = run.get("repo")
        started = _parse(run.get("started"))
        return {"repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(run.get("name") or "")[:60], "event": str(run.get("event") or "")[:20],
                "state": "queued" if run.get("status") in ("queued", "waiting", "pending") else "running", "seconds": _int(run.get("seconds"), 0, 10 ** 7, 0) if started is None else max(0, int(now - started)),
                "progress": _progress(run), "stuck": bool(run.get("stuck")), "jobs": len(run.get("jobs") or [])}
    running = sorted((row(r) for r in active if r.get("status") == "in_progress"), key=lambda r: (not r["stuck"], -r["seconds"]))[:ACTIVE_ROWS]
    queued = sorted((row(r) for r in active if r.get("status") in ("queued", "waiting", "pending")), key=lambda r: -r["seconds"])[:ACTIVE_ROWS]
    approval = []
    for run in runs:
        if run.get("conclusion") == "action_required":
            started = _parse(run.get("started"))
            approval.append({"repo": names.name(run.get("repo")), "ago": None if started is None else max(0, int(now - started))})
    recent_bad = []
    for run in sorted(runs, key=lambda r: _parse(r.get("started")) or 0, reverse=True):
        started = _parse(run.get("started"))
        if _is_red(run) and started is not None and now - started < 6 * 3600:
            repo = run.get("repo")
            recent_bad.append({"repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(run.get("name") or "")[:60], "ago": max(0, int(now - started)), "attempt": _int(run.get("attempt"), 1, 99, 1)})
    merges = []
    for run in sorted(runs, key=lambda r: _parse(r.get("started")) or 0, reverse=True):
        repo = run.get("repo")
        if run.get("status") == "completed" and run.get("conclusion") == "success" and run.get("event") in ("push", "merge_group") and branches.get(repo) and run.get("branch") == branches.get(repo):
            started = _parse(run.get("started"))
            merges.append({"repo": names.name(repo), "release": bool(re.search(r"release", str(run.get("name") or ""), re.I)), "ago": None if started is None else max(0, int(now - started))})
        if len(merges) >= MERGES:
            break
    candidates = [{"repo": names.name(c.get("repo")), "entries": _int(c.get("entries"), 0, 9999, 0), "age_days": round(_number(c.get("age_days")), 1)}
                  for c in _l(_d(_d(snapshot).get("a5")).get("candidates")) if isinstance(c, dict)][:MERGES]
    pending = [{"repo": names.name(c.get("repo")), "hours": round(_number(c.get("hours")), 1)} for c in _l(_d(_d(snapshot).get("a5")).get("pending_sign")) if isinstance(c, dict)][:MERGES]
    timeline = _events(state, names, now, TIMELINE)
    return {"running": running, "queued": queued, "approval": approval[:ACTIVE_ROWS], "failures": recent_bad[:FAILURES], "merges": merges, "next_releases": candidates, "pending_sign": pending,
            "timeline": timeline, "totals": {"running": len([r for r in active if r.get("status") == "in_progress"]), "queued": len([r for r in active if r.get("status") in ("queued", "waiting", "pending")]),
                                              "approval": len(approval), "failures": len(recent_bad)}}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# sentinels
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _count(snapshot, key):
    """How many open findings a sentinel panel holds, from the lists the snapshot already carries."""
    panel = (snapshot or {}).get(key)
    if not isinstance(panel, dict):
        return None
    def size(name):
        value = panel.get(name)
        return len(value) if isinstance(value, list) else 0
    if key == "a1":
        return size("stuck") + size("issues")
    if key == "a2":
        return size("red")
    if key == "a3":
        return _int(panel.get("codeql_total"), 0, 10 ** 6, 0) + _int(panel.get("dependabot_total"), 0, 10 ** 6, 0) + _int(panel.get("secret_total"), 0, 10 ** 6, 0)
    if key == "a4":
        return size("dependabot")
    if key == "a5":
        return size("candidates") + size("pending_sign")
    if key == "a6":
        return sum(len(r.get("problems") or []) for r in (panel.get("rows") or []) if isinstance(r, dict))
    if key == "a8":
        return size("files")
    if key == "a9":
        return size("boards")
    if key in ("a10", "a11"):
        return sum(_int(s.get("count"), 0, 10 ** 6, 0) for s in (panel.get("sections") or []) if isinstance(s, dict))
    return 0


def build_sentinels(state, snapshot, alerts, score, names, now, refresh):
    snap = snapshot if isinstance(snapshot, dict) else None
    broken = {str(e.get("section")) for e in ((snap or {}).get("errors") or []) if isinstance(e, dict)}
    generated = _parse((snap or {}).get("generated"))
    age = None if generated is None else max(0, int(now - generated))
    cache = (snap or {}).get("cache_age_seconds")
    age = age if cache is None else max(age or 0, int(_number(cache)))
    cycle = max(5, _int((state or {}).get("refresh_seconds"), 1, 3600, refresh))
    cards = []
    for key in SENTINELS:
        panel = (snap or {}).get(key) if snap else None
        level = _level((panel or {}).get("level")) if isinstance(panel, dict) else "unknown"
        cards.append({"id": key, "level": level, "open": _count(snap, key), "readable": bool(isinstance(panel, dict) and key not in broken and level != "unknown")})
    totals = (snap or {}).get("totals") if snap else None
    totals = totals if isinstance(totals, dict) else {}
    by_sentinel = _d(_d(alerts).get("summary")).get("by_sentinel")
    return {"enabled": bool(snap and snap.get("enabled", True)), "level": _level((snap or {}).get("level")), "loading": bool(snap and snap.get("loading")), "sweep": {"age_seconds": age, "cycle_seconds": cycle,
            "progress": None if age is None else round(max(0.0, min(1.0, age / cycle)), 3)}, "cards": cards,
            "totals": {k: _int(totals.get(k), 0, 10 ** 6, 0) for k in ("red", "stuck", "new_alerts", "candidates", "prs", "codeql", "dependabot", "secret")},
            "alerts": {**_alert_summary(alerts), "by_sentinel": {str(k)[:20]: _int(v, 0, 10 ** 6, 0) for k, v in (by_sentinel or {}).items()} if isinstance(by_sentinel, dict) else {}}}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# the payload
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def build(kind, state, snapshot, alerts, score, cfg, edition="complete", now=None):
    """The answer of /api/screens/data for one screen, from what the monitor holds. `state` is the last cycle (STATE["data"], or None before the first), `snapshot` the sentinel snapshot (or None),
    `alerts` the alerts payload, `score` the latest score. Never raises for missing parts: a part that is not there is empty and `meta.have_data` says so."""
    if kind not in KINDS:
        raise ValueError("unknown screen")
    now = time.time() if now is None else now
    data = state if isinstance(state, dict) else {}
    names = Names(data.get("repos"), data.get("repo_meta"), cfg["show_repo_names"])
    out = {"schema": SCHEMA, "screen": kind, "version": TOOL_VERSION, "epoch": int(now), "names": cfg["show_repo_names"], "meta": _meta(state, now, cfg["refresh_seconds"], edition)}
    if kind == "overview":
        out.update(build_overview(data, snapshot, alerts, score, names, now))
    elif kind == "now":
        out.update(build_now(data, snapshot, alerts, score, names, now))
    else:
        out.update(build_sentinels(data, snapshot, alerts, score, names, now, cfg["refresh_seconds"]))
    return out
