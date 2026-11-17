# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The closed list of commands of the chat and what each one answers. Every command only READS what the monitor already holds (the snapshot it is given): none writes on GitHub, runs an action, changes a
setting or reads a secret, and there is no way to add one from the chat. The texts are the catalogue's; every dynamic text goes through `esc` (render.py) before it is part of a line."""
from github_actions_monitor import i18n
from github_actions_monitor.chatops import render

COMMANDS = ("help", "status", "alerts", "red", "queue", "score")      # the whole list; `chatops.commands` can only narrow it


def number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def age(seconds):
    """A short age: minutes, hours or days; '?' when unknown."""
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0:
        return i18n.t("chatops.age_unknown")
    if seconds < 3600:
        return i18n.t("chatops.age_min", n=int(seconds // 60))
    if seconds < 86400:
        return i18n.t("chatops.age_hours", n=int(seconds // 3600))
    return i18n.t("chatops.age_days", n=int(seconds // 86400))


def tail(row):
    """A space and the link of the repository of the row, or '' (the adapter only gives one when the name is visible and `chatops.links` is on; render.link accepts nothing else than a repository address)."""
    found = render.link(row.get("link"))
    return " " + found if found else ""


def parse(text, allowed):
    """The command named by the first word of the text of the chat, or None when it is not in the list. Whatever follows the first word is ignored (no command takes an argument)."""
    words = str(text or "").split()
    word = words[0].lower().lstrip("/") if words else "help"
    return word if word in COMMANDS and word in allowed else None


def run(name, snap, max_rows, esc, allowed=COMMANDS):
    """The lines of the answer to `name`. `snap` is the snapshot built by the monitor (counts and already anonymised names); never raises for a missing part."""
    snap = snap if isinstance(snap, dict) else {}
    if name == "help":
        return [i18n.t("chatops.help", commands=", ".join(c for c in COMMANDS if c in allowed))]
    if not snap.get("loaded"):
        return [i18n.t("chatops.nodata")]
    fleet = snap.get("fleet") if isinstance(snap.get("fleet"), dict) else {}
    if name == "status":
        alerts = snap.get("alerts") if isinstance(snap.get("alerts"), dict) else {}
        return [i18n.t("chatops.status", version=esc(snap.get("version"), 20), red=number(fleet.get("red")), stuck=number(fleet.get("stuck")), waiting=number(fleet.get("waiting")),
                       green=number(fleet.get("green")), idle=number(fleet.get("idle")), total=number(fleet.get("total")), alerts=number(alerts.get("total")))]
    if name == "alerts":
        alerts = snap.get("alerts") if isinstance(snap.get("alerts"), dict) else {}
        rows = [r for r in (alerts.get("rows") or []) if isinstance(r, dict)]
        total = number(alerts.get("total"))
        if not total:
            return [i18n.t("chatops.alerts_none")]
        shown = rows[:max_rows]
        lines = [i18n.t("chatops.alerts_head", total=total, shown=len(shown))]
        for row in shown:
            level, code = esc(row.get("level"), 12), esc(row.get("code"), 40)
            lines.append("- " + (i18n.t("chatops.alert_line_repo", level=level, code=code, repo=esc(row.get("repo"), 60)) if row.get("repo") else i18n.t("chatops.alert_line", level=level, code=code)) + tail(row))
        if total > len(shown):
            lines.append(i18n.t("chatops.more", n=total - len(shown)))
        return lines
    if name == "red":
        rows = [r for r in (snap.get("red") or []) if isinstance(r, dict)]
        total = max(number(fleet.get("red")), len(rows))
        if not total:
            return [i18n.t("chatops.red_none")]
        shown = rows[:max_rows]
        lines = [i18n.t("chatops.red_head", total=total, shown=len(shown))]
        for row in shown:
            if row.get("workflow"):
                lines.append("- " + i18n.t("chatops.red_line", repo=esc(row.get("repo"), 60), workflow=esc(row.get("workflow"), 60), age=age(row.get("seconds")), streak=number(row.get("streak"))) + tail(row))
            else:
                lines.append("- " + i18n.t("chatops.red_line_hidden", repo=esc(row.get("repo"), 60), age=age(row.get("seconds")), streak=number(row.get("streak"))) + tail(row))
        if total > len(shown):
            lines.append(i18n.t("chatops.more", n=total - len(shown)))
        return lines
    if name == "queue":
        queue = snap.get("queue") if isinstance(snap.get("queue"), dict) else {}
        return [i18n.t("chatops.queue", running=number(queue.get("running")), queued=number(queue.get("queued")), approval=number(queue.get("approval")), minutes24=number(queue.get("minutes24")))]
    if name == "score":
        score = snap.get("score") if isinstance(snap.get("score"), dict) else {}
        value = score.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return [i18n.t("chatops.score_off")]
        trend = score.get("trend")
        trend = trend if isinstance(trend, (int, float)) and not isinstance(trend, bool) else 0
        return [i18n.t("chatops.score", value=round(value), letter=esc(score.get("letter") or "-", 3), trend=("%+d" % round(trend)))]
    return [i18n.t("chatops.unknown")]
