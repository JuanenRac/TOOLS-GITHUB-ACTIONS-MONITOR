# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tells the running monitor (127.0.0.1 only) that some repositories changed, so it refreshes JUST those and rewrites ci_red.json.

Used by `gha_dispatch_all.py finalize --execute` after a target was signed and published: instead of waiting for the next cold cycle the monitor
re-reads the runs of those repositories, forgets its cached local signing records and rewrites ci_red.json at once (the "pending signature"
alert goes away at once). Nothing leaves this PC; if the monitor is not running nothing happens. It never carries a token or a secret.
"""
import json
import urllib.request
import netguard

PORTS = range(8765, 8775)   # the monitor uses the first free port from 8765
PATH = "/api/refresh-repos"


def notify_refresh(repos, ports=PORTS, timeout=2.0, opener=None):
    """Returns the port of the monitor that accepted the request, or None. Never raises."""
    names = sorted({str(r) for r in repos if r})
    if not names:
        return None
    body = json.dumps({"repos": names}).encode("utf-8")
    for port in ports:
        request = urllib.request.Request(f"http://127.0.0.1:{port}{PATH}", data=body, method="POST", headers={"Content-Type": "application/json"})
        try:
            with (opener or netguard.local_open)(request, timeout=timeout) as answer:
                if json.load(answer).get("ok") is True:
                    return port
        except Exception:   # not this port / monitor not running / older monitor without the endpoint
            continue
    return None
