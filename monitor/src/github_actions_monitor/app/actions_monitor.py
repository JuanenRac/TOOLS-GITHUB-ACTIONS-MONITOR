#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Live monitor of GitHub Actions for the repositories of one GitHub account ("github_owner" in actions_monitor.json; default: the account of `gh`).

Starts a small web server that only listens on this PC (127.0.0.1) and opens a page
with what is running right now (runs, jobs and steps), the history, charts, the
unresolved failures and the open build-failed / build-stuck issues. Nothing is written
to GitHub and no secret is read: it only asks the `gh` command line (already logged in)
for public run data.

  py -3 bin/actions_monitor.py [--port 8765] [--no-browser] [--discover]

The repositories to watch, the refresh times and the "stuck" limit live in
actions_monitor.json next to this file (created on the first run):
  "repos": "all" or a list of names      "ecosystems": "all" or a list of ecosystem names of the ecosystems file (with "all" repos)
  "exclude": [names to skip]             "mode": "full" or "lite"
  "github_owner": the account to watch   "language": en | es | de | fr | it | ja | zh | pt (default: the system language)
Repositories with something running, a recent push or a failing last run are refreshed every
cycle ("hot"); the others only every cold_refresh_seconds with fewer runs, so ~130 repositories
do not use up the GitHub allowance shared with the agents.
"""
from github_actions_monitor.app import degraded
from github_actions_monitor.app import cycle_watch
import argparse
import json
import os
import random
import re
import signal
import ssl
import subprocess
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from github_actions_monitor.data_pipeline import analytics
from github_actions_monitor.data_pipeline import discovery
from github_actions_monitor.data_pipeline import etagcache
from github_actions_monitor.data_pipeline import graphql_checks
from github_actions_monitor import i18n
from github_actions_monitor.security import auth_http
from github_actions_monitor.security import localguard
from github_actions_monitor.app import modes
from github_actions_monitor.util import platform_compat
from github_actions_monitor.data_pipeline import redrule
from github_actions_monitor.util import resilience
from github_actions_monitor.security import secretstore
from github_actions_monitor.security import credential
from github_actions_monitor.app import toolconfig
from github_actions_monitor.util import tzdisplay
from github_actions_monitor.app import updatecheck
from github_actions_monitor.tool_version import AUTHOR, LICENSE_ID, TOOL_VERSION
from github_actions_monitor.security import private_io

from github_actions_monitor.util import paths, rootmigrate
from github_actions_monitor.util.paths import ROOT as HERE   # the product folder: the data of the person who runs the monitor stays there
CONFIG_FILE = paths.config_file()
LOG_FILE = paths.place("actions_monitor_log.txt")
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
    "discover_limit": 1000,        # the most repositories listed for the account
    "show_unclassified": True,     # repositories that no ecosystem claims are shown in an automatic group "Unclassified" instead of disappearing
    "stuck_minutes": 120,
    "watchdog_minutes": 10,      # a refresh cycle that runs longer than this is dumped to the log and restarted in a new thread (0 = off)
    "runs_per_repo": 20,
    "cold_runs_per_repo": 5,
    "hot_hours": 3,
    "max_workers": 20,
    "min_rate_remaining": 800,
    "report_history_days": 30,   # (before 1.5.0: parte_history_days, still read)
    "sentinel": {"enabled": True},
    "ai": {"provider": "none"},
    "webhook": {"enabled": False, "secret": "", "replay_seconds": 3600, "max_per_minute": 30},   # optional signed webhook receiver on 127.0.0.1, see webhook.py (off by default)
    "cache": {"etag": {"enabled": True, "ttl_hours": 24}},   # conditional reads: a 304 answer costs no quota (etagcache.py)
    "display": {"timezone": "local", "blink_red_tiles": True},   # blink_red_tiles: the red tiles and red items of the bar blink softly until the cause is solved; zone of the times written for people (log, reports, command line, notifications): local | utc | an IANA name such as Europe/Madrid
    "modes": {"auto_low": True, "auto_low_enter": 1000, "auto_low_exit": 2500, "low": {"refresh_seconds": 240, "cold_refresh_seconds": 1800, "runs_per_repo": 10, "hot_hours": 2}},      # see modes.py: only what is shown in the Quota tab
    "extra_reader": {"enabled": False, "file": "", "any_folder": False},      # a second read-only account: only the PATH of the file with its token (readpool.py)
    "github_app": {"enabled": False, "app_id": "", "key_path": "", "installation_id": ""},      # an optional GitHub App for the READS (its own allowance); only the PATH of the key is kept here (github_app.py)
    "central": {"source": "off", "max_age_minutes": 120, "git_dir": ""},      # the central panel of the profile repository as a base line that spends no allowance (central_source.py): off | git | http
    "sound": {"enabled": True, "on_new_red": True, "on_connection_lost": True, "cooldown_seconds": 30, "volume": 40, "server_beep": False},   # the "bing bing" of the page (soundalert.py: server_beep is the one for when the page is closed, off)
    "updates": {"check": True},    # tell when a newer version is published (read only, updatecheck.py); never installs anything
    "airgapped": False,            # True: nothing is requested from the network except GitHub's data you asked for; the update check is off
    "open_browser": True,
    "modes": {"start": "normal", "default_minutes": 60},     # normal | fast | turbo: see modes.py; the presets can be edited under modes.fast / modes.turbo
    "account": {"plan": "unknown"},     # free | pro | team | enterprise: the quotas of the plan come from quotas.json (quota.py)
    "quota": {"billing_api": False, "warn_percent": 75, "alert_percent": 90, "default_runner": "linux"},
    "session_guard": True,         # the page asks for a one-use token before it changes a setting or confirms an action
    "discovery": {"events": True, "suggest_groups": True, "auto_frequency": False, "hide": []},
    "auth": {"enabled": False, "session_hours": 12, "max_failed_logins": 5, "lockout_minutes": 15, "min_length": 10, "allow_bearer": False, "audit": True},     # OFF: one person, no login. On: users with roles once the first administrator exists (security/auth.py)
    "listen": {"network": False, "trusted_proxy": False, "local_port": 0, "host": "127.0.0.1", "token_env": "MONITOR_ACCESS_TOKEN", "allowed_hosts": [], "tls_cert_file": "", "tls_key_file": "", "secure_cookie": False, "proxy_public_host": "", "max_failed_attempts": 10, "query_access": True},     # OFF: only this computer. On: a private address, with an access token for every request
    "github_token": {"enabled": False, "store": "auto"},       # OFF: the monitor uses your own `gh login`. On: a token kept in the store of the system (secretstore.py)
    "github_actions": {"enabled": False, "allowed": ["rerun_failed", "cancel"], "merge_method": "squash"},      # OFF: actions on GitHub, each one confirmed on its own (ghactions.py)
    "act": {"enabled": False, "allowed": [], "timeout_seconds": 900, "allow_symlinks": False},
    "dispatch": {"required_ci": ["ci.yml"]},                                 # the workflow files that must have passed on a commit before a batch is fired (gha_dispatch_all.py)         # OFF: run a workflow here with `act`, each run confirmed on its own (actlocal.py)
    "mirror": {"enabled": False, "folder": "", "max_mb": 500, "keep_days": 14, "max_per_cycle": 3},     # OFF: a local copy of the artifacts of the runs (mirror.py)
    "runners": {"enabled": False, "scope": "owner"},                         # OFF: the self-hosted runners of the account (runners.py)
    "otlp": {"enabled": False, "endpoint": "", "interval_seconds": 60},       # OFF: OpenTelemetry export to a collector you name (otlp.py)
    "organizations": {"discover": False},                                    # OFF: list the organisations of the login (orgs.py)
    "finops": {"jobs_per_cycle": 0},
    "network": {"use_proxy": False, "etag": True, "graphql_checks": False, "graphql_batch": 20},                                         # OFF: outgoing requests ignore the proxy variables of the environment (netguard.py)
    "ai_notify": {"enabled": False, "confirmed_provider": "", "max_calls_per_hour": 4, "cost_per_call_cents": 5, "max_cost_per_hour_cents": 50, "command": "", "timeout_seconds": 30},      # OFF: tell an external AI of a NEW real alert (ai_notify.py)
    "ai_alerts": {"enabled": False, "folder": "", "brief_max_bytes": 2048, "hook": {"enabled": False, "url": "", "max_per_hour": 6},
                  "diagnose": {"enabled": False, "max_per_cycle": 3, "log_lines": 10, "max_bytes": 1500},      # OFF: reads logs of GitHub (the allowance)
                  "cascade": {"enabled": True, "map": {}},
                  "stream": {"enabled": False, "max_seconds": 3600, "max_clients": 3},      # OFF: GET /api/ai/stream
                  "heartbeat": {"enabled": True, "window_minutes": 15},
                  "client_hook": {"enabled": True, "block_on_stop": False, "cooldown_minutes": 20, "stale_hours": 3, "max_lines": 12, "max_chars": 2400}},     # a local, read-only feed of alerts for AIs (ai_alerts.py); the hook is OFF                                          # 0: the system of each job is not read (quota.default_runner is assumed)
}

DEMO = {"on": False}      # --demo: invented data, no gh, no network
LITE = {"on": False}      # the lite product: the same server without the sentinel, with its own configuration file, its own state files and a short settings page
LITE_PORT = 8766
CHILD = {"account": "", "folder": ""}      # set by account_child.py: this process is the monitor of ONE account of an installation with several (empty = the single account, as always)


def state_dir():
    """Where the small state files of this process live: the folder of the account when this is the monitor of one account, else next to the code, as always."""
    return Path(CHILD["folder"]) if CHILD["folder"] else paths.folder("data")
LITE_SHARED = ("/api/ai/state", "/api/ai/stream", "/api/ai/brief", "/api/ai/alerts", "/api/ai/ack")      # the channels for an AI tool are the same in both editions
LITE_PATHS = ("/api/gh-action", "/api/act", "/api/credential", "/api/github-token", "/api/runners", "/api/mirror", "/api/otlp", "/api/sentinel", "/api/ai", "/api/notify", "/api/analytics", "/api/live-events", "/api/live-status", "/api/outputs", "/api/webhook", "/api/refresh-repos", "/metrics", "/api/alerts", "/api/events")   # they do not exist in lite


LITE_INHERIT = ("github_owner", "ecosystems", "ecosystems_file", "targets_file", "profiles_file", "exclude", "repos", "language", "runs_per_repo", "cold_runs_per_repo", "hot_hours", "stuck_minutes", "refresh_seconds", "cold_refresh_seconds")   # what a first lite start copies from actions_monitor.json
HOT_FORCED = set()    # repositories a webhook event touched: they are read again in the next cycle
HIDDEN = {"hidden": 0, "discovered": 0, "names": []}      # repositories of the account that the ecosystem filter leaves out, and how many the account has


def lite_inheritance(source):
    """The settings of the complete monitor that the lite one starts with: the account, what to watch and the language; never the sentinel, the AI, the webhook or the outputs. {} when there is nothing."""
    try:
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: data[k] for k in LITE_INHERIT if isinstance(data, dict) and k in data}


def lite_requested(argv=None):
    """True with --lite or MONITOR_MODE=lite."""
    return "--lite" in (sys.argv[1:] if argv is None else argv) or os.environ.get("MONITOR_MODE", "").strip().lower() == "lite"


def enable_lite():
    """Switches the module to the lite product BEFORE the configuration is read: its own file names (so that the complete monitor and the lite one can live in the same folder)."""
    global CONFIG_FILE, LOG_FILE
    from github_actions_monitor.app import settings_api
    LITE["on"] = True
    CONFIG_FILE = paths.place("actions_monitor_lite.json")
    LOG_FILE = paths.place("actions_monitor_log_lite.txt")
    settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = CONFIG_FILE
    settings_api.BACKUP_DIR = paths.place("config_backups_lite")
    etagcache.CACHE_FILE = paths.place("etag_cache_lite.json")


RESTART_PENDING = set()   # settings changed from the page since this process started that only apply after a restart
STATE = {"data": None, "error": None, "hint": None}
WATCH = cycle_watch.CycleWatch()      # the heartbeat of the refresh loop (phase, last good cycle, last error, log problem)
SENTINEL = {"obj": None, "error": None, "registry": None}  # the CI sentinel (layer A) and the registry of all of them; a failure of any never stops the monitor
LOCK = threading.Lock()
ISSUE_CACHE = {"at": 0.0, "items": [], "busy": False}
RUN_CACHE = {}  # repo -> {"runs": [...], "at": float, "error": str|None}
PRIVATE = set()                           # private repositories of the account (read with the listing): the only ones whose minutes cost anything
QUOTA_ALERTS = None
DISCOVERED = {"at": 0.0, "names": [], "snapshot": {}}
DISCOVERY = {"events": [], "suggestions": []}   # what the last listing of the account brought (memory only)
HOT_ONLY = {"on": False, "until": 0.0}   # "only hot" switch (memory only): cold repositories are not refreshed until `until` (one long cycle)
LIVE_CONFIG = {}                          # the config the loop runs with, for the HTTP handler
AUTOSAVE = None                           # report_history.AutoSaver, created in main()
ETAG = {"cache": None}                    # etagcache.EtagCache (None = plain reads)
LINK = resilience.Link()                  # the connection: offline since..., back online
ANALYTICS = {"store": None, "summary": None, "at": 0.0}
LIVE_EVENTS = []                          # the newest webhook events (workflow_run / workflow_job), newest last
STARTED = time.time()


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
        example = paths.EXAMPLES / "actions_monitor.example.json"   # the template that travels with the package; the defaults are only the fallback
        try:
            if example.is_file() and LITE["on"]:   # lite: the same template with the sentinel off and the light reading
                template = json.loads(example.read_text(encoding="utf-8"))
                template.update({"mode": "lite", "ecosystems": "all", "sentinel": {"enabled": False}, "webhook": {"enabled": False, "secret": ""}})
                inherited = lite_inheritance(paths.place("actions_monitor.json", HERE))
                template.update(inherited)
                if inherited:
                    print(i18n.t("mon.lite_inherited", keys=", ".join(sorted(inherited))))
                private_io.write_private(CONFIG_FILE, json.dumps(template, ensure_ascii=False, indent=2) + "\n")
                config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
            elif example.is_file():
                private_io.write_private(CONFIG_FILE, example.read_text(encoding="utf-8"))
                config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
            else:
                private_io.write_private(CONFIG_FILE, json.dumps(DEFAULTS, indent=2))
        except (OSError, ValueError):
            pass
    except (OSError, ValueError) as error:
        print(i18n.t("mon.config_unreadable", error=error))
    return config


def pool_status():
    """What the Quota tab shows (never a token, never a path): every source with its allowance, the permissions the App was granted and the warning about a key or token file that others can read."""
    from github_actions_monitor.integrations import github_app
    from github_actions_monitor.data_pipeline import readpool
    config = LIVE_CONFIG or toolconfig.raw_config()
    out = {"sources": [], "recommended": {"modes.auto_low": True, "network.etag": True}, "trend": __import__("github_actions_monitor.data_pipeline.quotawatch", fromlist=["_"]).trend()}
    try:
        core = gh("api", "rate_limit", retries=0, as_user=True)["resources"]["core"]
        out["sources"].append({"name": "user", "ok": True, "remaining": core["remaining"], "limit": core["limit"], "reset": core["reset"]})
    except Exception as error:   # noqa: BLE001
        out["sources"].append({"name": "user", "ok": False, "error": github_app.clean(str(error))[:120]})
    app = github_app.status(config)
    if app.get("enabled"):
        rate = app.get("rate") or {}
        out["sources"].append({"name": "app", "ok": bool(app.get("ok")), "app": app.get("app", ""), "remaining": rate.get("remaining"), "limit": rate.get("limit"), "reset": rate.get("reset"),
                               "missing": [p for p, v in (app.get("permissions") or {}).items() if v == "missing"], "error": app.get("error", ""), "warning": app.get("warning", ""), "openssl": app.get("openssl")})
    extra = readpool.settings(config)
    if extra["enabled"]:
        item = {"name": "extra", "ok": False, "warning": readpool.file_warning(extra["file"])}
        if not readpool.token_from_file(extra["file"]):
            item["error"] = "no token in the file"
        else:
            try:
                core = gh("api", "rate_limit", retries=0, source="extra")["resources"]["core"]
                item.update({"ok": True, "remaining": core["remaining"], "limit": core["limit"], "reset": core["reset"]})
                readpool.note_probe("extra", core["remaining"])
            except Exception as error:   # noqa: BLE001
                item["error"] = github_app.clean(str(error))[:120]
        out["sources"].append(item)
    return out


def rate_probes(config):
    """{"user": {...}, "app": {...}, "extra": {...}}: the allowance of each source that is on, from the free call `rate_limit` (each answers for its own token). A source that cannot answer is left out."""
    from github_actions_monitor.data_pipeline import readpool
    out = {}
    for name in readpool.available(config) if len(readpool.available(config)) > 1 else ["user"]:
        try:
            core = gh("api", "rate_limit", retries=0, source=name)["resources"]["core"] if name != "user" else gh("api", "rate_limit", retries=0, as_user=True)["resources"]["core"]
        except Exception:   # noqa: BLE001
            if name == "user":
                raise
            readpool.note_failure(name)
            continue
        out[name] = {"remaining": core["remaining"], "limit": core["limit"], "reset": datetime.fromtimestamp(core["reset"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        readpool.note_probe(name, core["remaining"])
    return out


CALLS = {"n": 0}


def read_source(args, source=None):
    """(name, {"env": ...}) of the source that does a read (readpool.py): the user, the GitHub App or the second read-only account, the one with the most calls left; `source` forces one. Writes and actions
    always get the user."""
    try:
        from github_actions_monitor.data_pipeline import readpool
        config = LIVE_CONFIG or toolconfig.raw_config()
        if source:
            return source, readpool.env_for(config, source)
        return readpool.pick(config, args)
    except Exception as error:   # noqa: BLE001 - the pool never stops a read: the user's token answers
        degraded.note("loop.extra", error)
        return "user", {}


def gh(*args, timeout=40, retries=2, as_user=False, source=None):
    """Runs `gh` with a fixed argument list (no shell). Retries slow or flaky answers, not auth errors. The READS are spread over the sources of the pool (user, GitHub App, second read-only account); a source
    that is refused is left out for a while and the same read is made with the next one, the user last."""
    last = ""
    name, via = ("user", {}) if as_user else read_source(args, source)
    attempt, attempts = -1, retries + 1
    while attempt + 1 < attempts:
        attempt += 1
        try:
            CALLS["n"] += 1      # the calls of this monitor: the trend of the consumption tells them from the ones other tools make (quotawatch.py)
            extra = via or secretstore.gh_kwargs()
            result = cycle_watch.bounded(lambda: subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout, **extra), timeout + 15)      # a child that keeps its pipes open cannot hold the loop
        except subprocess.TimeoutExpired:
            last = "timeout"
            time.sleep(resilience.backoff(attempt))
            continue
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout.strip() else None
        last = (result.stderr or result.stdout).strip()[:300]
        if via:
            from github_actions_monitor.integrations import github_app
            from github_actions_monitor.data_pipeline import readpool
            if github_app.should_retry_with_user(last):      # this source lacks a permission or its token was refused: the same read with the next one
                readpool.note_failure(name)
                if name == "app":
                    github_app._STATE.update({"token": "", "failed_at": time.time(), "error": github_app.clean(last)[:120]})
                name, via = read_source(args) if not source else ("user", {})
                attempts += 1      # the read with the next source is one more try, not one less
                continue
        if "401" in last or "Bad credentials" in last or ("403" in last and "rate limit" not in last.lower()):
            raise AuthError(last)
        if "404" in last:
            break  # a repository without Actions: retrying does not help
        if attempt < retries:
            time.sleep(resilience.backoff(attempt) if resilience.is_transient(last) else secondary_wait(last, attempt, random.random()))
    raise RuntimeError(last or "gh failed")


def secondary_wait(message, attempt, jitter=0.0):
    """Seconds to wait after a failed call: a secondary (abuse) limit asks for at least a minute and then backs off exponentially; anything else keeps the short wait. `jitter` (0..1,
    random.random() in the callers) adds up to 20 % so that parallel readers do not retry in the same second."""
    text = (message or "").lower()
    if "secondary rate limit" in text or "retry-after" in text or "abuse" in text:
        base = min(300, 60 * 2 ** attempt)
    else:
        base = 2 * (attempt + 1)
    return base * (1 + 0.2 * max(0.0, min(1.0, jitter)))


def run_gh(args, timeout=40):
    """(returncode, stdout, stderr) of one `gh` call with a fixed argument list (no shell)."""
    try:
        extra = secretstore.gh_kwargs()
        done = cycle_watch.bounded(lambda: subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **extra), timeout + 15)
        return done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


def gh_read(endpoint, retries=2):
    """A GET read of the API: conditional (ETag) when the cache is on, else a plain `gh api`. Raises like gh()."""
    cache = ETAG["cache"]
    if cache is None or not cache.enabled:
        return gh("api", endpoint, retries=retries)
    last = ""
    for attempt in range(retries + 1):
        try:
            data, _status = cache.fetch(endpoint, run_gh)
            return data
        except RuntimeError as error:
            last = str(error)
            if "401" in last or "Bad credentials" in last or ("403" in last and "rate limit" not in last.lower()):
                raise AuthError(last) from None
            if "404" in last:
                break
            if attempt < retries:
                time.sleep(resilience.backoff(attempt) if resilience.is_transient(last) else secondary_wait(last, attempt, random.random()))
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
            limit = str(config.get("discover_limit", 1000))
            try:       # the richer listing (archived, fork, private, empty) lets the monitor notice news and apply the lifecycle rules
                data = gh("repo", "list", toolconfig.github_owner(config), "--limit", limit, "--json", "name,isArchived,isFork,isPrivate,isEmpty", retries=0) or []
            except AuthError:
                raise
            except Exception:   # an older gh without those fields: the plain listing, as before
                data = gh("repo", "list", toolconfig.github_owner(config), "--limit", limit, "--no-archived", "--json", "name") or []
            rules = discovery.settings(config)
            PRIVATE.clear()
            PRIVATE.update(item["name"] for item in data if item.get("isPrivate"))
            snapshot = {item["name"]: {"archived": bool(item.get("isArchived"))} for item in data}
            if rules["events"]:
                found = discovery.diff(DISCOVERED.get("snapshot"), snapshot)
                if found:
                    announce_discovery(found, config)
            DISCOVERED["snapshot"] = snapshot
            DISCOVERED["names"] = sorted(discovery.lifecycle([dict(item, isArchived=bool(item.get("isArchived"))) for item in data if not item.get("isArchived")], rules))
            DISCOVERED["at"] = time.time()
        known = toolconfig.ecosystem_names(config)
        wanted_eco = config["ecosystems"]
        allowed = set(known if wanted_eco in ("all", None) else wanted_eco)
        unclassified = config.get("show_unclassified", True) is True and wanted_eco in ("all", None)
        names = [n for n in DISCOVERED["names"] if not known or ecosystem_of(n) in allowed or n == toolconfig.github_owner(config) or (unclassified and ecosystem_of(n) == "other")]   # no ecosystems file: every repository
        kept = set(names)
        left_out = [n for n in DISCOVERED["names"] if n not in kept]
        HIDDEN["discovered"], HIDDEN["hidden"], HIDDEN["names"] = len(DISCOVERED["names"]), len(left_out), left_out[:50]
        if discovery.settings(config)["suggest_groups"]:
            DISCOVERY["suggestions"] = discovery.suggest_groups([n for n in DISCOVERED["names"] if ecosystem_of(n) in ("other", "rest")], taken=set(known))
    skip = set(config["exclude"])
    valid = [n for n in names if NAME_RE.match(n) and n not in skip]
    for n in names:
        if not NAME_RE.match(n):
            print(i18n.t("mon.bad_repo_name", name=repr(n)[:60]))
    return valid


def fetch_runs(repo, per_page):
    try:
        data = gh_read(f"repos/{toolconfig.github_owner()}/{repo}/actions/runs?per_page={per_page}")
    except AuthError:
        raise
    except Exception as error:  # a repo without Actions or a network problem must not stop the page
        LINK.record(str(error))
        return [], str(error)
    LINK.record(None)
    runs = []
    for run in data.get("workflow_runs", []):
        started = parse_time(run.get("run_started_at") or run.get("created_at"))
        updated = parse_time(run.get("updated_at"))
        finished = run.get("status") == "completed"
        runs.append({
            "repo": repo, "id": run["id"], "name": run.get("name") or "", "title": (run.get("display_title") or "")[:90],
            "event": run.get("event"), "branch": run.get("head_branch"), "path": (run.get("path") or "").split("@")[0].rsplit("/", 1)[-1], "sha": (run.get("head_sha") or "")[:7],
            "actor": (run.get("actor") or {}).get("login", ""), "status": run.get("status"), "number": run.get("run_number"),
            "queued": seconds_between(parse_time(run.get("created_at")), started) if run.get("created_at") and run.get("run_started_at") else None,
            "conclusion": run.get("conclusion"), "started": run.get("run_started_at") or run.get("created_at"),
            "seconds": seconds_between(started, updated if finished else None), "url": run.get("html_url"), "attempt": run.get("run_attempt"),
        })
    return runs, None


TUNED = {"refresh_seconds": None, "cold_refresh_seconds": None}
MODE = modes.State()      # the working mode: normal unless you ask (memory only, unless modes.remember is on)
MODE_SAID = [""]


def mode_remaining():
    with LOCK:
        rate = (STATE.get("data") or {}).get("rate") or {}
    return rate.get("remaining"), rate.get("limit")


def tuned(config, key, data=None):
    """The interval in force: the configured one, or (discovery.auto_frequency on) the one the real activity of the last 24 hours asks for, inside the quota budget (discovery.auto_frequency())."""
    if discovery.settings(config)["auto_frequency"] and data is not None and data.get("figures"):
        hot, cold = discovery.auto_frequency(config, data["figures"].get("ok24", 0) + data["figures"].get("fail24", 0), max(1, len(data.get("repos") or [])), 3000)
        TUNED["refresh_seconds"], TUNED["cold_refresh_seconds"] = hot, cold
    value = TUNED[key] if (discovery.settings(config)["auto_frequency"] and TUNED.get(key)) else config[key]
    remaining, _limit = mode_remaining()
    name = MODE.current(config, remaining)
    if MODE.notice and MODE.notice != MODE_SAID[0] and MODE.notice in ("expired", "quota", "auto_low", "auto_low_end"):
        MODE_SAID[0] = MODE.notice
        print(banner_mode_line(name, i18n.t("mode.back_" + MODE.notice)), flush=True)
    return modes.effective({**config, key: value}, key, name)


def banner_mode_line(name, extra=""):
    return f"{'[LITE]' if LITE['on'] else '[COMPLETE]'} {i18n.t('mode.title')}: {i18n.t('mode.' + name)} {extra}".strip()


def central_result(config=None):
    """The base line of the central panel (cached; {"ok": False} while it is off)."""
    from github_actions_monitor.sentinels import central_source
    config = config or toolconfig.raw_config()
    return central_source.read(config, toolconfig.github_owner(config), workspace_root_text())


def workspace_root_text():
    try:
        from github_actions_monitor.app import workspace
        return str(workspace.workspace_root_soft() or "")
    except Exception:   # noqa: BLE001
        return ""


def is_hot(repo, config, now):
    if repo in HOT_FORCED:
        return True
    if MODE.name == "low":
        try:      # in Low the central panel says which repositories are red without asking GitHub: those are read live, the others wait for the long interval
            from github_actions_monitor.sentinels import central_source
            if repo in central_source.red_repos(central_result(config)):
                return True
        except Exception as error:   # noqa: BLE001
            degraded.note("loop.extra", error)
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
        if started and (datetime.now(timezone.utc) - started).total_seconds() < tuned(config, "hot_hours") * 3600:
            return True
    return False


RATE_BLOCK = {"until": 0.0, "unread": 0}      # while the allowance of GitHub is used up the reads of the repositories wait for the renewal: one notice, not one error per repository
RATE_RE = re.compile(r"rate limit|api rate|secondary rate", re.I)


def is_rate_limit(error):
    return bool(RATE_RE.search(str(error or "")))


def short_error(error, limit=160):
    """The first line of an error of `gh`, without the legal paragraph and the request id GitHub adds to a rate limit message."""
    text = str(error or "").strip().splitlines()[0] if str(error or "").strip() else ""
    for cut in (" If you reach out", " (https://", " (http", " Request ID", " - Request"):
        if cut in text:
            text = text.split(cut)[0]
    return text.strip(" .,:;")[:limit]


def rate_block_start(now=None):
    """The allowance ran out in the middle of a cycle: the reads stop until its renewal (the free call `rate_limit` says when; ten minutes if it cannot be read)."""
    now = time.time() if now is None else now
    until = now + 600
    try:
        reset = gh("api", "rate_limit", retries=0)["resources"]["core"]["reset"]
        if reset > now:
            until = float(reset) + 5
    except Exception:   # noqa: BLE001 - the answer of rate_limit may itself be refused
        pass
    RATE_BLOCK["until"] = until
    return until


def rate_block_state(rate=None, now=None):
    """{"blocked", "until", "unread"} for the page, the bar and the alerts: `until` is the renewal in ISO UTC."""
    now = time.time() if now is None else now
    blocked = now < RATE_BLOCK["until"] or bool(rate and rate.get("remaining") is not None and rate["remaining"] <= 0)
    until = RATE_BLOCK["until"] if now < RATE_BLOCK["until"] else None
    if rate and rate.get("reset") and blocked:
        return {"blocked": True, "until": rate["reset"], "unread": RATE_BLOCK["unread"]}
    return {"blocked": blocked, "until": datetime.fromtimestamp(until, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if until else None, "unread": RATE_BLOCK["unread"]}


def refresh_runs(repos, config, progress=None):
    """Hot repositories every cycle with the full run list, cold ones only now and then with a short list."""
    now = time.time()
    lite = config["mode"] == "lite"
    only_hot = hot_only_state(now)["on"]
    todo = []
    cold_due = set()      # the repositories that only wait for their slow turn: the ones network.graphql_checks may read in batches
    for repo in repos:
        entry = RUN_CACHE.get(repo)
        hot = is_hot(repo, config, now)
        HOT_FORCED.discard(repo)
        if entry is None:
            todo.append((repo, config["cold_runs_per_repo"]))  # first look: a short list; the hot ones get the full list next cycle
        elif hot:
            todo.append((repo, config["cold_runs_per_repo"] if lite else tuned(config, "runs_per_repo")))
        elif not only_hot and now - entry["at"] > tuned(config, "cold_refresh_seconds"):
            todo.append((repo, config["cold_runs_per_repo"]))
            cold_due.add(repo)
    done = 0
    RATE_BLOCK["unread"] = 0
    if time.time() < RATE_BLOCK["until"]:      # the allowance is still used up: nothing is asked until it renews (the old picture stays)
        RATE_BLOCK["unread"] = len(todo)
        return 0
    total = len(todo)
    batched = graphql_cold(config, [r for r, _n in todo if r in cold_due])
    if batched:
        for repo, runs in batched.items():
            note_read(repo, runs, None)
        todo = [item for item in todo if item[0] not in batched]
    for start in range(0, len(todo), 40):  # chunks, so the page can show the first results while the rest loads
        chunk = todo[start:start + 40]
        with ThreadPoolExecutor(max_workers=config["max_workers"]) as pool:
            results = list(pool.map(lambda item: (item[0], *fetch_runs(*item)), chunk))
        limited = False
        for repo, runs, error in results:
            if error and is_rate_limit(error):
                limited = True
                continue      # not an error of the repository: the read is repeated after the renewal
            note_read(repo, runs, error)
        done += len(chunk)
        if limited:
            rate_block_start()
            RATE_BLOCK["unread"] = len(todo) - done + sum(1 for _r, _x, e in results if e and is_rate_limit(e))
            break
        if progress:
            progress(done, len(todo))
    return total


def graphql_cold(config, repos):
    """network.graphql_checks (off by default): the cold repositories that are due are read with batches of GraphQL (its own allowance) instead of one REST call each. {repo: runs} for the ones
    the batches answered; the others (and everything when the switch is off, a batch fails or the answer is not understood) are read through REST in the same cycle."""
    cfg = graphql_checks.settings(config)
    if not cfg["enabled"] or not repos:
        return {}

    def call(text):
        return gh("api", "graphql", "-f", "query=" + text, retries=0, as_user=True)
    try:
        found, _rest = graphql_checks.read_batches(toolconfig.github_owner(), repos, cfg["batch"], call)
    except Exception as error:   # noqa: BLE001 - a feature that saves allowance never stops the cycle
        degraded.note("loop.extra", error)
        return {}
    return found


def note_read(repo, runs, error):
    """Stores the result of one read of a repository. A passing failure (a TLS hiccup, a 5xx, a cut) keeps the last runs, is read again in the next cycle and is shown as an error only
    after resilience.TRANSIENT_CYCLES cycles in a row; any other error is shown at once (the old runs stay)."""
    entry = RUN_CACHE.get(repo)
    if not error:
        RUN_CACHE[repo] = {"runs": runs, "at": time.time(), "error": None, "fails": 0}
        return
    fails = (entry or {}).get("fails", 0) + 1
    if resilience.is_transient(error) and fails < resilience.TRANSIENT_CYCLES:
        if entry:
            entry.update({"fails": fails, "at": 0})      # the old picture stays and the read is repeated in the next cycle; nothing is shown yet
        else:
            RUN_CACHE[repo] = {"runs": [], "at": 0, "error": None, "fails": fails}
        return
    error = short_error(error) or "gh failed"      # one line: no legal paragraph, no request id
    if entry:
        entry.update({"error": error, "fails": fails})      # keep the old runs, report the problem
    else:
        RUN_CACHE[repo] = {"runs": runs, "at": time.time(), "error": error, "fails": fails}


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


def unresolved_failures(runs, default_branches=None):
    """The failures that are still open: the last completed run of a workflow on the DEFAULT branch of its repository failed (the rule of "red on main", redrule.py: cancelled, skipped and dynamic runs
    say nothing). A failure on a work branch is not an open alert: the tile "red on main", the list of alerts, the bar at the foot and the brief all count the same thing."""
    by_repo = {}
    for run in runs:
        by_repo.setdefault(run["repo"], []).append(run)
    out = []
    for repo, items in by_repo.items():
        branch = (default_branches or {}).get(repo) or redrule.guess_default_branch(items) or "main"
        last = {}
        for run in sorted(redrule.completed_runs(items, branch), key=lambda r: r.get("started") or ""):
            last[redrule.workflow_key(run)] = run
        out.extend(run for run in last.values() if run.get("conclusion") in redrule.BAD)
    return out


def collect(config, publish=None):
    repos = watched_repos(config)
    started = time.time()

    def partial(done, total):
        if publish and not STATE.get("complete"):  # only until the first complete picture exists
            publish(build(config, repos, started, done, True, f"{done}/{total}"))

    refreshed = refresh_runs(repos, config, partial)
    return build(config, repos, started, refreshed, False, "")


def repo_meta(repos):
    """{repo: {"private": bool, "branch": str or None, "pushed": ISO or None, "prs": int or None}} for the columns of the Repositories table. The visibility comes from the listing the monitor already
    reads; the rest from the CI sentinel when it has looked (the lite edition has none: those fields are None). Nothing new is read from GitHub."""
    info = {}
    sentinel = SENTINEL.get("obj")
    try:
        info = dict(getattr(sentinel, "repo_info", None) or {}) if sentinel is not None and not LITE["on"] else {}
    except Exception:       # noqa: BLE001 - extra columns never stop the page
        info = {}
    out = {}
    for repo in repos:
        item = info.get(repo) if isinstance(info.get(repo), dict) else {}
        prs = item.get("prs")
        out[repo] = {"private": repo in PRIVATE, "branch": item.get("branch") or None, "pushed": item.get("pushed") or None, "prs": len(prs) if isinstance(prs, list) else None}
    return out


def header_figures(runs, active, issues, now=None, red=None, approx=False):
    """The figures of the header, the same for both editions: runs of the last 24 hours (one per id), failures, successes, compute minutes, and what is running or queued."""
    now = time.time() if now is None else now
    since = now - 86400
    seen, last = set(), []
    for run in runs:
        started = parse_time(run.get("started"))
        if run.get("id") in seen or not started or started.timestamp() <= since:
            continue
        seen.add(run.get("id"))
        last.append(run)
    done = [r for r in last if r.get("status") == "completed"]
    figures = {"active": sum(1 for r in active if r.get("status") == "in_progress"), "queued": sum(1 for r in active if r.get("status") != "in_progress"),
               "fail24": sum(1 for r in done if r.get("conclusion") in ("failure", "timed_out", "startup_failure")), "ok24": sum(1 for r in done if r.get("conclusion") == "success"),
               "issues": len(issues), "min24": round(sum(r.get("seconds") or 0 for r in last) / 60)}
    if red is not None:
        figures["red"], figures["red_approx"], figures["red_repos"] = len(red), bool(approx), len({row["repo"] for row in red})
    return figures


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
    active, seen_active = [], set()
    for run in runs:        # one entry per run (a repository read twice must not count its runs twice): the header figures and the list "Right now" are made from this same list
        if run["status"] in ("in_progress", "queued", "waiting", "requested", "pending") and run.get("event") != "dynamic" and (run["repo"], run.get("id")) not in seen_active:
            seen_active.add((run["repo"], run.get("id")))
            active.append(run)
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
        rate_sources = rate_probes(config)      # free of quota: it is also read while loading, so the allowance is on the page from the first moment
        rate = max(rate_sources.values(), key=lambda r: r["remaining"])
    except Exception:
        rate, rate_sources = None, {}
    rate_user = (rate_sources.get("user") if rate is not None else None)
    try:
        from github_actions_monitor.data_pipeline import quotawatch
        if rate_user:      # the allowance of the user, the one the other tools spend too
            quotawatch.note(rate_user["remaining"], rate_user["limit"], rate_user["reset"], CALLS["n"], time.time())
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
    hot = sum(1 for repo in repos if is_hot(repo, config, time.time()))
    red, approx = None, False
    if LITE["on"]:      # the lite edition has no sentinel: it counts the red workflows with the same small rule, guessing the default branch
        red, approx = redrule.red_workflows({r: [x for x in runs if x["repo"] == r] for r in repos}, None, True, config.get("runs_per_repo"))
    else:      # the complete edition knows the real figure (the sentinel); without it the same small rule: both editions report the same keys
        try:
            red = red_rows({"runs": runs, "repos": repos})
        except Exception as error:   # noqa: BLE001 - a figure of the header never stops a cycle
            degraded.note("loop.extra", error)
    figures = header_figures(runs, active, ISSUE_CACHE["items"], red=red, approx=approx)
    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "updated_local": tzdisplay.stamp(time.time()), "took": round(time.time() - started, 1),
        "repos": repos, "ecosystems": {repo: ecosystem_of(repo) for repo in repos},
        "runs": runs[:600], "runs_total": len(runs), "active": active, "issues": ISSUE_CACHE["items"], "failing": unresolved_failures(runs, {r: m.get("branch") for r, m in repo_meta(repos).items() if m.get("branch")}),
        "errors": errors, "rate": rate, "rate_user": rate_user, "rate_sources": rate_sources, "quota_trend": __import__("github_actions_monitor.data_pipeline.quotawatch", fromlist=["_"]).trend(), "stuck_minutes": config["stuck_minutes"],
        "mode": config["mode"], "refreshed": refreshed, "hot": hot, "loading": progress_text if loading else "",
        "quota_block": rate_block_state(rate), "min_rate": config["min_rate_remaining"], "paused_quota": bool(rate and rate["remaining"] < config["min_rate_remaining"]),
        "refresh_seconds": config["refresh_seconds"], "hot_only": hot_only_state(),
        "offline": LINK.state(), "etag": ETAG["cache"].stats() if ETAG["cache"] else None, "graphql": graphql_checks.stats(config),
        "hidden": HIDDEN["hidden"], "discovered": HIDDEN["discovered"], "hidden_names": HIDDEN["names"],
        "figures": figures, "repo_meta": repo_meta(repos),
    }


WEBHOOK_STATS = {"accepted": 0, "bad_signature": 0, "ignored": 0, "duplicates": 0, "refused": 0, "last_at": None}      # deliveries seen since this process started (memory only; no payload, no secret)


def webhook_count(code, duplicate=False):
    """Counts one delivery by what the receiver answered: 200 accepted, 401 a signature that did not verify, 202 ignored (a repository that is not watched, an event that is not used, a replay), anything else refused. A 404 is the
    receiver being off: nothing arrived, so nothing is counted."""
    if code == 404:
        return
    key = "accepted" if code == 200 else "bad_signature" if code == 401 else ("duplicates" if duplicate else "ignored") if code == 202 else "refused"
    WEBHOOK_STATS[key] += 1
    if code == 200:
        WEBHOOK_STATS["last_at"] = resilience.stamp(time.time())


def webhook_status(config):
    """What the Live view says about the receiver: whether it is on, whether the secret is long enough (never the secret itself), the counters and the newest event. Read only."""
    from github_actions_monitor.security import webhook
    cfg = webhook.settings(config)
    newest = LIVE_EVENTS[-1] if LIVE_EVENTS else None
    return {"enabled": cfg["enabled"], "active": webhook.active(config), "secret_ok": len(cfg["secret"]) >= webhook.MIN_SECRET, "text": webhook.status_text(config), "stats": dict(WEBHOOK_STATS),
            "keep": webhook.live_settings(config)["live_events_keep"], "held": len(LIVE_EVENTS),
            "last": ({k: newest.get(k) for k in ("repo", "name", "event", "status", "conclusion", "at")} if newest else None)}


def apply_live_event(record, config):
    """A signed workflow_run / workflow_job event: it goes to the live list, updates the run list of the repository without a read (so no quota is used), feeds the analytics and, when a run
    ends red, the notifications. Nothing of the payload but the short validated fields is kept."""
    from github_actions_monitor.integrations import notifiers
    from github_actions_monitor.security import webhook
    keep = webhook.live_settings(config)["live_events_keep"]
    LIVE_EVENTS.append({k: v for k, v in record.items() if k in webhook.LIVE_FIELDS} | {"at": resilience.stamp(time.time())})
    del LIVE_EVENTS[:-keep]
    run = webhook.as_run(record)
    entry = RUN_CACHE.get(record["repo"])
    HOT_FORCED.add(record["repo"])      # whatever the event said, the repository is read again in the next cycle (the event is the news, the read is the proof)
    if run and entry is not None:
        runs = [r for r in entry["runs"] if r.get("id") != run["id"]]
        entry["runs"] = sorted(runs + [run], key=lambda r: r.get("started") or "", reverse=True)[:max(config.get("runs_per_repo", 20), 5)]
        entry["at"] = time.time()
    elif entry is not None:
        entry["at"] = 0
    store = ANALYTICS["store"]
    if record["event"] == "workflow_job" and store is not None and record.get("status") == "completed" and analytics.settings(config)["enabled"] and record.get("queue") is not None:
        key = f"{record['repo']}|{record['workflow']}"
        store.data["queue"][key] = (store.data["queue"].get(key, []) + [record["queue"]])[-store.max_samples:]
        for name, seconds in (record.get("steps") or {}).items():
            slot = store.data["steps"].setdefault(key, {})
            slot[name] = (slot.get(name, []) + [seconds])[-store.max_samples:]
        store.dirty = True
    if record["event"] == "workflow_run" and record.get("status") == "completed" and record.get("conclusion") in ("failure", "timed_out", "startup_failure"):
        notifiers.notify(config, {"kind": "workflow_failed", "owner": "main", "repo": record["repo"], "url": record.get("url"),
                                  "text": i18n.t("evt.workflow_failed", repo=record["repo"], workflow=record.get("workflow") or "")})


def announce_discovery(found, config):
    """New, vanished, archived or unarchived repositories go to the console, to the list shown in Settings > Basic and (complete edition) to the notifications. Never raises."""
    from github_actions_monitor.integrations import notifiers
    for item in found:
        text = i18n.t("evt." + item["code"], repo=item["repo"])
        DISCOVERY["events"].append({"code": item["code"], "repo": item["repo"], "text": text, "at": resilience.stamp(time.time())})
        print(text, flush=True)
        if not LITE["on"]:
            try:
                notifiers.notify(config, {"kind": item["code"], "code": item["code"], "level": "info", "repo": item["repo"], "owner": "main", "url": None, "args": {}, "text": text})
            except Exception as error:   # noqa: BLE001 - a notification problem never stops the loop
                degraded.note("notify", error)
                pass
    del DISCOVERY["events"][:-50]


def announce_link(transition, config):
    """A change of the connection goes to the event feed and to the notifications, once."""
    from github_actions_monitor.integrations import notifiers
    kind = transition["kind"]
    event = {"kind": kind, "code": kind, "level": "warn" if kind == "offline" else "info", "repo": "", "owner": "main", "url": None, "args": {},
             "text": i18n.t("evt." + kind, since=transition["at"], seconds=transition.get("seconds_offline", 0))}
    print(event["text"], flush=True)
    sentinel = SENTINEL["obj"]
    try:
        if sentinel is not None:
            sentinel.feed._append([event])
        notifiers.notify(config, event)
    except Exception as error:   # noqa: BLE001 - never stops the loop
        degraded.note("loop.step", error)
        pass


def quota_delay(rate, floor, delay, now=None):
    """The pause before the next cycle given the allowance of GitHub (it is shared by every tool of the account): below the floor the loop slows to 180 s so the agents and the owner keep what is left;
    when nothing is left it waits for the renewal (at most an hour and five minutes), because every call would fail and spend the next allowance as soon as it arrives."""
    if not rate or rate.get("remaining") is None:
        return delay
    if rate["remaining"] <= 0:
        try:
            reset = datetime.strptime(rate["reset"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            return max(delay, min(3900, int(reset - (time.time() if now is None else now)) + 5))
        except (KeyError, TypeError, ValueError):
            return max(delay, 600)
    if rate["remaining"] < floor:
        return max(delay, 180)
    return delay


def quota_watch(config):
    """The warning at 75 % and 90 % of the included minutes, once per level and month, through the notifications. Never raises."""
    global QUOTA_ALERTS
    try:
        from github_actions_monitor.integrations import notifiers
        from github_actions_monitor.data_pipeline import quota
        QUOTA_ALERTS = QUOTA_ALERTS or quota.Alerts()
        info = quota_payload()
        if info["included_minutes"] and QUOTA_ALERTS.due(info["level"]) and not LITE["on"]:
            used = (info["billing"] or {}).get("minutes", info["month_estimate"])
            text = i18n.t("evt.quota_" + info["level"], used=used, included=info["included_minutes"], estimate=i18n.t("quota.estimate") if not info["billing"] else "")
            notifiers.notify(config, {"kind": "quota_" + info["level"], "code": "quota_" + info["level"], "level": "warn", "repo": "", "owner": "main", "url": None, "args": {}, "text": text})
            print(text, flush=True)
    except Exception as error:   # noqa: BLE001 - a quota calculation never stops the monitor
        degraded.note("quota", error)
        pass


RUN_COSTS = {}      # run id -> exact cost from the labels of its jobs (quota.job_costs); filled up to finops.jobs_per_cycle runs per cycle


def read_costs(config, data):
    """FinOps: reads the jobs of a few finished private runs and keeps what each really cost (the system of every job, larger runners included). Costs one call per run, limited by
    finops.jobs_per_cycle (0 = not read: the system of quota.default_runner is assumed)."""
    from github_actions_monitor.data_pipeline import quota
    limit = (config.get("finops") or {}).get("jobs_per_cycle", 0) if isinstance(config.get("finops"), dict) else 0
    if not isinstance(limit, int) or limit <= 0:
        return 0
    table, runner, done = quota.load(), quota.settings(config)["default_runner"], 0
    since = time.time() - 86400
    for run in data.get("runs") or []:
        if done >= limit:
            break
        when = parse_time(run.get("started"))
        if run.get("status") != "completed" or run["repo"] not in PRIVATE or run["id"] in RUN_COSTS or not when or when.timestamp() <= since:
            continue
        try:
            body = gh_read(f"repos/{toolconfig.github_owner(config)}/{run['repo']}/actions/runs/{run['id']}/jobs?per_page=100", retries=0)
        except Exception:   # noqa: BLE001 - this run keeps the assumed system
            RUN_COSTS[run["id"]] = None
            continue
        jobs = [{"seconds": seconds_between(parse_time(j.get("started_at")), parse_time(j.get("completed_at"))), "labels": j.get("labels")} for j in (body or {}).get("jobs") or []]
        RUN_COSTS[run["id"]] = quota.job_costs(jobs, table, runner)
        done += 1
    while len(RUN_COSTS) > 3000:
        RUN_COSTS.pop(next(iter(RUN_COSTS)))
    return done


def download_artifact(endpoint, destination):
    """Binary download of one artifact through `gh api` (the answer is a zip, so it is not decoded as text)."""
    done = subprocess.run(["gh", "api", endpoint], capture_output=True, timeout=300, **secretstore.gh_kwargs())
    if done.returncode != 0 or not done.stdout:
        raise RuntimeError("download failed")
    Path(destination).write_bytes(done.stdout)


def red_rows(data):
    """The red workflows of this cycle: those of the sentinel when it runs, else the same small rule the lite edition uses."""
    sentinel = SENTINEL["obj"]
    if sentinel is not None:
        try:
            return list(((sentinel.snapshot() or {}).get("a2") or {}).get("red") or [])
        except Exception as error:   # noqa: BLE001
            degraded.note("loop.extra", error)
            pass
    runs = data.get("runs") or []
    return redrule.red_workflows({r: [x for x in runs if x["repo"] == r] for r in (data.get("repos") or [])}, None, True)[0]


FEED_SYNC = {"at": 0.0}
FEED_LOCK = threading.RLock()


def refresh_feed(config=None, min_gap=2.0):
    """Rewrites the feed and the brief from the red workflows as they are NOW, so that they agree with what the Alerts tab shows (they used to follow one cycle behind). Called at every
    refresh of the alert centre and at every read of the feed; it does not call GitHub (a diagnosis is only fetched in the cycle) and does nothing while the data has not loaded."""
    data = STATE.get("data") or {}
    if not data or data.get("loading") or (data.get("offline") or {}).get("offline") or not (data.get("repos") or data.get("runs")):
        return None
    if time.time() - FEED_SYNC["at"] < min_gap or not FEED_LOCK.acquire(False):
        return None
    try:
        FEED_SYNC["at"] = time.time()
        return feed_alerts(config or toolconfig.raw_config(), data, diagnose=False)
    except Exception as error:   # noqa: BLE001 - reading the alerts never fails because the feed could not be written
        degraded.note("ai_alerts.refresh", error)
        return None
    finally:
        FEED_LOCK.release()


def panel_list(lang=None):
    """The panels of the Sentinel tab (A1..A13 and the second sentinel) as data: same levels as the page, with the rows somebody has to act on (sentinel_panels.py). [] while the sentinel is off or still loading."""
    sentinel = SENTINEL.get("obj")
    if LITE["on"] or sentinel is None:
        return []
    from github_actions_monitor.sentinels import sentinel_panels
    snapshot = sentinel.snapshot()
    if not snapshot or snapshot.get("enabled") is False or snapshot.get("loading") == "starting":
        return []
    registry = SENTINEL.get("registry")
    collab = registry.get("collab") if registry else None
    try:
        collab_alerts = collab.get_alerts() if collab is not None and getattr(collab, "enabled", False) else None
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
        collab_alerts = None
    code = lang or "en"
    return sentinel_panels.panels(snapshot, lambda key, **values: i18n.tl(code, key, **values), analytics=ANALYTICS.get("summary"), collab=collab_alerts, owner=toolconfig.github_owner())


def ai_state(lang=None, data=None, panels=None):
    """The document of `GET /api/ai/state`: every signal of the monitor (signals.py), the same in both editions; the lite one says which panels do not exist there."""
    from github_actions_monitor.data_pipeline import signals
    data = data if data is not None else (STATE.get("data") or {})
    if panels is None:
        try:
            panels = panel_list(lang)
        except Exception as error:   # noqa: BLE001
            degraded.note("ai_alerts.panels", error)
            panels = []
    age = None
    try:
        age = int(time.time() - parse_time(data.get("updated")).timestamp()) if data.get("updated") else None
    except Exception:   # noqa: BLE001
        age = None
    config = toolconfig.raw_config()
    warnings = []
    try:
        from github_actions_monitor.cli import doctor
        for name, check in (("timezone", doctor.time_zone(config)), ("risks", doctor.risks(config))):
            if check[0] != "ok":
                warnings.append(f"{name}: {check[1]}")
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
    swallowed = degraded.read(state_dir())[0] if hasattr(degraded, "read") else 0
    if swallowed:
        warnings.append(f"degraded: {swallowed} failure(s) swallowed on purpose")
    stale = age is not None and age > 3 * int(data.get("refresh_seconds") or 120) + 60
    central = None
    try:
        from github_actions_monitor.sentinels import central_source
        central = central_source.read(config, toolconfig.github_owner(config), workspace_root_text())
        if central.get("source") == "off":
            central = None
        elif central.get("ok") and central.get("stale"):
            warnings.append("central panel behind: not trusted")
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
    return signals.state(data, panels, "lite" if LITE["on"] else "complete", {"age_seconds": age, "stale": stale, "warnings": warnings, "working_mode": MODE.name, "auto_mode": bool(MODE.auto),
                                                                                "central": central}, version=TOOL_VERSION)


def ai_sections(data, panels):
    """The Markdown of "What to do now / Pending / Monitor health" for the brief."""
    try:
        from github_actions_monitor.data_pipeline import signals
        return signals.brief_sections(ai_state(data=data, panels=panels))
    except Exception as error:   # noqa: BLE001 - the brief never fails because of this block
        degraded.note("ai_alerts.panels", error)
        return ""


def feed_alerts(config, data, diagnose=True):
    """The local feed for AIs: complete edition only; a NEW real alert also reaches the notification channels you configured. With `diagnose` (the cycle) and ai_alerts.diagnose.enabled,
    the failing step and the last relevant lines of the log of a new red run are read (read only calls to `gh`). The same in both editions: the lite one has no panels, only its signals."""
    from github_actions_monitor.integrations import ai_alerts
    with FEED_LOCK:      # the cycle and a refresh of the alert centre never write the feed at the same time
        try:
            panels = panel_list()
        except Exception as error:   # noqa: BLE001 - the panels never stop the feed of the red workflows
            degraded.note("ai_alerts.panels", error)
            panels = None
        extra, sections = None, ""
        try:
            from github_actions_monitor.data_pipeline import signals
            doc = ai_state(data=data, panels=panels)
            extra, sections = signals.extra_alert_rows(doc), signals.brief_sections(doc)
        except Exception as error:   # noqa: BLE001 - the signals never stop the feed of the red workflows
            degraded.note("ai_alerts.panels", error)
        result = ai_alerts.update(config, red_rows(data), runner=ai_alerts.gh_runner if diagnose else None, owner=toolconfig.github_owner(config), panels=panels, sections=sections, extra_rows=extra,
                                  status=f"running, cycle complete ({len(data.get('repos') or [])} repositories read)")
    for alert in result["opened"]:
        if alert["class"] == "real":
            try:
                from github_actions_monitor.integrations import soundalert
                soundalert.beep(config, "new_red")      # only with sound.server_beep (off by default), for when the page is not open
            except Exception as error:   # noqa: BLE001
                degraded.note("loop.extra2", error)
            try:
                from github_actions_monitor.integrations import notifiers
                notifiers.notify(config, {"kind": "ai_alert", "code": "ai_alert", "level": "warn", "repo": alert["repo"], "owner": "main", "url": alert.get("url"), "args": {},
                                          "text": i18n.t("evt.ai_alert", repo=alert["repo"], workflow=alert["workflow"])})
            except Exception as error:   # noqa: BLE001
                degraded.note("loop.extra2", error)
                pass
            notice_ai(config, alert)
    return result


def notice_ai(config, alert):
    """The active notice to an external AI (ai_notify.py, OFF by default, confirmed per provider, capped by hour): sent from a thread of its own so that a slow provider never holds the cycle."""
    try:
        from github_actions_monitor.integrations import ai_notify
        if not ai_notify.settings(config)["enabled"]:
            return
        threading.Thread(target=ai_notify.notify, args=(config, dict(alert)), name="ai-notify", daemon=True).start()
    except Exception as error:   # noqa: BLE001 - a notice never stops the cycle
        degraded.note("ai_alerts.hook", error)


def maintain_extras(config, data):
    """The opt-in features that run after a cycle (each is OFF by default and costs nothing while off): exact costs, the local mirror of artifacts and the OpenTelemetry export."""
    if data.get("loading") or data["offline"]["offline"]:
        brief_status(config, "connection lost, the alerts below are from the last complete cycle" if data["offline"]["offline"] else f"running, reading repositories ({data.get('loading')}), the alerts below are from the last complete cycle")
        return
    remaining = (data.get("rate") or {}).get("remaining")
    spare = remaining is None or remaining > 2 * config.get("min_rate_remaining", 800)
    for name, job in (("ai_alerts", lambda: feed_alerts(config, data)),
                      ("finops", lambda: spare and read_costs(config, data)),
                      ("mirror", lambda: spare and __import__("github_actions_monitor.integrations.mirror", fromlist=["_"]).cycle(config, data.get("runs") or [], toolconfig.github_owner(config), lambda e: gh_read(e, retries=0), download_artifact)),
                      ("otlp", lambda: __import__("github_actions_monitor.integrations.otlp", fromlist=["_"]).export(config, data, TOOL_VERSION))):
        try:
            job()
            if name == "ai_alerts":
                WATCH.log_ok("brief")
        except Exception as error:   # noqa: BLE001 - an extra never stops the monitor; a problem is said once
            if name == "ai_alerts":      # the brief for the AI that cannot be written is shown, not silent
                WATCH.log_failed(error, "brief")
            if name not in EXTRAS_WARNED:
                EXTRAS_WARNED.append(name)
                print(name + ":", repr(error)[:160], flush=True)


def brief_status(config, status):
    """The brief of the AI feed says what the monitor is doing (a cycle in progress, the connection lost, a cycle that failed) so that it never shows the hour of an old cycle as if it were
    the last word. Best effort: it never stops the loop."""
    try:
        from github_actions_monitor.integrations import ai_alerts
        ai_alerts.monitor_status(config, status)
    except Exception as error:   # noqa: BLE001
        degraded.note("ai_alerts.refresh", error)


EXTRAS_WARNED = []
CONNECTION_WAS = {"lost": False}


def retention_tick(config):
    """The tick of maintenance of the retention: when it is due (once per `retention.interval_hours`) the events and the analytics older than their limits are removed or archived. The
    lite edition has no such job. A failure is counted and never stops the cycle."""
    if LITE["on"]:
        return
    try:
        from github_actions_monitor.storage import retention, runtime
        storage, account = runtime.process_storage(CHILD["account"] or None)
        retention.tick(storage, account, config)
    except Exception as error:   # noqa: BLE001 - housekeeping never stops the monitor
        degraded.note("retention", error)


def maintain(config, data):
    """After each cycle: the conditional-read cache is saved, a few completed runs have their jobs sampled and the analytics are refreshed."""
    quota_watch(config)
    try:      # the connection that goes down is announced once, by the same switch as a new red
        from github_actions_monitor.integrations import soundalert
        lost = bool((data.get("offline") or {}).get("offline"))
        if lost and not CONNECTION_WAS["lost"]:
            soundalert.beep(toolconfig.raw_config(), "connection_lost")
        CONNECTION_WAS["lost"] = lost
    except Exception as error:   # noqa: BLE001 - a sound never stops a cycle
        degraded.note("loop.extra2", error)
    maintain_extras(toolconfig.raw_config() if not LITE["on"] else config, data)
    retention_tick(toolconfig.raw_config() if not LITE["on"] else config)
    try:
        if ETAG["cache"]:
            ETAG["cache"].save()
        cfg = analytics.settings(config)
        store = ANALYTICS["store"]
        if store is None or not cfg["enabled"] or data.get("loading") or data["offline"]["offline"]:
            return
        for run in analytics.pending_runs(data.get("runs") or [], store, cfg["jobs_per_cycle"]):
            try:
                body = gh_read(f"repos/{toolconfig.github_owner()}/{run['repo']}/actions/runs/{run['id']}/jobs?per_page=30", retries=0)
            except Exception:   # noqa: BLE001 - a job list that cannot be read is skipped for good
                store.add_jobs(run["repo"], run["name"], run["id"], [], cfg["steps"])
                continue
            store.add_jobs(run["repo"], run["name"], run["id"], (body or {}).get("jobs") or [], cfg["steps"])
        ANALYTICS["summary"] = analytics.summary(data.get("runs") or [], store, cfg)
        ANALYTICS["at"] = time.time()
        store.save()
    except Exception as error:   # noqa: BLE001 - analytics never stop the monitor, but a problem is said once
        degraded.note("analytics", error)
        if not MAINTAIN_WARNED:
            MAINTAIN_WARNED.append(1)
            print("analytics:", repr(error)[:160], flush=True)


MAINTAIN_WARNED = []


def sleep_for(seconds, generation=None):
    """Sleeps in slices of one second and gives up early when this loop was replaced by a newer one (the watchdog restarted it)."""
    end = time.time() + seconds
    while time.time() < end:
        if not WATCH.current(generation):
            return
        time.sleep(min(1.0, max(0.0, end - time.time())))


def write_cycle_log(data):
    """One line of counts per cycle (never titles). A failure is not swallowed: the heartbeat keeps it and the page and the doctor show it."""
    try:
        with private_io.open_append(LOG_FILE) as log:
            log.write(tzdisplay.localize(f"{data['updated']} repos={len(data['repos'])} hot={data['hot']} refreshed={data['refreshed']} active={len(data['active'])} issues={len(data['issues'])} rate={data['rate']}\n"))
        WATCH.log_ok()
    except Exception as error:   # noqa: BLE001 - a log that cannot be written never stops the monitor, but it is said
        WATCH.log_failed(error)
        degraded.note("loop.log", error)


def run_cycle(config, generation):
    """One refresh cycle; returns the pause before the next one, or None when this loop was replaced meanwhile (nothing is published then)."""
    def publish(snapshot):
        if not WATCH.current(generation):
            return
        with LOCK:
            STATE["data"], STATE["error"], STATE["hint"] = snapshot, None, None
        from github_actions_monitor.util import banner
        print(banner.tag(LITE["on"]), i18n.t("mon.loaded", n=snapshot["loading"]), flush=True)

    WATCH.begin()
    try:      # the log says that a cycle began, so a long one is not mistaken for a monitor that stopped
        with private_io.open_append(LOG_FILE) as log:
            log.write(tzdisplay.localize(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} cycle=started\n"))
    except Exception as error:   # noqa: BLE001
        WATCH.log_failed(error)
    brief_status(toolconfig.raw_config() if not LITE["on"] else config, "running, a cycle has started, the alerts below are from the last complete cycle")
    data = collect(config, publish)
    if WATCH.current(generation):      # the finished picture goes to the page NOW: the box "loading repositories" must not wait for the upkeep that follows (it may be slow)
        with LOCK:
            STATE["data"], STATE["error"], STATE["hint"] = data, None, None
    WATCH.phase("maintain")
    transition = LINK.end_cycle()
    if transition:
        announce_link(transition, config)
    data["offline"] = LINK.state()
    data["etag"] = ETAG["cache"].stats() if ETAG["cache"] else None
    maintain(config, data)
    if not WATCH.current(generation):
        return None
    WATCH.phase("publish")
    with LOCK:
        STATE["data"], STATE["error"], STATE["hint"] = data, None, None
        STATE["complete"] = True
    WATCH.phase("log")
    write_cycle_log(data)
    WATCH.phase("extras")
    delay = tuned(config, "refresh_seconds", data)
    try:   # the report of the day goes to the audit folder (never stops the loop)
        if SENTINEL["obj"] is not None and AUTOSAVE is not None and not data.get("loading"):
            from github_actions_monitor.sentinels import sentinel_local
            AUTOSAVE.maybe(sentinel_local.AUDIT_DIR, SENTINEL["obj"].snapshot(), config.get("report_history_days", config.get("parte_history_days", 30)))
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.autosave", error)
    delay = quota_delay(data.get("rate"), config["min_rate_remaining"], delay)
    if time.time() < RATE_BLOCK["until"]:
        delay = max(delay, min(3900, int(RATE_BLOCK["until"] - time.time()) + 1))
    WATCH.ok()
    credential_ok(config)
    return delay


def loop(config, generation=None):
    generation = WATCH.generation if generation is None else generation
    while WATCH.current(generation):
        try:
            delay = run_cycle(config, generation)
            if delay is None:
                return
        except AuthError as error:
            if not WATCH.current(generation):
                return
            WATCH.fail(error)
            outcome = credential_refusal(error, config)
            with LOCK:
                STATE["error"], STATE["hint"] = str(error), "auth"   # the page writes the hint in its own language
            brief_status(toolconfig.raw_config() if not LITE["on"] else config, "running, but the last cycle failed to sign in to GitHub; the alerts below are from the last complete cycle")
            delay = CONFIRM_DELAY if outcome == "strike" else 60      # the first refusal is confirmed soon: one stray 401 must not hide a lost login for a whole minute
        except Exception as error:
            if not WATCH.current(generation):
                return
            WATCH.fail(error)
            outcome = credential_refusal(error, config)
            degraded.note("loop.cycle", error)
            with LOCK:
                STATE["error"] = str(error)
            brief_status(toolconfig.raw_config() if not LITE["on"] else config, f"running, but the last cycle failed ({type(error).__name__}); the alerts below are from the last complete cycle")
            delay = CONFIRM_DELAY if outcome == "strike" else 60
        sleep_for(delay, generation)


def start_loop(config):
    """Starts a refresh loop in its own thread (a new generation: an older one that wakes up later leaves without publishing). Returns the thread."""
    generation = WATCH.new_generation()
    thread = threading.Thread(target=loop, args=(config, generation), daemon=True, name=f"refresh-loop-{generation}")
    LOOP["thread"] = thread
    thread.start()
    return thread


LOOP = {"thread": None}
SUPERVISOR_KEY_ENV = "MONITOR_SUPERVISOR_KEY"        # given by the supervisor to the process of each account: the proof that a request to change the login comes from it
SUPERVISOR_KEY_HEADER = "X-Monitor-Supervisor"
REMOTE_HEADER = "X-Monitor-Remote"                   # the supervisor adds "1" when the person is not at this computer; a child that was not started by it ignores it


def watchdog_restart(config, reason):
    """The traceback of every thread goes to the log (where the cycle hangs) and the loop starts again in a new thread. Returns the new thread."""
    try:
        with private_io.open_append(LOG_FILE) as log:
            log.write(tzdisplay.localize(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} WATCHDOG {reason} phase={WATCH.phase_name} running={WATCH.running_seconds()}s: threads follow\n"))
            log.flush()
            cycle_watch.dump_stacks(log)
    except Exception as error:   # noqa: BLE001
        WATCH.log_failed(error)
    print(i18n.t("mon.watchdog_restart", reason=reason, phase=WATCH.phase_name), flush=True)
    WATCH.restarts += 1
    WATCH.fail(f"{reason} in phase {WATCH.phase_name}")
    return start_loop(config)


def watchdog_limit(config):
    try:
        return max(0, int((LIVE_CONFIG or config).get("watchdog_minutes", 10))) * 60
    except (TypeError, ValueError):
        return 600


def watchdog_once(config):
    """One look of the watchdog: restarts the loop when a cycle runs longer than `watchdog_minutes` or its thread is gone. Returns "", "stuck" or "dead"."""
    thread = LOOP["thread"]
    verdict = cycle_watch.check(WATCH, watchdog_limit(config), thread is not None and thread.is_alive())
    if verdict:
        watchdog_restart(config, verdict)
    return verdict


def watchdog_loop(config, every=30):
    while True:
        time.sleep(every)
        try:
            watchdog_once(config)
        except Exception as error:   # noqa: BLE001 - the watchdog never stops
            degraded.note("loop.watchdog", error)


HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,100}$")


class QuietServer(ThreadingHTTPServer):
    """The server of the monitor: a client that disconnects is not an error worth a traceback; any other error is still shown."""

    tls_context = None

    def get_request(self):
        sock, address = super().get_request()
        if self.tls_context is not None:
            sock = self.tls_context.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)
            sock.settimeout(20)
        return sock, address

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], CLIENT_GONE):
            DISCONNECTS[0] += 1
            return
        super().handle_error(request, client_address)


def webhook_settle(repo):
    """After an accepted event: the conditional-read entries of the repository are dropped (the next read is a full one, never a stale 304) and the repository is read again in
    the next cycle, which reconciles whatever the live event changed."""
    cache = ETAG.get("cache")
    if cache is not None:
        cache.invalidate(repo)
    if repo in RUN_CACHE:
        RUN_CACHE[repo]["at"] = 0


def github_host():
    """The GitHub host the links of the page point to: the GH_HOST of the environment (GitHub Enterprise Server) when it is a plain host name, else github.com. `gh` itself reads GH_HOST."""
    host = os.environ.get("GH_HOST", "")
    return host if HOST_RE.match(host) else "github.com"


def render_page():
    """actions_monitor.html with the catalogues of the interface (keys "ui.*") for the 8 languages and the default language inlined."""
    page = (paths.STATIC / "actions_monitor.html").read_text(encoding="utf-8")
    data = {"default": i18n.language(), "langs": list(i18n.LANGS), "names": i18n.NATIVE_NAMES, "html": i18n.HTML_LANG, "locale": i18n.BROWSER_LOCALE, "catalogues": i18n.ui_catalogues(),
            "ecosystems": {**{"other": i18n.t("ui.eco_other")}, **{key: item["label"] for key, item in toolconfig.ecosystems().items()}}, "owner": toolconfig.github_owner(), "tz": tzdisplay.setting(), "blink": (toolconfig.raw_config().get("display") or {}).get("blink_red_tiles", True) is not False, "sound": {k: v for k, v in __import__("github_actions_monitor.integrations.soundalert", fromlist=["_"]).settings(toolconfig.raw_config()).items() if k != "server_beep"}, "host": github_host(), "lite": LITE["on"], "network": localguard.public_state(), "version": TOOL_VERSION, "author": AUTHOR, "license": LICENSE_ID}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return page.replace("/*I18N_DATA*/null", blob, 1)


DISCONNECTS = [0]     # requests whose browser went away before the answer was sent (counted in /metrics, never printed)
CLIENT_GONE = (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)
DRAIN_MAX = 1_048_576  # the most of an unread body that is read and dropped after an answer (see Handler.drain_body)
DRAIN_WAIT = 2.0       # seconds to wait for the rest of it


class CountedReader:
    """The input of a request, counting what the handlers read, so that what is left can be dropped after the answer."""

    def __init__(self, stream):
        self.stream, self.count = stream, 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.count += len(data)
        return data

    def __getattr__(self, name):
        return getattr(self.stream, name)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def handle(self):
        """A browser that closes or reloads its tab while the page is being sent is normal: it is counted, not printed. A real error still reaches the server's handle_error."""
        try:
            super().handle()
        except CLIENT_GONE:
            DISCONNECTS[0] += 1

    def finish(self):
        try:
            super().finish()
        except CLIENT_GONE:
            DISCONNECTS[0] += 1

    def end_headers(self):
        """Every answer: the page cannot be put in a frame of another site (clickjacking) and the browser does not guess a type."""
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        if getattr(self, "deprecated_access", False):
            self.send_header("Deprecation", "true")      # the ?access= address is deprecated: POST /api/access keeps the token out of the address bar
        super().end_headers()

    def reply(self, body, kind):
        payload = body.encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        except CLIENT_GONE:
            DISCONNECTS[0] += 1

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

    def ai_stream(self):
        """GET /api/ai/stream[?only=real]: `text/event-stream` with a `hello` frame (how many real alerts are open), then one `alert` frame per event of the feed and a keep-alive comment. It resumes
        from the `Last-Event-ID` header or `?since=`. Read only; the network mode asks for the access token as for every other request; a limited number of listeners, each for a limited time."""
        from github_actions_monitor.integrations import ai_alerts
        from urllib.parse import parse_qs
        config = toolconfig.raw_config()
        cfg = ai_alerts.settings(config)
        if not cfg["enabled"] or not cfg["stream"]["enabled"]:
            self.json_reply({"error": "stream off"}, 404)
            return
        if not ai_alerts.stream_acquire(config):
            self.json_reply({"error": "too many listeners"}, 429)
            return
        ask = parse_qs(self.path.partition("?")[2])
        resume = self.headers.get("Last-Event-ID") or (ask.get("since") or [""])[0]
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            for frame in ai_alerts.stream_frames(config, offset=int(resume) if str(resume).isdigit() else None,
                                                 only_real=(ask.get("only") or [""])[0] == "real"):
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except (ConnectionError, OSError):
            DISCONNECTS[0] += 1      # the listener went away: nothing to report
        except (ValueError, TypeError) as error:      # a frame that cannot be written ends this listener, never the server
            degraded.note("ai.stream", error)
        finally:
            ai_alerts.stream_release()

    local_door = False      # True only on the second, loopback-only port (listen.local_port): the way in of the person at this computer when a reverse proxy is declared

    def request_ok(self):
        return localguard.local_request_ok(self.headers, self.server.server_address[1], door=self.local_door)

    def is_local(self):
        """True when this request really comes from a person at this computer (see localguard.is_this_computer)."""
        return not self.remote_through_supervisor() and localguard.is_this_computer(self.client_address, self.headers, door=self.local_door)

    def guard(self):
        if self.request_ok():
            return True
        self.json_reply({"error": "forbidden"}, 403)
        return False

    def access_gate(self):
        """Network mode only: every request must prove the access token (cookie, header or `?access=` on the first visit, which sets the cookie and goes to the clean address)."""
        self.deprecated_access = False
        if not localguard.STATE["network"] or self.path.split("?")[0] == "/api/webhook":      # the webhook has its own proof (the HMAC of GitHub)
            return True
        if self.command == "POST" and self.path.split("?")[0] == "/api/access":      # the one-use post that opens the session: it checks the token itself (handle_post)
            return True
        if not self.request_ok():
            self.json_reply({"error": "forbidden"}, 403)
            return False
        from urllib.parse import parse_qs
        query_token = (parse_qs(self.path.partition("?")[2]).get("access") or [""])[0]
        if query_token and not localguard.query_token_counts(self.command, self.path, LIVE_CONFIG or DEFAULTS):      # deprecated: only the first visit of a page, and only while listen.query_access is on
            query_token = ""
        peer = localguard.client_key(self.client_address, self.headers)
        if not self.is_local() and localguard.is_locked_out(self.client_address, self.headers):      # the lock is looked at FIRST for every address that is not this computer: a locked address cannot keep guessing, not even with the right token
            self.json_reply({"error": "locked"}, 429)
            return False
        if not localguard.access_ok(self.headers, query_token):      # the person at this computer is never locked out of their own monitor; a shared proxy address is told apart with listen.trusted_proxy
            localguard.note_failure(peer, localguard.max_failed(LIVE_CONFIG or DEFAULTS))
            localguard.note_proxy_failure(self.client_address, self.headers, localguard.max_failed(LIVE_CONFIG or DEFAULTS))
            self.json_reply({"error": "access"}, 401)
            return False
        self.deprecated_access = bool(query_token) and not localguard.presented(self.headers)      # the token came in the address: every answer says that way is deprecated
        if query_token and self.command == "GET" and "text/html" in (self.headers.get("Accept") or "text/html"):
            self.send_response(302)
            self.send_header("Set-Cookie", localguard.cookie_header(query_token, secure=False if self.local_door else None))
            self.send_header("Referrer-Policy", "no-referrer")       # the clean address follows at once: the token must not travel on in a Referer header
            self.send_header("Cache-Control", "no-store")
            self.send_header("Location", self.path.split("?")[0])
            self.end_headers()
            return False
        return True

    def open_session(self):
        """POST /api/access {"token": "..."}: the access token travels in the body, so it never sits in an address bar, a history or a log. Same checks as every other request (Host, Origin,
        lock-out of an address after too many wrong tokens, constant-time comparison); on success the cookie of the session is set. Without the network mode there is nothing to open."""
        if not localguard.STATE["network"]:
            self.json_reply({"ok": False, "error": "not_network"}, 404)
            return
        if not self.request_ok():
            self.json_reply({"error": "forbidden"}, 403)
            return
        peer = localguard.client_key(self.client_address, self.headers)
        if not self.is_local() and localguard.is_locked_out(self.client_address, self.headers):      # the same rule as every other request (access_gate)
            self.json_reply({"error": "locked"}, 429)
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            if "application/json" not in (self.headers.get("Content-Type") or "").lower() or not 0 < size <= 512:
                raise ValueError("shape")
            body = json.loads(self.rfile.read(size))
            candidate = body.get("token") if isinstance(body, dict) else None
            if not isinstance(candidate, str) or not candidate or len(candidate) > 200:
                raise ValueError("token")
        except (ValueError, TypeError, OSError):
            self.json_reply({"ok": False, "error": "request"}, 400)
            return
        if not localguard.access_ok({}, candidate):
            localguard.note_failure(peer, localguard.max_failed(LIVE_CONFIG or DEFAULTS))
            localguard.note_proxy_failure(self.client_address, self.headers, localguard.max_failed(LIVE_CONFIG or DEFAULTS))
            self.json_reply({"error": "access"}, 401)
            return
        body = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Set-Cookie", localguard.cookie_header(candidate, secure=False if self.local_door else None))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def credential_post(self):
        """POST /api/credential {"action": "replace", "token": "..."} | {"action": "reload"}. In the monitor of one account it is only for the supervisor (it proves itself with the key it gave this process at
        start; the supervisor already asked for an administrator or for this computer); in a monitor on its own the person must be at this computer (and have the one-use token of the page). The token
        is checked against GitHub before it is kept and is never repeated in the answer."""
        key = os.environ.get(SUPERVISOR_KEY_ENV, "")
        if CHILD["account"]:
            import hmac
            if not key or not hmac.compare_digest(key.encode(), (self.headers.get(SUPERVISOR_KEY_HEADER) or "").encode()):
                self.json_reply({"ok": False, "status": "forbidden"}, 403)
                return
        elif not self.token_ok():
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            request = json.loads(self.rfile.read(size) if 0 < size <= 1024 else b"{}")
            request = request if isinstance(request, dict) else {}
            ok, status, info = credential_change(str(request.get("action") or ""), request.get("token") or "")
        except (ValueError, OSError):
            self.json_reply({"ok": False, "status": "request"}, 400)
            return
        self.json_reply({"ok": ok, "status": status, "credential": info}, 200 if ok else (400 if status in ("format", "request") else 422))

    def remote_through_supervisor(self):
        """True when the supervisor says the person is not at this computer (the network mode of the supervisor): this process then treats the request like a remote one."""
        return bool(os.environ.get(auth_http.CHILD_ENV)) and self.headers.get(REMOTE_HEADER) == "1"

    def this_computer(self):
        """Keys and actions that decide exposure or reach GitHub can only be changed from the same computer while the network mode is on (a 403 otherwise)."""
        if self.remote_through_supervisor():
            self.json_reply({"ok": False, "errors": {"_": "local_only"}}, 403)
            return False
        if not localguard.STATE["network"] or self.is_local():
            return True
        self.json_reply({"ok": False, "errors": {"_": "local_only"}}, 403)
        return False

    def request_language(self):
        """The language asked for with ?lang=xx (the page and read_report.py send it), else None = the configured one."""
        from urllib.parse import parse_qs
        found = parse_qs(self.path.partition("?")[2]).get("lang")
        return found[0] if found else None

    def token_ok(self):
        """True when no token is needed or the request carries a valid one-use token (header X-Monitor-Token); else answers 403 and returns False."""
        if not token_required() or SESSION.use(self.headers.get("X-Monitor-Token")):
            return True
        self.json_reply({"ok": False, "errors": {"_": "token"}}, 403)
        return False

    def drain_body(self, counted):
        """Reads and drops what the client sent and nobody read (a request refused with 403, 404 or 413 before its body was looked at). Closing a connection that still has unread data makes
        Windows (and sometimes Linux) send a reset, and the client then loses the answer it was owed: it saw `ConnectionAbortedError` instead of the 403. A cap and a short wait keep it harmless."""
        try:
            left = min(int(self.headers.get("Content-Length") or 0), DRAIN_MAX) - counted.count
        except ValueError:
            return
        if left <= 0:
            return
        try:
            self.connection.settimeout(DRAIN_WAIT)
            while left > 0:
                chunk = counted.read(min(left, 65536))
                if not chunk:
                    break
                left -= len(chunk)
        except OSError:
            pass

    def do_POST(self):
        counted = CountedReader(self.rfile)
        self.rfile = counted
        try:
            if not self.access_gate() or not auth_http.gate(self, LIVE_CONFIG or DEFAULTS, LITE["on"]):
                return
            with i18n.use_language(self.request_language()):
                self.handle_post()
        finally:
            self.drain_body(counted)

    def handle_post(self):
        path = self.path.split("?")[0]
        if LITE["on"] and path.startswith(LITE_PATHS) and path not in LITE_SHARED:
            self.send_response(404)
            self.end_headers()
            return
        if path == "/api/access":      # network mode: open the session with the access token in the BODY (never in the address); the cookie comes back and the token is not repeated
            self.open_session()
            return
        if path == "/api/credential":      # replace the login of this account, or read its files again, without a restart (complete edition)
            if not self.guard() or not self.this_computer():
                return
            self.credential_post()
            return
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
            from github_actions_monitor.security import webhook
            if localguard.STATE["network"] and localguard.over_rate("webhook", str(self.client_address[0]), 120):      # one address cannot flood the receiver
                self.json_reply({"ok": False, "error": "rate"}, 429)
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(size) if 0 <= size <= webhook.MAX_BODY else b"x" * (webhook.MAX_BODY + 1)
                code, answer, repo = webhook.handle(LIVE_CONFIG or DEFAULTS, body, self.headers, STATE["data"]["repos"] if STATE.get("data") else [])
                webhook_count(code, bool(answer.get("duplicate")) if isinstance(answer, dict) else False)
                record = webhook.parse_event(self.headers.get("X-GitHub-Event"), body) if (code == 200 and repo) else None
                if record and webhook.live_settings(LIVE_CONFIG or DEFAULTS)["record_events"]:
                    apply_live_event(record, LIVE_CONFIG or DEFAULTS)
                if repo:
                    webhook_settle(repo)
                self.json_reply(answer, code)
            except Exception:
                self.json_reply({"ok": False}, 400)
            return
        if path == "/api/mode":      # change the working mode: a local setting, with the one-use token
            if not self.guard() or not self.token_ok():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 512 else b"{}")
                request = request if isinstance(request, dict) else {}
                remaining, limit = mode_remaining()
                config = LIVE_CONFIG or DEFAULTS
                minutes = request.get("minutes", modes.settings(config)["default_minutes"])
                ok, why = MODE.set(request.get("mode"), minutes, config, limit, remaining)
                if ok:
                    RUN_CACHE_RESET()
                    print(banner_mode_line(MODE.name, f"({minutes} min)" if MODE.until else ""), flush=True)
                self.json_reply({"ok": ok, "reason": why, **mode_payload()}, 200 if ok else 400)
            except (ValueError, OSError):
                self.json_reply({"ok": False, "reason": "request"}, 400)
            return
        if path == "/api/sentinel/parte/save":      # a copy of the daily report in the audit folder: a POST with the one-use token (a GET never writes)
            if not self.guard() or not self.token_ok():
                return
            sentinel = SENTINEL["obj"]
            if sentinel is None or LITE["on"]:
                self.json_reply({"ok": False, "reason": "off"}, 404)
                return
            from github_actions_monitor.data_pipeline import report_history
            from github_actions_monitor.sentinels import sentinel_local
            try:
                body = report_history.parte_text(sentinel.snapshot()).encode("utf-8")
                folder = sentinel_local.AUDIT_DIR
                if not folder.is_dir():
                    self.json_reply({"ok": False, "reason": "no_folder"}, 400)
                    return
                name = "SENTINEL_REPORT_" + time.strftime("%Y-%m-%d_%H%M") + ".txt"
                (folder / name).write_bytes(body)
                self.json_reply({"ok": True, "file": name})
            except Exception:
                self.json_reply({"ok": False, "reason": "write"}, 500)
            return
        if path == "/api/discovery/group":      # the user confirmed a suggested group: it is added to the ecosystems file (with a copy of it)
            if not self.guard() or not self.token_ok():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 1024 else b"{}")
                request = request if isinstance(request, dict) else {}
                chosen = [g for g in DISCOVERY["suggestions"] if g["key"] == request.get("key") and g["prefix"] == request.get("prefix")]
                if not chosen:
                    self.json_reply({"ok": False, "error": "unknown"}, 400)
                    return
                target = toolconfig._data_path("MONITOR_ECOSYSTEMS_FILE", "ecosystems_file", toolconfig.DEFAULT_ECOSYSTEMS_FILE)
                if target.stem.endswith(".example"):
                    target = paths.place(target.name.replace(".example", ""))   # the neutral template travels in assets/examples; the file of the person goes in config/
                result = discovery.add_group(target, chosen[0]["key"], chosen[0]["prefix"], example=paths.EXAMPLES / "ecosystems.example.json")
                if result["ok"]:
                    toolconfig.forget()
                    DISCOVERED["at"] = 0.0
                    DISCOVERY["suggestions"] = [g for g in DISCOVERY["suggestions"] if g["key"] != chosen[0]["key"]]
                self.json_reply(result, 200 if result["ok"] else 400)
            except (ValueError, OSError):
                self.json_reply({"ok": False, "error": "request"}, 400)
            return
        if path in ("/api/ai/actions/confirm", "/api/ai/actions/unlock", "/api/ai/test", "/api/notify/test"):   # one request, one explicit person: local only, small JSON body
            if not self.guard() or not self.this_computer() or not self.token_ok():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 4096 else b"{}")
                request = request if isinstance(request, dict) else {}
                self.json_reply(handle_action_post(path, request), 200)
            except Exception as error:   # noqa: BLE001
                self.json_reply({"ok": False, "error": str(error)[:200]}, 400)
            return
        if path in ("/api/gh-action/plan", "/api/gh-action/confirm", "/api/act/plan", "/api/act/confirm", "/api/act/stop", "/api/github-token", "/api/welcome", "/api/ai/ack", "/api/alerts/mute", "/api/alerts/unmute"):
            if not self.guard() or not self.this_computer():
                return
            if path != "/api/welcome" and path != "/api/gh-action/plan" and path != "/api/act/plan" and not self.token_ok():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 2048 else b"{}")
                self.json_reply(handle_advanced_post(path, request if isinstance(request, dict) else {}, auth_http.acting_user(self)))
            except Exception:   # noqa: BLE001 - the answer never repeats the request: it could hold a token
                self.json_reply({"ok": False, "status": "request"}, 400)
            return
        if path == "/api/settings":   # the settings menu: whitelisted keys only, checked, backed up and written atomically (settings_api.py); local request only
            if not self.guard() or not self.token_ok():
                return
            from github_actions_monitor.app import settings_api
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
                if (localguard.STATE["network"] or self.remote_through_supervisor()) and not self.is_local() and isinstance(changes, dict) and any(localguard.local_only_key(k) for k in changes):
                    self.json_reply({"ok": False, "errors": {"_": "local_only"}}, 403)
                    return
                result = settings_api.apply(changes, CONFIG_FILE, lite=LITE["on"])
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
        if not self.access_gate() or not auth_http.gate(self, LIVE_CONFIG or DEFAULTS, LITE["on"]):
            return
        with i18n.use_language(self.request_language()):
            self.handle_get()

    def handle_get(self):
        path = self.path.split("?")[0]
        if LITE["on"] and path.startswith(LITE_PATHS) and path not in LITE_SHARED:      # the lite product does not have these endpoints
            self.send_response(404)
            self.end_headers()
            return
        if path == "/api/sentinel/parte.txt":   # the same text as the daily report, to copy or download
            if not self.guard():
                return
            sentinel = SENTINEL["obj"]
            from github_actions_monitor.data_pipeline import report_history
            markdown = "fmt=md" in self.path.partition("?")[2].split("&")
            try:
                snap = sentinel.snapshot() if sentinel else None
                body = (report_history.parte_markdown(snap) if markdown else report_history.parte_text(snap)).encode("utf-8")
            except Exception as error:
                body = (i18n.t("mon.sentinel_failed", error=error) + chr(10)).encode("utf-8")
            # a GET only reads: the copy in the audit folder is a POST of its own (below), with the one-use token
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
                from github_actions_monitor.data_pipeline import report_history
                from github_actions_monitor.sentinels import sentinel_local
                sentinel = SENTINEL["obj"]
                self.json_reply({"data": report_history.yesterday_vs_today(sentinel_local.AUDIT_DIR, sentinel.snapshot()) if sentinel else None, "error": None if sentinel else i18n.t("mon.sentinel_unavailable")})
            except Exception as error:
                self.json_reply({"data": None, "error": i18n.t("mon.history_failed", error=error)})
            return
        if path == "/api/sentinel/collab":      # the issues and pull requests that need a person (the Collab sentinel; off by default; read only)
            if not self.guard():
                return
            collab = (SENTINEL["registry"].get("collab") if SENTINEL["registry"] else None)
            try:
                self.json_reply({"data": collab.snapshot() if collab else None, "error": SENTINEL["error"] or (None if collab else i18n.t("mon.sentinel_not_loaded"))})
            except Exception as error:      # shown as a notice in the tab
                self.json_reply({"data": None, "error": i18n.t("mon.sentinel_failed", error=error)})
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
            from github_actions_monitor.app import settings_api
            self.json_reply({"ok": True, **settings_api.describe(CONFIG_FILE, lite=LITE["on"], remote=(localguard.STATE["network"] or self.remote_through_supervisor()) and not self.is_local()), "restart_pending": sorted(RESTART_PENDING)})
        elif path == "/metrics" or path.startswith("/api/outputs/"):   # optional outputs, off unless switched on (outputs.py); local request only, no quota used
            if not self.guard():
                return
            from github_actions_monitor.integrations import outputs
            from github_actions_monitor.app import settings_api
            cfg = toolconfig.raw_config()
            sentinel = SENTINEL["obj"]
            try:
                snapshot = sentinel.snapshot() if sentinel else None
            except Exception:
                snapshot = None
            with LOCK:
                data = STATE["data"]
            if path == "/metrics" and settings_api.output_enabled(cfg, "prometheus"):
                self.reply(outputs.metrics_text(snapshot, data, per_repo=settings_api.output_enabled(cfg, "prometheus", "per_repo"), extra=metrics_extra()), outputs.CONTENT_TYPE)
            elif path == "/api/outputs/grafana.json" and settings_api.output_enabled(cfg, "json"):
                self.json_reply(outputs.grafana_json(snapshot, data, metrics_extra()))
            elif path == "/api/outputs/dashboard.json" and settings_api.output_enabled(cfg, "dashboard"):
                document = outputs.dashboard_json(snapshot)
                if document is None:
                    self.json_reply({"error": "not ready"}, 503)
                else:
                    self.json_reply(document)
            else:
                self.send_response(404)
                self.end_headers()
        elif path == "/api/health":   # for a service manager or a container check: local only, no GitHub call
            if not self.guard():
                return
            payload, code = health_reply("deep=1" in self.path.partition("?")[2].split("&"))
            self.json_reply(payload, code)
        elif path == "/api/paths":      # where everything is: the folders in use and what is still next to the launchers; no secret
            if not self.guard():
                return
            from github_actions_monitor.integrations import ai_index
            self.json_reply(ai_index.paths_report("lite" if LITE["on"] else "complete"))
        elif path == "/api/about":      # the About panel: versions, links, files, health, credits, the update notice; no secret and no repository name
            if not self.guard():
                return
            self.json_reply(about_payload())
        elif path == "/api/help/topics":
            if not self.guard():
                return
            from github_actions_monitor.ui import helpdocs
            from urllib.parse import parse_qs
            tab = (parse_qs(self.path.partition("?")[2]).get("tab") or [""])[0]
            self.json_reply({"topics": helpdocs.topics(i18n.language()), "tab_topic": helpdocs.tab_topic(tab) if tab else None, "lang": i18n.language()})
        elif path in ("/api/help/topic", "/api/help/search"):
            if not self.guard():
                return
            from github_actions_monitor.ui import helpdocs
            from urllib.parse import parse_qs
            query = parse_qs(self.path.partition("?")[2])
            if path.endswith("search"):
                self.json_reply({"hits": helpdocs.search((query.get("q") or [""])[0][:100], i18n.language())})
            else:
                found = helpdocs.topic(((query.get("id") or [""])[0])[:40], i18n.language())
                if found is None:
                    self.json_reply({"error": "unknown topic"}, 404)
                else:
                    self.json_reply(found)
        elif path == "/api/quota-pool/status":      # this computer only: the allowance of every source of the reads and what the App lacks (never a key or a token)
            if not self.guard() or not self.this_computer():
                return
            self.json_reply(pool_status())
        elif path == "/api/github-app/status":      # this computer only: asks the App for a token and says its name, installation, permissions and allowance (never the key or the token)
            if not self.guard() or not self.this_computer():
                return
            from github_actions_monitor.integrations import github_app
            self.json_reply(github_app.status(LIVE_CONFIG or toolconfig.raw_config()))
        elif path == "/api/ai/state":      # read only, versioned: everything the monitor says, as signals (signals.py); the same in the lite and the complete edition
            if not self.guard():
                return
            query = self.path.partition("?")[2].split("&")
            lang = next((q[5:] for q in query if q.startswith("lang=") and q[5:] in i18n.LANGS), "en")
            self.json_reply(ai_state(lang))
        elif path == "/api/ai/stream":      # server-sent events, read only: the alerts as they open and resolve (ai_alerts.stream, off by default)
            if not self.guard():
                return
            self.ai_stream()
        elif path in ("/api/ai/brief", "/api/ai/alerts"):
            if not self.guard():
                return
            refresh_feed()
            answer = advanced_get(path, self.path.partition("?")[2])
            __import__("github_actions_monitor.integrations.ai_alerts", fromlist=["_"]).touch(toolconfig.raw_config(), "endpoint", self.headers.get("User-Agent") or "")
            if path == "/api/ai/brief" and "fmt=json" not in self.path:
                self.reply(answer["brief"], "text/markdown; charset=utf-8")
            else:
                self.json_reply(answer)
        elif path in ("/api/act/status", "/api/github-token", "/api/runners", "/api/mirror", "/api/otlp", "/api/welcome", "/api/advanced"):
            if not self.guard():
                return
            self.json_reply(advanced_get(path, self.path.partition("?")[2]))
        elif path == "/api/session-token":      # a one-use token for the next change of a setting (the page asks for it right before it writes)
            if not self.guard():
                return
            self.json_reply({"required": token_required(), "token": SESSION.issue() if token_required() else ""})
        elif path == "/api/discovery":
            if not self.guard():
                return
            self.json_reply(discovery_payload())
        elif path == "/api/mode":      # the working mode, the estimate of each mode and the time left
            if not self.guard():
                return
            self.json_reply(mode_payload())
        elif path == "/api/quota":      # plan, billable minutes (an estimate unless the billing report is on), API allowance, concurrency, long jobs
            if not self.guard():
                return
            self.json_reply(quota_payload())
        elif path == "/api/sentinel/panels":      # read only: the panels A1..A13 and the second sentinel as data (level, one line, rows to act on), for tools that do not look at the page
            if not self.guard():
                return
            query = self.path.partition("?")[2].split("&")
            lang = next((q[5:] for q in query if q.startswith("lang=") and q[5:] in i18n.LANGS), "en")
            try:
                panels = panel_list(lang)
                self.json_reply({"data": {"panels": panels, "act": sum(1 for p in panels if p["level"] == "bad"), "watch": sum(1 for p in panels if p["level"] == "warn")}, "error": None})
            except Exception as error:   # noqa: BLE001
                self.json_reply({"data": {"panels": [], "act": 0, "watch": 0}, "error": str(error)[:200]})
        elif path == "/api/analytics":
            if not self.guard():
                return
            self.json_reply(ANALYTICS["summary"] or {"enabled": ANALYTICS["store"] is not None, "duration": [], "queue": [], "steps": [], "flaky": [], "slower": []})
        elif path == "/api/statusbar":      # what the bar at the foot of the page shows about this monitor: edition, address, account, sentinels (no secret, no GitHub call)
            if not self.guard():
                return
            refresh_feed()      # the bar polls every 30 seconds: the feed follows the sentinel without waiting for a cycle
            self.json_reply(statusbar_payload(self.server.server_address[1], (not localguard.STATE["network"] and not self.remote_through_supervisor()) or self.is_local()))
        elif path in ("/api/alerts", "/api/events"):      # one list of the alerts of every sentinel, and the events of the feed (1.7.3; read only; the account comes from ?account= or the process)
            if not self.guard():
                return
            from urllib.parse import parse_qs
            ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            if path == "/api/events":
                from github_actions_monitor.sentinels import alert_center
                from github_actions_monitor.data_pipeline import events as events_mod
                rows = alert_center.read_events(events_mod.EVENTS_FILE, ask.get("sentinel", ""), ask.get("since", ""), min(500, int(ask["limit"])) if str(ask.get("limit", "")).isdigit() else 200)
                self.json_reply({"schema": 1, "account": CHILD["account"] or None, "events": rows})
            else:
                self.json_reply(alerts_payload(ask))
        elif path == "/api/live-events":
            if not self.guard():
                return
            self.json_reply({"events": list(reversed(LIVE_EVENTS))})
        elif path == "/api/live-status":      # the receiver of webhooks as the Live view shows it: on or off, never the secret
            if not self.guard():
                return
            self.json_reply(webhook_status(LIVE_CONFIG or DEFAULTS))
        elif path == "/api/ai/actions":
            if not self.guard():
                return
            from github_actions_monitor.integrations import ai_actions
            from github_actions_monitor.sentinels import sentinel_ai
            sentinel = SENTINEL["obj"]
            self.json_reply({"state": ai_actions.ACTIONS.state(toolconfig.raw_config()), "log": ai_actions.ACTIONS.log(),
                             "ai": sentinel_ai.status(sentinel.ai_cfg, sentinel.ai_store) if sentinel is not None and sentinel.ai_cfg["provider"] != "none" else None})
        elif path.startswith("/api/data"):
            if not self.guard():
                return
            with LOCK:      # only the references are taken under the lock: writing to a slow or dead connection with the lock held froze every other page and the cycle itself
                picture = {"data": STATE["data"], "error": STATE["error"], "hint": STATE["hint"]}
            picture = {**picture, "loop": WATCH.snapshot(limit_seconds=watchdog_limit(LIVE_CONFIG or DEFAULTS))}
            self.reply(json.dumps(picture), "application/json; charset=utf-8")
        elif path in ("/", "/index.html"):
            if not self.guard():      # the page checks the Host like the API does (a rebinding page gets a 403, not the monitor)
                return
            self.reply(render_page(), "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()


class LocalDoorHandler(Handler):
    """The same page on the second port (`listen.local_port`), bound to loopback only: the way in of the person at this computer when a reverse proxy is declared, because behind a proxy
    nothing that arrives on the main port counts as "this computer"."""

    local_door = True


def lan_address():
    """The address of this computer on the local network, found without sending a packet (a UDP socket only chooses a route); 127.0.0.1 when there is none."""
    import socket
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def statusbar_payload(port, client_local=True):
    """GET /api/statusbar: the facts of the bar at the foot of the page that the data of GitHub does not carry. In the network mode the address of this computer on the local network
    (`lan_address`) is only given to a client on this same computer: a client of the network already knows the address it used and the map of the network is not handed out."""
    registry = SENTINEL["registry"]
    figures = (STATE.get("data") or {}).get("figures") or {}
    sentinels = []
    if registry is not None:
        for name in registry.names():
            try:
                item = registry.get(name)
                status = item.get_status() if item is not None else {}
            except Exception:       # noqa: BLE001 - the bar must always answer
                status = {}
            sentinels.append({"name": name, "enabled": bool(status.get("enabled", True)), "level": status.get("level", "unknown"), "refresh_seconds": status.get("refresh_seconds")})
    state = localguard.public_state()
    answer = {"schema": 1, "version": TOOL_VERSION, "edition": "lite" if LITE["on"] else "complete", "port": port, "bind": state.get("host") or "127.0.0.1", "network": bool(state.get("network")),
              "lan_address": lan_address(), "account": CHILD["account"] or None, "uptime_seconds": int(time.time() - STARTED), "demo": bool(DEMO["on"]),
              "runs": {"active": figures.get("active"), "queued": figures.get("queued")},      # the same two figures as the header tiles and `monitor_cli status` (null until the first read)
              "sentinels": sentinels, "workers": ((LIVE_CONFIG or {}).get("sentinel") or {}).get("workers") if not LITE["on"] else None,
              "ai": None if LITE["on"] else __import__("github_actions_monitor.integrations.ai_alerts", fromlist=["_"]).presence(LIVE_CONFIG or toolconfig.raw_config())}      # was the feed read lately, and by what way (ai_alerts.heartbeat)
    if answer["network"] and not client_local:
        del answer["lan_address"]
    return answer


def alerts_payload(ask):
    """GET /api/alerts: the alerts of every sentinel in one list, each with `muted_until`; `?sentinel=`, `?level=`, `?muted=show|hide|only`. Lite has no sentinels: an empty list."""
    from github_actions_monitor.sentinels import alert_center
    refresh_feed()
    registry = SENTINEL["registry"]
    extra = credential_alerts()
    everything = alert_center.collect(registry, extra=extra)
    chosen = alert_center.select(everything, ask.get("sentinel", ""), ask.get("level", ""), ask.get("muted", "show") if ask.get("muted") in ("show", "hide", "only") else "show")
    return {"schema": 1, "account": CHILD["account"] or None, "alerts": chosen, "summary": alert_center.summary(everything), "mutes": alert_center.active(), "history": alert_center.history(20),
            "mute_hours": alert_center.hours_setting(LIVE_CONFIG or toolconfig.raw_config()), "sentinels": (registry.names() if registry else []) + (["system"] if extra else [])}


def service_mode():
    """True for a monitor that runs as a service: the process of one account under a supervisor, or MONITOR_SERVICE=1 (the image, the systemd unit). It does not give up when the login of GitHub is no good at
    start: it stays up, says so, and waits for another one."""
    return bool(CHILD["account"]) or os.environ.get("MONITOR_SERVICE", "").strip() == "1"


def cycle_verdict():
    """'' when the refresh loop is fine, 'stuck' when one cycle has run longer than the limit of the watchdog (`watchdog_minutes`, 30 minutes when that is off) and 'dead' when its thread is gone."""
    thread = LOOP["thread"]
    limit = watchdog_limit(LIVE_CONFIG or DEFAULTS) or 1800
    return cycle_watch.check(WATCH, limit, thread is not None and thread.is_alive())


def health_payload(deep=False):
    """The answer of /api/health. It never calls GitHub. Always: whether the data are loaded, the connection, and (complete edition) the state of the cycle and of the login of this account. With `deep` the
    answer also says whether the monitor is fit to serve: `ok` is false when the refresh loop is stuck or gone (see `health_reply`)."""
    with LOCK:
        loaded = bool(STATE.get("data"))
    out = {"ok": True, "lite": LITE["on"], "version": TOOL_VERSION, "uptime_seconds": int(time.time() - STARTED), "loaded": loaded, "offline": LINK.state()["offline"], "degraded": degraded.snapshot()["total"]}
    if CHILD["account"]:
        out["account"] = CHILD["account"]
    if not LITE["on"]:
        verdict = "" if DEMO["on"] else cycle_verdict()
        snap = WATCH.snapshot(limit_seconds=watchdog_limit(LIVE_CONFIG or DEFAULTS))
        out["cycle"] = {"phase": snap["phase"], "running_seconds": snap["running_seconds"], "seconds_since_ok": snap["seconds_since_ok"], "stuck": verdict == "stuck", "dead": verdict == "dead"}
        out["credential"] = credential.snapshot()
        if deep and verdict:
            out["ok"] = False
    return out


def health_reply(deep=False):
    """(payload, HTTP status): 200, or 503 when `deep` and the monitor is not fit to serve. The lite edition has no deep check and always answers 200."""
    payload = health_payload(deep and not LITE["on"])
    return payload, 200 if payload["ok"] else 503


CONFIRM_DELAY = 20      # seconds before the next cycle while a refusal of the login waits to be confirmed


def credential_refusal(error, config):
    """A cycle ended with a refusal of the login: after `credential.CONFIRM` in a row the account is blind and the alert opens (once). Returns 'blind', 'strike' or ''. Never raises, never in the lite edition."""
    if LITE["on"]:
        return ""
    try:
        outcome = credential.note_refusal(str(error))
        if outcome == "blind":
            announce_credential("credential_blind", config)
        return outcome
    except Exception as failure:   # noqa: BLE001 - a notice never stops the loop
        degraded.note("loop.step", failure)
        return ""


def credential_ok(config):
    """A cycle ended well: a blind account is back (one notice)."""
    if LITE["on"]:
        return
    try:
        if credential.note_success() == "back":
            announce_credential("credential_back", config)
    except Exception as failure:   # noqa: BLE001
        degraded.note("loop.step", failure)


def announce_credential(kind, config):
    """`credential_blind` / `credential_back` go to the console, the event feed and the notifications, once per change. The text never carries the token."""
    from github_actions_monitor.integrations import notifiers
    info = credential.snapshot()
    account = CHILD["account"] or ""
    reason = i18n.t("credential.reason_" + info["reason"]) if info["reason"] else ""
    event = {"kind": kind, "code": kind, "level": "bad" if kind == "credential_blind" else "ok", "repo": "", "owner": "main", "url": None, "args": {"account": account, "reason": info["reason"]},
             "text": i18n.t("evt." + kind, account=account or toolconfig.github_owner(config) or "-", reason=reason)}
    print(event["text"], flush=True)
    sentinel = SENTINEL["obj"]
    try:
        if sentinel is not None:
            sentinel.feed._append([event])
        notifiers.notify(config, event)
    except Exception as error:   # noqa: BLE001 - never stops the loop
        degraded.note("loop.step", error)


def credential_alerts():
    """The critical system alert of a blind account, ready for the Alerts tab (the title in the language of the page)."""
    if LITE["on"]:
        return []
    info = credential.snapshot()
    reason = i18n.t("credential.reason_" + info["reason"]) if info["reason"] else ""
    return credential.system_alerts(CHILD["account"] or "", i18n.t("credential.alert_title", reason=reason))


def verify_credential():
    """One free call to GitHub with the login the process uses now (the allowance endpoint: it works for every kind of token and costs nothing). (ok, why)."""
    try:
        gh("api", "rate_limit", retries=0, as_user=True)
        return True, ""
    except AuthError:
        return False, "rejected"
    except Exception:   # noqa: BLE001 - no network, no gh: the old login stays
        return False, "unreachable"


def credential_change(action, token=""):
    """Replaces the login of this account (`replace`, with the token) or reads its files again (`reload`) while everything runs. Returns (ok, status, snapshot). Never repeats the token."""
    config = LIVE_CONFIG or DEFAULTS
    folder = state_dir()
    was_blind = credential.is_blind()
    if action == "replace":
        ok, status = credential.replace(folder, token, verify_credential)
    elif action == "reload":
        status = credential.reload(folder, verify_credential)
        ok = status in ("reloaded", "unchanged", "none")
    else:
        return False, "request", credential.snapshot()
    if ok and status in ("saved", "reloaded"):
        if was_blind:
            announce_credential("credential_back", config)
        if not DEMO["on"]:
            start_loop(config)      # a new loop reads at once instead of waiting for the end of its pause
    return ok, status, credential.snapshot()


def reload_on_signal(signum=None, frame=None):
    """SIGHUP (where the system has it): read the credential files again, in a thread of its own so the handler returns at once."""
    threading.Thread(target=credential_change, args=("reload",), daemon=True, name="credential-reload").start()


def update_info():
    """The state of the update notice: the cached answer, refreshed (at most every 24 hours) through the conditional GitHub client; silent when it cannot be read."""
    config = LIVE_CONFIG or toolconfig.raw_config()
    state_file = state_dir() / ("update_check_lite.json" if LITE["on"] else "update_check.json")
    if DEMO["on"]:
        return updatecheck.view({"updates": {"check": False}}, TOOL_VERSION, {})
    return updatecheck.check(config, TOOL_VERSION, lambda endpoint: gh_read(endpoint, retries=0), state_file=state_file, offline=LINK.state()["offline"], background=True)      # never a network wait in the path of a page


def RUN_CACHE_RESET():
    """After a change of mode every repository is read again in the next cycle."""
    for entry in RUN_CACHE.values():
        entry["at"] = 0


def mode_payload():
    config = LIVE_CONFIG or DEFAULTS
    remaining, limit = mode_remaining()
    name = MODE.current(config, remaining)
    with LOCK:
        data = STATE.get("data") or {}
    etag = data.get("etag") or {}
    calls = max(1, etag.get("calls") or 0)
    saved = (etag.get("saved") or 0) / calls if etag.get("calls") else 0.0
    return {"mode": name, "auto": bool(MODE.auto), "seconds_left": MODE.seconds_left(), "notice": MODE.notice, "names": list(modes.NAMES), "allowed": not (isinstance(limit, int) and limit <= 60),
            "limit": limit, "remaining": remaining, "floor": int(config.get("min_rate_remaining", 800)), "default_minutes": modes.settings(config)["default_minutes"],
            "estimate": modes.estimate(config, len(data.get("repos") or []), data.get("hot") or 0, remaining, saved), "presets": modes.presets(config), "saved_share": round(saved, 2)}


def quota_payload():
    from github_actions_monitor.data_pipeline import quota
    config = LIVE_CONFIG or toolconfig.raw_config()
    with LOCK:
        data = STATE.get("data") or {}
    since = time.time() - 86400
    done = [r for r in (data.get("runs") or []) if r.get("status") == "completed" and (parse_time(r.get("started")) or datetime.fromtimestamp(0, timezone.utc)).timestamp() > since]
    rate = data.get("rate") or {}
    reader = None if DEMO["on"] else (lambda endpoint: gh_read(endpoint, retries=0))
    return quota.summary(config, done, data.get("active") or [], set(PRIVATE), reader, toolconfig.github_owner(config), rate.get("limit"), costs={k: v for k, v in RUN_COSTS.items() if v})


def about_payload():
    from github_actions_monitor.ui import about
    places = {"config": CONFIG_FILE, "log": LOG_FILE, "etag_cache": etagcache.CACHE_FILE, "package_folder": HERE}
    data = about.info(LITE["on"], health_payload(), places, update_info(), i18n.language())
    data["support"] = about.support_text(data)
    return data


def discovery_payload():
    config = LIVE_CONFIG or toolconfig.raw_config()
    with LOCK:
        data = STATE.get("data") or {}
    box = discovery.box(toolconfig.github_owner(config), len(data.get("repos") or []), HIDDEN["discovered"], HIDDEN["names"])
    from github_actions_monitor.data_pipeline import orgs
    organisations = orgs.view(toolconfig.raw_config(), lambda endpoint: gh_read(endpoint, retries=0), state_dir() / ("orgs_state_lite.json" if LITE["on"] else "orgs_state.json"), offline=LINK.state()["offline"]) if not DEMO["on"] else {"enabled": False, "orgs": []}
    return {**box, "events": list(reversed(DISCOVERY["events"]))[:20], "suggestions": DISCOVERY["suggestions"], "settings": discovery.settings(config), "demo": DEMO["on"], "organizations": organisations}


class SessionTokens:
    """One-use tokens for the POST requests that change something (settings, confirmations of the AI actions). A token lives ten minutes and works once; at most twenty are kept."""

    def __init__(self, clock=time.time):
        self.clock, self.items, self.lock = clock, {}, threading.Lock()

    def issue(self):
        import secrets
        with self.lock:
            now = self.clock()
            self.items = {k: v for k, v in self.items.items() if v > now}
            while len(self.items) >= 20:
                self.items.pop(next(iter(self.items)))
            token = secrets.token_hex(16)
            self.items[token] = now + 600
            return token

    def use(self, token):
        with self.lock:
            expires = self.items.pop(str(token or ""), 0)
            return expires > self.clock()


SESSION = SessionTokens()


def token_required():
    return (LIVE_CONFIG or {}).get("session_guard") is True


def metrics_extra():
    """What /metrics and the Grafana source add to the sentinel's picture: conditional reads, the connection, the analytics, the live events and the notifications."""
    from github_actions_monitor.integrations import notifiers
    return {"etag": ETAG["cache"].stats() if ETAG["cache"] else None, "offline": LINK.state()["offline"], "analytics": ANALYTICS["summary"], "live_events": len(LIVE_EVENTS),
            "notify": dict(notifiers.STATS), "disconnects": DISCONNECTS[0]}


def handle_action_post(path, request):
    """The endpoints that DO something on request of the page: confirm an action of the AI, unlock the actions, test the AI connection, send a test notification."""
    config = toolconfig.raw_config()
    if path == "/api/ai/actions/confirm":
        from github_actions_monitor.integrations import ai_actions
        return ai_actions.ACTIONS.run(request.get("id"), request.get("command"), config)
    if path == "/api/ai/actions/unlock":
        from github_actions_monitor.integrations import ai_actions
        ai_actions.ACTIONS.unlock()
        return {"ok": True}
    if path == "/api/ai/test":
        from github_actions_monitor.sentinels import sentinel_ai
        sentinel = SENTINEL["obj"]
        if sentinel is None or sentinel.ai_cfg["provider"] == "none":
            return {"ok": False, "error": i18n.t("ai.is_off")}
        return sentinel_ai.test_connection(sentinel.ai_cfg, sentinel.ai_store)
    from github_actions_monitor.integrations import notifiers
    cfg = notifiers.settings(config)
    name = request.get("channel")
    if name not in notifiers.CHANNELS:
        return {"ok": False, "reason": "bad_value"}
    return notifiers.send_channel(name, cfg["channels"][name], notifiers.test_event(i18n.t("evt.test")), allow_private=cfg["allow_private_targets"], use_proxy=cfg["use_proxy"])


def run_gh_checked(args, timeout=40):
    return run_gh(args, timeout)


def advanced_state(config):
    """What the page may know about the opt-in features: switches and the places, never a token."""
    from github_actions_monitor.integrations import actlocal
    from github_actions_monitor.integrations import ghactions
    from github_actions_monitor.security import secretstore
    token = secretstore.settings(config)
    network = localguard.public_state()
    return {"network": network, "token": {**token, **(secretstore.Store(token["store"]).status() if token["enabled"] else {"backend": "", "stored": False, "weak": False})},
            "github_actions": ghactions.settings(config), "act": {k: v for k, v in actlocal.settings(config).items()}, "demo": DEMO["on"]}


def welcome_file():
    return state_dir() / ("welcome_state_lite.json" if LITE["on"] else "welcome_state.json")


def advanced_get(path, query):
    config = toolconfig.raw_config()
    if path == "/api/advanced":
        return advanced_state(config)
    if path == "/api/github-token":
        return advanced_state(config)["token"]
    if path == "/api/act/status":
        from github_actions_monitor.integrations import actlocal
        from urllib.parse import parse_qs
        since = (parse_qs(query).get("since") or ["0"])[0]
        return actlocal.status(int(since) if since.isdigit() else 0)
    if path == "/api/ai/brief":
        from github_actions_monitor.integrations import ai_alerts
        from urllib.parse import parse_qs
        if "json" in (parse_qs(query).get("fmt") or [""]):
            return {**ai_alerts.brief_info(config), "alerts": ai_alerts.alerts(config, states=("open", "acknowledged"))}
        return {"brief": ai_alerts.read_brief(config)}
    if path == "/api/ai/alerts":
        from github_actions_monitor.integrations import ai_alerts
        from urllib.parse import parse_qs
        since = (parse_qs(query).get("since") or ["0"])[0]
        return {"alerts": ai_alerts.alerts(config, int(since) if since.isdigit() else 0)}
    if path == "/api/welcome":
        try:
            done = bool(json.loads(welcome_file().read_text(encoding="utf-8")).get("done"))
        except (OSError, ValueError, AttributeError):
            done = False
        return {"done": done and not DEMO["on"]}
    if path == "/api/runners":
        from github_actions_monitor.integrations import runners
        return runners.payload(config, lambda endpoint: gh_read(endpoint, retries=0), toolconfig.github_owner(config), DEMO["on"], list((STATE.get("data") or {}).get("repos") or []))
    if path == "/api/mirror":
        from github_actions_monitor.integrations import mirror
        return mirror.status(config)
    from github_actions_monitor.integrations import otlp
    return otlp.status(config)


def handle_advanced_post(path, request, who=""):
    """The plan / confirm pairs of the actions on GitHub and of `act`, the token of GitHub and the welcome flag. Answers never contain the request."""
    config = toolconfig.raw_config()
    if path in ("/api/alerts/mute", "/api/alerts/unmute"):      # a local silence (never a change on GitHub): scope alert|code|sentinel, hours optional
        from github_actions_monitor.sentinels import alert_center
        scope, value = str(request.get("scope") or ""), str(request.get("value") or "")
        if path.endswith("unmute"):
            return {"ok": alert_center.unmute(scope, value)}
        until_change = None
        if request.get("until_change") is True and scope == "alert":      # "until the item changes": remember the updated_at the alert carries now
            for alert in alert_center.collect(SENTINEL["registry"]):
                if alert.get("id") == value:
                    until_change = (alert.get("details") or {}).get("updated") if isinstance(alert.get("details"), dict) else None
                    break
        entry = alert_center.mute(scope, value, request.get("hours"), config, who=who, until_change=until_change)
        return {"ok": entry is not None, "mute": entry}
    if path == "/api/ai/ack":
        from github_actions_monitor.integrations import ai_alerts
        return {"ok": ai_alerts.ack(config, request.get("id"))}
    if path == "/api/welcome":
        if not DEMO["on"]:
            try:
                private_io.write_private(welcome_file(), json.dumps({"done": request.get("done") is True}) + chr(10))
            except OSError:
                return {"ok": False}
        return {"ok": True}
    if path == "/api/github-token":
        from github_actions_monitor.security import secretstore
        cfg = secretstore.settings(config)
        store = secretstore.Store(cfg["store"])
        if request.get("action") == "delete":
            ok = store.delete()
            secretstore.clear_environment()
            return {"ok": ok, **advanced_state(config)["token"]}
        if not cfg["enabled"]:
            return {"ok": False, "status": "off"}
        done, why = store.save(request.get("token"))
        if done:
            secretstore.apply_to_environment(config, store)
        return {"ok": done, "status": "saved" if done else why, **advanced_state(config)["token"]}
    if path.startswith("/api/gh-action"):
        from github_actions_monitor.integrations import ghactions
        if path.endswith("plan"):
            item, why = ghactions.plan(config, toolconfig.github_owner(config), request.get("action"), request.get("repo"), request.get("number"))
            return {"ok": item is not None, "status": why, "plan": item}
        return ghactions.execute(config, request.get("plan"), run_gh_checked)
    from github_actions_monitor.integrations import actlocal
    if path.endswith("plan"):
        from github_actions_monitor.app import workspace
        item, why = actlocal.plan(config, workspace.workspace_root_soft() if hasattr(workspace, "workspace_root_soft") else "", request.get("repo"), request.get("workflow"), request.get("event"), request.get("job") or None)
        return {"ok": item is not None, "status": why, "plan": item}
    if path.endswith("stop"):
        return actlocal.stop()
    return actlocal.start(config, request.get("plan"))


def update_loop():
    """Looks for a newer published version now and then (at most one read every 24 hours; silent when it fails or when the check is off)."""
    while True:
        try:
            info = update_info()
            if info.get("newer") and not UPDATE_SAID:
                UPDATE_SAID.append(info["latest"])
                print(updatecheck.notice(info, i18n.t), flush=True)
        except Exception as error:   # noqa: BLE001 - never stops anything
            degraded.note("update.loop", error)
            pass
        time.sleep(6 * 3600)


UPDATE_SAID = []


def start_sentinel(config):
    """Layer A of the Centinela in its own thread and cache; if the module fails, the monitor goes on and the tab shows a red notice."""
    try:
        from github_actions_monitor.sentinels import sentinel_registry

        def repos_fn():
            data = STATE["data"]
            if data and data.get("repos"):
                return data["repos"]
            try:
                return watched_repos(config)
            except Exception:
                return []

        ctx = {"gh": gh, "run_gh": run_gh, "repos_fn": repos_fn, "runs_fn": lambda: RUN_CACHE, "data_fn": lambda: STATE["data"], "eco_fn": ecosystem_of, "account_id": CHILD["account"]}
        from github_actions_monitor.app import workspace
        if not workspace.has_workspace():   # optional: without the local clones the sentinel runs in reduced mode (GitHub API data only)
            print(i18n.t("mon.reduced_mode"))
        SENTINEL["registry"] = sentinel_registry.SentinelRegistry.build(ctx, config)       # the sentinels by name (1.7.1); today only "ci"
        SENTINEL["obj"] = SENTINEL["registry"].get("ci")                                   # the CI sentinel answers everything the monitor always asked of it
        from github_actions_monitor.integrations import notifiers
        SENTINEL["obj"].feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
        collab = SENTINEL["registry"].get("collab")
        if collab is not None:
            collab.feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
        SENTINEL["registry"].start()
    except Exception as error:
        SENTINEL["error"] = i18n.t("mon.sentinel_start_failed", error=error)
        print(SENTINEL["error"])


def demo_main():
    """--demo: the page with invented data; nothing is read from GitHub and the configuration of the user is not touched."""
    from github_actions_monitor.app import demo_mode
    i18n.set_language(i18n.detect(None))
    i18n.cli_language() if "--lang" in " ".join(sys.argv) else None
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--lang")
    parser.add_argument("--lite", action="store_true")
    args, _rest = parser.parse_known_args()
    LITE["on"] = True       # the demo shows the page without the sentinel: its invented data are the runs, the figures and the history
    platform_compat.console_utf8()
    server, url = demo_mode.start(sys.modules[__name__], args.port)
    from github_actions_monitor.util import banner
    banner.set_title("GitHub Actions Monitor DEMO")
    print(i18n.t("mon.demo", url=url))
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def accounts_cli(argv):
    """The commands of the accounts that do not start a monitor: --accounts (list), --migrate-accounts [--apply]. Returns an exit code, or None when the arguments are not for them.
    The lite edition never gets here: it has no accounts."""
    if "--accounts" not in argv and "--migrate-accounts" not in argv:
        return None
    from github_actions_monitor.accounts import accounts
    i18n.set_language(i18n.detect(None))
    i18n.cli_language() if "--lang" in " ".join(argv) else None
    platform_compat.console_utf8()
    if "--migrate-accounts" in argv:
        done = accounts.migrate(apply="--apply" in argv)
        for source, target, kind in done["items"]:
            print(i18n.t("mon.migrate_done" if done["applied"] else "mon.migrate_would", kind=i18n.t("mon.kind_" + kind), name=Path(source).name, target=target))
        for problem in done["problems"]:
            print(i18n.t("mon.migrate_problem", text=problem))
        if not done["items"]:
            print(i18n.t("mon.migrate_nothing"))
        elif not done["applied"]:
            print(i18n.t("mon.migrate_dry"))
        return 1 if done["problems"] else 0
    on = set(accounts.enabled_accounts())
    for account_id in accounts.list_accounts():
        try:
            owner = json.loads(accounts.config_path(account_id).read_text(encoding="utf-8")).get("github_owner") or "-"
        except (OSError, ValueError):
            owner = "?"
        print(i18n.t("mon.account_line", id=account_id, owner=owner, state=i18n.t("mon.account_on" if account_id in on else "mon.account_off"),
                     default=i18n.t("mon.account_default") if account_id == accounts.default_account() else ""))
    return 0


def network_setup(config, lite=False):
    """The way this process listens, from `listen.*`: (listen, tls_context, access_token, token_was_generated). By default only this computer: nothing is configured and the token stays empty. In the
    network mode the access token comes from the environment variable named in `listen.token_env`, or from the file named by the same variable plus `_FILE` (a secret of a container), else a fresh one
    is made at each start; the certificate is loaded when one is given and a certificate that cannot be used raises (the process never falls back to plain HTTP behind the owner's back). Used by the
    monitor of one account and by the supervisor of several, so both answer to the same rules."""
    listen = {"network": False, "host": "127.0.0.1"} if lite else localguard.settings_from(config)
    access_token, generated, tls_ctx = "", False, None
    if listen["network"]:
        access_token = secret_from_environment(listen["token_env"])
        if len(access_token) < 16:
            access_token, generated = localguard.make_token(), True      # a fresh token at each start, shown once in this console and nowhere else
        tls = localguard.tls_settings(config)
        if tls["cert"] or tls["key"]:      # HTTPS served directly with YOUR certificate
            tls_ctx = localguard.tls_context(tls["cert"], tls["key"])
        localguard.configure(True, listen["host"], access_token, listen["allowed_hosts"], secure=tls_ctx is not None or tls["secure_cookie"], proxy_host=listen["proxy_public_host"], trusted_proxy=listen["trusted_proxy"],
                           behind_proxy=tls["secure_cookie"])
    return listen, tls_ctx, access_token, generated


def secret_from_environment(name):
    """The value of the environment variable `name`, else the first line of the file named by `name + "_FILE"` (the way a container hands over a secret), else ''. The value is never printed."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    path = os.environ.get(name + "_FILE", "").strip()
    if path:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                return handle.readline().strip()
        except (OSError, UnicodeError):
            return ""
    return ""


def supervisor_main(argv):
    """Several accounts: this process is the supervisor (accounts_supervisor.py) and starts one monitor per account. Returns an exit code."""
    from github_actions_monitor.accounts import accounts
    from github_actions_monitor.accounts import accounts_supervisor
    port = next((int(argv[i + 1]) for i, a in enumerate(argv) if a == "--port" and i + 1 < len(argv) and argv[i + 1].isdigit()), 8765)
    config = toolconfig.raw_config()
    i18n.set_language(i18n.detect(config.get("language")))
    platform_compat.console_utf8()
    try:      # the same listening rules as the monitor of one account: by default only this computer; `listen.*` opens the network mode (access token, optional certificate, declared proxy)
        listen, tls_ctx, access_token, generated = network_setup(config)
    except (OSError, ValueError, ssl.SSLError) as error:
        print(i18n.t("mon.tls_failed", error=str(error)[:200]))
        return 1
    host = listen["host"] if listen["network"] else "127.0.0.1"
    server = sup = None
    for candidate in range(port, port + 10):
        try:
            server, sup = accounts_supervisor.serve(candidate, host, tls=tls_ctx)
            if candidate != port:
                print(i18n.t("mon.port_busy", port=port, used=candidate))
            break
        except OSError:
            continue
    if server is None:
        print(i18n.t("mon.no_port", port=port))
        return 1
    url = f"{'https' if tls_ctx is not None else 'http'}://{localguard.display_host(server.server_address[0])}:{server.server_address[1]}/"
    if listen["network"]:
        print(i18n.t("mon.network_on", host=listen["host"], port=server.server_address[1]), flush=True)
        if tls_ctx is None and not localguard.STATE["secure"]:
            print(i18n.t("mon.network_plain"), flush=True)
        if generated:
            print(i18n.t("mon.network_token_post", url=url, token=access_token), flush=True)      # the only place a generated token is shown
    if listen["network"] and listen["local_port"] and listen["local_port"] != server.server_address[1]:      # the way in of the person at this computer when a reverse proxy is declared
        try:
            door = accounts_supervisor.Server(("127.0.0.1", listen["local_port"]), accounts_supervisor.DoorHandler)
            threading.Thread(target=door.serve_forever, daemon=True, name="supervisor-door").start()
            print(i18n.t("mon.local_door", port=listen["local_port"]), flush=True)
        except OSError:
            print(i18n.t("mon.local_door_failed", port=listen["local_port"]), flush=True)
    if hasattr(signal, "SIGHUP") and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, lambda signum, frame: threading.Thread(target=sup.reload_credentials, daemon=True, name="credential-reload").start())      # kill -HUP: every account reads its credential files again
    print(i18n.t("mon.accounts_started", n=len(accounts.enabled_accounts()), url=url), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sup.stop()
    return 0


def main():
    if "--demo" in sys.argv[1:]:
        return demo_main()
    if not CHILD["account"]:
        rootmigrate.auto()      # an installation of 1.8.1 or older: its data, logs and AI files move into config/, data/, logs/ and ai/ (undo: python -m github_actions_monitor.util.rootmigrate --undo)
    paths.ensure()      # config/, data/, logs/ and ai/ exist before anything is written
    if not CHILD["account"]:
        from github_actions_monitor.integrations import ai_index
        ai_index.write("lite" if lite_requested() else "complete")      # ai/INDEX.json and ai/README.md: the map for the AI tools that read this installation
    code = accounts_cli(sys.argv[1:]) if not lite_requested() else None
    if code is not None:
        return code
    if not lite_requested() and not CHILD["account"]:
        from github_actions_monitor.accounts import accounts
        asked = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--account" and i + 1 < len(sys.argv)), "")
        if asked:       # --account ID: only that account, as an ordinary monitor in this very process (no supervisor)
            if not accounts.valid_id(asked) or not accounts.config_path(asked).is_file():
                print(i18n.t("mon.account_unknown", id=asked[:40], known=", ".join(accounts.list_accounts()) or "-"))
                return 2
            from github_actions_monitor.accounts import account_child
            CHILD["account"], CHILD["folder"] = asked, str(account_child.redirect(asked))
            sys.argv = [a for i, a in enumerate(sys.argv) if not (a == "--account" or (i > 0 and sys.argv[i - 1] == "--account"))]
        elif accounts.layout() == "accounts":
            return supervisor_main(sys.argv[1:])
    if lite_requested():
        enable_lite()
    config = load_config()
    if LITE["on"]:
        config["mode"] = "full"                      # the lite edition reads as deep as the complete one: its figures must be the same
        config["sentinel"] = {"enabled": False}      # the lite product has no sentinel, whatever the file says
        config["webhook"] = {"enabled": False, "secret": ""}
    i18n.set_language(i18n.detect(config.get("language")))
    i18n.cli_language() if "--lang" in " ".join(sys.argv) else None
    from github_actions_monitor.security import secretstore
    secretstore.apply_to_environment(config)       # the optional token kept by the monitor (off by default) goes to GH_TOKEN of this process; nothing is printed
    if not LITE["on"]:
        credential.apply_stored(state_dir())      # a login put in place with the administrator endpoint, or the file named by GH_TOKEN_FILE: first match of credential.stored()
    parser = argparse.ArgumentParser(description=i18n.t("mon.description"), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=LITE_PORT if LITE["on"] else 8765, help=i18n.t("mon.help_port"))
    parser.add_argument("--lite", action="store_true", help=i18n.t("mon.help_lite"))
    parser.add_argument("--no-browser", action="store_true", help=i18n.t("mon.help_no_browser"))
    parser.add_argument("--discover", action="store_true", help=i18n.t("mon.help_discover"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    parser.add_argument("--init-catalog", action="store_true", help=i18n.t("mon.help_init_catalog"))
    parser.add_argument("--about", action="store_true", help=i18n.t("mon.help_about"))
    parser.add_argument("--help-topics", nargs="*", metavar="TOPIC", help=i18n.t("mon.help_topics"))
    parser.add_argument("--help-search", nargs="+", metavar="WORD", help=i18n.t("mon.help_search"))
    parser.add_argument("--doctor", action="store_true", help=i18n.t("mon.help_doctor"))
    parser.add_argument("--json", action="store_true", help=i18n.t("mon.help_json"))
    parser.add_argument("--demo", action="store_true", help=i18n.t("mon.help_demo"))
    parser.add_argument("--mode", choices=modes.NAMES, default=None, help=i18n.t("mon.help_mode"))
    parser.add_argument("--mode-minutes", type=int, default=None, help=i18n.t("mon.help_mode_minutes"))
    if not LITE["on"]:       # the lite edition has no accounts: it does not even show these options
        parser.add_argument("--account", metavar="ID", help=i18n.t("mon.help_account"))
        parser.add_argument("--accounts", action="store_true", help=i18n.t("mon.help_accounts"))
        parser.add_argument("--migrate-accounts", action="store_true", help=i18n.t("mon.help_migrate_accounts"))
        parser.add_argument("--apply", action="store_true", help=i18n.t("mon.help_apply"))
    args = parser.parse_args()
    platform_compat.console_utf8()
    if args.about:
        from github_actions_monitor.ui import about
        print(about.console_text(about.lone(i18n.t), i18n.t), end="")
        return 0
    if args.help_topics is not None or args.help_search:
        from github_actions_monitor.ui import helpdocs
        code, text = helpdocs.console((["--search"] + args.help_search) if args.help_search else args.help_topics, i18n.language(), i18n.t)
        print(text, end="")
        return code
    if args.doctor:
        from github_actions_monitor.cli import doctor
        checks = doctor.run(config=config)
        if args.json:
            print(json.dumps(doctor.as_json(checks, "lite" if LITE["on"] else "full"), ensure_ascii=False, indent=1))
        else:
            print(doctor.text(checks, i18n.t, "lite" if LITE["on"] else "full"), end="")
        return doctor.exit_code(checks)
    if args.init_catalog:
        for name, created in toolconfig.init_catalog():
            print(i18n.t("mon.catalog_created" if created else "mon.catalog_kept", name=name))
        return 0
    if not platform_compat.gh_available():
        print(platform_compat.gh_install_hint())
        return 1
    started_blind = False
    try:
        me = gh("api", "user", retries=0, as_user=True)
        toolconfig.prime_owner((me or {}).get("login"))   # the owner to watch when "github_owner" is empty, from the call that checks the login: no extra call
    except AuthError as error:
        if not (service_mode() and not LITE["on"]):
            print(i18n.t("mon.auth_rejected"))
            return 1
        started_blind = credential.mark_blind(str(error))      # a service stays up with a login that no longer works: it says so and waits for another one (an administrator or SIGHUP)
        print(i18n.t("mon.auth_rejected_service"), flush=True)
    except Exception as error:
        if not (service_mode() and not LITE["on"]):
            print(i18n.t("mon.gh_not_ready", error=error))
            return 1
        started_blind = credential.mark_blind(str(error))
        print(i18n.t("mon.gh_not_ready_service", error=credential.redact(error)), flush=True)
    if not toolconfig.github_owner(config):
        print(i18n.t("mon.no_owner"))
        return 1
    if args.discover:
        names = watched_repos(config, force=True)
        saved = dict(config)
        saved["repos"] = names
        private_io.write_private(CONFIG_FILE, json.dumps(saved, indent=2))
        print(i18n.t("mon.discovered", n=len(names), file=CONFIG_FILE.name))
        return 0
    using_example = toolconfig.catalog_in_example(config)
    if using_example:
        print(i18n.t("mon.catalog_example", names=", ".join(using_example)))
    global AUTOSAVE
    LIVE_CONFIG.update(config)
    if not LITE["on"] and not CHILD["account"]:      # an account process bound its storage when it was redirected; the lite edition has no database
        from github_actions_monitor.storage import runtime as storage_runtime
        storage_runtime.bind(config)
    etag_cfg = ((config.get("cache") or {}).get("etag") or {}) if isinstance(config.get("cache"), dict) else {}
    ETAG["cache"] = etagcache.EtagCache(ttl_hours=etag_cfg.get("ttl_hours", 24) if isinstance(etag_cfg.get("ttl_hours"), int) else 24, enabled=etag_cfg.get("enabled", True) is True and (config.get("network") or {}).get("etag", True) is not False)      # network.etag is the switch of the Quota tab; cache.etag.enabled stays as it was
    acfg = analytics.settings(config)
    if not LITE["on"]:
        ANALYTICS["store"] = analytics.Store(keep_days=acfg["keep_days"], max_samples=acfg["max_samples"])
    if not LITE["on"]:
        from github_actions_monitor.data_pipeline import report_history
        AUTOSAVE = report_history.AutoSaver()
    wanted = args.mode or modes.settings(config)["start"]
    if wanted in ("fast", "turbo"):
        ok, why = MODE.set(wanted, args.mode_minutes if args.mode_minutes is not None else modes.settings(config)["default_minutes"], config)
        print(banner_mode_line(MODE.name, "" if ok else why), flush=True)
    degraded.attach(state_dir() / ("degraded_lite.json" if LITE["on"] else "degraded.json"))
    start_loop(config)
    if started_blind:
        announce_credential("credential_blind", config)
    if not LITE["on"] and hasattr(signal, "SIGHUP") and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, reload_on_signal)      # kill -HUP: read the credential files again, no restart (where the system has the signal)
    threading.Thread(target=watchdog_loop, args=(config,), daemon=True, name="refresh-watchdog").start()
    threading.Thread(target=update_loop, daemon=True).start()
    if not LITE["on"]:
        start_sentinel(config)
    try:      # the token file of the second account is only accepted inside the accounts folder: a configuration that points elsewhere is told once, with the way out
        from github_actions_monitor.data_pipeline import readpool
        block = config.get("extra_reader") if isinstance(config.get("extra_reader"), dict) else {}
        if block.get("enabled") is True and block.get("file") and not readpool.settings(config)["file"]:
            print(i18n.t("mon.extra_file_outside"), flush=True)
    except Exception as error:   # noqa: BLE001 - a notice never stops the start
        degraded.note("loop.extra", error)
    server = None
    try:
        listen, tls_ctx, access_token, access_generated = network_setup(config, lite=LITE["on"])
    except (OSError, ValueError, ssl.SSLError) as error:
        print(i18n.t("mon.tls_failed", error=str(error)[:200]))
        return 1
    if listen["network"]:
        LIVE_CONFIG["session_guard"] = True      # the one-use token of the page is not optional on the network
    for port in range(args.port, args.port + 10):
        try:
            server = QuietServer((listen["host"] if listen["network"] else "127.0.0.1", port), Handler)
            if port != args.port:
                print(i18n.t("mon.port_busy", port=args.port, used=port))
            break
        except OSError:
            continue
    if server is None:
        print(i18n.t("mon.no_port", port=args.port))
        return 1
    door = None
    if listen["network"] and listen["local_port"] and listen["local_port"] != server.server_address[1]:      # the way in of the person at this computer when a reverse proxy is declared (listen.local_port)
        try:
            door = QuietServer(("127.0.0.1", listen["local_port"]), LocalDoorHandler)
            threading.Thread(target=door.serve_forever, daemon=True).start()
            print(i18n.t("mon.local_door", port=listen["local_port"]), flush=True)
        except OSError:
            print(i18n.t("mon.local_door_failed", port=listen["local_port"]), flush=True)
    server.tls_context = tls_ctx      # each connection is wrapped in its own thread (get_request), so a client that never finishes the handshake cannot stall the others
    url = f"{'https' if tls_ctx is not None else 'http'}://{localguard.display_host(server.server_address[0])}:{server.server_address[1]}/"      # from the address the server really listens on
    try:      # the feed for AIs is off by default since 1.7.6: an installation that was already using it keeps it, and is told
        from github_actions_monitor.integrations import ai_alerts
        if ai_alerts.settings(config)["legacy"]:
            print(i18n.t("mon.ai_feed_legacy"), flush=True)
    except Exception as error:   # noqa: BLE001 - a notice never stops the start
        degraded.note("loop.extra", error)
    if listen["network"]:
        print(i18n.t("mon.network_on", host=listen["host"], port=server.server_address[1]), flush=True)
        if tls_ctx is None and not localguard.STATE["secure"]:
            print(i18n.t("mon.network_plain"), flush=True)
        if localguard.query_access_allowed(config):
            print(i18n.t("mon.network_first_steps"), flush=True)      # first step of the network mode: the token must not travel in an address
        if access_generated and localguard.query_access_allowed(config):
            print(i18n.t("mon.network_token", url=url + "?access=" + access_token), flush=True)      # the only place the token is shown
            print(i18n.t("mon.network_token_deprecated"), flush=True)
        elif access_generated:
            print(i18n.t("mon.network_token_post", url=url, token=access_token), flush=True)
    if config.get("webhook", {}).get("enabled") is True:
        from github_actions_monitor.security import webhook
        print(i18n.t("mon.webhook", status=webhook.status_text(config)))
    from github_actions_monitor.util import banner
    banner.set_title(banner.window_title(LITE["on"], server.server_address[1], i18n.t))
    print(banner.line(LITE["on"], server.server_address[1], CONFIG_FILE.name, i18n.t, url, sentinel=not LITE["on"] and config.get("sentinel", {}).get("enabled", True) is not False))
    print(i18n.about_line())      # author and licence only: the version is in the banner line above, once
    print(i18n.t("mon.started", url=url))
    try:      # the notice of a new version never stops the start (a damaged state file, no network)
        news = updatecheck.notice(update_info(), i18n.t) if updatecheck.settings(config)["check"] else ""
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
        news = ""
    if news:
        print(news)
    if not args.no_browser and config.get("open_browser", True) is True:
        webbrowser.open(url + ("?access=" + access_token if access_generated and localguard.query_access_allowed(config) else ""))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
