#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Checks, by hand and against the REAL services, the parts of the monitor that the automatic tests can only cover with simulated answers. Nothing here runs by itself and nothing is
written: every step only READS (or sends the test message you ask for) and tells what it found. It never asks for a secret: it uses your own `gh` login and the channels you already configured.

    python tools/manual_check_live.py scopes      the scopes of your token (needed by the actions on GitHub)
    python tools/manual_check_live.py billing     the billing report (a login with the `user` scope, or an organisation owner; otherwise it says "not available", which is the expected answer)
    python tools/manual_check_live.py orgs        the organisations of the login
    python tools/manual_check_live.py runners ORG the self-hosted runners of an organisation
    python tools/manual_check_live.py copilot     the flags of `gh copilot` (needs the Copilot command line installed)
    python tools/manual_check_live.py notify [PORT]   asks a running monitor to send a test message through every channel you enabled
    python tools/manual_check_live.py tls         how to check direct HTTPS with a real browser and the POST that opens the session
    python tools/manual_check_live.py proxy [HOST] [PORT] [CONNECT]   checks, through your real HTTPS proxy on port 443, that the page is let in (listen.proxy_public_host)
    python tools/manual_check_live.py service     prints how to check the systemd / launchd examples of deploy/
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "monitor"))


def gh(*args):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    return done.returncode, done.stdout, done.stderr


PROXY_HELP = """HTTPS proxy on the default port 443 (listen.proxy_public_host). Set up, once:
  1. In actions_monitor.json: listen.network = true, listen.token_env (the NAME of the variable that holds the access token), listen.secure_cookie = true and
     listen.proxy_public_host = the public name of the proxy (a host name only, no port). Restart the monitor.
  2. The proxy keeps the name the browser used and sends it WITHOUT a port:
       nginx:  proxy_pass http://127.0.0.1:8765;  proxy_set_header Host $host;
       Caddy:  reverse_proxy 127.0.0.1:8765      (it sends the Host as it came)
  3. Run:  python tools/manual_check_live.py proxy PUBLIC.NAME 443   with MONITOR_ACCESS_TOKEN set to the access token (the variable is only read here, never printed)."""


def proxy_check(args):
    """Four requests through the real proxy: one that must be let in (session opened by POST, cookie Secure) and three that must stay refused. It never prints the token."""
    import http.client
    import os
    import ssl
    if not args:
        print(PROXY_HELP)
        return
    host, port = args[0], int(args[1]) if len(args) > 1 else 443
    connect = args[2] if len(args) > 2 else host      # where to connect (an address, before the name resolves); the Host and the Origin always carry the public name, without a port
    token = os.environ.get("MONITOR_ACCESS_TOKEN", "")
    if len(token) < 16:
        print("Set MONITOR_ACCESS_TOKEN to the access token of the monitor (16 characters or more) in this terminal first; it is only read, never printed.")
        return
    context = ssl.create_default_context()
    if os.environ.get("MONITOR_CHECK_INSECURE") == "1":
        context.check_hostname, context.verify_mode = False, ssl.CERT_NONE

    def call(path, body, origin, extra_host=None):
        connection = http.client.HTTPSConnection(connect, port, context=context, timeout=15)
        try:
            headers = {"Content-Type": "application/json", "X-Monitor-Access": token, "Host": extra_host or host}
            if origin is not None:
                headers["Origin"] = origin
            connection.request("POST" if body is not None else "GET", path, None if body is None else json.dumps(body), headers)
            answer = connection.getresponse()
            answer.read()
            return answer.status, answer.getheader("Set-Cookie") or ""
        except (OSError, ssl.SSLError) as error:
            return 0, str(error)[:100]
        finally:
            connection.close()
    checks = (("the page is let in (POST /api/access with the right token and the Origin of the proxy)", call("/api/access", {"token": token}, f"https://{host}"), 200),
              ("a wrong Origin scheme is refused", call("/api/session-token", None, f"http://{host}"), 403),
              ("another host name is refused", call("/api/session-token", None, "https://evil.example"), 403),
              ("the name with a port is refused", call("/api/session-token", None, f"https://{host}:8765"), 403))
    failed = 0
    for label, (status, cookie), wanted in checks:
        good = status == wanted and (wanted != 200 or ("Secure" in cookie and "HttpOnly" in cookie))
        failed += 0 if good else 1
        print(("OK   " if good else "FAIL ") + label + f" (answered {status})" + ("" if good or status else ": " + cookie))
    print("The proxy name is accepted and nothing else is." if not failed else f"{failed} check(s) failed: see docs/ADVANCED.md (HTTPS) and the settings of the proxy above.")


def main(argv):
    step = argv[0] if argv else "help"
    if step == "scopes":
        import actions_monitor as am
        import ghactions
        have = ghactions.scopes(am.run_gh)
        print("scopes:", "not listed (fine-grained or app token: GitHub decides)" if have is None else ", ".join(sorted(have)))
    elif step == "billing":
        import actions_monitor as am
        import quota
        owner = json.loads(gh("api", "user")[1] or "{}").get("login", "")
        result = quota.billing_usage(owner, lambda endpoint: am.gh("api", endpoint, retries=0))
        print("billing report:", "not available for this login (expected without the `user` scope)" if result is None else json.dumps(result, indent=1))
    elif step == "orgs":
        code, out, _err = gh("api", "user/orgs", "--jq", "[.[].login]")
        print("organisations:", out.strip() if code == 0 else "could not be read")
    elif step == "runners" and len(argv) > 1:
        code, out, err = gh("api", f"orgs/{argv[1]}/actions/runners", "--jq", "[.runners[] | {name, status, busy}]")
        print(out.strip() if code == 0 else "not available: " + err.strip()[:120])
    elif step == "copilot":
        code, out, err = gh("copilot", "--", "--help")
        print(out if code == 0 else "the Copilot command line is not installed (" + (err or out).strip()[:100] + "); the flags stay unverified")
    elif step == "notify":
        port = argv[1] if len(argv) > 1 else "8765"
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "monitor"))
        import notifiers
        base = f"http://127.0.0.1:{port}"
        token = json.load(urllib.request.urlopen(base + "/api/session-token", timeout=10)).get("token", "")
        for name in notifiers.CHANNELS:
            request = urllib.request.Request(base + "/api/notify/test", data=json.dumps({"channel": name}).encode(), method="POST", headers={"Content-Type": "application/json", "X-Monitor-Token": token})
            try:
                print(name, json.load(urllib.request.urlopen(request, timeout=20)))
            except Exception as error:   # noqa: BLE001
                print(name, "failed:", str(error)[:100])
            token = json.load(urllib.request.urlopen(base + "/api/session-token", timeout=10)).get("token", "")
    elif step == "tls":
        print(chr(10).join(["Direct HTTPS with a real browser (the unit test already does a same-origin POST against a real TLS server with a certificate it makes; this checks the browser itself):",
                         "  1. Put a certificate and a key (PEM) in listen.tls_cert_file / listen.tls_key_file, switch listen.network on, restart.",
                         "  2. Open the https:// address printed in the console, accept the certificate warning once, change a setting and save it: it must answer 200, not 403.",
                         "  3. From another computer: curl -k -X POST -H 'Content-Type: application/json' -d '{\"token\": \"<access token>\"}' https://HOST:PORT/api/access  must set the cookie."]))
    elif step == "proxy":
        proxy_check(argv[1:])
    elif step == "service":
        print("Linux:  systemctl --user status github-actions-monitor   (see deploy/ for the unit)\nmacOS:  launchctl list | grep github-actions-monitor   (see deploy/ for the plist)")
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
