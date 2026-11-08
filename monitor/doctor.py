# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--doctor`: checks what the monitor needs and says, for each failure, the exact command that fixes it (in the language of the interface). Read-only: it changes nothing and prints no secret.

Checks: python, gh (installed), login (session), quota (allowance left), network, folder (write permission), port (which ports are free and which are busy), docker (optional), rich and textual (optional),
targets (your own targets.json or only the neutral example), token (the one-use token of the page) and exposure (only this computer, or the network mode).
`--doctor --json` prints the same checks as one JSON document (no secret, no path of a person) for scripts.
Every check is {"id", "status": ok | warn | fail, "detail", "fix"}; `run()` takes the way of running a command as an argument so the tests need no `gh`.
"""
import json
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ("python", "gh", "login", "quota", "network", "folder", "port", "docker", "rich", "textual", "targets", "token", "exposure", "risks", "backend", "degraded")
FIX = {"python": "https://www.python.org/downloads/", "gh": "winget install --id GitHub.cli   |   brew install gh   |   sudo apt install gh", "login": "gh auth login",
       "quota": "gh api rate_limit", "network": "gh api rate_limit", "folder": "", "port": "python actions_monitor.py --port 8800", "docker": "", "rich": "pip install rich",
       "textual": "pip install textual", "targets": "python actions_monitor.py --init-catalog", "token": "", "exposure": "", "risks": "", "backend": "", "degraded": ""}


def default_runner(args, timeout=20):
    try:
        import secretstore
        done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **(secretstore.gh_kwargs() if args and args[0] == "gh" else {}))
        return done.returncode, done.stdout, done.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, "", str(error)


def _module(name):
    try:
        import importlib.util
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _port_free(port):
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _writable(folder):
    try:
        with tempfile.TemporaryFile(dir=str(folder)):
            return True
    except OSError:
        return False


def run(runner=default_runner, folder=HERE, ports=(8765, 8766), python=None, config=None):
    """The list of checks, in ORDER. `config` is the content of the configuration file ({} when there is none)."""
    config = config if isinstance(config, dict) else {}
    version = python or sys.version_info[:3]
    out = {}
    out["python"] = ("ok" if tuple(version) >= (3, 11) else "fail", "%d.%d.%d" % tuple(version[:3]))
    have_gh = shutil.which("gh") is not None
    out["gh"] = ("ok" if have_gh else "fail", "")
    if have_gh:
        code, stdout, stderr = runner(["gh", "auth", "status"])
        out["login"] = ("ok" if code == 0 else "fail", "")
        code, stdout, stderr = runner(["gh", "api", "rate_limit"])
        if code == 0:
            try:
                core = json.loads(stdout)["resources"]["core"]
                out["quota"] = ("ok" if core["remaining"] > 200 else "warn", "%d/%d" % (core["remaining"], core["limit"]))      # the allowance left, as the page shows it
            except (ValueError, KeyError, TypeError):
                out["quota"] = ("warn", "")
            out["network"] = ("ok", "")
        else:
            out["quota"] = ("warn", "")
            out["network"] = ("fail", (stderr or "").strip()[:120])
    else:
        for name in ("login", "quota", "network"):
            out[name] = ("warn", "gh")
    out["folder"] = ("ok" if _writable(folder) else "fail", str(folder))
    free = [p for p in ports if _port_free(p)]
    busy = [p for p in ports if p not in free]
    out["port"] = ("ok" if free else "warn", ("free " + ", ".join(str(p) for p in free) if free else "") + (" · " if free and busy else "") + ("busy " + ", ".join(str(p) for p in busy) if busy else ""))
    out["docker"] = ("ok" if shutil.which("docker") else "warn", "")
    out["rich"] = ("ok" if _module("rich") else "warn", "")
    out["textual"] = ("ok" if _module("textual") else "warn", "")
    own = [n for n in ("targets.json", "ecosystems.json", "profiles.json") if (Path(folder) / n).is_file()]
    out["targets"] = ("ok" if (Path(folder) / "targets.json").is_file() else "warn", ", ".join(own) if own else "example only")
    guard = config.get("session_guard", True) is True
    out["token"] = ("ok" if guard else "warn", "one-use, 10 min" if guard else "off")
    listen = config.get("listen") if isinstance(config.get("listen"), dict) else {}
    network = listen.get("network") is True
    out["exposure"] = ("warn" if network else "ok", ("network " + str(listen.get("host", ""))) if network else "127.0.0.1")
    out["risks"] = risks(config)
    out["backend"] = token_backend(config)
    import degraded
    swallowed, origins = degraded.read(folder)
    out["degraded"] = ("warn" if swallowed else "ok", (f"{swallowed}: " + ", ".join(f"{k} {v}" for k, v in sorted(origins.items(), key=lambda kv: -kv[1])[:5])) if swallowed else "0")
    return [{"id": name, "status": out[name][0], "detail": out[name][1], "fix": FIX[name] if out[name][0] != "ok" else ""} for name in ORDER]


def risks(config):
    """("ok" | "warn", codes): the dangerous combinations of options. network_all = listening on every interface (prefer one private address); execute_network = the AI may run
    actions while the monitor is reachable from the network; token_file = the own GitHub token kept in a plain 600 file (the weakest store); act_network = local runs of act while
    the monitor is reachable from the network."""
    listen = config.get("listen") if isinstance(config.get("listen"), dict) else {}
    network = listen.get("network") is True
    found = []
    if network and listen.get("host") == "0.0.0.0":
        found.append("network_all")
    ai_actions = (config.get("ai") or {}).get("actions") if isinstance(config.get("ai"), dict) else None
    if network and isinstance(ai_actions, dict) and ai_actions.get("enabled") is True and ai_actions.get("execute") is True:
        found.append("execute_network")
    token = config.get("github_token") if isinstance(config.get("github_token"), dict) else {}
    if token.get("enabled") is True and token.get("store") == "file":
        found.append("token_file")
    if network and isinstance(config.get("act"), dict) and config["act"].get("enabled") is True:
        found.append("act_network")
    return ("warn" if found else "ok", ", ".join(found))


def token_backend(config, store_factory=None):
    """The place the own token is kept (never the token). "ok" for the store of the system, "warn" for the plain file; "ok" and `off` when the feature is off."""
    token = config.get("github_token") if isinstance(config.get("github_token"), dict) else {}
    if token.get("enabled") is not True:
        return "ok", "off"
    try:
        import secretstore
        kind = (store_factory or secretstore.Store)(token.get("store") if token.get("store") in ("auto", "system", "file") else "auto").backend()
    except Exception:
        return "warn", "?"
    return ("warn" if kind == "file" else "ok"), str(kind)


def text(checks, translate, banner_for=None):
    sign = {"ok": "[ OK ]", "warn": "[warn]", "fail": "[FAIL]"}
    import banner
    lines = [translate("doctor.title"), "=" * 40] if not banner_for else [banner.line(banner_for == "lite", 8766 if banner_for == "lite" else 8765, "actions_monitor_lite.json" if banner_for == "lite" else "actions_monitor.json", translate), translate("doctor.title"), "=" * 40]
    for item in checks:
        row = f"{sign[item['status']]} {translate('doctor.t.' + item['id'])}" + (f" ({item['detail']})" if item["detail"] else "")
        lines.append(row)
        if item["status"] != "ok":
            lines.append("       " + translate("doctor.f." + item["id"]) + (f"\n       > {item['fix']}" if item["fix"] else ""))
    bad = sum(1 for c in checks if c["status"] == "fail")
    lines += ["", translate("doctor.all_ok") if not bad else translate("doctor.n_fail", n=bad)]
    return "\n".join(lines) + "\n"


def as_json(checks, edition="full"):
    """The checks as one JSON-ready dictionary: {"version", "edition", "ok", "checks": [{"id", "status", "detail", "fix"}]}. No secret and no path of a person."""
    from tool_version import TOOL_VERSION
    import about
    return {"version": TOOL_VERSION, "edition": "lite" if edition == "lite" else "full", "ok": not any(c["status"] == "fail" for c in checks),
            "checks": [{**c, "detail": about.home_free(c["detail"])} for c in checks]}


def exit_code(checks):
    return 1 if any(c["status"] == "fail" for c in checks) else 0
