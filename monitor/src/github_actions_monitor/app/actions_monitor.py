#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Live monitor of GitHub Actions for the repositories of one GitHub account ("github_owner" in actions_monitor.json; default: the account of `gh`).

Starts a small web server that only listens on this PC (127.0.0.1) and opens a page
with what is running right now (runs, jobs and steps), the history, charts, the
unresolved failures and the open build-failed / build-stuck issues. Nothing is written
to GitHub and no secret is read: it only asks the `gh` command line (already logged in)
for public run data.

  py -3 bin/actions_monitor.py [--port 8765] [--no-browser] [--discover]      (the default port is `ports.complete` of the configuration file, 8765 unless it says another)

The repositories to watch, the refresh times and the "stuck" limit live in
actions_monitor.json next to this file (created on the first run):
  "repos": "all" or a list of names      "ecosystems": "all" or a list of ecosystem names of the ecosystems file (with "all" repos)
  "exclude": [names to skip]             "mode": "full" or "lite"
  "github_owner": the account to watch   "language": en | es | de | fr | it | ja | zh | pt (default: the system language)
Repositories with something running, a recent push or a failing last run are refreshed every
cycle ("hot"); the others only every cold_refresh_seconds with fewer runs, so ~130 repositories
do not use up the GitHub allowance shared with the agents.
"""
from github_actions_monitor.app import api_spec, api_v1
from github_actions_monitor.app import codestale
from github_actions_monitor.app import selfwatch  # noqa: E402
from github_actions_monitor.app import degraded
from github_actions_monitor.app import viewers
from github_actions_monitor.app import lastpicture
from github_actions_monitor.app import cycle_watch
import argparse
import hmac
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
import urllib.parse
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from github_actions_monitor.data_pipeline import analytics, timesaved
from github_actions_monitor.data_pipeline import backpressure, quota_buckets, tickstats
from github_actions_monitor.integrations import notify_dedupe  # noqa: F401 - its ledger file is one of the state files an account child redirects
from github_actions_monitor.data_pipeline import activity
from github_actions_monitor.data_pipeline import fork_ci
from github_actions_monitor.data_pipeline import discovery
from github_actions_monitor.data_pipeline import etagcache, knownstates
from github_actions_monitor.data_pipeline import eventfeed, githubstatus, redeliver
from github_actions_monitor.security import wsforward
from github_actions_monitor.integrations import heartbeat
from github_actions_monitor.data_pipeline import graphql_checks
from github_actions_monitor import i18n
from github_actions_monitor.security import auth_http
from github_actions_monitor.security import envguard
from github_actions_monitor.security import localguard
from github_actions_monitor.app import modes
from github_actions_monitor.app import orglogo, screenmenu, screens
from github_actions_monitor.util import exclusive
from github_actions_monitor.util import platform_compat
from github_actions_monitor.util import ports
from github_actions_monitor.app import qaprofile
from github_actions_monitor.data_pipeline import causes
from github_actions_monitor.data_pipeline import alertflow
from github_actions_monitor.data_pipeline import paging
from github_actions_monitor.data_pipeline import redrule
from github_actions_monitor.data_pipeline import stuckrule
from github_actions_monitor.integrations import remote_workflows, runner_model
from github_actions_monitor.data_pipeline import workflow_scope
from github_actions_monitor.data_pipeline import sampling
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
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
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
    "workspace_root": "", "audit_dir": "", "signed_dir": "",      # "" = look for them (the environment, then the folder that holds the repositories): workspace.py
    "alerts": {"silences_expire_days": 0, "silences": [], "service": {"enabled": False, "failures": 3, "rate_percent": 0, "workflows": []}, "group": {"by_commit": False, "min": 3}, "digest": {"minutes": 0, "threshold": 10}},      # what reaches the channels when there are many alerts (alertflow.py): all off or empty
    "ci": {"red_events": ["push", "schedule", "workflow_dispatch", "merge_group", "workflow_run", "repository_dispatch"], "count_fork_runs": False, "automation_counts": False, "inactive_days": 90, "dormant_repos": True, "forks_need_own_ci": True, "fork_own_ci_days": 90, "red_ages": True, "red_age_days": 30, "stale_result_hours": 0, "disabled_apart": True, "dependabot_alerts": True, "copilot_alerts": False, "extra_branches": [], "branches_by_repo": [], "rerun_timing": False, "group": {"reusable": False, "min": 2}, "failed_jobs": {"enabled": False, "max_per_cycle": 4, "group_by": "auto"},
           "reusable_out_of_rankings": False, "orphan_workflows": False, "stuck": {"learned": False, "percentile": 95, "margin": 2.0, "min_samples": 3, "min_minutes": 30, "max_minutes": 720, "queue_minutes": 0, "workflow_minutes": [], "runner_minutes": [], "awaiting_stuck": True, "ghost_enabled": True, "ghost_days": 7, "no_runner_check": False}},      # which runs may make a branch red (redrule.py)
    "watchdog_minutes": 10,      # a refresh cycle that runs longer than this is dumped to the log and restarted in a new thread (0 = off)
    "watchdog_max_abandoned": 8,      # calls to GitHub that gave up waiting but never returned: with this many still alive no new call is started and the health check says so (0 = no limit)
    "runs_per_repo": 20,
    "cold_runs_per_repo": 5,
    "hot_hours": 3,
    "max_workers": 20,
    "min_rate_remaining": 800,
    "report_history_days": 30,   # (before 1.5.0: parte_history_days, still read)
    "sentinel": {"enabled": True},
    "ai": {"provider": "none"},
    "webhook": {"enabled": False, "secret_env": "MONITOR_WEBHOOK_SECRET", "replay_seconds": 3600, "max_per_minute": 30, "max_bad_per_minute": 120, "max_verified_per_minute": 120, "reject_stale": False, "persist_deliveries": True, "clock_skew_s": 300, "max_body_kb": 1024, "queue_max": 500, "stale_after_h": 6,
                "transport": "http", "ws_targets": [], "ws_max_targets": 10, "ws_cleanup": False, "redeliver": {"enabled": False, "hooks": [], "max_per_run": 20, "max_age_hours": 24, "interval_minutes": 60}},   # optional signed webhook receiver on 127.0.0.1, see webhook.py (off by default; the secret is only in the environment)
    "events_feed": {"enabled": False, "interval_seconds": 60, "owner_kind": "auto", "max_per_tick": 20},      # optional: the events of the account read with an ETag, to read only the repository that changed (eventfeed.py)
    "github_status": {"enabled": False, "interval_seconds": 300, "mark_reds": True, "quiet_notices": False},      # optional: the state of GitHub (githubstatus.com) in the bar, and the reds that appear during an incident of Actions (githubstatus.py)
    "heartbeat": {"enabled": False, "url_env": "MONITOR_HEARTBEAT_URL", "interval_seconds": 300, "send_state": True, "fail_suffix": ""},      # optional: a ping to an outside service that raises the alarm when the monitor stops (heartbeat.py)
    "chatops": {"enabled": False, "slack": {"enabled": False, "signing_secret_env": "MONITOR_SLACK_SIGNING_SECRET"}, "discord": {"enabled": False, "public_key_env": "MONITOR_DISCORD_PUBLIC_KEY"}, "allowed_teams": [], "allowed_channels": [], "allowed_users": [],
                "allowed_words": ["help", "status", "alerts", "red", "queue", "score"], "max_rows": 8, "show_repo_names": "all", "links": True, "max_age_seconds": 300, "rate_per_user_per_minute": 6, "rate_per_channel_per_minute": 20, "rate_per_minute": 60},   # read only commands from Slack and Discord, see chatops/inbound.py (off by default; the proofs are only in the environment)
    "config_check": {"strict": False},      # OFF: a key nobody reads, a wrong type or a number out of range is named at the start; ON: the monitor refuses to start (configcheck.py)
    "cache": {"etag": {"enabled": True, "ttl_hours": 24, "skip_stateful": True, "revalidate_active": True}, "negative_ttl_s": 300, "heavy_fresh_s": 5, "stale_serve_h": 1},   # conditional reads: a 304 answer costs no quota; a refusal is remembered for negative_ttl_s seconds (etagcache.py)
    "cli": {"prefer_v1": True, "default_format": "text", "status_codes": "classic", "watch": {"min_interval_seconds": 2, "default_interval_seconds": 5, "branch_timeout_seconds": 900}},      # the command line (cli/formats.py, cli/watch.py): the format of the answers when no --format is given, and the interval of `watch`
    "kiosk": {"enabled": False, "font_scale_percent": 150, "high_contrast": False, "rotate_views": False, "rotate_seconds": 30, "safe_margin_percent": 0, "scale_with_window": False},      # the profile for a TV or a wall (surfaces/kiosk.py): ?kiosk=1 only counts when enabled
    "expected_red": {"enabled": False, "max_days": 30},      # a workflow known to be red for a while, marked with a reason, an owner and an end (data_pipeline/expected_red.py): listed apart, not alerted until the mark runs out
    "audit_feed": {"clone_alert": {"enabled": False, "threshold": 5, "window_hours": 24, "bot_patterns": ["-bot", "_bot", "deploy", "guardian"], "check_minutes": 30}},      # one person who clones many different repositories (sentinels/clone_anomaly.py)
    "pwa": {"enabled": False, "refresh_on_return": True},      # the monitor as an installable app (surfaces/pwa.py): manifest, service worker (only the offline page and the icons) and a refresh when the app returns to the front
    "pairing": {"enabled": False, "code_minutes": 5, "max_devices": 10, "device_days": 90},      # phones and tablets that join the network mode with a one-use code shown as a QR code (security/devices.py)
    "startup": {"resume_max_age_hours": 12},   # the last picture is shown at once after a restart, with its age (lastpicture.py); 0 = off
    "display": {"timezone": "local", "blink_red_tiles": True, "live_throttle_s": 30, "whats_new": True, "density": "normal", "reduce_motion": "auto", "palette": "default"},   # blink_red_tiles: the red tiles and red items of the bar blink softly until the cause is solved; zone of the times written for people (log, reports, command line, notifications): local | utc | an IANA name such as Europe/Madrid
    "report_export": {"txt": True, "pdf": True, "json": False, "name": "monitor-{tab}-{date}", "paper": "a4", "pdf_path": "auto", "limits": True},      # save and print the report of a tab (reporting/tab_report.py): boxes marked at the start, suggested file name, paper of the PDF, way the PDF is made
    "modes": {"auto_low": True, "auto_low_enter": 1000, "auto_low_exit": 2500, "low": {"refresh_seconds": 240, "cold_refresh_seconds": 1800, "runs_per_repo": 10, "hot_hours": 2}},      # see modes.py: only what is shown in the Quota tab
    "extra_reader": {"enabled": False, "file": "", "any_folder": False},      # a second read-only account: only the PATH of the file with its token (readpool.py)
    "github_app": {"enabled": False, "app_id": "", "key_path": "", "installation_id": "", "share_reads": False},      # an optional GitHub App for the READS (its own allowance); only the PATH of the key is kept here (github_app.py)
    "central": {"source": "off", "max_age_minutes": 120, "git_dir": ""},      # the central panel of the profile repository as a base line that spends no allowance (central_source.py): off | git | http
    "ports": {"complete": 8765, "lite": 8766},      # the port of each edition (util/ports.py); --port wins, then MONITOR_PORT for the complete one
    "ui": {"orientation": "auto", "rotate_seconds": 0, "screen1_tabs": "", "screen1_orientation": "auto", "screen2_tabs": "", "screen2_orientation": "auto", "screen3_tabs": "", "screen3_orientation": "auto", "now_sort": "ecosystem", "alerts_sort": "server", "theme": "auto", "remember_folds": True, "about_org_logo": False, "compact": "auto", "palette": True},   # the screens (docs/SCREENS.md): the orientation of the page, and which tabs each /screen/N shows
    "screens": {"enabled": False, "blink": True, "blink_calm_minutes": 30, "rotate_seconds": 0, "default_theme": "inherit", "default_density": "normal", "refresh_seconds": 10, "burn_in_protection": True, "night_dim": False, "night_dim_from_hour": 22, "night_dim_to_hour": 7, "show_repo_names": "public", "sound": False, "sound_voices": "", "sound_volume": 0,
                "theme_overview": "inherit", "theme_fleet": "inherit", "theme_now": "inherit", "theme_sentinels": "inherit", "mode": "three", "rotate_every_seconds": 20, "alert_hold_seconds": 30, "logo_overview": True, "logo_fleet": False, "logo_now": False, "logo_sentinels": False,
                "logo_corner": "top-right", "logo_max_width": 160, "logo_max_height": 64, "group_map": True,
                "menu": True, "menu_target": "new", "menu_max_windows": 4, "menu_rotate_seconds": 20, "menu_tv_scale": 1.5, "safe_margin_percent": 0,
                "life": True, "glance_seconds": 3, "transition": "fade", "hide_healthy": False, "idle_dim_minutes": 0, "min_font_px": 12, "version_check_seconds": 300},   # the wall screens /screen/overview, /screen/now and /screen/sentinels (docs/SCREENS.md, screens.py): read only, from what the monitor already holds
    "sound": {"enabled": True, "on_new_red": True, "on_connection_lost": True, "on_warning": True, "on_resolved": True, "on_report": True, "on_lesson": True, "on_sentinel": True, "on_stuck": True, "on_score_drop": True, "on_info": True, "on_live_recovered": True, "cooldown_seconds": 30, "volume": 40, "server_beep": False, "theme": "classic", "quiet_enabled": False, "quiet_from_hour": 22, "quiet_to_hour": 7, "voices": "", "ambient": False, "ambient_volume": 10, "tick": False, "tick_seconds": 1},   # the "bing bing" of the page (soundalert.py: server_beep is the one for when the page is closed, off)
    "mcp": {"prompts": True, "write_tools": False},      # the MCP server (bin/mcp_server.py): guided prompts on, the governed write tool OFF (integrations/mcp_extras.py)
    "siem": {"queue_max": 500, "sinks": []},      # OFF: events towards Elasticsearch, Splunk, Loki, Sentinel, BigQuery or an HTTP receiver; each sink is enabled by hand in the file (integrations/siem.py)
    "selfwatch": {"enabled": True, "rss_warn_mb": 1024, "threads_warn": 400, "interval_seconds": 60},      # the monitor watches its own memory and threads (app/selfwatch.py)
    "updates": {"check": True, "systemd_helper": False},    # tell when a newer version is published (read only, updatecheck.py); never installs anything
    "airgapped": False,            # True: nothing is requested from the network except GitHub's data you asked for; the update check is off
    "open_browser": True,
    "modes": {"start": "normal", "default_minutes": 60, "idle_minutes": 0},     # normal | fast | turbo: see modes.py; the presets can be edited under modes.fast / modes.turbo
    "account": {"plan": "unknown"},     # free | pro | team | enterprise: the quotas of the plan come from quotas.json (quota.py)
    "quota": {"billing_api": False, "chip": True, "warn_percent": 75, "alert_percent": 90, "default_runner": "linux", "failover": False, "failover_max_age_minutes": 60},
    "session_guard": True,         # the page asks for a one-use token before it changes a setting or confirms an action
    "discovery": {"events": True, "suggest_groups": True, "auto_frequency": False, "hide": [], "skip_archived": True, "fork_policy": "show", "fork_ci_days": 90, "fork_checks_per_pass": 30},
    "auth": {"enabled": False, "session_hours": 12, "max_failed_logins": 5, "lockout_minutes": 15, "min_length": 10, "allow_bearer": False, "audit": True, "stream_revalidate_min": 10},     # OFF: one person, no login. On: users with roles once the first administrator exists (security/auth.py)
    "listen": {"network": False, "noindex": True, "trusted_proxy": False, "trusted_proxies": [], "local_port": 0, "host": "127.0.0.1", "token_env": "MONITOR_ACCESS_TOKEN", "allowed_hosts": [], "tls_cert_file": "", "tls_key_file": "", "secure_cookie": False, "proxy_public_host": "", "max_failed_attempts": 10, "query_access": False},     # OFF: only this computer. On: a private address, with an access token for every request
    "github_token": {"enabled": False, "store": "auto"},       # OFF: the monitor uses your own `gh login`. On: a token kept in the store of the system (secretstore.py)
    "github_actions": {"enabled": False, "allowed": ["rerun_failed", "cancel"], "merge_method": "squash", "require_reason": True, "operator": "", "comment_on_target": False, "preflight": True, "writer_lock": True},      # OFF: actions on GitHub, each one confirmed on its own (ghactions.py)
    "act": {"enabled": False, "allowed": [], "timeout_seconds": 900, "allow_symlinks": False},
    "dispatch": {"required_ci": ["ci.yml"]},                                 # the workflow files that must have passed on a commit before a batch is fired (gha_dispatch_all.py)         # OFF: run a workflow here with `act`, each run confirmed on its own (actlocal.py)
    "mirror": {"enabled": False, "folder": "", "max_mb": 500, "keep_days": 14, "max_per_cycle": 3},     # OFF: a local copy of the artifacts of the runs (mirror.py)
    "runners": {"enabled": False, "scope": "owner", "group_by": "none",                         # OFF: the self-hosted runners of the account (runners.py)
                "model": {"enabled": False, "jobs_per_cycle": 10, "thirdparty_labels": ["blacksmith", "buildjet", "namespace-profile", "depot", "warpbuild", "ubicloud", "runs-on", "actuated", "cirrus-runners", "codspeed"],
                          "large_labels": [], "self_labels": [], "queue_warn_minutes": 20, "runaway_runs_per_hour": 20, "runaway_ignore_events": ["pull_request", "pull_request_target"], "observed_reads_per_cycle": 0,
                          "thirdparty_usd_per_minute": 0.0, "alerts": True, "alert_level": "warning"}},      # OFF: kinds of runner, queue and cost by kind, runaway workflows, self-hosted queues (runner_model.py)
    "upstream": {"enabled": False, "refresh_hours": 12, "requests_per_hour": 6, "forks_per_request": 8, "news_days": 7, "notify": False, "repos": []},      # OFF: follow the original repository of each fork, its CI and its latest release (data_pipeline/upstream.py)
    "api": {"v1_enabled": "auto", "experimental_routes": False, "default_limit": 50, "max_limit": 200, "cursor_ttl_seconds": 900, "gzip_min_bytes": 1024},      # auto = on in the service mode, off for one person at one computer: the read API under /api/v1/ (app/api_v1.py)
    "compare": {"enabled": False, "default_window_days": 7, "default_days_filter": "all", "workdays": ["1", "2", "3", "4", "5"], "min_runs_per_window": 20, "min_days_of_history": 14, "min_resolved": 3, "min_snapshots": 12, "min_repo_runs": 3, "top_changes": 10, "include_in_report": False, "cache_seconds": 60, "progressive": False, "progressive_days": 7},      # OFF: this period against the one before (compare/): read only, from the ledger and the snapshots of the score
    "otlp": {"enabled": False, "endpoint": "", "interval_seconds": 60, "cicd_conventions": False, "job_spans": False},       # OFF: OpenTelemetry export to a collector you name (otlp.py)
    "organizations": {"discover": False},                                    # OFF: list the organisations of the login (orgs.py)
    "finops": {"jobs_per_cycle": 0, "by_change": False, "co2": False, "co2_watts": 40, "co2_grams_per_kwh": 400},      # the cost of the minutes; by_change and co2 are estimates from the runs already held (data_pipeline/change_cost.py)
    "limits": {"warn_percent": 80, "memory_mb": 512},      # the ceilings the doctor and /metrics compare the setup with (data_pipeline/limits.py)
    "refresh": {"share_by_workflow": False, "share_seconds": 20},      # OFF: one read of a workflow for every caller that asks at the same time (data_pipeline/sharedread.py)
    "fleet": {"page_size": 50, "group_by": "ecosystem", "sort": "risk", "show_all_active": True, "labels": [], "saved_filters": [], "meta_columns": [], "meta_per_call": 20, "meta_ttl_hours": 6, "fork_behind": False, "fork_behind_per_call": 5},      # the fleet view of the Team tab (health/fleet.py)
    "network": {"use_proxy": False, "etag": True, "graphql_checks": True, "graphql_batch": 20},                                         # OFF: outgoing requests ignore the proxy variables of the environment (netguard.py)
    "ai_notify": {"enabled": False, "confirmed_provider": "", "max_calls_per_hour": 4, "cost_per_call_cents": 5, "max_cost_per_hour_cents": 50, "command": "", "timeout_seconds": 30},      # OFF: tell an external AI of a NEW real alert (ai_notify.py)
    "pagination": {"workflow_pages": 3, "job_pages": 2, "collab_pages": 3, "cursor_pages": 3},      # pages of 100 followed when a list is full, and said when something is cut (paging.py)
    "workspaces": {"list": [], "active": ""},      # OFF while the list is empty: several workspaces (name=folder), the one named in active is used (app/workspace.py)
    "backpressure": {"enabled": False, "max_reads_per_cycle": 0, "shed_percent": 150, "min_reads": 20},      # OFF: a bounded queue for the reads of a cycle, the rest waits for the next one (data_pipeline/backpressure.py)
    "sampling": {"default_branch_probe": False, "active_probe": False, "min_coverage_minutes": 30, "api_budget_per_hour": 0},      # how much of a repository the list of runs shows, a second look at the default branch, a budget of requests (sampling.py)
    "savings": {"webhook_first": False, "webhook_live_per_repo": False, "webhook_window_minutes": 60, "webhook_full_minutes": 360, "feeds": {"enabled": False, "method": "atom", "max_age_minutes": 240}},      # read less: OFF (savings.py)
    "logs": {"failed_step": {"enabled": False, "lines": 12, "max_bytes": 2000, "max_per_minute": 10}},      # the log of the failed step in the page: OFF, one press of a button, steplog.py
    "reports": {"workflow_hygiene": {"enabled": False}, "queue": {"enabled": False}, "release_view": {"enabled": False}, "supply_chain": {"enabled": False}, "max_calls_per_cycle": 4},      # four optional reports, all OFF (reports.py)
    "lessons": {"enabled": True, "allow_write": False, "retention_days": 180, "max_entries": 5000, "brief_max_bytes": 3000, "recurring_from": 2},      # the book of failures and the library of lessons (lessons.py): local, read only; writing a lesson is OFF
    "live": {"sse": {"enabled": False, "max_seconds": 3600, "max_clients": 3}},      # OFF: GET /api/live-events/stream, the live events as server-sent events (webhook.py)
    "ai_alerts": {"enabled": False, "folder": "", "brief_max_bytes": 2048, "hook": {"enabled": False, "url": "", "max_per_hour": 6},
                  "diagnose": {"enabled": False, "max_per_cycle": 3, "log_lines": 10, "max_bytes": 1500},      # OFF: reads logs of GitHub (the allowance)
                  "cascade": {"enabled": True, "map": {}},
                  "stream": {"enabled": False, "max_seconds": 3600, "max_clients": 3},      # OFF: GET /api/ai/stream
                  "briefs": {"access_log": False},      # OFF: a record of which brief of a tab was read and by whom (GET /api/ai/briefs), no secret and no text
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
LITE_SHARED = ("/api/ai/state", "/api/ai/index", "/api/ai/briefs", "/api/ai/stream", "/api/ai/brief", "/api/ai/alerts", "/api/ai/ack")      # the channels for an AI tool are the same in both editions
LITE_PATHS = ("/api/gh-action", "/api/act", "/api/credential", "/api/github-token", "/api/runners", "/api/mirror", "/api/otlp", "/api/sentinel", "/api/ai", "/api/assistant", "/api/auth", "/api/notify", "/api/score", "/api/compare", "/api/report-files", "/api/ops", "/api/audit-log", "/api/team", "/api/repos", "/api/analytics", "/api/live-events", "/api/live-status", "/api/outputs", "/api/webhook", "/api/chatops", "/api/refresh-repos", "/metrics", "/api/alerts", "/api/events", "/api/updates", "/api/pair", "/api/devices")   # they do not exist in lite


LITE_INHERIT = ("github_owner", "ecosystems", "ecosystems_file", "targets_file", "profiles_file", "exclude", "repos", "language", "runs_per_repo", "cold_runs_per_repo", "hot_hours", "stuck_minutes", "refresh_seconds", "cold_refresh_seconds")   # what a first lite start copies from actions_monitor.json
HOT_FORCED = set()    # repositories a webhook event touched: they are read again in the next cycle
HIDDEN = {"hidden": 0, "discovered": 0, "names": [], "reasons": {}}      # repositories of the account that the ecosystem filter leaves out, and how many the account has


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
RUNNERS_MEMORY_SECONDS = 300             # how long the answer of /api/runners is kept: the same as the list the model of the runners reads
RUNNERS_SEEN = {"payload": None, "at": 0.0}      # the last answer of /api/runners: the labels that only offline runners carry explain a run that waits for ever (stuckrule.py)
RUN_CACHE = {}  # repo -> {"runs": [...], "at": float, "error": str|None}
PRIVATE = set()                           # private repositories of the account (read with the listing): the only ones whose minutes cost anything
VISIBILITY = {"known": set(), "at": 0.0}  # the repositories whose visibility (public or private) was READ from GitHub; any other one is of unknown visibility and a screen treats it as private
QUOTA_ALERTS = None
DISCOVERED = {"at": 0.0, "names": [], "snapshot": {}}
FORKS = {"known": {}, "kind": None, "kind_at": 0.0, "checked": 0, "kept": 0, "left": 0, "waiting": 0}      # fork_policy: what is known about the CI of each fork (memory only)
LISTING = {"suspect": False, "verdict": "ok", "before": 0, "now": 0, "at": 0.0}      # the last verdict on the listing of the account (discovery.listing_verdict)
DISCOVERY = {"events": [], "suggestions": []}   # what the last listing of the account brought (memory only)
HOT_ONLY = {"on": False, "until": 0.0}   # "only hot" switch (memory only): cold repositories are not refreshed until `until` (one long cycle)
V1_SECRET = os.urandom(32)                # signs the cursors of /api/v1/repos; a new one at every start (a cursor lives minutes)
LIVE_CONFIG = {}                          # the config the loop runs with, for the HTTP handler


def _device_token_ok(token):
    """The token of a paired device counts as the access token while `pairing.enabled` is on (localguard.access_ok asks)."""
    from github_actions_monitor.security import devices
    cfg = devices.settings(LIVE_CONFIG or toolconfig.raw_config())
    return cfg["enabled"] and devices.valid(token, cfg)


localguard.DEVICE_CHECK["fn"] = _device_token_ok
AUTOSAVE = None                           # report_history.AutoSaver, created in main()
ETAG = {"cache": None}                    # etagcache.EtagCache (None = plain reads)
LINK = resilience.Link()                  # the connection: offline since..., back online
ANALYTICS = {"store": None, "summary": None, "at": 0.0}
LIVE_EVENTS = []                          # the newest webhook events (workflow_run / workflow_job), newest last
LIVE_TOTAL = [0]                          # how many were accepted since the start (the running number of the stream)
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
                template.update({"mode": "lite", "ecosystems": "all", "sentinel": {"enabled": False}, "webhook": {"enabled": False}, "chatops": {"enabled": False}})
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


POOL_STATUS = {"payload": None, "at": 0.0}      # the last answer of pool_status(), made by the cycle every five minutes (the Quota tab reads this)


def refresh_pool_status():
    """The cycle reads the allowance of every source (pool_status) at most every five minutes and keeps it for /api/quota-pool/status."""
    if time.time() - POOL_STATUS["at"] <= RUNNERS_MEMORY_SECONDS:
        return False
    POOL_STATUS["at"] = time.time()
    POOL_STATUS["payload"] = pool_status()
    return True


def pool_status_pending():
    """The answer of the status of the quota before the cycle has read anything: the same shape, no source yet (nothing is read to make it)."""
    return {"pending": True, "total": None, "sources": [], "recommended": {"modes.auto_low": True, "network.etag": True}, "trend": __import__("github_actions_monitor.data_pipeline.quotawatch", fromlist=["_"]).trend(),
            "savings": savings_report(LIVE_CONFIG or toolconfig.raw_config())}


def read_extra_lists(config):
    """The organisations of the account (data_pipeline/orgs.py keeps its own hour): the cycle reads them, /api/discovery only shows what was read."""
    from github_actions_monitor.data_pipeline import orgs
    if DEMO["on"] or LINK.state()["offline"]:
        return False
    orgs.view(config, lambda endpoint: gh_read(endpoint, retries=0), state_dir() / ("orgs_state_lite.json" if LITE["on"] else "orgs_state.json"), offline=False)
    return True


def pool_status():
    """What the Quota tab shows (never a token, never a path): every source with its allowance, the permissions the App was granted and the warning about a key or token file that others can read."""
    from github_actions_monitor.integrations import github_app
    from github_actions_monitor.data_pipeline import readpool
    config = LIVE_CONFIG or toolconfig.raw_config()
    out = {"total": None, "sources": [], "recommended": {"modes.auto_low": True, "network.etag": True}, "trend": __import__("github_actions_monitor.data_pipeline.quotawatch", fromlist=["_"]).trend()}
    try:
        core = gh("api", "rate_limit", retries=0, as_user=True)["resources"]["core"]
        out["sources"].append({"name": "user", "ok": True, "remaining": core["remaining"], "limit": core["limit"], "reset": core["reset"]})
    except Exception as error:   # noqa: BLE001
        out["sources"].append({"name": "user", "ok": False, "error": github_app.clean(str(error))[:120]})
    out["failover"] = __import__("github_actions_monitor.data_pipeline.failover", fromlist=["_"]).snapshot(config)
    app = github_app.status(config)
    if app.get("enabled"):
        rate = app.get("rate") or {}
        out["sources"].append({"name": "app", "ok": bool(app.get("ok")), "app": app.get("app", ""), "remaining": rate.get("remaining"), "limit": rate.get("limit"), "reset": rate.get("reset"),
                               "missing": [p for p, v in (app.get("permissions") or {}).items() if v == "missing"], "error": app.get("error", ""), "warning": app.get("warning", ""), "openssl": app.get("openssl"), "openssl_path": app.get("openssl_path", "")})
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
    live = [s for s in out["sources"] if s.get("ok") and isinstance(s.get("remaining"), int)]
    if len(live) > 1:
        out["total"] = {"remaining": sum(s["remaining"] for s in live), "limit": sum(s["limit"] for s in live), "sources": len(live)}
    out["savings"] = savings_report(config)
    return out


def savings_report(config):
    """What each way of reading less has spared since the monitor started (about one call of the API per spared read), and whether it is on: the Quota tab shows it."""
    from github_actions_monitor.data_pipeline import savings
    cfg = savings.settings(config)
    figures = savings.stats(config)
    graphql = graphql_checks.stats(config) or {}
    etag = ETAG["cache"].stats() if ETAG["cache"] else None
    return {"ways": [{"id": "etag", "on": bool(config.get("network", {}).get("etag", True)), "spared": (etag or {}).get("saved", 0), "saved": (etag or {}).get("saved", 0), "calls": (etag or {}).get("calls", 0),
                      "no_etag": (etag or {}).get("no_etag", 0), "invalid": (etag or {}).get("invalid", 0), "hit_pct": (etag or {}).get("hit_pct"), "recent_cycles": (etag or {}).get("recent_cycles", [])[-10:]},
                     {"id": "graphql", "on": graphql_checks.settings(config)["enabled"], "spared": max(0, graphql.get("repos", 0) - graphql.get("calls", 0))},
                     {"id": "webhook", "on": cfg["webhook_first"], "spared": figures["webhook"]},
                     {"id": "feed", "on": cfg["feeds"]["enabled"] and cfg["feeds"]["method"] in ("atom", "auto"), "spared": figures["feed"]},
                     {"id": "git", "on": cfg["feeds"]["enabled"] and cfg["feeds"]["method"] in ("git", "auto"), "spared": figures["git"]},
                     {"id": "central", "on": (config.get("central") or {}).get("source", "off") != "off", "spared": 0}],
            "total": figures["total"], "unknown": figures["unknown"]}


def quota_chip_on(config):
    """`quota.chip` (on by default): the chip of the header shows the tightest bucket of the allowance."""
    block = config.get("quota") if isinstance(config, dict) and isinstance(config.get("quota"), dict) else {}
    return block.get("chip", True) is not False


def rate_probes(config):
    """{"user": {...}, "app": {...}, "extra": {...}}: the allowance of each source that is on, from the free call `rate_limit` (each answers for its own token). A source that cannot answer is left out."""
    from github_actions_monitor.data_pipeline import readpool
    out = {}
    for name in readpool.available(config) if len(readpool.available(config)) > 1 else ["user"]:
        try:
            resources = gh("api", "rate_limit", retries=0, source=name)["resources"] if name != "user" else gh("api", "rate_limit", retries=0, as_user=True)["resources"]
            core = resources["core"]
        except Exception:   # noqa: BLE001
            if name == "user":
                raise
            readpool.note_failure(name)
            continue
        quota_buckets.note(name, resources)      # every bucket of this source, for the chip and the breakdown by account (nothing is read here that the call did not already bring)
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


def failover_wanted():
    try:
        from github_actions_monitor.data_pipeline import failover
        return failover.settings(LIVE_CONFIG or toolconfig.raw_config())["failover"]
    except Exception:   # noqa: BLE001 - the switch never stops a read
        return False


def remember_good(args, data):
    """With quota.failover on, keeps the last good answer of a read of the API (memory only) so that it can be served when every source is spent."""
    if args and args[0] == "api" and failover_wanted():
        from github_actions_monitor.data_pipeline import failover
        failover.remember("|".join(str(a) for a in args), data)


def failover_step(args, name, error, tried):
    """quota.failover (off by default): a READ that failed because the allowance of its source is over is made once more with another source that can read ({"name", "via"}); when every source is spent
    the last good copy no older than quota.failover_max_age_minutes is served ({"data"}). None = nothing to do and the usual handling goes on. A limit is never taken for a refusal."""
    try:
        from github_actions_monitor.data_pipeline import failover, readpool
        from github_actions_monitor.integrations import github_app
        config = LIVE_CONFIG or toolconfig.raw_config()
        if not failover.settings(config)["failover"] or not failover.is_limit(error) or not github_app.is_read(args):
            return None
        readpool.note_spent(name)
        for other in failover.others(readpool.available(config), tried):
            via = readpool.env_for(config, other)
            if other == "user" or via:
                tried.add(other)
                failover.switched(name, other)
                return {"name": other, "via": via}
        key = "|".join(str(a) for a in args)
        copy = failover.recall(key, config) if args and args[0] == "api" else None
        if copy:
            failover.served(copy, key)
            return {"data": copy[0]}
    except Exception as problem:   # noqa: BLE001 - the switch never stops a read
        degraded.note("quota.failover", problem)
    return None


def gh(*args, timeout=40, retries=2, as_user=False, source=None):
    """Runs `gh` with a fixed argument list (no shell). Retries slow or flaky answers, not auth errors. The READS are spread over the sources of the pool (user, GitHub App, second read-only account); a source
    that is refused is left out for a while and the same read is made with the next one, the user last."""
    last = ""
    name, via = ("user", {}) if as_user else read_source(args, source)
    tried = {name}
    attempt, attempts = -1, retries + 1
    while attempt + 1 < attempts:
        attempt += 1
        try:
            CALLS["n"] += 1      # the calls of this monitor: the trend of the consumption tells them from the ones other tools make (quotawatch.py)
            extra = via or secretstore.gh_kwargs()
            result = cycle_watch.bounded(lambda: subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout, **extra), timeout + 15, abandoned_limit(None))      # a child that keeps its pipes open cannot hold the loop
        except subprocess.TimeoutExpired:
            last = "timeout"
            time.sleep(resilience.backoff(attempt))
            continue
        if result.returncode == 0:
            data = json.loads(result.stdout) if result.stdout.strip() else None
            if data is not None and not as_user and not source:
                remember_good(args, data)
            return data
        last = (result.stderr or result.stdout).strip()[:300]
        if not as_user and not source:
            moved = failover_step(args, name, last, tried)      # the allowance of this source is over: another one, then the last good copy
            if moved is not None:
                if "data" in moved:
                    return moved["data"]
                name, via = moved["name"], moved["via"]
                attempts += 1
                continue
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
        done = cycle_watch.bounded(lambda: subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **extra), timeout + 15, abandoned_limit(None))
        return done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


def report_config_problems(config):
    """Names what the configuration file has that nobody reads (a typo), a value of the wrong type and a number out of range, one line each. False when `config_check.strict` is on and there is something
    to say (the monitor must not start); True otherwise. A check that itself fails never stops the start."""
    from github_actions_monitor.app import configcheck
    try:
        found = configcheck.check(toolconfig.raw_config())
        clashes = configcheck.conflicts(toolconfig.raw_config())
        strict = configcheck.settings(toolconfig.raw_config())["strict"]
    except Exception as error:   # noqa: BLE001 - a notice never stops the start
        degraded.note("start.configcheck", error)
        return True
    for item in found[:20]:
        close = item["hint"]
        print(i18n.t("mon.config_" + item["problem"], path=item["path"], hint=(" - " + i18n.t("mon.config_did_you_mean", name=close)) if close else ""), flush=True)
    for clash in clashes[:20]:
        print(i18n.t("mon.conflict_" + clash["id"], paths=", ".join(clash["paths"])), flush=True)
    if (found or clashes) and strict:
        print(i18n.t("mon.config_strict", n=len(found) + len(clashes)), flush=True)
        return False
    return True


def credential_fingerprint():
    """The short fingerprint of the credential `gh` runs with (the stored token, else the own login of `gh`): the key of every entry of the conditional-read cache (etagcache.py)."""
    return etagcache.fingerprint(((secretstore.gh_kwargs().get("env") or {}).get("GH_TOKEN")) or "")


def failover_read(endpoint, error):
    """The conditional read met the end of the allowance of the user (quota.failover on): the same read with another source, else the stored answer with its age. {"data"} or None."""
    try:
        from github_actions_monitor.data_pipeline import failover, readpool
        config = LIVE_CONFIG or toolconfig.raw_config()
        if not failover.settings(config)["failover"] or not failover.is_limit(error):
            return None
        readpool.note_spent("user")
        for other in failover.others(readpool.available(config), {"user"}):
            if not readpool.env_for(config, other):
                continue
            try:
                data = gh("api", endpoint, retries=0, source=other)
            except Exception:   # noqa: BLE001 - this source failed too: the next one, then the copy
                readpool.note_spent(other)
                continue
            failover.switched("user", other)
            return {"data": data}
        held = ETAG["cache"].last_copy(endpoint) if ETAG["cache"] is not None else None
        if held and held[1] <= failover.settings(config)["failover_max_age_minutes"] * 60:
            failover.served(held, endpoint)
            return {"data": held[0]}
    except Exception as problem:   # noqa: BLE001 - the switch never stops a read
        degraded.note("quota.failover", problem)
    return None


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
            moved = failover_read(endpoint, last)
            if moved is not None:
                return moved["data"]
            if attempt < retries:
                time.sleep(resilience.backoff(attempt) if resilience.is_transient(last) else secondary_wait(last, attempt, random.random()))
    raise RuntimeError(last or "gh failed")


MAX_STEP_NAMES = 200      # names of step kept for each workflow in the statistics


def parse_time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if text else None
    except (TypeError, ValueError):      # a date that is not one (a run from an event with a wrong shape) is no date: it never stops a cycle
        return None


def seconds_between(start, end):
    if not start:
        return 0
    end = end or datetime.now(timezone.utc)
    return max(0, int((end - start).total_seconds()))


def ecosystem_of(name):
    return toolconfig.ecosystem_of(name)


def read_visibility(config, force=False):
    """With a list of repositories written by hand nothing tells which ones are private: read it once per `discover_refresh_seconds` with one listing of the account (names and visibility). Whatever fails
    leaves the visibility unknown, which is the same as private for everything that shows a name to other people; the listing is never retried before the next refresh time."""
    if not force and time.time() - VISIBILITY["at"] <= config["discover_refresh_seconds"]:
        return
    VISIBILITY["at"] = time.time()
    try:
        data = gh("repo", "list", toolconfig.github_owner(config), "--limit", str(config.get("discover_limit", 1000)), "--json", "name,isPrivate", retries=0) or []
    except Exception:   # noqa: BLE001 - a failed reading only leaves the visibility unknown
        return
    PRIVATE.clear()
    PRIVATE.update(item["name"] for item in data if isinstance(item, dict) and item.get("isPrivate"))
    VISIBILITY["known"] = {item["name"] for item in data if isinstance(item, dict) and isinstance(item.get("name"), str) and "isPrivate" in item}


def watched_repos(config, force=False):
    """The list from the config file or, with "repos": "all", the repositories of the account (one call, cached)."""
    wanted = config["repos"]
    if wanted != "all":
        names = list(wanted)
        read_visibility(config, force)
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
            before = len(DISCOVERED.get("snapshot") or {})
            verdict = discovery.listing_verdict(before, len(data), rules["min_keep_pct"])
            if verdict != "ok":      # an empty listing, or one that lost most of the repositories, is read once more before it is believed
                try:
                    again = gh("repo", "list", toolconfig.github_owner(config), "--limit", limit, "--json", "name,isArchived,isFork,isPrivate,isEmpty", retries=0) or []
                except AuthError:
                    raise
                except Exception:   # noqa: BLE001 - the second look failed: the last good listing stays
                    again = []
                if discovery.listing_verdict(before, len(again), rules["min_keep_pct"]) == "ok":
                    data, verdict = again, "ok"
            if verdict != "ok":
                LISTING.update({"suspect": True, "verdict": verdict, "before": before, "now": len(data), "at": time.time()})      # the last good listing stays; the doctor of the brief says so
                DISCOVERED["at"] = time.time() - max(0, config["discover_refresh_seconds"] - 300)      # asked again in five minutes, not in the next cycle
            else:
                LISTING.update({"suspect": False, "verdict": "ok", "before": before, "now": len(data), "at": time.time()})
                PRIVATE.clear()
                PRIVATE.update(item["name"] for item in data if item.get("isPrivate"))
                VISIBILITY["known"] = {item["name"] for item in data if "isPrivate" in item}      # the plain listing of an older gh has no such field: nothing is known then
                snapshot = {item["name"]: {"archived": bool(item.get("isArchived"))} for item in data}
                if rules["events"]:
                    found = discovery.diff(DISCOVERED.get("snapshot"), snapshot)
                    if found:
                        announce_discovery(found, config)
                DISCOVERED["snapshot"] = snapshot
                items = [dict(item, isArchived=bool(item.get("isArchived"))) for item in data if not item.get("isArchived") or not rules["skip_archived"]]
                answers = fork_ci_answers(config, rules, items)
                DISCOVERED["names"] = sorted(discovery.lifecycle(items, config.get("discovery") or {}, answers))
                DISCOVERED["reasons"] = discovery.exclusions(items, config.get("discovery") or {}, answers)
                DISCOVERED["at"] = time.time()
        known = toolconfig.ecosystem_names(config)
        wanted_eco = config["ecosystems"]
        allowed = set(known if wanted_eco in ("all", None) else wanted_eco)
        unclassified = config.get("show_unclassified", True) is True and wanted_eco in ("all", None)
        names = [n for n in DISCOVERED["names"] if not known or ecosystem_of(n) in allowed or n == toolconfig.github_owner(config) or (unclassified and ecosystem_of(n) == "other")]   # no ecosystems file: every repository
        kept = set(names)
        left_out = [n for n in DISCOVERED["names"] if n not in kept]
        HIDDEN["discovered"], HIDDEN["hidden"], HIDDEN["names"] = len(DISCOVERED["names"]), len(left_out), left_out[:50]
        HIDDEN["reasons"] = dict(DISCOVERED.get("reasons") or {})
        if discovery.settings(config)["suggest_groups"]:
            DISCOVERY["suggestions"] = discovery.suggest_groups([n for n in DISCOVERED["names"] if ecosystem_of(n) in ("other", "rest")], taken=set(known))
    skip = set(config["exclude"])
    valid = [n for n in names if NAME_RE.match(n) and n not in skip]
    for n in names:
        if not NAME_RE.match(n):
            print(i18n.t("mon.bad_repo_name", name=repr(n)[:60]))
    return valid


RUN_SUMMARY = {"by_repo": {}}      # repo -> counts over ALL the runs of the last cycle (health/repo_view.summarize_runs): the page only receives the 600 newest ones, the health must not
ALL_RUNS = {"runs": []}      # every run the last cycle read, before the page's cut to 600: the score, the reports, the mirror and the analytics read it when score.source is "ledger" (source_runs)
SAMPLE_INFO = {}      # repo -> {"asked": runs asked for, "total": total_count of GitHub or None, "probe": runs only the second look found}
SAMPLING_STATE = {"dropped": []}      # the repositories that waited in the last cycle because the budget of requests was spent
BUDGET = sampling.Budget()      # requests for run lists in the last hour
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}\Z")


def fork_ci_answers(config, rules, items):
    """{fork name: True | False | None}: only asked when the policy is skip_unless_ci or auto, a few forks per listing (the answer is kept for a week), never in the demo."""
    if rules["fork_policy"] not in ("skip_unless_ci", "auto") or DEMO["on"]:
        FORKS.update({"checked": 0, "kept": 0, "left": 0, "waiting": 0})
        return {}
    reader = lambda endpoint: gh_read(endpoint, retries=0)      # noqa: E731
    owner = toolconfig.github_owner(config)
    if rules["fork_policy"] == "auto" and (FORKS["kind"] is None or time.time() - FORKS["kind_at"] > 86400):
        FORKS["kind"], FORKS["kind_at"] = discovery.owner_kind(reader, owner), time.time()
    days = discovery.fork_window(rules, FORKS["kind"])
    forks = [item["name"] for item in items if item.get("isFork")]
    answers = discovery.check_forks(forks, FORKS["known"], reader, owner, days, rules["fork_checks_per_pass"])
    FORKS.update({"checked": sum(1 for v in answers.values() if v is not None), "kept": sum(1 for v in answers.values() if v is True),
                  "left": sum(1 for v in answers.values() if v is False), "waiting": sum(1 for v in answers.values() if v is None)})
    return answers


MAX_RUN_SECONDS = 35 * 86400      # GitHub stops a run after 35 days: a longer figure is a wrong clock (a re-run measured from the first attempt), not a long build
TIMING_PER_READ = 3      # requests for the duration of a re-run that one reading of one repository may make
TIMING = {"on": False, "known": {}}      # ci.rerun_timing: ask GitHub for the real duration of a re-run (runs/ID/timing), a few calls per read of a repository


def run_times(run):
    """(queued, seconds, started) of one run of the API, measured on the LATEST ATTEMPT: `created_at` belongs to the first attempt and stays when somebody re-runs the workflow days or months later, so
    it is only used for the first attempt; from the second one on the time of the attempt is `run_started_at` and the wait in the queue is unknown (None), never "the days since the first try".
    A duration longer than a run can last (35 days) is unknown too (None)."""
    attempt = run.get("run_attempt") if isinstance(run.get("run_attempt"), int) and run.get("run_attempt") >= 1 else 1
    first = run.get("created_at")
    begun = run.get("run_started_at") or (first if attempt == 1 else None)
    started, updated = parse_time(begun), parse_time(run.get("updated_at"))
    finished = run.get("status") == "completed"
    queued = seconds_between(parse_time(first), started) if attempt == 1 and first and run.get("run_started_at") else None
    seconds = seconds_between(started, updated if finished else None) if started else None
    if seconds is not None and seconds > MAX_RUN_SECONDS:
        seconds = None
    return queued, seconds, begun


def rerun_seconds(repo, run, allowance=None):
    """The real duration of a finished re-run from `runs/ID/timing` (wall clock of the attempt), when ci.rerun_timing is on and the allowance of this read (`allowance`, a list with the number of
    requests it may still make, one list for each reading of a repository) allows; else None."""
    key = (repo, run.get("id"), run.get("run_attempt"))
    if key in TIMING["known"]:
        return TIMING["known"][key]
    allowance = allowance if allowance is not None else [TIMING_PER_READ]
    if not TIMING["on"] or allowance[0] <= 0:
        return None
    if TIMING.get("limit") and BUDGET.used() >= TIMING["limit"]:      # the request is one of the hour: with the budget spent it is not made (it would be asked again at the next read)
        return None
    allowance[0] -= 1
    BUDGET.record(1)
    try:
        body = gh_read(f"repos/{toolconfig.github_owner()}/{repo}/actions/runs/{run.get('id')}/timing", retries=0) or {}
        ms = body.get("run_duration_ms")
        value = int(ms // 1000) if isinstance(ms, (int, float)) and not isinstance(ms, bool) and 0 <= ms <= MAX_RUN_SECONDS * 1000 else None
    except AuthError:
        raise
    except Exception:   # noqa: BLE001 - the duration of a re-run is a nicety: the page works without it
        value = None
    if len(TIMING["known"]) > 5000:
        TIMING["known"].clear()
    TIMING["known"][key] = value
    return value


def is_fork_run(run):
    """True when the head of the run lives in ANOTHER repository (a pull request from a fork): its branch name (`main`, `master`, `dev`) says nothing about the branch of this repository."""
    head, base = (run.get("head_repository") or {}).get("full_name"), (run.get("repository") or {}).get("full_name")
    return bool(head and base and str(head).lower() != str(base).lower())


def fetch_runs(repo, per_page):
    try:
        data = gh_read(f"repos/{toolconfig.github_owner()}/{repo}/actions/runs?per_page={per_page}")
    except AuthError:
        raise
    except Exception as error:  # a repo without Actions or a network problem must not stop the page
        LINK.record(str(error))
        return [], str(error)
    LINK.record(None)
    total = data.get("total_count")
    SAMPLE_INFO[repo] = {"asked": per_page, "total": total if isinstance(total, int) and not isinstance(total, bool) else None, "probe": 0}
    return parse_runs(repo, data), None


def fetch_active(repo, runs):
    """The runs of the repository that are still `in_progress` or `queued`, asked for on their own (sampling.active_probe) and joined to a full list: a long run that started before the
    window of the sample is not lost. A failed request leaves the list as it was."""
    for status in ("in_progress", "queued"):
        try:
            BUDGET.record(1)
            data = gh_read(f"repos/{toolconfig.github_owner()}/{repo}/actions/runs?status={status}&per_page=100")
        except AuthError:
            raise
        except Exception:   # noqa: BLE001 - the look at the active runs is extra: the first list stands
            continue
        runs, added = sampling.merge_probe(runs, parse_runs(repo, data))
        SAMPLE_INFO.setdefault(repo, {})["probe"] = SAMPLE_INFO.get(repo, {}).get("probe", 0) + added
    return runs


def fetch_sampled(repo, per_page, config):
    """The list of runs of a repository; with sampling.default_branch_probe on and a full list, one more request for the pushes to the default branch, joined to it (sampling.py)."""
    runs, error = fetch_runs(repo, per_page)
    wanted = sampling.settings(config)
    if error or len(runs) < per_page or not (wanted["default_branch_probe"] or wanted["active_probe"]):
        return runs, error
    if wanted["active_probe"]:
        runs = fetch_active(repo, runs)
    if not wanted["default_branch_probe"]:
        return runs, error
    branch = (repo_meta([repo]).get(repo) or {}).get("branch") or redrule.guess_default_branch(runs)
    if not branch or not BRANCH_RE.match(branch):
        return runs, error
    try:
        BUDGET.record(1)
        data = gh_read(f"repos/{toolconfig.github_owner()}/{repo}/actions/runs?branch={urllib.parse.quote(branch, safe='/')}&event=push&exclude_pull_requests=true&per_page={per_page}")
    except AuthError:
        raise
    except Exception:   # noqa: BLE001 - the second look is extra: the first list stands
        return runs, error
    merged, added = sampling.merge_probe(runs, parse_runs(repo, data))
    SAMPLE_INFO.setdefault(repo, {})["probe"] = added
    return merged, None


def parse_runs(repo, data):
    runs = []
    allowance = [TIMING_PER_READ]      # the requests for the duration of a re-run this reading of this repository may make: its own count, not one shared with the other threads of the cycle
    for run in data.get("workflow_runs", []):
        knownstates.observe(run)
        if not knownstates.is_well_formed(run):      # a run that is not an object or has no number is left out; the page goes on with the others
            continue
        full_path = str(run.get("path") or "").split("@")[0]
        queued, seconds, begun = run_times(run)
        if (run.get("run_attempt") or 1) > 1 and run.get("status") == "completed":
            seconds = rerun_seconds(repo, run, allowance) if TIMING["on"] else seconds
        runs.append({
            "repo": repo, "id": run["id"], "name": run.get("name") or "", "title": (run.get("display_title") or "")[:90],
            "event": run.get("event"), "branch": run.get("head_branch"), "fork": is_fork_run(run), "path": full_path.rsplit("/", 1)[-1], "sha": (run.get("head_sha") or "")[:7],
            "actor": (run.get("actor") or {}).get("login", ""), "actor_bot": (run.get("actor") or {}).get("type") == "Bot", "status": run.get("status"), "number": run.get("run_number"),
            "queued": queued,
            "conclusion": run.get("conclusion"), "started": begun or run.get("created_at"),
            "seconds": seconds, "url": run.get("html_url"), "attempt": run.get("run_attempt"), "reusable": causes.reusable_paths(run),
        })
        if full_path.startswith("dynamic/") or run.get("event") == "dynamic":      # a workflow GitHub makes for itself: it has no file, and the whole path says which service it is
            runs[-1]["dynamic"] = True
            runs[-1]["service"] = redrule.service_name(full_path, run.get("name"))
    return runs


AUDIT_REQUIRED_ROUTES = ("/api/alerts/mute", "/api/alerts/unmute")
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


REFRESH_COUNT = [0]      # repositories the last cycle read (the metric ghamon_tick_reads_last)


def refresh_runs(repos, config, progress=None):
    """Hot repositories every cycle with the full run list, cold ones only now and then with a short list."""
    now = time.time()
    lite = config["mode"] == "lite"
    only_hot = hot_only_state(now)["on"]
    todo = []
    cold_due = set()      # the repositories that only wait for their slow turn: the ones network.graphql_checks may read in batches
    slow = []             # the cold repositories whose slow turn has come: (name, cached entry)
    for repo in repos:
        entry = RUN_CACHE.get(repo)
        if entry and entry.get("retry_at", 0) > now:      # it failed several times in a row: it waits (the old picture stays) and the others are read
            continue
        hot = is_hot(repo, config, now)
        HOT_FORCED.discard(repo)
        if entry is None:
            todo.append((repo, config["cold_runs_per_repo"]))  # first look: a short list; the hot ones get the full list next cycle
        elif hot:
            todo.append((repo, config["cold_runs_per_repo"] if lite else tuned(config, "runs_per_repo")))
        elif not only_hot and now - entry["at"] > tuned(config, "cold_refresh_seconds"):
            if spare_by_webhook(entry, config, now, repo):      # savings.webhook_first (off by default): the slow turn passes with no call
                continue
            slow.append((repo, entry))
    if slow:
        for repo, spared in zip([r for r, _e in slow], spare_by_feed(slow, config, now)):      # savings.feeds (off by default): the newest commit from a source that costs no allowance
            if not spared:
                todo.append((repo, config["cold_runs_per_repo"]))
                cold_due.add(repo)
    done = 0
    RATE_BLOCK["unread"] = 0
    if time.time() < RATE_BLOCK["until"]:      # the allowance is still used up: nothing is asked until it renews (the old picture stays)
        RATE_BLOCK["unread"] = len(todo)
        return 0
    TIMING["on"] = isinstance(config.get("ci"), dict) and config["ci"].get("rerun_timing") is True
    TIMING["limit"] = sampling.settings(config)["api_budget_per_hour"]
    total = len(todo)
    batched = graphql_cold(config, [r for r, _n in todo if r in cold_due])
    if batched:
        BUDGET.record(1)
        for repo, runs in batched.items():
            named = {redrule.workflow_key(r) for r in runs}
            kept = [r for r in ((RUN_CACHE.get(repo) or {}).get("runs") or []) if redrule.workflow_key(r) not in named]      # the batch only sees the last commit of the branch: what it does not name (a cron, a workflow with a path filter) is kept
            note_read(repo, list(runs) + kept, None)
        todo = [item for item in todo if item[0] not in batched]
    limit = sampling.settings(config)["api_budget_per_hour"]
    probing = sampling.settings(config)["default_branch_probe"]
    watching = sampling.settings(config)["active_probe"]

    def price(item):      # a repository whose last list was full (or never read) also gets the second look at the pushes to its default branch: two requests
        held = RUN_CACHE.get(item[0])
        full = held is None or len(held.get("runs") or []) >= item[1]
        return 1 + (1 if probing and full else 0) + (2 if watching and full else 0)
    todo, waiting = sampling.plan(todo, red_repos_of([r for r, _n in todo]) if limit else set(), limit, BUDGET.used(), price)      # a spent budget: the repositories with red first, the others wait
    SAMPLING_STATE["dropped"] = [item[0] for item in waiting]
    todo, _waiting = backpressure.plan(todo, config, hot=[r for r, _n in todo if is_hot(r, config, now)], red=red_repos_of([r for r, _n in todo]), held=RUN_CACHE,
                                     last_seconds=tickstats.STATE.get("last_seconds"), interval=config.get("refresh_seconds"))      # backpressure.enabled (off): a bounded queue, the rest waits for the next cycle
    REFRESH_COUNT[0] = len(todo)
    for start in range(0, len(todo), 40):  # chunks, so the page can show the first results while the rest loads
        chunk = todo[start:start + 40]
        with ThreadPoolExecutor(max_workers=config["max_workers"]) as pool:
            results = list(pool.map(lambda item: (item[0], *fetch_sampled(item[0], item[1], config)), chunk))
        BUDGET.record(len(chunk))
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


def red_repos_of(repos):
    """The repositories (of `repos`) whose cached runs show a red workflow on main: they are read first when the budget of requests runs short."""
    out = set()
    for repo in repos:
        entry = RUN_CACHE.get(repo)
        if entry and entry.get("runs") and redrule.red_workflows({repo: entry["runs"]}, None, True)[0]:
            out.add(repo)
    return out


HEADS_PENDING = {}      # repo -> the newest commit seen BEFORE its read, stored with the read (savings.feeds)


def spare_by_webhook(entry, config, now, repo=None):
    """True when the webhook is alive and the slow turn of this cold repository may pass without a call (savings.webhook_first). The repository keeps its runs; the full read still comes
    at the intervals `savings` sets."""
    from github_actions_monitor.data_pipeline import savings
    try:
        if savings.quiet_by_webhook(config, entry, now, repo):
            savings.count_webhook()
            entry["at"] = now
            return True
    except Exception as error:   # noqa: BLE001 - a way to save allowance never stops the cycle
        degraded.note("loop.extra", error)
    return False


def spare_by_feed(slow, config, now):
    """[bool]: for each (repo, entry) of `slow`, True when a source that costs no allowance says that nothing was pushed since its last full read (savings.feeds.*). The questions are made
    together, a few at a time. The newest commit that was seen is kept to be stored with the read the repository gets when it is not spared. Anything unknown means: read it as always."""
    from github_actions_monitor.data_pipeline import savings
    if not savings.settings(config)["feeds"]["enabled"]:
        return [False] * len(slow)
    owner = toolconfig.github_owner(config)

    def one(item):
        repo, entry = item
        try:
            if savings.feed_quiet(config, owner, repo, entry, now):
                entry["at"] = now
                return True
            sha = savings.remember_head(config, owner, repo)
            if sha:
                HEADS_PENDING[repo] = sha
        except Exception as error:   # noqa: BLE001
            degraded.note("loop.extra", error)
        return False
    with ThreadPoolExecutor(max_workers=max(1, min(8, int(config.get("max_workers") or 4)))) as pool:
        return list(pool.map(one, slow))


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
        RUN_CACHE[repo] = {"runs": runs, "at": time.time(), "full_at": time.time(), "error": None, "fails": 0, "head": HEADS_PENDING.pop(repo, "") or (entry or {}).get("head", "")}
        return
    fails = (entry or {}).get("fails", 0) + 1
    retry_at = time.time() + resilience.retry_delay(fails)      # a repository that keeps failing is left alone for a while instead of being read in every cycle
    if resilience.is_transient(error) and fails < resilience.TRANSIENT_CYCLES:
        tickstats.note_retry()
        if entry:
            entry.update({"fails": fails, "at": 0, "retry_at": retry_at})      # the old picture stays and the read is repeated in the next cycle; nothing is shown yet
        else:
            RUN_CACHE[repo] = {"runs": [], "at": 0, "error": None, "fails": fails, "retry_at": retry_at}
        return
    error = short_error(error) or "gh failed"      # one line: no legal paragraph, no request id
    if entry:
        entry.update({"error": error, "fails": fails, "retry_at": retry_at})      # keep the old runs, report the problem
    else:
        RUN_CACHE[repo] = {"runs": runs, "at": time.time(), "error": error, "fails": fails, "retry_at": retry_at}


def run_jobs(repo, run_id):
    return run_jobs_info(repo, run_id)[0]


def run_jobs_info(repo, run_id):
    """(jobs, seen, total): the jobs of a run read in pages of 100 (up to pagination.job_pages); total is what GitHub says there are, so a matrix that is cut is said ("seen 100 of 240").
    With refresh.share_by_workflow on, the callers that ask for the same run at the same moment share one read (data_pipeline/sharedread.py)."""
    try:
        from github_actions_monitor.data_pipeline import sharedread
        return sharedread.read(LIVE_CONFIG or toolconfig.raw_config(), f"jobs:{repo}:{run_id}", lambda: _run_jobs_info(repo, run_id))
    except Exception as error:   # noqa: BLE001 - the shared reader never stops a read
        degraded.note("loop.extra", error)
        return _run_jobs_info(repo, run_id)


def _run_jobs_info(repo, run_id):
    try:
        pages = paging.settings(toolconfig.raw_config())["job_pages"]
        page = paging.read_pages(lambda path: gh("api", path, retries=1), f"repos/{toolconfig.github_owner()}/{repo}/actions/runs/{run_id}/jobs", "jobs", 100, pages)
    except Exception:
        return [], 0, None
    jobs = []
    for job in page["items"]:
        steps = job.get("steps") or []
        done = sum(1 for step in steps if step.get("status") == "completed")
        current = next((step.get("name") for step in steps if step.get("status") == "in_progress"), "")
        started = parse_time(job.get("started_at"))
        finished = parse_time(job.get("completed_at"))
        jobs.append({
            "name": job.get("name"), "status": job.get("status"), "conclusion": job.get("conclusion"),
            "steps_total": len(steps), "steps_done": done, "step": current, "runner": job.get("runner_name") or "",
            "seconds": seconds_between(started, finished) if started else 0, "url": job.get("html_url"), "labels": [str(x)[:40] for x in (job.get("labels") or [])][:12],
        })
    return jobs, page["seen"], (page["total"] if page["cut"] else None)


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
        out.extend(redrule.red_runs(items, branch))
    return out


def collect(config, publish=None):
    redrule.configure(config)
    fork_ci.configure(config)
    causes.configure(config)
    alertflow.configure(config)
    repos = watched_repos(config)
    started = time.time()

    def partial(done, total):
        if publish and not STATE.get("complete"):  # only until the first complete picture exists
            publish(build(config, repos, started, done, True, f"{done}/{total}"))

    refreshed = refresh_runs(repos, config, partial)
    return build(config, repos, started, refreshed, False, "")


def repo_meta(repos, config=None):
    """{repo: {"private": True, False or None (not read: treated as private), "branch": str or None, "pushed": ISO or None, "prs": int or None}} for the columns of the Repositories table. The visibility comes from the listing the monitor already
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
        out[repo] = {"private": True if repo in PRIVATE else (False if repo in VISIBILITY["known"] else None), "branch": item.get("branch") or None, "pushed": item.get("pushed") or None, "prs": len(prs) if isinstance(prs, list) else None, "fork": item.get("fork") is True}
        cached = RUN_CACHE.get(repo)
        if cached and cached.get("runs") is not None and cached.get("at"):
            sample = SAMPLE_INFO.get(repo) or {}      # not `info`: that name holds what the sentinel knows of every repository
            out[repo]["coverage"] = sampling.coverage(cached["runs"], sample.get("asked"), sample.get("total"), sampling.settings(config or {})["min_coverage_minutes"])
    return out


def sampling_summary(config, repos, meta):
    """The block `sampling` of the data: repositories with low coverage, the requests a setup like this spends per hour, and the budget (sampling.py)."""
    cfg = sampling.settings(config)
    low = sorted(r for r in repos if ((meta.get(r) or {}).get("coverage") or {}).get("low"))
    waiting = [r for r in SAMPLING_STATE["dropped"] if r in set(repos)]
    estimate = sampling.estimate_per_hour(len(repos), config.get("refresh_seconds") or 45, config.get("cold_refresh_seconds") or 600, probe=cfg["default_branch_probe"] or cfg["active_probe"])
    return {"low": low[:50], "low_count": len(low), "estimate_per_hour": estimate, "budget_per_hour": cfg["api_budget_per_hour"], "used_last_hour": BUDGET.used(),
            "waiting": waiting[:50], "waiting_count": len(waiting), "probe": cfg["default_branch_probe"], "min_coverage_minutes": cfg["min_coverage_minutes"]}


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
    figures = {"active": sum(1 for r in active if r.get("status") == "in_progress"), "queued": sum(1 for r in active if r.get("status") != "in_progress" and not redrule.is_awaiting(r)),
               "fail24": sum(1 for r in done if r.get("conclusion") in ("failure", "timed_out", "startup_failure")), "ok24": sum(1 for r in done if r.get("conclusion") == "success"),
               "done24": len(done), "issues": len(issues), "min24": round(sum(r.get("seconds") or 0 for r in last) / 60)}
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
    stuck_cfg = stuckrule.settings(config)
    learned = stuckrule.learn(runs, stuck_cfg) if stuck_cfg["learned"] else {}
    offline = stuckrule.offline_labels(RUNNERS_SEEN.get("payload"))
    known = stuckrule.known_labels(RUNNERS_SEEN.get("payload")) if stuck_cfg["no_runner_check"] else None
    ask_queued = [len(stuck_cfg["runner_minutes"]) > 0 or bool(offline) or known is not None, 10]      # queued runs only read their jobs (one call each) when a runner label can change the verdict
    for run in active:
        run["jobs"], seen, total = run_jobs_info(run["repo"], run["id"]) if (run["status"] == "in_progress" and not loading) else ([], 0, None)
        run["jobs_seen"], run["jobs_total"] = seen, total      # total only when the jobs were cut: "seen N of M"
        if run["status"] in stuckrule.QUEUE_STATES and ask_queued[0] and ask_queued[1] > 0 and not loading:
            ask_queued[1] -= 1
            run["jobs"] = run_jobs(run["repo"], run["id"])
        labels = sorted({label for job in run["jobs"] for label in job.get("labels") or []})
        run["stuck"], run["stuck_reason"], run["stuck_limit"] = stuckrule.evaluate(run, config["stuck_minutes"], stuck_cfg, learned, labels, offline, now=time.time(), known_labels=known)
    ghosts = [run for run in active if run.get("stuck_reason") == "ghost"]      # queued for days: GitHub never starts them; they are neither queued nor stuck, only counted apart
    if ghosts:
        active = [run for run in active if run.get("stuck_reason") != "ghost"]
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
        from github_actions_monitor.data_pipeline import readpool
        rate_sources = rate_probes(config)      # free of quota: it is also read while loading, so the allowance is on the page from the first moment
        rate = readpool.pooled(rate_sources)      # the sum of the allowances: the bar, the working modes and the pauses count against all of them
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
    figures["ghost"], figures["ghost_days"] = len(ghosts), stuck_cfg["ghost_days"]
    ghost_rows = [{"repo": r["repo"], "name": r.get("name"), "id": r.get("id"), "url": r.get("url"), "branch": r.get("branch"), "event": r.get("event"), "since": r.get("started")} for r in ghosts[:200]]
    activity_view = None
    idle_forks = []
    aged_rows, quiet_rows, expected_rows, ignored_rows = [], [], [], []
    meta = repo_meta(repos, config)
    try:
        held = redrule.states({r: [x for x in runs if x["repo"] == r] for r in repos}, {r: m.get("branch") for r, m in repo_meta(repos).items() if m.get("branch")}, True)
        figures["awaiting"], figures["inactive"] = len(held["awaiting"]), len(held["inactive"])
        expected_rows = [{k: row.get(k) for k in ("repo", "workflow", "since", "url", "streak", "conclusion", "reason", "owner", "until", "class")} for row in held["expected"]]      # red on purpose for a while (expected_red.py): listed apart
        figures["expected"] = len(expected_rows)
        figures["services_failing"] = len(held["services"])
        ignored_rows = [{"repo": row["repo"], "workflow": "%s (%s)" % (row["workflow"], row["branch"]), "since": row.get("since"), "url": row.get("url"), "branch": row["branch"]} for row in held["ignored"]]      # failures on branches nobody asked to watch: counted, not alerted
        figures["ignored"] = len(ignored_rows)
        aged_rows = [{k: row.get(k) for k in ("repo", "workflow", "since", "url", "streak", "conclusion")} for row in held["inactive"] if row.get("aged")]      # the reds that aged into "inactive" (ci.red_age_days) do not vanish without a trace
        figures["aged"], figures["aged_days"] = len(aged_rows), redrule.POLICY.get("red_age_days") or 0
        quiet_rows = [{k: row.get(k) for k in ("repo", "workflow", "since", "url", "streak", "conclusion")} for row in held["inactive"] if not row.get("aged")]      # abandoned workflows (ci.inactive_days) that failed: not red, but not hidden either
        figures["quiet"], figures["quiet_days"] = len(quiet_rows), redrule.POLICY.get("inactive_days") or 0
        for listed in (expected_rows, ignored_rows, aged_rows, quiet_rows):      # ci.stale_result_hours: a result older than that is said so (information only; a repository that could not be read is not marked)
            redrule.mark_stale(listed, errors)
        activity_view = activity.summarize(repos, {r: [x for x in runs if x["repo"] == r] for r in repos}, {r: (SAMPLE_INFO.get(r) or {}).get("total") for r in repos}, errors, time.time(), activity.settings(config))
        figures["dormant"], figures["inactive_repos"] = len(activity_view["dormant"]), len(activity_view["inactive"])
        by_repo_runs = {r: [x for x in runs if x["repo"] == r] for r in repos}
        full = {r for r in repos if (SAMPLE_INFO.get(r) or {}).get("asked") and len(by_repo_runs[r]) >= SAMPLE_INFO[r]["asked"]}
        idle_forks = fork_ci.idle_forks([r for r in repos if (meta.get(r) or {}).get("fork")], by_repo_runs, full, time.time(), dict(fork_ci.POLICY))
        figures["forks_idle"] = len(idle_forks)
    except Exception as error:   # noqa: BLE001 - a figure of the header never stops a cycle
        degraded.note("loop.extra", error)
    try:
        from github_actions_monitor.health import repo_view as health_repo_view
        RUN_SUMMARY["by_repo"] = health_repo_view.summarize_runs(runs, time.time())
    except Exception as error:   # noqa: BLE001 - the summary of the health never stops a cycle
        degraded.note("loop.summary", error)
    ALL_RUNS["runs"] = runs
    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "updated_local": tzdisplay.stamp(time.time()), "took": round(time.time() - started, 1),
        "repos": repos, "ecosystems": {repo: ecosystem_of(repo) for repo in repos},
        "runs": runs[:600], "runs_total": len(runs), "active": active, "ghosts": ghost_rows, "issues": ISSUE_CACHE["items"], "failing": unresolved_failures(runs, {r: m.get("branch") for r, m in meta.items() if m.get("branch")}),
        "errors": errors, "rate": rate, "rate_user": rate_user, "rate_sources": rate_sources, "quota_chip": quota_buckets.chip() if quota_chip_on(config) else None, "quota_trend": __import__("github_actions_monitor.data_pipeline.quotawatch", fromlist=["_"]).trend(), "stuck_minutes": config["stuck_minutes"],
        "mode": config["mode"], "refreshed": refreshed, "hot": hot, "loading": progress_text if loading else "",
        "quota_block": rate_block_state(rate), "min_rate": config["min_rate_remaining"], "paused_quota": bool(rate and rate["remaining"] < config["min_rate_remaining"]),
        "refresh_seconds": config["refresh_seconds"], "hot_only": hot_only_state(),
        "offline": LINK.state(), "etag": ETAG["cache"].stats() if ETAG["cache"] else None, "graphql": graphql_checks.stats(config),
        "listing": dict(LISTING), "drift": knownstates.drift(), "hidden": HIDDEN["hidden"], "discovered": HIDDEN["discovered"], "hidden_names": HIDDEN["names"],
        "figures": figures, "repo_meta": meta, "sampling": sampling_summary(config, repos, meta), "activity": activity_view, "forks_idle": idle_forks[:200], "forks_idle_all": idle_forks, "aged_reds": aged_rows[:100], "ignored_reds": ignored_rows[:100], "quiet_reds": quiet_rows[:100], "expected_reds": expected_rows[:100],
    }


WEBHOOK_STATS = {"accepted": 0, "bad_signature": 0, "ignored": 0, "duplicates": 0, "refused": 0, "too_big": 0, "queue_full": 0, "out_of_order": 0, "stale": 0, "last_at": None}      # deliveries seen since this process started (memory only; no payload, no secret)


def webhook_count(code, duplicate=False):
    """Counts one delivery by what the receiver answered: 200 accepted, 401 a signature that did not verify, 202 ignored (a repository that is not watched, an event that is not used, a replay), anything else refused. A 404 is the
    receiver being off: nothing arrived, so nothing is counted."""
    if code == 404:
        return
    key = "accepted" if code == 200 else "bad_signature" if code == 401 else ("duplicates" if duplicate else "ignored") if code == 202 else "refused"
    WEBHOOK_STATS[key] += 1
    if code in (413, 503):      # also counted apart: a body over the limit, an event the full queue sent back (both are in `refused` too)
        WEBHOOK_STATS["too_big" if code == 413 else "queue_full"] += 1
    if code == 200:
        WEBHOOK_STATS["last_at"] = resilience.stamp(time.time())



def webhook_status(config):
    """What the Live view says about the receiver: whether it is on, whether the secret is long enough (never the secret itself), the counters and the newest event. Read only."""
    from github_actions_monitor.data_pipeline import eventfeed
    from github_actions_monitor.security import webhook
    cfg = webhook.settings(config)
    newest = LIVE_EVENTS[-1] if LIVE_EVENTS else None
    return {"enabled": cfg["enabled"], "active": webhook.active(config), "secret_ok": len(cfg["secret"]) >= webhook.MIN_SECRET, "text": webhook.status_text(config), "stats": dict(WEBHOOK_STATS),
            "keep": webhook.live_settings(config)["live_events_keep"], "held": len(LIVE_EVENTS), "queue": webhook.INBOX.snapshot(config), "open_runs": webhook.open_count(), "feed": eventfeed.FEED.snapshot(config), "forwarders": wsforward.FORWARDERS.snapshot(config), "redelivery": redeliver.RECOVERY.snapshot(config), "secret_source": webhook.secret_source(config), "coverage": webhook.coverage(config),
            "last": ({k: newest.get(k) for k in ("repo", "workflow", "event", "status", "conclusion", "at")} if newest else None)}


def webhook_receive(config, body, headers, address=None, size=None):
    """(HTTP code, answer) for one delivery. The signature, the replay and the rate are checked at once; what an accepted event does (the live list, the run list, the analytics, the notices) is put in the
    bounded queue (`webhook.queue_max`) and applied by the worker, so GitHub is answered fast whatever the page or a notice is doing. A full queue answers 503 and forgets the delivery, so that its
    resend is not taken for a duplicate: an event is never dropped in silence. Without a worker (tests, the lite edition) the event is applied here."""
    from github_actions_monitor.security import webhook
    code, answer, repo = webhook.handle(config, body, headers, STATE["data"]["repos"] if STATE.get("data") else [], address, size=size)      # bad signatures and good ones are counted apart, in every mode
    if code == 200 and repo:
        event = headers.get("X-GitHub-Event")

        def job():
            record = webhook.parse_event(event, body)
            if record and webhook.live_settings(config)["record_events"]:
                apply_live_event(record, config)
            webhook.note_accepted()      # the coverage indicator counts it
            __import__("github_actions_monitor.data_pipeline.savings", fromlist=["_"]).note_webhook(repo=repo)      # the webhook is alive: savings.webhook_first may stretch the slow turn of the cold repositories
            webhook_settle(repo)
        if webhook.INBOX.worker:
            if not webhook.INBOX.put(job, webhook.guard_settings(config)["queue_max"]):
                webhook.forget(headers.get("X-GitHub-Delivery"), body)
                webhook_count(503)
                return 503, {"ok": False, "error": "queue_full"}
        else:
            job()
    webhook_count(code, bool(answer.get("duplicate")) if isinstance(answer, dict) else False)
    return code, answer


def webhook_sweep(config, now=None):
    """The runs an event left open for more than `webhook.stale_after_h` hours with no final event (a lost delivery) are marked obsolete in the run list and their repository is read again in the next cycle,
    which says what became of them. Returns how many."""
    from github_actions_monitor.security import webhook
    old = webhook.stale_open(config, now)
    for repo, run_id in old:
        entry = RUN_CACHE.get(repo)
        if entry is not None:
            for run in entry.get("runs", []):
                if run.get("id") == run_id and run.get("status") != "completed":
                    run["stale"] = True
            entry["at"] = 0
        HOT_FORCED.add(repo)
    WEBHOOK_STATS["stale"] += len(old)
    return len(old)


def webhook_apply(job):
    """Runs one queued job. A job that fails is counted and goes to the degraded list; it never stops the worker."""
    from github_actions_monitor.security import webhook
    try:
        job()
        webhook.INBOX.stats["done"] += 1
        return True
    except Exception as error:   # noqa: BLE001 - one bad event must not stop the others
        webhook.INBOX.stats["failed"] += 1
        degraded.note("webhook.apply", error)
        return False


def webhook_worker(config):
    """The thread that applies the queued events and, once a minute, sweeps the runs that never ended. A job that fails is counted and goes to the degraded list; it never stops the thread."""
    from github_actions_monitor.security import webhook
    last = time.time()
    while True:
        job = webhook.INBOX.take(5)
        if job is not None:
            webhook_apply(job)
        if time.time() - last >= 60:
            last = time.time()
            try:
                webhook_sweep(LIVE_CONFIG or config)
            except Exception as error:   # noqa: BLE001
                degraded.note("webhook.sweep", error)


def outside_tick(config, now=None):
    """One turn of the cheap reads that keep the monitor in step with the world, each only when it is switched on: the events of the account (which repository changed), the state of GitHub and the outside
    heartbeat. Nothing here runs in the demo. Returns what happened, for the tests: {"feed": [repositories read again], "status": "start" | "over" | "", "heartbeat": "sent" | ... | ""}."""
    out = {"feed": [], "status": "", "heartbeat": "", "redelivered": 0}
    if DEMO["on"]:
        return out
    from github_actions_monitor.integrations import notifiers
    from github_actions_monitor.security import netguard
    now = time.time() if now is None else now
    data = STATE.get("data") or {}
    if eventfeed.settings(config)["enabled"] and not (rate_block_state()["blocked"] or data.get("paused_quota")) and data.get("repos"):      # a read costs allowance only when something changed; a spent allowance is not asked
        owner = toolconfig.github_owner(config)
        names = [r.get("name") if isinstance(r, dict) else r for r in data["repos"]]
        for repo in eventfeed.FEED.tick(run_gh, owner, config, [n for n in names if isinstance(n, str)], now):
            webhook_settle(repo)      # the stored conditional reads of the repository are dropped and it is read again in the next cycle
            HOT_FORCED.add(repo)
            out["feed"].append(repo)
    if redeliver.settings(config)["enabled"] and not (rate_block_state()["blocked"] or data.get("paused_quota")):
        out["redelivered"] = redeliver.RECOVERY.run(config, run_gh, now)      # GitHub is asked to send again what never arrived (off by default: it writes to GitHub)
    if githubstatus.settings(config)["enabled"]:
        out["status"] = githubstatus.STATUS.tick(netguard.opener_for(False), config, now)
        if out["status"]:
            announce_github_status(out["status"], config)
    if heartbeat.settings(config)["enabled"]:
        healthy = LITE["on"] or health_payload(deep=True)["ok"]
        out["heartbeat"] = heartbeat.HEARTBEAT.tick(config, healthy, TOOL_VERSION, notifiers.settings(config)["allow_private_targets"], now=now)
    return out


def webhook_redeliver_now(config):
    """The operator asks now (POST /api/webhook/redeliver): the named webhooks are looked at at once, whatever the schedule, and GitHub is asked to send again what never arrived. {"asked", ...counters}."""
    asked = redeliver.RECOVERY.run(config, run_gh, force=True)
    return {"asked": asked, **redeliver.RECOVERY.snapshot(config)}


def wsforward_start(config, port):
    """Starts the forwarders of `gh webhook forward` when the receiver is on and the transport is `websocket` (once the server has its port). The temporary hooks of an earlier crash are deleted first only when
    `webhook.ws_cleanup` is on. Never raises."""
    from github_actions_monitor.security import webhook
    try:
        cfg = wsforward.settings(config)
        if DEMO["on"] or cfg["transport"] != "websocket" or not cfg["targets"] or not webhook.active(config):
            return []
        if cfg["cleanup"]:
            wsforward.cleanup(run_gh, cfg["targets"])
        started = wsforward.FORWARDERS.start(config, port)
        webhook.set_local_secret(wsforward.FORWARDERS.local_secret())
        import atexit
        atexit.register(wsforward.FORWARDERS.stop)
        return started
    except Exception as error:   # noqa: BLE001 - a forwarder that cannot start never stops the monitor
        degraded.note("webhook.forward", error)
        return []


def announce_github_status(transition, config):
    """The start and the end of an incident of GitHub Actions go to the console, the event feed and the notifications, once each. Never raises."""
    from github_actions_monitor.integrations import notifiers
    kind = "github_incident" if transition == "start" else "github_incident_over"
    info = githubstatus.STATUS.snapshot(config)
    name = (info["incidents"][0]["name"] if info["incidents"] else "") or info["description"] or "Actions"
    event = {"kind": kind, "code": kind, "level": "warn" if transition == "start" else "ok", "repo": "", "owner": "main", "url": None, "args": {"name": name},
             "text": i18n.t("evt." + kind, name=name)}
    if transition == "over":      # the notices held during the incident (github_status.quiet_notices) are told once, with how many are still red
        sentinel_now = SENTINEL["obj"]
        reds = ((getattr(getattr(sentinel_now, "feed", None), "state", None) or {}).get("reds")) if sentinel_now is not None else None
        held = githubstatus.STATUS.take_held((lambda repo, workflow: f"{repo}|{workflow}" in reds) if isinstance(reds, dict) else None)
        if held["held"]:
            event["args"].update({"held": held["held"], "still_red": held["still_red"] if held["still_red"] is not None else held["held"]})
            event["text"] = i18n.t("evt.github_incident_over_held", held=event["args"]["held"], still=event["args"]["still_red"])
    print(event["text"], flush=True)
    sentinel = SENTINEL["obj"]
    try:
        if sentinel is not None:
            sentinel.feed._append([event])
        notifiers.notify(config, event)
    except Exception as error:   # noqa: BLE001 - never stops the loop
        degraded.note("outside.announce", error)


def outside_loop(config):
    """The thread of the cheap outside reads: it looks at the settings every 15 seconds, so a switch turned on in Settings works without a restart. A failure is noted and the loop goes on."""
    while True:
        try:
            outside_tick(LIVE_CONFIG or config)
        except Exception as error:   # noqa: BLE001 - one bad turn never ends the loop
            degraded.note("outside.tick", error)
        time.sleep(15)


def outside_start(config):
    """Starts the thread once."""
    if OUTSIDE["on"]:
        return False
    OUTSIDE["on"] = True
    threading.Thread(target=outside_loop, args=(config,), name="outside-reads", daemon=True).start()
    return True


OUTSIDE = {"on": False}


def webhook_worker_start(config):
    """Starts the worker when the receiver is on (once)."""
    from github_actions_monitor.security import webhook
    if webhook.INBOX.worker or not webhook.active(config):
        return False
    webhook.INBOX.worker = True
    threading.Thread(target=webhook_worker, args=(config,), name="webhook-worker", daemon=True).start()
    return True


def apply_live_event(record, config):
    """A signed workflow_run / workflow_job event: it goes to the live list, updates the run list of the repository without a read (so no quota is used), feeds the analytics and, when a run
    ends red, the notifications. Nothing of the payload but the short validated fields is kept."""
    from github_actions_monitor.integrations import notifiers
    from github_actions_monitor.security import webhook
    known = None
    entry = RUN_CACHE.get(record["repo"])
    if record["event"] == "workflow_run" and entry is not None:
        known = next((r.get("status") for r in entry["runs"] if r.get("id") == record["run_id"] and r.get("attempt") in (None, record.get("attempt"))), None)      # a new attempt of a run starts again from queued
    if webhook.is_late(record, known):      # it says less than what is already known about this run or job (a late delivery): never a step back
        WEBHOOK_STATS["out_of_order"] += 1
        return
    webhook.note_open(record)
    keep = webhook.live_settings(config)["live_events_keep"]
    LIVE_EVENTS.append({k: v for k, v in record.items() if k in webhook.LIVE_FIELDS} | {"at": resilience.stamp(time.time())})
    del LIVE_EVENTS[:-keep]
    LIVE_TOTAL[0] += 1
    try:      # outputs.prometheus.histograms / per_runner (off by default): the histograms and the per-runner figures of the job events; never stops the event
        from github_actions_monitor.integrations import job_metrics
        job_metrics.COLLECTOR.feed(record, config)
        if (config.get("otlp") or {}).get("job_spans") is True:      # otlp.job_spans (off): the finished jobs become spans of the OpenTelemetry export
            from github_actions_monitor.integrations import otlp
            otlp.note_job(record)
    except Exception as error:   # noqa: BLE001
        degraded.note("webhook.metrics", error)
    run = webhook.as_run(record)
    entry = RUN_CACHE.get(record["repo"])
    HOT_FORCED.add(record["repo"])      # whatever the event said, the repository is read again in the next cycle (the event is the news, the read is the proof)
    if run and entry is not None:
        old = next((r for r in entry["runs"] if r.get("id") == run["id"]), None)
        if old is not None:      # the run the cycle already read keeps what the event does not say (its kind of event decides the colour; the actor, the title, the fork mark): the event only adds what is new
            if old.get("status") == "completed" and run.get("status") == "completed" and old.get("conclusion") == run.get("conclusion"):
                run = old
            else:
                run = {**old, **{k: v for k, v in run.items() if v not in ("", None) and not (k == "event" and v == "webhook")}, "conclusion": run.get("conclusion")}
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
            if name not in slot and len(slot) >= MAX_STEP_NAMES:      # a matrix that puts a number in the name of a step must not make the file grow for ever: the oldest name goes
                slot.pop(next(iter(slot)), None)
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
RUN_KINDS = {}      # run id -> minutes by kind of runner (runner_model.tally) and when the run started; filled by read_costs while runners.model is on
RUNNER_JOBS = {"rows": {}, "list": None, "list_at": 0.0}      # (repo, run id) -> the jobs of an unfinished run with their labels (runner_model.compact); the list of self-hosted runners, cached


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
        model = runner_model.settings(config)
        if model["enabled"]:      # a runner of another company is not billed by GitHub: it must not be priced as a standard one
            RUN_KINDS[run["id"]] = dict(runner_model.tally(jobs, table, runner, model), at=when.timestamp())
            jobs = [dict(j, labels=["self-hosted"]) if runner_model.kind_of(j.get("labels"), model) == "thirdparty" else j for j in jobs]
        RUN_COSTS[run["id"]] = quota.job_costs(jobs, table, runner)
        done += 1
    while len(RUN_COSTS) > 3000:
        RUN_COSTS.pop(next(iter(RUN_COSTS)))
    while len(RUN_KINDS) > 3000:
        RUN_KINDS.pop(next(iter(RUN_KINDS)))
    return done


def read_runner_jobs(config, data):
    """runners.model: reads the jobs (and their `runs-on` labels) of up to runners.model.jobs_per_cycle unfinished runs per cycle, the ones read longest ago first, and forgets the runs that are over.
    One call per run; 0 = not read. Read only."""
    cfg = runner_model.settings(config)
    if not cfg["enabled"] or cfg["jobs_per_cycle"] <= 0 or LITE["on"]:
        return 0
    now, held = time.time(), RUNNER_JOBS["rows"]
    active = {(r["repo"], r["id"]) for r in data.get("active") or [] if r.get("repo") and r.get("id")}
    for key in [k for k in held if k not in active]:
        del held[key]
    done = 0
    for key in sorted((k for k in active if now - held.get(k, {}).get("at", 0) > 120), key=lambda k: held.get(k, {}).get("at", 0)):
        if done >= cfg["jobs_per_cycle"]:
            break
        try:
            body = gh_read(f"repos/{toolconfig.github_owner(config)}/{key[0]}/actions/runs/{key[1]}/jobs?per_page=100", retries=0)
            held[key] = {"at": now, "rows": runner_model.compact(key[0], key[1], body)}
            done += 1
        except Exception:   # noqa: BLE001 - this run is tried again later
            held[key] = {"at": now, "rows": held.get(key, {}).get("rows", [])}
    return done


RUNNER_FILES = {"reader": None}      # the workflow files of the repositories with a job on a self-hosted runner (remote_workflows.Reader), for runners.model.observed_reads_per_cycle


def read_runner_workflows(config, data):
    """runners.model.observed_reads_per_cycle (0 = off): reads the workflow files of the repositories that have a job on a self-hosted runner, at most that many calls per cycle, a repository again only
    after six hours and a file only when its SHA changed. Read only. Returns the calls made."""
    cfg = runner_model.settings(config)
    if not cfg["enabled"] or cfg["observed_reads_per_cycle"] <= 0 or LITE["on"] or DEMO["on"]:
        return 0
    if RUNNER_FILES["reader"] is None:
        RUNNER_FILES["reader"] = remote_workflows.Reader(lambda endpoint: gh_read(endpoint, retries=0), lambda: toolconfig.github_owner(LIVE_CONFIG or toolconfig.raw_config()))
    reader = RUNNER_FILES["reader"]
    repos = sorted({r["repo"] for held in RUNNER_JOBS["rows"].values() for r in held["rows"] if runner_model.kind_of(r.get("labels"), cfg) == "selfhosted"})
    calls = 0
    for repo in reader.due(repos, 21600):
        if calls >= cfg["observed_reads_per_cycle"]:
            break
        calls += reader.refresh(repo, cfg["observed_reads_per_cycle"] - calls)
    return calls


def runner_list(config):
    """The self-hosted runners (runners.py) as the last cycle read them (read_runner_list); None when `runners.enabled` is off or the read failed (the model then says the reason is unknown). A request
    never reads GitHub: it is answered from this."""
    from github_actions_monitor.integrations import runners
    if not runners.settings(config)["enabled"] or DEMO["on"]:
        return None
    return RUNNER_JOBS["list"]


def read_runner_list(config, data=None):
    """The reading of the runners, done by the cycle at most every `RUNNERS_MEMORY_SECONDS`: it keeps the list for the model of the runners and the answer of /api/runners."""
    from github_actions_monitor.integrations import runners
    if not runners.settings(config)["enabled"] or DEMO["on"] or time.time() - RUNNER_JOBS["list_at"] <= RUNNERS_MEMORY_SECONDS:
        return False
    RUNNER_JOBS["list_at"] = time.time()
    repos = list(((data if isinstance(data, dict) else STATE.get("data")) or {}).get("repos") or [])
    try:
        got = runners.collect(config, lambda endpoint: gh_read(endpoint, retries=0), toolconfig.github_owner(config), repos)
        RUNNER_JOBS["list"] = None if got["errors"] and not got["runners"] else got["runners"]
        RUNNERS_SEEN["payload"], RUNNERS_SEEN["at"] = {"enabled": True, **got}, time.time()
    except Exception as error:   # noqa: BLE001
        degraded.note("runners.list", error)
        RUNNER_JOBS["list"] = None
    return True


def runner_model_payload(now=None):
    """GET /api/runners/model: the model of the runners from what the monitor holds (see runner_model.py)."""
    from github_actions_monitor.data_pipeline import quota
    config = LIVE_CONFIG or toolconfig.raw_config()
    now = time.time() if now is None else now
    data = STATE.get("data") or {}
    if not runner_model.settings(config)["enabled"]:
        return {"schema": 1, "enabled": False}
    rows = [row for held in RUNNER_JOBS["rows"].values() for row in held["rows"]]
    tallies = [v for v in RUN_KINDS.values() if v.get("at", 0) >= now - 86400]
    reader = RUNNER_FILES["reader"]
    declared = {repo: {name: runner_model.static_runs_on(text) for name, text in reader.texts(repo).items()} for repo in reader.known() if reader.state(repo)["state"] != "not_evaluable"} if reader else {}
    model = runner_model.build(config, rows, data.get("runs") or [], tallies, quota.load(), runner_list(config), now, config.get("runs_per_repo") or 0, declared, PRIVATE, set(data.get("repos") or []))
    from github_actions_monitor.integrations import job_metrics
    if job_metrics.settings(config)["per_runner"]:      # outputs.prometheus.per_runner (off): the figures of each self-hosted runner, from the signed job events
        model["per_runner"] = job_metrics.COLLECTOR.runner_stats()
    return model


def mark_alerts():
    """The alerts that come from the notes of this monitor: an "expected red" mark that ran out and the users above the threshold of clones (both off by default). Reads only memory and one small file; never raises."""
    if LITE["on"]:
        return []
    try:
        from github_actions_monitor.data_pipeline import expected_red
        from github_actions_monitor.sentinels import clone_anomaly
        account = CHILD["account"] or ""
        return expected_red.alerts(account) + clone_anomaly.alerts(account)
    except Exception as error:   # noqa: BLE001 - the list of alerts must still answer
        degraded.note("marks.alerts", error)
        return []


def clone_tick(config):
    """The audit log is read at most every `audit_feed.clone_alert.check_minutes` minutes, from a thread of its own, so that a slow answer never holds the cycle (off by default). Never raises."""
    try:
        from github_actions_monitor.sentinels import clone_anomaly
        cfg = clone_anomaly.settings(config)
        if cfg["enabled"] and clone_anomaly.due(cfg):
            threading.Thread(target=clone_anomaly.check, args=(gh_read, toolconfig.github_owner(config), cfg), name="clone-anomaly", daemon=True).start()
    except Exception as error:   # noqa: BLE001
        degraded.note("clones", error)


META = {"reader": None, "running": False, "fork_reader": None, "fork_running": False}


def meta_columns_payload():
    """GET /api/meta-columns: the columns of fleet.meta_columns and the value of each repository found so far. The reads (a few files per call, `fleet.meta_per_call`) are made by a thread of their own."""
    from github_actions_monitor.data_pipeline import meta_columns
    config = LIVE_CONFIG or toolconfig.raw_config()
    cfg = meta_columns.settings(config)
    if META["reader"] is None:
        META["reader"] = meta_columns.Reader()
    reader = META["reader"]
    with LOCK:
        repos = list((STATE["data"] or {}).get("repos") or [])
    due = 0
    if cfg["columns"] and repos and not DEMO["on"]:
        now = time.time()
        due = sum(1 for r in repos for c in cfg["columns"] if reader.due(r, c, cfg["ttl_hours"], now))
        if due and not META["running"]:
            META["running"] = True

            def work():
                try:
                    reader.fill(repos, cfg["columns"], gh_read, cfg["per_call"], cfg["ttl_hours"])
                except Exception as error:   # noqa: BLE001
                    degraded.note("meta_columns", error)
                finally:
                    META["running"] = False
            threading.Thread(target=work, name="meta-columns", daemon=True).start()
    answer = {"columns": [{"id": c["id"], "name": c["name"]} for c in cfg["columns"]], "rows": reader.rows(repos, cfg["columns"]), "pending": due, "running": META["running"]}
    behind = fork_behind_part(config, repos)
    if behind is not None:      # fleet.fork_behind (off: the key is not there)
        answer["fork_behind"] = behind
        answer["pending"] += behind["pending"]
    return answer


def fork_behind_part(config, repos):
    """The `fork_behind` part of GET /api/meta-columns while fleet.fork_behind is on, else None: {"enabled", "rows": {fork: {"state", "behind"}}, "pending"}. Only the forks of the listing the monitor already
    reads are asked about (two reads each, `fleet.fork_behind_per_call` forks a round, by a thread of its own); an answer lives `fleet.meta_ttl_hours`. Never raises."""
    from github_actions_monitor.data_pipeline import fork_behind
    cfg = fork_behind.settings(config)
    if not cfg["enabled"]:
        return None
    if META["fork_reader"] is None:
        META["fork_reader"] = fork_behind.Reader()
    reader = META["fork_reader"]
    try:
        forks = sorted(r for r, m in repo_meta(repos, config).items() if m.get("fork")) if not LITE["on"] else []
    except Exception as error:   # noqa: BLE001 - an extra column never stops the page
        degraded.note("fork_behind", error)
        forks = []
    waiting = 0
    if forks and not DEMO["on"]:
        waiting = reader.pending(forks, cfg["ttl_hours"])
        if waiting and not META["fork_running"]:
            META["fork_running"] = True
            owner = toolconfig.github_owner(config)

            def work():
                try:
                    reader.fill(forks, lambda endpoint: gh_read(endpoint, retries=0), cfg["per_call"], cfg["ttl_hours"], owner)
                except Exception as error:   # noqa: BLE001
                    degraded.note("fork_behind", error)
                finally:
                    META["fork_running"] = False
            threading.Thread(target=work, name="fork-behind", daemon=True).start()
    return {"enabled": True, "rows": reader.rows(forks), "pending": waiting}


def runner_alerts():
    """The alerts of the model of the runners, for the Alerts tab; [] while it is off. Never raises."""
    if LITE["on"]:
        return []
    try:
        config = LIVE_CONFIG or toolconfig.raw_config()
        if not runner_model.settings(config)["enabled"]:
            return []
        return runner_model.alerts(runner_model_payload(), config, CHILD["account"] or "")
    except Exception as error:   # noqa: BLE001 - the list of alerts must still answer
        degraded.note("runners.alerts", error)
        return []


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


# The POST routes that the monitor accepts only from the computer it runs on (guard + this_computer): from the network they answer 403 `local_only`. The handler reads these two lists and the generated
# references of the skills for the AIs (tools/make_skill_refs.py) read the same ones, so the table an AI reads cannot disagree with the code.
AI_MODEL_POST = ("/api/ai/models/refresh", "/api/ai/models/test", "/api/ai/models/data", "/api/ai/doctor")      # the list of models of the provider, the test of one model, the table of data, the doctor
THIS_COMPUTER_ACTIONS = ("/api/ai/actions/confirm", "/api/ai/actions/review", "/api/ai/actions/unlock", "/api/ai/test", "/api/notify/test") + AI_MODEL_POST
THIS_COMPUTER_ADVANCED = ("/api/gh-action/plan", "/api/gh-action/confirm", "/api/act/plan", "/api/act/confirm", "/api/act/stop", "/api/github-token", "/api/welcome", "/api/ai/ack", "/api/ai/lessons", "/api/ai/failures", "/api/ai/prompts/clear",
                          "/api/alerts/mute", "/api/alerts/unmute", "/api/report-files/run", "/api/report-files/summary", "/api/ops/backup", "/api/ops/purge",
                          "/api/updates/check", "/api/updates/plan", "/api/updates/apply", "/api/updates/rollback", "/api/updates/discard", "/api/webhook/redeliver", "/api/credential/probe")
THIS_COMPUTER_POST = THIS_COMPUTER_ACTIONS + THIS_COMPUTER_ADVANCED


def whole(text, default=0):
    """A whole number from a query string or a header: only the digits 0-9 and at most 15 of them. `str.isdigit()` also accepts "\u00b2" and the digits of other scripts, which `int()` refuses, and a
    number of thousands of digits is refused by `int()` too: both used to cut the connection; now they are the default."""
    text = str(text if text is not None else "").strip()
    return int(text) if re.fullmatch(r"[0-9]{1,15}", text) else default


def sentinel_reports():
    """{name: {"status", "alerts"}} of the sentinels that are switched on, for the signals of the AI (security, delivery and supply have no panel; each one tells what it could not read). Never raises."""
    out = {}
    registry = None if LITE["on"] else SENTINEL.get("registry")
    for name in (registry.names() if registry is not None else []):
        try:
            sentinel = registry.get(name)
            if name != "ci" and getattr(sentinel, "enabled", False):
                out[name] = {"status": sentinel.get_status(), "alerts": sentinel.get_alerts()}
        except Exception as error:   # noqa: BLE001 - one sentinel that fails never stops the state
            degraded.note("ai_alerts.panels", error)
    return out


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
    trend = None
    try:
        sentinel = None if LITE["on"] else SENTINEL.get("obj")
        trend = ((sentinel.snapshot() or {}).get("a3") or {}).get("trend") if sentinel is not None else None      # the daily trend of the CI sentinel, for its brief
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
    doc = signals.state(data, panels, "lite" if LITE["on"] else "complete", {"age_seconds": age, "stale": stale, "warnings": warnings, "working_mode": MODE.name, "auto_mode": bool(MODE.auto),
                                                                           "central": central}, version=TOOL_VERSION, trend=trend, sentinels=sentinel_reports())
    try:
        from github_actions_monitor.integrations import lessons
        doc["lessons"] = lessons.apply_now(config, limit=5) if lessons.settings(config)["enabled"] else []      # what the failures of this CI have already taught, for the AI that reads the state
    except Exception as error:   # noqa: BLE001 - the lessons never stop the state
        degraded.note("lessons.apply", error)
    return doc


def briefs_get(path, query, client=""):
    """(document, status) for GET /api/ai/index and GET /api/ai/briefs?tab=X[&lang=xx]: the catalogue of briefs and the brief of one tab, cleaned by the redactor. The record of who read what is kept only when
    `ai_alerts.briefs.access_log` is on (off by default)."""
    from urllib.parse import parse_qs
    from github_actions_monitor.data_pipeline import briefs
    from github_actions_monitor.security import redactor
    args = {k: v[0] for k, v in parse_qs(query).items() if v}
    lang = args.get("lang") if args.get("lang") in i18n.LANGS else "en"
    state = ai_state(lang)
    if path == "/api/ai/index":
        return redactor.redact_data(briefs.index(state, lang, i18n.tl)), 200
    if not args.get("tab") or args.get("tab") == "all":      # no tab: every brief in one document (the whole of what the page shows, for a tool that wants it all)
        every = [briefs.brief(tab, state, lang, i18n.tl) for tab in briefs.tabs()]
        return redactor.redact_data({"schema": briefs.SCHEMA, "kind": "ai-briefs", "edition": state.get("edition", "complete"), "version": state.get("version", ""), "generated_epoch": state.get("generated_epoch", 0),
                                     "count": len(every), "briefs": every}), 200
    document = briefs.brief(args.get("tab", ""), state, lang, i18n.tl)
    if document is None:
        return {"ok": False, "error": "tab", "tabs": list(briefs.tabs())}, 404
    try:
        config = toolconfig.raw_config()
        if ((config.get("ai_alerts") or {}).get("briefs") or {}).get("access_log") is True:
            briefs.note_access(state_dir(), args["tab"], client)
    except Exception as error:   # noqa: BLE001 - the record never stops the brief
        degraded.note("briefs.access", error)
    return redactor.redact_data(document), 200


def report_get(path, query):
    """('json' | 'text' | 'pdf', document, status) for GET /api/report/tab and /api/report/tab.pdf: the report of one tab of the page (reporting/tab_report.py), built ONCE and drawn as data, plain text or PDF so the
    formats never differ. `?tab=` (default now), `?lang=`, `?fmt=json|txt|options` (the PDF takes `?paper=a4|letter`). The structure is cleaned by the same redactor as the briefs."""
    from urllib.parse import parse_qs
    from github_actions_monitor.reporting import pdf_writer, tab_report
    from github_actions_monitor.security import redactor
    args = {k: v[0] for k, v in parse_qs(query).items() if v}
    lang = args.get("lang") if args.get("lang") in i18n.LANGS else i18n.language()
    tab = args.get("tab") or "now"
    config = toolconfig.raw_config()
    options = tab_report.settings(config)
    if args.get("fmt") == "options":
        return "json", {"options": options, "pdf_route": tab_report.pdf_route(lang, options["pdf_path"]), "browser_only": lang in tab_report.BROWSER_ONLY, "lang": lang, "tab": tab}, 200
    library = None
    if tab == "les":
        try:
            from github_actions_monitor.integrations import lessons
            library = sorted(lessons.load_library().values(), key=lambda x: x["category"]) if lessons.settings(config)["enabled"] else []
        except Exception as error:   # noqa: BLE001 - the lessons never stop a report
            degraded.note("report.lessons", error)
    document = tab_report.build(tab, ai_state(lang), lang, i18n.tl, data=STATE.get("data") or {}, library=library, limits=options["limits"])
    if document is None:
        return "json", {"ok": False, "error": "tab", "tabs": list(__import__("github_actions_monitor.data_pipeline.briefs", fromlist=["_"]).tabs())}, 404
    document = redactor.redact_data(document)
    if path.endswith(".pdf"):
        paper = args.get("paper") if args.get("paper") in tab_report.PAPER else options["paper"]
        if not pdf_writer.encodable(document):
            return "json", {"ok": False, "error": "pdf_script", "route": "browser"}, 422      # a text the standard fonts cannot set: the page uses the print of the browser, never a PDF with broken characters
        return "pdf", pdf_writer.render_pdf(document, paper), 200
    if args.get("fmt") == "txt":
        return "text", tab_report.render_text(document), 200
    return "json", document, 200


def skills_get(query):
    """('md' | 'json', document) for GET /api/skills: the list of skills, one file of a skill, or the whole skill in one text (`all=1`, what the page downloads)."""
    from urllib.parse import parse_qs
    from github_actions_monitor.integrations import skills
    args = {k: v[0] for k, v in parse_qs(query).items() if v}
    name = args.get("name", "")
    if not name:
        return "json", {"skills": [{"name": n, "files": skills.files(n), "version": TOOL_VERSION} for n in skills.names()], "monitor_version": TOOL_VERSION}
    if args.get("all") == "1":
        parts = [skills.read(name, f) for f in skills.files(name)]
        text = "\n\n---\n\n".join(p for p in parts if p)
        return ("md", text) if text else ("json", {"ok": False, "error": "name"})
    text = skills.read(name, args.get("file") or "SKILL.md")
    return ("md", text) if text is not None else ("json", {"ok": False, "error": "file"})


def lessons_get(path, query):
    """('md' | 'json', document) for GET /api/ai/lessons and /api/ai/failures. `?fmt=md` is the file ai/LESSONS.md, `?fmt=brief&repo=X` the brief before a push."""
    from urllib.parse import parse_qs
    from github_actions_monitor.integrations import lessons
    config = toolconfig.raw_config()
    args = {k: v[0] for k, v in parse_qs(query).items() if v}
    repo = args.get("repo", "") if re.fullmatch(r"[A-Za-z0-9._-]{1,100}", args.get("repo", "")) else ""
    if path == "/api/ai/failures":
        number = lambda key, default: whole(args.get(key), default)   # noqa: E731
        category = args.get("category", "") if re.fullmatch(r"[a-z][a-z0-9_]{0,39}", args.get("category", "")) else ""
        return "json", {"schema": lessons.SCHEMA, "enabled": lessons.settings(config)["enabled"], "failures": lessons.failures(config, number("since", 0), repo, category, number("limit", 100))}
    if args.get("fmt") in ("md", "brief"):
        text = lessons.render_markdown(config) if args["fmt"] == "md" else lessons.pre_push_brief(config, repo)
        return ("json", {"fmt": args["fmt"], "text": text}) if args.get("as") == "json" else ("md", text)
    return "json", lessons.document(config, repo)


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
        try:
            from github_actions_monitor.integrations import lessons
            sections = (sections or "") + lessons.brief_section(config)      # the lessons that apply now travel in the brief an AI reads
        except Exception as error:   # noqa: BLE001 - the lessons never stop the feed
            degraded.note("lessons.apply", error)
        result = ai_alerts.update(config, red_rows(data), runner=ai_alerts.gh_runner if diagnose else None, owner=toolconfig.github_owner(config), panels=panels, sections=sections, extra_rows=extra,
                                  status=f"running, cycle complete ({len(data.get('repos') or [])} repositories read)")
    try:      # --demo writes nothing: no book and no ai/LESSONS.md in the folder it runs from
        from github_actions_monitor.integrations import lessons
        if DEMO["on"]:
            pass
        elif result["opened"]:
            lessons.record(config, result["opened"], {(r.get("repo"), r.get("workflow")): r.get("sha") for r in red_rows(data) if r.get("sha")})      # a failure that opens goes into the book (local file)
        if not DEMO["on"]:
            lessons.write_markdown(config, force=bool(result["opened"] or result["resolved"]))
    except Exception as error:   # noqa: BLE001 - the book never stops the feed
        degraded.note("lessons.record", error)
    if not result["opened"] and any(a.get("class") == "real" for a in result["resolved"] if isinstance(a, dict)):
        try:
            from github_actions_monitor.integrations import soundalert
            soundalert.beep(config, "resolved")      # a red turned green (the sound of this computer, only with sound.server_beep)
        except Exception as error:   # noqa: BLE001
            degraded.note("loop.extra2", error)
    for alert in result["opened"]:
        if alert["class"] == "real":
            try:
                from github_actions_monitor.integrations import soundalert
                soundalert.beep(config, "new_red")      # only with sound.server_beep (off by default), for when the page is not open
            except Exception as error:   # noqa: BLE001
                degraded.note("loop.extra2", error)
            try:
                from github_actions_monitor.integrations import notifiers
                if alert.get("conclusion") == "panel":      # a red workflow already has its own event (red_new); this one is for the alerts that come from a panel or a signal of the monitor
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
                      ("runner_model", lambda: spare and read_runner_jobs(config, data)),
                      ("runners", lambda: spare and read_runner_list(config, data)),
                      ("runner_workflows", lambda: spare and read_runner_workflows(config, data)),
                      ("orgs", lambda: spare and read_extra_lists(config)),
                      ("pool", lambda: spare and refresh_pool_status()),
                      ("reports", lambda: spare and __import__("github_actions_monitor.integrations.reports", fromlist=["_"]).cycle(config, toolconfig.github_owner(config), list(data.get("repos") or []), source_runs(config, data),
                                                                                                                                  lambda endpoint: gh_read(endpoint, retries=0))),
                      ("mirror", lambda: spare and __import__("github_actions_monitor.integrations.mirror", fromlist=["_"]).cycle(config, source_runs(config, data), toolconfig.github_owner(config), lambda e: gh_read(e, retries=0), download_artifact)),
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
REPORT_WATCH, LESSON_WATCH = (__import__("github_actions_monitor.integrations.soundalert", fromlist=["_"]).KeyWatch(kind) for kind in ("report", "lesson"))
SOUND_WATCH = __import__("github_actions_monitor.integrations.soundalert", fromlist=["_"]).Watch()      # what is new in the list of alerts between two cycles, for the sound of this computer


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


def backup_job(config):
    """The scheduled copy, in a thread of its own so that a big installation never delays a refresh cycle. A failure is counted and never raised."""
    try:
        from github_actions_monitor.ops import schedule
        schedule.tick(config)
    except Exception as error:   # noqa: BLE001 - a copy that cannot be made is in its state file; the monitor goes on
        degraded.note("ops_backup", error)


def backup_tick(config):
    """The tick of the scheduled copy (`ops.backup.enabled`, off by default): when a copy is due it starts in a thread. The lite edition has no such job. Cheap while the switch is off."""
    if LITE["on"]:
        return
    try:
        from github_actions_monitor.ops import schedule
        if schedule.due(config):
            threading.Thread(target=backup_job, args=(config,), name="ops-backup", daemon=True).start()
    except Exception as error:   # noqa: BLE001
        degraded.note("ops_backup", error)


def score_security(registry, config):
    """{"penalty", "repos"} from the Security sentinel for the security part of the score, or None while the sentinel is off or has looked at fewer repositories than the score asks for (min_coverage)."""
    sentinel = registry.get("security") if registry else None
    if sentinel is None or not getattr(sentinel, "enabled", False):
        return None
    from github_actions_monitor.scoring import engine as score_engine
    status = sentinel.get_status()
    scope, checked = status.get("repos_in_scope") or 0, status.get("repos_checked") or 0
    minimum = score_engine.settings(config)["min_coverage"]
    if not scope or not checked or checked / scope < minimum:
        return None
    readable, total = status.get("sources_readable") or 0, status.get("sources_total") or 0
    if (total and readable / total < minimum) or (status.get("sources_na_plan") and not total):      # "could not be read" (or "not in the plan") is not "clean": the part is absent, not a 100
        return None
    return {"penalty": sentinel.get_metrics().get("security_penalty", 0), "repos": checked}


def score_missing_detail(registry, config, answer):
    """Why each part of the score that has no data has none: [{"part", "reason", "checked", "scope"}]. reason: `sentinel_off` (it is not running), `first_sweep` (it has not read a repository yet),
    `partial` (it has read fewer than `score.min_coverage` of its repositories), `unreadable` (the sources could not be read), `next_pass` (the data is there and the next pass of the score takes it)."""
    from github_actions_monitor.scoring import engine as score_engine
    sentinels = {"security": "security", "collaboration": "collab"}
    wanted = list(answer.get("missing_parts") or [])
    wanted += [p["part"] for p in answer.get("parts") or [] if p.get("part") in sentinels and not p.get("available") and p["part"] not in wanted]
    minimum = score_engine.settings(config)["min_coverage"]
    out = []
    for part in wanted:
        sentinel = registry.get(sentinels.get(part, part)) if registry else None
        row = {"part": part, "reason": "sentinel_off", "checked": 0, "scope": 0}
        if sentinel is not None and getattr(sentinel, "enabled", False):
            status = sentinel.get_status()
            scope, checked = status.get("repos_in_scope") or 0, status.get("repos_checked") or 0
            readable, total = status.get("sources_readable") or 0, status.get("sources_total") or 0
            row.update(checked=checked, scope=scope)
            if not scope or not checked:
                row["reason"] = "first_sweep"
            elif checked / scope < minimum:
                row["reason"] = "partial"
            elif (total and readable / total < minimum) or (status.get("sources_na_plan") and not total):
                row["reason"] = "unreadable"
            else:
                row["reason"] = "next_pass"
        out.append(row)
    return out


def compare_keep_days(config):
    """How many days the ledger of the score must keep for the comparison: two of its windows and a day, or 0 while it is off (then the ledger keeps what the score needs)."""
    from github_actions_monitor.compare import config as compare_config
    cfg = compare_config.settings(config)
    return 2 * max(cfg["default_window_days"], 7) + 1 if cfg["enabled"] else 0


def source_runs(config, data):
    """The runs the score, the reports, the mirror and the analytics read: with `score.source` "ledger" every run the last cycle read (the page keeps only the newest 600), otherwise the list of the page.
    The full list is used only while it belongs to the picture in hand (same total), so a picture resumed from disk never mixes with the runs of another cycle."""
    listed = data.get("runs") or []
    from github_actions_monitor.scoring import engine as score_engine
    if score_engine.settings(config if isinstance(config.get("score"), dict) else toolconfig.raw_config())["source"] != "ledger":
        return listed
    full = ALL_RUNS["runs"]
    return full if full and data.get("runs_total") == len(full) and len(full) >= len(listed) else listed


def score_tick(config, data):
    """The pass of the score (once every few minutes at most): the runs and the alerts of the collaboration sentinel go to the ledger and the snapshot of the hour is written. Complete only; a
    failure is counted and never stops the cycle."""
    if LITE["on"] or data.get("loading") or (data.get("offline") or {}).get("offline"):
        return
    try:
        from github_actions_monitor.scoring import ledger as score_service
        from github_actions_monitor.storage import runtime
        registry = SENTINEL["registry"]
        collab = registry.get("collab") if registry else None
        known = bool(collab is not None and getattr(collab, "enabled", False) and not (collab.get_status() or {}).get("loading"))
        storage, account = runtime.process_storage(CHILD["account"] or None)
        idle = set(data.get("forks_idle_all") or data.get("forks_idle") or [])      # the runs of a fork without a CI of its own (the cron it inherited) are not the work of the account
        snapshot = score_service.tick(storage, account, config, [r for r in source_runs(config, data) if r.get("repo") not in idle], collab.get_alerts() if known else [], collab_known=known, security=score_security(registry, config), activity=data.get("activity"), keep_days_min=compare_keep_days(config), seen=data.get("runs_total"))
        if snapshot and snapshot.get("drop_new") and snapshot.get("drop"):      # the moment a drop appears; it leaves the panel only when the person asked for it
            from github_actions_monitor.scoring import drop as score_drop, engine as score_engine
            sentinel = SENTINEL["obj"]
            if score_engine.settings(config)["alert"]["notify_external"] and sentinel is not None:
                sentinel.feed.emit([score_drop.event(snapshot["drop"])])
    except Exception as error:   # noqa: BLE001 - the score never stops the monitor
        degraded.note("score", error)


def audit_action(handler, action, target="", details=None, result="ok", force=False):
    """One line in the log of actions (security/audit_log.py): who did what on this account. Never raises; a value of a setting never goes in, only the names."""
    try:
        from github_actions_monitor.security import audit_log
        context = getattr(handler, "auth_user", None) or {}
        audit_log.record(toolconfig.raw_config(), action, context.get("user") or auth_http.acting_user(handler), context.get("role", ""), CHILD["account"] or "", target, result, details, force=force)
    except Exception as error:   # noqa: BLE001 - the log of actions never stops a request
        degraded.note("audit_log", error)
def report_gather():
    """What a report is made of, read from what the monitor holds (never GitHub): the latest score snapshot, every open alert and the team ranking."""
    from github_actions_monitor.health import repo_view
    from github_actions_monitor.scoring import api as score_api
    from github_actions_monitor.sentinels import alert_center
    from github_actions_monitor.storage import runtime
    config = toolconfig.raw_config()
    storage, account = runtime.process_storage(CHILD["account"] or None)
    snapshot = score_api.latest(storage, account, config)
    try:
        alerts = alert_center.collect(SENTINEL["registry"], extra=credential_alerts() + score_alerts() + runner_alerts() + mark_alerts())
    except Exception as error:   # noqa: BLE001 - the report still has the rest
        degraded.note("reports.alerts", error)
        alerts = []
    gathered = (snapshot, alerts, repo_view.team_view(health_views()))
    try:
        from github_actions_monitor.compare import config as compare_config, compare_service
        if compare_config.settings(config)["include_in_report"]:      # the comparison with the period before, only when the person asked for it
            gathered += (compare_service.build(storage, account, config),)
    except Exception as error:   # noqa: BLE001 - the report still has the rest
        degraded.note("reports.compare", error)
    return gathered


def report_summary_post(config, request):
    """POST /api/report-files/summary: `action` = `draft` (the template), `draft_ai` (the template and the draft of the AI, only with ai.report_summary.enabled), `save` (the text as the person
    edited it and where it came from) or `clear`. Nothing is written into a report here: the approved text goes into the next one."""
    from github_actions_monitor.reporting import report_service, report_summary
    from github_actions_monitor.sentinels import sentinel_ai
    action, account = request.get("action"), report_account()
    if action == "save":
        saved = report_service.save_summary(account, request.get("text"), request.get("origin"))
        return {"ok": saved is not None, "status": "saved" if saved else "empty", "summary": saved}
    if action == "clear":
        report_service.clear_summary(account)
        return {"ok": True, "status": "cleared", "summary": None}
    if action not in ("draft", "draft_ai"):
        return {"ok": False, "status": "action"}
    snapshot, alerts, team = report_gather()[:3]
    doc = report_service.document(config, account, snapshot, alerts, team)
    cfg, store = sentinel_ai.ai_config(config), ai_store()
    drafts = report_summary.drafts(config, doc, i18n.language(), lambda text: sentinel_ai.explain("report", text, cfg, store), with_ai=action == "draft_ai")
    return {"ok": True, "status": "draft", **drafts, "summary": report_service.pending_summary(account)}


def report_account():
    return CHILD["account"] or toolconfig.github_owner() or "main"


def report_tick(config):
    """The scheduled report, once a cycle: cheap while it is off or not due. Complete only; a failure is noted and never stops the cycle."""
    if LITE["on"] or DEMO["on"]:
        return
    try:
        from github_actions_monitor.reporting import report_service
        if report_service.settings(config)["enabled"]:
            report_service.tick(config, report_account(), report_gather)
    except Exception as error:   # noqa: BLE001
        degraded.note("reports", error)


def health_views(now=None, only=None):
    """The health of every repository the monitor watches, from what it already holds (runs, red and stuck, the alerts of every sentinel, the readiness of the releases). Never calls GitHub.
    The runs, the red workflows, the active runs and the alerts are grouped by repository ONCE, so the cost grows with the data and not with repositories x runs; `only` = one repository name."""
    from github_actions_monitor.health import repo_view
    from github_actions_monitor.sentinels import alert_center
    now = time.time() if now is None else now
    with LOCK:
        data = dict(STATE.get("data") or {})
    runs = (data.get("runs") or [])
    failing, active = data.get("failing") or [], data.get("active") or []
    registry = SENTINEL["registry"]
    try:
        alerts = alert_center.collect(registry, extra=credential_alerts() + score_alerts() + runner_alerts() + mark_alerts())
    except Exception as error:   # noqa: BLE001 - the health still answers without the alerts
        degraded.note("health.alerts", error)
        alerts = []
    sources = {}
    try:
        for name, status in (registry.status() if registry else {}).items():
            sources[name] = (status or {}).get("lifecycle") or ("healthy" if (status or {}).get("enabled", True) else "off")
    except Exception as error:   # noqa: BLE001
        degraded.note("health.sources", error)
    ready = {}
    try:
        sentinel = SENTINEL["obj"]
        snapshot = sentinel.snapshot() if sentinel else None
        for row in (((snapshot or {}).get("a11") or {}).get("sections") or [{}])[0].get("rows") or []:
            if isinstance(row, list) and len(row) >= 7:
                ready[str(row[0])] = {"entries": row[1], "ci": row[2], "version": row[3], "build": row[4], "signing": row[5], "next": row[6]}
    except Exception as error:   # noqa: BLE001
        degraded.note("health.readiness", error)
    names = sorted({r.get("repo") for r in runs if isinstance(r, dict) and r.get("repo")} | {r for r in (data.get("repos") or []) if isinstance(r, str)} | {a.get("repo") for a in alerts if a.get("repo")})
    if only is not None:
        names = [n for n in names if n == only]
    runs_by, failing_by, active_by, alerts_by = (repo_view.group_by_repo(x) for x in (runs, failing, active, alerts))
    from github_actions_monitor.health import fleet as fleet_view_module
    all_active = fleet_view_module.settings(toolconfig.raw_config())["show_all_active"]      # fleet.show_all_active: every run that is going, or only the newest of each workflow
    summary_by = RUN_SUMMARY["by_repo"] if (data.get("runs_total") or 0) > len(runs) else {}      # the cut was made: count over everything the cycle read
    views = []
    for repo in names:
        eco = toolconfig.ecosystem_of(repo)
        view = repo_view.repo_view(repo, runs_by.get(repo, []), failing_by.get(repo, []), active_by.get(repo, []), alerts_by.get(repo, []), ready.get(repo), sources, eco, now, summary_by.get(repo) if summary_by else None, all_active)
        view["ecosystem_label"] = toolconfig.label_of(eco)
        views.append(view)
    return views


def score_alerts():
    """The alert of a score that has dropped, for the Alerts tab: from the latest snapshot, only while it is fresh (an old one says nothing). Complete only; never raises."""
    if LITE["on"]:
        return []
    try:
        from github_actions_monitor.scoring import api as score_api, drop as score_drop, engine as score_engine
        from github_actions_monitor.storage import runtime
        config = toolconfig.raw_config()
        if not score_engine.settings(config)["alert"]["enabled"] or not score_engine.settings(config)["enabled"]:
            return []
        storage, account = runtime.process_storage(CHILD["account"] or None)
        latest = score_api.latest(storage, account, config)
        if latest.get("stale") or not latest.get("drop"):
            return []
        return [score_drop.alert(latest, latest["drop"], CHILD["account"] or "")]
    except Exception as error:   # noqa: BLE001 - the list of alerts must still answer
        degraded.note("score.alert", error)
        return []


def digest_tick(config):
    """The digests of the users (notify.users.enabled, OFF by default) whose time has come, from a thread of their own so that a slow relay never holds the cycle. Never raises."""
    try:
        from github_actions_monitor.integrations import dispatcher
        if dispatcher.settings(config)["enabled"]:
            threading.Thread(target=dispatcher.run_digests, args=(config,), kwargs={"title": i18n.t("notify.digest_title", n="{n}")}, name="notify-digest", daemon=True).start()
    except Exception as error:   # noqa: BLE001
        degraded.note("notify", error)


def maintain(config, data):
    """After each cycle: the conditional-read cache is saved, a few completed runs have their jobs sampled and the analytics are refreshed."""
    quota_watch(config)
    digest_tick(config)
    clone_tick(config)
    try:      # the connection that goes down is announced once, by the same switch as a new red
        from github_actions_monitor.integrations import soundalert
        lost = bool((data.get("offline") or {}).get("offline"))
        kinds = []
        if lost and not CONNECTION_WAS["lost"]:
            kinds.append("connection_lost")
        if not lost and CONNECTION_WAS["lost"]:
            kinds.append("live_recovered")      # the live connection is back after a loss: its own sound, by its own switch
        CONNECTION_WAS["lost"] = lost
        sound_config = toolconfig.raw_config()
        sound_cfg = soundalert.settings(sound_config)
        if sound_cfg["enabled"] and sound_cfg["server_beep"] and not LITE["on"]:      # the other kinds of the page, seen from the list of alerts (only when the beep of this computer is on)
            try:
                kinds += SOUND_WATCH.look(alerts_payload({}).get("alerts"))
            except Exception as error:   # noqa: BLE001
                degraded.note("sound.watch", error)
            try:      # the reports and the lessons that show something new (the same keys as the page)
                from github_actions_monitor.integrations import lessons, reports
                kinds += REPORT_WATCH.look(soundalert.report_keys(reports.payload(sound_config, None)))
                kinds += LESSON_WATCH.look(soundalert.lesson_keys(lessons.document(sound_config, "") if lessons.settings(sound_config)["enabled"] else None))
            except Exception as error:   # noqa: BLE001
                degraded.note("sound.watch", error)
        if kinds:
            soundalert.beep_kinds(sound_config, kinds)
    except Exception as error:   # noqa: BLE001 - a sound never stops a cycle
        degraded.note("loop.extra2", error)
    maintain_extras(toolconfig.raw_config() if not LITE["on"] else config, data)
    retention_tick(toolconfig.raw_config() if not LITE["on"] else config)
    backup_tick(toolconfig.raw_config() if not LITE["on"] else config)
    score_tick(toolconfig.raw_config() if not LITE["on"] else config, data)
    report_tick(toolconfig.raw_config() if not LITE["on"] else config)
    try:
        if ETAG["cache"]:
            ETAG["cache"].save()
        cfg = analytics.settings(config)
        store = ANALYTICS["store"]
        if store is None or not cfg["enabled"] or data.get("loading") or data["offline"]["offline"]:
            return
        for run in analytics.pending_runs(source_runs(config, data), store, cfg["jobs_per_cycle"]):
            try:
                body = gh_read(f"repos/{toolconfig.github_owner()}/{run['repo']}/actions/runs/{run['id']}/jobs?per_page=100", retries=0)
            except Exception:   # noqa: BLE001 - a job list that cannot be read is skipped for good
                store.add_jobs(run["repo"], run["name"], run["id"], [], cfg["steps"])
                continue
            store.add_jobs(run["repo"], run["name"], run["id"], (body or {}).get("jobs") or [], cfg["steps"])
        ranked = source_runs(config, data)
        if workflow_scope.settings(config)["reusable_out"]:      # ci.reusable_out_of_rankings: the runs of a workflow that only others call stay out of the rankings
            ranked = workflow_scope.drop_flat(ranked, local_reusable_files())
        ANALYTICS["summary"] = analytics.summary(ranked, store, cfg)
        ANALYTICS["summary"]["time_saved"] = timesaved.estimate(source_runs(config, data), timesaved.settings(config))
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


def degraded_line(text):
    """One line of a failure that was swallowed on purpose, in the log of the monitor, with the time. A log that cannot be written is not one more failure."""
    try:
        with private_io.open_append(LOG_FILE) as log:
            log.write(tzdisplay.localize(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {text}\n"))
    except Exception:   # noqa: BLE001
        pass


def write_cycle_log(data):
    """One line of counts per cycle (never titles). A failure is not swallowed: the heartbeat keeps it and the page and the doctor show it."""
    try:
        row = ETAG["cache"].end_cycle() if ETAG["cache"] else None      # I-155: how the conditional reads did in THIS cycle (a few figures, never a title)
        etag_part = f" etag={row['saved']}/{row['calls']} no_etag={row['no_etag']}" if row and row["calls"] else ""
        with private_io.open_append(LOG_FILE) as log:
            log.write(tzdisplay.localize(f"{data['updated']} repos={len(data['repos'])} hot={data['hot']} refreshed={data['refreshed']} active={len(data['active'])} issues={len(data['issues'])} rate={data['rate']}{etag_part}\n"))
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
    cycle_t0 = time.time()
    phase_marks = {}
    try:      # the log says that a cycle began, so a long one is not mistaken for a monitor that stopped
        with private_io.open_append(LOG_FILE) as log:
            log.write(tzdisplay.localize(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} cycle=started\n"))
    except Exception as error:   # noqa: BLE001
        WATCH.log_failed(error)
    brief_status(toolconfig.raw_config() if not LITE["on"] else config, "running, a cycle has started, the alerts below are from the last complete cycle")
    data = collect(config, publish)
    phase_marks["collect"] = time.time() - cycle_t0
    if WATCH.current(generation):      # the finished picture goes to the page NOW: the box "loading repositories" must not wait for the upkeep that follows (it may be slow)
        with LOCK:
            STATE["data"], STATE["error"], STATE["hint"] = data, None, None
    WATCH.phase("maintain")
    transition = LINK.end_cycle()
    if transition:
        announce_link(transition, config)
    data["offline"] = LINK.state()
    data["etag"] = ETAG["cache"].stats() if ETAG["cache"] else None
    data["github_status"] = githubstatus.STATUS.snapshot(config)      # the state of GitHub for the bar (nothing is read here: the loop of the outside reads keeps it)
    maintain_t0 = time.time()
    maintain(config, data)
    phase_marks["maintain"] = time.time() - maintain_t0
    if not WATCH.current(generation):
        return None
    WATCH.phase("publish")
    with LOCK:
        STATE["data"], STATE["error"], STATE["hint"] = data, None, None
        STATE["complete"] = True
    if not LITE["on"]:
        try:      # the picture is kept for the next start; a disk that refuses it never stops the cycle
            lastpicture.save(state_dir(), data, config)
        except Exception as error:   # noqa: BLE001
            degraded.note("loop.last_picture", error)
    WATCH.phase("log")
    write_cycle_log(data)
    WATCH.phase("extras")
    delay = viewers.stretch(config, tuned(config, "refresh_seconds", data), tuned(config, "cold_refresh_seconds"))      # nobody looking for modes.idle_minutes and nothing that must not wait: the cold pace
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
    tickstats.note_cycle(time.time() - cycle_t0, True, phase_marks, reads=REFRESH_COUNT[0])      # /metrics: the duration of the cycle and of its phases
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
            tickstats.note_cycle(max(0.0, time.time() - WATCH.cycle_started), False)
            outcome = credential_refusal(error, config)
            with LOCK:
                STATE["error"], STATE["hint"] = str(error), "auth"   # the page writes the hint in its own language
            brief_status(toolconfig.raw_config() if not LITE["on"] else config, "running, but the last cycle failed to sign in to GitHub; the alerts below are from the last complete cycle")
            delay = CONFIRM_DELAY if outcome == "strike" else 60      # the first refusal is confirmed soon: one stray 401 must not hide a lost login for a whole minute
        except Exception as error:
            if not WATCH.current(generation):
                return
            WATCH.fail(error)
            tickstats.note_cycle(max(0.0, time.time() - WATCH.cycle_started), False)
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


def abandoned_limit(config):
    """How many calls that never returned may stay alive before new calls to GitHub are refused (`watchdog_max_abandoned`)."""
    try:
        return max(0, int((LIVE_CONFIG or config or DEFAULTS).get("watchdog_max_abandoned", cycle_watch.DEFAULT_MAX_ABANDONED)))
    except (TypeError, ValueError):
        return cycle_watch.DEFAULT_MAX_ABANDONED


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


HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,100}\Z")


class QuietServer(exclusive.ExclusiveBind, ThreadingHTTPServer):
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
            "ecosystems": {**{"other": i18n.t("ui.eco_other")}, **{key: item["label"] for key, item in toolconfig.ecosystems().items()}}, "owner": toolconfig.github_owner(), "tz": tzdisplay.setting(), "screens": {k: v for k, v in (toolconfig.raw_config().get("ui") or {}).items() if k in DEFAULTS["ui"] and k != "theme"}, "kiosk": ({} if LITE["on"] else __import__("github_actions_monitor.surfaces.kiosk", fromlist=["_"]).public(toolconfig.raw_config())), "theme": screens.global_theme(toolconfig.raw_config()), "screen_menu": {k: v for k, v in screenmenu.menu_settings(toolconfig.raw_config()).items() if k in ("menu", "menu_target", "menu_max_windows")}, "blink": (toolconfig.raw_config().get("display") or {}).get("blink_red_tiles", True) is not False, "sound": {k: v for k, v in __import__("github_actions_monitor.integrations.soundalert", fromlist=["_"]).settings(toolconfig.raw_config()).items() if k != "server_beep"}, "host": github_host(), "lite": LITE["on"], "network": localguard.public_state(), "version": TOOL_VERSION, "author": AUTHOR, "license": LICENSE_ID}
    data["viewer_aware"] = bool(viewers.settings(toolconfig.raw_config())["idle_minutes"])      # modes.idle_minutes: a hidden tab stops asking
    from github_actions_monitor.surfaces import pwa
    from github_actions_monitor.security import devices
    pwa_cfg = pwa.settings(toolconfig.raw_config())
    data["pwa"] = pwa_cfg
    shown = toolconfig.raw_config().get("display") if isinstance(toolconfig.raw_config().get("display"), dict) else {}
    data["display"] = {"live_throttle_s": shown.get("live_throttle_s") if isinstance(shown.get("live_throttle_s"), int) and 0 <= shown.get("live_throttle_s") <= 300 else 30, "whats_new": shown.get("whats_new") is not False,
                       "density": "dense" if shown.get("density") == "dense" else "normal", "reduce_motion": "on" if shown.get("reduce_motion") == "on" else "auto", "palette": "colorblind" if shown.get("palette") == "colorblind" else "default"}
    data["pairing"] = {"enabled": devices.settings(toolconfig.raw_config())["enabled"] and bool(localguard.STATE["network"]) and not LITE["on"]}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("</head>", pwa.head(pwa_cfg) + "</head>", 1) if pwa_cfg["enabled"] else page
    extras_file = paths.STATIC / "ui_extras.js"
    extras = extras_file.read_text(encoding="utf-8") if extras_file.is_file() else ""
    if pwa_cfg["enabled"]:
        extras += "\n" + pwa.REGISTER_JS
    page = page.replace("/*EXTRAS_JS*/", extras, 1)
    return page.replace("/*I18N_DATA*/null", blob, 1)


def render_screen(kind, query):
    """The page of one wall screen (screens.html): the texts of the language, the settings that matter to it and the parameters of the window, embedded. No menu, nothing that changes anything."""
    config = toolconfig.raw_config()
    cfg = screens.settings(config)
    chosen = screens.global_theme(config)
    page = (paths.STATIC / "screens.html").read_text(encoding="utf-8").replace("/*THEME_CSS*/", screens.theme_css(), 1)
    data = screens.page_data(kind, cfg, screens.params(query, cfg, kind, chosen), logo=orglogo.info(), global_name=chosen)
    data["viewer_aware"] = bool(viewers.settings(config)["idle_minutes"])      # modes.idle_minutes: a hidden window stops asking
    from github_actions_monitor.integrations import soundalert
    data["sound"] = {key: value for key, value in soundalert.settings(toolconfig.raw_config()).items() if key != "server_beep"}
    from github_actions_monitor.integrations import soundlib
    data["sound"]["voices"] = soundlib.merged(data["sound"].get("voices"), cfg.get("sound_voices"))      # the wall may give a kind of event its own sound
    if cfg.get("sound_volume"):
        data["sound"]["volume"] = cfg["sound_volume"]      # and its own volume (0 = the one of the sound settings)      # the same sounds as the page, per kind (the window still needs ?sound=on and screens.sound)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return page.replace("/*SCREEN_DATA*/null", blob, 1)


def screens_payload(kind, cfg, repo=""):
    """GET /api/screens/data: what the screens show, from what the monitor holds. Nothing is read from GitHub here: the last cycle, the snapshot of the sentinel, the alerts and the score are already in memory or in the local files."""
    with LOCK:
        state = STATE["data"]
    sentinel = None if LITE["on"] else SENTINEL["obj"]
    snapshot = alerts = score = None
    if sentinel is not None:
        try:
            snapshot = sentinel.snapshot()
        except Exception as error:   # noqa: BLE001 - a screen without the sentinel still shows the rest
            degraded.note("screens.sentinel", error)
    if not LITE["on"] and kind in ("overview", "sentinels"):
        try:
            alerts = alerts_payload({})
        except Exception as error:   # noqa: BLE001
            degraded.note("screens.alerts", error)
    if not LITE["on"] and kind == "overview":
        try:
            if DEMO["on"]:
                from github_actions_monitor.app import demo_mode
                score = demo_mode.score_answer()
            else:
                from github_actions_monitor.scoring import api as score_api
                from github_actions_monitor.storage import runtime
                storage, account = runtime.process_storage(CHILD["account"] or None)
                score = score_api.latest(storage, account, toolconfig.raw_config())
        except Exception as error:   # noqa: BLE001
            degraded.note("screens.score", error)
    view = labels = None
    if not LITE["on"] and ((kind == "overview" and cfg.get("group_map", True)) or kind == "fleet"):
        view, labels = screens_groups()
    return screens.build(kind, state, snapshot, alerts, score, cfg, "lite" if LITE["on"] else "complete", fleet_view=view, labels=labels, repo=repo)


GROUPS_CACHE = {"at": 0.0, "view": None, "labels": None}


def screens_groups():
    """The groups of the fleet view for the overview wall screen, the same ones as the Fleet tab (fleet.group_by). The view is built at most once every 30 seconds: a screen asks every few seconds."""
    now = time.time()
    if GROUPS_CACHE["view"] is None or now - GROUPS_CACHE["at"] > 30:
        try:
            from github_actions_monitor.health import fleet
            GROUPS_CACHE.update(at=now, view=fleet.fleet_view(health_views(), toolconfig.raw_config()), labels={**{"other": i18n.t("ui.eco_other")}, **{key: item["label"] for key, item in toolconfig.ecosystems().items()}})
        except Exception as error:   # noqa: BLE001 - a screen without the map still shows the rest
            degraded.note("screens.groups", error)
            return None, None
    return GROUPS_CACHE["view"], GROUPS_CACHE["labels"]


def chatops_snapshot(config):
    """What the commands of the chat read (chatops/commands.py), from what the monitor holds and never from GitHub: the counts of the fleet, the red workflows, the queue, the score and the open alerts, with
    the names of the repositories already hidden the way `chatops.show_repo_names` says (the alias of a private repository, nothing of its workflows)."""
    from github_actions_monitor.chatops import inbound
    cfg = inbound.settings(config)
    with LOCK:
        state = STATE["data"]
    if not isinstance(state, dict) or not state:
        return {"loaded": False}
    overview = screens_payload("overview", dict(screens.settings(config), show_repo_names=cfg["show_repo_names"], group_map=False))
    names = screens.Names(state.get("repos"), state.get("repo_meta"), cfg["show_repo_names"])
    payload = alerts_payload({"muted": "hide"})
    code_ok = re.compile(r"^[a-z0-9_.:-]{1,40}\Z")
    owner, host = toolconfig.github_owner(config), github_host()
    visible = {r for r in (state.get("repos") or []) if isinstance(r, str) and not names.hidden(r)}

    def link(alias):      # the address of the repository, only when its name is shown as it is and the owner is known
        return f"https://{host}/{owner}/{alias}" if cfg["links"] and owner and alias in visible else None
    rows = [{"level": a.get("level") if a.get("level") in ("critical", "error", "warning", "info") else "info", "code": a.get("code") if isinstance(a.get("code"), str) and code_ok.match(a["code"]) else "other",
             "repo": names.name(a["repo"]) if a.get("repo") else None, "link": link(a["repo"]) if a.get("repo") else None} for a in payload["alerts"] if isinstance(a, dict)]
    red = [dict(r, link=link(r.get("repo"))) for r in (overview.get("top_red") or []) if isinstance(r, dict)]
    return {"loaded": True, "version": TOOL_VERSION, "fleet": overview.get("fleet"), "queue": overview.get("queue"), "score": overview.get("score"), "red": red,
            "alerts": {"total": payload["summary"]["total"], "rows": rows}}


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


def noindex_on(config):
    """`listen.noindex` (on unless it is a real false): the X-Robots-Tag header of every answer and the file /robots.txt."""
    listen = config.get("listen") if isinstance(config, dict) else None
    return not (isinstance(listen, dict) and listen.get("noindex") is False)


STORE_DOWN = [0]      # how many requests found the storage not answering since the monitor started
STORE_RETRY_SECONDS = 5


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
        for name, value in localguard.SECURITY_HEADERS:
            self.send_header(name, value)
        if getattr(self, "deprecated_access", False):
            self.send_header("Deprecation", "true")      # the ?access= address is deprecated: POST /api/access keeps the token out of the address bar
        if noindex_on(LIVE_CONFIG or DEFAULTS):      # no search engine indexes a monitor, whatever it is behind (`listen.noindex`, on by default)
            self.send_header("X-Robots-Tag", "noindex, nofollow")
        if getattr(self, "v1", False):      # every answer under /api/v1/ says which version of the API it is, whichever handler wrote it
            self.send_header(api_v1.VERSION_HEADER, api_v1.API_VERSION)
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

    def reply_bytes(self, payload, kind):
        try:
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Disposition", "inline; filename=monitor-report.pdf")
            self.end_headers()
            self.wfile.write(payload)
        except CLIENT_GONE:
            DISCONNECTS[0] += 1

    def send_response(self, code, message=None):
        self.reply_status = code      # the status of the answer, for the log of actions (audit_post)
        super().send_response(code, message)

    def audit_post(self, path):
        """One line in the log of actions for a POST that does something (the table of security/audited_posts.py): who, which action, the target the handler noted, the status and the result. The body never goes in."""
        from github_actions_monitor.security import audit_log, audited_posts
        target, details = audit_log.take_note()
        action = audited_posts.action_for(path)
        if not action:
            return
        status = getattr(self, "reply_status", 0)
        ok = getattr(self, "reply_ok", None)
        result = "ok" if 200 <= status < 300 and ok is not False else ("denied" if status in (401, 403) else "error")
        audit_action(self, action, target or path, {"status": status, **(details or {})}, result)

    def json_reply(self, payload, code=200, headers=None):
        self.reply_ok = payload.get("ok") if isinstance(payload, dict) else None
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        try:
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass   # the browser or a reader closed the tab mid-answer: nothing to report

    def stream_guard(self):
        """A function for the loop of a stream: True when the stream must end because the session that opened it was revoked or has expired, or because the role no longer allows it. It looks every
        `auth.stream_revalidate_min` minutes (10), so no connection keeps permissions that are gone."""
        last = [time.time()]

        def stop():
            from github_actions_monitor.security import auth
            config = toolconfig.raw_config()
            every = auth.settings(config)["stream_revalidate_min"] * 60
            if time.time() - last[0] < every:
                return False
            last[0] = time.time()
            return not auth_http.revalidate(self, config, self.path.split("?")[0])
        return stop

    def live_stream(self):
        """GET /api/live-events/stream: `text/event-stream` with a `hello` frame, then one `live` frame per webhook event accepted from now on (or after `Last-Event-ID` / `?since=` while still held)
        and a keep-alive comment. Read only, off by default (`live.sse.enabled`); the network mode asks for the access token as for every other request; limited listeners, each for a limited time."""
        from github_actions_monitor.security import webhook
        from urllib.parse import parse_qs
        config = toolconfig.raw_config()
        if not webhook.sse_settings(config)["enabled"]:
            self.json_reply({"error": "stream off"}, 404)
            return
        if not webhook.sse_acquire(config):
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
            for frame in webhook.sse_frames(config, lambda: (LIVE_TOTAL[0], list(LIVE_EVENTS)), since=whole(resume, None), stop=self.stream_guard()):
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except (ConnectionError, OSError):
            DISCONNECTS[0] += 1
        except (ValueError, TypeError) as error:
            degraded.note("live.stream", error)
        finally:
            webhook.sse_release()

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
            for frame in ai_alerts.stream_frames(config, offset=whole(resume, None), stop=self.stream_guard(),
                                                 only_real=(ask.get("only") or [""])[0] == "real"):
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except (ConnectionError, OSError):
            DISCONNECTS[0] += 1      # the listener went away: nothing to report
        except (ValueError, TypeError) as error:      # a frame that cannot be written ends this listener, never the server
            degraded.note("ai.stream", error)
        finally:
            ai_alerts.stream_release()

    def updates_stream(self):
        """GET /api/updates/stream: `text/event-stream` with `hello`, one `progress` frame each time the progress of the update changes (the JSON of /api/updates/progress), keep-alive comments and `bye`
        when the update is over. Same guard as the other routes of the Updates menu; at most two listeners, each for a limited time. No setting: it only reports a file the updater writes."""
        from github_actions_monitor.ops import updates
        if not updates.stream_acquire():
            self.json_reply({"error": "too many listeners"}, 429)
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            for frame in updates.stream_frames(stop=self.stream_guard()):      # ends with the session that opened it (auth.stream_revalidate_min)
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except (ConnectionError, OSError):
            DISCONNECTS[0] += 1
        except (ValueError, TypeError) as error:
            degraded.note("updates.stream", error)
        finally:
            updates.stream_release()

    local_door = False      # True only on the second, loopback-only port (listen.local_port): the way in of the person at this computer when a reverse proxy is declared

    def request_ok(self):
        return localguard.local_request_ok(self.headers, self.server.server_address[1], door=self.local_door)

    def is_local(self):
        """True when this request really comes from a person at this computer (see localguard.is_this_computer)."""
        return not self.remote_through_supervisor() and localguard.is_this_computer(self.client_address, self.headers, door=self.local_door)

    def webhook_sender(self):
        """Who sent a webhook request, for the limits: the process of an account is spoken to by its supervisor, which says who really sent it (and proves it with its key); otherwise the address of the
        peer, or the last address a trusted proxy appended (localguard.client_key)."""
        if os.environ.get(auth_http.CHILD_ENV):
            key, proof, given = envguard.get(SUPERVISOR_KEY_ENV), self.headers.get(auth_http.SUPERVISOR_KEY_HEADER) or "", self.headers.get(auth_http.WEBHOOK_PEER_HEADER) or ""
            if key and proof and hmac.compare_digest(key.encode(), proof.encode()) and 0 < len(given) <= 80:
                return "via:" + given
        return localguard.client_key(self.client_address, self.headers)

    def guard(self):
        if self.request_ok():
            return True
        self.json_reply({"error": "forbidden"}, 403)
        return False

    def expected_red_post(self):
        """POST /api/expected-red {action: add, repo, workflow, reason, owner, days} or {action: remove, id}. Needs `expected_red.enabled`, the role of a maintainer and the one-use token of the page."""
        from github_actions_monitor.data_pipeline import expected_red
        from github_actions_monitor.security import audit_log
        cfg = expected_red.settings(toolconfig.raw_config())
        if not cfg["enabled"] or LITE["on"]:
            self.json_reply({"ok": False, "error": "off"}, 404)
            return
        if not self.guard() or not self.token_ok():
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            request = json.loads(self.rfile.read(size) if 0 < size <= 4096 else b"{}")
        except (ValueError, TypeError):
            request = {}
        request = request if isinstance(request, dict) else {}
        if request.get("action") == "remove":
            done = expected_red.remove(request.get("id"))
            audit_log.note(str(request.get("id") or "")[:20])
            self.json_reply({"ok": done, "error": "" if done else "unknown"}, 200 if done else 404)
            return
        if request.get("action") != "add":
            self.json_reply({"ok": False, "error": "action"}, 400)
            return
        entry, why = expected_red.add(request.get("repo"), request.get("workflow"), request.get("reason"), request.get("owner"), request.get("days"), cfg["max_days"])
        audit_log.note(f"{request.get('repo')}:{request.get('workflow')}"[:120])
        self.json_reply({"ok": entry is not None, "error": why, "entry": entry}, 200 if entry else 400)

    def pwa_get(self, path):
        """The files of the app (manifest, worker, icons, offline page), the pairing page and the list of devices. True when the path was one of them (and answered)."""
        from github_actions_monitor.surfaces import pwa
        from github_actions_monitor.security import devices
        raw = toolconfig.raw_config()
        if path == "/pair":
            self.pair_page(devices.settings(raw))
            return True
        if path in ("/api/devices", "/api/pair/status"):
            if not self.guard() or not self.this_computer():
                return True
            cfg = devices.settings(raw)
            self.json_reply({"enabled": cfg["enabled"], "network": bool(localguard.STATE["network"]), "open": devices.is_open(), "max_devices": cfg["max_devices"], "code_minutes": cfg["code_minutes"],
                             "devices": devices.list_devices() if cfg["enabled"] else []})
            return True
        cfg = pwa.settings(raw)
        if not cfg["enabled"]:
            self.send_response(404)
            self.end_headers()
            return True
        if not self.guard():
            return True
        if path == "/manifest.webmanifest":
            self.reply_bytes(json.dumps(pwa.manifest(i18n.language(), i18n.t("ui.pwa_name"), i18n.t("ui.pwa_short"))).encode("utf-8"), "application/manifest+json; charset=utf-8")
        elif path == "/sw.js":
            self.reply_bytes(pwa.service_worker(TOOL_VERSION).encode("utf-8"), "text/javascript; charset=utf-8")
        elif path in ("/pwa/icon-192.png", "/pwa/icon-512.png"):
            self.reply_bytes(pwa.icon(192 if "192" in path else 512), "image/png")
        else:
            self.reply(pwa.offline_page(i18n.t("ui.pwa_offline_title"), i18n.t("ui.pwa_offline_text"), i18n.t("ui.pwa_offline_retry"), i18n.language()), "text/html; charset=utf-8")
        return True

    def pair_page(self, cfg):
        """GET /pair?c=CODE: the page a phone opens from the QR code. It only shows a button; the code is spent by the POST that the button sends, so a program that opens the address to preview it
        (a chat, a scanner) cannot spend it."""
        if not cfg["enabled"] or not localguard.STATE["network"] or LITE["on"]:
            self.send_response(404)
            self.end_headers()
            return
        if not self.guard():
            return
        from urllib.parse import parse_qs
        code = (parse_qs(self.path.partition("?")[2]).get("c") or [""])[0][:40]
        esc = lambda text: str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")      # noqa: E731
        page = ('<!doctype html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer"><title>%s</title>'
                '<style>body{margin:0;min-height:100vh;display:grid;place-items:center;font:16px system-ui,sans-serif;background:#0d1117;color:#e6edf3;text-align:center;padding:24px}'
                'button{margin-top:16px;padding:12px 24px;min-height:44px;font:inherit;border:0;border-radius:8px;background:#2f81f7;color:#fff}#out{margin-top:12px;min-height:1.4em}</style></head>'
                '<body><main><h1>%s</h1><p>%s</p><button id="go" type="button">%s</button><p id="out" role="status"></p></main>'
                '<script>const code=%s,bad=%s;document.getElementById("go").onclick=async()=>{const o=document.getElementById("out");try{const r=await fetch("/api/pair/redeem",{method:"POST",'
                'headers:{"Content-Type":"application/json"},body:JSON.stringify({code})});const j=await r.json();if(j.ok){location.href="/"}else{o.textContent=bad[j.error]||bad.wrong}}catch(e){o.textContent=bad.wrong}}</script></body></html>') % (
            esc(i18n.language()), esc(i18n.t("ui.pair_page_title")), esc(i18n.t("ui.pair_page_title")), esc(i18n.t("ui.pair_page_text")), esc(i18n.t("ui.pair_page_button")), json.dumps(code).replace("</", "<\\/"),
            json.dumps({k: i18n.t("ui.pair_err_" + k) for k in ("closed", "wrong", "full", "locked", "off")}).replace("</", "<\\/"))
        self.reply(page, "text/html; charset=utf-8")

    def pair_post(self, path):
        """POST /api/pair/start (this computer: opens a code and answers its address and QR code), /api/pair/redeem (the phone: spends the code and gets its cookie) and /api/devices/revoke
        ({id}: this computer takes a device away). All three need `pairing.enabled` and the network mode."""
        from github_actions_monitor.security import audit_log, devices
        cfg = devices.settings(toolconfig.raw_config())
        if not cfg["enabled"] or LITE["on"]:
            self.json_reply({"ok": False, "error": "off"}, 404)
            return
        if not localguard.STATE["network"]:
            self.json_reply({"ok": False, "error": "not_network"}, 409)
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            request = json.loads(self.rfile.read(size) if 0 < size <= 1024 else b"{}")
        except (ValueError, TypeError):
            request = {}
        request = request if isinstance(request, dict) else {}
        if path == "/api/pair/redeem":
            if not self.guard():
                return
            if not self.is_local() and localguard.is_locked_out(self.client_address, self.headers, token_ok=False):
                self.json_reply({"ok": False, "error": "locked"}, 429)
                return
            token, answer = devices.redeem(cfg, request.get("code"), self.headers.get("User-Agent"))
            if token is None:
                if answer == "wrong":      # a guess counts against the address like a wrong access token
                    localguard.note_failure(localguard.client_key(self.client_address, self.headers), localguard.max_failed(LIVE_CONFIG or DEFAULTS))
                audit_log.note("redeem")
                self.json_reply({"ok": False, "error": answer}, 403)
                return
            audit_log.note(answer["id"])
            body = json.dumps({"ok": True, "device": answer}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Set-Cookie", localguard.cookie_header(token, secure=False if self.local_door else None) + "; Max-Age=%d" % ((cfg["device_days"] or 3650) * 86400))
            self.end_headers()
            self.wfile.write(body)
            return
        if not self.guard() or not self.this_computer() or not self.token_ok():
            return
        if path == "/api/pair/start":
            from github_actions_monitor.util import qrcode
            opened = devices.start(cfg)
            host = (self.headers.get("Host") or "").strip()
            name = host.rsplit(":", 1)[0].strip("[]") if host else ""
            if not host or name in localguard.LOOPBACK_HOSTS or name == "::1":      # a phone cannot reach the loopback address: the address of this computer on the network
                host = "%s:%s" % (lan_address(), self.server.server_address[1])
            url = "%s://%s/pair?c=%s" % ("https" if localguard.STATE["secure"] else "http", host, opened["code"])
            audit_log.note("start")
            self.json_reply({"ok": True, "url": url, "code": opened["code"], "expires_in": opened["expires_in"], "svg": qrcode.svg(url, label=i18n.t("ui.pair_qr_alt"))})
            return
        if path == "/api/devices/revoke":
            done = devices.revoke(str(request.get("id") or ""))
            audit_log.note(str(request.get("id") or "")[:20])
            self.json_reply({"ok": done, "error": "" if done else "unknown"}, 200 if done else 404)

    def access_gate(self):
        """Network mode only: every request must prove the access token (cookie, header or `?access=` on the first visit, which sets the cookie and goes to the clean address)."""
        self.deprecated_access = False
        if not localguard.STATE["network"] or self.path.split("?")[0] in ("/api/webhook", "/api/chatops/slack", "/api/chatops/discord"):      # the webhook and the chat have their own proof (the HMAC of GitHub, the signature of Slack or of Discord)
            return True
        if (self.command == "GET" and self.path.split("?")[0] == "/pair") or (self.command == "POST" and self.path.split("?")[0] == "/api/pair/redeem"):      # a phone with a one-use code has no token yet: the code is its proof (pair_page, pair_post)
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
        if not self.is_local() and localguard.is_locked_out(self.client_address, self.headers, token_ok=localguard.access_ok(self.headers, query_token)):      # the lock is looked at FIRST for every address that is not this computer: a locked address cannot keep guessing, not even with the right token
            self.json_reply({"error": "locked"}, 429)
            return False
        if not localguard.access_ok(self.headers, query_token):      # the person at this computer is never locked out of their own monitor; a shared proxy address is told apart with listen.trusted_proxy
            if localguard.presented(self.headers) or query_token:      # a request that carries NO token is not a guess: it is refused but it does not count against its address
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
        if not self.is_local() and localguard.is_locked_out(self.client_address, self.headers, token_ok=True):      # the lock of this address, as in every other request (access_gate); the common one is looked at below, once the token is known
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
        right = localguard.access_ok({}, candidate)
        if not self.is_local() and localguard.is_locked_out(self.client_address, self.headers, token_ok=right):
            self.json_reply({"error": "locked"}, 429)
            return
        if not right:
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
        key = envguard.get(SUPERVISOR_KEY_ENV)
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

    #: besides the routes of the table of audited_posts, the silences also leave a line of their own; the settings are not here on purpose: they must stay open to put the log right
    def do_POST(self):
        counted = CountedReader(self.rfile)
        self.rfile = counted
        self.reply_status, self.reply_ok = 0, None
        try:
            if not self.access_gate() or not auth_http.gate(self, LIVE_CONFIG or DEFAULTS, LITE["on"]):
                return
            from github_actions_monitor.security import audit_log, audited_posts
            audit_log.take_note()
            route = self.path.split("?")[0]
            if (audited_posts.action_for(route) or route in AUDIT_REQUIRED_ROUTES) and not audit_log.writable(toolconfig.raw_config()):      # `audit_log.required`: an action that cannot be recorded is not done
                self.json_reply({"ok": False, "error": "audit_log_required", "code": "audit_unwritable"}, 503)
                return
            with i18n.use_language(self.request_language()):
                try:
                    self.handle_post()
                except Exception as error:      # noqa: BLE001 - see storage_failure
                    if not self.storage_failure(error):
                        raise
            self.audit_post(self.path.split("?")[0])
        finally:
            self.drain_body(counted)

    def chatops_post(self, provider):
        """POST /api/chatops/slack and /api/chatops/discord: a command of the chat, read only (chatops/inbound.py). The proof is the signature of the platform, checked before anything is read; every command that reaches
        the monitor leaves one line in the log of actions with the ids of the chat and never the text."""
        from github_actions_monitor.chatops import inbound
        from github_actions_monitor.security import audit_log
        config = LIVE_CONFIG or DEFAULTS
        if not inbound.active(config, provider):      # closed: nothing to say to anyone
            self.json_reply({"ok": False}, 404)
            return
        if localguard.over_rate("chatops.ip", str(self.client_address[0]), 120):      # one address cannot flood the receiver (each check of a signature costs time)
            self.json_reply({"ok": False, "error": "rate"}, 429)
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(size) if 0 <= size <= inbound.MAX_BODY else b"x" * (inbound.MAX_BODY + 1)
            code, answer, record = inbound.handle(provider, config, body, self.headers, lambda: chatops_snapshot(config))
            if record:
                audit_log.record(toolconfig.raw_config(), "chatops_command", provider + ":" + record["user"], "chat", CHILD["account"] or "", provider + ":" + (record["command"] or "none"),
                                 record["result"], {"channel": record["channel"], "status": code})
            self.json_reply(answer, code)
        except Exception as error:   # noqa: BLE001 - the chat gets a plain refusal and nothing of the error
            degraded.note("chatops", error)
            self.json_reply({"ok": False}, 400)

    def handle_post(self):
        path = self.path.split("?")[0]
        if LITE["on"] and path.startswith(LITE_PATHS) and path not in LITE_SHARED:
            self.send_response(404)
            self.end_headers()
            return
        if path == "/api/access":      # network mode: open the session with the access token in the BODY (never in the address); the cookie comes back and the token is not repeated
            self.open_session()
            return
        if path in ("/api/pair/start", "/api/pair/redeem", "/api/devices/revoke"):      # the pairing of a phone (security/devices.py)
            self.pair_post(path)
            return
        if path == "/api/expected-red":      # mark or unmark a workflow as "expected red": a note of this monitor, never a change on GitHub
            self.expected_red_post()
            return
        if path == "/api/credential":      # replace the login of this account, or read its files again, without a restart (complete edition)
            if not self.guard() or not self.this_computer():
                return
            self.credential_post()
            return
        if path in ("/api/screens/logo", "/api/screens/logo/remove"):      # the logo of the organization: the image is the body of the request (at most 1 MB, checked by its first bytes)
            if not self.guard() or not self.token_ok():
                return
            from github_actions_monitor.security import audit_log
            try:
                if path.endswith("/remove"):
                    audit_log.note("remove")
                    self.json_reply({"ok": True, "removed": orglogo.remove(), "logo": orglogo.info()})
                    return
                size = int(self.headers.get("Content-Length") or 0)
                if size <= 0 or size > orglogo.MAX_BYTES:
                    self.json_reply({"ok": False, "error": "too_big" if size > 0 else "empty"}, 413 if size > 0 else 400)
                    return
                data = self.rfile.read(size)
                kind, reason = orglogo.validate(data)
                if kind is None:
                    self.json_reply({"ok": False, "error": reason}, 400)
                    return
                audit_log.note("upload", {"kind": kind, "bytes": len(data)})
                self.json_reply({"ok": True, "logo": orglogo.save(data)})
            except (ValueError, OSError):
                self.json_reply({"ok": False, "error": "request"}, 400)
            return
        if path == "/api/assistant/ask":      # a fixed question to the assistant (assistant.py): off = this route does not exist; the role of the person decides which tools it may use
            from github_actions_monitor.integrations import assistant
            from github_actions_monitor.sentinels import sentinel_ai
            if not self.guard():
                return
            if not assistant.settings(sentinel_ai.ai_config(toolconfig.raw_config()))["enabled"]:
                self.send_response(404)
                self.end_headers()
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= 1024 else b"{}")
                if not isinstance(request, dict):
                    self.json_reply({"ok": False, "error": "argument"}, 400)
                    return
                context = getattr(self, "auth_user", None)
                answer = assistant_ask(request, context["role"] if context else "admin")
                self.json_reply(answer, 200 if answer.get("ok") or answer.get("error") not in ("action", "argument") else 400)
            except Exception as error:   # noqa: BLE001 - the answer never repeats the request
                degraded.note("assistant.ask", error)
                self.json_reply({"ok": False, "error": "unavailable"}, 500)
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
            try:
                size = int(self.headers.get("Content-Length") or 0)
                limit = webhook.guard_settings(LIVE_CONFIG or DEFAULTS)["max_body"]
                body = self.rfile.read(size) if 0 <= size <= limit else b""      # a body over the limit is not read: the declared size is what answers 413
                code, answer = webhook_receive(LIVE_CONFIG or DEFAULTS, body, self.headers, self.webhook_sender(), size if not 0 <= size <= limit else None)
                self.json_reply(answer, code, **({"headers": {"Retry-After": "30"}} if code == 503 else {}))
            except Exception:
                self.json_reply({"ok": False}, 400)
            return
        if path in ("/api/chatops/slack", "/api/chatops/discord"):   # off unless configured; no Host check (the platform comes through a tunnel or a proxy), but every request must carry a valid signature
            self.chatops_post(path.rsplit("/", 1)[1])
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
                from github_actions_monitor.security import audit_log
                audit_log.note(str(request.get("mode"))[:30])
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
                from github_actions_monitor.security import audit_log
                audit_log.note(str(chosen[0]["key"])[:60])
                result = discovery.add_group(target, chosen[0]["key"], chosen[0]["prefix"], example=paths.EXAMPLES / "ecosystems.example.json")
                if result["ok"]:
                    toolconfig.forget()
                    DISCOVERED["at"] = 0.0
                    DISCOVERY["suggestions"] = [g for g in DISCOVERY["suggestions"] if g["key"] != chosen[0]["key"]]
                self.json_reply(result, 200 if result["ok"] else 400)
            except (ValueError, OSError):
                self.json_reply({"ok": False, "error": "request"}, 400)
            return
        if path in THIS_COMPUTER_ACTIONS:   # one request, one explicit person: local only, small JSON body
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
        if path in THIS_COMPUTER_ADVANCED:
            if not self.guard() or not self.this_computer():
                return
            if path == "/api/ops/purge" and not ops_purge_on():      # the purge on demand does not exist (for this computer) until an administrator switches it on
                self.send_response(404)
                self.end_headers()
                return
            if path != "/api/welcome" and path != "/api/gh-action/plan" and path != "/api/act/plan" and not self.token_ok():
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size) if 0 < size <= (8192 if path == "/api/report-files/summary" else 2048) else b"{}")      # the text of a summary is up to 1200 characters
                answer = handle_advanced_post(path, request if isinstance(request, dict) else {}, auth_http.acting_user(self))
                self.json_reply(answer)
                if path in ("/api/updates/apply", "/api/updates/rollback") and isinstance(answer, dict) and answer.get("started"):      # the process of the update is waiting for this one to stop
                    from github_actions_monitor.ops import updates
                    updates.stop_soon(self.server)
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
                touches_log = isinstance(changes, dict) and any(str(k).startswith("audit_log.") for k in changes)      # switching the log off is written even though it is off by then
                audit_action(self, "settings_change", "settings", {"settings": sorted(str(k)[:80] for k in changes)[:30]} if isinstance(changes, dict) else None, "ok" if result.get("ok") else "error", force=touches_log)
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
        self.reply_status = 0
        try:
            self.serve_get()
        except Exception as error:      # noqa: BLE001 - only a storage that does not answer is turned into an answer; anything else goes on as it always did
            if not self.storage_failure(error):
                raise

    def storage_failure(self, error):
        """A storage that does not answer (the database is locked, gone or full; the disk is unplugged) is a 503 with `Retry-After`, never a connection that drops with no answer. The monitor keeps running and
        the next request that finds the storage back is served as usual. True when the error was that. A browser that closed the tab is not a storage failure."""
        from github_actions_monitor.storage import base, state_io
        import sqlite3
        if isinstance(error, CLIENT_GONE):
            return False
        cause = error.__cause__
        if not (isinstance(error, (base.StorageError, sqlite3.Error)) or (isinstance(error, OSError) and isinstance(cause, (sqlite3.Error, base.StorageError)) and state_io.bound()[0] is not None)):
            return False      # a file that does not exist is not a storage that does not answer: only what state_io raised FROM a database error counts
        STORE_DOWN[0] += 1
        if getattr(self, "reply_status", 0):      # an answer is already on its way: the connection ends and the client asks again
            self.close_connection = True
            return True
        body = json.dumps({"ok": False, "error": "storage_unavailable", "retry_after": STORE_RETRY_SECONDS}).encode("utf-8")
        try:
            self.send_response(503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Retry-After", str(STORE_RETRY_SECONDS))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass
        return True

    def serve_get(self):
        self.v1 = False
        if self.path.split("?")[0] == "/robots.txt" and noindex_on(toolconfig.raw_config()):      # nothing here is for a search engine; the file is public and says so
            self.reply("User-agent: *\nDisallow: /\n", "text/plain; charset=utf-8")
            return
        if not self.access_gate():      # the access token first: the 404 of a switch that is off does not tell a visitor without credentials whether the versioned API exists
            return
        if not self.v1_enter() or not auth_http.gate(self, LIVE_CONFIG or DEFAULTS, LITE["on"]):
            return
        viewers.touch(self.path)      # a page, a wall screen or a live stream asking for data is somebody looking (modes.idle_minutes)
        with i18n.use_language(self.request_language()):
            if self.v1 and self.path.split("?")[0] in api_v1.OWN_ROUTES:
                self.handle_v1()
            else:
                self.handle_get()

    def v1_enter(self):
        """The prefix `/api/v1/` (app/api_v1.py): 404 while `api.v1_enabled` is off (or "auto" outside the service mode), in the lite edition and for any other version. A route that already exists is served under its old path (so the
        same roles and the same gate apply to it); the three own routes (me, repos, openapi.json) keep theirs and are answered by `handle_v1`."""
        path = self.path.split("?")[0]
        version, rest = api_v1.route_of(path)
        if version is None:
            return True
        if LITE["on"] or version != api_v1.API_VERSION or not api_v1.enabled(api_v1.settings(toolconfig.raw_config()), service_mode()):
            self.send_response(404)
            self.end_headers()
            return False
        if path not in api_v1.OWN_ROUTES and api_spec.experimental(rest) and not api_v1.settings(toolconfig.raw_config())["experimental_routes"]:      # a route the contract does not freeze: 404 unless `api.experimental_routes`
            self.send_response(404)
            self.end_headers()
            return False
        self.v1 = True
        if path not in api_v1.OWN_ROUTES:
            self.path = rest + self.path[len(path):]
        return True

    def handle_v1(self):
        """GET /api/v1/me, /api/v1/repos and /api/v1/openapi.json: read only, from what the monitor already holds (no call to GitHub). Errors use the envelope of api_v1."""
        from urllib.parse import parse_qs
        path = self.path.split("?")[0]
        cfg = api_v1.settings(toolconfig.raw_config())
        ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
        try:
            if path == "/api/v1/openapi.json":
                payload = api_spec.document(TOOL_VERSION, experimental_routes=cfg["experimental_routes"])
            elif path == "/api/v1/me":
                context = getattr(self, "auth_user", None)
                team = auth_http.active(LIVE_CONFIG or DEFAULTS, LITE["on"]) or bool(context)      # the process of an account is told by its supervisor, with a signed context, that the team mode is on
                payload = api_v1.me_payload(version=TOOL_VERSION, edition="complete", mode="team" if team else "individual", authenticated=bool(context), user=auth_http.acting_user(self),
                                            role=context["role"] if context else None, accounts=context["accounts"] if context else None, cfg=cfg)
            else:
                payload = api_v1.repos_payload(health_views(), ask, secret=V1_SECRET, now=time.time(), cfg=cfg, who=f"{auth_http.acting_user(self) or ''}|{CHILD['account'] or ''}")      # a cursor belongs to who asked for it
        except api_v1.ApiError as error:
            status, body = error.envelope()
            self.json_reply(body, status)
            return
        except Exception:   # noqa: BLE001 - whatever else goes wrong is the envelope of a 500, never a cut connection with a trace in the console
            status, body = api_v1.ApiError(500, "api.server_error").envelope()
            self.json_reply(body, status)
            return
        body, extra = api_v1.maybe_compress(json.dumps(payload).encode("utf-8"), self.headers.get("Accept-Encoding"), cfg["gzip_min_bytes"])
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in extra.items():
            self.send_header(key, value)
        try:
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass

    def handle_get(self):
        path = self.path.split("?")[0]
        if path == "/favicon.ico":      # a browser (a kiosk at every start) asks for it: nothing to give, and no error in its console
            self.send_response(204)
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            return
        if LITE["on"] and path.startswith(LITE_PATHS) and path not in LITE_SHARED:      # the lite product does not have these endpoints
            self.send_response(404)
            self.end_headers()
            return
        if path in ("/pair", "/api/devices", "/api/pair/status", "/manifest.webmanifest", "/sw.js", "/pwa/offline", "/pwa/icon-192.png", "/pwa/icon-512.png"):      # the app, the pairing page and the devices
            if self.pwa_get(path):
                return
        if path in ("/api/whats-new", "/api/glossary"):      # the notes of the page: read only, from the files of the installed version
            if not self.guard():
                return
            if path == "/api/glossary":
                from github_actions_monitor.ui import glossary
                self.json_reply(glossary.payload(toolconfig.raw_config()))
            else:
                from urllib.parse import parse_qs
                from github_actions_monitor.ui import whats_new
                ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
                raw = toolconfig.raw_config()
                self.json_reply(whats_new.payload(i18n.language(), ask.get("since", ""), TOOL_VERSION, (raw.get("display") or {}).get("whats_new") is not False))
            return
        if path in ("/api/expected-red", "/api/clone-anomalies", "/api/meta-columns"):      # the notes of this monitor: read only (the marks are written by POST /api/expected-red)
            if not self.guard():
                return
            from github_actions_monitor.data_pipeline import expected_red
            from github_actions_monitor.sentinels import clone_anomaly
            raw = toolconfig.raw_config()
            if path == "/api/expected-red":
                cfg = expected_red.settings(raw)
                self.json_reply({"enabled": cfg["enabled"], "max_days": cfg["max_days"], "entries": expected_red.entries() if cfg["enabled"] else []})
            elif path == "/api/clone-anomalies":
                self.json_reply(clone_anomaly.check(gh_read, toolconfig.github_owner(raw), clone_anomaly.settings(raw)))
            else:
                self.json_reply(meta_columns_payload())
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
        if path == "/api/sentinel/security":      # what GitHub says is open or missing about security (the Security sentinel; off by default; read only)
            if not self.guard():
                return
            security = (SENTINEL["registry"].get("security") if SENTINEL["registry"] else None)
            try:
                self.json_reply({"data": security.snapshot() if security else None, "error": SENTINEL["error"] or (None if security else i18n.t("mon.sentinel_not_loaded"))})
            except Exception as error:      # shown as a notice in the tab
                self.json_reply({"data": None, "error": i18n.t("mon.sentinel_failed", error=error)})
            return
        if path == "/api/sentinel/supply":      # what the workflow files let a moved tag or an outsider do (the Supply chain sentinel; off by default; read only)
            if not self.guard():
                return
            supply = (SENTINEL["registry"].get("supply") if SENTINEL["registry"] else None)
            try:
                self.json_reply({"data": supply.snapshot() if supply else None, "error": SENTINEL["error"] or (None if supply else i18n.t("mon.sentinel_not_loaded"))})
            except Exception as error:      # shown as a notice in the tab
                self.json_reply({"data": None, "error": i18n.t("mon.sentinel_failed", error=error)})
            return
        if path == "/api/sentinel/delivery":      # whether what is built is also delivered (the Delivery sentinel; off by default; read only)
            if not self.guard():
                return
            delivery = (SENTINEL["registry"].get("delivery") if SENTINEL["registry"] else None)
            try:
                self.json_reply({"data": delivery.snapshot() if delivery else None, "error": SENTINEL["error"] or (None if delivery else i18n.t("mon.sentinel_not_loaded"))})
            except Exception as error:      # shown as a notice in the tab
                self.json_reply({"data": None, "error": i18n.t("mon.sentinel_failed", error=error)})
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
        if path == "/api/screens/logo":      # the logo of the organization (docs/SCREENS.md): the image itself, with its real type; it is also what Settings shows as a preview
            if not self.guard():
                return
            found = orglogo.load()
            if not found:
                self.send_response(404)
                self.end_headers()
                return
            data, ctype, tag = found
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("ETag", '"' + tag + '"')
            self.send_header("Cache-Control", "private, max-age=3600")      # the address carries the tag of the file (?v=): a new logo has a new address
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; sandbox")
            try:
                self.end_headers()
                self.wfile.write(data)
            except CLIENT_GONE:
                DISCONNECTS[0] += 1
            return
        if path == "/api/screens/menu":      # the Screens menu of the page (docs/SCREENS.md): the catalogue of every kind of screen with its address and parameters; navigation only, nothing is read from GitHub
            if not self.guard():
                return
            self.json_reply(screenmenu.payload(toolconfig.raw_config(), LITE["on"]))
            return
        if path == "/api/screens/logo/info":
            if not self.guard():
                return
            self.json_reply(orglogo.info())
            return
        if screens.kind_of(path) or path == "/api/screens/data":      # the wall screens (docs/SCREENS.md): read only; 404 while screens.enabled is off
            if not self.guard():
                return
            from urllib.parse import parse_qs
            ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            kind = screens.kind_of(path) or ask.get("screen", "")
            if not screens.enabled(toolconfig.raw_config()) or (path == "/api/screens/data" and kind not in screens.KINDS):
                self.send_response(404)
                self.end_headers()
                return
            if path == "/api/screens/data":
                self.json_reply(screens_payload(kind, screens.settings(toolconfig.raw_config()), ask.get("repo", "")))
            else:
                self.reply(render_screen(kind, ask), "text/html; charset=utf-8")
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
        elif path == "/readyz":   # ready to serve? (the loop, the data folder, the queue of the receiver): local only, no GitHub call; 200 or 503, with each check
            if not self.guard():
                return
            payload, code = readiness()
            self.json_reply(payload, code)
        elif path == "/api/version":      # what a page that stays open for days asks to know whether the monitor was updated or restarted under it (wall screens, kiosk): never cached, no GitHub call
            if not self.guard():
                return
            self.json_reply({"version": TOOL_VERSION, "started": int(STARTED)}, headers={"Cache-Control": "no-store"})
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
            self.json_reply(POOL_STATUS["payload"] or pool_status_pending())      # what the cycle read: a request never reads GitHub
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
            self.json_reply(__import__("github_actions_monitor.security.redactor", fromlist=["_"]).redact_data(ai_state(lang)))      # the same cleaner as the feed, the brief and the MCP
        elif path in ("/api/ai/index", "/api/ai/briefs"):      # read only: the master index of the briefs and the brief of one tab (briefs.py); the same in both editions, cleaned like the state
            if not self.guard():
                return
            self.json_reply(*briefs_get(path, self.path.partition("?")[2], self.headers.get("User-Agent") or ""))
        elif path == "/api/report/tab":      # read only: the report of one tab as data, text or the options of the saving dialog (reporting/tab_report.py); the same in both editions, cleaned like the briefs
            if not self.guard():
                return
            kind, document, status = report_get(path, self.path.partition("?")[2])
            if kind == "text":
                self.reply(document, "text/plain; charset=utf-8")
            else:
                self.json_reply(document, status)
        elif path == "/api/report/tab.pdf":      # this computer only: the same report written as a PDF by the monitor itself (no library, standard fonts); a script the fonts lack answers 422 and the page prints through the browser
            if not self.guard() or not self.this_computer():
                return
            kind, document, status = report_get(path, self.path.partition("?")[2])
            if kind == "pdf":
                audit_action(self, "report_export", "pdf", {"tab": re.sub(r"[^a-z0-9]", "", self.path.partition("tab=")[2].partition("&")[0])[:12] or "now", "bytes": len(document)})
                self.reply_bytes(document, "application/pdf")
            else:
                self.json_reply(document, status)
        elif path == "/api/skills":      # read only: the two skills of the monitor as text (?name=internal|external[&file=references/api.md][&all=1])
            if not self.guard():
                return
            kind, document = skills_get(self.path.partition("?")[2])
            if kind == "md":
                self.reply(document, "text/markdown; charset=utf-8")
            else:
                self.json_reply(document, 200 if document.get("ok", True) else 404)
        elif path == "/api/reports":      # read only: the four optional reports (workflow hygiene, queue by runner, release ready or blocked, supply chain), each on only when its setting is
            if not self.guard():
                return
            from github_actions_monitor.integrations import reports
            from github_actions_monitor.data_pipeline import freshness
            config = LIVE_CONFIG or toolconfig.raw_config()

            def build_reports():
                snapshot = None
                sentinel = SENTINEL.get("obj")
                if sentinel is not None and reports.settings(config)["release_view"]:
                    snapshot = sentinel.snapshot()
                return reports.payload(config, snapshot)
            state, value, age = freshness.serve(("reports", CHILD["account"] or ""), build_reports, freshness.settings(config))
            if state == "error":
                raise value
            if state == "timeout":
                self.json_reply({"error": "the query took too long", "code": "query_timeout"}, 504)
                return
            self.json_reply(value, headers=freshness.headers(state, age))
        elif path == "/api/run-log":      # read only, off by default (logs.failed_step.enabled): the failing step of one run and its last relevant lines, cleaned (steplog.py)
            if not self.guard():
                return
            from urllib.parse import parse_qs
            from github_actions_monitor.integrations import steplog
            args = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            config = LIVE_CONFIG or toolconfig.raw_config()
            with LOCK:
                repos = list((STATE.get("data") or {}).get("repos") or [])
            answer = steplog.read(config, toolconfig.github_owner(config), args.get("repo", ""), args.get("run", ""), repos)
            self.json_reply(answer, 200 if answer.get("ok") else 403 if answer.get("error") == "off" else 400)
        elif path in ("/api/ai/lessons", "/api/ai/failures"):      # read only: the lessons that apply and the book of failures (lessons.py); data for an AI, never instructions
            if not self.guard():
                return
            refresh_feed()
            __import__("github_actions_monitor.integrations.ai_alerts", fromlist=["_"]).touch(toolconfig.raw_config(), "endpoint", self.headers.get("User-Agent") or "")
            kind, document = lessons_get(path, self.path.partition("?")[2])
            if kind == "md":
                self.reply(document, "text/markdown; charset=utf-8")
            else:
                self.json_reply(document)
        elif path == "/api/ai/presets":      # read only: the presets of AI providers (ai_presets.json): address, name of the variable of the key, example models, privacy; never a key
            if not self.guard():
                return
            from github_actions_monitor.sentinels import ai_presets
            self.json_reply({"ok": True, "presets": ai_presets.load()})
        elif path == "/api/ai/models":      # read only: the configured provider, the list of models kept (it never asks the provider), the check of the configured model and the table of data per model
            if not self.guard():
                return
            from github_actions_monitor.sentinels import ai_models, sentinel_ai
            self.json_reply(ai_models.listing(sentinel_ai.ai_config(toolconfig.raw_config()), ai_store()))
        elif path == "/api/assistant":      # read only: whether the assistant is on, its fixed actions, its tools and its limits (it spends nothing; off = it does not exist)
            if not self.guard():
                return
            from github_actions_monitor.integrations import assistant
            from github_actions_monitor.sentinels import sentinel_ai
            cfg = sentinel_ai.ai_config(toolconfig.raw_config())
            if not assistant.settings(cfg)["enabled"]:
                self.send_response(404)
                self.end_headers()
                return
            self.json_reply(assistant.describe(cfg))
        elif path == "/api/ai/prompts":      # read only, administrator: the local record of the cleaned prompts and answers (off by default; it only exists while `ai.prompt_log.enabled` is on)
            if not self.guard():
                return
            from github_actions_monitor.integrations import ai_prompt_log
            from github_actions_monitor.sentinels import sentinel_ai
            self.json_reply(ai_prompt_log.read(sentinel_ai.ai_config(toolconfig.raw_config()), 100))
        elif path == "/api/ai/budget":      # read only: the calls and the estimated cost of today for each model, the limits and the last failures of a main model
            if not self.guard():
                return
            from github_actions_monitor.sentinels import ai_chain, sentinel_ai
            self.json_reply(ai_chain.view(sentinel_ai.ai_config(toolconfig.raw_config()), ai_store()))
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
        elif path == "/api/runners/model":      # the model of the runners (kinds, queue and cost by kind, runaway workflows, self-hosted queues), read only; {"enabled": false} while it is off
            if not self.guard():
                return
            self.json_reply(runner_model_payload())
        elif path == "/api/team/health" or (path.startswith("/api/repos/") and path.endswith("/health")):      # the health of a repository and of the team, read only, from what is held (Complete only)
            if not self.guard():
                return
            from urllib.parse import parse_qs, unquote
            from github_actions_monitor.health import repo_view
            ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            if path == "/api/team/health":
                self.json_reply(repo_view.team_view(health_views(), ask.get("ecosystem", ""), ask.get("severity", ""), ask.get("q", "")[:80], ask.get("label", "")[:40]))
            else:
                parts = [unquote(x) for x in path.split("/")]      # ["", "api", "repos", owner, repo, "health"]
                owner, name = (parts[3], parts[4]) if len(parts) == 6 else ("", "")
                found = next(iter(health_views(only=name)), None) if owner.lower() == toolconfig.github_owner().lower() else None      # one repository: only its view is built
                self.json_reply({"schema": 1, "health": found} if found else {"error": "unknown repository", "code": "repo_unknown"}, 200 if found else 404)
        elif path == "/api/team/fleet":      # the same health grouped and paged for hundreds of repositories, read only, from what is held (Complete only)
            if not self.guard():
                return
            from urllib.parse import parse_qs
            from github_actions_monitor.health import fleet
            ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            self.json_reply(fleet.fleet_view(health_views(), toolconfig.raw_config(), ask.get("ecosystem", ""), ask.get("severity", ""), ask.get("q", "")[:80], ask.get("label", "")[:40],
                                             ask.get("group", ""), ask.get("sort", ""), ask.get("saved", "")[:30]))
        elif path in ("/api/score", "/api/score/history"):      # the score of the account of this process, from the snapshots of the hour (read only; Complete only)
            if not self.guard():
                return
            from urllib.parse import parse_qs
            from github_actions_monitor.scoring import api as score_api
            from github_actions_monitor.storage import runtime
            ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            if DEMO["on"]:      # --demo writes nothing: an invented score answers
                from github_actions_monitor.app import demo_mode
                self.json_reply(demo_mode.score_history(ask) if path.endswith("/history") else demo_mode.score_answer())
                return
            storage, account = runtime.process_storage(CHILD["account"] or None)
            config = toolconfig.raw_config()
            if path.endswith("/history"):
                self.json_reply(score_api.history(storage, account, config, ask))
                return
            answer = score_api.latest(storage, account, config)
            try:
                answer["missing_detail"] = score_missing_detail(SENTINEL.get("registry"), config, answer) if answer.get("state") != "off" else []
            except Exception:   # noqa: BLE001 - the reason is a help: the answer is given without it
                answer["missing_detail"] = []
            self.json_reply(answer)
        elif path == "/api/compare":      # this period against the one before, from the ledger and the snapshots of the score (read only; Complete only)
            if not self.guard():
                return
            from urllib.parse import parse_qs
            from github_actions_monitor.compare import compare_service, windows as compare_windows
            from github_actions_monitor.storage import runtime
            ask = {k: v[0][:80] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
            fmt = ask.pop("format", "json")
            if fmt not in compare_service.FORMATS:
                self.json_reply({"error": "bad format", "code": "bad_format"}, 400)
                return
            if DEMO["on"]:      # --demo writes nothing and holds no history: the answer says the comparison is off
                self.json_reply(compare_service.off_answer(CHILD["account"] or ""))
                return
            storage, account = runtime.process_storage(CHILD["account"] or None)
            from github_actions_monitor.data_pipeline import freshness
            config = toolconfig.raw_config()
            state, value, age = freshness.serve(("compare", account, tuple(sorted(ask.items())), repr((config.get("compare"), config.get("score")))), lambda: compare_service.build(storage, account, config, ask), freshness.settings(config))
            if state == "error":      # a bad request is answered as before; anything else was a failure of the computation itself
                if isinstance(value, compare_windows.WindowError):
                    self.json_reply({"error": "bad request", "code": value.code}, 400)
                    return
                raise value
            if state == "timeout":      # past analytics.query_timeout_s: the answer says so instead of waiting for ever (no copy young enough to serve exists)
                self.json_reply({"error": "the query took too long", "code": "query_timeout"}, 504)
                return
            answer, marks = value, freshness.headers(state, age)      # a stale copy is served at once and says so in two headers; the body is the same shape either way
            if fmt == "json":
                self.json_reply(answer, headers=marks)
            else:
                kind, text = compare_service.render(answer, fmt)
                body = text.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", kind + "; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for name, mark in marks.items():
                    self.send_header(name, mark)
                self.end_headers()
                self.wfile.write(body)
        elif path == "/api/audit-log":      # the log of actions of this account: an administrator, or a maintainer when the setting says so (Complete only)
            if not self.guard():
                return
            from github_actions_monitor.security import audit_log
            context = getattr(self, "auth_user", None) or {}
            config = toolconfig.raw_config()
            if LITE["on"] or not audit_log.may_read(config, context.get("role", "")):
                self.json_reply({"error": "forbidden", "code": "forbidden_role"}, 403)
                return
            self.json_reply({"schema": 1, "account": CHILD["account"] or "", "enabled": audit_log.settings(config)["enabled"], "chain": audit_log.verify(), "entries": audit_log.read(200, CHILD["account"] or None),
                             "write_failures": audit_log.STATS["write_failures"], "last_write_error_at": audit_log.STATS["last_write_error_at"]})
        elif path == "/api/updates/stream":      # the progress of an update as server-sent events (the page falls back to asking every 1.5 s); Complete only, read only
            if not self.guard():
                return
            self.updates_stream()
        elif path in ("/api/updates/status", "/api/updates/progress", "/api/updates/history", "/api/updates/log", "/api/updates/copies"):      # the Updates menu: what is installed, what is new, the progress of an update, the updates done (Complete only; no path, no secret)
            if not self.guard():
                return
            from github_actions_monitor.ops import updates
            if path.endswith("progress"):
                self.json_reply(updates.progress())
            elif path.endswith("history"):
                self.json_reply({"entries": updates.history()})
            elif path.endswith("/log"):      # the last lines of the log of the process of the last update (the values after token, secret, password are hidden); Complete only
                from urllib.parse import parse_qs
                ask = {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items() if v}
                self.json_reply(updates.process_log(whole(ask.get("lines"), 200)))
            elif path.endswith("/copies"):      # the copies in the folder of copies: name, status, versions, size, whether one can be discarded; Complete only
                self.json_reply({"copies": updates.copies()})
            else:
                self.json_reply(updates.status(toolconfig.raw_config(), TOOL_VERSION, update_info(read=False), lite=LITE["on"], demo=DEMO["on"]))
        elif path == "/api/ops/status":      # the operation of the installation: the last copy, the schedule, the purge switch and the retention in force (Complete only; no path, no secret)
            if not self.guard():
                return
            from github_actions_monitor.ops import schedule
            self.json_reply(schedule.overview(toolconfig.raw_config()))
        elif path in ("/api/report-files", "/api/report-files/file"):      # the scheduled reports: the list and one file, read only, of the account of this process (Complete only)
            if not self.guard():
                return
            from urllib.parse import parse_qs
            from github_actions_monitor.reporting import report_service
            config, account = toolconfig.raw_config(), report_account()
            if path == "/api/report-files":
                cfg = report_service.settings(config)
                from github_actions_monitor.reporting import report_summary
                self.json_reply({"schema": 1, "account": account, "enabled": cfg["enabled"], "cron": cfg["cron"], "formats": cfg["formats"], "reports": report_service.listing(account),
                                 "summary": {"ai": report_summary.enabled(config), "next": report_service.pending_summary(account)}})
                return
            name = (parse_qs(self.path.partition("?")[2]).get("name") or [""])[0]
            found = report_service.read_file(account, name)
            if found is None:
                self.json_reply({"error": "unknown report", "code": "report_unknown"}, 404)
                return
            body = found[0]
            self.send_response(200)
            self.send_header("Content-Type", found[1])
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/analytics":
            if not self.guard():
                return
            self.json_reply(ANALYTICS["summary"] or {"enabled": ANALYTICS["store"] is not None, "duration": [], "queue": [], "steps": [], "flaky": [], "slower": [], "time_saved": timesaved.off()})
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
                rows = alert_center.read_events(events_mod.EVENTS_FILE, ask.get("sentinel", ""), ask.get("since", ""), min(500, whole(ask.get("limit"), 200)))
                self.json_reply({"schema": 1, "account": CHILD["account"] or None, "events": rows})
            else:
                self.json_reply(alerts_payload(ask))
        elif path == "/api/live-events":
            if not self.guard():
                return
            self.json_reply({"events": list(reversed(LIVE_EVENTS))})
        elif path == "/api/live-events/stream":      # server-sent events, read only: the webhook events as they are accepted (live.sse, off by default)
            if not self.guard():
                return
            self.live_stream()
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
            self.json_reply({"state": ai_actions.ACTIONS.state(toolconfig.raw_config()), "log": ai_actions.ACTIONS.log(), "proposals": ai_actions.ACTIONS.listing(toolconfig.raw_config()),
                             "ai": sentinel_ai.status(sentinel.ai_cfg, sentinel.ai_store) if sentinel is not None and sentinel.ai_cfg["provider"] != "none" else None})
        elif path.startswith("/api/data"):
            if not self.guard():
                return
            with LOCK:      # only the references are taken under the lock: writing to a slow or dead connection with the lock held froze every other page and the cycle itself
                picture = {"data": STATE["data"], "error": STATE["error"], "hint": STATE["hint"]}
            picture = {**picture, "loop": WATCH.snapshot(limit_seconds=watchdog_limit(LIVE_CONFIG or DEFAULTS))}
            self.reply(json.dumps(picture), "application/json; charset=utf-8")
        elif path in ("/", "/index.html") or re.fullmatch(r"/screen/[1-3]/?", path):
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
              "ai_internal": {"enabled": str(((LIVE_CONFIG or toolconfig.raw_config()).get("ai") or {}).get("provider") or "none").lower() not in ("", "none")},      # the AI built into the monitor is configured (never its key)
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
    extra = credential_alerts() + score_alerts() + runner_alerts() + mark_alerts()
    everything = alert_center.collect(registry, extra=extra)
    chosen = alert_center.select(everything, ask.get("sentinel", ""), ask.get("level", ""), ask.get("muted", "show") if ask.get("muted") in ("show", "hide", "only") else "show")
    out = {"schema": 1, "account": CHILD["account"] or None, "alerts": chosen, "summary": alert_center.summary(everything), "mutes": alert_center.active(), "history": alert_center.history(20),
           "mute_hours": alert_center.hours_setting(LIVE_CONFIG or toolconfig.raw_config()), "sentinels": (registry.names() if registry else []) + (["system"] if extra else [])}
    if ask.get("since"):      # ?since=24h: the alerts that were open at some moment of that time, closed ones too (the ledger of what was seen)
        seconds = alert_center.parse_since(ask["since"])
        out["since"] = {"seconds": seconds, "error": None if seconds else "bad_since", "alerts": alert_center.recent(seconds, ask.get("sentinel", ""), ask.get("level", "")) if seconds else []}
    return out


def service_mode():
    """True for a monitor that runs as a service: the process of one account under a supervisor, or MONITOR_SERVICE=1 (the image, the systemd unit). It does not give up when the login of GitHub is no good at
    start: it stays up, says so, and waits for another one."""
    return bool(CHILD["account"]) or os.environ.get("MONITOR_SERVICE", "").strip() == "1"


def cycle_verdict():
    """'' when the refresh loop is fine, 'stuck' when one cycle has run longer than the limit of the watchdog (`watchdog_minutes`, 30 minutes when that is off) and 'dead' when its thread is gone."""
    thread = LOOP["thread"]
    limit = watchdog_limit(LIVE_CONFIG or DEFAULTS) or 1800
    verdict = cycle_watch.check(WATCH, limit, thread is not None and thread.is_alive())
    if not verdict and cycle_watch.blocked(abandoned_limit(None)):
        return "blocked"      # too many calls to GitHub that never returned are still alive: restarting the loop would not free them, so the monitor says it is degraded instead
    return verdict


def health_payload(deep=False):
    """The answer of /api/health. It never calls GitHub. Always: whether the data are loaded, the connection, and (complete edition) the state of the cycle and of the login of this account. With `deep` the
    answer also says whether the monitor is fit to serve: `ok` is false when the refresh loop is stuck or gone (see `health_reply`)."""
    with LOCK:
        loaded = bool(STATE.get("data"))
    out = {"ok": True, "lite": LITE["on"], "version": TOOL_VERSION, "uptime_seconds": int(time.time() - STARTED), "loaded": loaded, "offline": LINK.state()["offline"], "degraded": degraded.snapshot()["total"], "code_stale": codestale.stale(TOOL_VERSION), "selfwatch": selfwatch.WATCH.snapshot()}      # code_stale: the files on the disk are of another version than this process (it must be restarted)
    if CHILD["account"]:
        out["account"] = CHILD["account"]
    out["viewers"] = viewers.public(LIVE_CONFIG or DEFAULTS)      # whether the polling is aware of who is looking (modes.idle_minutes), for how long nobody has, and whether it is cold
    if not LITE["on"]:
        verdict = "" if DEMO["on"] else cycle_verdict()
        snap = WATCH.snapshot(limit_seconds=watchdog_limit(LIVE_CONFIG or DEFAULTS))
        out["cycle"] = {"phase": snap["phase"], "running_seconds": snap["running_seconds"], "seconds_since_ok": snap["seconds_since_ok"], "stuck": verdict == "stuck", "dead": verdict == "dead", "blocked": verdict == "blocked", "abandoned_calls": cycle_watch.abandoned()}
        out["credential"] = credential.snapshot()
        out["heartbeat"] = heartbeat.HEARTBEAT.snapshot(LIVE_CONFIG or DEFAULTS)
        if deep and verdict:
            out["ok"] = False
    return out


def health_reply(deep=False):
    """(payload, HTTP status): 200, or 503 when `deep` and the monitor is not fit to serve. The lite edition has no deep check and always answers 200."""
    payload = health_payload(deep and not LITE["on"])
    return payload, 200 if payload["ok"] else 503


def readiness():
    """(payload, HTTP status) of /readyz. /api/health says the process lives; this says whether it is fit to take work now: `loaded` (a first read is in), `cycle` (the refresh loop neither stuck nor gone,
    complete edition), `store` (the data folder can be written) and `queue` (the events of the receiver wait in a queue that is not full). Each check is named, so an orchestrator or a person sees which one holds
    it back. It never calls GitHub."""
    from github_actions_monitor.security import webhook
    health = health_payload(deep=not LITE["on"])
    queue = webhook.INBOX.snapshot(LIVE_CONFIG or DEFAULTS)
    try:
        folder = paths.folder("data")
        while not folder.exists() and folder != folder.parent:      # the folder is made when something is first written: the nearest one that exists must take a file
            folder = folder.parent
        store = os.access(str(folder), os.W_OK)
    except OSError:
        store = False
    checks = {"loaded": bool(health["loaded"]), "cycle": bool(health["ok"]), "store": store, "queue": queue["depth"] < queue["max"]}
    ready = all(checks.values())
    return {"ready": ready, "checks": checks, "queue": {"depth": queue["depth"], "max": queue["max"]}, "version": TOOL_VERSION}, 200 if ready else 503


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


def update_info(read=True):
    """The state of the update notice: the cached answer, refreshed (at most every 24 hours) through the conditional GitHub client; silent when it cannot be read. `read` False (a request of the page)
    only gives the cached answer: the loop that looks for updates is the one that reads."""
    config = LIVE_CONFIG or toolconfig.raw_config()
    state_file = state_dir() / ("update_check_lite.json" if LITE["on"] else "update_check.json")
    if DEMO["on"]:
        return updatecheck.view({"updates": {"check": False}}, TOOL_VERSION, {})
    return updatecheck.check(config, TOOL_VERSION, lambda endpoint: gh_read(endpoint, retries=0), state_file=state_file, offline=LINK.state()["offline"] or not read, background=True)      # never a network wait in the path of a page


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


def cost_inputs(data):
    """(every run the last cycle read, those completed in the last 24 hours, the repositories counted as private) for the cost figures: the whole read and not the cut of 600 of the page when the cycle
    kept it, and a repository whose visibility was never read counts as private (an upper bound), never as free."""
    since = time.time() - 86400
    listed = data.get("runs") or []
    full = ALL_RUNS["runs"]
    every = full if full and data.get("runs_total") == len(full) and len(full) >= len(listed) else listed
    done = [r for r in every if r.get("status") == "completed" and (parse_time(r.get("started")) or datetime.fromtimestamp(0, timezone.utc)).timestamp() > since]
    return every, done, set(PRIVATE) | {r.get("repo") for r in done if r.get("repo") not in VISIBILITY["known"]}


def quota_payload():
    from github_actions_monitor.data_pipeline import quota
    config = LIVE_CONFIG or toolconfig.raw_config()
    with LOCK:
        data = STATE.get("data") or {}
    _every, done, private = cost_inputs(data)
    rate = data.get("rate") or {}
    reader = None if DEMO["on"] else (lambda endpoint: gh_read(endpoint, retries=0))
    info = quota.summary(config, done, data.get("active") or [], private, reader, toolconfig.github_owner(config), rate.get("limit"), costs={k: v for k, v in RUN_COSTS.items() if v})
    from github_actions_monitor.data_pipeline import quotawatch
    info["accounts"] = quota_buckets.view(trend=quotawatch.trend())      # the allowance by account (source) and bucket, with the tightest one (the chip of the header)
    report = change_cost_report(config)
    if report.get("enabled"):
        info["by_change"] = report      # finops.by_change / finops.co2 (off by default)
    return info


def about_logo():
    """What the About panel needs to draw the logos: the logo of the monitor is always drawn by the page; the one of the organization only when `ui.about_org_logo` is on, with the tag of the file
    (the page builds the address of the image from it, so a new logo is never shown from the cache) when one is uploaded. A logo folder that cannot be read is "not present", never an error."""
    want = ((LIVE_CONFIG or toolconfig.raw_config()).get("ui") or {}).get("about_org_logo") is True
    found = {"present": False, "tag": ""}
    if want:
        try:
            found = orglogo.info()
        except Exception as error:      # noqa: BLE001 - a logo that cannot be read must never break the About panel
            degraded.note("about.logo", error)
    present = bool(found.get("present"))
    return {"org": {"enabled": want, "present": present, "tag": str(found.get("tag") or "")[:16] if present else ""}}


def about_payload():
    from github_actions_monitor.ui import about
    places = {"config": CONFIG_FILE, "log": LOG_FILE, "etag_cache": etagcache.CACHE_FILE, "package_folder": HERE}
    data = about.info(LITE["on"], health_payload(), places, update_info(read=False), i18n.language())
    data["support"] = about.support_text(data)
    data["logo"] = about_logo()
    return data


def discovery_payload():
    config = LIVE_CONFIG or toolconfig.raw_config()
    with LOCK:
        data = STATE.get("data") or {}
    box = discovery.box(toolconfig.github_owner(config), len(data.get("repos") or []), HIDDEN["discovered"], HIDDEN["names"], HIDDEN["reasons"])
    from github_actions_monitor.data_pipeline import orgs
    organisations = orgs.view(toolconfig.raw_config(), lambda endpoint: gh_read(endpoint, retries=0), state_dir() / ("orgs_state_lite.json" if LITE["on"] else "orgs_state.json"), offline=True) if not DEMO["on"] else {"enabled": False, "orgs": [], "checked_at": 0}      # offline=True: it shows what the cycle read, it never reads
    return {**box, "events": list(reversed(DISCOVERY["events"]))[:20], "suggestions": DISCOVERY["suggestions"], "settings": discovery.settings(config), "owner_kind": FORKS["kind"], "forks": {k: FORKS[k] for k in ("checked", "kept", "left", "waiting")}, "demo": DEMO["on"], "organizations": organisations}


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


def score_metrics():
    """The few figures of the score that /metrics shows (state, number, coverage), or None in Lite, with the score off or when nothing can be read."""
    if LITE["on"]:
        return None
    try:
        from github_actions_monitor.scoring import api as score_api
        from github_actions_monitor.storage import runtime
        storage, account = runtime.process_storage(CHILD["account"] or None)
        latest = score_api.latest(storage, account, toolconfig.raw_config())
        if latest.get("state") == "off":
            return None
        if latest.get("stale"):      # an old number is not exported as if it were current
            return {"state": "stale", "score": None, "coverage": latest.get("coverage")}
        return {"state": latest.get("state"), "score": latest.get("score"), "coverage": latest.get("coverage")}
    except Exception as error:   # noqa: BLE001 - /metrics must still answer
        degraded.note("score.metrics", error)
        return None


def metrics_extra():
    """What /metrics and the Grafana source add to the sentinel's picture: conditional reads, the connection, the analytics, the live events, the notifications and the score."""
    from github_actions_monitor.integrations import notifiers
    from github_actions_monitor.data_pipeline import quota
    config = LIVE_CONFIG or toolconfig.raw_config()
    return {"etag": ETAG["cache"].stats() if ETAG["cache"] else None, "offline": LINK.state()["offline"], "analytics": ANALYTICS["summary"], "live_events": len(LIVE_EVENTS),
            "notify": dict(notifiers.STATS), "disconnects": DISCONNECTS[0], "score": score_metrics(), "config": config, "run_cache": RUN_CACHE, "quota": quota.last(),
            "runners": None if LITE["on"] else runner_list(config), "runner_waits": runner_wait_figures(config),
            "change_cost": change_cost_report(config), "limits_live": limits_live_figures(config)}


def local_reusable_files():
    """{repo: {file}} of the workflows that only other workflows call (the sentinel scans), {} while there is no sentinel. Never raises."""
    try:
        sentinel = SENTINEL["obj"]
        return sentinel.surface.local_reusables() if sentinel is not None and not LITE["on"] else {}
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
        return {}


def change_cost_report(config):
    """The cost of the CI by kind of change and the carbon estimate (finops.by_change, finops.co2: off by default), from the runs of the last 24 hours the monitor already holds."""
    from github_actions_monitor.data_pipeline import change_cost, quota
    if not change_cost.settings(config)["by_change"] and not change_cost.settings(config)["co2"]:
        return {"enabled": False}
    with LOCK:
        data = STATE.get("data") or {}
    every, done, private = cost_inputs(data)
    rate = ((quota.load().get("rates_usd_per_minute") or {}).get("linux")) or None
    report = change_cost.build(config, done, private, local_reusable_files(), rate)
    if report.get("enabled"):
        total = data.get("runs_total")
        report["partial"] = bool(isinstance(total, int) and total > len(every))      # the cycle read more runs than these: the figures are a minimum
        report["runs_read"] = len(every)
    return report


def limits_live_figures(config):
    """What the running monitor holds against its ceilings, for /metrics (data_pipeline/limits.py)."""
    from github_actions_monitor.data_pipeline import backpressure
    from github_actions_monitor.integrations import job_metrics
    from github_actions_monitor.security import webhook
    snap = backpressure.snapshot()
    return {"live_events": len(LIVE_EVENTS), "live_events_keep": webhook.live_settings(config)["live_events_keep"], "sse_clients": webhook.SSE_STREAMS[0], "sse_max": webhook.sse_settings(config)["max_clients"],
            "read_queue_depth": snap["depth"], "read_queue_wanted": snap["last_wanted"] if snap["last_wanted"] else None,
            "histogram_series": len(job_metrics.COLLECTOR.queue.series), "histogram_max": job_metrics.settings(config)["histogram_max_series"]}


def runner_wait_figures(config):
    """The wait in the queue by kind of runner, from the model of the runners (only while runners.model is on): {kind: {"jobs", "oldest_seconds"}}. Never raises."""
    try:
        if LITE["on"] or not runner_model.settings(config)["enabled"]:
            return None
        queue = runner_model_payload().get("queue") or {}
        return {kind: {"jobs": row.get("jobs", 0), "oldest_seconds": row.get("oldest_wait_seconds", 0)} for kind, row in queue.items() if isinstance(row, dict)}
    except Exception as error:   # noqa: BLE001
        degraded.note("metrics.runners", error)
        return None


def ai_store():
    """The cache and counters of the AI: the ones of the running sentinel, or (lite, or before it starts) the file itself."""
    from github_actions_monitor.sentinels import sentinel_ai
    sentinel = SENTINEL["obj"]
    if sentinel is not None and getattr(sentinel, "ai_store", None) is not None:
        return sentinel.ai_store
    if "store" not in AI_FALLBACK_STORE:
        AI_FALLBACK_STORE["store"] = sentinel_ai.Store(sentinel_ai.CACHE_FILE)
    return AI_FALLBACK_STORE["store"]


AI_FALLBACK_STORE = {}


def assistant_reader():
    """What the tools of the assistant read: the health of every repository and the score of the account, both from what the monitor already holds (no call to GitHub). Read only."""
    def score():
        from github_actions_monitor.scoring import api as score_api
        from github_actions_monitor.storage import runtime
        storage, account = runtime.process_storage(CHILD["account"] or None)
        return score_api.latest(storage, account, toolconfig.raw_config())
    def history():
        from github_actions_monitor.integrations import ai_alerts, similar_alerts
        return similar_alerts.from_feed(ai_alerts.alerts(toolconfig.raw_config(), states=("resolved",))[:200])
    return {"views": health_views, "score": score, "history": history}


def assistant_ask(request, role="admin"):
    """The answer of POST /api/assistant/ask: one fixed action ({action, repo?, alert?}) answered by the AI of the monitor with the shared budget, cache and chain; the text of the request is never kept."""
    from github_actions_monitor.integrations import assistant
    from github_actions_monitor.sentinels import sentinel_ai
    cfg = sentinel_ai.ai_config(toolconfig.raw_config())
    store = ai_store()
    out = assistant.ask(request.get("action"), {"repo": request.get("repo"), "alert": request.get("alert")}, cfg, assistant_reader(), lambda text: sentinel_ai.explain("assistant", text, cfg, store), role)
    out["used_today"], out["daily_limit"] = store.used_today(), cfg["daily_limit"]
    return out


def _tell_cloud_fallback(first, used):
    """The chain of the AI went from a model on this computer to one on the internet: the notice goes to the channels (the line in the log of actions is written by the chain itself)."""
    from github_actions_monitor.integrations import notifiers
    notifiers.notify(LIVE_CONFIG or toolconfig.raw_config(), {"kind": "ai_alert", "owner": "main", "repo": "", "level": "warn", "url": None, "text": i18n.t("evt.ai_cloud_fallback", frm=first, to=used)})


def _register_cloud_hook():
    from github_actions_monitor.sentinels import ai_chain
    if _tell_cloud_fallback not in ai_chain.CLOUD_HOOKS:
        ai_chain.CLOUD_HOOKS.append(_tell_cloud_fallback)


_register_cloud_hook()


def handle_action_post(path, request):
    """The endpoints that DO something on request of the page: confirm an action of the AI, unlock the actions, test the AI connection, send a test notification."""
    config = toolconfig.raw_config()
    if path in AI_MODEL_POST:
        from github_actions_monitor.sentinels import ai_models, sentinel_ai
        return ai_models.handle_post(path, request, sentinel_ai.ai_config(config), ai_store())
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
        return actlocal.status(whole(since, 0))
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
        return {"alerts": ai_alerts.alerts(config, whole(since, 0))}
    if path == "/api/welcome":
        try:
            done = bool(json.loads(welcome_file().read_text(encoding="utf-8")).get("done"))
        except (OSError, ValueError, AttributeError):
            done = False
        return {"done": done and not DEMO["on"]}
    if path == "/api/runners":
        from github_actions_monitor.integrations import runners
        if DEMO["on"] or not runners.settings(config)["enabled"]:
            return runners.payload(config, None, toolconfig.github_owner(config), DEMO["on"])
        return RUNNERS_SEEN["payload"] or {"enabled": True, "pending": True, "runners": [], "counts": {"idle": 0, "busy": 0, "offline": 0}, "errors": 0}      # what the cycle read: a request never reads GitHub
    if path == "/api/mirror":
        from github_actions_monitor.integrations import mirror
        return mirror.status(config)
    from github_actions_monitor.integrations import otlp
    return otlp.status(config)


def _audit_plain(action, who, target, details=None, result="ok"):
    """The same as audit_action for the places that know the name of the person and not the request."""
    try:
        from github_actions_monitor.security import audit_log
        audit_log.record(toolconfig.raw_config(), action, who or "", "", CHILD["account"] or "", target, result, details)
    except Exception as error:   # noqa: BLE001
        degraded.note("audit_log", error)


def ops_purge_on():
    """True when the purge on demand is switched on (`ops.purge.enabled`) in the complete edition."""
    if LITE["on"]:
        return False
    from github_actions_monitor.ops import opsconf
    return opsconf.settings(toolconfig.raw_config())["purge"]["enabled"]


def handle_updates_post(path, request, who, config):
    """check / plan / apply / rollback of the Updates menu. Nothing is downloaded or applied without the person pressing the button; apply and rollback need `confirm: true`; every answer is a short code."""
    from github_actions_monitor.ops import updates
    if LITE["on"] or CHILD["account"]:
        return {"ok": False, "status": "lite" if LITE["on"] else "account"}
    target = str(request.get("target") or "latest")[:40]
    policy = str(request.get("policy") or "conservative")
    lang = i18n.language()
    edition = "lite" if LITE["on"] else "complete"
    try:
        if path.endswith("/check"):
            notice = updatecheck.settings(config)
            versions = updates.check(notice, LINK.state()["offline"])
            _audit_plain("update_check", who, "releases", {"n": len(versions)}, "ok")
            return {"ok": True, "versions": versions}
        if path.endswith("/plan"):
            return {"ok": True, "plan": updates.plan(target, policy)}
        if path.endswith("/apply"):
            answer = updates.apply(target, policy, request.get("confirm"), edition, lang, lite=LITE["on"], demo=DEMO["on"], helper=updates.helper_on(toolconfig.raw_config()))
            _audit_plain("update_apply", who, target, {"from": answer.get("from")}, "ok")
            return {"ok": True, **answer}
        if path.endswith("/discard"):
            answer = updates.discard(str(request.get("name") or "")[:120], request.get("confirm"), request.get("force"), lite=LITE["on"], demo=DEMO["on"])
            _audit_plain("update_discard", who, answer["discarded"], {"freed": answer["freed"]}, "ok")
            return {"ok": True, **answer}
        if path.endswith("/rollback"):
            answer = updates.rollback(request.get("confirm"), edition, lang, lite=LITE["on"], demo=DEMO["on"], helper=updates.helper_on(toolconfig.raw_config()))
            _audit_plain("update_rollback", who, "previous", None, "ok")
            return {"ok": True, **answer}
    except updates.UpdatesError as error:
        _audit_plain("update_" + path.rsplit("/", 1)[-1], who, target, {"status": error.code}, "error")
        return {"ok": False, "status": error.code}
    except Exception as error:   # noqa: BLE001 - the updater may fail in many ways; the page gets a code, the log gets the line
        degraded.note("updates", error)
        return {"ok": False, "status": "failed"}
    return {"ok": False, "status": "unknown"}


def handle_advanced_post(path, request, who=""):
    """The plan / confirm pairs of the actions on GitHub and of `act`, the token of GitHub and the welcome flag. Answers never contain the request."""
    config = toolconfig.raw_config()
    if path in ("/api/alerts/mute", "/api/alerts/unmute"):      # a local silence (never a change on GitHub): scope alert|code|sentinel, hours optional
        from github_actions_monitor.sentinels import alert_center
        scope, value = str(request.get("scope") or ""), str(request.get("value") or "")
        if path.endswith("unmute"):
            done = alert_center.unmute(scope, value)
            _audit_plain("alert_unmute", who, f"{scope}:{value}"[:120], None, "ok" if done else "error")
            return {"ok": done}
        until_change = None
        if request.get("until_change") is True and scope == "alert":      # "until the item changes": remember the updated_at the alert carries now
            for alert in alert_center.collect(SENTINEL["registry"]):
                if alert.get("id") == value:
                    until_change = (alert.get("details") or {}).get("updated") if isinstance(alert.get("details"), dict) else None
                    break
        entry = alert_center.mute(scope, value, request.get("hours"), config, who=who, until_change=until_change)
        _audit_plain("alert_mute", who, f"{scope}:{value}"[:120], {"hours": request.get("hours")}, "ok" if entry is not None else "error")
        return {"ok": entry is not None, "mute": entry}
    if path.startswith("/api/updates/"):      # the Updates menu (admin, from this computer, with the one-use token); Complete only
        return handle_updates_post(path, request, who, config)
    if path == "/api/webhook/redeliver":      # ask GitHub now to send again the deliveries that never arrived (admin, from this computer); it WRITES to GitHub, so it only touches the hooks you named
        answer = webhook_redeliver_now(config)
        _audit_plain("webhook_redeliver", who, "", {"asked": answer["asked"]}, "ok")
        return {"ok": True, **answer}
    if path == "/api/credential/probe":      # does the login (and the GitHub App) work: a few small reads, nothing written; at most one real check every 10 seconds (a GET never starts gh, so this is a POST)
        from github_actions_monitor.integrations import credential_probe
        return credential_probe.probe(config, lambda args: run_gh(args[1:]), toolconfig.github_owner(config))
    if path == "/api/ops/backup":      # make a copy now (admin, from this computer); Complete only. The answer says whether it worked, never a path of the person or a secret
        if LITE["on"]:
            return {"ok": False, "status": "lite"}
        from github_actions_monitor.ops import schedule
        state = schedule.run_locked(config)
        return {"ok": state["ok"] is True, "status": state["error"] or "ok", "file": state["file"], "bytes": state["bytes"], "sealed": state["sealed"], "accounts": state["accounts"], "events": state["events"]}
    if path == "/api/ops/purge":      # the retention purge now (admin, from this computer, switched on, after a good copy); a dry run unless the request says "dry_run": false
        from github_actions_monitor.ops import purge
        from github_actions_monitor.ops.bundle import OpsError
        from github_actions_monitor.storage import runtime
        storage, account = runtime.process_storage(CHILD["account"] or None)
        try:
            done = purge.run(config, storage, account, dry_run=request.get("dry_run") is not False)
        except OpsError as error:
            return {"ok": False, "status": error.code}
        from github_actions_monitor.security import audit_log
        audit_log.note(account + (":dry" if done["dry_run"] else ":purge"), {"removed": (done.get("line") or {}).get("events_removed", 0)})
        return {"ok": True, **done}
    if path == "/api/report-files/run":      # write a report now (admin, from this computer); Complete only
        if LITE["on"]:
            return {"ok": False, "status": "lite"}
        from github_actions_monitor.reporting import report_service
        snapshot, alerts, team = report_gather()
        done = report_service.run(config, report_account(), snapshot, alerts, team)
        return {"ok": True, "files": done["files"], "at": done["at"]}
    if path == "/api/report-files/summary":      # the summary of the next report: the drafts, the text a person approved, or its removal (admin, from this computer); Complete only
        if LITE["on"]:
            return {"ok": False, "status": "lite"}
        return report_summary_post(config, request)
    if path == "/api/ai/prompts/clear":      # the local record of prompts is emptied (admin)
        from github_actions_monitor.integrations import ai_prompt_log
        return {"ok": True, "removed": ai_prompt_log.clear()}
    if path == "/api/ai/ack":
        from github_actions_monitor.integrations import ai_alerts
        return {"ok": ai_alerts.ack(config, request.get("id"))}
    if path == "/api/ai/failures":      # lines of a book of the same schema from elsewhere: needs lessons.allow_write and an administrator, like a lesson
        from github_actions_monitor.integrations import lessons
        if not lessons.settings(config)["allow_write"]:
            return {"ok": False, "status": "write_off"}
        text = str(request.get("lines") or "")
        return {"ok": True, "added": lessons.import_book(config, text[:2000])}
    if path == "/api/ai/lessons":      # a lesson for the library: needs lessons.allow_write, an administrator and the confirmation (lessons.register); without it the answer is the draft
        from github_actions_monitor.integrations import lessons
        return lessons.register(config, request.get("lesson"), request.get("confirm") is True, admin=True)
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
            from github_actions_monitor.security import audit_log
            audit_log.note("delete")
            ok = store.delete()
            secretstore.clear_environment()
            return {"ok": ok, **advanced_state(config)["token"]}
        if not cfg["enabled"]:
            return {"ok": False, "status": "off"}
        from github_actions_monitor.security import audit_log
        audit_log.note("save")
        done, why = store.save(request.get("token"))
        if done:
            secretstore.apply_to_environment(config, store)
        return {"ok": done, "status": "saved" if done else why, **advanced_state(config)["token"]}
    if path.startswith("/api/gh-action"):
        from github_actions_monitor.integrations import ghactions
        if path.endswith("plan"):
            item, why = ghactions.plan(config, toolconfig.github_owner(config), request.get("action"), request.get("repo"), request.get("number"), reason=request.get("reason"),
                                       operator=request.get("operator") or who, run_gh=run_gh_checked)
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

        ctx = {"gh": gh, "run_gh": run_gh, "repos_fn": repos_fn, "runs_fn": lambda: RUN_CACHE, "sample_fn": lambda: SAMPLE_INFO, "data_fn": lambda: STATE["data"], "eco_fn": ecosystem_of, "account_id": CHILD["account"]}
        from github_actions_monitor.app import workspace
        if not workspace.has_workspace():   # optional: without the local clones the sentinel runs in reduced mode (GitHub API data only)
            print(i18n.t("mon.reduced_mode"))
        SENTINEL["registry"] = sentinel_registry.SentinelRegistry.build(ctx, config)       # the sentinels by name (1.7.1); today only "ci"
        SENTINEL["obj"] = SENTINEL["registry"].get("ci")                                   # the CI sentinel answers everything the monitor always asked of it
        from github_actions_monitor.integrations import notifiers
        SENTINEL["obj"].feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
        from github_actions_monitor.integrations import siem      # OFF: events towards a SIEM, only for the sinks that are enabled (siem.sinks)
        for _name in ("ci", "collab", "security", "supply", "delivery"):
            _sentinel = SENTINEL["registry"].get(_name)
            if _sentinel is not None:
                _sentinel.feed.listeners.append(siem.make_listener(toolconfig.raw_config))
        collab = SENTINEL["registry"].get("collab")
        if collab is not None:
            collab.feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
        security = SENTINEL["registry"].get("security")
        if security is not None:
            security.feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
        supply = SENTINEL["registry"].get("supply")
        if supply is not None:
            supply.feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
        delivery = SENTINEL["registry"].get("delivery")
        if delivery is not None:
            delivery.feed.listeners.append(notifiers.make_listener(toolconfig.raw_config))
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
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--lang")
    parser.add_argument("--lite", action="store_true")
    args, _rest = parser.parse_known_args()
    LITE["on"] = True       # the demo shows the page without the sentinel: its invented data are the runs, the figures and the history
    platform_compat.console_utf8()
    server, url = demo_mode.start(sys.modules[__name__], ports.resolve("complete", flag=args.port))
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
        envguard.hold(listen["token_env"])      # read once: the programs this process starts later do not inherit it
        if len(access_token) < 16:
            access_token, generated = localguard.make_token(), True      # a fresh token at each start, shown once in this console and nowhere else
        tls = localguard.tls_settings(config)
        if tls["cert"] or tls["key"]:      # HTTPS served directly with YOUR certificate
            tls_ctx = localguard.tls_context(tls["cert"], tls["key"])
        localguard.configure(True, listen["host"], access_token, listen["allowed_hosts"], secure=tls_ctx is not None or tls["secure_cookie"], proxy_host=listen["proxy_public_host"], trusted_proxy=listen["trusted_proxy"],
                           behind_proxy=tls["secure_cookie"], trusted_proxies=listen["trusted_proxies"])
    return listen, tls_ctx, access_token, generated


def secret_from_environment(name):
    """The value of the environment variable `name`, else the first line of the file named by `name + "_FILE"` (the way a container hands over a secret), else ''. The value is never printed."""
    value = envguard.get(name).strip()
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
    port = ports.from_argv(argv, "complete")
    config = toolconfig.raw_config()
    from github_actions_monitor.security import webhook as _webhook
    envguard.hold(_webhook.secret_env_name(config), *accounts_supervisor.webhook_names())      # the secrets of the webhook of the installation (the main one and the one of each account): held here, given to each account process explicitly, one to each
    from github_actions_monitor.chatops import inbound as _chat
    envguard.hold(*_chat.env_names(config))      # the proofs of the chat: no program the monitor starts inherits them
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


def network_needs_administrator(config):
    """True when the network mode is asked together with the team mode and there is no administrator yet: the first one can only be created from this computer, so the monitor does not open the
    network before that (it would answer 403 to everybody else anyway). The local mode never asks. A storage that cannot be read is not a reason to refuse."""
    from github_actions_monitor.security import auth
    try:
        if not localguard.settings_from(config)["network"] or not auth.settings(config)["enabled"]:
            return False
        return not auth.users_exist(auth.get_storage(config))
    except Exception as error:   # noqa: BLE001
        degraded.note("loop.extra", error)
        return False


INFO_FLAGS = ("-h", "--help", "--version", "--about", "--doctor", "--help-topics", "--help-search")      # they answer and leave: a monitor that is already on the port (the one of the person) must not stop them


def only_informs():
    return any(flag in sys.argv[1:] for flag in INFO_FLAGS)


def main():
    envguard.hold()      # the supervisor key and the access token leave the environment before ANY program is started (the first `gh` runs long before the network is set up), in every process: monitor, supervisor and account
    if "--demo" in sys.argv[1:]:
        return demo_main()
    if not CHILD["account"]:
        rootmigrate.auto()      # an installation of 1.8.1 or older: its data, logs and AI files move into config/, data/, logs/ and ai/ (undo: python -m github_actions_monitor.util.rootmigrate --undo)
    paths.ensure()      # config/, data/, logs/ and ai/ exist before anything is written
    from github_actions_monitor.integrations import notifiers as _notifiers
    _notifiers.sweep_at_start()      # the folders with the addresses of the services that an earlier run left behind go now, not at the first send
    if not CHILD["account"]:
        from github_actions_monitor.integrations import ai_index
        ai_index.write("lite" if lite_requested() else "complete")      # ai/INDEX.json and ai/README.md: the map for the AI tools that read this installation
    code = accounts_cli(sys.argv[1:]) if not lite_requested() else None
    if code is not None:
        return code
    if not CHILD["account"] and not only_informs() and not lite_requested() and network_needs_administrator(toolconfig.raw_config()):      # H1: no network before the first administrator exists
        print(i18n.t("mon.network_needs_admin_service" if os.environ.get("MONITOR_SERVICE") == "1" else "mon.network_needs_admin"))      # the service cannot turn the network off (its environment sets it): it says the exact command
        return 1
    if not CHILD["account"] and not only_informs() and "--account" not in sys.argv[1:]:      # a second monitor on a port that a monitor already listens on would share it: say so and stop (an account process is started by its supervisor on a port of its own)
        wanted = ports.from_argv(sys.argv, "lite" if lite_requested() else "complete")
        if exclusive.monitor_on(wanted):
            print(i18n.t("mon.already_running", port=wanted))
            return 1
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
    envguard.hold(localguard.settings_from(config)["token_env"])      # the access token may be under another name: it leaves the environment here too
    from github_actions_monitor.security import webhook as _webhook
    _webhook.load_memory(paths.folder("data") / "webhook_deliveries.json") if _webhook.guard_settings(config)["persist_deliveries"] else None      # the memory of deliveries survives a restart
    _webhook.freeze_secret_name(config)      # the shared secret of the webhook is read from the environment once, under the name this process started with, and no program the monitor starts inherits it
    redeliver.RECOVERY.load(paths.folder("data") / "webhook_redelivered.json")      # what was already asked for again is not asked again after a restart
    redeliver.RECOVERY.next_run = time.time() + 60      # the first look a minute after the start
    outside_start(config)      # the cheap outside reads (events of the account, state of GitHub, heartbeat): each one only when switched on
    webhook_worker_start(config)      # the events of the receiver are applied by a thread of their own (a bounded queue, see webhook_receive)
    from github_actions_monitor.chatops import inbound as _chat
    envguard.hold(*_chat.env_names(config))      # the proofs of the chat (the signing secret of Slack, the public key of Discord) leave the environment here too
    if LITE["on"]:
        config["mode"] = "full"                      # the lite edition reads as deep as the complete one: its figures must be the same
        config["sentinel"] = {"enabled": False}      # the lite product has no sentinel, whatever the file says
        config["webhook"] = {"enabled": False}
        config["chatops"] = {"enabled": False}
    i18n.set_language(i18n.detect(config.get("language")))
    i18n.cli_language() if "--lang" in " ".join(sys.argv) else None
    from github_actions_monitor.security import secretstore
    secretstore.apply_to_environment(config)       # the optional token kept by the monitor (off by default) goes to GH_TOKEN of this process; nothing is printed
    if not LITE["on"]:
        credential.apply_stored(state_dir())      # a login put in place with the administrator endpoint, or the file named by GH_TOKEN_FILE: first match of credential.stored()
    parser = argparse.ArgumentParser(description=i18n.t("mon.description"), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=None, help=i18n.t("mon.help_port"))      # none = the port of the edition: ports.complete / ports.lite of the configuration file
    parser.add_argument("--lite", action="store_true", help=i18n.t("mon.help_lite"))
    parser.add_argument("--profile", choices=qaprofile.PROFILES, default=None, help=i18n.t("mon.help_profile"))
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
    if args.profile:
        os.environ[qaprofile.ENV] = args.profile      # the rest of the monitor (the port, the writer lock, the command line) reads it from here
    args.port = ports.resolve("lite" if LITE["on"] else "complete", flag=args.port)
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
        try:
            checks = doctor.run(config=config, edition="lite" if LITE["on"] else "complete")
        except Exception:   # noqa: BLE001 - the doctor itself could not run: its own exit code, not a traceback
            print(i18n.t("doctor.broken"))
            return doctor.EXIT_DOCTOR_ERROR
        strict = False if LITE["on"] else doctor.strict_from(config)
        if args.json:
            print(json.dumps(doctor.as_json(checks, "lite" if LITE["on"] else "full", strict), ensure_ascii=False, indent=1))
        else:
            print(doctor.text(checks, i18n.t, "lite" if LITE["on"] else "full"), end="")
        return doctor.exit_code(checks, strict)
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
    if not report_config_problems(config):
        return 1
    global AUTOSAVE
    LIVE_CONFIG.update(config)
    if not LITE["on"] and not CHILD["account"]:      # an account process bound its storage when it was redirected; the lite edition has no database
        from github_actions_monitor.storage import runtime as storage_runtime
        storage_runtime.bind(config)
    etag_cfg = ((config.get("cache") or {}).get("etag") or {}) if isinstance(config.get("cache"), dict) else {}
    cache_cfg = config.get("cache") if isinstance(config.get("cache"), dict) else {}
    negative = cache_cfg.get("negative_ttl_s", 300)
    qa_cache = qaprofile.etag_file() if qaprofile.active() else None      # the profile qa keeps its ETags in a temporary file that is deleted at the end
    if qa_cache is not None:
        import atexit
        atexit.register(qaprofile.forget, qa_cache)
        print(i18n.t("mon.profile_qa", port=args.port), flush=True)
    ETAG["cache"] = etagcache.EtagCache(**({"path": qa_cache} if qa_cache is not None else {}), ttl_hours=etag_cfg.get("ttl_hours", 24) if isinstance(etag_cfg.get("ttl_hours"), int) else 24, enabled=etag_cfg.get("enabled", True) is True and (config.get("network") or {}).get("etag", True) is not False,      # network.etag is the switch of the Quota tab; cache.etag.enabled stays as it was
                                        negative_ttl=negative if isinstance(negative, int) and not isinstance(negative, bool) else 300, skip_stateful=etag_cfg.get("skip_stateful", True) is not False,
                                        revalidate_active=etag_cfg.get("revalidate_active", True) is not False, identity=credential_fingerprint)
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
    degraded.set_writer(degraded_line)
    if not LITE["on"]:
        try:      # the page shows the last picture with its age while the first cycle reads GitHub
            resumed = lastpicture.load(state_dir(), config)
            if resumed is not None:
                with LOCK:
                    if STATE["data"] is None:
                        STATE["data"] = resumed
        except Exception as error:   # noqa: BLE001
            degraded.note("loop.last_picture", error)
    start_loop(config)
    if started_blind:
        announce_credential("credential_blind", config)
    if not LITE["on"] and hasattr(signal, "SIGHUP") and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, reload_on_signal)      # kill -HUP: read the credential files again, no restart (where the system has the signal)
    threading.Thread(target=watchdog_loop, args=(config,), daemon=True, name="refresh-watchdog").start()
    threading.Thread(target=update_loop, daemon=True).start()
    selfwatch.start(config, note=degraded.note)      # the memory and the threads of this process, noted before the system ends it
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
    wsforward_start(config, server.server_address[1])      # `gh webhook forward` hands the deliveries to the receiver of this very process (webhook.transport = websocket)
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
    if config.get("chatops", {}).get("enabled") is True:
        from github_actions_monitor.chatops import inbound as chat
        print(i18n.t("mon.chatops", status=chat.status_text(config)))
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
