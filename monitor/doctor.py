# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--doctor`: checks what the monitor needs and says, for each failure, the exact command that fixes it (in the language of the interface). Read-only: it changes nothing and prints no secret.

Checks: python, gh (installed), login (session), quota, network, folder (write permission), port (free), docker (optional), rich and textual (optional).
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
ORDER = ("python", "gh", "login", "quota", "network", "folder", "port", "docker", "rich", "textual")
FIX = {"python": "https://www.python.org/downloads/", "gh": "winget install --id GitHub.cli   |   brew install gh   |   sudo apt install gh", "login": "gh auth login",
       "quota": "gh api rate_limit", "network": "gh api rate_limit", "folder": "", "port": "python actions_monitor.py --port 8800", "docker": "", "rich": "pip install rich",
       "textual": "pip install textual"}


def default_runner(args, timeout=20):
    try:
        done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
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


def run(runner=default_runner, folder=HERE, ports=(8765, 8766), python=None):
    """The list of checks, in ORDER."""
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
                out["quota"] = ("ok" if core["remaining"] > 200 else "warn", "%d/%d" % (core["remaining"], core["limit"]))
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
    out["port"] = ("ok" if free else "warn", ", ".join(str(p) for p in free) or ", ".join(str(p) for p in ports))
    out["docker"] = ("ok" if shutil.which("docker") else "warn", "")
    out["rich"] = ("ok" if _module("rich") else "warn", "")
    out["textual"] = ("ok" if _module("textual") else "warn", "")
    return [{"id": name, "status": out[name][0], "detail": out[name][1], "fix": FIX[name] if out[name][0] != "ok" else ""} for name in ORDER]


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


def exit_code(checks):
    return 1 if any(c["status"] == "fail" for c in checks) else 0
