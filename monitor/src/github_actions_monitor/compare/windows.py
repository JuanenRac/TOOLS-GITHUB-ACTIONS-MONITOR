# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two windows of a comparison and the calendar filter. Pure functions: the clock and the time zone are given.

  window      the last N days (7 or 30 by default) ending now, or any `from` / `to` (at most 90 days long)
  baseline    `previous` (the window of the same length right before), `year_ago` (the same dates one year earlier) or `custom` (`base_from` / `base_to`)
  days        `all`, `workdays` (the days of `compare.workdays`, Monday = 1) or `weekend` (the others); the day of a moment is the day in the zone of display.timezone

Bank holidays are NOT known: a holiday counts as the weekday it falls on."""
from github_actions_monitor.scoring.collector import DAY, to_ts
from github_actions_monitor.util import tzdisplay

MAX_DAYS = 90
FUTURE_MARGIN = 300.0


class WindowError(ValueError):
    """A request that cannot be answered; `code` is stable (bad_range, bad_baseline, bad_days, bad_window)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _moment(value):
    if value in (None, ""):
        return None
    if isinstance(value, str) and value.strip().isdigit():
        return float(value)
    return to_ts(value)


def _span_ok(start, end):
    return start is not None and end is not None and 0 < end - start <= MAX_DAYS * DAY


def resolve(ask, cfg, now):
    """{"now": (start, end), "base": (start, end), "baseline": kind, "days": filter, "window_days": n}; raises WindowError."""
    ask = ask or {}
    days = str(ask.get("days") or cfg["default_days_filter"])
    if days not in ("all", "workdays", "weekend"):
        raise WindowError("bad_days")
    baseline = str(ask.get("baseline") or "previous")
    if baseline not in ("previous", "year_ago", "custom"):
        raise WindowError("bad_baseline")
    if ask.get("from") or ask.get("to"):
        start, end = _moment(ask.get("from")), (_moment(ask.get("to")) if ask.get("to") else now)
        if start is None or end is None or not _span_ok(start, end) or end > now + FUTURE_MARGIN:
            raise WindowError("bad_range")
    else:
        text = str(ask.get("window") or "").strip().lower().rstrip("d")
        if text:
            if not text.isdigit() or not 1 <= int(text) <= MAX_DAYS:
                raise WindowError("bad_window")
            length = int(text)
        else:
            length = cfg["default_window_days"]
        start, end = now - length * DAY, now
    span = end - start
    if baseline == "previous":
        base = (start - span, start)
    elif baseline == "year_ago":
        base = (start - 365 * DAY, end - 365 * DAY)
    else:
        base = (_moment(ask.get("base_from")), _moment(ask.get("base_to")))
        if not _span_ok(*base):
            raise WindowError("bad_baseline")
    return {"now": (start, end), "base": base, "baseline": baseline, "days": days, "window_days": round(span / DAY, 2)}


def day_matches(moment, days, workdays, zone=None):
    """True when the moment falls on a day the filter keeps."""
    if days == "all":
        return True
    try:
        weekday = tzdisplay.at(moment, zone).isoweekday()
    except (ValueError, TypeError, OverflowError, OSError):
        return False
    inside = weekday in workdays
    return inside if days == "workdays" else not inside
