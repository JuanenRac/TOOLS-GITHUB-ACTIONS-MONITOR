#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/demo_monitor.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A demo monitor with invented data (the demo-* repositories of the demo-owner account) for the screenshots of the documentation.

    python tools/demo_monitor.py [PORT] [--lite] [--network]   # default 18765; runs until it is stopped

It starts the real web server of the monitor on 127.0.0.1 with a temporary configuration and made-up runs, alerts, a signing queue, analytics and linter findings, so the page can be
photographed without touching your own configuration or GitHub. Nothing is read from GitHub and nothing is written outside a temporary folder.

`--network` shows the page as it looks in the network mode (the persistent red bar and, in Settings, the warning for every interface) so that it can be photographed: the page only
shows them, the demo still listens on 127.0.0.1 only and no access token is needed. It exists for the pictures and is never the real network mode.
"""
import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "monitor"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import actions_monitor as am  # noqa: E402
import analytics  # noqa: E402
import etagcache  # noqa: E402
import sentinel_local as sl  # noqa: E402
import settings_api  # noqa: E402
import toolconfig  # noqa: E402
from test_sentinel import run as make_run  # noqa: E402

OWNER = "demo-owner"
REPOS = ["demo-alpha-core", "demo-alpha-app", "demo-beta-fw", "demo-beta-docs", "demo-gamma-api", "demo-gamma-ui"]


def setup(now):
    tmp = Path(tempfile.mkdtemp(prefix="ghamon_demo_"))
    cfg = json.loads((ROOT / "actions_monitor.example.json").read_text(encoding="utf-8"))
    cfg.update({"github_owner": OWNER, "workspace_root": "", "signed_dir": "", "audit_dir": ""})
    (tmp / "actions_monitor.json").write_text(json.dumps(cfg), encoding="utf-8")
    am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = tmp / "actions_monitor.json"
    settings_api.BACKUP_DIR = tmp / "backups"
    toolconfig.set_owner(OWNER)
    toolconfig.set_ecosystems({"alpha": {"label": "Alpha", "prefixes": ["demo-alpha-"]}, "beta": {"label": "Beta", "prefixes": ["demo-beta-"]}, "gamma": {"label": "Gamma", "prefixes": ["demo-gamma-"]}})
    am.LIVE_CONFIG.update(cfg)
    return cfg, tmp


def build(now):
    iso = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    plan = {"demo-alpha-core": ["success"] * 7, "demo-alpha-app": ["success", "failure", "failure", "failure"] + ["success"] * 3, "demo-beta-fw": ["success"] * 6,
            "demo-beta-docs": ["success", "success", "failure", "success", "success"], "demo-gamma-api": ["failure", "failure"] + ["success"] * 5, "demo-gamma-ui": ["success"] * 6}
    runs, rid = [], 100
    for repo, outcomes in plan.items():
        for i, outcome in enumerate(outcomes):
            rid += 1
            row = make_run(repo, "CI" if i % 2 == 0 else "Release build", outcome, iso(now - timedelta(hours=2 + 5 * i)), rid=rid, path="ci.yml" if i % 2 == 0 else "build.yml")
            row.update({"sha": f"{(rid * 7919) % 16 ** 7:07x}", "url": f"https://github.com/{OWNER}/{repo}/actions/runs/{rid}", "title": f"demo change {rid}", "event": "push", "actor": "demo-user", "seconds": 40 + (rid * 37) % 600, "attempt": 1})
            runs.append(row)
    for extra_id, outcome, hours in ((900, "failure", 40), (901, "success", 39)):     # a failure that passed on the very same commit: a flaky workflow
        row = make_run("demo-beta-docs", "CI", outcome, iso(now - timedelta(hours=hours)), rid=extra_id)
        row.update({"sha": "aaaaaaa", "url": f"https://github.com/{OWNER}/demo-beta-docs/actions/runs/{extra_id}", "seconds": 75, "attempt": 1, "event": "push", "actor": "demo-user", "title": "demo"})
        runs.append(row)
    active = []
    for repo, name, status, secs in (("demo-beta-fw", "Firmware build", "in_progress", 640), ("demo-alpha-app", "Release build", "in_progress", 190), ("demo-gamma-ui", "CI", "queued", 20)):
        rid += 1
        run = make_run(repo, name, None, iso(now - timedelta(seconds=secs)), rid=rid, status=status)
        run.update({"url": f"https://github.com/{OWNER}/{repo}/actions/runs/{rid}", "title": "demo run", "event": "push", "actor": "demo-user", "seconds": secs, "stuck": False,
                    "jobs": [{"name": "build", "status": "in_progress", "conclusion": None, "steps_total": 8, "steps_done": 5, "step": "Compile", "runner": "demo-runner-1", "seconds": secs, "url": "#"},
                             {"name": "test", "status": "completed", "conclusion": "success", "steps_total": 6, "steps_done": 6, "step": "", "runner": "demo-runner-2", "seconds": 90, "url": "#"}]
                    if status == "in_progress" else []})
        active.append(run)
    runs.sort(key=lambda r: r["started"], reverse=True)
    issues = [{"repo": "demo-alpha-app", "number": 12, "title": "Build failed: Release build", "created": iso(now - timedelta(days=1)), "labels": ["build-failed"], "url": "#"}]
    data = {"updated": iso(now), "took": 4.2, "repos": REPOS, "ecosystems": {r: am.ecosystem_of(r) for r in REPOS}, "runs": runs, "active": active, "issues": issues, "failing": am.unresolved_failures(runs),
            "errors": {}, "rate": {"remaining": 4630, "limit": 5000, "reset": iso(now + timedelta(minutes=40))}, "stuck_minutes": 120, "mode": "full", "refreshed": 3, "hot": 4, "loading": "", "min_rate": 1500,
            "paused_quota": False, "refresh_seconds": 120, "hot_only": {"on": False, "seconds_left": 0}, "offline": {"offline": False, "since": None, "last_ok": iso(now)},
            "etag": {"enabled": True, "entries": 64, "saved": 482, "calls": 1290}}
    for run in runs:
        am.RUN_CACHE.setdefault(run["repo"], {"runs": [], "at": time.time(), "error": None})["runs"].append(run)
    am.STATE.update({"data": data, "error": None, "hint": None, "complete": True})
    return data, runs, iso


def snapshot(now, data, runs, iso):
    info = {r: {"branch": "main", "pushed": iso(now - timedelta(hours=3)), "release": {"tagName": "v1.2.0", "publishedAt": iso(now - timedelta(days=9))}, "vuln_total": 0, "vuln_sev": {}, "prs": [],
                "rulesets": [{"name": "protect-main", "enforcement": "ACTIVE"}], "label_dependencies": True, "files": {"README.md": True, "LICENSE.md": True, "CHANGELOG.md": True, "SECURITY.md": True}}
            for r in REPOS}
    by_repo = {r: [x for x in runs if x["repo"] == r] for r in REPOS}
    snap = sl.compute_snapshot({"now": now, "today": now.strftime("%Y-%m-%d"), "cfg": sl.DEFAULTS, "repos": REPOS, "eco": {r: am.ecosystem_of(r) for r in REPOS}, "repo_info": info,
                                "alerts": {r: {"at": 1, "codeql": [], "secret": 0} for r in REPOS}, "perms": {}, "runs": by_repo, "data": data, "history": {"days": {}},
                                "unreleased": {"demo-beta-docs": 4, "demo-gamma-api": 3}, "targets": {}, "errors": {}, "loading": "", "audits": None,
                                "lint": {"by_repo": {"demo-alpha-app": [{"file": "ci.yml", "line": 14, "rule": "unpinned_uses", "severity": "warn", "detail": "actions/setup-python@v5"},
                                                                          {"file": "release.yml", "line": 3, "rule": "permissions", "severity": "warn", "detail": "missing"}],
                                                    "demo-gamma-ui": [{"file": "deploy.yml", "line": 22, "rule": "injection", "severity": "warn", "detail": ""}]},
                                         "summary": {"findings": 3, "repos": 2, "bad": 0, "warn": 3, "info": 0, "by_rule": {}, "top": [("demo-alpha-app", 2), ("demo-gamma-ui", 1)]}, "in_report": True}})

    def queue(name, repo, eco, hours, trust, kind):
        return {"name": name, "repo": repo, "ecosystem": eco, "hours": hours, "step": "sign", "run_id": 4242, "last_build_at": iso(now - timedelta(hours=hours)), "signature_kind": kind,
                "signature_verified": {"verified": True, "failed": False}.get(trust, "unknown"), "trust": trust, "url": "#", "argv": [], "command": f"py -3 demo_fetch_and_sign.py {repo} --run 4242",
                "attestation": trust == "verified"}
    snap["a5"]["sign_queue"] = [queue("demo-beta-fw firmware", "demo-beta-fw", "beta", 31, "verified", "release"), queue("demo-alpha-app package", "demo-alpha-app", "alpha", 20, "unknown", "none"),
                                queue("demo-gamma-ui bundle", "demo-gamma-ui", "gamma", 7, "failed", "dev")]
    snap["a5"]["pending_sign"] = [dict(q, pending_sign_hours=q["hours"], workflow="build.yml", state="built_on_gha") for q in snap["a5"]["sign_queue"] if q["hours"] > 24]
    snap["a11"]["enabled"] = True
    snap["a11"]["health"] = [{"ecosystem": "alpha", "score": 64, "coverage": 1.0, "external": False, "parts": []}, {"ecosystem": "beta", "score": 92, "coverage": 1.0, "external": False, "parts": []},
                             {"ecosystem": "gamma", "score": 81, "coverage": 1.0, "external": False, "parts": []}]
    snap["a11"]["warn_below"] = 70
    return snap


def demo_analytics(runs):
    store = analytics.Store(Path(tempfile.mkdtemp()) / "a.json")
    job = {"created_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:12Z", "steps": [{"name": "Set up job", "started_at": "2026-01-01T00:00:12Z", "completed_at": "2026-01-01T00:00:14Z"},
                                                                                             {"name": "Build", "started_at": "2026-01-01T00:00:14Z", "completed_at": "2026-01-01T00:02:44Z"},
                                                                                             {"name": "Test", "started_at": "2026-01-01T00:02:44Z", "completed_at": "2026-01-01T00:04:04Z"}]}
    for i, (repo, workflow) in enumerate((("demo-beta-fw", "Release build"), ("demo-alpha-app", "Release build"), ("demo-gamma-api", "CI"))):
        for n in range(8):
            queued = dict(job, started_at=f"2026-01-01T00:00:{10 + i * 7 + n:02d}Z")
            store.add_jobs(repo, workflow, 5000 + i * 100 + n, [queued])
    cfg = analytics.settings({"analytics": {"min_samples": 3}})
    summary = analytics.summary(runs, store, cfg)
    summary["slower"] = [{"repo": "demo-beta-fw", "workflow": "Release build", "p50": 410, "usual": 240, "factor": 1.71}]
    return summary


def main():
    lite = "--lite" in sys.argv
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    port = int(numbers[0]) if numbers else 18765
    now = datetime.now(timezone.utc).replace(microsecond=0)
    setup(now)
    am.LITE["on"] = lite       # the lite edition: no sentinel, no analytics, a short settings page
    data, runs, iso = build(now)
    snap = snapshot(now, data, runs, iso)

    class Demo:
        ai_cfg = {"provider": "none"}

        def snapshot(self):
            return snap

        def refresh_repos(self, names):
            return names
    if not lite:
        am.SENTINEL["obj"] = Demo()
        am.ANALYTICS["store"] = analytics.Store(Path(tempfile.mkdtemp()) / "a.json")
        am.ANALYTICS["summary"] = demo_analytics(runs)
    am.ETAG["cache"] = etagcache.EtagCache(Path(tempfile.mkdtemp()) / "e.json")
    am.update_info = lambda: {"enabled": True, "newer": True, "latest": "9.9.9", "current": am.TOOL_VERSION, "url": "https://example.invalid/release", "changelog": "https://example.invalid/changelog", "airgapped": False}   # an invented newer version, for the picture of the badge
    am.LIVE_CONFIG.update({"account": {"plan": "free"}, "session_guard": False})
    if "--network" in sys.argv:      # only what the page shows: the server below still listens on 127.0.0.1 and localguard stays off
        real_state = am.localguard.public_state
        am.localguard.public_state = lambda: {**real_state(), "network": True, "host": "0.0.0.0", "token_required": True, "secure": True}
    server = ThreadingHTTPServer(("127.0.0.1", port), am.Handler)
    print("demo on", port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
