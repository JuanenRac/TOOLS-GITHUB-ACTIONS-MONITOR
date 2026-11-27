#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/demo_parts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Invented data for the boxes of the optional parts (`python tools/demo_monitor.py PORT --parts`): extensions, proposals of the AI, the chat, the collaboration views, the fleet by role and group
and the posture report. Everything is made up, nothing is read from GitHub or from a model, and what would be kept in a file of the monitor lives in the memory of the demo process.

`settings(cfg)` is applied to the configuration of the demo before it is written and `fill(...)` after the runs were made."""
import hashlib
import tempfile
import time
from pathlib import Path

#: the blocks the demo switches on (every one of them is off by default in the monitor)
ON = {"teamwork": {"enabled": True, "inactive_workflows": True, "keep_alive_days": 45, "dismissed_alerts": True, "dismiss_allowed": ["demo-lead"]}, "posture": {"enabled": True},
      "plugins": {"enabled": True, "third_party": {"enabled": True}, "official": {"discussions": {"enabled": True}}}}


def settings(cfg):
    """The configuration of the demo with the optional parts on."""
    for key, block in ON.items():
        cfg[key] = {**cfg.get(key, {}), **block}
    ai = dict(cfg.get("ai") or {})
    ai["chat"] = {"enabled": True}
    ai["actions"] = {**(ai.get("actions") or {}), "enabled": True}
    ai["assistant"] = {"can_propose": True}
    cfg["ai"] = ai
    return cfg


def _collaboration(runs, iso, now):
    from github_actions_monitor.data_pipeline import run_dismiss
    from github_actions_monitor.families.actions import actions_engine as engine
    stamp = time.time()
    extra = [dict(runs[0], id=701, repo="demo-gamma-ui", name="Deploy", path="deploy.yml", status="waiting", conclusion=None, started=iso(now), url="#"),
             dict(runs[0], id=702, repo="demo-alpha-app", name="CI", path="ci.yml", status="completed", conclusion="action_required", fork=True, event="pull_request", started=iso(now), url="#"),
             dict(runs[0], id=703, repo="demo-beta-fw", name="Firmware build", path="build.yml", status="queued", conclusion=None, started=iso(now), url="#")]
    view = engine.runs_view({"teamwork": ON["teamwork"]}, extra + runs, stamp)
    view["all_runs"], view["repos_waiting"] = [], []

    def pull(repo, number, title, group, bot="", behind=False, failing=0, author="demo-user"):
        return {"repo": repo, "number": number, "title": title, "author": author, "url": "#", "draft": False, "bot": bot, "state": "clean", "failing": failing, "behind": behind, "group": group}
    repos = {"demo-alpha-app": {"at": stamp, "pulls": [pull("demo-alpha-app", 41, "Bump the build tools", "needs_action", "author", failing=2, author="dependabot[bot]"),
                                                       pull("demo-alpha-app", 44, "Faster cache of the build", "pending_rebase", behind=True)],
                                "vulnerable": {"repo": "demo-alpha-app", "critical": 1, "high": 2, "oldest_days": 23, "url": "#"},
                                "dismissals": [{"repo": "demo-alpha-app", "kind": "dependency", "number": 7, "who": "demo-user", "reason": "tolerable_risk", "at": iso(now), "url": "#", "authorized": False}],
                                "workflows": [], "ageing": [], "unread": {}},
             "demo-beta-docs": {"at": stamp, "pulls": [pull("demo-beta-docs", 12, "New guide of the screens", "mergeable")], "vulnerable": None, "dismissals": [],
                                "workflows": [{"repo": "demo-beta-docs", "id": 5001, "name": "Weekly links"}],
                                "ageing": [{"repo": "demo-beta-docs", "id": 5002, "name": "Nightly spelling", "quiet_days": 52, "days_left": 8}], "unread": {"dismissals": "forbidden"}}}
    data = {"repos": repos, "runs_view": view, "rerun": {}, "hooks": [{"at": iso(now), "phase": "started", "repo": "demo-owner/demo-beta-fw", "run": "4242", "job": "build", "workflow": "Firmware build",
                                                                      "runner": "demo-runner-1"}]}
    engine.load = lambda account="": data
    run_dismiss.rows = lambda now=None: [{"repo": "demo-gamma-api", "run": 99, "owner": "demo-lead", "reason": "waits for the new server", "at": int(stamp), "until": int(stamp + 86400 * 14)}]


def _posture(iso, now):
    from github_actions_monitor.families.posture import posture_catalogue as catalogue
    from github_actions_monitor.families.posture import posture_engine as engine
    stamp = time.time()
    by_group = {}
    for check, row in catalogue.CHECKS.items():
        by_group.setdefault(row[2], []).append(check)

    def entry(wanted, items, unread=None):
        checked = sorted(g for g in by_group if g not in (unread or {}))
        return {"at": stamp, "kind": "standard", "findings": [{"check": by_group[g][0], "item": item, "detail": ""} for g, item in zip(wanted, items) if g in by_group], "unread": unread or {}, "checked": checked, "skipped": ""}
    groups = [g for g in sorted(by_group) if g not in ("org", "upstream")]
    repos = {"demo-alpha-app": entry(groups[:3], ["main", "deploy.yml", ""]), "demo-gamma-api": entry(groups[3:5], ["demo-key", ""], {groups[0]: "forbidden"}), "demo-beta-fw": entry([], [])}
    org = entry(["org"], [""]) if "org" in by_group else entry([], [])
    org["kind"] = "organization"
    history = [{"day": time.strftime("%Y-%m-%d", time.gmtime(stamp - 86400 * (9 - i))), "error": [3, 3, 3, 2, 2, 2, 1, 1, 1, 1][i], "warning": [6, 6, 5, 5, 5, 4, 4, 3, 3, 3][i], "info": 2, "repos": 3} for i in range(10)]
    data = {"repos": repos, "org": org, "history": history}
    engine.load = lambda account="": data


def _assistant(config_runs):
    from github_actions_monitor.integrations import ai_actions, ai_chat
    store = ai_actions.Actions(log_file=Path(tempfile.mkdtemp(prefix="ghamon_demo_ai_")) / "ai_actions.jsonl", persist=False)
    command = "gh run rerun 104 --failed -R demo-owner/demo-alpha-app"
    store.pending["demo1"] = {"id": "demo1", "action": "rerun_failed", "command": command, "runnable": False, "argv": None, "repo": "demo-alpha-app", "at": store.clock(), "ttl": 3600, "status": "pending", "by": "",
                              "number": 104, "owner": "demo-owner", "origin": "ia", "creator": "demo-user", "hash": hashlib.sha256(command.encode("utf-8")).hexdigest(), "approvers": []}
    ai_actions.ACTIONS = store
    ai_chat.ask = lambda message, history, cfg, reader, explain: {"ok": True, "error": "", "tool_calls": 2,
                                                                  "text": "demo-alpha-app has Release build red on main since yesterday: three runs in a row end in the build step (npm: missing script build). demo-gamma-api recovered this morning.",
                                                                  "sources": [{"tool": "list_alerts", "repo": ""}, {"tool": "repo_runs", "repo": "demo-alpha-app"}]}


def _extensions():
    from github_actions_monitor.plugins import plugin_host as host

    def catalogue(config):
        rows = []
        for name, (manifest, _folder) in sorted(host.official().items()):
            on = name == "discussions"
            rows.append({"name": name, "version": manifest["version"], "trust": manifest["trust"], "author": manifest["author"], "description": manifest["description"], "permissions": manifest["permissions"],
                         "get_paths": manifest["get_paths"], "enabled": on, "state": "healthy" if on else "off", "reason": "", "isolation": "in_process", "key_id": "", "fingerprint": "", "check": "ok"})
        rows.append({"name": "demo-badges", "version": "0.3.0", "trust": "third_party", "author": "Demo Author", "description": "Counts the workflows without a status badge (an invented extension).",
                     "permissions": ["contents:read"], "get_paths": ["repos/{owner}/{repo}/readme"], "enabled": True, "state": "healthy", "reason": "", "isolation": "no_network_isolation",
                     "key_id": "demo0123456789ab", "fingerprint": "9f2c41d7a0b35e68c1d4f7a92b60e3c85d1a4f7096b2e8c31a5d70f4b92c6e18", "check": "ok"})
        return {"ok": True, "enabled": True, "third_party": True, "plugins": rows, "candidates": []}
    host.catalogue = catalogue


def fill(repos, runs, iso, now):
    """The invented answers behind the boxes. Only the functions that read a file, a model or GitHub are replaced: the code that turns them into the page is the one of the monitor."""
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.families.fleet import fleet_views
    toolconfig._raw_cache["at"] = 0.0      # noqa: SLF001 - what was read before the file of the demo existed is forgotten
    _collaboration(runs, iso, now)
    _posture(iso, now)
    _assistant(runs)
    _extensions()
    fleet_views.remember(runs, repos)
