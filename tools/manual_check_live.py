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
    elif step == "service":
        print("Linux:  systemctl --user status github-actions-monitor   (see deploy/ for the unit)\nmacOS:  launchctl list | grep github-actions-monitor   (see deploy/ for the plist)")
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
