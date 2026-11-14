# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`python -m github_actions_monitor.cli.healthcheck`: the deep health check for a container or a service manager (HEALTHCHECK, systemd `ExecStartPost`, a probe of the proxy).

It asks `GET /api/health?deep=1` of the monitor on this computer (or of `--url`), with the access token when the network mode needs one (`MONITOR_ACCESS_TOKEN`, the file named by
`MONITOR_ACCESS_TOKEN_FILE`, or the file the service keeps in `MONITOR_STATE_DIR`), and never calls GitHub. Exit codes: 0 healthy; 1 unhealthy (the supervisor or the refresh cycle of an account is
stuck or gone, or no account answers); 2 the monitor cannot be reached; 3 the monitor refuses the access token. An account whose login GitHub refuses (blind) is told in the line but is NOT a failure:
a restart does not fix it, a new login does (see `monitor_cli.py credential`).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from github_actions_monitor import i18n
from github_actions_monitor.cli import monitor_cli
from github_actions_monitor.security import netguard

EXIT_OK, EXIT_UNHEALTHY, EXIT_DOWN, EXIT_REFUSED = 0, 1, 2, 3


def token(env=None):
    """The access token for this check: the usual variables of the command line, else the file named by `MONITOR_ACCESS_TOKEN_FILE`, else the file of the service in `MONITOR_STATE_DIR`. '' when none."""
    env = os.environ if env is None else env
    for name in monitor_cli.TOKEN_VARIABLES:
        if (env.get(name) or "").strip():
            return env[name].strip()
    candidates = [env.get("MONITOR_ACCESS_TOKEN_FILE") or ""]
    if (env.get("MONITOR_STATE_DIR") or "").strip():
        candidates.append(os.path.join(env["MONITOR_STATE_DIR"].strip(), "access_token"))
    for path in candidates:
        if path:
            try:
                with open(path, "r", encoding="utf-8-sig") as handle:
                    value = handle.readline().strip()
            except (OSError, UnicodeError):
                continue
            if value:
                return value
    return ""


def ask(base, timeout, access):
    """(status, document or None): the answer of the deep check; (0, None) when nothing answers."""
    request = urllib.request.Request(base + "/api/health?deep=1", headers={"Accept": "application/json", **({"X-Monitor-Access": access} if access else {})})
    try:
        with netguard.local_open(request, timeout=timeout, follow_redirects=False) as answer:
            status, body = answer.status, answer.read(1_000_000)
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read(1_000_000)
        error.close()
    except (urllib.error.URLError, OSError, ValueError):
        return 0, None
    try:
        document = json.loads(body.decode("utf-8"))
    except ValueError:
        document = None
    return status, document if isinstance(document, dict) else None


def judge(status, document):
    """(exit code, text) for an answer."""
    if status == 0:
        return EXIT_DOWN, i18n.t("healthcheck.unreachable")
    if status in (401, 403):
        return EXIT_REFUSED, i18n.t("healthcheck.refused", code=status)
    if document is None:
        return EXIT_UNHEALTHY, i18n.t("healthcheck.unreadable", code=status)
    if document.get("supervisor"):
        states = document.get("states") if isinstance(document.get("states"), dict) else {}
        listing = ", ".join(f"{name}={state}" for name, state in sorted(states.items()))
        blind = ", ".join(str(a) for a in (document.get("blind") or []))
        if status == 200 and document.get("ok"):
            return EXIT_OK, i18n.t("healthcheck.supervisor_ok", n=document.get("accounts", 0), states=listing) + (" " + i18n.t("healthcheck.blind", accounts=blind) if blind else "")
        why = i18n.t("healthcheck.supervisor_stale") if document.get("stale") else ", ".join(f"{p.get('id')}={p.get('state')}" for p in document.get("problems") or [])
        return EXIT_UNHEALTHY, i18n.t("healthcheck.supervisor_bad", why=why or "-", states=listing)
    cycle = document.get("cycle") if isinstance(document.get("cycle"), dict) else {}
    blind = (document.get("credential") or {}).get("state") == "blind" if isinstance(document.get("credential"), dict) else False
    if status == 200 and document.get("ok"):
        return EXIT_OK, i18n.t("healthcheck.ok", version=document.get("version", "-")) + (" " + i18n.t("healthcheck.blind", accounts=document.get("account") or "-") if blind else "")
    state = "dead" if cycle.get("dead") else "stuck"
    return EXIT_UNHEALTHY, i18n.t("healthcheck.cycle_bad", state=state, seconds=cycle.get("running_seconds", "-"))


def main(argv=None):
    i18n.cli_language(argv)
    parser = argparse.ArgumentParser(description=i18n.t("healthcheck.description"), prog="healthcheck")
    parser.add_argument("--url", default="", help=i18n.t("healthcheck.help_url"))
    parser.add_argument("--timeout", type=float, default=5.0, help=i18n.t("healthcheck.help_timeout"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    try:
        args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit as stop:
        return EXIT_OK if stop.code in (0, None) else EXIT_UNHEALTHY
    if args.lang:
        i18n.set_language(args.lang)
    base = args.url.strip().rstrip("/") or os.environ.get("MONITOR_URL", "").strip().rstrip("/") or f"http://127.0.0.1:{(os.environ.get('MONITOR_PORT') or '8765').strip()}"
    try:
        base = monitor_cli.base_url(base)
    except monitor_cli.CliError as error:
        print(error.text, file=sys.stderr)
        return EXIT_UNHEALTHY
    status, document = ask(base, max(1.0, min(60.0, args.timeout)), token())
    code, text = judge(status, document)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
