# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""History of the daily Centinela report: text/Markdown formats, one saved report per day with retention,
and the "yesterday vs today" comparison (reds, pending-signature repositories, budget warnings and report lines that appear or disappear).

Pure functions on a Centinela snapshot (no network). Files in the audit folder:
  SENTINEL_REPORT_DAY_YYYY-MM-DD.txt   the report of that day (the last one saved that day)
  SENTINEL_REPORT_DAY_YYYY-MM-DD.json  the small state used for the comparison
A missing or unwritable folder is never an error: nothing is saved.
"""
import json
import re
import time
from datetime import datetime, timedelta, timezone

from github_actions_monitor import i18n
from github_actions_monitor.util import tzdisplay
from github_actions_monitor.security import private_io

PREFIX = "SENTINEL_REPORT_DAY_"
LEGACY_PREFIX = "PARTE_CENTINELA_DIA_"   # the name used by versions before 1.5.0: still read (and kept in the retention), never written
DAY_RE = re.compile(r"^(?:" + re.escape(PREFIX) + "|" + re.escape(LEGACY_PREFIX) + r")(\d{4}-\d{2}-\d{2})\.(txt|json)\Z")
DEFAULT_DAYS = 30
NEWER_KINDS = ("budget", "parte")


def parte_lines(snap):
    return [(l.get("level"), l.get("text")) for l in (snap or {}).get("parte") or []]


def _when(snap):
    generated = (snap or {}).get("generated")
    return tzdisplay.stamp(generated) if generated else generated


def parte_text(snap):
    lines = [f"{i18n.t('ph.title_text')} - {_when(snap)}"] + [f"[{lv}] {tx}" for lv, tx in parte_lines(snap)]
    return "\n".join(lines) + "\n"


def parte_markdown(snap):
    """The report as Markdown, ready to paste into an issue."""
    out = [f"## {i18n.t('ph.title_md')} - {_when(snap)}", ""]
    for lv, tx in parte_lines(snap):
        out.append(f"- **{lv}**: {tx}")
    totals = (snap or {}).get("totals") or {}
    if totals:
        out += ["", "| " + " | ".join(i18n.t("ph.col_" + c) for c in ("red", "stuck", "new", "candidates", "prs")) + " |", "|---|---|---|---|---|",
                f"| {totals.get('red', 0)} | {totals.get('stuck', 0)} | {totals.get('new_alerts', 0)} | {totals.get('candidates', 0)} | {totals.get('prs', 0)} |"]
    return "\n".join(out) + "\n"


def day_state(snap):
    """What the comparison needs from a snapshot: the red workflows and the repositories waiting for a signature."""
    snap = snap or {}
    red = sorted({f"{r.get('repo')} ({r.get('workflow')})" for r in (snap.get("a2") or {}).get("red") or []})
    pend = sorted({g.get("repo") for g in (snap.get("a5") or {}).get("pending_sign") or [] if g.get("repo")})
    budget = sorted(f"{b.get('ecosystem')} {b.get('level')}" for b in ((snap.get("a7") or {}).get("budget") or []) if b.get("level") != "ok")
    # the lines of the report with the numbers blanked out (hours and counts change all day; the sentence is what appears or disappears)
    lines = sorted({re.sub(r"\d+(?:[.,]\d+)?", "#", str(tx))[:160] for _, tx in parte_lines(snap) if tx})
    return {"red": red, "pending_sign": pend, "budget": budget, "parte": lines}


def compare(before, after):
    """Appeared (in `after` only) and disappeared (in `before` only), per kind."""
    out = {}
    for kind in ("red", "pending_sign", "budget", "parte"):
        b, a = set((before or {}).get(kind) or []), set((after or {}).get(kind) or [])
        if kind in NEWER_KINDS and kind not in (before or {}):   # a day saved by an older version has no such list: nothing to compare against
            out[kind] = {"appeared": [], "disappeared": [], "now": sorted(a), "no_base": True}
            continue
        out[kind] = {"appeared": sorted(a - b), "disappeared": sorted(b - a), "now": sorted(a)}
    return out


def _path(folder, day, ext):
    path = folder / f"{PREFIX}{day}.{ext}"
    legacy = folder / f"{LEGACY_PREFIX}{day}.{ext}"
    return legacy if (not path.exists() and legacy.exists()) else path


def save_day(folder, snap, keep_days=DEFAULT_DAYS, today=None):
    """Saves (overwrites) today's report and removes the days older than `keep_days`. Returns the day saved, or None."""
    if folder is None or not snap or snap.get("enabled") is False or snap.get("loading"):
        return None   # an incomplete picture must not become the report of the day
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        if not folder.is_dir():
            return None
        private_io.write_private(_path(folder, today, "txt"), parte_text(snap))
        private_io.write_private(_path(folder, today, "json"), json.dumps({"day": today, "generated": snap.get("generated"), **day_state(snap)}))
        prune(folder, keep_days, today)
    except OSError:
        return None
    return today


def prune(folder, keep_days, today):
    """Deletes the report files older than `keep_days` days (only files with our own name pattern)."""
    try:
        keep = max(1, int(keep_days))
    except (TypeError, ValueError):
        keep = DEFAULT_DAYS
    limit = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=keep - 1)).strftime("%Y-%m-%d")
    removed = 0
    try:
        for item in folder.iterdir():
            m = DAY_RE.match(item.name)
            if m and m.group(1) < limit:
                try:
                    item.unlink()
                    removed += 1
                except OSError:
                    pass
    except OSError:
        pass
    return removed


def saved_days(folder):
    try:
        return sorted({m.group(1) for item in folder.iterdir() for m in [DAY_RE.match(item.name)] if m and m.group(2) == "json"})
    except OSError:
        return []


def load_day(folder, day):
    try:
        return json.loads(_path(folder, day, "json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def yesterday_vs_today(folder, snap, today=None):
    """The view for the page: today's state is the live snapshot; the base is the most recent saved day before today (normally yesterday)."""
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    days = [d for d in saved_days(folder) if d < today] if folder is not None else []
    if not days:
        return {"available": False, "today": today, "message": i18n.t("ph.no_previous")}
    base_day = days[-1]
    base = load_day(folder, base_day) or {}
    return {"available": True, "today": today, "base_day": base_day, "is_yesterday": base_day == (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_saved": len(saved_days(folder)), **compare(base, day_state(snap))}


class AutoSaver:
    """Saves the report of the day at most every `every` seconds (called from the monitor loop)."""
    def __init__(self, every=900):
        self.every, self.last = every, 0.0

    def maybe(self, folder, snap, keep_days):
        if time.time() - self.last < self.every:
            return None
        day = save_day(folder, snap, keep_days)
        if day:
            self.last = time.time()
        return day
