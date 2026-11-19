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

from github_actions_monitor import i18n
from github_actions_monitor.data_pipeline import alertflow
from github_actions_monitor.app import screens, surface
from github_actions_monitor.app import toolconfig
from github_actions_monitor.security import envguard
from github_actions_monitor.security import private_io
from github_actions_monitor.ui import ordering
from github_actions_monitor.util import ports

from github_actions_monitor.util import paths
from github_actions_monitor.util.paths import ROOT as HERE   # the product folder: the data of the person who runs the monitor stays there
CONFIG_FILE = paths.config_file()
BACKUP_DIR = CONFIG_FILE.parent / "config_backups"
BACKUPS = 10
MAX_BODY = 16384

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
NET_RE = re.compile(r"^[0-9A-Fa-f:.]{2,45}(?:/[0-9]{1,3})?\Z")      # an address or a block of addresses (listen.trusted_proxies)
LABEL_RE = re.compile(r"^[\w .:/+-]{1,50}\Z")      # a label of GitHub may hold a colon, a space or a slash ("monitor:ignore", "good first issue")
PAIR_KEYS = ("ci.stuck.workflow_minutes", "ci.stuck.runner_minutes")
LABEL_KEYS = ("sentinels.collab.rules.issue_critical_labels", "sentinels.collab.rules.ignore_labels")
PATH_RE = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9._/-]{1,120}\Z")      # sentinels.delivery.changelog_paths / version_files: a path inside the repository (no leading slash, no ..)
PATH_KEYS = ("sentinels.delivery.changelog_paths", "sentinels.delivery.version_files")
GLOB_RE = re.compile(r"^[A-Za-z0-9._*? -]{1,100}\Z")      # a name or a pattern of names (a ruleset may be called "Protect main" or "main-*")
HYGIENE_SKIP = ("ruleset", "label", "file", "sha", "allowed", "schedule")
TZ_RE = re.compile(r"^(?:local|utc|UTC|[A-Za-z][A-Za-z0-9_+./-]{1,63})\Z")      # display.timezone: local, utc or an IANA name
CRON_RE = re.compile(r"^[0-9*/,\- ]{9,60}\Z")      # report_schedule.cron: five fields of numbers, lists, ranges and steps (reporting/report_schedule.py reads it)
PAIR_RE = re.compile(r"^[A-Za-z0-9._*/-]{1,100}=[0-9]{1,5}\Z")      # ci.stuck.workflow_minutes / ci.stuck.runner_minutes: "pattern=minutes"
BRANCH_RE = re.compile(r"^[A-Za-z0-9._*/-]{1,100}\Z")      # a branch name or a pattern of branch names (ci.extra_branches)
from github_actions_monitor.health import fleet as _fleet      # noqa: E402 - the two shapes of the lists of the fleet view are defined next to the code that reads them
FLEET_LABEL_RE, FLEET_FILTER_RE = _fleet.LABEL_RE, _fleet.FILTER_RE
RUNNER_LABEL_RE = re.compile(r"^[A-Za-z0-9._*?=/-]{1,60}\Z")      # a label of runs-on, or the start / pattern of one (runners.model.*_labels)
RUNNER_LABEL_KEYS = ("runners.model.thirdparty_labels", "runners.model.large_labels", "runners.model.self_labels")
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{0,39}\Z")
MODEL_RE = re.compile(r"^[A-Za-z0-9._:/@-]{0,100}\Z")
AI_REF_RE = re.compile(r"^[A-Za-z0-9-]{0,40}\Z")      # a preset (openai, ollama...) or a protocol (anthropic, openai-compatible...) for a task
AI_FALLBACK_RE = re.compile(r"^[A-Za-z0-9._:/@+=, -]{0,400}\Z")      # provider=model, provider=model
OLLAMA_RE = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}/?\Z")   # the local service only: nothing leaves this computer
HTTPS_RE = re.compile(r"^(https://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]{4,250})?\Z")
AI_URL_RE = re.compile(r"^(https://[A-Za-z0-9._~:/?#!$&()*+,;=%-]{4,250}|http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/-]{0,100})?)?\Z")   # https, or a server on this computer
PROXY_HOST_RE = re.compile(r"^([A-Za-z0-9]([A-Za-z0-9.-]{0,98}[A-Za-z0-9])?)?\Z")      # the public NAME of an HTTPS proxy: a host name only, no port, path, user or space (empty = none)
WORKDAY_RE = re.compile(r"^[1-7]\Z")      # compare.workdays: one day of the week, Monday = 1
ENV_NAME_RE = re.compile(r"^([A-Z_][A-Z0-9_]{0,63})?\Z")
AI_ENV_RE = re.compile(r"^(?!(?:GH_TOKEN|GITHUB_TOKEN|GITHUB_PAT|PATH|HOME|USERPROFILE|SYSTEMROOT|TEMP|TMP|APPDATA|LOCALAPPDATA|PYTHONPATH|MONITOR_[A-Z0-9_]*)\Z)([A-Z_][A-Z0-9_]{0,63})?\Z")   # the NAME of the variable of the key of a provider: never a variable of the system or of the monitor   # the NAME of an environment variable, never the key itself


def _env_name_except(own):
    """The pattern of the NAME of a variable that holds a secret of the monitor: never the system, the login to GitHub or a secret of the monitor that belongs to another setting (`own` = this one's)."""
    barred = [name for name in envguard.SYSTEM_NAMES + envguard.SECRET_NAMES if name != own]
    return re.compile(r"^(?!(?:" + "|".join(re.escape(name) for name in barred) + r")\Z)([A-Z_][A-Z0-9_]{0,63})?\Z")


WEBHOOK_ENV_RE = _env_name_except(envguard.WEBHOOK_SECRET_ENV)      # webhook.secret_env
TOKEN_ENV_RE = _env_name_except(envguard.ACCESS_TOKEN_ENV)          # listen.token_env
SLACK_ENV_RE = _env_name_except(envguard.SLACK_SIGNING_ENV)          # chatops.slack.signing_secret_env
DISCORD_ENV_RE = _env_name_except(envguard.DISCORD_KEY_ENV)         # chatops.discord.public_key_env
NOTIFY_ENV_RE = _env_name_except("")                                # the variable of a channel of notices: no secret of the monitor belongs to it
LOOP_HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])\Z")                      # a broker or a service ON THIS COMPUTER
LOOP_URL_RE = re.compile(r"^(http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/%-]{0,100})?)?\Z")
CHAT_RE = re.compile(r"^(-?[0-9]{1,20})?\Z")
ROOM_RE = re.compile(r"^(![A-Za-z0-9:._-]{3,120})?\Z")
TOPIC_RE = re.compile(r"^[A-Za-z0-9/_.-]{1,100}\Z")
NTFY_SERVER_RE = re.compile(r"^(https://[A-Za-z0-9._~:/-]{4,200}|http://(127\.0\.0\.1|localhost)(:[0-9]{1,5})?)\Z")      # a ntfy server: https, or one on this computer
SENDER_RE = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,200}\Z")
PATTERN_RE = re.compile(r"^[A-Za-z0-9._*-]{1,100}:[A-Za-z0-9._*/-]{1,100}:[a-z_*]{1,30}\Z")      # repository:file:rule, with * for "any"
FILE_PATTERN_RE = re.compile(r"^[A-Za-z0-9._*?-]{1,80}\Z")   # a file name pattern of the audit folder (no folders)
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9._-][A-Za-z0-9._/-]{0,79}\Z")
LISTEN_HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})\Z")   # this computer or a private address: never a public one
OTLP_RE = re.compile(r"^(https://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]{4,250}|http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/%-]{0,100})?)?\Z")   # HTTPS anywhere, plain HTTP only on this computer
ACT_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}:[A-Za-z0-9._-]{1,80}\.ya?ml:[a-z_]{1,30}\Z")      # repository:workflow-file:event, no wildcard
IDENT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,60}\Z")
SOURCE_KEYS = {"ecosystem": NAME_RE, "kind": re.compile(r"^(pin_table|lock_files)\Z"), "provider": NAME_RE, "file": FILE_NAME_RE, "key": IDENT_RE,
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
_f("basic", "start", "config_check.strict", "bool")
_f("basic", "start", "startup.resume_max_age_hours", "int", (0, 168))
_f("basic", "updates", "updates.check", "bool", restart=False)
_f("basic", "updates", "updates.systemd_helper", "bool", restart=False)
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
_f("basic", "lifecycle", "discovery.skip_archived", "bool")
_f("basic", "lifecycle", "discovery.fork_policy", "enum", ("show", "skip", "skip_unless_ci", "auto"))
_f("basic", "lifecycle", "discovery.fork_ci_days", "int", (0, 365), unit="d")
_f("basic", "lifecycle", "discovery.fork_checks_per_pass", "int", (1, 500), unit="calls")
_f("basic", "lifecycle", "discovery.min_keep_pct", "int", (0, 100), unit="%")
# --- General
_f(_T_GENERAL, "identity", "github_owner", "text", OWNER_RE)
_f(_T_GENERAL, "identity", "language", "enum", ("",) + tuple(i18n.LANGS), False)
_f(_T_GENERAL, "identity", "display.timezone", "text", TZ_RE, False)
_f(_T_GENERAL, "identity", "display.blink_red_tiles", "bool", restart=False)
_f(_T_GENERAL, "screens", "ui.orientation", "enum", ("auto", "portrait", "landscape"), restart=False)
_f(_T_GENERAL, "screens", "ui.rotate_seconds", "int", (0, 3600), unit="s", restart=False)
_f(_T_GENERAL, "screens", "ui.screen1_tabs", "text", re.compile(r"^[a-z,]{0,60}\Z"), restart=False)
_f(_T_GENERAL, "screens", "ui.screen1_orientation", "enum", ("auto", "portrait", "landscape"), restart=False)
_f(_T_GENERAL, "screens", "ui.screen2_tabs", "text", re.compile(r"^[a-z,]{0,60}\Z"), restart=False)
_f(_T_GENERAL, "screens", "ui.screen2_orientation", "enum", ("auto", "portrait", "landscape"), restart=False)
_f(_T_GENERAL, "screens", "ui.screen3_tabs", "text", re.compile(r"^[a-z,]{0,60}\Z"), restart=False)
_f(_T_GENERAL, "screens", "ui.screen3_orientation", "enum", ("auto", "portrait", "landscape"), restart=False)
_f(_T_GENERAL, "wall", "screens.enabled", "bool", restart=False)
_f(_T_GENERAL, "look", "ui.theme", "enum", screens.GLOBAL_THEMES, restart=False)
_f(_T_GENERAL, "wall", "screens.default_theme", "enum", screens.THEME_CHOICES, restart=False)
_f(_T_GENERAL, "wall", "screens.theme_overview", "enum", screens.THEME_CHOICES, restart=False)
_f(_T_GENERAL, "wall", "screens.theme_now", "enum", screens.THEME_CHOICES, restart=False)
_f(_T_GENERAL, "wall", "screens.theme_sentinels", "enum", screens.THEME_CHOICES, restart=False)
_f(_T_GENERAL, "wall", "screens.mode", "enum", screens.MODES, restart=False)
_f(_T_GENERAL, "wall", "screens.rotate_every_seconds", "int", (5, 300), unit="s", restart=False)
_f(_T_GENERAL, "wall", "screens.alert_hold_seconds", "int", (5, 600), unit="s", restart=False)
_f(_T_GENERAL, "wall", "screens.default_density", "enum", ("compact", "normal", "large"), restart=False)
_f(_T_GENERAL, "wall", "screens.refresh_seconds", "int", (5, 120), unit="s", restart=False)
_f(_T_GENERAL, "wall", "screens.rotate_seconds", "int", (0, 3600), unit="s", restart=False)
_f(_T_GENERAL, "wall", "screens.blink", "bool", restart=False)
_f(_T_GENERAL, "wall", "screens.blink_calm_minutes", "int", (0, 1440), unit="min", restart=False)
_f(_T_GENERAL, "wall", "screens.sound", "bool", restart=False)
_f(_T_GENERAL, "wall", "screens.burn_in_protection", "bool", restart=False)
_f(_T_GENERAL, "wall", "screens.night_dim", "bool", restart=False)
_f(_T_GENERAL, "wall", "screens.night_dim_from_hour", "int", (0, 23), unit="h", restart=False)
_f(_T_GENERAL, "wall", "screens.night_dim_to_hour", "int", (0, 23), unit="h", restart=False)
_f(_T_GENERAL, "wall", "screens.show_repo_names", "enum", ("all", "public", "none"), secure=True, restart=False)
_f(_T_GENERAL, "wall", "screens.group_map", "bool", restart=False)
_f(_T_GENERAL, "wall", "screens.menu", "bool", restart=False)
_f(_T_GENERAL, "wall", "screens.menu_target", "enum", ("new", "same"), restart=False)
_f(_T_GENERAL, "wall", "screens.menu_max_windows", "int", (1, 9), restart=False)
_f(_T_GENERAL, "wall", "screens.menu_rotate_seconds", "int", (5, 300), unit="s", restart=False)
_f(_T_GENERAL, "wall", "screens.menu_tv_scale", "float", (0.5, 3.0), unit="x", restart=False)
_f(_T_GENERAL, "logo", "screens.logo_overview", "bool", restart=False)
_f(_T_GENERAL, "logo", "screens.logo_now", "bool", restart=False)
_f(_T_GENERAL, "logo", "screens.logo_sentinels", "bool", restart=False)
_f(_T_GENERAL, "logo", "screens.logo_corner", "enum", screens.CORNERS, restart=False)
_f(_T_GENERAL, "logo", "screens.logo_max_width", "int", (16, 640), unit="px", restart=False)
_f(_T_GENERAL, "logo", "screens.logo_max_height", "int", (16, 320), unit="px", restart=False)
_f(_T_GENERAL, "order", "ui.now_sort", "enum", ordering.KINDS["now"], restart=False)
_f(_T_GENERAL, "order", "ui.alerts_sort", "enum", ordering.KINDS["alerts"], restart=False)
_f(_T_GENERAL, "ports", "ports.complete", "int", (ports.LOW, ports.HIGH), restart=True)
_f(_T_GENERAL, "ports", "ports.lite", "int", (ports.LOW, ports.HIGH), restart=True)
_f(_T_GENERAL, "sound", "sound.enabled", "bool", restart=False)
_f(_T_GENERAL, "fleet", "fleet.page_size", "int", (10, 500), unit="", restart=False)
_f(_T_GENERAL, "fleet", "fleet.group_by", "enum", ("ecosystem", "label", "state", "none"), restart=False)
_f(_T_GENERAL, "fleet", "fleet.sort", "enum", ("risk", "name", "last_run", "state"), restart=False)
_f(_T_GENERAL, "fleet", "fleet.labels", "names", restart=False)
_f(_T_GENERAL, "fleet", "fleet.saved_filters", "names", restart=False)
_f("quota", "modes", "modes.auto_low", "bool", restart=False)
_f("quota", "modes", "modes.auto_low_enter", "int", (50, 4000), restart=False, unit="calls")
_f("quota", "modes", "modes.auto_low_exit", "int", (100, 5000), restart=False, unit="calls")
_f("quota", "modes", "modes.low.refresh_seconds", "int", (10, 3600), restart=False, unit="s")
_f("quota", "modes", "modes.low.cold_refresh_seconds", "int", (30, 86400), restart=False, unit="s")
_f("quota", "modes", "modes.low.runs_per_repo", "int", (5, 100), restart=False)
_f("quota", "modes", "modes.low.hot_hours", "int", (1, 48), restart=False, unit="h")
_f("quota", "saving", "network.etag", "bool", restart=True)
_f("quota", "saving", "network.graphql_checks", "bool", restart=False)
_f("quota", "saving", "network.graphql_batch", "int", (1, 30), restart=False)
_f("quota", "extra_reader", "extra_reader.enabled", "bool", restart=False, secure=True)
_f("quota", "extra_reader", "extra_reader.file", "path", restart=False, secure=True)
_f("quota", "extra_reader", "extra_reader.any_folder", "bool", restart=False, secure=True)
_f("quota", "github_app", "github_app.enabled", "bool", restart=False, secure=True)
_f("quota", "github_app", "github_app.share_reads", "bool", restart=False, secure=True)
_f(_T_SENT, "reports", "reports.workflow_hygiene.enabled", "bool", restart=False, secure=True)
_f(_T_SENT, "reports", "reports.queue.enabled", "bool", restart=False, secure=True)
_f(_T_SENT, "reports", "reports.release_view.enabled", "bool", restart=False)
_f(_T_SENT, "reports", "reports.supply_chain.enabled", "bool", restart=False, secure=True)
_f(_T_SENT, "reports", "reports.max_calls_per_cycle", "int", (1, 50), restart=False, unit="calls")
_f(_T_AI, "failed_step", "logs.failed_step.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "failed_step", "logs.failed_step.lines", "int", (3, 40), restart=False, unit="")
_f(_T_AI, "failed_step", "logs.failed_step.max_bytes", "int", (200, 4000), restart=False, unit="")
_f(_T_AI, "failed_step", "logs.failed_step.max_per_minute", "int", (1, 60), restart=False, unit="")
_f("quota", "github_app", "github_app.app_id", "text", re.compile(r"^[0-9]{0,12}\Z"), restart=False, secure=True)
_f("quota", "github_app", "github_app.key_path", "path", restart=False, secure=True)
_f("quota", "github_app", "github_app.installation_id", "text", re.compile(r"^[0-9]{0,12}\Z"), restart=False, secure=True)
_f("quota", "github_app", "github_app.openssl_path", "path", restart=False, secure=True)

for _kind in ("runs", "security", "issues", "history", "discovery", "other"):
    _f("quota", "rp_prefer", f"readpool.prefer.{_kind}", "enum", ("auto", "user", "app", "extra"), restart=False, label=["cfg.p.rp_prefer", "cfg.p.rp_kind_" + _kind], help="cfg.h.rp_prefer")
for _source in ("user", "app", "extra"):
    _f("quota", "rp_reserve", f"readpool.reserve.{_source}", "int", (0, 4000), restart=False, unit="", label=["cfg.p.rp_reserve", "cfg.p.rp_src_" + _source], help="cfg.h.rp_reserve")
_f("quota", "failover", "quota.failover", "bool", restart=False)
_f("quota", "failover", "quota.failover_max_age_minutes", "int", (1, 1440), unit="min", restart=False)
_f("quota", "central", "central.source", "enum", ("off", "git", "http"), restart=False, secure=True)
_f("quota", "central", "central.max_age_minutes", "int", (5, 10080), unit="min", restart=False)
_f(_T_GENERAL, "sound", "sound.on_new_red", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_connection_lost", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_warning", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_resolved", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_report", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_lesson", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_sentinel", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_stuck", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_score_drop", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_info", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.on_live_recovered", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.theme", "enum", ("classic", "soft"), restart=False)
_f(_T_GENERAL, "sound", "sound.quiet_enabled", "bool", restart=False)
_f(_T_GENERAL, "sound", "sound.quiet_from_hour", "int", (0, 23), unit="h", restart=False)
_f(_T_GENERAL, "sound", "sound.quiet_to_hour", "int", (0, 23), unit="h", restart=False)
_f(_T_GENERAL, "sound", "sound.cooldown_seconds", "int", (0, 3600), unit="s", restart=False)
_f(_T_GENERAL, "sound", "sound.volume", "int", (1, 100), unit="%", restart=False)
_f(_T_GENERAL, "sound", "sound.server_beep", "bool", restart=False, secure=True)
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
_f(_T_POLL, "background", "watchdog_minutes", "int", (0, 1440), unit="min")
_f(_T_POLL, "background", "watchdog_max_abandoned", "int", (0, 100))
_f(_T_POLL, "cold", "cold_refresh_seconds", "int", (60, 86400))
_f(_T_POLL, "cold", "cold_runs_per_repo", "int", (1, 100))
_f(_T_POLL, "background", "issues_refresh_seconds", "int", (30, 86400))
_f(_T_POLL, "background", "discover_refresh_seconds", "int", (300, 86400))
_f(_T_POLL, "background", "discover_limit", "int", (10, 5000), unit="")
_f(_T_POLL, "background", "max_workers", "int", (1, 32))
_f(_T_POLL, "quota", "min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_POLL, "pagination", "pagination.workflow_pages", "int", (1, 20), unit="", restart=False)
_f(_T_POLL, "pagination", "pagination.job_pages", "int", (1, 20), unit="", restart=False)
_f(_T_POLL, "pagination", "pagination.collab_pages", "int", (1, 20), unit="", restart=False)
_f(_T_POLL, "pagination", "pagination.cursor_pages", "int", (0, 20), unit="", restart=False)
_f(_T_POLL, "sampling", "sampling.default_branch_probe", "bool", restart=False)
_f(_T_POLL, "sampling", "sampling.active_probe", "bool", restart=False)
_f(_T_POLL, "sampling", "sampling.min_coverage_minutes", "int", (0, 10080), unit="min", restart=False)
_f(_T_POLL, "sampling", "sampling.api_budget_per_hour", "int", (0, 100000), unit="calls", restart=False)
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
_f(_T_SENT, "resolve", "sentinel.a2_resolve_batch_min", "int", (0, 50), unit="")
_f(_T_SENT, "resolve", "sentinel.a2_resolve_batch_pages", "int", (1, 10), unit="")
_f(_T_SENT, "origin", "ci.red_events", "names", restart=False)
_f(_T_SENT, "origin", "ci.count_fork_runs", "bool", restart=False)
_f(_T_SENT, "origin", "ci.automation_counts", "bool", restart=False)
_f(_T_SENT, "origin", "ci.inactive_days", "int", (0, 3650), restart=False)
_f(_T_SENT, "origin", "ci.dormant_repos", "bool", restart=False)
_f(_T_SENT, "origin", "ci.red_ages", "bool", restart=False)
_f(_T_SENT, "origin", "ci.red_age_days", "int", (1, 3650), restart=False)
_f(_T_SENT, "origin", "ci.disabled_apart", "bool", restart=False)
_f(_T_SENT, "origin", "ci.dependabot_alerts", "bool", restart=False)
_f(_T_SENT, "origin", "ci.copilot_alerts", "bool", restart=False)
_f(_T_SENT, "origin", "ci.forks_need_own_ci", "bool", restart=False)
_f(_T_SENT, "origin", "ci.fork_own_ci_days", "int", (1, 365), restart=False)
_f(_T_SENT, "origin", "ci.extra_branches", "names", restart=False)
_f(_T_SENT, "causes", "ci.group.reusable", "bool", restart=False)
_f(_T_SENT, "causes", "ci.group.min", "int", (2, 50), restart=False)
_f(_T_SENT, "causes", "ci.failed_jobs.enabled", "bool", restart=False)
_f(_T_SENT, "causes", "ci.failed_jobs.max_per_cycle", "int", (1, 50), restart=False, unit="calls")
_f(_T_SENT, "causes", "ci.failed_jobs.group_by", "enum", ("auto", "platform", "matrix", "prefix"), restart=False)
_f(_T_SENT, "durations", "ci.rerun_timing", "bool", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.learned", "bool", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.percentile", "int", (50, 100), restart=False)
_f(_T_SENT, "stuck", "ci.stuck.margin", "int", (1, 20), restart=False)
_f(_T_SENT, "stuck", "ci.stuck.min_samples", "int", (2, 100), restart=False)
_f(_T_SENT, "stuck", "ci.stuck.min_minutes", "int", (1, 10000), unit="min", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.max_minutes", "int", (1, 100000), unit="min", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.queue_minutes", "int", (0, 100000), unit="min", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.awaiting_stuck", "bool", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.ghost_enabled", "bool", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.ghost_days", "int", (1, 3650), restart=False)
_f(_T_SENT, "stuck", "ci.stuck.workflow_minutes", "names", restart=False)
_f(_T_SENT, "stuck", "ci.stuck.runner_minutes", "names", restart=False)
_f(_T_SENT, "prs", "sentinel.stale_pr_days", "int", (1, 90))
_f(_T_SENT, "prs", "sentinel.dependency_bots", "names")
_f(_T_SENT, "prs", "sentinel.bots_apart", "bool")
_f(_T_SENT, "hygiene_files", "sentinel.required_files", "filegroups")
_f(_T_SENT, "hygiene_rules", "sentinel.hygiene.ruleset_mode", "enum", ("name", "effective", "off"))
_f(_T_SENT, "hygiene_rules", "sentinel.hygiene.ruleset_names", "names")
_f(_T_SENT, "hygiene_rules", "sentinel.hygiene.skip", "names")
_f(_T_SENT, "hygiene_rules", "sentinel.hygiene.community_fallback", "bool")
_f(_T_SENT, "minutes", "sentinel.minutes_budget_period", "enum", ("7d", "24h"))
_f(_T_SENT, "minutes", "sentinel.minutes_budget", "intmap", (0, 1000000), unit="min")
_f(_T_SENT, "trend", "sentinel.trend_green_pct", "int", (1, 100), unit="%")
_f(_T_SENT, "trend", "sentinel.trend_health", "int", (1, 100))
_f(_T_SENT, "trend", "sentinel.trend_quota_pct", "int", (1, 100), unit="%")
_f(_T_SENT, "audits", "sentinel.audit_files.reconciliation", "text", FILE_PATTERN_RE)
_f(_T_SENT, "audits", "sentinel.audit_files.rounds", "text", FILE_PATTERN_RE)
_f(_T_SENT, "audits", "sentinel.audit_files.rounds_extra", "text", FILE_PATTERN_RE)
# the Collab sentinel (1.7.3): issues and pull requests that need a person; off by default, read only
_f(_T_SENT, "collab", "sentinels.collab.enabled", "bool")
_f(_T_SENT, "collab", "sentinels.collab.search_api", "bool", restart=False)
_f(_T_SENT, "collab", "sentinels.collab.refresh_seconds", "int", (60, 86400))
_f(_T_SENT, "collab", "sentinels.collab.max_repos_per_tick", "int", (1, 100), unit="calls")
_f(_T_SENT, "collab", "sentinels.collab.deadline_s", "int", (0, 600), unit="s")
_f(_T_SENT, "collab", "sentinels.collab.min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_SENT, "collab", "sentinels.collab.repos", "repos")
_f(_T_SENT, "collab", "sentinels.collab.rules.issue_stale_days", "int", (1, 365))
_f(_T_SENT, "collab", "sentinels.collab.rules.issue_critical_labels", "names")
_f(_T_SENT, "collab", "sentinels.collab.rules.pr_review_pending_days", "int", (1, 90))
_f(_T_SENT, "collab", "sentinels.collab.rules.pr_draft_max_days", "int", (1, 365))
_f(_T_SENT, "collab", "sentinels.collab.rules.pr_conflict_days", "int", (1, 90))
_f(_T_SENT, "collab", "sentinels.collab.rules.watch_external_comments", "bool")
_f(_T_SENT, "collab", "sentinels.collab.rules.ignore_labels", "names")
# --- Security sentinel (1.9.1; the weights of the penalty it puts on the score, sentinels.security.penalty.*, are read from the file)
_f(_T_SENT, "security", "sentinels.security.enabled", "bool")
_f(_T_SENT, "security", "sentinels.security.refresh_seconds", "int", (300, 86400))
_f(_T_SENT, "security", "sentinels.security.max_repos_per_tick", "int", (1, 100), unit="calls")
_f(_T_SENT, "security", "sentinels.security.deadline_s", "int", (0, 600), unit="s")
_f(_T_SENT, "security", "sentinels.security.min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_SENT, "security", "sentinels.security.repos", "repos")
_f(_T_SENT, "security", "sentinels.security.signals.dependabot.enabled", "bool")
_f(_T_SENT, "security", "sentinels.security.signals.dependabot.min_severity", "enum", ("low", "medium", "high", "critical"))
_f(_T_SENT, "security", "sentinels.security.signals.code_scanning.enabled", "bool")
_f(_T_SENT, "security", "sentinels.security.signals.code_scanning.min_severity", "enum", ("low", "medium", "high", "critical"))
_f(_T_SENT, "security", "sentinels.security.signals.secret.enabled", "bool")
_f(_T_SENT, "security", "sentinels.security.signals.branch.enabled", "bool")
_f(_T_SENT, "security", "sentinels.security.signals.workflow.enabled", "bool")
_f(_T_SENT, "security", "sentinels.security.signals.codeowners.enabled", "bool")
# --- Supply chain sentinel (2.1.1; off by default; read only; the weights of its informative penalty, sentinels.supply.penalty.*, are read from the file)
_f(_T_SENT, "supply", "sentinels.supply.enabled", "bool")
_f(_T_SENT, "supply", "sentinels.supply.refresh_seconds", "int", (600, 86400))
_f(_T_SENT, "supply", "sentinels.supply.max_repos_per_tick", "int", (1, 200), unit="calls")
_f(_T_SENT, "supply", "sentinels.supply.deadline_s", "int", (0, 600), unit="s")
_f(_T_SENT, "supply", "sentinels.supply.max_calls_per_tick", "int", (1, 600), unit="calls")
_f(_T_SENT, "supply", "sentinels.supply.max_files_per_repo", "int", (1, 100))
_f(_T_SENT, "supply", "sentinels.supply.min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_SENT, "supply", "sentinels.supply.repos", "repos")
_f(_T_SENT, "supply", "sentinels.supply.ignore", "patterns")
_f(_T_SENT, "supply", "sentinels.supply.signals.unpinned.enabled", "bool")
_f(_T_SENT, "supply", "sentinels.supply.signals.unpinned.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "supply", "sentinels.supply.signals.mutable_ref.enabled", "bool")
_f(_T_SENT, "supply", "sentinels.supply.signals.mutable_ref.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "supply", "sentinels.supply.signals.permissions_wide.enabled", "bool")
_f(_T_SENT, "supply", "sentinels.supply.signals.permissions_wide.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "supply", "sentinels.supply.signals.permissions_missing.enabled", "bool")
_f(_T_SENT, "supply", "sentinels.supply.signals.permissions_missing.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "supply", "sentinels.supply.signals.pr_target_checkout.enabled", "bool")
_f(_T_SENT, "supply", "sentinels.supply.signals.pr_target_checkout.level", "enum", ("info", "warning", "error", "critical"))
# --- Delivery sentinel (2.1.1; off by default; read only)
_f(_T_SENT, "delivery", "sentinels.delivery.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.refresh_seconds", "int", (600, 86400))
_f(_T_SENT, "delivery", "sentinels.delivery.max_repos_per_tick", "int", (1, 200), unit="calls")
_f(_T_SENT, "delivery", "sentinels.delivery.deadline_s", "int", (0, 600), unit="s")
_f(_T_SENT, "delivery", "sentinels.delivery.max_calls_per_tick", "int", (1, 600), unit="calls")
_f(_T_SENT, "delivery", "sentinels.delivery.min_rate_remaining", "int", (100, 5000), unit="calls")
_f(_T_SENT, "delivery", "sentinels.delivery.repos", "repos")
_f(_T_SENT, "delivery", "sentinels.delivery.unreleased_days", "int", (1, 365), unit="d")
_f(_T_SENT, "delivery", "sentinels.delivery.unreleased_min_entries", "int", (1, 100))
_f(_T_SENT, "delivery", "sentinels.delivery.changelog_paths", "names")
_f(_T_SENT, "delivery", "sentinels.delivery.version_files", "names")
_f(_T_SENT, "delivery", "sentinels.delivery.expected_assets", "names")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.unreleased_pending.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.unreleased_pending.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "delivery", "sentinels.delivery.signals.tag_without_release.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.tag_without_release.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "delivery", "sentinels.delivery.signals.release_without_notes.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.release_without_notes.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "delivery", "sentinels.delivery.signals.version_mismatch.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.version_mismatch.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "delivery", "sentinels.delivery.signals.ecosystem_drift.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.ecosystem_drift.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "delivery", "sentinels.delivery.signals.assets_missing.enabled", "bool")
_f(_T_SENT, "delivery", "sentinels.delivery.signals.assets_missing.level", "enum", ("info", "warning", "error", "critical"))
_f(_T_SENT, "collab", "alerts.mute_hours", "int", (1, 720), restart=False, unit="h")
_f(_T_SENT, "flow_silences", "alerts.silences", "names", restart=False)
_f(_T_SENT, "flow_silences", "alerts.silences_expire_days", "int", (0, 3650), restart=False, unit="d")
_f(_T_SENT, "flow_service", "alerts.service.enabled", "bool", restart=False)
_f(_T_SENT, "flow_service", "alerts.service.failures", "int", (2, 50), restart=False)
_f(_T_SENT, "flow_service", "alerts.service.rate_percent", "int", (0, 100), restart=False, unit="%")
_f(_T_SENT, "flow_service", "alerts.service.workflows", "names", restart=False)
_f(_T_SENT, "flow_group", "alerts.group.by_commit", "bool", restart=False)
_f(_T_SENT, "flow_group", "alerts.group.min", "int", (2, 50), restart=False)
_f(_T_SENT, "flow_digest", "alerts.digest.minutes", "int", (0, 1440), restart=False, unit="min")
_f(_T_SENT, "flow_digest", "alerts.digest.threshold", "int", (3, 500), restart=False)
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
_f(_T_SURF, "chk_release_assets", "sentinel.surface.checks.release_assets.require_sha256", "bool")
_f(_T_SURF, "chk_release_assets", "sentinel.surface.checks.release_assets.require_signature", "bool")
_f(_T_SURF, "chk_release_assets", "sentinel.surface.checks.release_assets.allow_empty", "bool")
_f(_T_SURF, "chk_tag_vs_version", "sentinel.surface.checks.tag_vs_version.prefixes", "names")
_f(_T_SURF, "chk_tag_vs_version", "sentinel.surface.checks.tag_vs_version.prerelease_ok", "bool")
# --- Release readiness (A11)
_f(_T_READY, "main", "sentinel.readiness.enabled", "bool")
_f(_T_READY, "main", "sentinel.readiness.min_coverage", "float", (0.0, 1.0), unit="x")
_f(_T_READY, "main", "sentinel.readiness.warn_below", "int", (0, 100), unit="pts")
for _w in ("red", "stuck", "secret", "high_alert", "alert", "stale_pr", "unsigned", "hygiene"):
    _f(_T_READY, "weights", f"sentinel.readiness.health.weights.{_w}", "int", (0, 1000), unit="pts", label=["cfg.w." + _w], help="cfg.h.weight")
_f(_T_READY, "pins", "sentinel.readiness.pins.refresh_seconds", "int", (60, 86400))
_f(_T_READY, "pins", "sentinel.readiness.pins.max_depth", "int", (1, 12))
_f(_T_READY, "pins", "sentinel.readiness.pins.sources", "sources")
# --- Score of the account (Complete only). The limits of every part (score.limits.*) are read from the file and shown in the guide, not edited here.
_f(_T_SENT, "score", "score.enabled", "bool", restart=False)
_f(_T_SENT, "score", "score.window_days", "int", (1, 90), restart=False)
_f(_T_SENT, "score", "score.calibrating_hours", "int", (0, 720), restart=False)
_f(_T_SENT, "score", "score.min_runs", "int", (1, 100000), restart=False, unit="")
_f(_T_SENT, "score", "score.min_coverage", "float", (0.0, 1.0), restart=False, unit="x")
_f(_T_SENT, "score", "score.trend_flat", "int", (0, 100), restart=False, unit="pts")
_f(_T_SENT, "score", "score.alert.enabled", "bool", restart=False)
_f(_T_SENT, "score", "score.alert.drop_points", "int", (1, 100), restart=False, unit="pts")
_f(_T_SENT, "score", "score.alert.notify_external", "bool", restart=False, secure=True)
for _w in ("reliability", "speed", "recovery", "collaboration", "security"):
    _f(_T_SENT, "score_weights", f"score.weights.{_w}", "int", (0, 1000), restart=False, unit="pts")
for _g in ("A", "B", "C", "D"):
    _f(_T_SENT, "score_grades", f"score.grades.{_g}", "int", (0, 100), restart=False, unit="pts")
# --- Memory and comparison (Complete only): this period against the one before, from the ledger and the snapshots of the score
_f(_T_SENT, "compare", "compare.enabled", "bool", restart=False)
_f(_T_SENT, "compare", "compare.default_window_days", "int", (1, 90), restart=False)
_f(_T_SENT, "compare", "compare.default_days_filter", "enum", ("all", "workdays", "weekend"), restart=False)
_f(_T_SENT, "compare", "compare.workdays", "names", restart=False)
_f(_T_SENT, "compare", "compare.min_runs_per_window", "int", (1, 10000), restart=False, unit="")
_f(_T_SENT, "compare", "compare.min_days_of_history", "int", (1, 3650), restart=False, unit="d")
_f(_T_SENT, "compare", "compare.min_resolved", "int", (1, 1000), restart=False, unit="")
_f(_T_SENT, "compare", "compare.min_snapshots", "int", (1, 10000), restart=False, unit="")
_f(_T_SENT, "compare", "compare.min_repo_runs", "int", (1, 1000), restart=False, unit="")
_f(_T_SENT, "compare", "compare.top_changes", "int", (3, 50), restart=False, unit="")
_f(_T_SENT, "compare", "compare.include_in_report", "bool", restart=False)
_f(_T_SENT, "compare", "compare.cache_seconds", "int", (0, 3600), restart=False)
# --- The log of actions (Complete only): who changed what, with a chain of hashes; on by default, only names and never values
_f(_T_SENT, "audit_log", "audit_log.enabled", "bool", restart=False, secure=True)
_f(_T_SENT, "audit_log", "audit_log.max_mb", "int", (1, 500), restart=False, unit="MB")
_f(_T_SENT, "audit_log", "audit_log.keep_generations", "int", (1, 20), restart=False, unit="", secure=True)
_f(_T_SENT, "audit_log", "audit_log.required", "bool", restart=False, secure=True)
_f(_T_SENT, "audit_log", "audit_log.maintainers_can_read", "bool", restart=False, secure=True)
# --- Scheduled reports (Complete only): HTML and Markdown on a cron schedule, off by default
_f(_T_SENT, "report_schedule", "report_schedule.enabled", "bool", restart=False)
_f(_T_SENT, "report_schedule", "report_schedule.cron", "text", CRON_RE, restart=False)
_f(_T_SENT, "report_schedule", "report_schedule.formats", "enum", ("html", "markdown", "both"), restart=False)
_f(_T_SENT, "report_schedule", "report_schedule.keep", "int", (1, 500), restart=False, unit="")
_f(_T_SENT, "report_schedule", "report_schedule.top", "int", (1, 50), restart=False, unit="")
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
_f(_T_PATHS, "retention", "retention.enabled", "bool", restart=False, secure=True)
_f(_T_PATHS, "retention", "retention.events_days", "int", (1, 3650), restart=False)
_f(_T_PATHS, "retention", "retention.analytics_days", "int", (1, 3650), restart=False)
_f(_T_PATHS, "retention", "retention.mode", "enum", ("delete", "archive"), restart=False, secure=True)
_f(_T_PATHS, "retention", "retention.events_max_kb", "int", (64, 1048576), unit="KB")
_f(_T_PATHS, "retention", "retention.interval_hours", "int", (1, 168), restart=False)
_f(_T_PATHS, "retention", "retention.warn_events_mb", "int", (1, 100000), restart=False, unit="MB")
_f(_T_PATHS, "ops_backup", "ops.backup.enabled", "bool", restart=False, secure=True)
_f(_T_PATHS, "ops_backup", "ops.backup.dir", "path", restart=False)
_f(_T_PATHS, "ops_backup", "ops.backup.interval_hours", "int", (1, 720), restart=False)
_f(_T_PATHS, "ops_backup", "ops.backup.keep", "int", (1, 365), restart=False, unit="")
_f(_T_PATHS, "ops_backup", "ops.backup.include_config", "bool", restart=False, secure=True)
_f(_T_PATHS, "ops_backup", "ops.backup.compress_level", "int", (0, 9), restart=False, unit="")
_f(_T_PATHS, "ops_backup", "ops.backup.encrypt", "bool", restart=False, secure=True)
_f(_T_PATHS, "ops_backup", "ops.backup.key_env", "text", AI_ENV_RE, restart=False, secure=True)
_f(_T_PATHS, "ops_purge", "ops.purge.enabled", "bool", restart=False, secure=True)
_f(_T_PATHS, "ops_purge", "ops.purge.require_backup_hours", "int", (0, 720), restart=False, secure=True, unit="h")
_f(_T_PATHS, "ops_doctor", "ops.doctor.strict_exit", "bool", restart=False)
_f(_T_PATHS, "ops_doctor", "ops.doctor.backup_max_age_days", "int", (1, 365), restart=False)
_f(_T_PATHS, "ops_doctor", "ops.doctor.min_free_mb", "int", (50, 10000000), restart=False, unit="MB")
_f(_T_PATHS, "ops_doctor", "ops.doctor.sqlite_check", "enum", ("quick", "deep", "off"), restart=False)
_f(_T_PATHS, "ops_doctor", "ops.doctor.sqlite_timeout_s", "int", (1, 600), restart=False, unit="s")
_f(_T_PATHS, "ops_doctor", "ops.doctor.webhook_min_length", "int", (8, 128), restart=False, unit="")
# --- Outputs and exports
_f(_T_OUT, "prometheus", "outputs.prometheus.enabled", "bool", restart=False, secure=True)
_f(_T_OUT, "prometheus", "outputs.prometheus.per_repo", "bool", restart=False)
_f(_T_OUT, "json", "outputs.json.enabled", "bool", restart=False, secure=True)
_f(_T_OUT, "dashboard", "outputs.dashboard.enabled", "bool", restart=False, secure=True)
# --- Integrations: external AI, incoming webhook
_f(_T_AI, "provider", "ai.provider", "enum", ("none", "ollama", "openai-compatible", "anthropic", "copilot"), secure=True)
_f(_T_AI, "provider", "ai.model", "text", MODEL_RE)
_f(_T_AI, "provider", "ai.ollama_url", "text", OLLAMA_RE)
_f(_T_AI, "provider", "ai.base_url", "text", AI_URL_RE, secure=True)
_f(_T_AI, "provider", "ai.allow_private_targets", "bool", secure=True)
_f(_T_AI, "provider", "ai.api_key_env", "text", AI_ENV_RE)
_f(_T_AI, "provider", "ai.daily_limit", "int", (0, 500), unit="calls")
_f(_T_AI, "limits", "ai.max_input_chars", "int", (500, 20000), unit="chars")
_f(_T_AI, "limits", "ai.max_output_chars", "int", (200, 8000), unit="chars")
_f(_T_AI, "limits", "ai.timeout_seconds", "int", (5, 300))
_f(_T_AI, "limits", "ai.skill", "bool", restart=False)
_f(_T_AI, "limits", "ai.skill_max_chars", "int", (300, 12000), unit="chars", restart=False)
_f(_T_AI, "limits", "ai.untrusted_text_max", "int", (200, 20000), unit="chars", restart=False)
_f(_T_AI, "privacy", "ai.airgapped", "bool", restart=False, secure=True)
_f(_T_AI, "privacy", "ai.airgap_hosts", "names", restart=False, secure=True)
_f(_T_AI, "privacy", "ai.redact.extra_terms", "names", restart=False, secure=True)
_f(_T_AI, "privacy", "ai.redact.extra_patterns", "names", restart=False, secure=True)
_f(_T_AI, "privacy", "ai.prompt_log.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "privacy", "ai.prompt_log.keep", "int", (10, 5000), unit="lines", restart=False)
_f(_T_AI, "assistant", "ai.assistant.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "assistant", "ai.assistant.max_context", "int", (500, 200000), unit="tokens", restart=False)
_f(_T_AI, "assistant", "ai.assistant.tools", "names", restart=False, secure=True)
_f(_T_AI, "assistant", "ai.assistant.max_tool_calls", "int", (0, 20), unit="calls", restart=False)
_f(_T_AI, "assistant", "ai.similar.enabled", "bool", restart=False)
_f(_T_AI, "assistant", "ai.similar.max", "int", (1, 20), unit="", restart=False)
_f(_T_AI, "catalog", "ai.catalog.enabled", "bool", secure=True)
_f(_T_AI, "catalog", "ai.catalog.ttl_minutes", "int", (5, 10080))
_f(_T_AI, "catalog", "ai.catalog.max_requests_per_day", "int", (1, 200), unit="calls")
_f(_T_AI, "catalog", "ai.catalog.fit_context", "bool")
for _task in ("build", "codeql", "report", "diagnose", "alert"):      # a model for each kind of question: empty = the general one (see sentinels/ai_chain.py)
    _f(_T_AI, "task_" + _task, f"ai.tasks.{_task}.provider", "text", AI_REF_RE, secure=True)
    _f(_T_AI, "task_" + _task, f"ai.tasks.{_task}.model", "text", MODEL_RE)
    _f(_T_AI, "task_" + _task, f"ai.tasks.{_task}.max_input_chars", "int", (0, 20000), unit="chars")
    _f(_T_AI, "task_" + _task, f"ai.tasks.{_task}.max_output_chars", "int", (0, 8000), unit="chars")
    _f(_T_AI, "task_" + _task, f"ai.tasks.{_task}.timeout_seconds", "int", (0, 300))
_f(_T_AI, "fallback", "ai.fallback", "text", AI_FALLBACK_RE, secure=True)
_f(_T_AI, "fallback", "ai.fallback_max_attempts", "int", (1, 5), unit="")
_f(_T_AI, "fallback", "ai.fallback_cloud_allowed", "names", secure=True)
_f(_T_AI, "fallback", "ai.fallback_after_seconds", "int", (0, 300))
_f(_T_AI, "budget", "ai.model_daily_limit", "int", (0, 500), unit="calls")
_f(_T_AI, "budget", "ai.cost_limit_daily", "float", (0.0, 100000.0), unit="")
_f(_T_AI, "budget", "ai.model_cost_limit_daily", "float", (0.0, 100000.0), unit="")
_f(_T_AI, "scope", "ai.events", "names")
_f(_T_AI, "scope", "ai.allowed_repos", "names")
_f(_T_AI, "scope", "ai.answer_language", "enum", ("",) + tuple(i18n.LANGS), False)
_f(_T_AI, "actions", "ai.actions.enabled", "bool", secure=True)
_f(_T_AI, "actions", "ai.actions.execute", "bool", secure=True)
_f(_T_AI, "actions", "ai.actions.allowed", "names")
_f(_T_AI, "actions", "ai.actions.max_per_hour", "int", (1, 60), unit="")
_f(_T_AI, "actions", "ai.actions.ttl_seconds", "int", (30, 3600))
_f(_T_HOOK, "inbound", "webhook.enabled", "bool", secure=True)
_f(_T_HOOK, "inbound", "webhook.secret_env", "text", WEBHOOK_ENV_RE, secure=True)
_f(_T_HOOK, "inbound", "webhook.signing_state", "status", restart=False)
_f(_T_HOOK, "inbound", "webhook.record_events", "bool")
_f(_T_HOOK, "inbound", "webhook.live_events_keep", "int", (10, 1000), unit="")
_f(_T_HOOK, "inbound", "live.sse.enabled", "bool", restart=False, secure=True)
_f(_T_HOOK, "inbound", "live.sse.max_seconds", "int", (60, 86400), restart=False)
_f(_T_HOOK, "inbound", "live.sse.max_clients", "int", (1, 10), restart=False, unit="")
_f(_T_HOOK, "inbound", "webhook.replay_seconds", "int", (60, 86400))
_f(_T_HOOK, "inbound", "webhook.max_per_minute", "int", (1, 600), unit="")
_f(_T_HOOK, "inbound", "webhook.max_bad_per_minute", "int", (1, 6000), unit="")
_f(_T_HOOK, "inbound", "webhook.max_verified_per_minute", "int", (1, 6000), unit="")
_f(_T_HOOK, "inbound", "webhook.reject_stale", "bool")
_f(_T_HOOK, "inbound", "webhook.persist_deliveries", "bool")
_f(_T_HOOK, "chatops", "chatops.enabled", "bool", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.slack.enabled", "bool", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.slack.signing_secret_env", "text", SLACK_ENV_RE, secure=True)
_f(_T_HOOK, "chatops", "chatops.slack.state", "status", restart=False)
_f(_T_HOOK, "chatops", "chatops.discord.enabled", "bool", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.discord.public_key_env", "text", DISCORD_ENV_RE, secure=True)
_f(_T_HOOK, "chatops", "chatops.discord.state", "status", restart=False)
_f(_T_HOOK, "chatops", "chatops.allowed_teams", "names", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.allowed_channels", "names", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.allowed_users", "names", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.allowed_words", "names", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.links", "bool", restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.show_repo_names", "enum", ("all", "public", "none"), restart=False, secure=True)
_f(_T_HOOK, "chatops", "chatops.max_rows", "int", (1, 25), restart=False, unit="")
_f(_T_HOOK, "chatops", "chatops.max_age_seconds", "int", (30, 300), restart=False)
_f(_T_HOOK, "chatops", "chatops.rate_per_user_per_minute", "int", (1, 600), restart=False, unit="")
_f(_T_HOOK, "chatops", "chatops.rate_per_channel_per_minute", "int", (1, 600), restart=False, unit="")
_f(_T_HOOK, "chatops", "chatops.rate_per_minute", "int", (1, 6000), restart=False, unit="")
# --- Reads and cache (conditional reads)
_f("cache", "etag", "cache.etag.enabled", "bool")
_f("cache", "etag", "cache.etag.ttl_hours", "int", (1, 168))
_f("cache", "etag", "cache.etag.skip_stateful", "bool")
_f("cache", "etag", "cache.etag.revalidate_active", "bool")
_f("cache", "etag", "cache.negative_ttl_s", "int", (0, 3600))
# --- Notifications
_f("notify", "main", "notify.enabled", "bool", secure=True)
_f("notify", "main", "notify.allow_private_targets", "bool", secure=True)
_f("notify", "main", "network.use_proxy", "bool", restart=False, secure=True)
_f("notify", "main", "notify.events", "names")
_f("notify", "main", "notify.max_per_hour", "int", (1, 600), unit="")
_f("notify", "ch_telegram", "notify.channels.telegram.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_telegram", "notify.channels.telegram.token_env", "text", NOTIFY_ENV_RE, label=["cfg.p.token_env"], help="cfg.h.p.token_env")
_f("notify", "ch_telegram", "notify.channels.telegram.chat_id", "text", CHAT_RE, label=["cfg.p.chat_id"], help="cfg.h.p.chat_id")
_f("notify", "ch_discord", "notify.channels.discord.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_discord", "notify.channels.discord.url_env", "text", NOTIFY_ENV_RE, label=["cfg.p.url_env"], help="cfg.h.p.url_env")
_f("notify", "ch_slack", "notify.channels.slack.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_slack", "notify.channels.slack.url_env", "text", NOTIFY_ENV_RE, label=["cfg.p.url_env"], help="cfg.h.p.url_env")
_f("notify", "ch_apprise", "notify.channels.apprise.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on", secure=True)
_f("notify", "ch_apprise", "notify.channels.apprise.urls_env", "text", NOTIFY_ENV_RE, label=["cfg.p.url_env"], help="cfg.h.p.apprise_env")
_f("notify", "ch_matrix", "notify.channels.matrix.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_matrix", "notify.channels.matrix.homeserver", "text", HTTPS_RE, label=["cfg.p.homeserver"], help="cfg.h.p.homeserver")
_f("notify", "ch_matrix", "notify.channels.matrix.room", "text", ROOM_RE, label=["cfg.p.room"], help="cfg.h.p.room")
_f("notify", "ch_matrix", "notify.channels.matrix.token_env", "text", NOTIFY_ENV_RE, label=["cfg.p.token_env"], help="cfg.h.p.token_env")
_f("notify", "ch_mqtt", "notify.channels.mqtt.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_mqtt", "notify.channels.mqtt.host", "text", LOOP_HOST_RE, label=["cfg.p.local_host"], help="cfg.h.p.local_host")
_f("notify", "ch_mqtt", "notify.channels.mqtt.port", "int", (1, 65535), unit="", label=["cfg.p.port"], help="cfg.h.p.port")
_f("notify", "ch_mqtt", "notify.channels.mqtt.topic", "text", TOPIC_RE, label=["cfg.p.topic"], help="cfg.h.p.topic")
_f("notify", "ch_http_local", "notify.channels.http_local.enabled", "bool", label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_http_local", "notify.channels.http_local.url", "text", LOOP_URL_RE, label=["cfg.p.local_url"], help="cfg.h.p.local_url")
_f("notify", "users", "notify.users.enabled", "bool", restart=False, secure=True)
_f("notify", "users", "notify.users.max_per_hour", "int", (1, 600), restart=False, unit="")
_f("notify", "digest", "notify.digest.max_items", "int", (5, 200), restart=False, unit="")
_f("notify", "ch_ntfy", "notify.channels.ntfy.enabled", "bool", restart=False, secure=True, label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_ntfy", "notify.channels.ntfy.server", "text", NTFY_SERVER_RE, restart=False, secure=True, label=["cfg.p.server"], help="cfg.h.p.server")
_f("notify", "ch_teams", "notify.channels.teams.enabled", "bool", restart=False, secure=True, label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_email", "notify.channels.email.enabled", "bool", restart=False, secure=True, label=["cfg.p.channel_on"], help="cfg.h.channel_on")
_f("notify", "ch_email", "notify.channels.email.host", "text", LOOP_HOST_RE, restart=False, secure=True, label=["cfg.p.local_host"], help="cfg.h.p.local_host")
_f("notify", "ch_email", "notify.channels.email.port", "int", (1, 65535), restart=False, secure=True, unit="", label=["cfg.p.port"], help="cfg.h.p.port")
_f("notify", "ch_email", "notify.channels.email.sender", "text", SENDER_RE, restart=False, secure=True, label=["cfg.p.sender"], help="cfg.h.p.sender")
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
_f("lint", "lint_source", "lint.source", "enum", ("clone", "auto", "sparse"))
_f("lint", "lint_api", "lint.api.refresh_seconds", "int", (600, 604800))
_f("lint", "lint_api", "lint.api.max_calls_per_tick", "int", (1, 200), unit="calls")
_f("lint", "lint_api", "lint.api.max_files_per_repo", "int", (1, 100))
_f("lint", "lint_sparse", "lint.sparse.refresh_seconds", "int", (600, 604800))
_f("lint", "lint_sparse", "lint.sparse.max_repos_per_tick", "int", (1, 20))
_f("lint", "own_actions", "lint.own_owners", "names")
_f("lint", "own_actions", "lint.unpinned_own", "enum", ("same", "info", "ignore"))
for _rule in ("unpinned_uses", "permissions", "secrets_in_clear", "injection", "pr_target", "no_timeout", "secrets_inherit", "own_action_main", "permissions_top"):
    _f("lint", "rule_" + _rule, f"lint.rules.{_rule}.enabled", "bool", label=["cfg.p.rule_on"], help="cfg.h.rule_on")
    _f("lint", "rule_" + _rule, f"lint.rules.{_rule}.severity", "enum", ("info", "warn", "bad"), label=["cfg.p.severity"], help="cfg.h.p.severity")
# --- Terminal view
_f("console", "tui", "tui.theme", "enum", ("dark", "light"), False)
_f("console", "tui", "tui.refresh_seconds", "int", (2, 300), False)
# --- Advanced: opt-in features, every one OFF by default (network, own token, actions on GitHub, act, mirror, runners, OTLP, organisations, FinOps)
_f("advanced", "network", "listen.network", "bool", secure=True)
_f("advanced", "network", "listen.host", "text", LISTEN_HOST_RE, secure=True)
_f("advanced", "network", "listen.token_env", "text", TOKEN_ENV_RE, secure=True)
_f("advanced", "network", "listen.allowed_hosts", "names", secure=True)
_f("advanced", "network", "listen.tls_cert_file", "path", secure=True)
_f("advanced", "network", "listen.tls_key_file", "path", secure=True)
_f("advanced", "network", "listen.secure_cookie", "bool", secure=True)
_f("advanced", "network", "listen.proxy_public_host", "text", PROXY_HOST_RE, secure=True)
_f("advanced", "network", "listen.max_failed_attempts", "int", (3, 100), unit="", secure=True)
_f("advanced", "network", "listen.query_access", "bool", secure=True)
_f("advanced", "network", "listen.trusted_proxy", "bool", secure=True)
_f("advanced", "network", "listen.trusted_proxies", "names", secure=True)
# --- Team mode: users with roles (off by default; one person alone needs nothing of this)
_f("advanced", "auth", "auth.enabled", "bool", restart=False, secure=True)
_f("advanced", "auth", "auth.session_hours", "int", (1, 720), restart=False, secure=True, unit="h")
_f("advanced", "auth", "auth.max_failed_logins", "int", (3, 20), restart=False, secure=True, unit="")
_f("advanced", "auth", "auth.lockout_minutes", "int", (1, 1440), restart=False, secure=True, unit="min")
_f("advanced", "auth", "auth.min_length", "int", (8, 64), restart=False, secure=True, unit="")
_f("advanced", "auth", "auth.allow_bearer", "bool", restart=False, secure=True)
_f("advanced", "auth", "auth.audit", "bool", restart=False, secure=True)

_f("advanced", "network", "listen.local_port", "int", (0, 65535), unit="", secure=True)
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
_f("advanced", "runner_model", "runners.model.enabled", "bool", restart=False)
_f("advanced", "runner_model", "runners.model.jobs_per_cycle", "int", (0, 100), unit="calls", restart=False)
_f("advanced", "runner_model", "runners.model.thirdparty_labels", "names", restart=False)
_f("advanced", "runner_model", "runners.model.large_labels", "names", restart=False)
_f("advanced", "runner_model", "runners.model.self_labels", "names", restart=False)
_f("advanced", "runner_model", "runners.model.thirdparty_usd_per_minute", "float", (0, 10), unit="", restart=False)
_f("advanced", "runner_model", "runners.model.queue_warn_minutes", "int", (1, 10080), unit="min", restart=False)
_f("advanced", "runner_model", "runners.model.runaway_runs_per_hour", "int", (0, 1000), unit="", restart=False)
_f("advanced", "runner_model", "runners.model.runaway_ignore_events", "names", restart=False)
_f("advanced", "runner_model", "runners.model.alerts", "bool", restart=False)
_f("advanced", "upstream", "upstream.enabled", "bool", restart=False)
_f("advanced", "upstream", "upstream.refresh_hours", "int", (1, 720), unit="h", restart=False)
_f("advanced", "upstream", "upstream.requests_per_hour", "int", (1, 120), unit="calls", restart=False)
_f("advanced", "upstream", "upstream.forks_per_request", "int", (1, 25), restart=False)
_f("advanced", "upstream", "upstream.news_days", "int", (1, 90), unit="d", restart=False)
_f("advanced", "upstream", "upstream.notify", "bool", restart=False)
_f("advanced", "upstream", "upstream.repos", "names", restart=False)
_f("advanced", "api_v1", "api.v1_enabled", "enum", ("auto", "on", "off"), restart=False)
_f("advanced", "api_v1", "api.experimental_routes", "bool", restart=False)
_f("advanced", "api_v1", "cli.prefer_v1", "bool", restart=False)
_f("advanced", "api_v1", "api.default_limit", "int", (1, 1000), restart=False)
_f("advanced", "api_v1", "api.max_limit", "int", (1, 1000), restart=False)
_f("advanced", "api_v1", "api.cursor_ttl_seconds", "int", (30, 86400), unit="s", restart=False)
_f("advanced", "api_v1", "api.gzip_min_bytes", "int", (0, 10000000), unit="", restart=False)
_f("advanced", "runner_model", "runners.model.alert_level", "enum", ("info", "warning", "error"), restart=False)
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
_f(_T_AI, "notice", "ai_notify.enabled", "bool", restart=False, secure=True)
_f(_T_AI, "notice", "ai_notify.confirmed_provider", "text", re.compile(r"^[a-z0-9-]{0,40}\Z"), restart=False, secure=True)
_f(_T_AI, "notice", "ai_notify.max_calls_per_hour", "int", (1, 60), restart=False, secure=True, unit="calls")
_f(_T_AI, "notice", "ai_notify.cost_per_call_cents", "int", (0, 10000), restart=False, secure=True, unit="")
_f(_T_AI, "notice", "ai_notify.max_cost_per_hour_cents", "int", (0, 100000), restart=False, secure=True, unit="")
_f(_T_AI, "notice", "ai_notify.timeout_seconds", "int", (5, 120), restart=False, secure=True, unit="s")
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
_f(_T_AI, "alerts", "ai_alerts.briefs.access_log", "bool", restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.enabled", "bool", restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.block_on_stop", "bool", restart=False, secure=True)
_f(_T_AI, "alerts", "ai_alerts.client_hook.cooldown_minutes", "int", (1, 1440), restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.stale_hours", "int", (1, 168), restart=False)
_f(_T_AI, "alerts", "ai_alerts.client_hook.max_lines", "int", (1, 40), restart=False, unit="")
_f(_T_AI, "alerts", "ai_alerts.client_hook.max_chars", "int", (400, 8000), restart=False, unit="")
_f(_T_AI, "lessons", "lessons.enabled", "bool", restart=False)
_f(_T_AI, "lessons", "lessons.allow_write", "bool", restart=False, secure=True)
_f(_T_AI, "lessons", "lessons.retention_days", "int", (1, 3650), restart=False)
_f(_T_AI, "lessons", "lessons.max_entries", "int", (100, 100000), restart=False, unit="")
_f(_T_AI, "lessons", "lessons.brief_max_bytes", "int", (500, 20000), restart=False, unit="")
_f(_T_AI, "lessons", "lessons.recurring_from", "int", (2, 20), restart=False, unit="")
_f("quota", "savings", "savings.webhook_first", "bool", restart=False)
_f("quota", "savings", "savings.webhook_live_per_repo", "bool", restart=False)
_f("quota", "savings", "savings.webhook_window_minutes", "int", (5, 1440), restart=False)
_f("quota", "savings", "savings.webhook_full_minutes", "int", (30, 10080), restart=False)
_f("quota", "savings", "savings.feeds.enabled", "bool", restart=False, secure=True)
_f("quota", "savings", "savings.feeds.method", "enum", ("atom", "git", "auto"), restart=False)
_f("quota", "savings", "savings.feeds.max_age_minutes", "int", (15, 10080), restart=False)
# @@MORE_SETTINGS@@

TAB_ORDER = ("basic", "general", "polling", "cache", "quota", "sentinel", "surface", "readiness", "paths", "outputs", "ai", "webhook", "notify", "analytics", "lint", "advanced", "console")
ROWS.sort(key=lambda row: TAB_ORDER.index(row[0]))     # stable: inside a tab the order of writing is kept
SCHEMA = [(tab, key, kind, bounds, restart) for tab, _block, key, kind, bounds, restart in ROWS]
FIELDS = {row[1]: row for row in SCHEMA}
GROUPS = tuple(dict.fromkeys(row[0] for row in SCHEMA))
assert set(GROUPS) <= set(TAB_ORDER)
OUTPUT_DEFAULTS = {"prometheus": {"enabled": False, "per_repo": True}, "json": {"enabled": False}, "dashboard": {"enabled": False}}
STATUS_KEYS = {"webhook.signing_state", "chatops.slack.state", "chatops.discord.state"}      # computed, read-only: never written


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
        if path == "display.timezone":      # a name the system and the built-in table do not know would silently show the local time: it is refused
            from github_actions_monitor.util import tzdisplay
            return (True, value.strip()) if bounds.match(value.strip()) and tzdisplay.valid_setting(value.strip()) else (False, "text")
        if path == "report_schedule.cron":      # a schedule the reports could not read would silently never run: it is refused
            from github_actions_monitor.reporting import report_schedule as schedule
            return (True, " ".join(value.split())) if bounds.match(value.strip()) and schedule.parse(value) is not None else (False, "text")
        return (True, value.strip()) if bounds.match(value.strip()) else (False, "text")
    if kind == "path":
        if not isinstance(value, str):
            return False, "type"
        text = value.strip()
        if len(text) > 260 or any(ord(c) < 32 for c in text) or text.startswith(("\\\\", "//")) or _FOREIGN.match(text):
            return False, "path"
        if path == "ops.backup.dir" and (not text or not (text.startswith("/") or re.match(r"^[A-Za-z]:", text)) and ".." in re.split(r"[\\/]+", text)):
            return False, "path"      # the folder of the copies: never empty and a relative one never climbs out of the data folder
        return True, text
    if kind == "names":
        pattern = WORKDAY_RE if path == "compare.workdays" else FLEET_LABEL_RE if path == "fleet.labels" else FLEET_FILTER_RE if path == "fleet.saved_filters" else RUNNER_LABEL_RE if path in RUNNER_LABEL_KEYS else LABEL_RE if path in LABEL_KEYS else (NET_RE if path == "listen.trusted_proxies" else (BRANCH_RE if path == "ci.extra_branches" else (GLOB_RE if path in ("sentinel.hygiene.ruleset_names", "sentinels.delivery.expected_assets") else (PATH_RE if path in PATH_KEYS else (alertflow.SILENCE_RE if path == "alerts.silences" else (alertflow.PATTERN_RE if path == "alerts.service.workflows" else (PAIR_RE if path in PAIR_KEYS else NAME_RE)))))))
        if not isinstance(value, list) or len(value) > 200 or not all(isinstance(v, str) and pattern.match(v) for v in value):
            return False, "names"
        if path == "sentinel.hygiene.ruleset_names" and not value:
            return False, "names"      # no name at all would flag every repository
        if path == "sentinel.hygiene.skip" and not set(value) <= set(HYGIENE_SKIP):
            return False, "names"
        if path == "chatops.allowed_words":      # the closed list of the chat can only be narrowed, never widened
            from github_actions_monitor.chatops import commands as chat_commands
            if not set(value) <= set(chat_commands.COMMANDS):
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


LITE_KEYS = ("ports.complete", "ports.lite", "github_owner", "language", "repos", "ecosystems", "exclude", "refresh_seconds", "open_browser", "updates.check", "airgapped") + tuple(
    k for k in FIELDS if k.startswith(("ai_alerts.", "sound.", "display.", "modes.", "central.", "extra_reader.", "github_app.", "network.etag", "network.graphql")))      # the short settings page of the lite product; the connection with an AI tool, the sound and the look are the same in both editions


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
    if "ports.complete" in clean and clean.get("ports.complete") == clean.get("ports.lite"):      # two editions cannot listen on one port
        errors["ports.lite"] = "same_port"
        del clean["ports.lite"], clean["ports.complete"]
    return clean, errors


def _read_file(path):
    """The dict in the file; None when it is missing, FileNotFoundError aside; ValueError when it is not a JSON object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value


def webhook_state(config):
    """"defined" | "short" | "undefined": the only thing the page may know about the webhook secret (never the secret, nor its length). It is read where the receiver reads it: the environment."""
    from github_actions_monitor.security import webhook
    secret = webhook.settings(config)["secret"]
    if not secret:
        return "undefined"
    return "defined" if len(secret) >= webhook.MIN_SECRET else "short"


def chatops_state(config, provider):
    """"defined" | "undefined": the only thing the page may know about the proof of a chat platform (the signing secret of Slack, the public key of Discord), never its value. It is read where the receiver reads it."""
    from github_actions_monitor.chatops import inbound
    return inbound.state(config, provider)


def _remote_visible():
    from github_actions_monitor.security import localguard
    return localguard.REMOTE_WRITABLE


def describe(path=CONFIG_FILE, lite=False, remote=False):
    """`remote` = the asker is a client of the network, not this computer: the value of every setting that a client of the network may not change (see localguard.REMOTE_WRITABLE) is
    left out and the field only says whether it is defined (paths of keys, names of variables and channels are for the computer of the monitor). What the page shows: {"groups": [{"id", "blocks": [{"id", "title_key", "fields": [...]}], "fields": [...]}], "backups": N}. A field: {"key", "type", "value", "default", "min",
    "max", "enum", "restart", "unit", "secure", "label", "help", "block", "master"}. Values come from the file over the template; nothing outside SCHEMA is ever included."""
    template = {}
    try:
        template = _read_file(paths.EXAMPLES / "actions_monitor.example.json")
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
                    value = chatops_state(current, key.split(".")[1]) if key.startswith("chatops.") else webhook_state(current)
                hidden = remote and key not in _remote_visible()
                if hidden:
                    kind, default = "status", None
                    value = "defined" if value not in (None, "", [], {}, False) else "undefined"
                item = {"key": key, "type": kind, "value": value if value is not None else ("" if kind in ("text", "path", "enum") else None), "default": default, "restart": restart,
                        "unit": META[key]["unit"], "secure": META[key]["secure"], "label": label_keys(key), "help": help_key(key), "block": block,
                        "master": index == 0 and kind == "bool" and len(keys) > 1, **({"redacted": True} if hidden else {})}
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
    from github_actions_monitor.app import profiles
    return {"groups": groups, "backups": backups, "presets": profiles.listing(lite=lite)}


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
LOCK_WAIT = 10.0      # seconds a save waits for the lock file of another process (the tests shorten it)


class LockBusy(OSError):
    """The lock file of the configuration is held by another process for longer than the wait: nothing is written (a save without the lock could undo the other one)."""


@contextlib.contextmanager
def file_lock(path, timeout=10.0):
    """Exclusive lock around read -> change -> write of the configuration: a lock of this process (two requests of the page at once) AND a lock file next to it (another process that
    saves at the same time). Without it the second save would start from the file as it was before the first and undo it. When the lock of another process is not released within
    `timeout` the save FAILS with LockBusy; it never goes on without the lock. (A lock file that cannot even be created, for example a read-only folder, does not block: the write itself fails then.)"""
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
                        handle.close()
                        raise LockBusy("the configuration is locked by another process") from None
                    time.sleep(0.05)
        except LockBusy:
            raise
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
    try:
        with file_lock(path, LOCK_WAIT):
            return _apply_locked(clean, path)
    except LockBusy:
        return {"ok": False, "errors": {"_": "busy"}}


def _apply_locked(clean, path):
    try:
        current = _read_file(path) if path.is_file() else {}
    except (OSError, ValueError):
        return {"ok": False, "errors": {"_": "unreadable"}}     # a broken file is never overwritten from the page
    changed = [key for key, value in clean.items() if _get(current, key, "\0missing") != value]
    if not changed:
        return {"ok": True, "changed": [], "restart": [], "backup": False}
    merged = json.loads(json.dumps(current))
    for key in changed:
        _set(merged, key, clean[key])
    taken = {key for _name, keys in envguard.shared_names(merged) for key in keys} - {key for _name, keys in envguard.shared_names(current) for key in keys}
    clashes = {key: "invalid" for key in changed if key in taken and key in envguard.ENV_SETTINGS}      # a variable is named by ONE setting: the second to say it is refused
    if clashes:
        return {"ok": False, "errors": clashes}
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
