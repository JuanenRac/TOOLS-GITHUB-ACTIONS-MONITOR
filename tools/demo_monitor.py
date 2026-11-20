#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/demo_monitor.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A demo monitor with invented data (the demo-* repositories of the demo-owner account) for the screenshots of the documentation.

    python tools/demo_monitor.py [PORT] [--lite] [--network] [--rich] [--kiosk]   # default 18765; runs until it is stopped

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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import analytics  # noqa: E402
from github_actions_monitor.data_pipeline import etagcache  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402
from test_sentinel import run as make_run  # noqa: E402

OWNER = "demo-owner"
REPOS = ["demo-alpha-core", "demo-alpha-app", "demo-beta-fw", "demo-beta-docs", "demo-gamma-api", "demo-gamma-ui"]
#: what the demo puts in each tab of the page: `plain` = the invented runs, alerts and analytics of the plain demo already fill it; `rich` = only `--rich` fills it, with the thing named here. Every tab of the page is here
#: (a test fails when a tab is added without its line, and runs `--rich` to check that every `rich` tab really has data).
TAB_DEMO = {
    "now": ("plain", "running, queued and recent runs"), "al": ("plain", "alerts of the sentinels"), "charts": ("plain", "analytics of the demo runs"),
    "sent": ("plain", "the sentinel snapshot"), "sci": ("plain", "red and stuck workflows"), "scol": ("plain", "collaboration alerts"),
    "ssec": ("rich", "security findings"), "sdel": ("rich", "delivery findings"), "ssup": ("rich", "supply chain findings"),
    "strend": ("rich", "fourteen days of daily trend"), "syvt": ("rich", "a saved report of the day before"),
    "team": ("plain", "the health of the team"), "fleet": ("plain", "the fleet by ecosystem"), "repos": ("plain", "the six demo repositories"),
    "rep": ("rich", "workflow hygiene, queue, release view and supply chain"), "trep": ("rich", "one scheduled report"), "les": ("rich", "four failures in the book of failures"),
    "hist": ("plain", "the demo runs"), "upd": ("plain", "an invented newer version"), "cfg": ("plain", "the settings of the demo"),
}


def setup(now):
    tmp = Path(tempfile.mkdtemp(prefix="ghamon_demo_"))
    cfg = json.loads((ROOT / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
    cfg.update({"github_owner": OWNER, "workspace_root": "", "signed_dir": "", "audit_dir": "", "screens": {**cfg.get("screens", {}), "enabled": True}})      # the wall screens are off by default; the demo shows them
    if "--kiosk" in sys.argv:      # the kiosk profile is off by default too: the measuring tool of the screens asks for it
        cfg["kiosk"] = {**cfg.get("kiosk", {}), "enabled": True}
    (tmp / "actions_monitor.json").write_text(json.dumps(cfg), encoding="utf-8")
    am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = tmp / "actions_monitor.json"
    settings_api.BACKUP_DIR = tmp / "backups"
    toolconfig.set_owner(OWNER)
    toolconfig.set_ecosystems({"alpha": {"label": "Alpha", "prefixes": ["demo-alpha-"]}, "beta": {"label": "Beta", "prefixes": ["demo-beta-"]}, "gamma": {"label": "Gamma", "prefixes": ["demo-gamma-"]}})
    am.LIVE_CONFIG.update(cfg)
    from github_actions_monitor.sentinels import alert_center
    alert_center.STATE_FILE = tmp / "alert_mutes.json"       # a silence made while taking the pictures never reaches the files next to the code
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
                    "jobs": [{"name": "Build and test the firmware image for every supported board (release candidate with the long job name of a real project)", "status": "in_progress", "conclusion": None, "steps_total": 8, "steps_done": 5, "step": "Compile", "runner": "demo-runner-1", "seconds": secs, "url": "#"},
                             {"name": "test", "status": "completed", "conclusion": "success", "steps_total": 6, "steps_done": 6, "step": "", "runner": "demo-runner-2", "seconds": 90, "url": "#"}]
                    if status == "in_progress" else []})
        active.append(run)
    runs.sort(key=lambda r: r["started"], reverse=True)
    issues = [{"repo": "demo-alpha-app", "number": 12, "title": "Build failed: Release build", "created": iso(now - timedelta(days=1)), "labels": ["build-failed"], "url": "#"}]
    data = {"updated": iso(now), "took": 4.2, "repos": REPOS, "ecosystems": {r: am.ecosystem_of(r) for r in REPOS}, "runs": runs, "active": active, "issues": issues, "failing": am.unresolved_failures(runs),
            "errors": {}, "rate": {"remaining": 4630, "limit": 5000, "reset": iso(now + timedelta(minutes=40))}, "stuck_minutes": 120, "mode": "full", "refreshed": 3, "hot": 4, "loading": "", "min_rate": 1500,
            "paused_quota": False, "refresh_seconds": 120, "hot_only": {"on": False, "seconds_left": 0}, "offline": {"offline": False, "since": None, "last_ok": iso(now)},
            "etag": {"enabled": True, "entries": 64, "saved": 482, "calls": 1290},
            "repo_meta": {r: {"private": r.endswith(("fw", "api")), "branch": "main", "pushed": iso(now - timedelta(hours=3 + i)), "prs": i % 3} for i, r in enumerate(REPOS)}}
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


def demo_alerts(now, iso):
    """The alerts of the two sentinels with invented repositories and numbers, for the picture of the Alerts tab."""
    def one(sentinel, code, level, repo, title, hours, url="#", number=None):
        details = {"url": url}
        if number:
            details.update({"number": number, "url": f"https://github.com/{OWNER}/{repo}/issues/{number}"})
        return {"id": f"{code}:{repo}:{number or title[:12]}", "code": code, "level": level, "sentinel": sentinel, "account_id": "", "repo": repo, "title": title, "details": details, "created_at": iso(now - timedelta(hours=hours))}
    return [one("ci", "ci.red", "error", "demo-alpha-app", "demo-alpha-app: Release build is red on main", 30),
            one("ci", "ci.pending_sign", "warning", "demo-beta-fw", "demo-beta-fw: a build waits for its signature (31 h)", 31),
            one("collab", "collab.issue.critical", "error", "demo-gamma-api", "Critical issue (security): demo-gamma-api #31 Token printed in a log", 52, number=31),
            one("collab", "collab.pr.review_pending", "warning", "demo-alpha-core", "Review waiting for 4 days: demo-alpha-core #8 Faster cache", 96, number=8),
            one("collab", "collab.pr.conflict", "warning", "demo-beta-docs", "Pull request with conflicts for 9 days: demo-beta-docs #5 New guide", 220, number=5),
            one("collab", "collab.pr.draft_old", "info", "demo-gamma-ui", "Draft pull request open for 41 days: demo-gamma-ui #14 Dark theme", 980, number=14)]


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


def rich_alerts(now, iso):
    """Invented findings of the Delivery sentinel (release.*) and of the Supply chain sentinel (actions.supply.*)."""
    def one(code, level, repo, title, hours):
        return {"id": f"{code}:{repo}", "code": code, "level": level, "sentinel": "delivery" if code.startswith("release.") else ("security" if code.startswith("security.") else "supply"), "account_id": "", "repo": repo, "title": title, "details": {"url": "#"},
                "created_at": iso(now - timedelta(hours=hours))}
    return [one("release.unreleased_pending", "info", "demo-beta-docs", "demo-beta-docs: 4 changelog entries wait for a release (18 days)", 430),
            one("release.tag_without_release", "warning", "demo-alpha-app", "demo-alpha-app: tag v2.4.0 has no release", 52),
            one("release.version_mismatch", "warning", "demo-gamma-api", "demo-gamma-api: the version file says 1.3.1 and the latest tag is v1.3.0", 120),
            one("release.assets_missing", "warning", "demo-beta-fw", "demo-beta-fw: the release v0.9.0 lacks the checksum file", 75),
            one("release.ecosystem_drift", "warning", "demo-gamma-ui", "demo-gamma-ui pins demo-alpha-core 0.7.0; the provider is at 0.8.2", 200),
            one("actions.supply.unpinned", "warning", "demo-alpha-app", "demo-alpha-app: 3 actions are not pinned to a commit", 90),
            one("actions.supply.mutable_ref", "info", "demo-gamma-ui", "demo-gamma-ui: an action uses a branch as its reference", 300),
            one("actions.supply.permissions_wide", "error", "demo-gamma-api", "demo-gamma-api: a workflow grants write-all to the token", 60),
            one("actions.supply.pr_target_checkout", "error", "demo-beta-docs", "demo-beta-docs: pull_request_target checks out code of the pull request", 40),
            one("security.secret", "error", "demo-gamma-api", "demo-gamma-api: a secret was found in the history (1 open alert)", 18),
            one("security.code_scanning", "warning", "demo-alpha-app", "demo-alpha-app: 2 open code scanning alerts (1 high)", 70),
            one("security.dependabot", "warning", "demo-beta-fw", "demo-beta-fw: 4 open Dependabot alerts (1 critical)", 100),
            one("security.branch_unprotected", "warning", "demo-gamma-ui", "demo-gamma-ui: the default branch is not protected", 260),
            one("security.codeowners_missing", "info", "demo-beta-docs", "demo-beta-docs: no CODEOWNERS file", 500),
            one("security.workflow_write", "warning", "demo-alpha-core", "demo-alpha-core: the workflow token can write by default", 150),
            one("security.runs_deleted", "error", "demo-gamma-api", "demo-gamma-api: 1 workflow run was deleted after the monitor saw it", 30)]


def rich_tabs(config, snap, now):
    """--rich, the tabs that have data of their own: the book of failures of the Lessons tab (four failures of the demo runs) and one scheduled report for the Scheduled reports tab. Each one is written into the temporary
    folders of the demo and none stops the others: a tab that could not be filled says so on the console."""
    from github_actions_monitor.integrations import lessons
    from github_actions_monitor.reporting import report_service
    stamp = int(now.timestamp())
    failures = [{"repo": "demo-alpha-app", "workflow": "Release build", "conclusion": "failure", "cause": "Process completed with exit code 1: npm ERR! missing script build", "url": f"https://github.com/{OWNER}/demo-alpha-app/actions/runs/401"},
                {"repo": "demo-gamma-api", "workflow": "CI", "conclusion": "failure", "cause": "ModuleNotFoundError: No module named 'requests'", "url": f"https://github.com/{OWNER}/demo-gamma-api/actions/runs/402"},
                {"repo": "demo-beta-docs", "workflow": "CI", "conclusion": "timed_out", "cause": "The job running on runner demo-runner-2 has exceeded the maximum execution time of 360 minutes", "url": f"https://github.com/{OWNER}/demo-beta-docs/actions/runs/403"},
                {"repo": "demo-beta-fw", "workflow": "Firmware build", "conclusion": "failure", "cause": "error: linker command failed with exit code 1", "url": f"https://github.com/{OWNER}/demo-beta-fw/actions/runs/404"}]
    try:
        lessons.record(config, failures, now=stamp)
    except Exception as error:   # noqa: BLE001
        print("demo: the Lessons tab stays empty:", error, flush=True)
    try:
        rich_yesterday(snap, now)
    except Exception as error:   # noqa: BLE001
        print("demo: the Yesterday against today tab stays empty:", error, flush=True)
    try:
        rich_reports(config, now)
    except Exception as error:   # noqa: BLE001
        print("demo: the Reports tab stays empty:", error, flush=True)
    try:
        snapshot, alerts, team = am.report_gather()
        report_service.run(config, am.report_account(), snapshot, alerts, team, now=stamp)
    except Exception as error:   # noqa: BLE001
        print("demo: the Scheduled reports tab stays empty:", error, flush=True)


def rich_yesterday(snap, now):
    """--rich, the tab Yesterday against today: a saved report of the day before (in a temporary folder that replaces the audit folder for this process only), with one red workflow that is green today and one
    repository that was not waiting for a signature, so that the tab shows something that appeared and something that disappeared."""
    from github_actions_monitor.data_pipeline import report_history
    folder = Path(tempfile.mkdtemp(prefix="ghamon_demo_audit_"))
    today = report_history.day_state(snap)
    before = {"day": (now - timedelta(days=1)).strftime("%Y-%m-%d"), "generated": snap.get("generated"), "red": sorted(set(today["red"][1:]) | {"demo-beta-docs (CI)"}), "pending_sign": sorted(set(today["pending_sign"]) - {"demo-beta-fw"}),
              "budget": [], "parte": []}
    (folder / f"{report_history.PREFIX}{before['day']}.json").write_text(json.dumps(before), encoding="utf-8")
    sl.AUDIT_DIR = folder


def rich_reports(config, now):
    """--rich, the tab Reports: the four optional reports switched on and filled with invented findings (nothing is read from GitHub)."""
    from github_actions_monitor.integrations import reports
    config["reports"] = {kind: {"enabled": True} for kind in reports.KINDS}
    stamp = int(now.timestamp())
    reports.reset()
    with reports.LOCK:
        reports.STATE["hygiene"]["demo-alpha-app"] = {"at": stamp, "files": 3, "findings": [{"rule": "no_timeout", "line": 12, "severity": "warn", "detail": "build"}, {"rule": "no_concurrency", "line": 1, "severity": "info", "detail": ""}]}
        reports.STATE["hygiene"]["demo-gamma-api"] = {"at": stamp, "files": 2, "findings": [{"rule": "no_timeout", "line": 9, "severity": "warn", "detail": "test"}]}
        for repo, tag, sbom, sums, sig in (("demo-alpha-app", "v2.3.0", True, True, True), ("demo-beta-fw", "v0.9.0", False, False, False), ("demo-gamma-api", "v1.3.0", False, True, False)):
            reports.STATE["supply"][repo] = {"at": stamp, "tag": tag, "sbom": sbom, "checksums": sums, "signature": sig}
        reports.STATE["queue"] = [{"group": group, "wait": wait} for group, waits in (("github-hosted", (4, 6, 9, 12, 20)), ("self-hosted", (35, 60, 180, 240))) for wait in waits]


def rich_setup(snap, now):
    """--rich: the history of the daily trend and the answer of the comparison of periods, both invented, and the comparison switched on."""
    days = [(now - timedelta(days=13 - i)).strftime("%Y-%m-%d") for i in range(14)]
    series = {"codeql": [5, 5, 4, 4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1], "dependabot": [9, 9, 8, 10, 10, 9, 7, 7, 6, 6, 5, 5, 4, 4], "secret": [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
              "prs": [3, 4, 4, 5, 3, 2, 3, 6, 5, 4, 3, 3, 2, 2], "red": [4, 3, 5, 2, 2, 3, 1, 2, 4, 3, 2, 2, 1, 3], "candidates": [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5]}
    n = None      # a day before the figure existed: a gap in the chart, never a zero
    series.update({"stuck": [1, 0, 2, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1], "ci_green_pct": [88.0, 91.5, 86.2, 94.0, 93.1, 90.4, 96.0, 95.2, 89.9, 92.3, 94.7, 95.1, 97.0, 91.0], "ci_repos_ok": [6, 7, 6, 8, 8, 7, 9, 8, 7, 8, 8, 9, 9, 8],
                   "issues_open": [2, 2, 3, 3, 2, 2, 1, 1, 2, 2, 1, 1, 1, 0], "prs_old": [1, 1, 2, 2, 2, 3, 3, 2, 2, 1, 1, 1, 0, 0], "unsigned": [0, 0, 1, 1, 1, 2, 2, 1, 1, 0, 0, 0, 1, 1],
                   "health": [72.0, 74.5, 73.0, 76.0, 78.5, 77.0, 80.0, 82.5, 81.0, 83.0, 84.5, 85.0, 86.5, 87.0], "ready": [1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4],
                   "quota_used_pct": [35.0, 42.0, 51.0, 47.0, 66.0, 83.0, 71.0, 58.0, 49.0, 44.0, 52.0, 61.0, 57.0, 54.0], "minutes24": [210, 180, 330, 290, 150, 400, 360, 240, 260, 310, 190, 220, 280, 300],
                   "sev_critical": [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], "sev_high": [3, 3, 4, 4, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1],
                   "sev_medium": [n, n, n, n, 6, 6, 5, 5, 5, 4, 4, 4, 3, 3], "sev_low": [n, n, n, n, 9, 9, 9, 8, 8, 8, 7, 7, 7, 6],
                   "dur_avg": [n, n, n, 4.2, 4.0, 4.6, 5.1, 4.4, 4.1, 4.0, 3.9, 4.3, 4.5, 4.2], "dur_p95": [n, n, n, 11.0, 10.2, 12.5, 14.0, 11.8, 10.9, 10.4, 10.1, 11.2, 12.0, 11.5],
                   "queue_avg": [n, n, n, 8.0, 7.5, 12.0, 15.5, 9.0, 8.5, 7.0, 6.5, 8.0, 9.5, 8.0], "flaky": [n, n, n, 1, 0, 2, 3, 1, 1, 0, 0, 1, 0, 1], "artifact_mb": [n, n, n, n, n, 120.5, 124.0, 131.2, 133.0, 140.4, 138.9, 142.0, 150.3, 151.0]})
    trend = {k: {"dates": days, "values": v} for k, v in series.items()}
    trend["min_repo"] = {"dates": days, "repos": {"demo-alpha-app": [n, n, n, 60, 55, 80, 90, 70, 65, 72, 60, 58, 77, 80], "demo-gamma-api": [n, n, n, 40, 35, 50, 45, 42, 38, 41, 39, 44, 46, 47], "demo-beta-docs": [n, n, n, 12, 10, 18, 16, 14, 13, 12, 11, 15, 16, 14]}}
    trend["releases"] = {days[3]: ["demo-alpha-app v1.4.0"], days[9]: ["demo-gamma-api v2.0.1", "demo-beta-docs v0.9.0"]}
    trend["thresholds"] = {"ci_green_pct": 90, "health": 70, "quota_used_pct": 80}
    trend["versions"] = [None] * 14
    snap["a3"]["trend"] = trend
    from github_actions_monitor.compare import compare_service
    cmp_answer = {"schema": compare_service.SCHEMA, "account": OWNER, "enabled": True, "state": "compared", "windows": None, "days": "all", "baseline": "previous", "coverage": 0.92,
                  "metrics": {"red_rate": {"state": "ok", "now": 0.12, "base": 0.21, "direction": "better"}, "duration_p50": {"state": "ok", "now": 196, "base": 171, "direction": "worse"},
                              "resolution": {"state": "ok", "now": 7200, "base": 14400, "direction": "better"}, "score_mean": {"state": "ok", "now": 82.5, "base": 80.0, "direction": "better"},
                              "score_coverage": {"state": "ok", "now": 0.92, "base": 0.92, "direction": "same"}},
                  "alerts": {"opened_now": 9, "open_at_end_now": 4},
                  "changes": {"worse": [{"repo": "demo-alpha-app", "red_rate_base": 0.1, "red_rate_now": 0.4}], "better": [{"repo": "demo-gamma-api", "red_rate_base": 0.5, "red_rate_now": 0.1}],
                              "new_failures": [{"repo": "demo-alpha-app", "workflow": "Release build", "failures": 3}], "resolved_failures": [{"repo": "demo-gamma-api", "workflow": "CI", "failures_before": 4}], "reason": ""},
                  "data_quality": {"runs_now": 212, "runs_base": 198, "min_runs": 20, "truncated": False, "reasons": []}}
    compare_service.build = lambda *a, **k: cmp_answer
    am.LIVE_CONFIG.setdefault("compare", {})["enabled"] = True


def main():
    lite = "--lite" in sys.argv
    rich = "--rich" in sys.argv      # the pictures of the newest tabs: findings for the Delivery and Supply chain sentinels, a daily trend and a comparison of periods
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    port = int(numbers[0]) if numbers else 18765
    now = datetime.now(timezone.utc).replace(microsecond=0)
    setup(now)
    am.LITE["on"] = lite       # the lite edition: no sentinel, no analytics, a short settings page
    data, runs, iso = build(now)
    snap = snapshot(now, data, runs, iso)
    if rich:
        rich_setup(snap, now)

    class Demo:
        ai_cfg = {"provider": "none"}

        def snapshot(self):
            return snap

        def refresh_repos(self, names):
            return names
    class DemoCollab:
        def snapshot(self):
            alerts = [a for a in demo_alerts(now, iso) if a["sentinel"] == "collab"]
            return {"enabled": True, "level": "bad", "status": {"enabled": True, "level": "bad", "repos_in_scope": 6, "repos_checked": 6, "refresh_seconds": 600, "errors": []}, "alerts": alerts}

    class DemoSecurity:
        def snapshot(self):
            return {"enabled": True, "level": "warn", "status": {"enabled": True, "level": "warn", "repos_in_scope": 6, "repos_checked": 6, "refresh_seconds": 600, "errors": []}, "alerts": []}

    class DemoRelease:
        """--rich: the Delivery and the Supply chain sentinels with invented findings (the plain demo leaves them with none, so no test that counts alerts moves)."""
        def __init__(self, items):
            self.items = items

        def snapshot(self):
            return {"enabled": True, "level": "warn", "status": {"enabled": True, "level": "warn", "lifecycle": "healthy", "repos_in_scope": 6, "repos_checked": 6, "refresh_seconds": 3600, "errors": []},
                    "alerts": [a for a in rich_alerts(now, iso) if a["code"].startswith(self.items)]}

    class DemoRegistry:
        def alerts(self):
            return demo_alerts(now, iso) + (rich_alerts(now, iso) if rich else [])

        def names(self):
            return ["ci", "collab", "security", "delivery", "supply"]

        def get(self, name):
            if rich and name in ("delivery", "supply", "security"):
                return DemoRelease({"delivery": "release.", "supply": "actions.supply.", "security": "security."}[name])
            return DemoCollab() if name == "collab" else (DemoSecurity() if name in ("security", "delivery", "supply") else None)
    if not lite:
        am.SENTINEL["registry"] = DemoRegistry()
        am.SENTINEL["obj"] = Demo()
        am.ANALYTICS["store"] = analytics.Store(Path(tempfile.mkdtemp()) / "a.json")
        am.ANALYTICS["summary"] = demo_analytics(runs)
    am.ETAG["cache"] = etagcache.EtagCache(Path(tempfile.mkdtemp()) / "e.json")
    am.update_info = lambda read=True: {"enabled": True, "newer": True, "latest": "9.9.9", "current": am.TOOL_VERSION, "url": "https://example.invalid/release", "changelog": "https://example.invalid/changelog", "airgapped": False, "checked_at": 0, "offline": False}   # an invented newer version, for the picture of the badge
    am.LIVE_CONFIG.update({"account": {"plan": "free"}, "session_guard": False})
    if rich and not lite:
        rich_tabs(am.LIVE_CONFIG, snap, now)
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
