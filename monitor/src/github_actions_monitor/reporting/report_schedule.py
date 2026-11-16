# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A cron expression of five fields (minute, hour, day of month, month, day of week) and the question the scheduler asks: was a run due since the last one? Numbers, `*`, lists (`1,15`), ranges (`1-5`) and steps (`*/15`, `10-50/10`); no names, no `@daily`. The time is the local time of this computer, as for any cron. Pure functions."""
import time

LIMITS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))      # day of week: 0 and 7 are Sunday
MAX_LOOKBACK_MINUTES = 8 * 24 * 60      # a schedule that fires every week or oftener looks back this far
MONTHLY_LOOKBACK_MINUTES = 32 * 24 * 60      # one that names a day of the month: a month, so a monthly report lost to a long stop is still owed
YEARLY_LOOKBACK_MINUTES = 367 * 24 * 60      # one that names a month


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


def lookback_minutes(parsed):
    """How far back a missed run is still owed: the period of the schedule, never less than eight days (a monthly report must survive a stop of ten days)."""
    fields = parsed["fields"]
    if len(fields[3]) < 12:
        return YEARLY_LOOKBACK_MINUTES
    if not parsed["dom_star"]:
        return MONTHLY_LOOKBACK_MINUTES
    return MAX_LOOKBACK_MINUTES


def last_due(parsed, now, since):
    """The latest minute in (since, now] that the expression names, as seconds since the epoch, or None. Looks back as far as the period of the schedule needs (eight days at least), so a monitor that was
    off for a long time produces ONE report and not a pile of them. A minute whose wall clock is not after the wall clock of `since` is the same minute seen again (the clock went back in autumn): it is not owed twice."""
    top = int(now // 60) * 60
    bottom = max(int(since // 60) * 60 + 60, top - lookback_minutes(parsed) * 60)
    seen = tuple(time.localtime(since)[:5])
    hours = parsed["fields"][1]
    stamp = top
    while stamp >= bottom:
        moment = time.localtime(stamp)
        if matches(parsed, moment) and tuple(moment[:5]) > seen:
            return stamp
        # jump over what cannot match: the rest of a day whose date does not fit, the rest of an hour that is not named
        if moment.tm_mon not in parsed["fields"][3] or not _day_fits(parsed, moment):
            stamp -= moment.tm_hour * 3600 + moment.tm_min * 60 + moment.tm_sec + 60
        elif moment.tm_hour not in hours:
            stamp -= moment.tm_min * 60 + moment.tm_sec + 60
        else:
            stamp -= 60
    return None


def _day_fits(parsed, moment):
    dom, dow = parsed["fields"][2], parsed["fields"][4]
    day_ok, week_ok = moment.tm_mday in dom, (moment.tm_wday + 1) % 7 in dow
    if parsed["dom_star"] or parsed["dow_star"]:
        return day_ok and week_ok
    return day_ok or week_ok


def due(expression, now, last_run):
    """True when a run is owed: the expression is valid and names a minute after `last_run` (None = never ran: the first run waits for the next named minute, it does not fire at once)."""
    parsed = parse(expression)
    if parsed is None:
        return False
    since = last_run if last_run is not None else now - 60
    return last_due(parsed, now, since) is not None
