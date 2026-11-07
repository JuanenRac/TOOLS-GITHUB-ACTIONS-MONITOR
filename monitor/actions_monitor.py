#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Live monitor of GitHub Actions for the repositories of one GitHub account ("github_owner" in actions_monitor.json; default: the account of `gh`).

Starts a small web server that only listens on this PC (127.0.0.1) and opens a page
with what is running right now (runs, jobs and steps), the history, charts, the
unresolved failures and the open build-failed / build-stuck issues. Nothing is written
to GitHub and no secret is read: it only asks the `gh` command line (already logged in)
for public run data.

  py -3 actions_monitor.py [--port 8765] [--no-browser] [--discover]

The repositories to watch, the refresh times and the "stuck" limit live in
actions_monitor.json next to this file (created on the first run):
  "repos": "all" or a list of names      "ecosystems": "all" or a list of ecosystem names of the ecosystems file (with "all" repos)
  "exclude": [names to skip]             "mode": "full" or "lite"
  "github_owner": the account to watch   "language": en | es | de | fr | it | ja | zh | pt (default: the system language)
Repositories with something running, a recent push or a failing last run are refreshed every
cycle ("hot"); the others only every cold_refresh_seconds with fewer runs, so ~130 repositories
do not use up the GitHub allowance shared with the agents.
"""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import i18n
import platform_compat
import toolconfig
from tool_version import AUTHOR, LICENSE_ID, TOOL_VERSION

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "actions_monitor.json"
LOG_FILE = HERE / "actions_monitor_log.txt"
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
DEFAULTS = {
    "repos": "all",
    "github_owner": "",     # "" = the account of `gh` (asked once at start)
    "language": "",         # "" = the language of the system; one of en es de fr it ja zh pt
    "ecosystems": "all",    # "all" or a list of the ecosystem names of the ecosystems file
    "exclude": [],
    "mode": "full",
    "refresh_seconds": 45,
    "cold_refresh_seconds": 600,
    "issues_refresh_seconds": 180,
    "discover_refresh_seconds": 3600,
    "stuck_minutes": 120,
    "runs_per_repo": 20,
    "cold_runs_per_repo": 5,
    "hot_hours": 3,
    "max_workers": 20,
    "min_rate_remaining": 800,
    "report_history_days": 30,   # (before 1.5.0: parte_history_days, still read)
    "sentinel": {"enabled": True},
    "ai": {"provider": "none"},
    "webhook": {"enabled": False, "secret": ""},   # optional signed webhook receiver on 127.0.0.1, see webhook.py (off by default)
}

RESTART_PENDING = set()   # settings changed from the page since this process started that only apply after a restart
STATE = {"data": None, "error": None, "hint": None}
SENTINEL = {"obj": None, "error": None}  # the sentinel module (layer A); a failure of it never stops the monitor
LOCK = threading.Lock()
ISSUE_CACHE = {"at": 0.0, "items": [], "busy": False}
RUN_CACHE = {}  # repo -> {"runs": [...], "at": float, "error": str|None}
DISCOVERED = {"at": 0.0, "names": []}
HOT_ONLY = {"on": False, "until": 0.0}   # "only hot" switch (memory only): cold repositories are not refreshed until `until` (one long cycle)
LIVE_CONFIG = {}                          # the config the loop runs with, for the HTTP handler
AUTOSAVE = None                           # report_history.AutoSaver, created in main()


def set_hot_only(on, config, now=None):
    """Turns the "only hot" mode on (for one long cycle: cold_refresh_seconds) or off. Returns the public state."""
    now = time.time() if now is None else now
    HOT_ONLY["on"] = bool(on)
    HOT_ONLY["until"] = now + config.get("cold_refresh_seconds", 600) if on else 0.0
    return hot_only_state(now)


def hot_only_state(now=None):
    now = time.time() if now is None else now
    if HOT_ONLY["on"] and now >= HOT_ONLY["until"]:
        HOT_ONLY["on"], HOT_ONLY["until"] = False, 0.0   # the long cycle has come: the cold repositories refresh again
    return {"on": HOT_ONLY["on"], "seconds_left": max(0, int(HOT_ONLY["until"] - now)) if HOT_ONLY["on"] else 0}


class AuthError(RuntimeError):
    pass


def load_config():
    config = dict(DEFAULTS)
    try:
        config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except FileNotFoundError:
        example = HERE / "actions_monitor.example.json"   # the template that travels with the package; the defaults are only the fallback
        try:
            if example.is_file():
                CONFIG_FILE.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
                config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
            else:
                CONFIG_FILE.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
        except (OSError, ValueError):
            pass
    except (OSError, ValueError) as error:
        print(i18n.t("mon.config_unreadable", error=error))
    return config


def gh(*args, timeout=40, retries=2):
    """Runs `gh` with a fixed argument list (no shell). Retries slow or flaky answers, not auth errors."""
    last = ""
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        except subprocess.TimeoutExpired:
            last = "timeout"
            time.sleep(2 * (attempt + 1))
            continue
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout.strip() else None
        last = (result.stderr or result.stdout).strip()[:300]
        if "401" in last or "Bad credentials" in last or ("403" in last and "rate limit" not in last.lower()):
            raise AuthError(last)
        if "404" in last:
            break  # a repository without Actions: retrying does not help
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(last or "gh failed")


def parse_time(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if text else None


def seconds_between(start, end):
    if not start:
        return 0
    end = end or datetime.now(timezone.utc)
    return max(0, int((end - start).total_seconds()))


def ecosystem_of(name):
    return toolconfig.ecosystem_of(name)


def watched_repos(config, force=False):
    """The list from the config file or, with "repos": "all", the repositories of the account (one call, cached)."""
    wanted = config["repos"]
    if wanted != "all":
        names = list(wanted)
    else:
        if force or time.time() - DISCOVERED["at"] > config["discover_refresh_seconds"] or not DISCOVERED["names"]:
            data = gh("repo", "list", toolconfig.github_owner(config), "--limit", "400", "--no-archived", "--json", "name") or []
            DISCOVERED["names"] = sorted(item["name"] for item in data)
            DISCOVERED["at"] = time.time()
        known = toolconfig.ecosystem_names(config)
        wanted_eco = config["ecosystems"]
        allowed = set(known if wanted_eco in ("all", None) else wanted_eco)
        names = [n for n in DISCOVERED["names"] if not known or ecosystem_of(n) in allowed or n == toolconfig.github_owner(config)]   # no ecosystems file: every repository
    skip = set(config["exclude"])
    valid = [n for n in names if NAME_RE.match(n) and n not in skip]
    for n in names:
        if not NAME_RE.match(n):
            print(i18n.t("mon.bad_repo_name", name=repr(n)[:60]))
    return valid


def fetch_runs(repo, per_page):
    try:
        data = gh("api", f"repos/{toolconfig.github_owner()}/{repo}/actions/runs?per_page={per_page}")
    except AuthError:
        raise
    except Exception as error:  # a repo without Actions or a network problem must not stop the page
        return [], str(error)
    runs = []
    for run in data.get("workflow_runs", []):
        started = parse_time(run.get("run_started_at") or run.get("created_at"))
        updated = parse_time(run.get("updated_at"))
        finished = run.get("status") == "completed"
        runs.append({
            "repo": repo, "id": run["id"], "name": run.get("name") or "", "title": (run.get("display_title") or "")[:90],
            "event": run.get("event"), "branch": run.get("head_branch"), "path": (run.get("path") or "").split("@")[0].rsplit("/", 1)[-1], "sha": (run.get("head_sha") or "")[:7],
            "actor": (run.get("actor") or {}).get("login", ""), "status": run.get("status"),
            "conclusion": run.get("conclusion"), "started": run.get("run_started_at") or run.get("created_at"),
            "seconds": seconds_between(started, updated if finished else None), "url": run.get("html_url"),
        })
    return runs, None


def is_hot(repo, config, now):
    entry = RUN_CACHE.get(repo)
    if entry is None:
        return True
    runs = entry["runs"]
    if any(r["status"] != "completed" for r in runs):
        return True
    if runs:
        latest = max(runs, key=lambda r: r["started"] or "")
        if latest["conclusion"] in ("failure", "timed_out", "startup_failure"):
            return True
        started = parse_time(latest["started"])
        if started and (datetime.now(timezone.utc) - started).total_seconds() < config["hot_hours"] * 3600:
            return True
    return False


def refresh_runs(repos, config, progress=None):
    """Hot repositories every cycle with the full run list, cold ones only now and then with a short list."""
    now = time.time()
    lite = config["mode"] == "lite"
    only_hot = hot_only_state(now)["on"]
    todo = []
    for repo in repos:
        entry = RUN_CACHE.get(repo)
        hot = is_hot(repo, config, now)
        if entry is None:
            todo.append((repo, config["cold_runs_per_repo"]))  # first look: a short list; the hot ones get the full list next cycle
        elif hot:
            todo.append((repo, config["cold_runs_per_repo"] if lite else config["runs_per_repo"]))
        elif not only_hot and now - entry["at"] > config["cold_refresh_seconds"]:
            todo.append((repo, config["cold_runs_per_repo"]))
    done = 0
    for start in range(0, len(todo), 40):  # chunks, so the page can show the first results while the rest loads
        chunk = todo[start:start + 40]
        with ThreadPoolExecutor(max_workers=config["max_workers"]) as pool:
            results = list(pool.map(lambda item: (item[0], *fetch_runs(*item)), chunk))
        for repo, runs, error in results:
            if error and RUN_CACHE.get(repo):
                RUN_CACHE[repo]["error"] = error  # keep the old runs, report the problem
            else:
                RUN_CACHE[repo] = {"runs": runs, "at": time.time(), "error": error}
        done += len(chunk)
        if progress:
            progress(done, len(todo))
    return len(todo)


def run_jobs(repo, run_id):
    try:
        data = gh("api", f"repos/{toolconfig.github_owner()}/{repo}/actions/runs/{run_id}/jobs?per_page=30", retries=1)
    except Exception:
        return []
    jobs = []
    for job in data.get("jobs", []):
        steps = job.get("steps") or []
        done = sum(1 for step in steps if step.get("status") == "completed")
        current = next((step.get("name") for step in steps if step.get("status") == "in_progress"), "")
        started = parse_time(job.get("started_at"))
        finished = parse_time(job.get("completed_at"))
        jobs.append({
            "name": job.get("name"), "status": job.get("status"), "conclusion": job.get("conclusion"),
            "steps_total": len(steps), "steps_done": done, "step": current, "runner": job.get("runner_name") or "",
            "seconds": seconds_between(started, finished) if started else 0, "url": job.get("html_url"),
        })
    return jobs


def repo_issues(repo):
    try:
        data = gh("api", f"repos/{toolconfig.github_owner()}/{repo}/issues?state=open&per_page=50", retries=1) or []
    except AuthError:
        raise
    except Exception:
        return []
    items = []
    for issue in data:
        labels = [label["name"] for label in issue.get("labels", [])]
        if "pull_request" not in issue and ("build-failed" in labels or "build-stuck" in labels):
            items.append({"repo": repo, "number": issue["number"], "title": issue["title"], "created": issue["created_at"],
                          "labels": labels, "url": issue["html_url"]})
    return items


def open_issues(repos, workers):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [item for part in pool.map(repo_issues, repos) for item in part]


def unresolved_failures(runs):
    """A failed run counts as unresolved while no later run of the same workflow in the same repository has succeeded."""
    latest = {}
    for run in sorted(runs, key=lambda r: r["started"] or ""):
        if run["status"] == "completed":
            latest[(run["repo"], run["name"])] = run
    return [r for r in latest.values() if r["conclusion"] in ("failure", "timed_out", "startup_failure")]


def collect(config, publish=None):
    repos = watched_repos(config)
    started = time.time()

    def partial(done, total):
        if publish and not STATE.get("complete"):  # only until the first complete picture exists
            publish(build(config, repos, started, done, True, f"{done}/{total}"))

    refreshed = refresh_runs(repos, config, partial)
    return build(config, repos, started, refreshed, False, "")


def build(config, repos, started, refreshed, loading, progress_text):
    runs, errors = [], {}
    for repo in repos:
        entry = RUN_CACHE.get(repo)
        if not entry:
            continue
        runs.extend(entry["runs"])
        if entry.get("error"):
            errors[repo] = entry["error"]
    runs.sort(key=lambda run: run["started"] or "", reverse=True)
    # Runs with event "dynamic" are the internal jobs of Dependabot ("Configured Graph Update"): GitHub leaves them "queued" for ever although the work is done
    # (the owner cannot cancel them and they finish by themselves), so they are not builds that can be stuck.
    active = [run for run in runs if run["status"] in ("in_progress", "queued", "waiting", "requested", "pending") and run.get("event") != "dynamic"]
    for run in active:
        run["jobs"] = run_jobs(run["repo"], run["id"]) if (run["status"] == "in_progress" and not loading) else []
        run["stuck"] = run["seconds"] > config["stuck_minutes"] * 60
    if not loading and time.time() - ISSUE_CACHE["at"] > config["issues_refresh_seconds"] and not ISSUE_CACHE["busy"]:
        ISSUE_CACHE["busy"] = True  # the issues load in the background so the first page does not wait for them

        def refresh_issues():
            try:
                ISSUE_CACHE["items"] = open_issues(repos, config["max_workers"])
                ISSUE_CACHE["at"] = time.time()
            except Exception:
                ISSUE_CACHE["at"] = time.time() - config["issues_refresh_seconds"] + 60
            finally:
                ISSUE_CACHE["busy"] = False

        threading.Thread(target=refresh_issues, daemon=True).start()
    try:
        if loading:
            raise RuntimeError("skip")
        limit = gh("api", "rate_limit", retries=0)["resources"]["core"]
        rate = {"remaining": limit["remaining"], "limit": limit["limit"], "reset": datetime.fromtimestamp(limit["reset"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    except Exception:
        rate = None
    hot = sum(1 for repo in repos if is_hot(repo, config, time.time()))
    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "took": round(time.time() - started, 1),
        "repos": repos, "ecosystems": {repo: ecosystem_of(repo) for repo in repos},
        "runs": runs[:600], "active": active, "issues": ISSUE_CACHE["items"], "failing": unresolved_failures(runs),
        "errors": errors, "rate": rate, "stuck_minutes": config["stuck_minutes"],
        "mode": config["mode"], "refreshed": refreshed, "hot": hot, "loading": progress_text if loading else "",
        "min_rate": config["min_rate_remaining"], "paused_quota": bool(rate and rate["remaining"] < config["min_rate_remaining"]),
        "refresh_seconds": config["refresh_seconds"], "hot_only": hot_only_state(),
    }


def loop(config):
    while True:
        try:
            def publish(snapshot):
                with LOCK:
                    STATE["data"], STATE["error"], STATE["hint"] = snapshot, None, None
                print(i18n.t("mon.loaded", n=snapshot["loading"]), flush=True)

            data = collect(config, publish)
            with LOCK:
                STATE["data"], STATE["error"], STATE["hint"] = data, None, None
                STATE["complete"] = True
            with LOG_FILE.open("a", encoding="utf-8") as log:  # counts only, never titles
                log.write(f"{data['updated']} repos={len(data['repos'])} hot={data['hot']} refreshed={data['refreshed']} active={len(data['active'])} issues={len(data['issues'])} rate={data['rate']}\n")
            delay = config["refresh_seconds"]
            try:   # the report of the day goes to the audit folder (never stops the loop)
                if SENTINEL["obj"] is not None and AUTOSAVE is not None and not data.get("loading"):
                    import sentinel_local
                    AUTOSAVE.maybe(sentinel_local.AUDIT_DIR, SENTINEL["obj"].snapshot(), config.get("report_history_days", config.get("parte_history_days", 30)))
            except Exception:
                pass
            if data["rate"] and data["rate"]["remaining"] < config["min_rate_remaining"]:
                delay = max(delay, 180)  # leave the GitHub allowance to the agents and the owner
        except AuthError as error:
            with LOCK:
                STATE["error"], STATE["hint"] = str(error), "auth"   # the page writes the hint in its own language
            delay = 60
        except Exception as error:
            with LOCK:
                STATE["error"] = str(error)
            delay = 60
        time.sleep(delay)


def render_page():
    """actions_monitor.html with the catalogues of the interface (keys "ui.*") for the 8 languages and the default language inlined."""
    page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
    data = {"default": i18n.language(), "langs": list(i18n.LANGS), "names": i18n.NATIVE_NAMES, "html": i18n.HTML_LANG, "locale": i18n.BROWSER_LOCALE, "catalogues": i18n.ui_catalogues(),
            "ecosystems": {key: item["label"] for key, item in toolconfig.ecosystems().items()}, "owner": toolconfig.github_owner(), "version": TOOL_VERSION, "author": AUTHOR, "license": LICENSE_ID}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return page.replace("/*I18N_DATA*/null", blob, 1)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, body, kind):
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def json_reply(self, payload, code=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        try:
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass   # the browser or a reader closed the tab mid-answer: nothing to report

    def guard(self):
        import sentinel_local
        if sentinel_local.local_request_ok(self.headers, self.server.server_address[1]):
            return True
        self.json_reply({"error": "forbidden"}, 403)
        return False

    def request_language(self):
        """The language asked for with ?lang=xx (the page and read_report.py send it), else None = the configured one."""
        from urllib.parse import parse_qs
        found = parse_qs(self.path.partition("?")[2]).get("lang")
        return found[0] if found else None

    def do_POST(self):
        with i18n.use_language(self.request_language()):
            self.handle_post()

    def handle_post(self):
        path = self.path.split("?")[0]
        if path == "/api/hot-only":   # "only hot" switch: local request only, tiny body {"on": true|false}
            if not self.guard():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 256 else b"{}")
                if not isinstance(request, dict) or not isinstance(request.get("on"), bool):
                    self.json_reply({"ok": False, "error": "bad request"}, 400)
                    return
                self.json_reply({"ok": True, "hot_only": set_hot_only(request["on"], LIVE_CONFIG or DEFAULTS)})
            except Exception as error:
                self.json_reply({"ok": False, "error": str(error)[:200]}, 400)
            return
        if path == "/api/webhook":   # off unless configured; no Host check (a tunnel changes it), but every request must carry a valid HMAC
            import webhook
            try:
                size = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(size) if 0 <= size <= webhook.MAX_BODY else b"x" * (webhook.MAX_BODY + 1)
                code, answer, repo = webhook.handle(LIVE_CONFIG or DEFAULTS, body, self.headers, STATE["data"]["repos"] if STATE.get("data") else [])
                if repo and repo in RUN_CACHE:
                    RUN_CACHE[repo]["at"] = 0   # refreshed in the next cycle
                self.json_reply(answer, code)
            except Exception:
                self.json_reply({"ok": False}, 400)
            return
        if path == "/api/settings":   # the settings menu: whitelisted keys only, checked, backed up and written atomically (settings_api.py); local request only
            if not self.guard():
                return
            import settings_api
            try:
                if "application/json" not in (self.headers.get("Content-Type") or "").lower():
                    self.json_reply({"ok": False, "errors": {"_": "content-type"}}, 415)
                    return
                size = int(self.headers.get("Content-Length") or 0)
                if size <= 0 or size > settings_api.MAX_BODY:
                    self.json_reply({"ok": False, "errors": {"_": "size"}}, 413)
                    return
                request = json.loads(self.rfile.read(size))
                changes = request.get("changes") if isinstance(request, dict) else None
                result = settings_api.apply(changes, CONFIG_FILE)
                if result.get("ok"):
                    RESTART_PENDING.update(result.get("restart") or [])
                    result["restart_pending"] = sorted(RESTART_PENDING)
                self.json_reply(result, 200 if result.get("ok") else 400)
            except (ValueError, OSError) as error:
                self.json_reply({"ok": False, "errors": {"_": "request"}}, 400)
            return
        if path == "/api/refresh-repos":   # from `finalize --execute`: refresh just these repositories and rewrite ci_red.json (local request only)
            if not self.guard():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 4096 else b"{}")
                names = [n for n in (request.get("repos") if isinstance(request, dict) else None) or [] if isinstance(n, str) and NAME_RE.match(n)][:50]
                for name in names:
                    if name in RUN_CACHE:
                        RUN_CACHE[name]["at"] = 0
                done = SENTINEL["obj"].refresh_repos(names) if SENTINEL["obj"] is not None else []
                self.json_reply({"ok": True, "repos": done})
            except Exception as error:
                self.json_reply({"ok": False, "error": str(error)[:200]}, 400)
            return
        if path != "/api/sentinel/ai" or not self.guard():
            if path != "/api/sentinel/ai":
                self.send_response(404)
                self.end_headers()
            return
        sentinel = SENTINEL["obj"]
        if sentinel is not None and getattr(sentinel, "ai_cfg", {}).get("provider") == "none":   # AI off: this endpoint does not exist
            self.send_response(404)
            self.end_headers()
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            if size > 4096 or size < 0:   # a request for the explainer is a few hundred bytes: refuse anything big instead of cutting it
                self.json_reply({"ok": False, "error": "request too large"}, 413)
                return
            request = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(request, dict):
                self.json_reply({"ok": False, "error": "bad request"}, 400)
                return
            self.json_reply(sentinel.ai_explain(request) if sentinel else {"ok": False, "error": i18n.t("mon.sentinel_unavailable")})
        except Exception as error:
            self.json_reply({"ok": False, "error": str(error)[:200]})

    def do_GET(self):
        with i18n.use_language(self.request_language()):
            self.handle_get()

    def handle_get(self):
        path = self.path.split("?")[0]
        if path == "/api/sentinel/parte.txt":   # the same text as the daily report, to copy or download
            if not self.guard():
                return
            sentinel = SENTINEL["obj"]
            import report_history
            markdown = "fmt=md" in self.path.partition("?")[2].split("&")
            try:
                snap = sentinel.snapshot() if sentinel else None
                body = (report_history.parte_markdown(snap) if markdown else report_history.parte_text(snap)).encode("utf-8")
            except Exception as error:
                body = (i18n.t("mon.sentinel_failed", error=error) + chr(10)).encode("utf-8")
            if "save=1" in self.path:   # optional copy in the audit folder; never fails the answer
                try:
                    import sentinel_local
                    folder = sentinel_local.AUDIT_DIR
                    if folder.is_dir():
                        (folder / ("SENTINEL_REPORT_" + time.strftime("%Y-%m-%d_%H%M") + ".txt")).write_bytes(body)
                except OSError:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", ("text/markdown" if markdown else "text/plain") + "; charset=utf-8")
            self.send_header("Content-Disposition", "inline; filename=parte_centinela." + ("md" if markdown else "txt"))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            try:
                self.end_headers()
                self.wfile.write(body)
            except (ConnectionError, OSError):
                pass
            return
        if path == "/api/sentinel/historial":   # yesterday vs today: reds and pending signatures that appear or disappear
            if not self.guard():
                return
            try:
                import report_history
                import sentinel_local
                sentinel = SENTINEL["obj"]
                self.json_reply({"data": report_history.yesterday_vs_today(sentinel_local.AUDIT_DIR, sentinel.snapshot()) if sentinel else None, "error": None if sentinel else i18n.t("mon.sentinel_unavailable")})
            except Exception as error:
                self.json_reply({"data": None, "error": i18n.t("mon.history_failed", error=error)})
            return
        if path == "/api/sentinel":
            if not self.guard():
                return
            sentinel = SENTINEL["obj"]
            try:
                snapshot = sentinel.snapshot() if sentinel else None
                self.json_reply({"data": snapshot, "error": SENTINEL["error"] or (None if sentinel else i18n.t("mon.sentinel_not_loaded"))})
            except Exception as error:  # shown as a red notice in the tab
                self.json_reply({"data": None, "error": i18n.t("mon.sentinel_failed", error=error)})
        elif path == "/api/settings":
            if not self.guard():
                return
            import settings_api
            self.json_reply({"ok": True, **settings_api.describe(CONFIG_FILE), "restart_pending": sorted(RESTART_PENDING)})
        elif path == "/metrics" or path.startswith("/api/outputs/"):   # optional outputs, off unless switched on (outputs.py); local request only, no quota used
            if not self.guard():
                return
            import outputs
            import settings_api
            cfg = toolconfig.raw_config()
            sentinel = SENTINEL["obj"]
            try:
                snapshot = sentinel.snapshot() if sentinel else None
            except Exception:
                snapshot = None
            with LOCK:
                data = STATE["data"]
            if path == "/metrics" and settings_api.output_enabled(cfg, "prometheus"):
                self.reply(outputs.metrics_text(snapshot, data, per_repo=settings_api.output_enabled(cfg, "prometheus", "per_repo")), outputs.CONTENT_TYPE)
            elif path == "/api/outputs/grafana.json" and settings_api.output_enabled(cfg, "json"):
                self.json_reply(outputs.grafana_json(snapshot, data))
            elif path == "/api/outputs/dashboard.json" and settings_api.output_enabled(cfg, "dashboard"):
                document = outputs.dashboard_json(snapshot)
                if document is None:
                    self.json_reply({"error": "not ready"}, 503)
                else:
                    self.json_reply(document)
            else:
                self.send_response(404)
                self.end_headers()
        elif path.startswith("/api/data"):
            if not self.guard():
                return
            with LOCK:
                self.reply(json.dumps({"data": STATE["data"], "error": STATE["error"], "hint": STATE["hint"]}), "application/json; charset=utf-8")
        elif path in ("/", "/index.html"):
            self.reply(render_page(), "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()


def start_sentinel(config):
    """Layer A of the Centinela in its own thread and cache; if the module fails, the monitor goes on and the tab shows a red notice."""
    try:
        import sentinel_local

        def repos_fn():
            data = STATE["data"]
            if data and data.get("repos"):
                return data["repos"]
            try:
                return watched_repos(config)
            except Exception:
                return []

        ctx = {"gh": gh, "repos_fn": repos_fn, "runs_fn": lambda: RUN_CACHE, "data_fn": lambda: STATE["data"], "eco_fn": ecosystem_of}
        import workspace
        if not workspace.has_workspace():   # optional: without the local clones the sentinel runs in reduced mode (GitHub API data only)
            print(i18n.t("mon.reduced_mode"))
        SENTINEL["obj"] = sentinel_local.Sentinel(ctx, config)
        SENTINEL["obj"].start()
    except Exception as error:
        SENTINEL["error"] = i18n.t("mon.sentinel_start_failed", error=error)
        print(SENTINEL["error"])


def main():
    config = load_config()
    i18n.set_language(i18n.detect(config.get("language")))
    i18n.cli_language() if "--lang" in " ".join(sys.argv) else None
    parser = argparse.ArgumentParser(description=i18n.t("mon.description"), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765, help=i18n.t("mon.help_port"))
    parser.add_argument("--no-browser", action="store_true", help=i18n.t("mon.help_no_browser"))
    parser.add_argument("--discover", action="store_true", help=i18n.t("mon.help_discover"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    parser.add_argument("--init-catalog", action="store_true", help=i18n.t("mon.help_init_catalog"))
    args = parser.parse_args()
    platform_compat.console_utf8()
    if args.init_catalog:
        for name, created in toolconfig.init_catalog():
            print(i18n.t("mon.catalog_created" if created else "mon.catalog_kept", name=name))
        return 0
    if not platform_compat.gh_available():
        print(platform_compat.gh_install_hint())
        return 1
    try:
        me = gh("api", "user", retries=0)
        toolconfig.prime_owner((me or {}).get("login"))   # the owner to watch when "github_owner" is empty, from the call that checks the login: no extra call
    except AuthError:
        print(i18n.t("mon.auth_rejected"))
        return 1
    except Exception as error:
        print(i18n.t("mon.gh_not_ready", error=error))
        return 1
    if not toolconfig.github_owner(config):
        print(i18n.t("mon.no_owner"))
        return 1
    if args.discover:
        names = watched_repos(config, force=True)
        saved = dict(config)
        saved["repos"] = names
        CONFIG_FILE.write_text(json.dumps(saved, indent=2), encoding="utf-8")
        print(i18n.t("mon.discovered", n=len(names), file=CONFIG_FILE.name))
        return 0
    using_example = toolconfig.catalog_in_example(config)
    if using_example:
        print(i18n.t("mon.catalog_example", names=", ".join(using_example)))
    global AUTOSAVE
    LIVE_CONFIG.update(config)
    import report_history
    AUTOSAVE = report_history.AutoSaver()
    threading.Thread(target=loop, args=(config,), daemon=True).start()
    start_sentinel(config)
    server = None
    for port in range(args.port, args.port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            if port != args.port:
                print(i18n.t("mon.port_busy", port=args.port, used=port))
            break
        except OSError:
            continue
    if server is None:
        print(i18n.t("mon.no_port", port=args.port))
        return 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if config.get("webhook", {}).get("enabled") is True:
        import webhook
        print(i18n.t("mon.webhook", status=webhook.status_text(config)))
    print(i18n.t("mon.version", version=TOOL_VERSION))
    print(i18n.about_line())
    print(i18n.t("mon.started", url=url))
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
