#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor under limits: an account of 120 workflows (invented runs, nothing read from GitHub) is loaded into the real server, which then answers the main routes many times while its own memory and
threads are read. The CI runs this in a container with ONE processor and 512 MB (`docker run --cpus 1 --memory 512m`), so a monitor that would be killed by a small container, or that hangs on a single
core, fails the job instead of a user's night.

    python tools/limits_check.py [--repos 120] [--requests 60] [--max-rss-mb 400]

Fails (exit 1) when a route does not answer 200 within 20 s, when the resident memory goes above --max-rss-mb or when the number of threads keeps growing from one round to the next."""
import argparse
import json
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "monitor"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

ROUTES = ("/api/health", "/api/data", "/api/alerts", "/")


def build(repos, now):
    """The data of an account with `repos` repositories of one workflow each, eight runs apiece."""
    from github_actions_monitor.app import actions_monitor as am
    from test_sentinel import run as make_run
    names = [f"limit-repo-{n:03d}" for n in range(repos)]
    iso = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    runs, rid = [], 1000
    for index, repo in enumerate(names):
        for i in range(8):
            rid += 1
            outcome = "failure" if (index + i) % 11 == 0 else "success"
            row = make_run(repo, "CI", outcome, iso(now - timedelta(hours=2 + 3 * i)), rid=rid, path="ci.yml")
            row.update({"sha": f"{rid:07x}", "url": f"https://github.com/limits/{repo}/actions/runs/{rid}", "title": f"change {rid}", "event": "push", "actor": "user", "seconds": 60 + i})
            runs.append(row)
    runs.sort(key=lambda r: r["started"], reverse=True)
    data = {"updated": iso(now), "took": 1.0, "repos": names, "ecosystems": {r: "" for r in names}, "runs": runs, "active": [], "issues": [], "failing": am.unresolved_failures(runs), "errors": {},
            "rate": {"remaining": 4000, "limit": 5000, "reset": iso(now + timedelta(minutes=30))}, "stuck_minutes": 120, "mode": "full", "refreshed": 3, "hot": 4, "loading": "", "min_rate": 1500,
            "paused_quota": False, "refresh_seconds": 120, "hot_only": {"on": False, "seconds_left": 0}, "offline": {"offline": False, "since": None, "last_ok": iso(now)},
            "etag": {"enabled": True, "entries": 0, "saved": 0, "calls": 0}, "repo_meta": {r: {"private": False, "branch": "main", "pushed": iso(now), "prs": 0} for r in names}}
    for run in runs:
        am.RUN_CACHE.setdefault(run["repo"], {"runs": [], "at": time.time(), "error": None})["runs"].append(run)
    am.STATE.update({"data": data, "error": None, "hint": None, "complete": True})
    return names


def run(repos=120, requests=60, max_rss_mb=400):
    from github_actions_monitor.app import actions_monitor as am
    from github_actions_monitor.app import selfwatch, toolconfig
    tmp = Path(tempfile.mkdtemp(prefix="ghamon_limits_"))
    cfg = json.loads((ROOT / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
    (tmp / "actions_monitor.json").write_text(json.dumps(cfg), encoding="utf-8")
    am.CONFIG_FILE = toolconfig.CONFIG_FILE = tmp / "actions_monitor.json"
    am.LIVE_CONFIG.update(cfg)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    names = build(repos, now)
    server = am.QuietServer(("127.0.0.1", 0), am.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    problems, threads, peak = [], [], 0.0
    previous = None
    for round_ in range(max(2, requests // len(ROUTES))):
        for route in ROUTES:
            began = time.time()
            try:
                with urllib.request.urlopen(base + route, timeout=20) as answer:
                    answer.read()
                    if answer.status != 200:
                        problems.append(f"{route} answered {answer.status}")
            except OSError as error:
                problems.append(f"{route} did not answer: {error}")
            if time.time() - began > 20:
                problems.append(f"{route} took more than 20 s")
        sampled = selfwatch.sample(previous)
        previous = sampled
        threads.append(sampled["threads"])
        if sampled["rss_mb"] is not None:
            peak = max(peak, sampled["rss_mb"])
    server.shutdown()
    server.server_close()
    if peak > max_rss_mb:
        problems.append(f"memory {peak} MB is above {max_rss_mb} MB")
    if len(threads) >= 4 and all(b > a for a, b in zip(threads[-4:], threads[-3:])):
        problems.append(f"the threads keep growing: {threads[-4:]}")
    return {"repos": len(names), "rounds": len(threads), "peak_rss_mb": peak, "threads": threads, "problems": problems}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repos", type=int, default=120)
    ap.add_argument("--requests", type=int, default=60)
    ap.add_argument("--max-rss-mb", type=float, default=400)
    args = ap.parse_args(argv)
    report = run(args.repos, args.requests, args.max_rss_mb)
    print(json.dumps(report, indent=1))
    print("LIMITS=" + ("FAIL" if report["problems"] else "PASS"))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
