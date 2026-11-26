# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The fleet seen by role and by group, the CCTray feed and the switch of repositories and groups. The last runs of a cycle are kept in memory by the tick of the part; the rest is pure."""
import fnmatch
import threading
import time
import xml.sax.saxutils

from github_actions_monitor import families
from github_actions_monitor.app import toolconfig

BAD = ("failure", "timed_out", "startup_failure", "action_required")
ORDER = {"red": 3, "running": 2, "unknown": 1, "ok": 0}
LOCK = threading.RLock()
SNAPSHOT = {"at": 0.0, "runs": [], "repos": []}


def settings(config):
    return families.block(config if isinstance(config, dict) else {}, "fleet")


def remember(runs, repos, now=None):
    keep = ("repo", "name", "path", "branch", "status", "conclusion", "started", "url", "number", "event")
    with LOCK:
        SNAPSHOT.update(at=time.time() if now is None else now, runs=[{k: r.get(k) for k in keep} for r in runs or [] if isinstance(r, dict)][:5000],
                        repos=[str((r.get("name") if isinstance(r, dict) else r) or "").split("/")[-1] for r in repos or []])


def snapshot():
    with LOCK:
        return {"at": SNAPSHOT["at"], "runs": list(SNAPSHOT["runs"]), "repos": list(SNAPSHOT["repos"])}


def group_of(repo):
    return toolconfig.ecosystem_of(repo or "") or "other"


def switched_off(repo, disabled):
    """True when a line of `fleet.disabled` names the repository (a pattern) or its group ("group:<key>")."""
    name = str(repo or "").lower()
    for line in disabled or ():
        line = str(line).lower()
        if line.startswith("group:"):
            if group_of(repo).lower() == line[6:]:
                return True
        elif fnmatch.fnmatchcase(name, line):
            return True
    return False


def roles(lines):
    """[(role, [patterns])] from `fleet.roles` lines "role=pattern|pattern"."""
    out = []
    for line in lines or ():
        role, mark, patterns = str(line).partition("=")
        if mark and role:
            out.append((role, [p.lower() for p in patterns.split("|") if p]))
    return out


def role_of(run, table):
    names = [str(run.get("name") or "").lower(), str(run.get("path") or "").lower()]
    for role, patterns in table:
        if any(fnmatch.fnmatchcase(n, p) for n in names for p in patterns):
            return role
    return "other"


def latest(runs):
    """The newest run of each (repository, workflow), with the state of the newest finished one: {"state", "running", "run"}."""
    out = {}
    for run in sorted(runs, key=lambda r: str(r.get("started") or "")):
        key = (run.get("repo"), run.get("path") or run.get("name"))
        entry = out.setdefault(key, {"state": "unknown", "running": False, "run": run})
        if run.get("status") != "completed":
            entry["running"] = True
        else:
            entry["running"] = False
            conclusion = run.get("conclusion")
            if conclusion in BAD:
                entry.update(state="red", run=run)
            elif conclusion == "success":
                entry.update(state="ok", run=run)
    return out


def worst(states):
    return max(states, key=lambda s: ORDER.get(s, 1), default="unknown")


def columns(runs, repos, table):
    """{"roles": [names], "rows": [{"repo", "group", "state", "cells": {role: state}}]}: one column per role of workflow."""
    names = [role for role, _p in table] + ["other"]
    cells = {}
    for (repo, _workflow), entry in latest(runs).items():
        role = role_of(entry["run"], table)
        state = "running" if entry["running"] and entry["state"] != "red" else entry["state"]
        cells.setdefault(repo, {}).setdefault(role, []).append(state)
    rows = []
    for repo in sorted(set(repos) | set(cells)):
        found = {role: worst(states) for role, states in cells.get(repo, {}).items()}
        rows.append({"repo": repo, "group": group_of(repo), "state": worst(found.values()), "cells": found})
    return {"roles": names, "rows": rows}


def groups(view):
    """The worst case of each group, the worst first: {"key", "state", "repos", "red", "rows"}."""
    out = {}
    for row in view["rows"]:
        out.setdefault(row["group"], []).append(row)
    result = [{"key": key, "state": worst(r["state"] for r in rows), "repos": len(rows), "red": sum(1 for r in rows if r["state"] == "red"), "rows": sorted(rows, key=lambda r: (-ORDER.get(r["state"], 1), r["repo"]))}
              for key, rows in out.items()]
    return sorted(result, key=lambda g: (-ORDER.get(g["state"], 1), g["key"]))


def projects(runs):
    """The projects of the CCTray feed, one per workflow of a repository."""
    out = []
    for (repo, workflow), entry in sorted(latest(runs).items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        run = entry["run"]
        out.append({"name": f"{repo} :: {run.get('name') or workflow}", "activity": "Building" if entry["running"] else "Sleeping",
                    "lastBuildStatus": {"red": "Failure", "ok": "Success"}.get(entry["state"], "Unknown"), "lastBuildLabel": str(run.get("number") or ""),
                    "lastBuildTime": str(run.get("started") or "1970-01-01T00:00:00Z"), "webUrl": str(run.get("url") or "")})
    return out


def cctray_xml(found):
    quote = xml.sax.saxutils.quoteattr
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<Projects>"]
    for project in found:
        attributes = " ".join(f"{k}={quote(''.join(c for c in v if c.isprintable()))}" for k, v in project.items())
        lines.append(f"  <Project {attributes}/>")
    return "\n".join(lines + ["</Projects>", ""])


def security_alerts(registry, kind):
    """The open alerts of the security sentinel of one kind ("secrets" or "code-scanning"), counts only, with the repositories that could not be read named. Never the value of a secret."""
    sentinel = registry.get("security") if registry else None
    if sentinel is None or not getattr(sentinel, "enabled", False):
        return {"ok": True, "available": False, "reason": "sentinel_off", "alerts": [], "not_read": []}
    code = {"secrets": "security.secret", "code-scanning": "security.code_scanning"}[kind]
    rows = []
    for alert in sentinel.get_alerts():
        if alert.get("code") == code:
            details = alert.get("details") or {}
            rows.append({"repo": alert.get("repo"), "level": alert.get("level"), "open": details.get("n"), "critical": details.get("critical"), "high": details.get("high"),
                         "since": alert.get("created_at"), "unread_since": details.get("unread_since")})
    status = sentinel.get_status() or {}
    word = "secret" if kind == "secrets" else "code"
    not_read = [{"section": e.get("section"), "message": str(e.get("message") or "")[:120]} for e in status.get("errors") or [] if word in str(e.get("section") or "")]
    return {"ok": True, "available": True, "loading": bool(status.get("loading")), "repos_checked": status.get("repos_checked"), "repos_in_scope": status.get("repos_in_scope"), "alerts": sorted(rows, key=lambda r: str(r["repo"])), "not_read": not_read}
