# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command line as a client of the monitor (1.7.4): one entry, `python bin/monitor_cli.py COMMAND [options]`, that reads what the running monitor says (`GET /api/...` on this computer, or
`--url` / the variable MONITOR_URL) and never repeats the work of the page against GitHub. The scripts that already exist (read_report.py, --doctor, gha_dispatch_all.py ...) keep working.

  status    one screen: version, edition, repositories, what runs, what fails, the allowance
  accounts  the accounts the supervisor watches (the complete edition with an `accounts/` folder)
  alerts    the alerts of every sentinel in one list (--sentinel ci|collab, --level, --muted)
  live      the last events that arrived through the webhook and the state of the receiver
  doctor    the checks of --doctor for this installation (no monitor needed); --strict makes a warning exit 3
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

Every command takes --json (the answer as one JSON document), --account ID, --url URL, --timeout SECONDS and --lang CODE. In the network mode the access token is read from MONITOR_ACCESS_TOKEN,
then from its alias MONITOR_TOKEN, then from --token-file (a file only you can read) and last from --token (it shows in the list of processes, so it prints a warning on stderr); plain http to another computer prints a warning on stderr. Nothing here writes to GitHub or changes a setting.
The lite edition answers `status`, `doctor` and `health` (use --lite for its port, 8766 unless `ports.lite` says another); the rest need the complete edition.

Exit codes (stable): 0 all right; 1 wrong use of the command; 2 the monitor cannot be reached; 3 the monitor or GitHub refuses the credential (access token of the network mode, or the login
of GitHub); 4 the monitor answers but is degraded (offline, allowance exhausted, no data yet) or an answer that cannot be read; 5 `alerts --fail-on LEVEL` found alerts of that level or worse.
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
COMMANDS = ("status", "accounts", "alerts", "live", "doctor", "health", "check", "score", "team", "ai-hook", "credential", "lessons", "install-skill", "gh-token", "ai", "backup", "update")
BACKUP_ACTIONS = ("create", "verify", "restore", "status", "list")
SKILL_ACTIONS = ("internal", "external")
AI_ACTIONS = ("models", "doctor", "test")
LESSONS_ACTIONS = ("list", "brief", "failures", "close")
AI_HOOK_ACTIONS = ("install", "status", "uninstall")
CREDENTIAL_ACTIONS = ("replace", "reload")
LITE_COMMANDS = ("status", "doctor", "health", "check")
LEVELS = ("info", "warning", "error", "critical")
from github_actions_monitor.cli import monitor_admin      # noqa: E402
CLIENT = monitor_admin.CLIENT      # the session of the team mode and the authority of the certificate: one dict, shared
PORTS = dict(ports.DEFAULTS)      # the defaults; the port in use is ports.resolve (configuration file, MONITOR_PORT)
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
    try:
        checks = doctor.run(config=config, edition=edition)
    except Exception:      # noqa: BLE001 - the doctor itself could not run: its own exit code, not a traceback
        return {"ok": False, "exit": doctor.EXIT_DOCTOR_ERROR}, [i18n.t("doctor.broken")], doctor.EXIT_DOCTOR_ERROR
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


HANDLERS = {"credential": cmd_credential, "ai-hook": cmd_ai_hook, "status": cmd_status, "accounts": cmd_accounts, "alerts": cmd_alerts, "score": cmd_score, "team": cmd_team, "live": cmd_live, "doctor": cmd_doctor, "backup": cmd_backup, "health": cmd_health, "check": cmd_health, "lessons": cmd_lessons, "gh-token": cmd_gh_token, "install-skill": cmd_install_skill, "ai": cmd_ai}


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


def build_parser():
    ap = argparse.ArgumentParser(prog="monitor_cli.py", description=i18n.t("cli.description"), epilog=i18n.t("cli.epilog"), formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=COMMANDS, help=i18n.t("cli.help_command"))
    ap.add_argument("action", nargs="?", choices=AI_HOOK_ACTIONS + CREDENTIAL_ACTIONS + LESSONS_ACTIONS + SKILL_ACTIONS + AI_ACTIONS + BACKUP_ACTIONS, default=None, help=i18n.t("cli.help_ai_action"))
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
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    ap.add_argument("--provider", metavar="NAME", default="", help=i18n.t("cli.help_provider"))
    ap.add_argument("--model", metavar="NAME", default="", help=i18n.t("cli.help_model"))
    ap.add_argument("--refresh", action="store_true", help=i18n.t("cli.help_refresh"))
    ap.add_argument("--version", action="store_true", help=i18n.t("cli.help_version"))
    return ap


def main(argv=None):
    i18n.cli_language(argv)
    platform_compat.console_utf8()
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args_list and args_list[:1] != ["update"]:
        print(f"monitor_cli {TOOL_VERSION}")
        return EXIT_OK
    if args_list[:1] == ["update"]:      # the updater parses its own options (and has its own exit codes)
        return cmd_update(args_list[1:])
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
               "sentinel": args.sentinel, "level": args.level, "muted": args.muted, "fail_on": args.fail_on, "lite": args.lite, "compare": args.compare, "severity": args.severity,
               "action": args.action or "", "target": args.target, "scope": args.scope, "project_dir": args.project_dir, "dry_run": args.dry_run, "deep": args.deep, "file": args.file, "strict": args.strict, "force": args.force, "encrypt": args.encrypt, "key_env": args.key_env if re.fullmatch(r"[A-Z_][A-Z0-9_]{0,63}", args.key_env) else "", "to_dir": args.to_dir, "new_token_file": args.new_token_file, "dest": args.dest, "read_only": args.read_only, "repo": args.repo if re.fullmatch(r"[A-Za-z0-9._/-]{0,201}", args.repo) else "",
               "provider": args.provider if re.fullmatch(r"[A-Za-z0-9-]{0,40}", args.provider) else "", "model": args.model if re.fullmatch(r"[A-Za-z0-9._:/@+-]{0,100}", args.model) else "", "refresh": args.refresh}
        CLIENT.update({"session": "", "ca": (args.ca_file or os.environ.get("MONITOR_CA_FILE") or "").strip()})
        if CLIENT["ca"] and not os.path.isfile(CLIENT["ca"]):
            raise CliError(EXIT_USAGE, i18n.t("cli.ca_file_bad", file=CLIENT["ca"]))
        insecure = plain_http_to_network(ctx["base"])
        if insecure:
            print(i18n.t("cli.plain_http", host=insecure), file=sys.stderr)
        who = (args.user or os.environ.get("MONITOR_USER") or "").strip()
        if who and args.command not in ("doctor", "ai-hook"):
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
