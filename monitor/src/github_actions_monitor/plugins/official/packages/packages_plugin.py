# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Official plugin: packages (container, npm) with more versions than `max_versions`. Needs the permission read:packages of the token; without it the plugin says it could not look."""
from urllib.parse import quote

from github_actions_monitor import i18n

MAX_PACKAGES = 50


def listing(ctx, kind):
    """(users | orgs, the packages of that type). An organization answers under orgs/."""
    try:
        return "users", ctx.get(f"users/{ctx.owner}/packages?package_type={kind}") or []
    except Exception:      # noqa: BLE001 - the second try says what is wrong
        return "orgs", ctx.get(f"orgs/{ctx.owner}/packages?package_type={kind}") or []


def run(ctx):
    limit = ctx.options.get("max_versions", 50)
    kinds = [k for k in ctx.options.get("types", ["container"]) if k in ("container", "npm")]
    alerts = []
    for kind in kinds:
        base, found = listing(ctx, kind)
        for package in found[:MAX_PACKAGES]:
            name = str(package.get("name") or "")
            count = package.get("version_count")
            if not isinstance(count, int):
                count = len(ctx.get(f"{base}/{ctx.owner}/packages/{kind}/{quote(name, safe='')}/versions?per_page=100") or [])
            if count > limit:
                repo = (package.get("repository") or {}).get("name")
                alerts.append({"id": f"{kind}/{name}", "code": "retention", "level": "info", "repo": repo, "url": package.get("html_url"),
                               "title": i18n.t("ui.plugins.alert_package", name=name, kind=kind, count=count, limit=limit)})
    return {"alerts": alerts}
