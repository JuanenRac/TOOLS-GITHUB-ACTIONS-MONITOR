# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--doctor`: checks what the monitor needs and says, for each failure, the exact command that fixes it (in the language of the interface). Read-only: it changes nothing and prints no secret.

Checks: python, gh (installed), login (session), quota (allowance left), network, folder (write permission), port (which ports are free and which are busy), docker (optional), rich and textual (optional),
targets (your own targets.json or only the neutral example), token (the one-use token of the page) and exposure (only this computer, or the network mode).
`--doctor --json` prints the same checks as one JSON document (no secret, no path of a person) for scripts.
Every check is {"id", "status": ok | warn | fail, "detail", "fix"}; `run()` takes the way of running a command as an argument so the tests need no `gh`.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from github_actions_monitor.util import paths
from github_actions_monitor.util.paths import ROOT as HERE   # the product folder
ORDER = ("python", "gh", "login", "quota", "network", "folder", "port", "docker", "rich", "textual", "targets", "token", "exposure", "risks", "backend", "degraded", "credential", "timezone", "github_app", "layout", "storage", "retention")
FIX = {"python": "https://www.python.org/downloads/", "gh": "winget install --id GitHub.cli   |   brew install gh   |   sudo apt install gh", "login": "gh auth login",
       "quota": "gh api rate_limit", "network": "gh api rate_limit", "folder": "", "port": "python bin/actions_monitor.py --port 8800", "docker": "", "rich": "pip install rich",
       "textual": "pip install textual", "targets": "python bin/actions_monitor.py --init-catalog", "token": "", "exposure": "", "risks": "", "backend": "", "degraded": "", "credential": "", "timezone": "", "github_app": "", "layout": "python -m github_actions_monitor.util.rootmigrate --apply", "storage": "python tools/migrate_storage.py --from file --to sqlite", "retention": ""}


def default_runner(args, timeout=20):
    try:
        from github_actions_monitor.security import secretstore
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
    own = [n for n in ("targets.json", "ecosystems.json", "profiles.json") if paths.place(n, folder).is_file()]
    out["targets"] = ("ok" if paths.place("targets.json", folder).is_file() else "warn", ", ".join(own) if own else "example only")
    guard = config.get("session_guard", True) is True
    out["token"] = ("ok" if guard else "warn", "one-use, 10 min" if guard else "off")
    listen = config.get("listen") if isinstance(config.get("listen"), dict) else {}
    network = listen.get("network") is True
    out["exposure"] = ("warn" if network else "ok", ("network " + str(listen.get("host", ""))) if network else "127.0.0.1")
    out["risks"] = risks(config)
    out["backend"] = token_backend(config)
    from github_actions_monitor.app import degraded
    swallowed, origins = degraded.read(paths.folder("data", folder))
    out["degraded"] = ("warn" if swallowed else "ok", (f"{swallowed}: " + ", ".join(f"{k} {v}" for k, v in sorted(origins.items(), key=lambda kv: -kv[1])[:5])) if swallowed else "0")
    out["credential"] = shared_credential(folder)
    out["timezone"] = time_zone(config)
    out["github_app"] = github_app_check(config)
    out["layout"] = layout_check(folder)
    out["storage"] = storage_check(config, folder)
    out["retention"] = retention_check(config, folder)
    return [{"id": name, "status": out[name][0], "detail": out[name][1], "fix": FIX[name] if out[name][0] != "ok" else ""} for name in ORDER]


def time_zone(config):
    """("ok" | "warn", the setting): the zone of the times for people. A name that neither the system nor the built-in table knows would be shown in UTC (the settings page refuses it, a hand-edited file
    or MONITOR_TIMEZONE can still carry it)."""
    from github_actions_monitor.util import tzdisplay
    display = config.get("display") if isinstance(config.get("display"), dict) else {}
    setting = os.environ.get("MONITOR_TIMEZONE", "").strip() or (display.get("timezone") if isinstance(display.get("timezone"), str) else "") or "local"
    return ("ok" if tzdisplay.valid_setting(setting) else "warn"), setting[:64]


def layout_check(folder=HERE):
    """("ok" | "warn", detail): files of the old flat layout (versions up to 1.7.9) or data of 1.8.1 and older (state, logs, AI files) still lying next to the launchers. The monitor starts by moving
    the second kind by itself (rootmigrate); tools/migrate_layout.py moves the first away."""
    from github_actions_monitor.util import layout, rootmigrate
    left = [p.as_posix() for p in layout.stale(folder)] + [source.name for source, _destination in rootmigrate.plan(folder)]
    if not left:
        return "ok", "src/ assets/ config/ data/ logs/ ai/"
    return "warn", f"{len(left)}: " + ", ".join(left[:5])


def _account_configs(config, folder):
    """[(account id or '', its configuration)] the storage and the retention checks look at: every enabled account of an accounts/ layout, else the one configuration."""
    from github_actions_monitor.accounts import accounts
    try:
        ids = accounts.enabled_accounts(folder) if accounts.layout(folder) == "accounts" else []
    except Exception:       # noqa: BLE001 - the doctor must always answer
        ids = []
    out = []
    for account_id in ids:
        try:
            cfg = json.loads(accounts.config_path(account_id, folder).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {}
        out.append((account_id, cfg if isinstance(cfg, dict) else {}))
    return out or [("", config)]


def storage_check(config, folder=HERE):
    """("ok" | "warn", detail): the backend of the state. Files = ok. SQLite = the database exists, passes SQLite's integrity check and has a schema this version understands (read only: nothing is
    created or migrated here)."""
    from github_actions_monitor.accounts import accounts
    from github_actions_monitor.storage import factory
    problems, backends = [], set()
    for account_id, cfg in _account_configs(config, folder):
        settings = factory.settings(cfg.get("storage"))
        backends.add(settings["backend"])
        if settings["backend"] != "sqlite":
            continue
        from github_actions_monitor.storage import sqlite_storage
        path = Path(settings["path"]) if settings["path"] else (accounts.account_dir(account_id, folder) / factory.DB_NAME if account_id else paths.place(factory.DB_NAME, folder))
        info = sqlite_storage.inspect(path)
        label = account_id or "default"
        if not info["exists"]:
            problems.append(f"{label}: no database yet")
        problems += [f"{label}: {p}" for p in info["problems"]]
    detail = "+".join(sorted(backends)) or "file"
    return ("warn", detail + " - " + "; ".join(problems[:3])) if problems else ("ok", detail)


def _folder_bytes(path):
    total = 0
    try:
        for item in Path(path).rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except OSError:
        pass
    return total


def retention_check(config, folder=HERE, env=None):
    """("ok" | "warn", detail): the size of the events of every account against `retention.warn_events_mb`, and, for a monitor that runs as a service, whether a `retention` block exists at all
    (without one the defaults apply, which is fine, but a service that is left alone for months should say what it keeps). Read only."""
    from github_actions_monitor.accounts import accounts
    from github_actions_monitor.storage import factory, retention
    service = retention.service_mode(config, env)
    notes, biggest = [], 0
    for account_id, cfg in _account_configs(config, folder):
        cfg_r = retention.settings(cfg)
        sqlite = factory.settings(cfg.get("storage"))["backend"] == "sqlite"
        base = accounts.account_dir(account_id, folder) if account_id else paths.folder("data", folder)
        if sqlite:
            size = (base / "storage.sqlite3").stat().st_size if (base / "storage.sqlite3").is_file() else 0
        else:
            size = (_folder_bytes(base / "events") if account_id else sum(p.stat().st_size for p in base.glob("events_monitor.jsonl") if p.is_file()))
        biggest = max(biggest, size)
        label = account_id or "default"
        if size > cfg_r["warn_events_mb"] * 1024 * 1024:
            notes.append(f"{label}: {size // (1024 * 1024)} MB > {cfg_r['warn_events_mb']} MB")
        if cfg_r["enabled"] is False and service:
            notes.append(f"{label}: off")
        elif service and not retention.configured(cfg):
            notes.append(f"{label}: not configured")
    detail = f"{biggest // 1024} KB" if biggest < 1024 * 1024 else f"{biggest // (1024 * 1024)} MB"
    return ("warn", detail + " - " + "; ".join(notes[:3])) if notes else ("ok", detail)


def github_app_check(config):
    """("ok" | "warn", detail): off = ok; on = the program openssl, the key file and its permissions. Never the key, never a token."""
    from github_actions_monitor.integrations import github_app
    cfg = github_app.settings(config)
    if not cfg["enabled"]:
        return "ok", "off"
    problems = []
    if not shutil.which("openssl"):
        problems.append("openssl missing")
    if not cfg["app_id"]:
        problems.append("app_id missing")
    if not cfg["key_path"]:
        problems.append("key_path missing")
    else:
        warning = github_app.key_warning(cfg["key_path"])
        if warning:
            problems.append(warning)
    return ("warn", "; ".join(problems)) if problems else ("ok", "on")


def fingerprint(secret):
    """A short digest that tells two equal credentials apart from two different ones without showing either: the first 8 hexadecimal digits of the SHA-256. Never the credential itself."""
    import hashlib
    return hashlib.sha256(str(secret).encode("utf-8")).hexdigest()[:8]


def shared_credential(folder=HERE, env=None, loader=None):
    """("ok" | "warn", detail): whether two or more accounts of the supervisor would read GitHub with the SAME personal access token. The credential of an account is the token kept by the
    monitor when the configuration of that account turns `github_token.enabled` on (the store is one per user, so every such account gets the same one), else the token of the environment
    (GH_TOKEN, GITHUB_TOKEN) that every account process inherits, else nothing (the login of `gh`, which is not compared). Only a fingerprint is compared and shown, never a token."""
    from github_actions_monitor.accounts import accounts
    env = os.environ if env is None else env
    try:
        ids = accounts.enabled_accounts(folder)
    except Exception:       # noqa: BLE001 - the doctor must always answer
        ids = []
    if len(ids) < 2:
        return "ok", "single account" if not ids else "1"
    inherited = next((env.get(name) for name in ("GH_TOKEN", "GITHUB_TOKEN") if (env.get(name) or "").strip()), "")
    kept = None
    groups = {}
    for account_id in ids:
        try:
            cfg = json.loads(accounts.config_path(account_id, folder).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {}
        settings = cfg.get("github_token") if isinstance(cfg, dict) and isinstance(cfg.get("github_token"), dict) else {}
        secret = ""
        if settings.get("enabled") is True:
            if kept is None:
                try:
                    from github_actions_monitor.security import secretstore
                    kept = (loader or secretstore.Store(settings.get("store") if settings.get("store") in ("auto", "system", "file") else "auto").load)() or ""
                except Exception:       # noqa: BLE001
                    kept = ""
            secret = kept
        try:      # a login put in place for this account alone (security/credential.py) is the one it uses before any other
            from github_actions_monitor.security import credential
            own = credential.read_file(credential.path_in(accounts.account_dir(account_id, folder)))
        except Exception:       # noqa: BLE001
            own = ""
        secret = own or secret or inherited
        if secret:
            groups.setdefault(fingerprint(secret), []).append(account_id)
    shared = {fp: names for fp, names in groups.items() if len(names) > 1}
    if not shared:
        return "ok", "%d accounts" % len(ids)
    return "warn", "; ".join("%s: %s" % (fp, ", ".join(names[:6])) for fp, names in sorted(shared.items()))


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
        from github_actions_monitor.security import secretstore
        kind = (store_factory or secretstore.Store)(token.get("store") if token.get("store") in ("auto", "system", "file") else "auto").backend()
    except Exception:
        return "warn", "?"
    return ("warn" if kind == "file" else "ok"), str(kind)


def text(checks, translate, banner_for=None):
    sign = {"ok": "[ OK ]", "warn": "[warn]", "fail": "[FAIL]"}
    from github_actions_monitor.util import banner
    lines = [translate("doctor.title"), "=" * 40] if not banner_for else [banner.line(banner_for == "lite", 8766 if banner_for == "lite" else 8765, "actions_monitor_lite.json" if banner_for == "lite" else "actions_monitor.json", translate), translate("doctor.title"), "=" * 40]
    for item in checks:
        row = f"{sign[item['status']]} {translate('doctor.t.' + item['id'])}" + (f" ({item['detail']})" if item["detail"] else "")
        lines.append(row)
        if item["status"] != "ok":
            lines.append("       " + translate("doctor.f." + item["id"]) + (f"\n       > {item['fix']}" if item["fix"] else ""))
    bad = sum(1 for c in checks if c["status"] == "fail")
    lines += ["", translate("doctor.all_ok") if not bad else translate("doctor.n_fail", n=bad)]
    return "\n".join(lines) + "\n"


def as_json(checks, edition="complete"):
    """The checks as one JSON-ready dictionary: {"version", "edition", "ok", "checks": [{"id", "status", "detail", "fix"}]}. No secret and no path of a person."""
    from github_actions_monitor.tool_version import TOOL_VERSION
    from github_actions_monitor.ui import about
    return {"version": TOOL_VERSION, "edition": "lite" if edition == "lite" else "complete", "ok": not any(c["status"] == "fail" for c in checks),
            "checks": [{**c, "detail": about.home_free(c["detail"])} for c in checks]}


def exit_code(checks):
    return 1 if any(c["status"] == "fail" for c in checks) else 0
