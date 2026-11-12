# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--demo`: the real web page with INVENTED data (the demo-* repositories of the demo-owner account), so the monitor can be tried without `gh`, a login or a network.

Nothing is read from GitHub, nothing is written outside a temporary folder, the configuration of the user is not touched and the loop that reads GitHub is not started.
"""
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

OWNER = "demo-owner"
REPOS = ["demo-alpha-core", "demo-alpha-app", "demo-beta-fw", "demo-beta-docs", "demo-gamma-api", "demo-gamma-ui"]
PLAN = {"demo-alpha-core": ["success"] * 6, "demo-alpha-app": ["success", "failure", "failure"] + ["success"] * 3, "demo-beta-fw": ["success"] * 5,
        "demo-beta-docs": ["success", "success", "failure", "success"], "demo-gamma-api": ["failure"] + ["success"] * 4, "demo-gamma-ui": ["success"] * 5}


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run(repo, name, status, conclusion, started, rid, seconds):
    return {"repo": repo, "id": rid, "name": name, "title": f"demo change {rid}", "event": "push", "branch": "main", "path": "ci.yml", "sha": f"{(rid * 7919) % 16 ** 7:07x}", "actor": "demo-user",
            "status": status, "conclusion": conclusion, "started": iso(started), "seconds": seconds, "url": f"https://example.invalid/{OWNER}/{repo}/actions/runs/{rid}", "attempt": 1}


def data(now):
    runs, active, rid = [], [], 100
    for repo, outcomes in PLAN.items():
        for i, outcome in enumerate(outcomes):
            rid += 1
            runs.append(make_run(repo, "CI" if i % 2 == 0 else "Release build", "completed", outcome, now - timedelta(hours=2 + 5 * i), rid, 40 + (rid * 13) % 300))
    for repo, name, status, secs in (("demo-beta-fw", "Firmware build", "in_progress", 640), ("demo-gamma-ui", "CI", "queued", 20)):
        rid += 1
        run = make_run(repo, name, status, None, now - timedelta(seconds=secs), rid, secs)
        run.update({"stuck": False, "jobs": [{"name": "build", "status": "in_progress", "conclusion": None, "steps_total": 8, "steps_done": 5, "step": "Compile", "runner": "demo-runner", "seconds": secs,
                                              "url": "#"}] if status == "in_progress" else []})
        active.append(run)
    runs += active
    runs.sort(key=lambda r: r["started"], reverse=True)
    failing = [r for r in runs if r["status"] == "completed" and r["conclusion"] == "failure"][:3]
    done = [r for r in runs if r["status"] == "completed"]
    figures = {"active": 1, "queued": 1, "fail24": sum(1 for r in done if r["conclusion"] == "failure"), "ok24": sum(1 for r in done if r["conclusion"] == "success"), "issues": 1, "min24": 42}
    return {"updated": iso(now), "took": 1.0, "repos": REPOS, "ecosystems": {r: "other" for r in REPOS}, "runs": runs, "active": active,
            "issues": [{"repo": "demo-alpha-app", "number": 12, "title": "Build failed: Release build", "created": iso(now - timedelta(days=1)), "labels": ["build-failed"], "url": "#"}],
            "failing": failing, "errors": {}, "rate": {"remaining": 4800, "limit": 5000, "reset": iso(now + timedelta(minutes=40))}, "stuck_minutes": 120, "mode": "demo", "refreshed": 0, "hot": 3,
            "loading": "", "min_rate": 800, "paused_quota": False, "refresh_seconds": 45, "hot_only": {"on": False, "seconds_left": 0}, "offline": {"offline": False, "since": None, "last_ok": iso(now)},
            "etag": {"enabled": False, "entries": 0, "saved": 0, "calls": 0}, "hidden": 0, "discovered": len(REPOS), "hidden_names": [], "figures": figures}


STATE_FILES = (("actions_monitor", "LOG_FILE", "actions_monitor_log_demo.txt"), ("etagcache", "CACHE_FILE", "etag_cache_demo.json"), ("events", "EVENTS_FILE", "events_monitor_demo.jsonl"),
               ("events", "STATE_FILE", "events_state_demo.json"), ("analytics", "HISTORY_FILE", "analytics_history_demo.json"), ("ai_actions", "LOG_FILE", "ai_actions_log_demo.jsonl"),
               ("updatecheck", "STATE_FILE", "update_check_demo.json"), ("ghactions", "LOG_FILE", "github_actions_log_demo.jsonl"), ("sentinel_local", "CACHE_FILE", "sentinel_cache_demo.json"),
               ("sentinel_local", "HISTORY_FILE", "sentinel_history_demo.json"), ("sentinel_ai", "CACHE_FILE", "sentinel_ai_cache_demo.json"), ("sentinel_collab", "STATE_FILE", "collab_state_demo.json"), ("alert_center", "STATE_FILE", "alert_mutes_demo.json"))


def redirect_state(tmp):
    """Every file the monitor writes by itself (logs, caches, event feed, history, the ci_red export of the sentinel) goes to the temporary folder of the demo, with the suffix _demo: the files of the
    real installation are neither read nor written. Only modules that are already loaded are touched (the demo does not load the sentinel). Returns the list of (module, attribute) redirected."""
    import sys
    done = []
    for module, attribute, name in STATE_FILES:
        loaded = sys.modules.get(module)
        if loaded is not None and hasattr(loaded, attribute):
            setattr(loaded, attribute, tmp / name)
            done.append((module, attribute))
    return done


def start(am, port, tmp=None):
    """Serves the demo page on 127.0.0.1:port (blocks). `am` is the actions_monitor module."""
    import settings_api
    import toolconfig
    tmp = Path(tmp) if tmp else Path(tempfile.mkdtemp(prefix="ghamon_demo_"))
    redirect_state(tmp)
    cfg = json.loads((Path(__file__).resolve().parent / "actions_monitor.example.json").read_text(encoding="utf-8"))
    cfg.update({"github_owner": OWNER, "workspace_root": "", "signed_dir": "", "audit_dir": "", "sentinel": {"enabled": False}, "updates": {"check": False}})
    am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = tmp / "actions_monitor.json"
    am.CONFIG_FILE.write_text(json.dumps(cfg), encoding="utf-8")
    settings_api.BACKUP_DIR = tmp / "backups"
    toolconfig.set_owner(OWNER)
    am.DEMO["on"] = True
    am.LIVE_CONFIG.update(cfg)
    am.ETAG["cache"] = None
    snapshot = data(datetime.now(timezone.utc).replace(microsecond=0))
    with am.LOCK:
        am.STATE.update({"data": snapshot, "error": None, "hint": None, "complete": True})
    server = am.QuietServer(("127.0.0.1", port), am.Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    return server, url
