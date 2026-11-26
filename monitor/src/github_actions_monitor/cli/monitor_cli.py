# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command line as a client of the monitor (1.7.4): one entry, `python bin/monitor_cli.py COMMAND [options]`, that reads what the running monitor says (`GET /api/...` on this computer, or
`--url` / the variable MONITOR_URL) and never repeats the work of the page against GitHub. The scripts that already exist (read_report.py, --doctor, gha_dispatch_all.py ...) keep working.

  status    one screen: version, edition, repositories, what runs, what fails, the allowance
  accounts  the accounts the supervisor watches (the complete edition with an `accounts/` folder)
  alerts    the alerts of every sentinel in one list (--sentinel ci|collab, --level, --muted); with --since 24h the ones that were open at some moment of that time, closed ones too
  proposals the actions the AI proposed: list | show ID | approve ID | reject ID | execute ID (this computer only; nothing runs without `ai.actions.execute`, and with
            `ai.actions.require_approval` not before it is approved)
  live      the last events that arrived through the webhook and the state of the receiver
  metrics   the figures of the monitor as one `name=value` line each (nothing else on the standard output), made for cron and for mail; with --if-problem it writes nothing at all
            when all is well, so cron sends no mail
  doctor    the checks of --doctor for this installation (no monitor needed); --strict makes a warning exit 3
            --latency adds one check that reads the events of the account and the runs of the latest pushes and tells how late the events are (reads only)
  monitor   `monitor [N]`: `watch status` that refreshes every N seconds, for a terminal left open
  backup    create | verify | restore | status | list: the complete backup package of this installation (no monitor needed); --key-env NAME with --encrypt seals it (optional library), --deep on
            verify restores it into a temporary folder, restore takes --account ID, --to-dir DIR and --force
  ai-hook   install | status | uninstall the gate script that tells an AI tool what the monitor sees (--assistant, --cursor or --generic; --scope project|user); it needs no
            running monitor and writes only the settings file of that tool (merged, with a backup), never anything on GitHub
  health    a quick check before reading anything heavy: is the monitor reachable, does it accept this client, does the GitHub credential of the account answer (a limit of the
            allowance is told apart from a credential that failed). Alias: check. With --deep it also asks whether the supervisor and the refresh cycle of every account are alive
  update    the updater of the monitor (tools/monitor_updater.py, the same engine as the page, the window and the text menu): `update` opens the page in your browser; `update status|releases|plan|apply|migrate|rollback|history`
            take the options of the updater (--to, --zip, --dry-run, --json ...); it needs no running monitor and never updates by itself. Its exit codes are its own (see docs/UPDATE.md)
  credential  replace | reload: put another login of GitHub in place of the one of an account that GitHub revoked (or let expire) without restarting anything; the token is read from a
            file (--new-token-file, or - for the standard input), never from a flag, and it is checked against GitHub before it is kept. Needs an administrator in the team mode, or this computer

A monitor on another computer works the same way: --url (or MONITOR_URL) names it; --ca-file (or MONITOR_CA_FILE) trusts the certificate authority of its HTTPS certificate; in the team mode
--user NAME with --password-file FILE (or MONITOR_USER, MONITOR_PASSWORD_FILE) signs in and the session travels as a Bearer token (`auth.allow_bearer` must be on).

Every command takes --format text|table|plain|json|ndjson (--json is --format json; `cli.default_format` sets the one used when none is given) and --json (the answer as one JSON document), --account ID, --url URL, --timeout SECONDS and --lang CODE. In the network mode the access token is read from MONITOR_ACCESS_TOKEN,
then from its alias MONITOR_TOKEN, then from --token-file (a file only you can read) and last from --token (it shows in the list of processes, so it prints a warning on stderr); plain http to another computer prints a warning on stderr. Nothing here writes to GitHub or changes a setting.
The lite edition answers `status`, `doctor` and `health` (use --lite for its port, 8766 unless `ports.lite` says another); the rest need the complete edition.

Exit codes (stable): 0 all right; 1 wrong use of the command; 2 the monitor cannot be reached; 3 the monitor or GitHub refuses the credential (access token of the network mode, or the login
of GitHub); 4 the monitor answers but is degraded (offline, allowance exhausted, no data yet) or an answer that cannot be read; 5 `alerts --fail-on LEVEL` found alerts of that level or worse;
6 `watch --exit-on-change` saw a change (only when that flag is given).
"""
import argparse
import ipaddress
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

from github_actions_monitor import i18n
from github_actions_monitor.util import platform_compat
from github_actions_monitor.util import ports
from github_actions_monitor.util import tzdisplay
from github_actions_monitor.tool_version import TOOL_VERSION
from github_actions_monitor.security import netguard

EXIT_OK, EXIT_USAGE, EXIT_DOWN, EXIT_AUTH, EXIT_DEGRADED, EXIT_ALERTS = 0, 1, 2, 3, 4, 5
COMMANDS = ("status", "accounts", "alerts", "live", "doctor", "health", "check", "score", "team", "ai-hook", "credential", "lessons", "briefs", "api", "install-skill", "gh-token", "ai", "backup", "update", "compare", "screens", "docs")
BACKUP_ACTIONS = ("create", "verify", "restore", "status", "list")
SKILL_ACTIONS = ("internal", "external")
AI_ACTIONS = ("models", "doctor", "test")
LESSONS_ACTIONS = ("list", "brief", "failures", "close")
PROPOSALS_ACTIONS = ("list", "show", "approve", "reject", "execute")
BRIEFS_ACTIONS = ("index", "show", "all")
DOCS_ACTIONS = ("list", "show")
DOCS_TAIL = {"en": "", "es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}      # the suffix of the translated guides of docs/
SCREENS_ACTIONS = ("list", "urls")
TOOLBOX_ACTIONS = ("limits", "workspaces", "ledger", "summary", "export-events")
API_ACTIONS = ("openapi", "me", "contract-check")
AI_HOOK_ACTIONS = ("install", "status", "uninstall")
CREDENTIAL_ACTIONS = ("replace", "reload")
LITE_COMMANDS = ("status", "doctor", "health", "check", "briefs")
LEVELS = ("info", "warning", "error", "critical")
from github_actions_monitor import families      # noqa: E402
from github_actions_monitor.cli import completions, formats, monitor_admin, terminal      # noqa: E402
from github_actions_monitor.cli import watch as watch_loop      # noqa: E402
from github_actions_monitor.cli import branchwatch      # noqa: E402
from github_actions_monitor.app import codestale      # noqa: E402
from github_actions_monitor.surfaces import kiosk      # noqa: E402
COMMANDS = COMMANDS + ("toolbox", "watch", "monitor", "completions", "kiosk", "metrics", "proposals")      # the operator commands (docs/CLI_OPERATOR.md)
STATUS_CODES = ("classic", "operator")      # `cli.status_codes` / --status-codes: classic = the codes 0 to 5 of every command; operator = status alone says 0 healthy, 1 nothing serving, 2 up but needs attention
EXIT_CHANGED = watch_loop.EXIT_CHANGED      # 6: `watch --exit-on-change` saw something change (only when the flag is given)
COMMANDS = COMMANDS + tuple(c.name for c in families.commands())      # the commands of the parts that plug in by themselves (families/)
LITE_COMMANDS = LITE_COMMANDS + tuple(c.name for c in families.commands() if c.lite)
OPERATOR_WORDS = {"watch": watch_loop.WATCHABLE, "completions": completions.SHELLS, "kiosk": tuple(kiosk.PRESETS)}
WORDS_BY_COMMAND = {"proposals": PROPOSALS_ACTIONS, "ai-hook": AI_HOOK_ACTIONS, "credential": CREDENTIAL_ACTIONS, "lessons": LESSONS_ACTIONS, "install-skill": SKILL_ACTIONS, "ai": AI_ACTIONS, **OPERATOR_WORDS, **{c.name: tuple(c.words) for c in families.commands() if c.words}}
CLIENT = monitor_admin.CLIENT      # the session of the team mode and the authority of the certificate: one dict, shared
PORTS = dict(ports.DEFAULTS)      # the defaults; the port in use is ports.resolve (configuration file, MONITOR_PORT)
TOKEN_VARIABLES = ("MONITOR_ACCESS_TOKEN", "MONITOR_TOKEN")      # the first is the one the monitor itself reads; the second is an alias


class CliError(Exception):
    """An error of the command: the exit code, what happened and `help`, the next step (a sentence that names the guide to read: `docs show NAME`). Without its own help the code gives a general one."""

    def __init__(self, code, text, help=""):      # noqa: A002 - the field is called `help` in the answers
        super().__init__(text)
        self.code, self.text = code, text
        self.help = help or (i18n.t("cli.fix_%d" % code) if code in (EXIT_USAGE, EXIT_DOWN, EXIT_AUTH, EXIT_DEGRADED) else "")


def read_token_file(path):
    """The first line of a file that holds the access token. Raises CliError(1) when it cannot be read or is empty. On a system with file modes a file that others can read is told about on stderr."""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = handle.readline().strip()
        mode = os.stat(path).st_mode
    except (OSError, UnicodeError):
        raise CliError(EXIT_USAGE, i18n.t("cli.token_file_bad", file=path)) from None
    if not value:
        raise CliError(EXIT_USAGE, i18n.t("cli.token_file_bad", file=path))
    if os.name != "nt" and mode & 0o077:
        print(i18n.t("cli.token_file_open", file=path), file=sys.stderr)
    return value


def resolve_token(env=None, flag="", token_file=""):
    """The access token of the network mode: MONITOR_ACCESS_TOKEN, else its alias MONITOR_TOKEN, else the first line of `--token-file`, else the `--token` flag (the last resort: a flag shows
    in the list of processes, so it warns on stderr)."""
    env = os.environ if env is None else env
    for name in TOKEN_VARIABLES:
        value = (env.get(name) or "").strip()
        if value:
            return value
    if token_file:
        return read_token_file(token_file)
    if (flag or "").strip():
        print(i18n.t("cli.token_flag_warn"), file=sys.stderr)
    return (flag or "").strip()


def plain_http_to_network(url):
    """The host when `url` is plain http to an address that is not this computer (the token and the answers would travel in the clear), else ''."""
    parts = urlparse(url if "://" in url else "http://" + url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "http" or not host or host == "localhost":
        return ""
    try:
        return "" if ipaddress.ip_address(host).is_loopback else host
    except ValueError:
        return host


def base_url(url=None, lite=False, env=None):
    """The address of the monitor: --url, else MONITOR_URL, else 127.0.0.1 on the port of the edition. Only http and https are accepted; a path or a query is dropped."""
    env = os.environ if env is None else env
    chosen = (url or env.get("MONITOR_URL") or "").strip()
    if not chosen:
        return f"http://127.0.0.1:{ports.resolve('lite' if lite else 'complete', env=env)}"
    parts = urlparse(chosen if "://" in chosen else "http://" + chosen)
    try:
        port_ok = parts.port is None or 0 < parts.port < 65536
    except ValueError:
        port_ok = False
    if parts.scheme not in ("http", "https") or not parts.hostname or not port_ok:
        raise CliError(EXIT_USAGE, i18n.t("cli.bad_url"))
    return f"{parts.scheme}://{parts.netloc}"


request_headers = monitor_admin.request_headers
open_url = monitor_admin.open_url


def post_json(base, path, payload, timeout=8, token="", guarded=False):
    """(status, document) of the one request with a body this command line makes (see monitor_admin); CliError(2) when nothing answers or its certificate is not trusted. `guarded`: with the one-use
    token the monitor asks for before a write."""
    try:
        return monitor_admin.send_json(base, path, payload, timeout, token, guarded)
    except monitor_admin.BadCertificate:
        raise CliError(EXIT_DOWN, i18n.t("cli.cert_bad", url=base)) from None
    except monitor_admin.Unreachable:
        raise CliError(EXIT_DOWN, i18n.t("cli.unreachable", url=base)) from None


def sign_in(base, user, password, timeout=8, token=""):
    """Opens a session of the team mode for a script: POST /api/auth/login with client "api" and keeps the Bearer token in CLIENT. Raises CliError(3) when the monitor refuses it."""
    status, answer = post_json(base, "/api/auth/login", {"username": user, "password": password, "client": "api"}, timeout, token)
    if status != 200 or not answer.get("token"):
        raise CliError(EXIT_AUTH, i18n.t("cli.login_refused", code=answer.get("code") or status))
    CLIENT["session"] = str(answer["token"])


V1_STATE = {"closed": set()}      # the monitors that answered 404 under /api/v1/ and 200 under /api/: they are asked the old way from then on


def prefer_v1(env=None, config=None):
    """Whether the frozen routes are asked under `/api/v1/` first (`cli.prefer_v1`, true by default; `MONITOR_CLI_PREFER_V1=0|1` wins). It only acts when the monitor answers there (`api.v1_enabled`):
    the first 404 under the prefix sends the request to the old route and the monitor is not asked again."""
    env = os.environ if env is None else env
    flag = (env.get("MONITOR_CLI_PREFER_V1") or "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    if config is None:
        try:
            from github_actions_monitor.util import paths
            config = ports.read_file(paths.config_file())
        except Exception:      # noqa: BLE001 - a configuration that cannot be read never stops a command
            config = {}
    block = config.get("cli") if isinstance(config, dict) else None
    value = block.get("prefer_v1") if isinstance(block, dict) else None
    return value if isinstance(value, bool) else True


def v1_path(path):
    """The route under the prefix when the contract freezes `path` (it answers the same there), else None."""
    from github_actions_monitor.app import api_spec
    base = path.split("?")[0]
    if not base.startswith("/api/") or base.startswith("/api/v1"):
        return None
    return api_spec.prefixed(base) if api_spec.prefixed(base) in api_spec.frozen_paths() else None


def fetch(base, path, query=None, timeout=8, token=""):
    """GET one JSON document of the monitor, under `/api/v1/` first when the route is frozen and `cli.prefer_v1` allows it (see prefer_v1): the same document by either way."""
    versioned = v1_path(path) if base not in V1_STATE["closed"] and prefer_v1() else None
    if versioned:
        try:
            return plain_fetch(base, versioned, query, timeout, token)
        except CliError as error:
            if getattr(error, "http_status", 0) != 404:
                raise
        answer = plain_fetch(base, path, query, timeout, token)      # 404 under the prefix: closed, or a route that does not exist there; the old route decides
        V1_STATE["closed"].add(base)
        return answer
    return plain_fetch(base, path, query, timeout, token)


def plain_fetch(base, path, query=None, timeout=8, token=""):
    """GET one JSON document of the monitor. Raises CliError(2) when it cannot be reached, CliError(3) when it refuses, CliError(4) for an answer that is not JSON."""
    url = base + path + (("?" + urlencode({k: v for k, v in (query or {}).items() if v not in (None, "")})) if query else "")
    request = urllib.request.Request(url, headers=request_headers(token))
    try:
        with open_url(request, timeout) as answer:     # noqa: S310 - http/https only, checked in base_url
            body = answer.read(4_000_000)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise CliError(EXIT_AUTH, i18n.t("cli.refused", code=error.code)) from None
        if error.code == 404:
            gone = CliError(EXIT_DEGRADED, i18n.t("cli.not_here", path=path))
            gone.http_status = 404
            raise gone from None
        raise CliError(EXIT_DEGRADED, i18n.t("cli.http_error", code=error.code)) from None
    except (urllib.error.URLError, OSError, ValueError) as error:
        if monitor_admin.certificate_problem(error):
            raise CliError(EXIT_DOWN, i18n.t("cli.cert_bad", url=base)) from None
        raise CliError(EXIT_DOWN, i18n.t("cli.unreachable", url=base)) from None
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        raise CliError(EXIT_DEGRADED, i18n.t("cli.not_json", path=path)) from None
    if not isinstance(data, dict):      # every answer of the monitor is an object: a list, null or a number is not the monitor (or a broken one)
        raise CliError(EXIT_DEGRADED, i18n.t("cli.not_json", path=path))
    return data


def ago_text(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 3600} h {seconds % 3600 // 60} min" if seconds >= 3600 else (f"{seconds // 60} min" if seconds >= 60 else f"{seconds} s")


# -- the commands: each returns (payload for --json, text lines, exit code)
EXIT_OPERATOR_DOWN, EXIT_OPERATOR_ATTENTION = 1, 2      # the operator scheme of `status`: 0 healthy, 1 nothing is serving, 2 up but needs attention


def status_scheme(ctx):
    """classic or operator: the flag --status-codes, else `cli.status_codes` of the configuration, else classic (the codes every script already knows)."""
    asked = ctx.get("status_codes") or (((ctx.get("raw") or {}).get("cli") or {}).get("status_codes") if isinstance(ctx.get("raw"), dict) and isinstance((ctx.get("raw") or {}).get("cli"), dict) else "")
    return asked if asked in STATUS_CODES else "classic"


def operator_status_code(code):
    """The operator scheme for a `status` that could not read the monitor: nothing answers or the credential is refused = 1 (nothing is serving); an answer that is not the monitor's = 2."""
    return EXIT_OPERATOR_ATTENTION if code == EXIT_DEGRADED else EXIT_OPERATOR_DOWN


def cmd_status(ctx):
    health = fetch(ctx["base"], "/api/health", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    answer = fetch(ctx["base"], "/api/data", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    data = answer.get("data") or {}
    figures = data.get("figures") or {}
    rate = data.get("rate") or {}
    for value, kind in ((data, dict), (figures, dict), (rate, dict), (data.get("repos") or [], list), (data.get("updated") or "", str), (data.get("offline") or {}, dict)):
        if not isinstance(value, kind):      # a field of the wrong type: the answer cannot be read (exit 4), never a half-printed status
            raise ValueError("shape")
    payload = {"version": health.get("version"), "edition": "lite" if health.get("lite") else "complete", "account": health.get("account"), "uptime_seconds": health.get("uptime_seconds"),
               "repos": len(data.get("repos") or []), "active": figures.get("active"), "queued": figures.get("queued"), "failures_24h": figures.get("fail24"), "successes_24h": figures.get("ok24"),
               "red_workflows": figures.get("red"), "updated": data.get("updated"), "updated_local": tzdisplay.stamp(data["updated"]) if data.get("updated") else None, "offline": bool((data.get("offline") or {}).get("offline")),
               "allowance": {"remaining": rate.get("remaining"), "limit": rate.get("limit"), "reset": rate.get("reset")}, "error": answer.get("error") or None,
               "listening": health.get("listening") if health.get("listening") in ("this_computer", "network", "proxy") else None, "credential": (health.get("credential") or {}).get("state") if isinstance(health.get("credential"), dict) else None}
    lines = [i18n.t("cli.status_head", version=payload["version"], edition=i18n.t("cli.edition_" + ("lite" if payload["edition"] == "lite" else "complete")), account=payload["account"] or "-"),
             i18n.t("cli.status_repos", n=payload["repos"], active=payload["active"], queued=payload["queued"], fail=payload["failures_24h"], ok=payload["successes_24h"]),
             i18n.t("cli.status_allowance", remaining=rate.get("remaining", "-"), limit=rate.get("limit", "-")),
             i18n.t("cli.status_updated", when=payload["updated_local"] or "-")]
    if payload["listening"]:
        lines.append(i18n.t("cli.status_listening", where=i18n.t("cli.listening_" + payload["listening"])))
    attention = []      # what makes a monitor that answers "up but needs attention" (the operator scheme of the exit codes)
    if health.get("code_stale") is True:
        attention.append("code_stale")
        lines.append(i18n.t("cli.status_code_stale"))
    if data.get("paused_quota") is True:
        attention.append("quota_paused")
        lines.append(i18n.t("cli.status_quota_paused"))
    code = EXIT_OK
    if payload["credential"] == "blind":
        attention.append("blind")
        lines.append(i18n.t("cli.status_blind"))
        code = EXIT_AUTH
    if not data and not answer.get("error"):      # the monitor has not read GitHub yet: nothing to report is not "all right" (same as `health`)
        lines.append(i18n.t("cli.health_no_data"))
        attention.append("no_data")
        code = EXIT_DEGRADED
    if payload["offline"]:
        attention.append("offline")
        lines.append(i18n.t("cli.status_offline"))
        code = EXIT_DEGRADED
    if payload["error"]:
        attention.append("error")
        lines.append(i18n.t("cli.status_error", error=str(payload["error"])[:160]))
        code = EXIT_AUTH if answer.get("hint") == "auth" else EXIT_DEGRADED
    if status_scheme(ctx) == "operator":      # the document of the classic scheme is frozen (a golden test): the reasons only appear with the operator scheme
        payload["attention"] = attention
        code = EXIT_OPERATOR_ATTENTION if attention else EXIT_OK
    return payload, lines, code


def cmd_accounts(ctx):
    answer = fetch(ctx["base"], "/api/accounts", None, ctx["timeout"], ctx["token"])
    rows = answer.get("accounts") or []
    lines = [i18n.t("cli.accounts_head", n=len(rows))] + [f"  {a.get('id')}  {a.get('state', '-')}  {i18n.t('cli.accounts_row', repos=a.get('repos', '-'), running=a.get('running', '-'), failing=a.get('failing', '-'))}" for a in rows]
    if answer.get("listening") in ("this_computer", "network", "proxy"):
        lines.append(i18n.t("cli.status_listening", where=i18n.t("cli.listening_" + answer["listening"])))
    blind = [a.get("id") for a in rows if a.get("state") == "blind"]
    if blind:
        lines.append(i18n.t("cli.accounts_blind", accounts=", ".join(str(b) for b in blind)))
    return answer, lines, EXIT_AUTH if blind else EXIT_OK


def _since_text(seconds):
    """90 -> "90 s", 5400 -> "90 min", 86400 -> "24 h", 172800 -> "2 d": the length of a window as the person would say it."""
    for unit, size, floor in (("d", 86400, 172800), ("h", 3600, 3600), ("min", 60, 60)):
        if seconds % size == 0 and seconds >= floor:
            return f"{seconds // size} {unit}"
    return f"{seconds} s"


def cmd_alerts_since(ctx):
    """alerts --since LENGTH (90m, 24h, 7d): the alerts that were open at some moment of that time, the closed ones too, from the ledger the monitor keeps (it starts to fill when the monitor runs, so a
    young monitor cannot know older ones). Closing needs ten minutes of absence, so a restart does not close anything."""
    answer = fetch(ctx["base"], "/api/alerts", {"account": ctx["account"], "sentinel": ctx.get("sentinel"), "level": ctx.get("level"), "muted": "show", "since": ctx["since"]}, ctx["timeout"], ctx["token"])
    window = answer.get("since")
    if not isinstance(window, dict):      # a monitor older than this command ignores ?since= and would answer the current list: say so, never pass it off as the history
        raise CliError(EXIT_DEGRADED, i18n.t("cli.alerts_since_old"))
    if window.get("error"):
        raise CliError(EXIT_USAGE, i18n.t("cli.alerts_since_bad"))
    rows = window.get("alerts") or []
    lines = [i18n.t("cli.alerts_since_head", n=len(rows), since=_since_text(window.get("seconds") or 0))]
    for a in rows:
        mark = {"critical": "[CRIT]", "error": "[ERR ]", "warning": "[warn]", "info": "[info]"}.get(a.get("level"), "[    ]")
        end = i18n.t("cli.alerts_since_resolved", at=a["resolved_at"]) if a.get("resolved_at") else i18n.t("cli.alerts_since_open")
        lines.append(f"  {mark} {a.get('sentinel', '?'):<6} {a.get('code', '')}  {a.get('repo') or '-'}  {a.get('title', '')}  ({a.get('first_seen', '?')} - {end})")
    return {"since": window.get("seconds"), "alerts": rows}, lines, EXIT_OK


def cmd_alerts(ctx):
    if ctx.get("since"):
        return cmd_alerts_since(ctx)
    answer = fetch(ctx["base"], "/api/alerts", {"account": ctx["account"], "sentinel": ctx.get("sentinel"), "level": ctx.get("level"), "muted": ctx.get("muted")}, ctx["timeout"], ctx["token"])
    alerts = answer.get("alerts") or []
    lines = [i18n.t("cli.alerts_head", n=len(alerts))]
    for a in alerts:
        mark = {"critical": "[CRIT]", "error": "[ERR ]", "warning": "[warn]", "info": "[info]"}.get(a.get("level"), "[    ]")
        lines.append(f"  {mark} {a.get('sentinel', '?'):<6} {a.get('code', '')}  {a.get('repo') or '-'}  {a.get('title', '')}" + (f"  ({i18n.t('cli.alerts_muted', until=a['muted_until'])})" if a.get("muted_until") else ""))
    code = EXIT_OK
    wanted = ctx.get("fail_on")
    if wanted:
        worst = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        if any(worst.get(a.get("level"), 0) >= worst[wanted] and not a.get("muted_until") for a in alerts):
            code = EXIT_ALERTS
    return answer, lines, code


def _proposal_line(row):
    return f"  {row.get('id', '?')}  {row.get('status', '?'):<8} {row.get('repo') or '-':<22} {row.get('command', '')}  ({i18n.t('cli.proposals_left', s=row.get('expires_in_s', 0))})"


def cmd_proposals(ctx):
    """proposals list | show ID | approve ID | reject ID | execute ID: the actions the AI proposed (`ai.actions.enabled`), read from `/api/ai/actions`. approve and reject record the decision and run nothing;
    execute runs the proposal through the same door as the page (the exact command, `ai.actions.execute` on, a rate limit, a local log, and approved first when `ai.actions.require_approval` is on).
    approve, reject and execute are for this computer only. An id may be shortened to a prefix that names one proposal. 0 done; 1 wrong use; 4 the monitor refused or it could not be done."""
    action = ctx["action"] or "list"
    if action not in PROPOSALS_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.proposals_action"))
    answer = fetch(ctx["base"], "/api/ai/actions", None, ctx["timeout"], ctx["token"])
    rows = [r for r in (answer.get("proposals") or []) if isinstance(r, dict)]
    state = answer.get("state") if isinstance(answer.get("state"), dict) else {}
    if action == "list":
        lines = [i18n.t("cli.proposals_head", n=len(rows), approval=i18n.t("cli.proposals_approval_on" if state.get("require_approval") else "cli.proposals_approval_off"))]
        lines += [_proposal_line(r) for r in rows]
        return {"proposals": rows, "state": state}, lines, EXIT_OK
    wanted = (ctx.get("file") or "").strip()
    if not wanted:
        raise CliError(EXIT_USAGE, i18n.t("cli.proposals_need_id"))
    found = [r for r in rows if r.get("id") == wanted] or [r for r in rows if str(r.get("id", "")).startswith(wanted)]
    if len(found) != 1:
        raise CliError(EXIT_USAGE, i18n.t("cli.proposals_unknown" if not found else "cli.proposals_ambiguous", id=wanted))
    row = found[0]
    if action == "show":
        return {"proposal": row}, [_proposal_line(row), i18n.t("cli.proposals_detail", action=row.get("action", "?"), runnable=i18n.t("cli.yes" if row.get("runnable") else "cli.no"), by=row.get("by") or "-")], EXIT_OK
    if action in ("approve", "reject"):
        status, result = post_json(ctx["base"], "/api/ai/actions/review", {"id": row["id"], "decision": action, "by": "cli"}, ctx["timeout"], ctx["token"], guarded=True)
    else:
        status, result = post_json(ctx["base"], "/api/ai/actions/confirm", {"id": row["id"], "command": row.get("command")}, max(ctx["timeout"], 70.0), ctx["token"], guarded=True)
    if status in (401, 403):
        raise CliError(EXIT_AUTH, i18n.t("cli.proposals_refused", code=result.get("code") or result.get("error") or status))
    ok = status == 200 and result.get("ok") is True
    reason = str(result.get("reason") or result.get("error") or status)
    line = i18n.t("cli.proposals_done_" + action, id=row["id"]) if ok else i18n.t("cli.proposals_failed", id=row["id"], reason=i18n.t("cli.proposals_reason_" + reason) if reason in PROPOSAL_REASONS else reason)
    return {"action": action, "id": row["id"], "ok": ok, "reason": reason}, [line], EXIT_OK if ok else EXIT_DEGRADED


PROPOSAL_REASONS = ("off", "unknown", "expired", "mismatch", "rejected", "not_approved", "locked", "rate", "failed", "decided", "bad_decision")


def _signed(number):
    return f"{number:+g}"


def cmd_score(ctx):
    """score [--compare]: the score of the account, read from the same source as the page (`/api/score`). Read only. With --compare the history of the window is read too and the score is set
    against the oldest point of it. A score that does not exist yet (calibrating, not enough data, off) is not an error: exit 0 and the reason."""
    answer = fetch(ctx["base"], "/api/score", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    state = answer.get("state")
    account = answer.get("account") or ctx["account"] or "-"
    payload = dict(answer)
    if isinstance(answer.get("score"), (int, float)) and state == "scored":
        trend = answer.get("trend") or {}
        direction = trend.get("direction") if trend.get("direction") in ("up", "down", "flat", "unknown") else "unknown"
        words = i18n.t("cli.score_trend_" + direction, delta=abs(trend["delta"]) if isinstance(trend.get("delta"), (int, float)) else "")
        lines = [i18n.t("cli.score_head", account=account, score=answer["score"], letter=answer.get("letter") or "-", trend=words)]
    else:
        key = "cli.score_state_" + str(state) if state in ("calibrating", "insufficient_data", "off", "scored") else "cli.score_state_calibrating"
        lines = [i18n.t("cli.score_none", account=account, state=i18n.t(key))]
    quality = answer.get("data_quality") or {}
    if state != "off":
        lines.append(i18n.t("cli.score_coverage", coverage=round(float(answer.get("coverage") or 0) * 100), runs=quality.get("runs", 0), days=answer.get("window_days", "-")))
    for part in answer.get("parts") or []:
        name = i18n.t("cli.score_p_" + str(part.get("part"))) if part.get("part") in ("reliability", "speed", "recovery", "collaboration", "security") else str(part.get("part"))
        lines.append(i18n.t("cli.score_part", part=name, score=part["score"], weight=part.get("weight")) if isinstance(part.get("score"), (int, float)) else i18n.t("cli.score_part_none", part=name, weight=part.get("weight")))
    if answer.get("missing_parts"):
        lines.append(i18n.t("cli.score_missing", parts=", ".join(str(p) for p in answer["missing_parts"])))
    for repo in (answer.get("repos") or [])[:10]:
        lines.append(i18n.t("cli.score_repo", repo=repo.get("repo"), score=repo["score"], letter=repo.get("letter") or "-", runs=repo.get("runs", 0)) if isinstance(repo.get("score"), (int, float))
                     else i18n.t("cli.score_repo_none", repo=repo.get("repo"), state=repo.get("state"), runs=repo.get("runs", 0)))
    if answer.get("stale") and answer.get("age_seconds") is not None:
        lines.append(i18n.t("cli.score_stale", age=ago_text(answer["age_seconds"])))
    if ctx.get("compare"):
        hours = int(answer.get("window_days") or 7) * 24
        history = fetch(ctx["base"], "/api/score/history", {"account": ctx["account"], "hours": hours}, ctx["timeout"], ctx["token"])
        points = [p for p in history.get("points") or [] if isinstance(p.get("score"), (int, float))]
        if len(points) >= 2 and isinstance(answer.get("score"), (int, float)):
            scores = [p["score"] for p in points]
            delta = round(answer["score"] - points[0]["score"], 1)
            payload["compare"] = {"hours": hours, "from_score": points[0]["score"], "delta": delta, "lowest": min(scores), "highest": max(scores), "points": len(points)}
            lines.append(i18n.t("cli.score_compare", hours=hours, delta=_signed(delta), low=min(scores), high=max(scores), n=len(points)))
        else:
            payload["compare"] = None
            lines.append(i18n.t("cli.score_compare_none"))
    return payload, lines, EXIT_OK


COMPARE_FORMATS = ("table", "json", "ndjson", "csv")      # `compare` also writes csv; the other formats are in cli/formats.py


def cmd_compare(ctx):
    """compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]: this period against the one before (`/api/compare`). Read only, from what
    the monitor holds. Exit 0 when every figure could be compared, 4 when a figure has too little data, there is no baseline or the comparison is off, 5 with --fail-on when a figure got worse."""
    fmt = ctx.get("format") or "table"
    answer = fetch(ctx["base"], "/api/compare", {"account": ctx["account"], "window": ctx.get("window"), "days": ctx.get("days"), "baseline": ctx.get("baseline")}, ctx["timeout"], ctx["token"])
    if answer.get("enabled") is False:
        return answer, [i18n.t("cli.compare_off")], EXIT_DEGRADED
    wins = answer.get("windows") or {}
    metrics = answer.get("metrics") or {}
    code = EXIT_OK if answer.get("state") == "compared" and all(m.get("state") == "ok" for m in metrics.values()) else EXIT_DEGRADED
    if ctx.get("fail_on") and any(m.get("direction") == "worse" for m in metrics.values()):
        code = EXIT_ALERTS
    from github_actions_monitor.compare import metrics as compare_metrics
    if fmt in ("ndjson", "csv"):
        from github_actions_monitor.compare import compare_service
        return answer, compare_service.render(answer, fmt)[1].splitlines(), code
    now = wins.get("now") or {}
    end = tzdisplay.stamp(now["to"]) if isinstance(now.get("to"), (int, float)) else "-"
    lines = [i18n.t("cli.compare_head", account=answer.get("account") or ctx["account"] or "-", days=wins.get("days", "-"), end=end, baseline=i18n.t("ui.cmp_b_" + str(answer.get("baseline")))
                    if answer.get("baseline") in ("previous", "year_ago") else str(answer.get("baseline")))]
    if answer.get("state") in ("calibrating", "baseline_unavailable"):
        reason = ((answer.get("data_quality") or {}).get("reasons") or ["no_history"])[0]
        lines.append(i18n.t("ui.cmp_state_" + answer["state"], reason=i18n.t("ui.cmp_reason_" + reason) if reason in ("no_history", "watched_briefly", "history_too_short", "before_history") else reason))
    for name, entry in metrics.items():
        label = i18n.t("ui.cmp_m_" + name) if name in ("red_rate", "duration_p50", "resolution", "score_mean", "score_coverage") else name
        if entry.get("state") == "ok":
            delta = entry.get("delta")
            lines.append(i18n.t("cli.compare_row", metric=label, now=compare_metrics.humanize(name, entry.get("now")), base=compare_metrics.humanize(name, entry.get("base")),
                                delta=_signed(round(delta * 100, 1)) + " pts" if name in ("red_rate", "score_coverage") else (_signed(round(delta)) + " s" if name in ("duration_p50", "resolution") else _signed(delta)),
                                direction=i18n.t("ui.cmp_dir_" + str(entry.get("direction")))))
        else:
            lines.append(i18n.t("cli.compare_row_none", metric=label, state=i18n.t("ui.cmp_insufficient" if entry.get("state") == "insufficient_data" else "ui.cmp_unavailable")))
    changes = answer.get("changes") or {}
    for key, title in (("worse", "ui.cmp_ch_worse"), ("better", "ui.cmp_ch_better")):
        if changes.get(key):
            lines.append(i18n.t(title))
            lines.extend(i18n.t("cli.compare_change", repo=row["repo"], a=f"{row['red_rate_base'] * 100:.0f}%", b=f"{row['red_rate_now'] * 100:.0f}%") for row in changes[key])
    for key, title, field in (("new_failures", "ui.cmp_ch_new", "failures"), ("resolved_failures", "ui.cmp_ch_resolved", "failures_before")):
        if changes.get(key):
            lines.append(i18n.t(title))
            lines.extend(i18n.t("cli.compare_row_none", metric=f"{row['repo']} / {row['workflow']}", state=str(row.get(field, 0))) for row in changes[key])
    if changes.get("reason") == "no_data":
        lines.append(i18n.t("ui.cmp_ch_nodata"))
    return answer, lines, code


def cmd_team(ctx):
    """team [--severity warn|bad] [--repo OWNER/NAME]: the health of the repositories, ranked with the ones that need a person first (`/api/team/health`), or the detail of one repository
    (`/api/repos/<owner>/<repo>/health`). Read only, from what the monitor already holds; a repository that was not fully seen is said, never shown as healthy."""
    if ctx.get("repo"):
        owner, _, name = ctx["repo"].partition("/")
        if not owner or not name or "/" in name:
            raise CliError(EXIT_USAGE, i18n.t("cli.team_repo_bad"))
        answer = fetch(ctx["base"], f"/api/repos/{quote(owner, safe='')}/{quote(name, safe='')}/health", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
        view = answer["health"]
        ci, alerts = view["ci"], view["alerts"]
        lines = [i18n.t("cli.repo_head", repo=view["repo"], state=i18n.t("cli.team_state_" + view["state"]), risk=view["risk"]),
                 i18n.t("cli.repo_ci", ok=ci["successes_24h"], bad=ci["failures_24h"], red=", ".join(ci["red_workflows"]) or "-", stuck=ci["stuck_runs"]),
                 i18n.t("cli.repo_alerts", n=alerts["total"])]
        for item in alerts["items"][:10]:
            lines.append(f"  [{item.get('level', '?')}] {item.get('sentinel', '?')} {item.get('code', '')}  {item.get('title', '')}")
        if view.get("not_fully_seen"):
            lines.append(i18n.t("cli.repo_unseen", list=", ".join(view["not_fully_seen"])))
        return answer, lines, EXIT_OK
    answer = fetch(ctx["base"], "/api/team/health", {"account": ctx["account"], "severity": ctx.get("severity")}, ctx["timeout"], ctx["token"])
    totals = answer["totals"]
    lines = [i18n.t("cli.team_head", shown=answer["shown"], all=answer["all"], bad=totals.get("bad", 0), warn=totals.get("warn", 0), ok=totals.get("ok", 0), unknown=totals.get("unknown", 0))]
    if not answer["ranking"]:
        lines.append(i18n.t("cli.team_none"))
    for row in answer["ranking"][:20]:
        lines.append(i18n.t("cli.team_row", state=i18n.t("cli.team_state_" + row["state"]), risk=row["risk"], repo=row["repo"], alerts=row["alerts"], red=row["red_workflows"]))
    return answer, lines, EXIT_OK


def cmd_lessons(ctx):
    """lessons [list | brief | failures] [--repo NAME]: what the failures of this CI have taught (read only; the brief is the one to read before a push)."""
    action = ctx["action"] or "list"
    if action not in LESSONS_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.lessons_action"))
    if action == "brief":
        answer = fetch(ctx["base"], "/api/ai/lessons", {"fmt": "brief", "as": "json", "repo": ctx.get("repo")}, ctx["timeout"], ctx["token"])
        return answer, str(answer.get("text") or "").splitlines(), EXIT_OK
    if action == "close":
        answer = fetch(ctx["base"], "/api/ai/lessons", {"repo": ctx.get("repo")}, ctx["timeout"], ctx["token"])
        pending = [r for r in answer.get("categories") or [] if r.get("needs_guard")]
        lines = [i18n.t("cli.close_head", n=len(pending))] + [f"  {r.get('category', '?'):<16} {r.get('n7', 0)}/7d {', '.join(r.get('repos') or [])}" for r in pending]
        return {"pending": [r.get("category") for r in pending]}, lines, EXIT_ALERTS if pending else EXIT_OK
    if action == "failures":
        answer = fetch(ctx["base"], "/api/ai/failures", {"repo": ctx.get("repo"), "limit": 20}, ctx["timeout"], ctx["token"])
        rows = answer.get("failures") or []
        return answer, [i18n.t("cli.failures_head", n=len(rows))] + [f"  {r.get('category', '?'):<16} {r.get('repo', '-')}  {r.get('workflow', '')}  {r.get('root_cause', '')[:80]}" for r in rows], EXIT_OK
    answer = fetch(ctx["base"], "/api/ai/lessons", {"repo": ctx.get("repo")}, ctx["timeout"], ctx["token"])
    rows = answer.get("categories") or []
    lines = [i18n.t("cli.lessons_head", n=len(rows))]
    for row in rows:
        lesson = row.get("lesson") or {}
        lines.append(f"  {row.get('category', '?'):<16} {row.get('n24', 0)}/24h {row.get('n7', 0)}/7d {row.get('trend', '')}  {lesson.get('do', '')}")
    return answer, lines, EXIT_OK


def cmd_screens(ctx):
    """screens [list | urls]: the Screens menu of the page, from `/api/screens/menu`: every kind of screen (the page, kiosks, tab screens, the wall screens, the TV, a set of monitors) and whether it can be opened here.
    `urls` prints the full address of each one (the address of the monitor plus its path and default parameters), ready to paste into a kiosk command. Read only: it opens nothing and carries no token."""
    action = ctx["action"] or "list"
    if action not in SCREENS_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.screens_action"))
    answer = fetch(ctx["base"], "/api/screens/menu", None, ctx["timeout"], ctx["token"])
    rows = answer.get("entries") or []
    lines = [i18n.t("cli.screens_head", n=len(rows), wall=i18n.t("cli.screens_wall_on" if answer.get("wall_enabled") else "cli.screens_wall_off"))]
    base = str(ctx["base"]).rstrip("/")
    for row in rows:
        mark = "" if row.get("available", True) else "(-) "
        lines.append(f"  {row.get('id', '?'):<13} {mark}{(base + row.get('url', '')) if action == 'urls' else row.get('path', '')}")
    return answer, lines, EXIT_OK


def cmd_toolbox(ctx):
    """toolbox limits [N] | workspaces | ledger [--force] | summary | export-events FILE: the small tools of the operator that work on this computer, with no monitor running.
    `limits` puts the setup against its ceilings (N = the number of repositories; without it the one of the last picture); `workspaces` lists the workspaces and the one in use; `ledger` shows the
    ledger of notifications already sent (`--force` forgets it); `summary` counts the events of the events file by kind, repository and day; `export-events FILE` writes them as jsonl, csv, parquet
    or duckdb by the end of the name of FILE (parquet and duckdb need their package; the file must be new). Nothing is sent anywhere and nothing is read from GitHub."""
    from github_actions_monitor.app import toolconfig, workspace
    from github_actions_monitor.data_pipeline import events as events_mod, limits
    from github_actions_monitor.integrations import event_export, notify_dedupe
    action, config = ctx["action"], toolconfig.raw_config()
    if action not in TOOLBOX_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.toolbox_action"))
    if action == "limits":
        repos = int(ctx["file"]) if str(ctx["file"]).isdigit() else None
        if repos is None:
            from github_actions_monitor.ops import checks
            status, detail = checks.capacity(config)
            return {"ok": status != "fail", "status": status, "detail": detail}, [f"capacity: {status} ({detail})"], EXIT_OK if status != "fail" else EXIT_DEGRADED
        rows = limits.planned(config, repos)
        status, detail = limits.verdict(rows)
        return {"ok": status != "fail", "status": status, "repos": repos, "rows": rows}, [f"{r['id']}: {r['used']} / {r['limit']} ({r['percent']} %, {r['level']})" for r in rows], EXIT_OK if status != "fail" else EXIT_DEGRADED
    if action == "workspaces":
        info = workspace.describe(config)
        lines = [f"{'*' if w['active'] else ' '} {w['name']}{'' if w['folder_exists'] else ' (folder missing)'}" for w in info["workspaces"]] or ["-"]
        return info, lines, EXIT_OK
    if action == "ledger":
        stats = notify_dedupe.stats()
        if ctx["force"]:
            try:
                Path(notify_dedupe.LEDGER_FILE).unlink()
            except OSError:
                pass
            notify_dedupe.reset()
            return {"ok": True, "cleared": True}, [i18n.t("cli.toolbox_ledger_cleared")], EXIT_OK
        return stats, [f"{k}: {v}" for k, v in stats.items()], EXIT_OK
    rows = event_export.read_events(events_mod.EVENTS_FILE)
    if action == "summary":
        report = event_export.summary(rows)
        lines = [f"events: {report['events']}", f"first: {report['first']}", f"last: {report['last']}"] + [f"kind {k}: {v}" for k, v in report["by_kind"].items()] + [f"repo {k}: {v}" for k, v in list(report["by_repo"].items())[:10]]
        return report, lines, EXIT_OK
    if not ctx["file"]:
        raise CliError(EXIT_USAGE, i18n.t("cli.toolbox_dest"))
    suffix = str(ctx["file"]).rsplit(".", 1)[-1].lower() if "." in str(ctx["file"]) else ""
    fmt = {"jsonl": "jsonl", "csv": "csv", "parquet": "parquet", "duckdb": "duckdb", "db": "duckdb"}.get(suffix)
    if fmt is None:
        raise CliError(EXIT_USAGE, i18n.t("cli.toolbox_dest"))
    try:
        done = event_export.write(rows, ctx["file"], fmt)
    except event_export.ExportError as error:
        raise CliError(EXIT_USAGE, i18n.t("cli.toolbox_failed", reason=str(error))) from None
    return {"ok": True, **done}, [i18n.t("cli.toolbox_exported", rows=done["rows"], file=done["file"], format=fmt)], EXIT_OK


def cmd_briefs(ctx):
    """briefs [index | show TAB | all]: the catalogued briefs the AI tools read, one per tab of the page (`/api/ai/index` and `/api/ai/briefs`). Read only, the same in both editions; the monitor cleans
    every text and a brief carries no secret. `index` lists them, `show TAB` prints the signals of one tab, `all` prints every brief in one document."""
    action = ctx["action"] or "index"
    if action not in BRIEFS_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.briefs_action"))
    lang = i18n.language()
    if action == "index":
        answer = fetch(ctx["base"], "/api/ai/index", {"lang": lang}, ctx["timeout"], ctx["token"])
        rows = answer.get("briefs") or []
        lines = [i18n.t("cli.briefs_head", n=len(rows), edition=answer.get("edition") or "-")]
        for row in rows:
            lines.append(f"  {row.get('tab', '?'):<12} {'' if row.get('available', True) else '(-) '}{row.get('title', '')}  [{row.get('kind', '')}]")
        return answer, lines, EXIT_OK
    if action == "all":
        answer = fetch(ctx["base"], "/api/ai/briefs", {"tab": "all", "lang": lang}, ctx["timeout"], ctx["token"])
        rows = answer.get("briefs") or []
        return answer, [i18n.t("cli.briefs_head", n=len(rows), edition=answer.get("edition") or "-")] + [f"  {r.get('tab', '?'):<12} {len(r.get('signals') or [])} {i18n.t('cli.briefs_signals')}" for r in rows], EXIT_OK
    tab = (ctx.get("file") or "").strip()
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", tab):
        raise CliError(EXIT_USAGE, i18n.t("cli.briefs_tab_needed"))
    try:
        answer = fetch(ctx["base"], "/api/ai/briefs", {"tab": tab, "lang": lang}, ctx["timeout"], ctx["token"])
    except CliError as error:
        if error.code == EXIT_DEGRADED:      # the monitor answers 404 for a tab that does not exist
            raise CliError(EXIT_USAGE, i18n.t("cli.briefs_unknown_tab", tab=tab)) from None
        raise
    lines = [f"{answer.get('title', tab)} [{answer.get('tab_kind', '')}]"]
    for signal in answer.get("signals") or []:
        lines.append(f"  {str(signal.get('level', '')):<6} {signal.get('id', '?')}  {signal.get('summary') or ''}")
    if not answer.get("signals"):
        lines.append("  " + i18n.t("cli.briefs_none"))
    return answer, lines, EXIT_OK


def _guide_names():
    """The guides of docs/ that travel with this version (the English file names, without the suffix of a language), sorted."""
    from github_actions_monitor.util import paths
    tails = tuple(t for t in DOCS_TAIL.values() if t)
    return sorted(f.stem for f in paths.DOCS.glob("*.md") if not f.stem.endswith(tails))


def _guide_title(path):
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                return line.lstrip("# ").strip()
    except OSError:
        pass
    return ""


def cmd_docs(ctx):
    """docs [list | show NAME]: the guides of docs/ that come with THIS version, read from the installation (no monitor running, nothing from the network), in the language of the command (the English
    text when a guide is not translated). `list` names them with their title, `show NAME` prints one (the name is the file without .md, in any case). A mistake in any command points here with its `help`."""
    from github_actions_monitor.tool_version import TOOL_VERSION as version
    from github_actions_monitor.util import paths
    action = ctx["action"] or "list"
    if action not in DOCS_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.docs_action"))
    lang = i18n.language()
    names = _guide_names()
    if action == "list":
        rows = [{"name": n, "title": _guide_title(paths.DOCS / (n + DOCS_TAIL.get(lang, "") + ".md")) or _guide_title(paths.DOCS / (n + ".md"))} for n in names]
        return {"ok": True, "version": version, "lang": lang, "count": len(rows), "docs": rows}, [i18n.t("cli.docs_head", n=len(rows), version=version)] + [f"  {r['name']:<22} {r['title']}" for r in rows], EXIT_OK
    wanted = (ctx.get("file") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", wanted):
        raise CliError(EXIT_USAGE, i18n.t("cli.docs_name_needed"), i18n.t("cli.docs_help_list"))
    found = next((n for n in names if n.lower() == wanted.lower()), "")
    if not found:
        raise CliError(EXIT_USAGE, i18n.t("cli.docs_unknown", name=wanted), i18n.t("cli.docs_help_list"))
    path = paths.DOCS / (found + DOCS_TAIL.get(lang, "") + ".md")
    shown = lang if path.is_file() else "en"
    if shown == "en":
        path = paths.DOCS / (found + ".md")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise CliError(EXIT_DEGRADED, i18n.t("cli.docs_unreadable", name=found), i18n.t("cli.docs_help_list")) from None
    return {"ok": True, "version": version, "lang": shown, "name": found, "title": _guide_title(path), "text": text}, text.rstrip("\n").split("\n"), EXIT_OK


def _contract_check(ctx):
    """api contract-check: the contract suite for clients (tools/api_contract_suite.py, only reads) against the monitor of this command line. Exit 0 when every check passes, 4 when one fails."""
    from github_actions_monitor.app import api_spec
    module = api_spec.contract_suite()
    if module is None:
        raise CliError(EXIT_USAGE, i18n.t("cli.api_no_suite"))
    try:
        report = module.run(module.Client(ctx["base"], ctx["token"], ctx["timeout"]))
    except OSError:
        raise CliError(EXIT_DOWN, i18n.t("cli.unreachable", url=ctx["base"])) from None
    failed = report.failed
    lines = [("PASS " if row["ok"] else "FAIL ") + row["check"] + ("" if row["ok"] else ": " + row["detail"]) for row in report.rows]
    lines.append(i18n.t("cli.api_suite_total", ok=len(report.rows) - len(failed), n=len(report.rows)))
    return api_spec.suite_summary(report), lines, EXIT_DEGRADED if failed else EXIT_OK


def cmd_api(ctx):
    """api [openapi | me | contract-check]: the read API for clients (`/api/v1/`, see docs/API.md). `openapi` prints the OpenAPI document of every frozen route (redirect it to a file); `me` says who the monitor takes this
    client for (mode, user, role and what the session may do); `contract-check` runs the contract suite for clients against it. Read only; a monitor whose API is closed (`api.v1_enabled`) is told in one line."""
    action = ctx["action"] or "me"
    if action not in API_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.api_action"))
    if action == "contract-check":
        return _contract_check(ctx)
    try:
        answer = fetch(ctx["base"], "/api/v1/openapi.json" if action == "openapi" else "/api/v1/me", {"lang": i18n.language()} if action == "me" else None, ctx["timeout"], ctx["token"])
    except CliError as error:
        if error.code == EXIT_DEGRADED:      # the monitor answers 404 while the prefix is closed
            raise CliError(EXIT_DEGRADED, i18n.t("cli.api_closed")) from None
        raise
    if action == "openapi":
        return answer, [json.dumps(answer, ensure_ascii=False, indent=1)], EXIT_OK
    can = answer.get("capabilities") or {}
    line = i18n.t("cli.api_me", mode=answer.get("mode") or "-", user=answer.get("user") or "-", role=answer.get("role") or "-", contract=answer.get("contract") or "-")
    return answer, [line, i18n.t("cli.api_can", things=", ".join(k for k in ("read", "write", "admin") if can.get(k)) or "-")], EXIT_OK


def _post_ai(ctx, path, payload):
    """One local-only POST of the AI models family; 403 = the monitor refuses (not this computer or no token), 404 = this monitor has no such route."""
    status, answer = post_json(ctx["base"], path, payload, max(ctx["timeout"], 30.0), ctx["token"])
    if status in (401, 403):
        raise CliError(EXIT_AUTH, i18n.t("cli.refused", code=answer.get("code") or status))
    if status == 404:
        raise CliError(EXIT_DEGRADED, i18n.t("cli.not_here", path=path))
    return answer


def cmd_ai(ctx):
    """ai models [--refresh] | ai test --provider X --model Y | ai doctor: the models of the AI provider, the test of one model with a synthetic text, and why an AI does not answer (never prints a key)."""
    action = ctx["action"]
    if action not in AI_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.ai_action"))
    body = {k: ctx[k] for k in ("provider", "model") if ctx.get(k)}
    if action == "models":
        note = ""
        if ctx.get("refresh"):
            done = _post_ai(ctx, "/api/ai/models/refresh", body)
            note = done.get("message") or (i18n.t("cli.ai_refreshed", n=done.get("count", 0)) if done.get("ok") else "")
        answer = fetch(ctx["base"], "/api/ai/models", None, ctx["timeout"], ctx["token"])
        rows = answer.get("models") or []
        unknown = i18n.t("cli.ai_unknown")
        lines = [i18n.t("cli.ai_models_head", provider=answer.get("label") or answer.get("provider"), model=answer.get("model") or "-", n=len(rows))]
        if note:
            lines.append(note)
        lines.append((answer.get("check") or {}).get("message") or "")
        for row in rows[:60]:
            lines.append(f"  {row.get('id', '?'):<44} {i18n.t('cli.ai_ctx')} {row.get('context') or unknown}  {i18n.t('cli.ai_in')} {unknown if row.get('in_per_mtok') is None else row['in_per_mtok']}  "
                         f"{i18n.t('cli.ai_out')} {unknown if row.get('out_per_mtok') is None else row['out_per_mtok']}")
        if len(rows) > 60:
            lines.append(i18n.t("cli.ai_more", n=len(rows) - 60))
        if not rows:
            lines.append(i18n.t("cli.ai_no_list"))
        return answer, [line for line in lines if line], EXIT_OK
    if action == "test":
        answer = _post_ai(ctx, "/api/ai/models/test", body)
        if answer.get("ok"):
            cost = answer.get("cost")
            lines = [i18n.t("cli.ai_test_ok", provider=answer.get("provider"), model=answer.get("model"), ms=answer.get("ms"), tin=answer.get("tokens_in"), tout=answer.get("tokens_out"),
                            est=i18n.t("cli.ai_estimated") if answer.get("tokens_estimated") else "", cost=i18n.t("cli.ai_unknown") if cost is None else cost, at=answer.get("tested_at")), answer.get("answer") or ""]
            return answer, lines, EXIT_OK
        return answer, [i18n.t("cli.ai_test_fail", error=answer.get("error") or "?")], EXIT_DEGRADED
    answer = _post_ai(ctx, "/api/ai/doctor", body)
    lines = [i18n.t("cli.ai_doctor_" + ("ok" if answer.get("ok") else "head"))] + [f"  [{'ok' if c.get('ok') else '!!'}] {c.get('text', '')}" for c in answer.get("checks") or []]
    return answer, lines, EXIT_OK if answer.get("ok") else EXIT_DEGRADED


def cmd_install_skill(ctx):
    """install-skill internal|external --dest FOLDER: copies a skill of the monitor to the folder an AI tool reads its skills from. Works without a running monitor; never overwrites a file that differs."""
    from github_actions_monitor.integrations import skills
    name = ctx["action"]
    if name not in SKILL_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.skill_action"))
    result = skills.install(name, ctx.get("dest"))
    if result["error"] == "dest" or (not ctx.get("dest")):
        raise CliError(EXIT_USAGE, i18n.t("cli.skill_dest"))
    lines = [i18n.t("cli.skill_done", n=len(result["written"]), same=len(result["same"]), kept=len(result["kept"]), dest=result["dest"])]
    lines += [f"  {i18n.t('cli.skill_kept')}: {f}" for f in result["kept"]]
    return result, lines, EXIT_OK if result["ok"] else EXIT_DEGRADED


def cmd_gh_token(ctx):
    """gh-token --read-only: prints a one-hour installation token of the GitHub App of the monitor, so that the reads of a tool (a `gh` of an agent) spend the allowance of the App and not the one of the
    user. Only with github_app.share_reads on (off by default). The token goes to the standard output and nowhere else: never to a file or a log. Run it without --json."""
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.integrations import github_app
    config = toolconfig.raw_config()
    if not ctx.get("read_only"):
        raise CliError(EXIT_USAGE, i18n.t("cli.gh_token_flag"))
    if not github_app.settings(config)["share_reads"]:
        raise CliError(EXIT_AUTH, i18n.t("cli.gh_token_off"))
    value, reason = github_app.shared_token(config)      # asked apart, for read permissions only; a token that could write is refused
    if reason == "not_read_only":
        raise CliError(EXIT_AUTH, i18n.t("cli.gh_token_not_read_only"))
    if not value:
        raise CliError(EXIT_DEGRADED, i18n.t("cli.gh_token_none"))
    return {"ok": True}, [value], EXIT_OK


def cmd_live(ctx):
    events = fetch(ctx["base"], "/api/live-events", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    status = fetch(ctx["base"], "/api/live-status", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    rows = events.get("events") or []
    lines = [i18n.t("cli.live_head", state=i18n.t("cli.live_on" if status.get("enabled") else "cli.live_off"), n=len(rows))]
    for e in rows[:20]:
        lines.append(f"  {e.get('at', '')}  {e.get('repo', '')}  {e.get('name') or e.get('workflow') or e.get('event') or ''}  {e.get('status', '')} {e.get('conclusion') or ''}".rstrip())
    return {"webhook": {k: status.get(k) for k in ("enabled", "active", "secret_ok", "stats", "last")}, "events": rows}, lines, EXIT_OK


def cmd_doctor(ctx):
    from github_actions_monitor.cli import doctor
    from github_actions_monitor.app import toolconfig
    edition = "lite" if ctx.get("lite") else "complete"
    config = toolconfig.raw_config()
    if ctx.get("egress"):      # `doctor --egress`: the hosts this configuration can call and what fails if they are blocked (no check is run, nothing is called)
        from github_actions_monitor.ops import egress
        rows = egress.table(config)
        return {"egress": rows, "airgapped": config.get("airgapped") is True}, egress.lines(config, i18n.t), EXIT_OK
    if getattr(ctx.get("args"), "doctor_release", ""):      # `doctor --verify-release DIR`: the signed files of a release against this installation, nothing else is checked
        from github_actions_monitor.families.supply import commands
        return commands.doctor_release(ctx["args"].doctor_release)
    try:
        checks = doctor.run(config=config, edition=edition)
    except Exception:      # noqa: BLE001 - the doctor itself could not run: its own exit code, not a traceback
        return {"ok": False, "exit": doctor.EXIT_DOCTOR_ERROR}, [i18n.t("doctor.broken")], doctor.EXIT_DOCTOR_ERROR
    if ctx.get("latency"):      # `doctor --latency`: reads only, the delay between a push and its run in the events of the account (a failed read is "not evaluable", never a defect)
        checks = list(checks) + [doctor.latency_check(doctor.default_runner, config)]
    strict = bool(ctx.get("strict")) or doctor.strict_from(config)
    return doctor.as_json(checks, edition, strict), doctor.text(checks, i18n.t, edition).rstrip("\n").split("\n"), doctor.exit_code(checks, strict)


def cmd_backup(ctx):
    """backup create [FILE] [--account ID] | verify FILE [--deep] | restore FILE [--account ID] [--to-dir DIR] [--force] | status | list: the complete package of this installation. They work on the folder, so no monitor is needed
    (and a monitor that is running is not touched; restore asks for it to be stopped). Exit 0 when it is done, 1 when it is refused or the package does not verify."""
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.ops import bundle, opsconf, restore, schedule
    action, config = ctx["action"], toolconfig.raw_config()
    if action not in BACKUP_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.backup_action"))
    if action in ("verify", "restore") and not ctx["file"]:
        raise CliError(EXIT_USAGE, i18n.t("cli.backup_file"))
    env_name = ctx["key_env"] or None
    try:
        if action == "create":
            state = schedule.run_locked(config, dest=ctx["file"] or None, encrypt=True if ctx["encrypt"] else None, key_env=env_name, account=ctx["account"] or None)
            if not state["ok"]:
                return {"ok": False, "error": state["error"]}, [i18n.t("ops.err." + state["error"], detail=state.get("detail", ""))], EXIT_USAGE
            where = (Path(ctx["file"]) if ctx["file"] else opsconf.backup_dir(config) / state["file"]).as_posix()
            return {"ok": True, **state}, [i18n.t("ops.created_sealed" if state["sealed"] else "ops.created", file=where, accounts=state["accounts"], events=state["events"], size=_size(state["bytes"]))], EXIT_OK
        if action == "verify":
            problems = bundle.verify(ctx["file"], env_name, config=config)
            if not problems and ctx["deep"]:
                problems = restore.deep_verify(ctx["file"], config, env_name)
            if problems:
                return {"ok": False, "problems": problems}, [i18n.t("ops.verify_bad", why="; ".join(problems[:3]))], EXIT_USAGE
            return {"ok": True, "deep": ctx["deep"]}, [i18n.t("ops.deep_ok" if ctx["deep"] else "ops.verify_ok")], EXIT_OK
        if action == "restore":
            report = restore.restore(ctx["file"], config, account=ctx["account"] or None, to_dir=ctx["to_dir"] or None, force=ctx["force"], key_env=env_name)
            lines = [i18n.t("ops.restored", accounts=report["accounts"], events=report["events"], written=len(report["files"]["written"]), skipped=len(report["files"]["skipped"]))]
            if report["verify"]:
                lines.append(i18n.t("ops.verify_bad", why="; ".join(report["verify"][:3])))
            lines.append(i18n.t("ops.todo_head"))
            lines += ["  - " + i18n.t("ops.todo." + code, n=report["config_omitted"], names=", ".join(report["files"]["skipped"])) for code in report["todo"]]
            return {"ok": not report["verify"], **report}, lines, EXIT_OK if not report["verify"] else EXIT_USAGE
        if action == "status":
            state, cfg = schedule.read_status(), opsconf.settings(config)["backup"]
            age = schedule.age_days()
            schedule_text = i18n.t("ops.sched_on", hours=cfg["interval_hours"], keep=cfg["keep"]) if cfg["enabled"] else i18n.t("ops.sched_off")
            if not state["last_ok"]:
                lines = [i18n.t("ops.status_none")]
            else:
                lines = [i18n.t("ops.status_line", at=state["last_ok"], age=i18n.t("ops.age_days", n="%.1f" % age), file=state["file"], size=_size(state["bytes"]), schedule=schedule_text)]
            if state["ok"] is False:
                lines.append(i18n.t("ops.status_failed", at=state["last_attempt"], why=i18n.t("ops.err." + (state["error"] or "failed"), detail="")))
            return {"schedule": cfg, **state, "age_days": age}, lines, EXIT_OK
        rows = schedule.list_backups(config)
        folder = opsconf.backup_dir(config).as_posix()
        lines = [i18n.t("ops.list_head", n=len(rows), dir=folder)] + [f"  {row['name']}  {_size(row['bytes'])}  {row['at']}" for row in rows] if rows else [i18n.t("ops.list_none", dir=folder)]
        return {"dir": folder, "backups": rows}, lines, EXIT_OK
    except bundle.OpsError as error:
        return {"ok": False, "error": error.code}, [i18n.t("ops.err." + error.code, detail=error.detail)], EXIT_USAGE


def _size(count):
    return "%.1f MB" % (count / 1048576) if count >= 1048576 else "%d KB" % max(1, count // 1024)


def deep_health(ctx):
    """The deep check of the monitor (`GET /api/health?deep=1`) with the session of this command: (exit code, text, document). 4 when the supervisor or the refresh cycle of an account is stuck."""
    from github_actions_monitor.cli import healthcheck
    asked = {"account": ctx["account"]} if ctx["account"] else {}
    request = urllib.request.Request(ctx["base"] + "/api/health?deep=1" + ("&" + urlencode(asked) if asked else ""), headers=request_headers(ctx["token"]))
    try:
        with open_url(request, ctx["timeout"]) as answer:
            status, body = answer.status, answer.read(1_000_000)
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read(1_000_000)
        error.close()
    except (urllib.error.URLError, OSError, ValueError):
        return EXIT_DOWN, i18n.t("healthcheck.unreachable"), None
    try:
        document = json.loads(body.decode("utf-8"))
    except ValueError:
        document = None
    document = document if isinstance(document, dict) else None
    code, text = healthcheck.judge(status, document)
    return {healthcheck.EXIT_OK: EXIT_OK, healthcheck.EXIT_UNHEALTHY: EXIT_DEGRADED, healthcheck.EXIT_DOWN: EXIT_DOWN, healthcheck.EXIT_REFUSED: EXIT_AUTH}[code], text, document


def cmd_health(ctx):
    """Reachable? accepted? does the credential of GitHub answer? Reads only what is needed, in this order, and stops at the first failure. With --deep it asks the deep check first."""
    out = {"monitor": "unreachable", "access": None, "github": None, "allowance": None, "exit": EXIT_DOWN}
    lines = []
    if ctx.get("deep"):
        code, text, document = deep_health(ctx)
        out.update({"deep": document, "exit": code})
        lines.append(text)
        if code != EXIT_OK:
            out["monitor"] = "unreachable" if code == EXIT_DOWN else ("refused" if code == EXIT_AUTH else "unhealthy")
            return out, lines, code
        if isinstance(document, dict) and document.get("supervisor") and not ctx["account"]:      # the supervisor of several accounts answers for all of them: there is no single account to read after it
            out["monitor"] = "ok"
            return out, lines, EXIT_OK
    try:
        health = fetch(ctx["base"], "/api/health", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    except CliError as error:
        out["exit"] = error.code
        out["monitor"] = "refused" if error.code == EXIT_AUTH else "unreachable"
        out["access"] = False if error.code == EXIT_AUTH else None
        return out, [i18n.t("cli.health_monitor_bad", reason=error.text)], error.code
    out.update({"monitor": "ok", "access": True, "version": health.get("version")})
    lines.append(i18n.t("cli.health_monitor_ok", version=health.get("version"), uptime=ago_text(health.get("uptime_seconds"))))
    try:
        answer = fetch(ctx["base"], "/api/data", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    except CliError as error:
        out["exit"] = error.code
        return out, lines + [i18n.t("cli.health_data_bad", reason=error.text)], error.code
    data = answer.get("data") or {}
    rate = data.get("rate") or {}
    remaining = rate.get("remaining")
    out["allowance"] = {"remaining": remaining, "limit": rate.get("limit")}
    if answer.get("error") and answer.get("hint") == "auth":      # the login of GitHub is the problem: not the same as an allowance that ran out
        out.update({"github": "credential_failed", "exit": EXIT_AUTH})
        return out, lines + [i18n.t("cli.health_github_auth")], EXIT_AUTH
    if data.get("paused_quota") or (isinstance(remaining, int) and remaining <= 0):
        out.update({"github": "rate_limited", "exit": EXIT_DEGRADED})
        return out, lines + [i18n.t("cli.health_github_rate", remaining=remaining if remaining is not None else "-")], EXIT_DEGRADED
    if (data.get("offline") or {}).get("offline") or answer.get("error"):
        out.update({"github": "unreachable", "exit": EXIT_DEGRADED})
        return out, lines + [i18n.t("cli.health_github_offline")], EXIT_DEGRADED
    if not data:
        out.update({"github": "no_data_yet", "exit": EXIT_DEGRADED})
        return out, lines + [i18n.t("cli.health_no_data")], EXIT_DEGRADED
    out.update({"github": "ok", "exit": EXIT_OK})
    return out, lines + [i18n.t("cli.health_github_ok", remaining=remaining if remaining is not None else "-")], EXIT_OK


def cmd_ai_hook(ctx):
    """`ai-hook install|status|uninstall`: local, no monitor needed. The --json answer is plain ASCII (see main)."""
    from github_actions_monitor.integrations import ai_hook_install as hook
    action = ctx.get("action") or "status"
    try:
        if action == "status":
            from github_actions_monitor.integrations import ai_alerts
            from github_actions_monitor.app import toolconfig
            report = hook.status(ctx.get("project_dir") or None)
            report["presence"] = ai_alerts.presence(toolconfig.raw_config())
            lines = [i18n.t("cli.aih_state_on" if report["installed"] else "cli.aih_state_off")]
            for row in report["targets"]:
                if row["events"] or row["error"]:
                    lines.append(i18n.t("cli.aih_row", target=row["target"], scope=row["scope"], events=", ".join(row["events"]) or "-", file=row["file"]) + (f" [{row['error']}]" if row["error"] else ""))
            cfg = report["settings"]
            lines.append(i18n.t("cli.aih_settings", enabled=i18n.t("ui.yes" if cfg["enabled"] else "ui.no"), block=i18n.t("ui.yes" if cfg["block_on_stop"] else "ui.no"), minutes=cfg["cooldown_minutes"]))
            seen = report["presence"]
            lines.append(i18n.t("cli.aih_last_read", via=seen["via"], ago=ago_text(seen["age_seconds"])) if seen.get("last_at") else i18n.t("cli.aih_never"))
            return report, lines, EXIT_OK
        target = ctx.get("target") or "assistant"
        scope = ctx.get("scope") or "project"
        if action == "install":
            report = hook.install(target, scope, ctx.get("project_dir") or None, dry_run=ctx.get("dry_run", False))
        else:
            report = hook.uninstall(target, scope, ctx.get("project_dir") or None, dry_run=ctx.get("dry_run", False))
    except hook.InstallError as error:
        raise CliError(EXIT_USAGE, i18n.t("cli.aih_error", reason=str(error))) from None
    lines = [i18n.t("cli.aih_" + report["action"], target=report["target"], scope=report["scope"] or "-", file=report["file"] or "-")]
    if report["action"] == "printed":
        lines.append(i18n.t("cli.aih_generic"))
        lines.extend(f"  {event}: {command}" for event, command in report["commands"].items())
    if report.get("backup"):
        lines.append(i18n.t("cli.aih_backup", file=report["backup"]))
    if action == "install" and report["action"] != "printed":
        lines.append(i18n.t("cli.aih_next"))
    return report, lines, EXIT_OK


def read_new_token(path):
    """The token for `credential replace`: the first line of a file, or of the standard input for `-`. Never a command line flag (it would show in the list of processes). CliError(1) if there is none."""
    try:
        if path == "-":
            buffer = getattr(sys.stdin, "buffer", None)      # the bytes, so the BOM that PowerShell puts in front of a piped text is dropped whatever the code page of the console is
            line = buffer.readline().decode("utf-8-sig", "replace") if buffer is not None else sys.stdin.readline().lstrip(chr(0xFEFF))
        else:
            with open(path, "r", encoding="utf-8-sig") as handle:
                line = handle.readline()
    except (OSError, UnicodeError):
        raise CliError(EXIT_USAGE, i18n.t("cli.token_file_bad", file=path)) from None
    if not line.strip():
        raise CliError(EXIT_USAGE, i18n.t("cli.token_file_bad", file=path))
    return line.strip()


def cmd_credential(ctx):
    """`credential replace|reload [--account ID] [--new-token-file FILE|-]`: another login of GitHub for one account, while everything runs. 0 done; 3 the monitor refuses you; 4 GitHub refused the new token
    (nothing changed) or the monitor could not do it."""
    action = ctx.get("action") or ""
    if action not in CREDENTIAL_ACTIONS:
        raise CliError(EXIT_USAGE, i18n.t("cli.credential_usage"))
    payload = {"action": action}
    if action == "replace":
        if not ctx.get("new_token_file"):
            raise CliError(EXIT_USAGE, i18n.t("cli.credential_needs_file"))
        payload["token"] = read_new_token(ctx["new_token_file"])
    accounts_path = "/api/accounts/%s/credential" % ctx["account"] if ctx["account"] else None
    health = fetch(ctx["base"], "/api/health", None, ctx["timeout"], ctx["token"])
    path = accounts_path if health.get("supervisor") and accounts_path else ("/api/credential" if not health.get("supervisor") else None)
    if path is None:
        raise CliError(EXIT_USAGE, i18n.t("cli.credential_needs_account"))
    status, answer = post_json(ctx["base"], path, payload, max(ctx["timeout"], 30.0), ctx["token"], guarded=True)
    shown = {k: v for k, v in answer.items() if k != "token"}      # an answer never carries the token, and this command does not print one in any case
    if status in (401, 403):
        raise CliError(EXIT_AUTH, i18n.t("cli.credential_refused", code=answer.get("code") or answer.get("status") or status))
    if status == 404:
        raise CliError(EXIT_DEGRADED, i18n.t("cli.credential_unknown"))
    result = str(answer.get("status") or "")
    ok = status == 200 and answer.get("ok") is True
    line = i18n.t("cli.credential_" + ("done" if ok else "failed"), status=i18n.t("cli.credential_status_" + result) if result else str(status))
    return {"action": action, "ok": ok, **shown}, [line], EXIT_OK if ok else EXIT_DEGRADED


def _config():
    """The configuration of this computer as a dictionary ({} when it cannot be read): the command line works without a monitor, so this is read from the file, never asked of the server."""
    try:
        from github_actions_monitor.app import toolconfig
        raw = toolconfig.raw_config()
        return raw if isinstance(raw, dict) else {}
    except Exception:      # noqa: BLE001 - a configuration that cannot be read is the defaults, not a traceback
        return {}


def cmd_completions(ctx):
    """completions bash|zsh|fish|powershell: prints the script that completes this command line, written from its real parser. Needs no monitor and writes nothing."""
    shell = ctx["action"]
    if shell not in completions.SHELLS:
        raise CliError(EXIT_USAGE, i18n.t("cli.completions_usage"))
    text = completions.script(shell, build_parser(), WORDS_BY_COMMAND)
    return {"shell": shell, "script": text}, text.rstrip("\n").split("\n"), EXIT_OK


def cmd_kiosk(ctx):
    """kiosk [ops|team|release|quiet]: prints the address of the monitor for a TV or a wall. Needs no monitor; with `kiosk.enabled` off the page ignores the profile and this says so."""
    preset = ctx["action"] or "ops"
    if preset not in kiosk.PRESETS:
        raise CliError(EXIT_USAGE, i18n.t("cli.kiosk_usage", presets=", ".join(kiosk.PRESETS)))
    raw = ctx.get("raw") or {}
    link = kiosk.url(ctx["base"], preset, raw, ctx["account"])
    config = kiosk.settings(raw)
    lines = [link]
    if not config["enabled"]:
        lines.append(i18n.t("cli.kiosk_off"))
    return {"preset": preset, "tabs": list(kiosk.PRESETS[preset]), "url": link, "enabled": config["enabled"]}, lines, EXIT_OK


def cmd_branch(ctx):
    """One read of `watch branch`: the runs of the commit of the current folder (or of --repo / --branch) as the monitor holds them. Exit 0 = all passed, 1 = a failure or not finished."""
    repo, branch = ctx.get("repo_asked") or "", ctx.get("branch") or ""      # what was typed, not the cleaned copy: a repository that is not valid is refused, never replaced by the one of the folder
    if repo and not branchwatch.valid_repo(repo) or branch and not branchwatch.valid_branch(branch):
        raise CliError(EXIT_USAGE, i18n.t("cli.branch_bad_args"))
    here = branchwatch.git_context(ctx.get("cwd"))
    owner, _, name = repo.rpartition("/") if repo else ("", "", "")
    if not repo:
        owner, name = here["owner"], here["name"]
    if not name:
        raise CliError(EXIT_USAGE, i18n.t("cli.branch_no_repo"))
    branch_name = branch or here["branch"]
    if not branch_name:
        raise CliError(EXIT_USAGE, i18n.t("cli.branch_no_branch"))
    sha = here["sha"] if not branch and not repo else ""      # a commit only makes sense for the folder itself: with --repo or --branch the newest run of each workflow is followed
    answer = fetch(ctx["base"], "/api/data", {"account": ctx["account"]}, ctx["timeout"], ctx["token"])
    data = answer.get("data") or {}
    if not isinstance(data, dict) or not isinstance(data.get("runs") or [], list):
        raise ValueError("shape")
    verdict = branchwatch.evaluate(data.get("runs") or [], owner, name, branch_name, sha)
    full = (owner + "/" if owner else "") + name
    payload = {"repo": full, "branch": branch_name, "sha": sha[:7], **verdict, "exit": branchwatch.exit_code(verdict["state"])}
    lines = [i18n.t("cli.branch_head", repo=full, branch=branch_name, sha=sha[:7] or "-", state=i18n.t("cli.branch_state_" + verdict["state"]))]
    for row in verdict["runs"]:
        lines.append("  " + i18n.t("cli.branch_row", workflow=row["workflow"], status=row["status"], conclusion=row["conclusion"] or "-"))
    return payload, lines, payload["exit"]


METRIC_LEVELS = ("info", "warning", "error", "critical")


def cmd_metrics(ctx):
    """metrics [--if-problem] [--fail-on LEVEL]: the figures of the monitor, one `name=value` per line, in a fixed order and with no text around them, so that `cron` mails exactly that and a script
    can read it with `cut -d= -f2`. A figure that is not known is left out, never written as 0. With --if-problem nothing is written and the exit code is 0 when there are no red workflows and no
    alert at --fail-on (error by default) or worse; otherwise the figures are written and the exit code is 5. Read only: it asks the monitor, never GitHub."""
    status, _, code = cmd_status(dict(ctx, format="json"))
    alerts = fetch(ctx["base"], "/api/alerts", {"account": ctx["account"], "muted": "hide"}, ctx["timeout"], ctx["token"]).get("alerts") or []
    per_level = {level: sum(1 for a in alerts if isinstance(a, dict) and a.get("level") == level) for level in METRIC_LEVELS}
    allowance = status.get("allowance") or {}
    figures = {"repos": status.get("repos"), "active": status.get("active"), "queued": status.get("queued"), "failures_24h": status.get("failures_24h"), "successes_24h": status.get("successes_24h"),
               "red_workflows": status.get("red_workflows"), "alerts": len(alerts), **{"alerts_" + level: n for level, n in per_level.items()},
               "allowance_remaining": allowance.get("remaining"), "allowance_limit": allowance.get("limit"), "offline": 1 if status.get("offline") else 0}
    figures = {k: v for k, v in figures.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    wanted = ctx.get("fail_on") or "error"
    rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    worse = sum(n for level, n in per_level.items() if rank[level] >= rank[wanted])
    problem = bool(figures.get("red_workflows")) or worse > 0
    if ctx.get("if_problem") and not problem and code == EXIT_OK:
        return figures, [], EXIT_OK
    lines = [f"{name}={value}" for name, value in figures.items()]
    if problem:
        code = EXIT_ALERTS if code == EXIT_OK else code
    return figures, lines, code


def cmd_watch(ctx):
    """watch status|alerts [--interval S] [--once] [--exit-on-change] [--no-clear]: the same read again and again, from the API of the monitor (never GitHub). Ctrl-C ends it with 0; with
    --exit-on-change it ends with 6 when something changed; a monitor that cannot be reached is retried with a longer pause each time."""
    command = ctx["action"]
    if command not in watch_loop.WATCHABLE:
        raise CliError(EXIT_USAGE, i18n.t("cli.watch_usage"))
    handler = cmd_branch if command == "branch" else HANDLERS[command]
    interval = watch_loop.interval_for(ctx.get("interval"), ctx.get("raw"))
    on_branch = command == "branch"

    operator = command == "status" and status_scheme(ctx) == "operator"      # `watch status` follows the codes of the operator also when the read fails (network, refusal, an answer that cannot be read)

    def read():
        try:
            return handler(ctx)
        except (AttributeError, TypeError, KeyError, ValueError, IndexError):
            raise CliError(operator_status_code(EXIT_DEGRADED) if operator else EXIT_DEGRADED, i18n.t("cli.bad_shape")) from None
        except CliError as error:
            if operator and error.code != EXIT_USAGE:
                raise CliError(operator_status_code(error.code), error.text) from None
            raise

    def show(payload, lines, code):
        out = formats.render(ctx["format"], command, payload, lines, code, width=terminal.width(), color=ctx.get("color", False))
        if not terminal.emit(out if ctx["format"] in ("json", "ndjson", "table") else terminal.clean(out)):
            raise KeyboardInterrupt      # the reader of the pipe is gone: end like Ctrl-C does

    def clear():
        if ctx.get("clear") and ctx["format"] in ("text", "table") and sys.stdout.isatty():
            print("\x1b[2J\x1b[H", end="")
    extra = {}
    if on_branch:      # it waits for the runs of the commit to finish: it ends by itself with 0 (all passed) or 1 (a failure, or not finished in time)
        extra = {"stop": lambda payload: payload.get("exit") if isinstance(payload, dict) and payload.get("done") else None, "timeout": watch_loop.branch_timeout(ctx.get("raw"), ctx.get("wait")),
                 "on_timeout": lambda: print(i18n.t("cli.branch_timeout"), file=sys.stderr, flush=True)}
    code = watch_loop.run(command, read, show, interval, once=ctx.get("once", False), exit_on_change=ctx.get("exit_on_change", False), error=lambda text: print(text, file=sys.stderr, flush=True), clear=clear, **extra)
    return None, None, code


def cmd_monitor(ctx):
    """`monitor [N]`: `watch status`. `monitor_words` turns the words into `watch status` before the parser reads them, so this is only the way in when the command reached the parser as it is."""
    return cmd_watch(dict(ctx, action="status"))


HANDLERS = {"proposals": cmd_proposals, "monitor": cmd_monitor, "credential": cmd_credential, "ai-hook": cmd_ai_hook, "status": cmd_status, "accounts": cmd_accounts, "alerts": cmd_alerts, "score": cmd_score, "compare": cmd_compare, "team": cmd_team, "live": cmd_live, "doctor": cmd_doctor, "backup": cmd_backup, "health": cmd_health, "check": cmd_health, "lessons": cmd_lessons, "briefs": cmd_briefs, "docs": cmd_docs, "screens": cmd_screens, "toolbox": cmd_toolbox, "api": cmd_api, "gh-token": cmd_gh_token, "install-skill": cmd_install_skill, "ai": cmd_ai, "watch": cmd_watch, "completions": cmd_completions, "kiosk": cmd_kiosk, "metrics": cmd_metrics}
HANDLERS.update({c.name: c.run for c in families.commands()})


def cmd_update(rest):
    """`update [...]`: hands everything after the word to tools/monitor_updater.py (one file, standard library only) and returns its exit code; the word is not parsed here because the updater has its own options."""
    import importlib.util
    here = Path(__file__).resolve().parents[3]
    tool = here / "tools" / "monitor_updater.py"
    if not tool.is_file():
        print(i18n.t("cli.update_missing", file=str(tool)), file=sys.stderr)
        return EXIT_USAGE
    spec = importlib.util.spec_from_file_location("monitor_updater", tool)
    module = importlib.util.module_from_spec(spec)
    sys.modules["monitor_updater"] = module
    spec.loader.exec_module(module)
    return int(module.main(rest))


class TranslatedFormatter(argparse.RawDescriptionHelpFormatter):
    """The formatter of the help with the word of the usage line in the language of the command line (`--lang`, MONITOR_LANG)."""

    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(usage, actions, groups, prefix if prefix is not None else i18n.t("cli.argparse_usage") + " ")


class TranslatedParser(argparse.ArgumentParser):
    """An ArgumentParser whose own words (the titles of the sections, the line of -h and the messages of a wrong use) come from the catalogue of the monitor, in the eight languages, so that a
    wrong use is not told half in English. The error still ends the command with the exit code of a wrong use."""

    PATTERNS = (
        (re.compile(r"argument (?P<name>.+?): invalid choice: (?P<value>.+?) \(choose from (?P<choices>.*)\)$", re.S), "cli.argparse_invalid_choice"),
        (re.compile(r"the following arguments are required: (?P<names>.+)$"), "cli.argparse_required"),
        (re.compile(r"unrecognized arguments: (?P<values>.+)$"), "cli.argparse_unrecognized"),
        (re.compile(r"argument (?P<name>.+?): expected one argument$"), "cli.argparse_expected"),
        (re.compile(r"argument (?P<name>.+?): invalid (?P<kind>\w+) value: (?P<value>.+)$"), "cli.argparse_invalid_value"),
    )

    def translate(self, message):
        for pattern, key in self.PATTERNS:
            found = pattern.match(message)
            if found:
                return i18n.t(key, **found.groupdict())
        return message

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: {i18n.t('cli.argparse_error')}: {self.translate(message)}\n")


def build_parser():
    ap = TranslatedParser(prog="monitor_cli.py", description=i18n.t("cli.description"), epilog=i18n.t("cli.epilog"), formatter_class=TranslatedFormatter, add_help=False)
    ap._positionals.title, ap._optionals.title = i18n.t("cli.argparse_positional"), i18n.t("cli.argparse_options")
    ap.add_argument("-h", "--help", action="help", help=i18n.t("cli.argparse_help"))
    ap.add_argument("command", choices=COMMANDS, help=command_help(families.commands()))
    ap.add_argument("action", nargs="?", choices=AI_HOOK_ACTIONS + CREDENTIAL_ACTIONS + LESSONS_ACTIONS + PROPOSALS_ACTIONS + BRIEFS_ACTIONS + DOCS_ACTIONS + API_ACTIONS + SKILL_ACTIONS + AI_ACTIONS + BACKUP_ACTIONS + SCREENS_ACTIONS + TOOLBOX_ACTIONS + tuple(w for words in OPERATOR_WORDS.values() for w in words) + tuple(w for c in families.commands() for w in c.words), default=None, help=i18n.t("cli.help_ai_action"))
    ap.add_argument("file", nargs="?", default="", help=i18n.t("cli.help_file"))
    ap.add_argument("--json", action="store_true", help=i18n.t("cli.help_json"))
    for name in ("assistant", "cursor", "generic"):
        ap.add_argument("--" + name, dest="target", action="store_const", const=name, default="", help=i18n.t("cli.help_" + name))
    ap.add_argument("--scope", choices=("project", "user"), default="project", help=i18n.t("cli.help_scope"))
    ap.add_argument("--project-dir", metavar="DIR", default="", dest="project_dir", help=i18n.t("cli.help_project_dir"))
    ap.add_argument("--dry-run", action="store_true", dest="dry_run", help=i18n.t("cli.help_dry_run"))
    ap.add_argument("--account", metavar="ID", default="", help=i18n.t("cli.help_account"))
    ap.add_argument("--url", metavar="URL", default="", help=i18n.t("cli.help_url"))
    ap.add_argument("--lite", action="store_true", help=i18n.t("cli.help_lite"))
    ap.add_argument("--token-file", metavar="FILE", default="", dest="token_file", help=i18n.t("cli.help_token_file"))
    ap.add_argument("--token", metavar="TOKEN", default="", help=i18n.t("cli.help_token"))
    ap.add_argument("--deep", action="store_true", help=i18n.t("cli.help_deep"))
    ap.add_argument("--user", metavar="NAME", default="", help=i18n.t("cli.help_user"))
    ap.add_argument("--password-file", metavar="FILE", default="", dest="password_file", help=i18n.t("cli.help_password_file"))
    ap.add_argument("--ca-file", metavar="FILE", default="", dest="ca_file", help=i18n.t("cli.help_ca_file"))
    ap.add_argument("--new-token-file", metavar="FILE", default="", dest="new_token_file", help=i18n.t("cli.help_new_token_file"))
    ap.add_argument("--timeout", type=float, default=8.0, metavar="SECONDS", help=i18n.t("cli.help_timeout"))
    ap.add_argument("--sentinel", choices=("ci", "collab", "security", "supply", "delivery", "system"), default="", help=i18n.t("cli.help_sentinel"))
    ap.add_argument("--level", choices=LEVELS, default="", help=i18n.t("cli.help_level"))
    ap.add_argument("--muted", choices=("show", "hide", "only"), default="hide", help=i18n.t("cli.help_muted"))
    ap.add_argument("--since", metavar="LENGTH", default="", help=i18n.t("cli.help_since"))
    ap.add_argument("--fail-on", choices=LEVELS, default="", dest="fail_on", help=i18n.t("cli.help_fail_on"))
    ap.add_argument("--strict", action="store_true", help=i18n.t("cli.help_strict"))
    ap.add_argument("--force", action="store_true", help=i18n.t("cli.help_force"))
    ap.add_argument("--encrypt", action="store_true", help=i18n.t("cli.help_encrypt"))
    ap.add_argument("--key-env", metavar="NAME", default="", dest="key_env", help=i18n.t("cli.help_key_env"))
    ap.add_argument("--to-dir", metavar="DIR", default="", dest="to_dir", help=i18n.t("cli.help_to_dir"))
    ap.add_argument("--dest", metavar="FOLDER", default="", help=i18n.t("cli.help_dest"))
    ap.add_argument("--read-only", action="store_true", dest="read_only", help=i18n.t("cli.help_read_only"))
    ap.add_argument("--repo", metavar="NAME", default="", help=i18n.t("cli.help_repo"))
    ap.add_argument("--severity", choices=("warn", "bad"), default="", help=i18n.t("cli.help_severity"))
    ap.add_argument("--compare", action="store_true", help=i18n.t("cli.help_compare"))
    ap.add_argument("--window", metavar="DAYS", default="", help=i18n.t("cli.help_window"))
    ap.add_argument("--days", choices=("all", "workdays", "weekend"), default="", help=i18n.t("cli.help_days"))
    ap.add_argument("--baseline", choices=("previous", "year_ago"), default="", help=i18n.t("cli.help_baseline"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    ap.add_argument("--provider", metavar="NAME", default="", help=i18n.t("cli.help_provider"))
    ap.add_argument("--model", metavar="NAME", default="", help=i18n.t("cli.help_model"))
    ap.add_argument("--refresh", action="store_true", help=i18n.t("cli.help_refresh"))
    ap.add_argument("--format", choices=formats.FORMATS + ("csv",), default="", help=i18n.t("cli.help_format"))
    ap.add_argument("--interval", type=float, default=None, metavar="SECONDS", help=i18n.t("cli.help_interval"))
    ap.add_argument("--once", action="store_true", help=i18n.t("cli.help_once"))
    ap.add_argument("--exit-on-change", action="store_true", dest="exit_on_change", help=i18n.t("cli.help_exit_on_change"))
    ap.add_argument("--no-clear", action="store_true", dest="no_clear", help=i18n.t("cli.help_no_clear"))
    ap.add_argument("--single-pass", action="store_true", dest="single_pass", help=i18n.t("cli.help_single_pass"))
    ap.add_argument("--branch", metavar="NAME", default="", help=i18n.t("cli.help_branch"))
    ap.add_argument("--wait", type=float, default=None, metavar="SECONDS", help=i18n.t("cli.help_wait"))
    ap.add_argument("--status-codes", choices=STATUS_CODES, default="", dest="status_codes", help=i18n.t("cli.help_status_codes"))
    ap.add_argument("--if-problem", action="store_true", dest="if_problem", help=i18n.t("cli.help_if_problem"))
    ap.add_argument("--color", choices=terminal.MODES, default="auto", help=i18n.t("cli.help_color"))
    ap.add_argument("--egress", action="store_true", help=i18n.t("cli.help_egress"))
    ap.add_argument("--latency", action="store_true", help=i18n.t("cli.help_latency"))
    ap.add_argument("--version", action="store_true", help=i18n.t("cli.help_version"))
    add_family_options(ap, families.commands())
    return ap


def command_help(commands):
    """The help of the word `command`: the text of the monitor and, after it, one line for each command of a part."""
    return " ".join([i18n.t("cli.help_command")] + [f"{c.name}: {i18n.t(c.help)}" for c in commands])


def add_family_options(parser, commands):
    """The options of the commands of the parts. Two commands may share one option (the same flag is added once)."""
    for command in commands:
        for option in command.options:
            if option.flag not in parser._option_string_actions:      # noqa: SLF001
                parser.add_argument(option.flag, help=i18n.t(option.help), **option.kwargs)


def monitor_words(args_list):
    """`monitor [N]` is `watch status` that refreshes every N seconds (the interval of the setting when N is not given; raised to the floor `cli.watch.min_interval_seconds`): the screen of a terminal left open. The
    rest of the options are kept, so `monitor 10 --json` and `monitor --url ...` work, and so do options in front (`--lang es monitor 10`). Anything else is returned as it came."""
    at = 0
    known = build_parser()._option_string_actions if "monitor" in args_list else {}
    while at < len(args_list) and args_list[at].startswith("-"):      # the options in front of the command: a flag takes no word, an option with a value takes the next one
        action = known.get(args_list[at])
        at += 2 if action is not None and action.nargs != 0 and "=" not in args_list[at] else 1
    if args_list[at:at + 1] != ["monitor"]:
        return args_list
    head, rest = args_list[:at], args_list[at + 1:]
    if rest and re.fullmatch(r"[0-9]{1,4}", rest[0]):
        return head + ["watch", "status", "--interval", rest[0]] + rest[1:]
    return head + ["watch", "status"] + rest


def main(argv=None):
    i18n.cli_language(argv)
    platform_compat.console_utf8()
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args_list and args_list[:1] != ["update"]:
        print(f"monitor_cli {TOOL_VERSION}")
        return EXIT_OK
    args_list = monitor_words(args_list)
    if args_list[:1] == ["update"]:      # the updater parses its own options (and has its own exit codes)
        return cmd_update(args_list[1:])
    parser = build_parser()
    try:
        args = parser.parse_args(args_list)
    except SystemExit as exit_:
        return EXIT_OK if exit_.code in (0, None) else EXIT_USAGE
    if args.command == "monitor":      # monitor_words did not meet it (something odd stood in front): it is `watch status` all the same
        args.command, args.action = "watch", "status"
    if args.format == "json":
        args.json = True
    if args.lang:
        i18n.set_language(args.lang)
    if args.lite and args.command not in LITE_COMMANDS:
        print(i18n.t("cli.lite_only"), file=sys.stderr)
        return EXIT_USAGE
    scheme = {"operator": False}      # set once the configuration is read: the exit code of a `status` that fails follows the scheme in use
    try:
        ctx = {"base": base_url(args.url, args.lite), "account": args.account, "timeout": max(1.0, min(60.0, args.timeout)), "token": resolve_token(flag=args.token, token_file=args.token_file),
               "sentinel": args.sentinel, "level": args.level, "since": args.since.strip() if re.fullmatch(r"\s*[0-9]{1,6}\s*[smhdwSMHDW]?\s*", args.since) else ("bad" if args.since.strip() else ""), "muted": args.muted, "fail_on": args.fail_on, "lite": args.lite, "compare": args.compare, "severity": args.severity, "window": args.window if re.fullmatch(r"[0-9]{1,3}d?", args.window) else "", "days": args.days, "baseline": args.baseline, "format": args.format,
               "action": args.action or "", "target": args.target, "scope": args.scope, "project_dir": args.project_dir, "dry_run": args.dry_run, "deep": args.deep, "file": args.file, "strict": args.strict, "force": args.force, "encrypt": args.encrypt, "key_env": args.key_env if re.fullmatch(r"[A-Z_][A-Z0-9_]{0,63}", args.key_env) else "", "to_dir": args.to_dir, "new_token_file": args.new_token_file, "dest": args.dest, "read_only": args.read_only, "repo": args.repo if re.fullmatch(r"[A-Za-z0-9._/-]{0,201}", args.repo) else "",
               "provider": args.provider if re.fullmatch(r"[A-Za-z0-9-]{0,40}", args.provider) else "", "model": args.model if re.fullmatch(r"[A-Za-z0-9._:/@+-]{0,100}", args.model) else "", "refresh": args.refresh}
        if args.format == "csv" and args.command != "compare":      # only `compare` writes csv: any other command would give text with a 0, which a script that asked for csv takes for csv
            raise CliError(EXIT_USAGE, i18n.t("cli.csv_only_compare", command=args.command))
        raw = _config() if args.command in ("watch", "kiosk", "status") or not (args.format or args.json) else {}
        ctx.update({"raw": raw, "format": "csv" if args.format == "csv" else formats.choose(args.format, args.json, formats.configured_format(raw)), "interval": args.interval, "once": args.once or args.single_pass, "exit_on_change": args.exit_on_change, "clear": not args.no_clear,
                    "branch": args.branch, "repo_asked": args.repo, "wait": args.wait, "status_codes": args.status_codes, "if_problem": args.if_problem, "color": terminal.use_color(args.color)})
        scheme["operator"] = args.command == "status" and status_scheme(ctx) == "operator"
        ctx["args"] = args      # every parsed option, for the commands of the parts
        ctx["egress"] = args.egress
        ctx["latency"] = args.latency
        CLIENT.update({"session": "", "ca": (args.ca_file or os.environ.get("MONITOR_CA_FILE") or "").strip()})
        if CLIENT["ca"] and not os.path.isfile(CLIENT["ca"]):
            raise CliError(EXIT_USAGE, i18n.t("cli.ca_file_bad", file=CLIENT["ca"]))
        insecure = plain_http_to_network(ctx["base"])
        if insecure:
            print(i18n.t("cli.plain_http", host=insecure), file=sys.stderr)
        who = (args.user or os.environ.get("MONITOR_USER") or "").strip()
        if who and args.command not in ("doctor", "ai-hook", "completions", "kiosk"):
            secret_file = (args.password_file or os.environ.get("MONITOR_PASSWORD_FILE") or "").strip()
            password = read_token_file(secret_file) if secret_file else (os.environ.get("MONITOR_PASSWORD") or "")
            if not password:
                raise CliError(EXIT_USAGE, i18n.t("cli.password_missing"))
            sign_in(ctx["base"], who, password, ctx["timeout"], ctx["token"])
        try:
            payload, lines, code = HANDLERS[args.command](ctx)
        except (AttributeError, TypeError, KeyError, ValueError, IndexError):      # a field of the wrong type in an answer that is an object: degraded, never a traceback
            raise CliError(EXIT_DEGRADED, i18n.t("cli.bad_shape")) from None
    except CliError as error:
        code = operator_status_code(error.code) if scheme["operator"] and error.code != EXIT_USAGE else error.code
        if args.json or args.format in ("json", "ndjson"):
            print(json.dumps({"ok": False, "exit": code, "error": error.text, "help": error.help}, ensure_ascii=False))
        else:
            print(error.text, file=sys.stderr)
            if error.help:
                print(i18n.t("cli.help_line", help=error.help), file=sys.stderr)
        return code
    if lines is None:      # `watch` wrote its own results while it ran
        return code
    if args.command == "compare" and ctx["format"] != "json":      # `compare` writes its own table, ndjson and csv
        terminal.emit(terminal.clean("\n".join(lines)))
        return code
    if args.command == "metrics" and not lines and ctx["format"] in ("text", "table", "plain"):      # `metrics --if-problem` with nothing to report writes nothing at all
        return code
    out = formats.render(ctx["format"], args.command, payload, lines, code, ascii_only=args.command == "ai-hook", width=terminal.width(), color=ctx["color"])      # ai-hook: plain ASCII, whatever the console
    terminal.emit(out if ctx["format"] in ("json", "ndjson", "table") else terminal.clean(out))
    return code


if __name__ == "__main__":
    sys.exit(main())
