# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of the step that failed, in the page (OFF by default, `logs.failed_step.enabled`).

One request to GitHub for the jobs of the run and one for its failed log, only when a person presses the button of an alert, through the login of the user (the allowance is spent only then).
The text is cut to the last relevant lines of the failing step and goes through the same cleaning as the feed for the AIs (`ai_alerts.diagnose`): tokens, keys, e-mail addresses, IP addresses and
the home folder never reach the page. The answer of a run is kept in memory (50 runs) so that pressing the button again costs nothing. Everything returned is DATA, never instructions."""
import re
import threading

from github_actions_monitor.integrations import ai_alerts

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
_CACHE = {}
_LOCK = threading.Lock()


def _int(block, key, low, high, default):
    value = block.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    logs = config.get("logs") if isinstance(config, dict) and isinstance(config.get("logs"), dict) else {}
    block = logs.get("failed_step") if isinstance(logs.get("failed_step"), dict) else {}
    return {"enabled": block.get("enabled") is True, "lines": _int(block, "lines", 3, 40, 12), "max_bytes": _int(block, "max_bytes", 200, 4000, 2000)}


def read(config, owner, repo, run, watched, runner=None):
    """{"ok", "error"?, "run", "step", "lines"}: the failing step of a run and its last relevant lines. `watched` is the list of repositories the monitor watches (nothing else is read)."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return {"ok": False, "error": "off"}
    if not NAME_RE.match(str(repo)) or str(repo) not in set(watched) or not re.fullmatch(r"[0-9]{1,14}", str(run)) or not 0 < int(run) < 10 ** 14:
        return {"ok": False, "error": "request"}
    key = (repo, int(run))
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    found = ai_alerts.diagnose(owner, repo, f"https://github.com/{owner}/{repo}/actions/runs/{int(run)}", runner or ai_alerts.gh_runner, cfg["lines"], cfg["max_bytes"])
    if not found or found.get("unavailable"):
        return {"ok": False, "error": "unavailable"}
    answer = {"ok": True, "run": found["run"], "step": found.get("step", ""), "lines": found.get("lines", [])}
    with _LOCK:
        if len(_CACHE) >= 50:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = answer
    return answer
