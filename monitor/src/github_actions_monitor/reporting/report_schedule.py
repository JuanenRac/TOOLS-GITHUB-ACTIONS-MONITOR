# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A cron expression of five fields (minute, hour, day of month, month, day of week) and the question the scheduler asks: was a run due since the last one? Numbers, `*`, lists (`1,15`), ranges (`1-5`) and steps (`*/15`, `10-50/10`); no names, no `@daily`. The time is the local time of this computer, as for any cron. Pure functions."""
import time

LIMITS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))      # day of week: 0 and 7 are Sunday
MAX_LOOKBACK_MINUTES = 8 * 24 * 60


def _field(text, low, high):
    values = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, _, raw = part.partition("/")
            if not raw.isdigit() or int(raw) < 1:
                raise ValueError("step")
            step = int(raw)
        if part == "*":
            start, end = low, high
        elif "-" in part:
            a, _, b = part.partition("-")
            if not (a.isdigit() and b.isdigit()):
                raise ValueError("range")
            start, end = int(a), int(b)
        elif part.isdigit():
            start = int(part)
            end = high if step > 1 else start
        else:
            raise ValueError("value")
        if start < low or end > high or start > end:
            raise ValueError("out of range")
        values.update(range(start, end + 1, step))
    return values


def parse(expression):
    """The sets of the five fields, or None when the text is not a valid expression."""
    parts = str(expression or "").split()
    if len(parts) != 5:
        return None
    try:
        sets = [_field(text, low, high) for text, (low, high) in zip(parts, LIMITS)]
    except ValueError:
        return None
    sets[4] = {v % 7 for v in sets[4]}
    return {"fields": sets, "dom_star": parts[2] == "*", "dow_star": parts[4] == "*"}


def matches(parsed, moment):
    """Whether the struct_time `moment` (local time) is one of the minutes of the expression. As in cron, when both the day of the month and the day of the week are restricted either one is enough."""
    minute, hour, dom, month, dow = parsed["fields"]
    if moment.tm_min not in minute or moment.tm_hour not in hour or moment.tm_mon not in month:
        return False
    weekday = (moment.tm_wday + 1) % 7      # time.struct_time counts Monday as 0; cron counts Sunday as 0
    day_ok, week_ok = moment.tm_mday in dom, weekday in dow
    if parsed["dom_star"] or parsed["dow_star"]:
        return day_ok and week_ok
    return day_ok or week_ok


def last_due(parsed, now, since):
    """The latest minute in (since, now] that the expression names, as seconds since the epoch, or None. Looks back at most eight days, so a monitor that was off for a month produces ONE report and not a
    pile of them."""
    top = int(now // 60) * 60
    bottom = max(int(since // 60) * 60 + 60, top - MAX_LOOKBACK_MINUTES * 60)
    stamp = top
    while stamp >= bottom:
        if matches(parsed, time.localtime(stamp)):
            return stamp
        stamp -= 60
    return None


def due(expression, now, last_run):
    """True when a run is owed: the expression is valid and names a minute after `last_run` (None = never ran: the first run waits for the next named minute, it does not fire at once)."""
    parsed = parse(expression)
    if parsed is None:
        return False
    since = last_run if last_run is not None else now - 60
    return last_due(parsed, now, since) is not None
