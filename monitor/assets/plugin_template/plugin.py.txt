# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# Example plugin of GitHub Actions Monitor. Change it as you like: this file is yours (GPL-3.0-or-later).
"""run(ctx) returns {"alerts": [{"id", "code", "level", "repo", "url", "title"}]}. ctx offers: ctx.owner, ctx.now, ctx.repos(), ctx.get(path) and ctx.discussions()."""


def run(ctx):
    alerts = []
    for repo in ctx.repos()[:50]:
        if not ctx.get(f"repos/{ctx.owner}/{repo}/labels"):
            alerts.append({"id": repo, "code": "no_labels", "level": "info", "repo": repo, "url": f"https://github.com/{ctx.owner}/{repo}/labels", "title": f"{repo} has no label"})
    return {"alerts": alerts}
