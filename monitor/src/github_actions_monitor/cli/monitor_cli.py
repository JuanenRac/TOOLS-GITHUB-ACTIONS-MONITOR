# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command line as a client of the monitor (1.7.4): one entry, `python monitor_cli.py COMMAND [options]`, that reads what the running monitor says (`GET /api/...` on this computer, or
`--url` / the variable MONITOR_URL) and never repeats the work of the page against GitHub. The scripts that already exist (read_report.py, --doctor, gha_dispatch_all.py ...) keep working.

  status    one screen: version, edition, repositories, what runs, what fails, the allowance
  accounts  the accounts the supervisor watches (the complete edition with an `accounts/` folder)
  alerts    the alerts of every sentinel in one list (--sentinel ci|collab, --level, --muted)
  live      the last events that arrived through the webhook and the state of the receiver
  doctor    the checks of --doctor for this installation (no monitor needed)
  ai-hook   install | status | uninstall the gate script that tells an AI tool what the monitor sees (--assistant, --cursor or --generic; --scope project|user); it needs no
            running monitor and writes only the settings file of that tool (merged, with a backup), never anything on GitHub
  health    a quick check before reading anything heavy: is the monitor reachable, does it accept this client, does the GitHub credential of the account answer (a limit of the
            allowance is told apart from a credential that failed). Alias: check. With --deep it also asks whether the supervisor and the refresh cycle of every account are alive
  credential  replace | reload: put another login of GitHub in place of the one of an account that GitHub revoked (or let expire) without restarting anything; the token is read from a
            file (--new-token-file, or - for the standard input), never from a flag, and it is checked against GitHub before it is kept. Needs an administrator in the team mode, or this computer

A monitor on another computer works the same way: --url (or MONITOR_URL) names it; --ca-file (or MONITOR_CA_FILE) trusts the certificate authority of its HTTPS certificate; in the team mode
--user NAME with --password-file FILE (or MONITOR_USER, MONITOR_PASSWORD_FILE) signs in and the session travels as a Bearer token (`auth.allow_bearer` must be on).

Every command takes --json (the answer as one JSON document), --account ID, --url URL, --timeout SECONDS and --lang CODE. In the network mode the access token is read from MONITOR_ACCESS_TOKEN,
then from its alias MONITOR_TOKEN, then from --token-file (a file only you can read) and last from --token (it shows in the list of processes, so it prints a warning on stderr); plain http to another computer prints a warning on stderr. Nothing here writes to GitHub or changes a setting.
The lite edition answers `status`, `doctor` and `health` (use --lite for its port 8766); the rest need the complete edition.

Exit codes (stable): 0 all right; 1 wrong use of the command; 2 the monitor cannot be reached; 3 the monitor or GitHub refuses the credential (access token of the network mode, or the login
of GitHub); 4 the monitor answers but is degraded (offline, allowance exhausted, no data yet) or an answer that cannot be read; 5 `alerts --fail-on LEVEL` found alerts of that level or worse.
"""
import argparse
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlparse

from github_actions_monitor import i18n
from github_actions_monitor.util import platform_compat
from github_actions_monitor.util import tzdisplay
from github_actions_monitor.tool_version import TOOL_VERSION
from github_actions_monitor.security import netguard

EXIT_OK, EXIT_USAGE, EXIT_DOWN, EXIT_AUTH, EXIT_DEGRADED, EXIT_ALERTS = 0, 1, 2, 3, 4, 5
COMMANDS = ("status", "accounts", "alerts", "live", "doctor", "health", "check", "ai-hook", "credential")
AI_HOOK_ACTIONS = ("install", "status", "uninstall")
CREDENTIAL_ACTIONS = ("replace", "reload")
LITE_COMMANDS = ("status", "doctor", "health", "check")
LEVELS = ("info", "warning", "error", "critical")
from github_actions_monitor.cli import monitor_admin      # noqa: E402
CLIENT = monitor_admin.CLIENT      # the session of the team mode and the authority of the certificate: one dict, shared
PORTS = {"complete": 8765, "lite": 8766}
TOKEN_VARIABLES = ("MONITOR_ACCESS_TOKEN", "MONITOR_TOKEN")      # the first is the one the monitor itself reads; the second is an alias


class CliError(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code, self.text = code, text


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
        return f"http://127.0.0.1:{PORTS['lite' if lite else 'complete']}"
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


def post_json(base, path, payload, timeout=8, token=""):
    """(status, document) of the one request with a body this command line makes (see monitor_admin); CliError(2) when nothing answers."""
    try:
        return monitor_admin.send_json(base, path, payload, timeout, token)
    except monitor_admin.Unreachable:
        raise CliError(EXIT_DOWN, i18n.t("cli.unreachable", url=base)) from None


def sign_in(base, user, password, timeout=8, token=""):
    """Opens a session of the team mode for a script: POST /api/auth/login with client "api" and keeps the Bearer token in CLIENT. Raises CliError(3) when the monitor refuses it."""
    status, answer = post_json(base, "/api/auth/login", {"username": user, "password": password, "client": "api"}, timeout, token)
    if status != 200 or not answer.get("token"):
        raise CliError(EXIT_AUTH, i18n.t("cli.login_refused", code=answer.get("code") or status))
    CLIENT["session"] = str(answer["token"])


def fetch(base, path, query=None, timeout=8, token=""):
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
            raise CliError(EXIT_DEGRADED, i18n.t("cli.not_here", path=path)) from None
        raise CliError(EXIT_DEGRADED, i18n.t("cli.http_error", code=error.code)) from None
    except (urllib.error.URLError, OSError, ValueError):
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
    code = EXIT_OK
    if payload["credential"] == "blind":
        lines.append(i18n.t("cli.status_blind"))
        code = EXIT_AUTH
    if not data and not answer.get("error"):      # the monitor has not read GitHub yet: nothing to report is not "all right" (same as `health`)
        lines.append(i18n.t("cli.health_no_data"))
        code = EXIT_DEGRADED
    if payload["offline"]:
        lines.append(i18n.t("cli.status_offline"))
        code = EXIT_DEGRADED
    if payload["error"]:
        lines.append(i18n.t("cli.status_error", error=str(payload["error"])[:160]))
        code = EXIT_AUTH if answer.get("hint") == "auth" else EXIT_DEGRADED
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


def cmd_alerts(ctx):
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
    checks = doctor.run(config=toolconfig.raw_config())
    edition = "lite" if ctx.get("lite") else "complete"
    return doctor.as_json(checks, edition), doctor.text(checks, i18n.t, edition).rstrip("\n").split("\n"), doctor.exit_code(checks)


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
            line = sys.stdin.readline()
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
    status, answer = post_json(ctx["base"], path, payload, max(ctx["timeout"], 30.0), ctx["token"])
    shown = {k: v for k, v in answer.items() if k != "token"}      # an answer never carries the token, and this command does not print one in any case
    if status in (401, 403):
        raise CliError(EXIT_AUTH, i18n.t("cli.credential_refused", code=answer.get("code") or answer.get("status") or status))
    if status == 404:
        raise CliError(EXIT_DEGRADED, i18n.t("cli.credential_unknown"))
    result = str(answer.get("status") or "")
    ok = status == 200 and answer.get("ok") is True
    line = i18n.t("cli.credential_" + ("done" if ok else "failed"), status=i18n.t("cli.credential_status_" + result) if result else str(status))
    return {"action": action, "ok": ok, **shown}, [line], EXIT_OK if ok else EXIT_DEGRADED


HANDLERS = {"credential": cmd_credential, "ai-hook": cmd_ai_hook, "status": cmd_status, "accounts": cmd_accounts, "alerts": cmd_alerts, "live": cmd_live, "doctor": cmd_doctor, "health": cmd_health, "check": cmd_health}


def build_parser():
    ap = argparse.ArgumentParser(prog="monitor_cli.py", description=i18n.t("cli.description"), epilog=i18n.t("cli.epilog"), formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=COMMANDS, help=i18n.t("cli.help_command"))
    ap.add_argument("action", nargs="?", choices=AI_HOOK_ACTIONS + CREDENTIAL_ACTIONS, default=None, help=i18n.t("cli.help_ai_action"))
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
    ap.add_argument("--sentinel", choices=("ci", "collab", "system"), default="", help=i18n.t("cli.help_sentinel"))
    ap.add_argument("--level", choices=LEVELS, default="", help=i18n.t("cli.help_level"))
    ap.add_argument("--muted", choices=("show", "hide", "only"), default="hide", help=i18n.t("cli.help_muted"))
    ap.add_argument("--fail-on", choices=LEVELS, default="", dest="fail_on", help=i18n.t("cli.help_fail_on"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    ap.add_argument("--version", action="store_true", help=i18n.t("cli.help_version"))
    return ap


def main(argv=None):
    i18n.cli_language(argv)
    platform_compat.console_utf8()
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args_list:
        print(f"monitor_cli {TOOL_VERSION}")
        return EXIT_OK
    parser = build_parser()
    try:
        args = parser.parse_args(args_list)
    except SystemExit as exit_:
        return EXIT_OK if exit_.code in (0, None) else EXIT_USAGE
    if args.lang:
        i18n.set_language(args.lang)
    if args.lite and args.command not in LITE_COMMANDS:
        print(i18n.t("cli.lite_only"), file=sys.stderr)
        return EXIT_USAGE
    try:
        ctx = {"base": base_url(args.url, args.lite), "account": args.account, "timeout": max(1.0, min(60.0, args.timeout)), "token": resolve_token(flag=args.token, token_file=args.token_file),
               "sentinel": args.sentinel, "level": args.level, "muted": args.muted, "fail_on": args.fail_on, "lite": args.lite,
               "action": args.action or "", "target": args.target, "scope": args.scope, "project_dir": args.project_dir, "dry_run": args.dry_run, "deep": args.deep, "new_token_file": args.new_token_file}
        CLIENT.update({"session": "", "ca": (args.ca_file or os.environ.get("MONITOR_CA_FILE") or "").strip()})
        if CLIENT["ca"] and not os.path.isfile(CLIENT["ca"]):
            raise CliError(EXIT_USAGE, i18n.t("cli.ca_file_bad", file=CLIENT["ca"]))
        who = (args.user or os.environ.get("MONITOR_USER") or "").strip()
        if who and args.command not in ("doctor", "ai-hook"):
            secret_file = (args.password_file or os.environ.get("MONITOR_PASSWORD_FILE") or "").strip()
            password = read_token_file(secret_file) if secret_file else (os.environ.get("MONITOR_PASSWORD") or "")
            if not password:
                raise CliError(EXIT_USAGE, i18n.t("cli.password_missing"))
            sign_in(ctx["base"], who, password, ctx["timeout"], ctx["token"])
        insecure = plain_http_to_network(ctx["base"])
        if insecure:
            print(i18n.t("cli.plain_http", host=insecure), file=sys.stderr)
        try:
            payload, lines, code = HANDLERS[args.command](ctx)
        except (AttributeError, TypeError, KeyError, ValueError, IndexError):      # a field of the wrong type in an answer that is an object: degraded, never a traceback
            raise CliError(EXIT_DEGRADED, i18n.t("cli.bad_shape")) from None
    except CliError as error:
        if args.json:
            print(json.dumps({"ok": False, "exit": error.code, "error": error.text}, ensure_ascii=False))
        else:
            print(error.text, file=sys.stderr)
        return error.code
    if args.json:
        print(json.dumps({"ok": code == EXIT_OK, "exit": code, "data": payload}, ensure_ascii=args.command == "ai-hook", indent=1))      # ai-hook: plain ASCII, whatever the console
    else:
        print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
