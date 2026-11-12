# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The settings menu of the web panel: which values of actions_monitor.json can be changed from the page, how they are checked and how they are written.

Safety rules (every one of them is tested):

  * Only the keys of SCHEMA can be read or written from the page. Anything else in the file (tokens, secrets, commands, keys of other tools) is neither shown
    nor touched: a write changes the listed keys and keeps every other key exactly as it was. The webhook secret, the signature keys, the command the
    sentinel can run and the AI settings with credentials are NOT in the schema, so the page can neither show nor change them. The only thing the page learns
    about the webhook secret is whether it is defined and long enough (a read-only "state").
  * Every value is checked against its type and range before anything is written; one invalid value refuses the whole request and nothing is written.
  * The file is written atomically (temporary file + replace) after a copy of the previous one goes to config_backups/ (the last BACKUPS copies are kept).
  * A path must be text without control characters, never a network (UNC) path and never on the D: drive.
  * Each setting says whether it needs a restart of the monitor (the loop reads the configuration once) or applies at once.

Layout: every setting belongs to exactly ONE tab (GROUPS, the order of the page: from the common to the advanced) and to one block of that tab (a titled box; its first
field is the main switch when it is a bool, and the rest of the block dims while it is off). Labels and help lines are texts of locales/*.json: label_keys(key)
and help_key(key) say which ones.

The web server only answers these requests to the page of the same machine (the same Host/Origin checks as every other endpoint).
"""
import contextlib
import json
import os
import re
import shutil
import threading
import time
from pathlib import Path

import i18n
import surface
import toolconfig
import private_io

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "actions_monitor.json"
BACKUP_DIR = HERE / "config_backups"
BACKUPS = 10
MAX_BODY = 16384

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
LABEL_RE = re.compile(r"^[\w .:/+-]{1,50}$")      # a label of GitHub may hold a colon, a space or a slash ("monitor:ignore", "good first issue")
LABEL_KEYS = ("sentinels.collab.rules.issue_critical_labels", "sentinels.collab.rules.ignore_labels")
TZ_RE = re.compile(r"^(?:local|utc|UTC|[A-Za-z][A-Za-z0-9_+./-]{1,63})$")      # display.timezone: local, utc or an IANA name
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{0,39}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9._:/@-]{0,100}$")
OLLAMA_RE = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}/?$")   # the local service only: nothing leaves this computer
HTTPS_RE = re.compile(r"^(https://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]{4,250})?$")
PROXY_HOST_RE = re.compile(r"^([A-Za-z0-9]([A-Za-z0-9.-]{0,98}[A-Za-z0-9])?)?$")      # the public NAME of an HTTPS proxy: a host name only, no port, path, user or space (empty = none)
ENV_NAME_RE = re.compile(r"^([A-Z_][A-Z0-9_]{0,63})?$")   # the NAME of an environment variable, never the key itself
LOOP_HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])$")                      # a broker or a service ON THIS COMPUTER
LOOP_URL_RE = re.compile(r"^(http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/%-]{0,100})?)?$")
CHAT_RE = re.compile(r"^(-?[0-9]{1,20})?$")
ROOM_RE = re.compile(r"^(![A-Za-z0-9:._-]{3,120})?$")
TOPIC_RE = re.compile(r"^[A-Za-z0-9/_.-]{1,100}$")
PATTERN_RE = re.compile(r"^[A-Za-z0-9._*-]{1,100}:[A-Za-z0-9._*/-]{1,100}:[a-z_*]{1,30}$")      # repository:file:rule, with * for "any"
FILE_PATTERN_RE = re.compile(r"^[A-Za-z0-9._*?-]{1,80}$")   # a file name pattern of the audit folder (no folders)
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9._-][A-Za-z0-9._/-]{0,79}$")
LISTEN_HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})$")   # this computer or a private address: never a public one
OTLP_RE = re.compile(r"^(https://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]{4,250}|http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/%-]{0,100})?)?$")   # HTTPS anywhere, plain HTTP only on this computer
ACT_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}:[A-Za-z0-9._-]{1,80}\.ya?ml:[a-z_]{1,30}$")      # repository:workflow-file:event, no wildcard
IDENT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,60}$")
SOURCE_KEYS = {"ecosystem": NAME_RE, "kind": re.compile(r"^(pin_table|lock_files)$"), "provider": NAME_RE, "file": FILE_NAME_RE, "key": IDENT_RE,
               "lock_name": FILE_NAME_RE, "version_key": IDENT_RE}
_FOREIGN = re.compile(r"^(?:[Dd]:|/mnt/[dD](?:/|$)|/[dD](?:/|$))")

ROWS = []     # (tab, block, key, type, bounds / enum, restart)
META = {}     # key -> {"tab", "block", "secure", "unit", "label", "help"}
_UNIT_BY_SUFFIX = (("_seconds", "s"), ("_minutes", "min"), ("_hours", "h"), ("_days", "d"), ("max_mb", "MB"))


def _unit(key):
    for suffix, unit in _UNIT_BY_SUFFIX:
        if key.endswith(suffix):
            return unit
    return ""


def _f(tab, block, key, kind, bounds=None, restart=True, secure=False, unit=None, label=None, help=None):
    ROWS.append((tab, block, key, kind, bounds, restart))
    META[key] = {"tab": tab, "block": block, "secure": secure, "unit": _unit(key) if unit is None else unit, "label": label, "help": help}


_T_GENERAL, _T_POLL, _T_SENT, _T_SURF, _T_READY, _T_PATHS, _T_OUT, _T_AI, _T_HOOK = "general", "polling", "sentinel", "surface", "readiness", "paths", "outputs", "ai", "webhook"
_G_GENERAL, _G_POLL, _G_SENT, _G_SURF, _G_READY, _G_PATHS, _G_OUT, _G_AI = _T_GENERAL, _T_POLL, _T_SENT, _T_SURF, _T_READY, _T_PATHS, _T_OUT, _T_AI

# --- Basic: what a new user may want to change first
_f("basic", "start", "open_browser", "bool")
_f("basic", "updates", "updates.check", "bool", restart=False)
_f("basic", "network", "airgapped", "bool", restart=False, secure=True)
_f("basic", "plan", "account.plan", "enum", ("unknown", "free", "pro", "team", "enterprise"), restart=False)
_f("basic", "plan", "quota.default_runner", "enum", ("linux", "windows", "macos"), restart=False)
_f("basic", "plan", "quota.warn_percent", "int", (1, 100), unit="%", restart=False)
_f("basic", "plan", "quota.alert_percent", "int", (1, 100), unit="%", restart=False)
_f("basic", "plan", "quota.billing_api", "bool", restart=False, secure=True)
_f("basic", "safety", "session_guard", "bool", restart=False, secure=True)
_f("basic", "discovery", "discovery.events", "bool", restart=False)
_f("basic", "discovery", "discovery.suggest_groups", "bool", restart=False)
_f("basic", "discovery", "discovery.auto_frequency", "bool", restart=False)
_f("basic", "lifecycle", "discovery.hide", "names")
# --- General
_f(_T_GENERAL, "identity", "github_owner", "text", OWNER_RE)
_f(_T_GENERAL, "identity", "language", "enum", ("",) + tuple(i18n.LANGS), False)
_f(_T_GENERAL, "identity", "display.timezone", "text", TZ_RE, False)
_f(_T_GENERAL, "scope", "mode", "enum", ("full", "lite"))
_f(_T_GENERAL, "scope", "repos", "repos")
_f(_T_GENERAL, "scope", "ecosystems", "eco")
_f(_T_GENERAL, "scope", "show_unclassified", "bool")
_f(_T_GENERAL, "scope", "exclude", "names")
_f(_T_GENERAL, "history", "report_history_days", "int", (1, 365))
# --- Refresh and limits
_f(_T_POLL, "hot", "refresh_seconds", "int", (10, 3600))
_f(_T_POLL, "hot", "hot_hours", "int", (1, 48))
_f(_T_POLL, "hot", "runs_per_repo", "int", (5, 100))
_f(_T_POLL, "hot", "stuck_minutes", "int", (10, 1440))
_f(_T_POLL, "cold", "cold_refresh_seconds", "int", (60, 86400))
_f(_T_POLL, "cold", "cold_runs_per_repo", "int", (1, 100))
_f(_T_POLL, "background", "issues_refresh_seconds", "int", (30, 86400))
_f(_T_POLL, "background", "discover_refresh_seconds", "int", (300, 86400))
_f(_T_POLL, "background", "discover_limit", "int", (10, 5000), unit="")
_f(_T_POLL, "background", "max_workers", "int", (1, 32))
_f(_T_POLL, "quota", "min_rate_remaining", "int", (100, 5000), unit="calls")
# --- Sentinel
_f(_T_SENT, "main", "sentinel.enabled", "bool")
_f(_T_SENT, "main", "sentinel.refresh_seconds", "int", (60, 86400))
_f(_T_SENT, "main", "sentinel.hot_hours", "int", (1, 48))
_f(_T_SENT, "alerts", "sentinel.alerts_hot_seconds", "int", (60, 86400))
_f(_T_SENT, "alerts", "sentinel.alerts_cold_seconds", "int", (60, 86400))
_f(_T_SENT, "alerts", "sentinel.hygiene_seconds", "int", (300, 604800))
_f(_T_SENT, "budget", "sentinel.max_calls_per_tick", "int", (10, 500), unit="calls")
_f(_T_SENT, "budget", "sentinel.budget_per_hour", "int", (50, 5000), unit="calls")
_f(_T_SENT, "budget", "sentinel.workers", "int", (1, 32))
_f(_T_SENT, "budget", "sentinel.min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_SENT, "releases", "sentinel.candidate_days", "int", (0, 60))
_f(_T_SENT, "releases", "sentinel.candidate_min_entries", "int", (1, 100))
_f(_T_SENT, "releases", "sentinel.skip_candidate_prefixes", "names")
_f(_T_SENT, "releases", "sentinel.pending_sign_hours", "int", (1, 720))
_f(_T_SENT, "releases", "sentinel.require_verified_signature", "bool", secure=True)
_f(_T_SENT, "resolve", "sentinel.a2_full_sample_unknown", "bool")
_f(_T_SENT, "resolve", "sentinel.a2_resolve_max_calls_per_tick", "int", (0, 50), unit="calls")
_f(_T_SENT, "resolve", "sentinel.a2_resolve_ttl_seconds", "int", (60, 86400))
_f(_T_SENT, "prs", "sentinel.stale_pr_days", "int", (1, 90))
_f(_T_SENT, "hygiene_files", "sentinel.required_files", "filegroups")
_f(_T_SENT, "minutes", "sentinel.minutes_budget_period", "enum", ("7d", "24h"))
_f(_T_SENT, "minutes", "sentinel.minutes_budget", "intmap", (0, 1000000), unit="min")
_f(_T_SENT, "audits", "sentinel.audit_files.reconciliation", "text", FILE_PATTERN_RE)
_f(_T_SENT, "audits", "sentinel.audit_files.rounds", "text", FILE_PATTERN_RE)
_f(_T_SENT, "audits", "sentinel.audit_files.rounds_extra", "text", FILE_PATTERN_RE)
# the Collab sentinel (1.7.3): issues and pull requests that need a person; off by default, read only
_f(_T_SENT, "collab", "sentinels.collab.enabled", "bool")
_f(_T_SENT, "collab", "sentinels.collab.refresh_seconds", "int", (60, 86400))
_f(_T_SENT, "collab", "sentinels.collab.max_repos_per_tick", "int", (1, 100), unit="calls")
_f(_T_SENT, "collab", "sentinels.collab.min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_SENT, "collab", "sentinels.collab.repos", "repos")
_f(_T_SENT, "collab", "sentinels.collab.rules.issue_stale_days", "int", (1, 365))
_f(_T_SENT, "collab", "sentinels.collab.rules.issue_critical_labels", "names")
_f(_T_SENT, "collab", "sentinels.collab.rules.pr_review_pending_days", "int", (1, 90))
_f(_T_SENT, "collab", "sentinels.collab.rules.pr_draft_max_days", "int", (1, 365))
_f(_T_SENT, "collab", "sentinels.collab.rules.pr_conflict_days", "int", (1, 90))
_f(_T_SENT, "collab", "sentinels.collab.rules.watch_external_comments", "bool")
_f(_T_SENT, "collab", "sentinels.collab.rules.ignore_labels", "names")
_f(_T_SENT, "collab", "alerts.mute_hours", "int", (1, 720), restart=False, unit="h")
# --- Actions and releases surface (A10)
_f(_T_SURF, "main", "sentinel.surface.enabled", "bool")
_f(_T_SURF, "main", "sentinel.surface.refresh_seconds", "int", (600, 604800))
_f(_T_SURF, "main", "sentinel.surface.local_seconds", "int", (60, 86400))
_f(_T_SURF, "main", "sentinel.surface.max_repos_per_tick", "int", (1, 50))
_f(_T_SURF, "main", "sentinel.surface.min_rate_factor", "float", (1.0, 10.0), unit="x")
_f(_T_SURF, "main", "sentinel.surface.budget_share", "float", (0.1, 1.0), unit="x")
CHECK_PARAMS = {"dead_schedule": (("days", (1, 365)),), "stuck_concurrency": (("minutes", (5, 1440)),), "matrix_os": (("max_per_tick", (1, 20)),),
                "artifacts": (("max_mb", (1, 100000)), ("retention_days", (1, 400))), "release_assets": (("recent_days", (1, 365)),), "drafts": (("days", (1, 365)),),
                "security_aged": (("days", (1, 365)),), "pr_human": (("days", (1, 365)),), "attestation": (("max_per_tick", (1, 20)),)}
for _check in surface.DEFAULTS["checks"]:
    _f(_T_SURF, "chk_" + _check, f"sentinel.surface.checks.{_check}.enabled", "bool", label=["cfg.p.check_on"], help="cfg.h.check_on")
    for _param, _bounds in CHECK_PARAMS.get(_check, ()):
        _f(_T_SURF, "chk_" + _check, f"sentinel.surface.checks.{_check}.{_param}", "int", _bounds, label=["cfg.p." + _param], help="cfg.h.p." + _param)
# --- Release readiness (A11)
_f(_T_READY, "main", "sentinel.readiness.enabled", "bool")
_f(_T_READY, "main", "sentinel.readiness.min_coverage", "float", (0.0, 1.0), unit="x")
_f(_T_READY, "main", "sentinel.readiness.warn_below", "int", (0, 100), unit="pts")
for _w in ("red", "stuck", "secret", "high_alert", "alert", "stale_pr", "unsigned", "hygiene"):
    _f(_T_READY, "weights", f"sentinel.readiness.health.weights.{_w}", "int", (0, 1000), unit="pts", label=["cfg.w." + _w], help="cfg.h.weight")
_f(_T_READY, "pins", "sentinel.readiness.pins.refresh_seconds", "int", (60, 86400))
_f(_T_READY, "pins", "sentinel.readiness.pins.max_depth", "int", (1, 12))
_f(_T_READY, "pins", "sentinel.readiness.pins.sources", "sources")
# --- Folders and files
_f(_T_PATHS, "workspace", "workspace_root", "path")
_f(_T_PATHS, "workspace", "signed_dir", "path")
_f(_T_PATHS, "workspace", "audit_dir", "path")
_f(_T_PATHS, "workspace", "tools_dir", "path")
_f(_T_PATHS, "data", "ecosystems_file", "path")
_f(_T_PATHS, "data", "targets_file", "path")
_f(_T_PATHS, "data", "profiles_file", "path")
_f(_T_PATHS, "ci_red", "sentinel.ci_red_file", "path")
_f(_T_PATHS, "ci_red", "sentinel.ci_red_audit_copy", "bool")
# --- Outputs and exports
_f(_T_OUT, "prometheus", "outputs.prometheus.enabled", "bool", restart=False, secure=True)
_f(_T_OUT, "prometheus", "outputs.prometheus.per_repo", "bool", restart=False)
_f(_T_OUT, "json", "outputs.json.enabled", "bool", restart=False, secure=True)
_f(_T_OUT, "dashboard", "outputs.dashboard.enabled", "bool", restart=False, secure=True)
# --- Integrations: external AI, incoming webhook
_f(_T_AI, "provider", "ai.provider", "enum", ("none", "ollama", "openai-compatible", "anthropic", "copilot"), secure=True)
_f(_T_AI, "provider", "ai.model", "text", MODEL_RE)
_f(_T_AI, "provider", "ai.ollama_url", "text", OLLAMA_RE)
_f(_T_AI, "provider", "ai.base_url", "text", HTTPS_RE, secure=True)
_f(_T_AI, "provider", "ai.api_key_env", "text", ENV_NAME_RE)
_f(_T_AI, "provider", "ai.daily_limit", "int", (0, 500), unit="calls")
_f(_T_AI, "limits", "ai.max_input_chars", "int", (500, 20000), unit="chars")
_f(_T_AI, "limits", "ai.max_output_chars", "int", (200, 8000), unit="chars")
_f(_T_AI, "limits", "ai.timeout_seconds", "int", (5, 300))
_f(_T_AI, "scope", "ai.events", "names")
_f(_T_AI, "scope", "ai.allowed_repos", "names")
_f(_T_AI, "scope", "ai.answer_language", "enum", ("",) + tuple(i18n.LANGS), False)
_f(_T_AI, "actions", "ai.actions.enabled", "bool", secure=True)
_f(_T_AI, "actions", "ai.actions.execute", "bool", secure=True)
_f(_T_AI, "actions", "ai.actions.allowed", "names")
_f(_T_AI, "actions", "ai.actions.max_per_hour", "int", (1, 60), unit="")
_f(_T_AI, "actions", "ai.actions.ttl_seconds", "int", (30, 3600))
_f(_T_HOOK, "inbound", "webhook.enabled", "bool", secure=True)
_f(_T_HOOK, "inbound", "webhook.signing_state", "status", restart=False)
_f(_T_HOOK, "inbound", "webhook.record_events", "bool")
_f(_T_HOOK, "inbound", "webhook.live_events_keep", "int", (10, 1000), unit="")
_f(_T_HOOK, "inbound", "webhook.replay_seconds", "int", (60, 86400))
_f(_T_HOOK, "inbound", "webhook.max_per_minute", "int", (1, 600), unit="")
# --- Reads and cache (conditional reads)
_f("cache", "etag", "cache.etag.enabled", "bool")
_f("cache", "etag", "cache.etag.ttl_hours", "int", (1, 168))
# --- Notifications
_f("notify", "main", "notify.enabled", "bool", secure=True)
_f("notify", "main", "notify.allow_private_targets", "bool", secure=True)
_f("notify", "main", "notify.events", "names")
_f("notify", "main", "notify.max_per_hour", "int", (1, 600), unit="")
_f("notify", "ch_telegram", "notify.channels.telegram.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_telegram", "notify.channels.telegram.token_env", "text", ENV_NAME_RE, label=["cfg.p.token_env"], help="cfg.h.p.token_env")
_f("notify", "ch_telegram", "notify.channels.telegram.chat_id", "text", CHAT_RE, label=["cfg.p.chat_id"], help="cfg.h.p.chat_id")
_f("notify", "ch_discord", "notify.channels.discord.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_discord", "notify.channels.discord.url_env", "text", ENV_NAME_RE, label=["cfg.p.url_env"], help="cfg.h.p.url_env")
_f("notify", "ch_slack", "notify.channels.slack.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_slack", "notify.channels.slack.url_env", "text", ENV_NAME_RE, label=["cfg.p.url_env"], help="cfg.h.p.url_env")
_f("notify", "ch_matrix", "notify.channels.matrix.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_matrix", "notify.channels.matrix.homeserver", "text", HTTPS_RE, label=["cfg.p.homeserver"], help="cfg.h.p.homeserver")
_f("notify", "ch_matrix", "notify.channels.matrix.room", "text", ROOM_RE, label=["cfg.p.room"], help="cfg.h.p.room")
_f("notify", "ch_matrix", "notify.channels.matrix.token_env", "text", ENV_NAME_RE, label=["cfg.p.token_env"], help="cfg.h.p.token_env")
_f("notify", "ch_mqtt", "notify.channels.mqtt.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_mqtt", "notify.channels.mqtt.host", "text", LOOP_HOST_RE, label=["cfg.p.local_host"], help="cfg.h.p.local_host")
_f("notify", "ch_mqtt", "notify.channels.mqtt.port", "int", (1, 65535), unit="", label=["cfg.p.port"], help="cfg.h.p.port")
_f("notify", "ch_mqtt", "notify.channels.mqtt.topic", "text", TOPIC_RE, label=["cfg.p.topic"], help="cfg.h.p.topic")
_f("notify", "ch_http_local", "notify.channels.http_local.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_http_local", "notify.channels.http_local.url", "text", LOOP_URL_RE, label=["cfg.p.local_url"], help="cfg.h.p.local_url")
# --- Analytics
_f("analytics", "main", "analytics.enabled", "bool")
_f("analytics", "main", "analytics.keep_days", "int", (1, 365))
_f("analytics", "sampling", "analytics.min_samples", "int", (1, 100), unit="")
_f("analytics", "sampling", "analytics.max_samples", "int", (20, 1000), unit="")
_f("analytics", "sampling", "analytics.jobs_per_cycle", "int", (0, 20), unit="calls")
_f("analytics", "sampling", "analytics.steps", "bool")
_f("analytics", "signals", "analytics.slow_factor", "float", (1.1, 10.0), unit="x")
_f("analytics", "signals", "analytics.flaky", "bool")
# --- Workflow linter
_f("lint", "main", "lint.enabled", "bool")
_f("lint", "main", "lint.refresh_seconds", "int", (60, 86400))
_f("lint", "main", "lint.in_report", "bool")
_f("lint", "main", "lint.ignore", "patterns")
for _rule in ("unpinned_uses", "permissions", "secrets_in_clear", "injection", "pr_target"):
    _f("lint", "rule_" + _rule, f"lint.rules.{_rule}.enabled", "bool", label=["cfg.p.rule_on"], help="cfg.h.rule_on")
    _f("lint", "rule_" + _rule, f"lint.rules.{_rule}.severity", "enum", ("info", "warn", "bad"), label=["cfg.p.severity"], help="cfg.h.p.severity")
# --- Terminal view
_f("console", "tui", "tui.theme", "enum", ("dark", "light"), False)
_f("console", "tui", "tui.refresh_seconds", "int", (2, 300), False)
# --- Advanced: opt-in features, every one OFF by default (network, own token, actions on GitHub, act, mirror, runners, OTLP, organisations, FinOps)
_f("advanced", "network", "listen.network", "bool", secure=True)
_f("advanced", "network", "listen.host", "text", LISTEN_HOST_RE, secure=True)
_f("advanced", "network", "listen.token_env", "text", ENV_NAME_RE, secure=True)
_f("advanced", "network", "listen.allowed_hosts", "names", secure=True)
_f("advanced", "network", "listen.tls_cert_file", "path", secure=True)
_f("advanced", "network", "listen.tls_key_file", "path", secure=True)
_f("advanced", "network", "listen.secure_cookie", "bool", secure=True)
_f("advanced", "network", "listen.proxy_public_host", "text", PROXY_HOST_RE, secure=True)
_f("advanced", "network", "listen.max_failed_attempts", "int", (3, 100), unit="", secure=True)
_f("advanced", "network", "listen.query_access", "bool", secure=True)
_f("advanced", "token", "github_token.enabled", "bool", restart=False, secure=True)
_f("advanced", "token", "github_token.store", "enum", ("auto", "system", "file"), restart=False, secure=True)
_f("advanced", "ghactions", "github_actions.enabled", "bool", restart=False, secure=True)
_f("advanced", "ghactions", "github_actions.allowed", "names", restart=False, secure=True)
_f("advanced", "ghactions", "github_actions.merge_method", "enum", ("squash", "merge", "rebase"), restart=False, secure=True)
_f("advanced", "act", "act.enabled", "bool", restart=False, secure=True)
_f("advanced", "act", "act.allowed", "acts", restart=False, secure=True)
_f("advanced", "act", "act.timeout_seconds", "int", (30, 7200), restart=False)
_f("advanced", "act", "act.allow_symlinks", "bool", restart=False, secure=True)
_f("advanced", "dispatch", "dispatch.required_ci", "names", restart=False)
_f("advanced", "mirror", "mirror.enabled", "bool", restart=False, secure=True)
_f("advanced", "mirror", "mirror.folder", "path", restart=False)
_f("advanced", "mirror", "mirror.max_mb", "int", (10, 100000), restart=False)
_f("advanced", "mirror", "mirror.keep_days", "int", (1, 365), restart=False)
_f("advanced", "mirror", "mirror.max_per_cycle", "int", (1, 20), restart=False, unit="")
_f("advanced", "runners", "runners.enabled", "bool", restart=False)
_f("advanced", "runners", "runners.scope", "enum", ("owner", "repos"), restart=False)
_f("advanced", "otlp", "otlp.enabled", "bool", restart=False, secure=True)
_f("advanced", "otlp", "otlp.endpoint", "text", OTLP_RE, restart=False, secure=True)
_f("advanced", "otlp", "otlp.interval_seconds", "int", (15, 3600), restart=False)
_f("advanced", "orgs", "organizations.discover", "bool", restart=False)
_f("advanced", "finops", "finops.jobs_per_cycle", "int", (0, 50), restart=False, unit="calls")
_f(_T_AI, "alerts", "ai_alerts.enabled", "bool", restart=False)
_f(_T_AI, "alerts", "ai_alerts.folder", "path", restart=False)
_f(_T_AI, "alerts", "ai_alerts.brief_max_bytes", "int", (512, 20000), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.hook.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "alerts", "ai_alerts.hook.url", "text", LOOP_URL_RE, restart=False, secure=True)
_f(_T_AI, "alerts", "ai_alerts.hook.max_per_hour", "int", (1, 60), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.diagnose.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "alerts", "ai_alerts.diagnose.max_per_cycle", "int", (1, 10), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.diagnose.log_lines", "int", (3, 40), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.diagnose.max_bytes", "int", (200, 4000), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.cascade.enabled", "bool", restart=False)
_f(_T_AI, "alerts", "ai_alerts.stream.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "alerts", "ai_alerts.stream.max_seconds", "int", (60, 86400), restart=False)
_f(_T_AI, "alerts", "ai_alerts.stream.max_clients", "int", (1, 10), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.heartbeat.enabled", "bool", restart=False)
_f(_T_AI, "alerts", "ai_alerts.heartbeat.window_minutes", "int", (1, 1440), restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.enabled", "bool", restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.block_on_stop", "bool", restart=False, secure=True)
_f(_T_AI, "alerts", "ai_alerts.client_hook.cooldown_minutes", "int", (1, 1440), restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.stale_hours", "int", (1, 168), restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.max_lines", "int", (1, 40), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.client_hook.max_chars", "int", (400, 8000), restart=False, unit="")
# @@MORE_SETTINGS@@

TAB_ORDER = ("basic", "general", "polling", "cache", "sentinel", "surface", "readiness", "paths", "outputs", "ai", "webhook", "notify", "analytics", "lint", "advanced", "console")
ROWS.sort(key=lambda row: TAB_ORDER.index(row[0]))     # stable: inside a tab the order of writing is kept
SCHEMA = [(tab, key, kind, bounds, restart) for tab, _block, key, kind, bounds, restart in ROWS]
FIELDS = {row[1]: row for row in SCHEMA}
GROUPS = tuple(dict.fromkeys(row[0] for row in SCHEMA))
assert set(GROUPS) <= set(TAB_ORDER)
OUTPUT_DEFAULTS = {"prometheus": {"enabled": False, "per_repo": True}, "json": {"enabled": False}, "dashboard": {"enabled": False}}
STATUS_KEYS = {"webhook.signing_state"}      # computed, read-only: never written


def label_keys(key):
    """The locale keys whose texts, joined with a dash, make the label of a setting (one key for most)."""
    custom = META[key]["label"]
    return list(custom) if custom else ["cfg.f." + key]


def help_key(key):
    return META[key]["help"] or "cfg.h." + key


def block_title_key(block):
    """The locale key of the title of a block: the title of the check for the blocks of the A10 checks."""
    if block.startswith("chk_"):
        return "surf.t." + block[4:]
    if block.startswith("rule_"):
        return "lint.rule." + block[5:]
    return "ui.cfg_b_" + block


def layout():
    """[(tab, [(block, [keys])])] in page order."""
    out = {}
    for tab, block, key, *_ in ROWS:
        out.setdefault(tab, {}).setdefault(block, []).append(key)
    return [(tab, list(blocks.items())) for tab, blocks in out.items()]


def _get(tree, dotted, default=None):
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _set(tree, dotted, value):
    node = tree
    parts = dotted.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def check_value(path, value):
    """(ok, clean value or the reason as a stable code). Reasons: unknown, type, range, enum, text, path, names, ecosystems, list, map."""
    row = FIELDS.get(path)
    if row is None or row[2] == "status":
        return False, "unknown"
    kind, bounds = row[2], row[3]
    if kind == "bool":
        return (True, value) if isinstance(value, bool) else (False, "type")
    if kind == "int":
        if not _is_int(value):
            return False, "type"
        return (True, value) if bounds[0] <= value <= bounds[1] else (False, "range")
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, "type"
        return (True, float(value)) if bounds[0] <= value <= bounds[1] else (False, "range")
    if kind == "enum":
        if not isinstance(value, str):
            return False, "type"
        return (True, value) if value in bounds else (False, "enum")
    if kind == "text":
        if not isinstance(value, str):
            return False, "type"
        return (True, value.strip()) if bounds.match(value.strip()) else (False, "text")
    if kind == "path":
        if not isinstance(value, str):
            return False, "type"
        text = value.strip()
        if len(text) > 260 or any(ord(c) < 32 for c in text) or text.startswith(("\\\\", "//")) or _FOREIGN.match(text):
            return False, "path"
        return True, text
    if kind == "names":
        pattern = LABEL_RE if path in LABEL_KEYS else NAME_RE
        if not isinstance(value, list) or len(value) > 200 or not all(isinstance(v, str) and pattern.match(v) for v in value):
            return False, "names"
        return True, list(value)
    if kind == "patterns":
        if not isinstance(value, list) or len(value) > 100 or not all(isinstance(v, str) and PATTERN_RE.match(v) for v in value):
            return False, "names"
        return True, list(value)
    if kind == "acts":
        if not isinstance(value, list) or len(value) > 50 or not all(isinstance(v, str) and ACT_RE.match(v) for v in value):
            return False, "names"
        return True, list(value)
    if kind == "repos":
        if value == "all":
            return True, "all"
        return check_value_list(value)
    if kind == "eco":
        if value == "all":
            return True, "all"
        known = set(toolconfig.ecosystem_names())
        if isinstance(value, list) and len(value) <= 50 and all(isinstance(v, str) and (v in known or not known) and NAME_RE.match(v) for v in value):
            return True, list(value)
        return False, "ecosystems"
    if kind == "intmap":
        if not isinstance(value, dict) or len(value) > 50:
            return False, "map"
        for name, number in value.items():
            if not isinstance(name, str) or not NAME_RE.match(name) or not _is_int(number) or not bounds[0] <= number <= bounds[1]:
                return False, "map"
        return True, dict(value)
    if kind == "filegroups":
        if not isinstance(value, list) or not value or len(value) > 40:
            return False, "list"
        for group in value:
            if not isinstance(group, list) or not group or len(group) > 8 or not all(isinstance(n, str) and FILE_NAME_RE.match(n) and ".." not in n for n in group):
                return False, "list"
        return True, [list(g) for g in value]
    if kind == "sources":
        if not isinstance(value, list) or len(value) > 20:
            return False, "list"
        for item in value:
            if not isinstance(item, dict) or set(item) - set(SOURCE_KEYS) or not {"ecosystem", "kind", "provider"} <= set(item):
                return False, "list"
            if not all(isinstance(v, str) and SOURCE_KEYS[k].match(v) and ".." not in v for k, v in item.items()):
                return False, "list"
        return True, [dict(i) for i in value]
    return False, "unknown"


def check_value_list(value):
    if not isinstance(value, list) or len(value) > 400 or not all(isinstance(v, str) and NAME_RE.match(v) for v in value):
        return False, "names"
    return True, list(value)


LITE_KEYS = ("github_owner", "language", "repos", "ecosystems", "exclude", "refresh_seconds", "open_browser", "updates.check", "airgapped")      # the short settings page of the lite product


def validate(changes, lite=False):
    """({path: clean value}, {path: reason}) for a request {path: value}. A non-dict or an empty request is an error. With lite only LITE_KEYS can be changed."""
    if not isinstance(changes, dict) or not changes or len(changes) > len(SCHEMA):
        return {}, {"_": "request"}
    clean, errors = {}, {}
    for path, value in changes.items():
        if lite and path not in LITE_KEYS:
            errors[str(path)[:80]] = "unknown"
            continue
        ok, result = check_value(path, value) if isinstance(path, str) else (False, "unknown")
        if ok:
            clean[path] = result
        else:
            errors[str(path)[:80]] = result
    return clean, errors


def _read_file(path):
    """The dict in the file; None when it is missing, FileNotFoundError aside; ValueError when it is not a JSON object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value


def webhook_state(config):
    """"defined" | "short" | "undefined": the only thing the page may know about the webhook secret (never the secret, nor its length)."""
    secret = ((config or {}).get("webhook") or {}).get("secret") if isinstance((config or {}).get("webhook"), dict) else ""
    if not isinstance(secret, str) or not secret:
        return "undefined"
    return "defined" if len(secret) >= 32 else "short"


def describe(path=CONFIG_FILE, lite=False):
    """What the page shows: {"groups": [{"id", "blocks": [{"id", "title_key", "fields": [...]}], "fields": [...]}], "backups": N}. A field: {"key", "type", "value", "default", "min",
    "max", "enum", "restart", "unit", "secure", "label", "help", "block", "master"}. Values come from the file over the template; nothing outside SCHEMA is ever included."""
    template = {}
    try:
        template = _read_file(HERE / "actions_monitor.example.json")
    except (OSError, ValueError):
        pass
    try:
        current = _read_file(path)
    except (OSError, ValueError):
        current = {}
    groups = []
    for tab, blocks in layout():
        group_fields, group_blocks = [], []
        for block, keys in blocks:
            fields = []
            keys = [k for k in keys if not lite or k in LITE_KEYS]
            for index, key in enumerate(keys):
                _tab, _kind_key, _kind, bounds, restart = FIELDS[key][0], key, FIELDS[key][2], FIELDS[key][3], FIELDS[key][4]
                kind = _kind
                default = _get(template, key)
                if default is None and key.startswith("outputs."):
                    default = _get(OUTPUT_DEFAULTS, key[len("outputs."):], False)
                if default is None and key == "repos":
                    default = "all"
                value = _get(current, key, default)
                if key == "repos" and value is None:
                    value = "all"
                if kind == "status":
                    value = webhook_state(current)
                item = {"key": key, "type": kind, "value": value if value is not None else ("" if kind in ("text", "path", "enum") else None), "default": default, "restart": restart,
                        "unit": META[key]["unit"], "secure": META[key]["secure"], "label": label_keys(key), "help": help_key(key), "block": block,
                        "master": index == 0 and kind == "bool" and len(keys) > 1}
                if kind in ("int", "float"):
                    item["min"], item["max"] = bounds
                if kind == "intmap":
                    item["min"], item["max"] = bounds
                if kind == "enum":
                    item["enum"] = list(bounds)
                if kind in ("eco", "intmap"):
                    item["choices"] = toolconfig.ecosystem_names()
                fields.append(item)
            group_fields += fields
            if fields:
                group_blocks.append({"id": block, "title_key": block_title_key(block), "fields": fields})
        if group_blocks:
            groups.append({"id": tab, "blocks": group_blocks, "fields": group_fields})
    try:
        backups = len(list(BACKUP_DIR.glob("actions_monitor-*.json")))
    except OSError:
        backups = 0
    return {"groups": groups, "backups": backups}


def _backup(path):
    """Copies the file to config_backups/ (keeps the newest BACKUPS). Returns the copy or None when there was nothing to copy."""
    if not Path(path).is_file():
        return None
    BACKUP_DIR.mkdir(exist_ok=True)
    name = BACKUP_DIR / ("actions_monitor-" + time.strftime("%Y%m%d-%H%M%S") + ".json")
    n = 1
    while name.exists():
        n += 1
        name = BACKUP_DIR / ("actions_monitor-" + time.strftime("%Y%m%d-%H%M%S") + f"-{n}.json")
    shutil.copy2(path, name)
    old = sorted(BACKUP_DIR.glob("actions_monitor-*.json"))
    for extra in old[:-BACKUPS]:
        try:
            extra.unlink()
        except OSError:
            pass
    return name


_WRITE_LOCK = threading.RLock()


@contextlib.contextmanager
def file_lock(path, timeout=10.0):
    """Exclusive lock around read -> change -> write of the configuration: a lock of this process (two requests of the page at once) AND, best effort, a lock file next to it
    (another process that saves at the same time). Without it the second save would start from the file as it was before the first and undo it."""
    with _WRITE_LOCK:
        handle = None
        try:
            handle = open(str(path) + ".lock", "a+b")
            end = time.time() + timeout
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.time() > end:
                        break          # the lock of another process is stuck: the lock of this process still protects the page
                    time.sleep(0.05)
        except OSError:
            handle = None
        try:
            yield
        finally:
            if handle is not None:
                try:
                    if os.name == "nt":
                        import msvcrt
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                handle.close()


def apply(changes, path=CONFIG_FILE, lite=False):
    """Checks and writes. {"ok": True, "changed": [paths], "restart": [paths that need a restart], "backup": bool} or {"ok": False, "errors": {path: reason}}.
    Nothing is written when any value is invalid or when nothing changes."""
    clean, errors = validate(changes, lite)
    if errors:
        return {"ok": False, "errors": errors}
    path = Path(path)
    with file_lock(path):
        return _apply_locked(clean, path)


def _apply_locked(clean, path):
    try:
        current = _read_file(path) if path.is_file() else {}
    except (OSError, ValueError):
        return {"ok": False, "errors": {"_": "unreadable"}}     # a broken file is never overwritten from the page
    changed = [key for key, value in clean.items() if _get(current, key, "\0missing") != value]
    if not changed:
        return {"ok": True, "changed": [], "restart": [], "backup": False}
    for key in changed:
        _set(current, key, clean[key])
    backup = _backup(path)
    tmp = path.with_name(path.name + ".tmp")
    private_io.write_tmp(tmp, json.dumps(current, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)
    toolconfig.forget()
    if "language" in changed:
        i18n.set_language(None)      # detect again with the new value
    return {"ok": True, "changed": changed, "restart": [k for k in changed if FIELDS[k][4]], "backup": backup is not None}


def output_enabled(config, name, sub="enabled"):
    """True when outputs.<name>.<sub> is on in the configuration (off when missing)."""
    return _get(config or {}, f"outputs.{name}.{sub}", OUTPUT_DEFAULTS.get(name, {}).get(sub, False)) is True
