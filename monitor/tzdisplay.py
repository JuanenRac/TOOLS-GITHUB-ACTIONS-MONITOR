# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The time zone of every text meant for people (command line, log, reports, notifications, brief). Standard library only.

  display.timezone in actions_monitor.json:  "local" (default) = the zone of this computer | "utc" | an IANA name such as "Europe/Madrid"
                                             (the environment variable MONITOR_TIMEZONE, when set, wins over the file)

  stamp(value)       "2026-03-29 11:43:07 CEST (09:43:07 UTC)"   date + time in the chosen zone, with the zone name and the UTC time next to it
  clock(value)       "11:43 CEST"                                 just the time, with the zone
  iso_local(value)   "2026-03-29T11:43:07+02:00"                  ISO 8601 with the offset (for fields that sit next to a UTC one)
  localize(text)     the same text with every "YYYY-MM-DDTHH:MM:SSZ" inside it replaced by stamp()

`value` is an ISO "...Z" text, a Unix time (int/float) or a datetime. Machine fields (the JSON of the API, `generated` in ci_red.json) stay in UTC; they get a
sibling field `*_local` made with stamp(). A value that cannot be read is returned unchanged, so this can never break a caller.

IANA names use the zoneinfo database of the system when it has one; without it (a Windows install without the tzdata package) a small built-in table of the
usual zones (European and North American rules, Japan, China, India, Australia...) is used, so the result does not depend on what is installed.
"""
import os
import re
import time
from datetime import datetime, timedelta, timezone

ISO_Z = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_UTC = timezone.utc

# name -> (standard offset in minutes, standard abbreviation, daylight abbreviation, rule)   rule: "eu" | "us" | "" (no daylight saving time)
_TABLE = {
    "Europe/Madrid": (60, "CET", "CEST", "eu"), "Europe/Paris": (60, "CET", "CEST", "eu"), "Europe/Berlin": (60, "CET", "CEST", "eu"),
    "Europe/Rome": (60, "CET", "CEST", "eu"), "Europe/Amsterdam": (60, "CET", "CEST", "eu"), "Europe/Brussels": (60, "CET", "CEST", "eu"),
    "Europe/Vienna": (60, "CET", "CEST", "eu"), "Europe/Zurich": (60, "CET", "CEST", "eu"), "Europe/Stockholm": (60, "CET", "CEST", "eu"),
    "Europe/Oslo": (60, "CET", "CEST", "eu"), "Europe/Copenhagen": (60, "CET", "CEST", "eu"), "Europe/Prague": (60, "CET", "CEST", "eu"),
    "Europe/Warsaw": (60, "CET", "CEST", "eu"), "Europe/Lisbon": (0, "WET", "WEST", "eu"), "Europe/London": (0, "GMT", "BST", "eu"),
    "Europe/Dublin": (0, "GMT", "IST", "eu"), "Europe/Athens": (120, "EET", "EEST", "eu"), "Europe/Helsinki": (120, "EET", "EEST", "eu"),
    "Atlantic/Canary": (0, "WET", "WEST", "eu"), "Europe/Istanbul": (180, "+03", "+03", ""), "Europe/Moscow": (180, "MSK", "MSK", ""),
    "America/New_York": (-300, "EST", "EDT", "us"), "America/Chicago": (-360, "CST", "CDT", "us"), "America/Denver": (-420, "MST", "MDT", "us"),
    "America/Los_Angeles": (-480, "PST", "PDT", "us"), "America/Phoenix": (-420, "MST", "MST", ""), "America/Sao_Paulo": (-180, "-03", "-03", ""),
    "America/Mexico_City": (-360, "CST", "CST", ""), "America/Argentina/Buenos_Aires": (-180, "-03", "-03", ""),
    "Asia/Tokyo": (540, "JST", "JST", ""), "Asia/Seoul": (540, "KST", "KST", ""), "Asia/Shanghai": (480, "CST", "CST", ""),
    "Asia/Hong_Kong": (480, "HKT", "HKT", ""), "Asia/Singapore": (480, "+08", "+08", ""), "Asia/Kolkata": (330, "IST", "IST", ""),
    "Asia/Dubai": (240, "+04", "+04", ""), "Australia/Sydney": (600, "AEST", "AEDT", "au"), "Pacific/Auckland": (720, "NZST", "NZDT", "nz"),
    "Africa/Johannesburg": (120, "SAST", "SAST", ""), "Africa/Cairo": (120, "EET", "EET", ""), "UTC": (0, "UTC", "UTC", ""), "Etc/UTC": (0, "UTC", "UTC", ""),
    "GMT": (0, "GMT", "GMT", ""),
}
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_+./-]{0,63}$")


def _nth_weekday(year, month, weekday, n):
    """Day of the month of the n-th (1-based; -1 = last) `weekday` (Monday = 0)."""
    if n > 0:
        first = datetime(year, month, 1).weekday()
        return 1 + (weekday - first) % 7 + 7 * (n - 1)
    nxt = datetime(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return nxt.day - (nxt.weekday() - weekday) % 7


def _in_dst(utc_dt, std_minutes, rule):
    """Is daylight saving time in force at this UTC moment? (naive UTC datetime)"""
    y = utc_dt.year
    if rule == "eu":      # last Sunday of March -> last Sunday of October, both at 01:00 UTC
        start = datetime(y, 3, _nth_weekday(y, 3, 6, -1), 1)
        end = datetime(y, 10, _nth_weekday(y, 10, 6, -1), 1)
        return start <= utc_dt < end
    if rule == "us":      # second Sunday of March 02:00 local standard -> first Sunday of November 02:00 local daylight
        start = datetime(y, 3, _nth_weekday(y, 3, 6, 2), 2) - timedelta(minutes=std_minutes)
        end = datetime(y, 11, _nth_weekday(y, 11, 6, 1), 2) - timedelta(minutes=std_minutes + 60)
        return start <= utc_dt < end
    if rule == "au":      # first Sunday of October -> first Sunday of April, 02:00 local standard
        start = datetime(y, 10, _nth_weekday(y, 10, 6, 1), 2) - timedelta(minutes=std_minutes)
        end = datetime(y, 4, _nth_weekday(y, 4, 6, 1), 3) - timedelta(minutes=std_minutes + 60)
        return utc_dt >= start or utc_dt < end
    if rule == "nz":      # last Sunday of September -> first Sunday of April
        start = datetime(y, 9, _nth_weekday(y, 9, 6, -1), 2) - timedelta(minutes=std_minutes)
        end = datetime(y, 4, _nth_weekday(y, 4, 6, 1), 3) - timedelta(minutes=std_minutes + 60)
        return utc_dt >= start or utc_dt < end
    return False


def _short_name(name, offset):
    """Zone names from the operating system can be long words ("Hora estándar romance"): then the offset is shown instead."""
    if name and len(name) <= 5 and name.isascii() and " " not in name:
        return name
    total = int(offset.total_seconds() // 60)
    sign = "+" if total >= 0 else "-"
    hours, minutes = divmod(abs(total), 60)
    return f"UTC{sign}{hours:02d}" + (f":{minutes:02d}" if minutes else "")


def _setting(value=None):
    if value is not None:
        return str(value).strip() or "local"
    forced = os.environ.get("MONITOR_TIMEZONE", "").strip()      # the environment wins (scripts, tests)
    if forced:
        return forced
    try:
        import toolconfig
        display = toolconfig.raw_config().get("display")
        text = display.get("timezone") if isinstance(display, dict) else None
    except Exception:
        text = None
    return str(text).strip() if isinstance(text, str) and text.strip() else "local"


def valid_setting(value):
    """True for "local", "utc" or a name the system or the built-in table knows (settings page)."""
    text = str(value or "").strip()
    if text.lower() in ("", "local", "utc"):
        return True
    return bool(_NAME_RE.match(text)) and (text in _TABLE or _zoneinfo(text) is not None)


def _zoneinfo(name):
    try:
        import zoneinfo
        return zoneinfo.ZoneInfo(name)
    except Exception:
        return None


def _to_timestamp(value):
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=_UTC)).timestamp()
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=_UTC)).timestamp()


def at(value, zone=None):
    """The moment `value` as an aware datetime in the zone of display.timezone (or in `zone`: "local" | "utc" | IANA). Raises ValueError when it cannot be read."""
    ts = _to_timestamp(value)
    utc_dt = datetime.fromtimestamp(ts, _UTC)
    mode = _setting(zone)
    low = mode.lower()
    if low == "utc":
        return utc_dt
    if low != "local":
        entry = _TABLE.get(mode)
        info = _zoneinfo(mode) if _NAME_RE.match(mode) else None
        if info is not None:
            local = utc_dt.astimezone(info)
            return local.replace(tzinfo=timezone(local.utcoffset(), _short_name(local.tzname(), local.utcoffset())))
        if entry:
            std, std_name, dst_name, rule = entry
            naive = utc_dt.replace(tzinfo=None)
            dst = _in_dst(naive, std, rule)
            offset = timedelta(minutes=std + (60 if dst else 0))
            return utc_dt.astimezone(timezone(offset, dst_name if dst else std_name))
    local = _local(ts)
    return local.replace(tzinfo=timezone(local.utcoffset(), _short_name(local.tzname(), local.utcoffset())))


def _local(ts):
    """The zone of this computer (a seam for the tests)."""
    return datetime.fromtimestamp(ts).astimezone()


def stamp(value, zone=None, seconds=True):
    """"2026-03-29 11:43:07 CEST (09:43:07 UTC)"; in UTC just "2026-03-29 09:43:07 UTC". The input comes back unchanged when it cannot be read."""
    try:
        local = at(value, zone)
    except (ValueError, TypeError, OverflowError, OSError):
        return value
    fmt = "%H:%M:%S" if seconds else "%H:%M"
    utc_dt = local.astimezone(_UTC)
    name = local.tzname()
    if name == "UTC":
        return f"{local:%Y-%m-%d} {local.strftime(fmt)} UTC"
    other = utc_dt.strftime(fmt) if utc_dt.date() == local.date() else utc_dt.strftime("%Y-%m-%d " + fmt)
    return f"{local:%Y-%m-%d} {local.strftime(fmt)} {name} ({other} UTC)"


def clock(value, zone=None, seconds=False):
    """"11:43 CEST" (the time of day in the zone of display)."""
    try:
        local = at(value, zone)
    except (ValueError, TypeError, OverflowError, OSError):
        return value
    return f"{local.strftime('%H:%M:%S' if seconds else '%H:%M')} {local.tzname()}"


def iso_local(value, zone=None):
    """"2026-03-29T11:43:07+02:00" (ISO 8601 with the offset of the zone of display)."""
    try:
        return at(value, zone).isoformat(timespec="seconds")
    except (ValueError, TypeError, OverflowError, OSError):
        return value


def localize(text, zone=None):
    """Replaces every ISO UTC time ("...Z") inside `text` by stamp(); everything else is left as it is."""
    if not isinstance(text, str) or "Z" not in text:
        return text
    mode = _setting(zone)
    return ISO_Z.sub(lambda m: str(stamp(m.group(0), mode)), text)


def now_stamp(zone=None):
    return stamp(time.time(), zone)


def zone_name(zone=None, when=None):
    """The abbreviation or offset of the zone of display right now ("CET"), for the clocks."""
    try:
        return at(time.time() if when is None else when, zone).tzname()
    except (ValueError, TypeError, OverflowError, OSError):
        return "UTC"


def setting():
    """The configured value of display.timezone as the page needs it ("local", "utc" or an IANA name)."""
    return _setting()
