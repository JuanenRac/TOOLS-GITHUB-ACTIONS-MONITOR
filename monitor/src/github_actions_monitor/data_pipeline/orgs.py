# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The organisations of the login (`organizations.discover`, OFF by default). One read a day of `user/orgs` (the organisations the logged-in account belongs to); the page lists them in
Settings > Basic with the exact command to watch one of them.

What it does NOT do (and why): it does not put several owners in one page. Every repository is identified by its NAME alone in the monitor (the runs, the sentinel, the cache, the exports),
so two owners with a repository of the same name would mix; watching an organisation is done by a second monitor with `github_owner` set to it (own configuration file and port).
"""
import json
import os
import re
import time
from pathlib import Path
from github_actions_monitor.security import private_io

LOGIN_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
INTERVAL = 24 * 3600


def settings(config):
    cfg = config.get("organizations") if isinstance(config, dict) and isinstance(config.get("organizations"), dict) else {}
    return {"discover": cfg.get("discover") is True}


def clean(body):
    return sorted({str(o.get("login")) for o in (body if isinstance(body, list) else []) if isinstance(o, dict) and LOGIN_RE.match(str(o.get("login", "")))})


def view(config, reader, state_file, now=None, offline=False):
    """{"enabled", "orgs": [...], "checked_at"}. The last answer is kept in `state_file`; a failed read is silent."""
    if not settings(config)["discover"]:
        return {"enabled": False, "orgs": [], "checked_at": 0}
    now = time.time() if now is None else now
    try:
        state = json.loads(Path(state_file).read_text(encoding="utf-8"))
        state = state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        state = {}
    if not offline and (not state.get("checked_at") or now - float(state["checked_at"]) >= INTERVAL):
        try:
            state = {"checked_at": int(now), "orgs": clean(reader("user/orgs?per_page=100"))}
        except Exception:   # noqa: BLE001 - no permission or offline: the last answer stays, the next try is in an hour
            state = dict(state, checked_at=int(now) - INTERVAL + 3600)
        try:
            tmp = Path(str(state_file) + ".tmp")
            private_io.write_tmp(tmp, json.dumps(state) + "\n")
            os.replace(tmp, state_file)
        except OSError:
            pass
    return {"enabled": True, "orgs": [o for o in state.get("orgs") or [] if LOGIN_RE.match(str(o))], "checked_at": state.get("checked_at") or 0}
