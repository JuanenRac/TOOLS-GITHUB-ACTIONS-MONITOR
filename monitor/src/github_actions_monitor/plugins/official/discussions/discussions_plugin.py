# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Official plugin: open discussions without any comment for more than `days` days. Codes plugin.discussions.* only (issues and pull requests are the business of Collab)."""
import calendar
import time

from github_actions_monitor import i18n


def age_days(text, now):
    try:
        return (now - calendar.timegm(time.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ"))) / 86400
    except (ValueError, OverflowError):
        return -1


def run(ctx):
    days = ctx.options.get("days", 7)
    alerts = []
    for node in ctx.discussions():
        age = age_days(node.get("createdAt"), ctx.now)
        if node.get("closed") or (node.get("comments") or {}).get("totalCount") or age < days:
            continue
        repo = node["repository"]["name"]
        alerts.append({"id": f"{repo}#{node.get('number')}", "code": "unanswered", "level": "info", "repo": repo, "url": node.get("url"),
                       "title": i18n.t("ui.plugins.alert_discussion", repo=repo, number=node.get("number"), days=int(age), title=str(node.get("title"))[:60])})
    return {"alerts": alerts}
